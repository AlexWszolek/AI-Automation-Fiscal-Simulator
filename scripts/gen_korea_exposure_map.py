"""Map the US per-occupation exposure measures onto KSCO 6th major groups.

    .venv/bin/python scripts/gen_korea_exposure_map.py

Path: SOC 2018 (the Budget Lab / Webb files' codes) → SOC 2010 (O*NET crosswalk) → ISCO-08
(BLS crosswalk, via the eworx mirror) → KSCO major. KSCO majors are ISCO-08 majors except that
KSCO 2 (전문가 및 관련 종사자) = ISCO 2 + 3 and ISCO 5 splits into KSCO 4 (service: 51/53/54)
and KSCO 5 (sales: 52). A SOC occupation that maps to several KSCO majors has its employment
split equally across them. Weighted by US employment (the Budget Lab file's counts) — the
only occupation-level employment available on the US side of the map.

Two vectors come out: ROBOT_SHARE (Webb's robot-patent exposure percentile/100 — the physical
channel Korea has no published measure for) and US_COGNITIVE_SHARE (the Budget Lab percentile
share — reference / sensitivity only; the cognitive headline stays on the BOK read). Prints
the literals for fiscal_model/korea_exposure.py; the test regenerates and compares.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CW = ROOT / "data" / "raw" / "crosswalks"

KSCO_NAMES = {1: "managers", 2: "professionals+related", 3: "clerical", 4: "service", 5: "sales",
              6: "agriculture/fishery", 7: "craft", 8: "operators/assemblers", 9: "elementary"}


def isco_to_ksco(isco4: str) -> int | None:
    major = int(isco4[0])
    if major == 0:
        return None                          # armed forces: not in the KSCO frame
    if major == 3:
        return 2                             # technicians sit inside KSCO 2
    if major == 4:
        return 3                             # clerical support → KSCO 3 사무 종사자
    if major == 5:
        return 5 if isco4[:2] == "52" else 4  # sales (52) vs service (51/53/54)
    return major


def build_map() -> tuple[dict, dict, pd.DataFrame]:
    from fiscal_model import levers, loaders
    occ = loaders.load_ai_exposure(validate=False)["occ"].copy()
    occ["cog_share"] = levers.cognitive_exposure(occ["ai_pca_score"].to_numpy(), levers.LeverParams())
    occ["rob_share"] = occ["soc_code"].map(levers.load_robot_exposure())
    occ["soc18"] = occ["soc_code"].str.replace("-", "", regex=False)

    x = pd.read_excel(CW / "soc_2010_to_2018.xlsx", header=3, dtype=str)
    x = x.rename(columns={x.columns[0]: "onet10", x.columns[2]: "soc18"}).dropna(subset=["onet10", "soc18"])
    x["soc10"] = x["onet10"].str.slice(0, 7).str.replace("-", "", regex=False)
    x["soc18"] = x["soc18"].str.replace("-", "", regex=False)
    s18_to_s10 = x.groupby("soc18")["soc10"].apply(lambda s: sorted(set(s)))

    d = pd.read_stata(CW / "soc10_isco08.dta")
    d["soc10"] = d["soc10"].astype(str).str.zfill(6)
    d["isco08"] = d["isco08"].astype(str).str.zfill(4)
    s10_to_isco = d.groupby("soc10")["isco08"].apply(lambda s: sorted(set(s)))

    rows = []
    for r in occ.itertuples():
        kscos = set()
        for s10 in s18_to_s10.get(r.soc18, []):
            for isco in s10_to_isco.get(s10, []):
                k = isco_to_ksco(isco)
                if k is not None:
                    kscos.add(k)
        if not kscos:
            rows.append({"soc18": r.soc18, "ksco": None, "w": r.emp_thousands,
                         "cog": r.cog_share, "rob": r.rob_share})
            continue
        for k in kscos:
            rows.append({"soc18": r.soc18, "ksco": k, "w": r.emp_thousands / len(kscos),
                         "cog": r.cog_share, "rob": r.rob_share})
    m = pd.DataFrame(rows)
    unmapped = m[m["ksco"].isna()]
    mapped = m.dropna(subset=["ksco"])
    g = mapped.groupby("ksco").apply(lambda t: pd.Series({
        "emp_k": t["w"].sum(),
        "cog": np.average(t["cog"], weights=t["w"]),
        "rob": np.average(t["rob"], weights=t["w"])}))
    g.index = g.index.astype(int)
    rob = {int(k): round(float(v), 3) for k, v in g["rob"].items()}
    cog = {int(k): round(float(v), 3) for k, v in g["cog"].items()}
    g["name"] = pd.Series(KSCO_NAMES)
    g.attrs["unmapped_emp_share"] = float(unmapped["w"].sum() / m["w"].sum())
    g.attrs["unmapped_n"] = int(unmapped["soc18"].nunique())
    return rob, cog, g


def main() -> None:
    rob, cog, g = build_map()
    print(g[["name", "emp_k", "cog", "rob"]].round(3).to_string())
    print(f"\nunmapped SOC occupations: {g.attrs['unmapped_n']} "
          f"({100 * g.attrs['unmapped_emp_share']:.1f}% of US employment)")
    print("\nROBOT_SHARE =", rob)
    print("US_COGNITIVE_SHARE =", cog)


if __name__ == "__main__":
    main()
