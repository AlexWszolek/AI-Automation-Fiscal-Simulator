"""Fetch Korean occupation/industry wage tables from the MOEL statHtml mirror.

KOSIS proper sits behind an SSO handshake, but MOEL mirrors the same tables at
`stathtml.moel.go.kr` with no login and a bulk-export endpoint. The flow this script
automates is the site's own "대용량 다운로드" (bulk download):

    GET  /statHtml/statHtml.do?orgId=118&tblId=<ID>&conn_path=I2   # session + metadata
    POST /statHtml/makeLarge.do                                    # server builds the file
    POST /statHtml/downLarge.do?file=<name>                        # fetch it (SpreadsheetML)

The statHtml page embeds everything needed to construct the OLAP request in its JS:
dimension member codes (`defaultTempClass.push("<classId>^<lvl>#<member>")`), item ids
(`defaultTempItem.push`), the row/column axes, and per-dimension member counts
(`var totalCnt = "N"`). We parse those rather than hardcoding per-table constants, and
fail loudly if a dimension's default selection does not cover its full member list.

Outputs per table, under data/raw/korea/:
    <tblId>.xml.gz    the raw SpreadsheetML exactly as served (EUC-KR bytes), gzipped
    <tblId>.tidy.csv  long format, UTF-8: one row per dimension-combination x item x year

Run:  .venv/bin/python scripts/fetch_korea_tables.py [--dry-run] [--table DT_118N_PAYM39]
      .venv/bin/python scripts/fetch_korea_tables.py --parse-only   # no network: rebuild
                                                     # tidy CSVs from committed .xml.gz
"""
from __future__ import annotations

import argparse
import csv
import gzip
import io
import json
import re
import sys
from pathlib import Path

import requests
from lxml import etree

BASE = "https://stathtml.moel.go.kr"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw" / "korea"

# Years are pinned per table (verified vintages, research doc §9); the parser asserts the
# export's year columns match, so a silently-shorter series cannot slip through.
TABLES = {
    # occupation x sex x wage bracket x age: worker count + hours (KSCO 6th major groups)
    "DT_118N_PAYM39": {"years": ["2025", "2024", "2023", "2022", "2021", "2020"]},
    # industry x education x age x sex: mean wage + worker count (19 industries)
    "DT_118N_PAYN42": {"years": ["2025", "2024", "2023", "2022", "2021", "2020"]},
}


def parse_form_pairs(html: str) -> list[tuple[str, str]]:
    """Serialize the ParamInfo form the way jQuery's .serialize() would."""
    scope_m = re.search(r'<form[^>]*id="ParamInfo"(.*?)</form>', html, re.S)
    if not scope_m:
        raise RuntimeError("ParamInfo form not found — page layout changed")
    scope = scope_m.group(1)
    pairs = []
    for m in re.finditer(r"<input([^>]*?)/?>", scope):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        name = attrs.get("name")
        if not name:
            continue
        typ = attrs.get("type", "text").lower()
        if typ in ("checkbox", "radio") and "checked" not in m.group(1):
            continue
        if typ in ("button", "submit", "image"):
            continue
        pairs.append((name, attrs.get("value", "")))
    for m in re.finditer(r"<select([^>]*)>(.*?)</select>", scope, re.S):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        name = attrs.get("name")
        if not name:
            continue
        sel = (re.search(r'<option[^>]*selected[^>]*value="([^"]*)"', m.group(2))
               or re.search(r'<option[^>]*value="([^"]*)"', m.group(2)))
        if sel:
            pairs.append((name, sel.group(1)))
    return pairs


def parse_meta(html: str) -> dict:
    """Pull the OLAP metadata out of the page JS and class-selection popup markup."""
    # dimensions, in declaration order: var defaultClassId = "X"; var totalCnt = "N"; ...
    dims = []
    for m in re.finditer(
        r'var defaultClassId = "([^"]+)";\s*'
        r'var totalCnt\s*=\s*"(\d+)";\s*'
        r'var classSn\s*=\s*"(\d+)";\s*'
        r'var classNm\s*=\s*"([^"]*)";', html):
        dims.append({"classId": m.group(1), "totalCnt": int(m.group(2)),
                     "sn": int(m.group(3)), "name": m.group(4), "members": [],
                     "labels": {}})
    if not dims:
        raise RuntimeError("no dimension declarations found")
    by_sn = {d["sn"]: d for d in dims}
    # every member (level 1) is listed in the class popup:
    #   <input id="classChkLi<sn>_1_<code>" name="classChkLi<sn>_1" value="<code>=" title="<label>">
    for m in re.finditer(
            r'name="classChkLi(\d+)_1"[^>]*?\svalue="([^"=]+)=?"[^>]*?\stitle="([^"]*)"',
            html, re.S):
        sn, code, label = int(m.group(1)), m.group(2), m.group(3)
        if sn in by_sn and code not in by_sn[sn]["labels"]:
            by_sn[sn]["members"].append(code)
            by_sn[sn]["labels"][code] = label
    for d in dims:
        if len(d["members"]) != d["totalCnt"]:
            raise RuntimeError(
                f"dimension {d['classId']} ({d['name']}): popup lists "
                f"{len(d['members'])} level-1 members, expected {d['totalCnt']} — "
                f"refusing to pull a partial table")
    items, item_labels = [], {}
    for m in re.finditer(
            r'name="itemChkLi"[^>]*?\svalue="([^"]+)"[^>]*?\stitle="([^"]*)"', html, re.S):
        if m.group(1) not in item_labels:
            items.append(m.group(1))
            item_labels[m.group(1)] = m.group(2)
    if not items:
        raise RuntimeError("no item declarations found")
    row_axis = re.findall(r'defaultRowList\.push\("([^"]+)"\)', html)
    col_axis = re.findall(r'defaultColList\.push\("([^"]+)"\)', html)
    dim_co_m = re.search(r'var g_dimCo = "(\d+)"', html)
    if not (row_axis and col_axis and dim_co_m):
        raise RuntimeError("axes or dimCo not found")
    return {"dims": dims, "items": items, "itemLabels": item_labels,
            "rowAxis": row_axis, "colAxis": col_axis, "dimCo": dim_co_m.group(1)}


def fetch_table(tbl_id: str, years: list[str], dry_run: bool = False) -> bytes | None:
    s = requests.Session()
    s.headers.update({"User-Agent": UA})
    r = s.get(f"{BASE}/statHtml/statHtml.do",
              params={"orgId": "118", "tblId": tbl_id, "conn_path": "I2"}, timeout=60)
    r.raise_for_status()
    html = r.text
    s.headers.update({"Referer": r.url, "X-Requested-With": "XMLHttpRequest"})

    meta = parse_meta(html)
    n_class_cells = 1
    for d in meta["dims"]:
        n_class_cells *= len(d["members"])
    item_multiply = n_class_cells * len(meta["items"])
    req_cells = item_multiply * len(years)
    print(f"[{tbl_id}] dims: " + " x ".join(
        f"{d['name']}({len(d['members'])})" for d in meta["dims"])
        + f"; items: {len(meta['items'])}; years: {len(years)}; cells: {req_cells:,}")
    if dry_run:
        print(f"[{tbl_id}] items: " + ", ".join(
            f"{i}={meta['itemLabels'][i]}" for i in meta["items"]))
        for d in meta["dims"]:
            print(f"[{tbl_id}]   {d['classId']} ({d['name']}): "
                  + ", ".join(f"{c}={d['labels'][c]}" for c in d["members"]))
        return None

    field_list = [{"targetId": "PRD", "targetValue": "",
                   "prdValue": "Y," + ",".join(years) + ",@"}]
    for it in meta["items"]:
        field_list.append({"targetId": "ITM_ID", "targetValue": it, "prdValue": ""})
    for lvl, d in enumerate(meta["dims"], start=1):
        for c in d["members"]:
            field_list.append({"targetId": f"OV_L{lvl}_ID", "targetValue": c, "prdValue": ""})
    class_all = [{"objVarId": d["classId"], "ovlSn": str(i)}
                 for i, d in enumerate(meta["dims"], start=1)]

    override = {
        "fieldList": json.dumps(field_list, separators=(",", ":")),
        "classAllArr": json.dumps(class_all, separators=(",", ":")),
        "rowAxis": ",".join(meta["rowAxis"]),
        "colAxis": ",".join(meta["colAxis"]),
        "isFirst": "N",
        "reqCellCnt": str(req_cells),
        "viewKind": "2",           # the fn_downLargeSubmit() constants
        "view": "excel",
        "viewSubKind": "2_7_1",
        "itemMultiply": str(item_multiply),
        "dimCo": meta["dimCo"],
        "selectAllFlag": "N",
        "doAnal": "N",
    }
    pairs = parse_form_pairs(html)
    out = [(k, override.get(k, v)) for k, v in pairs if k not in ("itemChkLi", "timeChkY")]
    seen = {k for k, _ in out}
    out += [(k, v) for k, v in override.items() if k not in seen]
    out += [("itemChkLi", it) for it in meta["items"]]
    out += [("timeChkY", y) for y in years]

    r2 = s.post(f"{BASE}/statHtml/makeLarge.do", data=out, timeout=900)
    r2.raise_for_status()
    fname = r2.json().get("file")
    if not fname:
        raise RuntimeError(f"makeLarge returned no file: {r2.text[:300]}")
    r3 = s.post(f"{BASE}/statHtml/downLarge.do", params={"file": fname},
                data=out + [("file", fname)], timeout=900)
    r3.raise_for_status()
    if b"<Workbook" not in r3.content[:2000]:
        raise RuntimeError(f"downLarge did not return SpreadsheetML: {r3.content[:200]!r}")
    return r3.content, meta


SS = "{urn:schemas-microsoft-com:office:spreadsheet}"


def tidy_rows(raw: bytes, tbl_id: str, years: list[str]):
    """SpreadsheetML -> long-format rows. Yields header first, then data rows."""
    text = raw.decode("euc-kr")
    root = etree.fromstring(text.encode("utf-8"),
                            parser=etree.XMLParser(recover=True, huge_tree=True))
    rows = []
    for row in root.iter(f"{SS}Row"):
        rows.append([d.text if d.text is not None else ""
                     for d in row.iter(f"{SS}Data")])
    # locate the header row: contains 항목 and 단위
    hdr_i = next(i for i, r in enumerate(rows) if "항목" in r and "단위" in r)
    hdr = rows[hdr_i]
    item_col = hdr.index("항목")
    unit_col = hdr.index("단위")
    dim_names = hdr[:item_col]
    year_cols = [(j, c.replace("년", "").strip()) for j, c in enumerate(hdr)
                 if re.match(r"^\d{4}\s*년?$", c.strip())]
    got_years = sorted(y for _, y in year_cols)
    if got_years != sorted(years):
        raise RuntimeError(f"{tbl_id}: year columns {got_years} != requested {sorted(years)}")
    yield dim_names + ["item", "unit", "year", "value"]
    n_data = 0
    for r in rows[hdr_i + 1:]:
        if len(r) < unit_col + 1:
            continue
        for j, y in year_cols:
            val = r[j].strip() if j < len(r) else ""
            yield r[:item_col] + [r[item_col], r[unit_col], y, val]
            n_data += 1
    print(f"[{tbl_id}] parsed {n_data:,} data cells across {len(dim_names)} dimensions")


def validate_paym39(csv_path: Path) -> None:
    """Pin the scrape to the totals recorded in docs/research/korea-fiscal-system.md §9.0."""
    # keyed by KSCO 6th major-group number (the "(N)" suffix in the export labels),
    # "T" = 전직종; values are the 2025 counts recorded in the research doc
    expected_2025 = {
        "T": 12_413_858, "1": 120_892, "2": 3_669_625, "3": 3_447_778, "4": 960_008,
        "5": 561_179, "6": 28_684, "7": 758_694, "8": 1_835_977, "9": 1_031_019,
    }
    got = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        hdr = next(rdr)
        for r in rdr:
            if (r[1] == "전체" and r[2] == "전체" and r[3] == "전체"
                    and r[hdr.index("item")] == "근로자수" and r[hdr.index("year")] == "2025"):
                v = r[hdr.index("value")]
                m = re.search(r"\((\d)\)$", r[0])
                key = m.group(1) if m else ("T" if r[0] == "전직종" else None)
                if key and v not in ("", "-"):
                    got[key] = round(float(v))
    missing = set(expected_2025) - set(got)
    assert not missing, f"PAYM39 validation: occupations absent from scrape: {missing}"
    bad = {k: (got[k], expected_2025[k]) for k in expected_2025 if got[k] != expected_2025[k]}
    assert not bad, f"PAYM39 validation: 2025 worker counts diverge (got, expected): {bad}"
    total_of_groups = sum(v for k, v in expected_2025.items() if k != "T")
    # survey-weighted counts are independently rounded, so the groups can miss the
    # published total by a few workers (2025: off by 2)
    assert abs(total_of_groups - expected_2025["T"]) <= 5, \
        f"occupation groups sum to {total_of_groups:,}, total is {expected_2025['T']:,}"
    print(f"[DT_118N_PAYM39] validation OK: 2025 totals match the recorded calibration "
          f"numbers ({expected_2025['T']:,} wage workers)")


def validate_payn42(csv_path: Path) -> None:
    """Pin the all-total 2025 row to the research doc's anchors."""
    want = {"월임금총액": 4_482, "근로자수": 12_413_858}
    got = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        rdr = csv.reader(f)
        hdr = next(rdr)
        for r in rdr:
            if (r[0] == "전체" and r[1] == "전학력" and r[2] == "전체" and r[3] == "전체"
                    and r[hdr.index("year")] == "2025" and r[hdr.index("item")] in want):
                got[r[hdr.index("item")]] = round(float(r[hdr.index("value")]))
    assert got == want, f"PAYN42 validation: 2025 anchors diverge (got {got}, want {want})"
    print("[DT_118N_PAYN42] validation OK: 2025 mean wage ₩4,482k and worker count match")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=sorted(TABLES), help="fetch a single table")
    ap.add_argument("--dry-run", action="store_true",
                    help="print discovered metadata, fetch nothing")
    ap.add_argument("--parse-only", action="store_true",
                    help="rebuild tidy CSVs from the committed raw exports, no network")
    args = ap.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for tbl_id, cfg in TABLES.items():
        if args.table and tbl_id != args.table:
            continue
        if args.parse_only:
            raw = gzip.open(RAW_DIR / f"{tbl_id}.xml.gz", "rb").read()
            meta = None
        else:
            result = fetch_table(tbl_id, cfg["years"], dry_run=args.dry_run)
            if result is None:
                continue
            raw, meta = result
        raw_path = RAW_DIR / f"{tbl_id}.xml.gz"
        if meta is not None:
            meta_path = RAW_DIR / f"{tbl_id}.meta.json"
            meta_path.write_text(json.dumps({
                "tblId": tbl_id, "years": cfg["years"],
                "items": {i: meta["itemLabels"][i] for i in meta["items"]},
                "dims": [{"classId": d["classId"], "name": d["name"],
                          "members": {c: d["labels"][c] for c in d["members"]}}
                         for d in meta["dims"]],
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            with gzip.open(raw_path, "wb") as f:
                f.write(raw)
        csv_path = RAW_DIR / f"{tbl_id}.tidy.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            for row in tidy_rows(raw, tbl_id, cfg["years"]):
                w.writerow(row)
        print(f"[{tbl_id}] wrote {raw_path.name} "
              f"({raw_path.stat().st_size/1e6:.1f} MB) and {csv_path.name} "
              f"({csv_path.stat().st_size/1e6:.1f} MB)")
        if tbl_id == "DT_118N_PAYM39":
            validate_paym39(csv_path)
        elif tbl_id == "DT_118N_PAYN42":
            validate_payn42(csv_path)


if __name__ == "__main__":
    main()
