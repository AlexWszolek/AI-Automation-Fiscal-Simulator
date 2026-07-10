"""The fiscal summary table — the presentation layer over the C6 reconciliation.

Builds the ai-shock-style summary (revenue by category × year, baseline-anchored, keystone net row) from
a `DynamicModelV2.run()` result. Two groupings:
  - "tax":     federal revenue changes / federal outlays / net / absolute levels / state & local;
  - "channel": the Windfall Trust four-channel decomposition (labour→capital, resident→non-resident,
               taxable→consumer surplus, government spending) — the same columns, re-grouped.

SIGN CONVENTION (differs from the model's loss-positive internals): revenue lines are signed revenue
CHANGES (negative = lost revenue), outlay lines are signed spending changes (positive = more spending),
and the keystone row **"Net fiscal impact" = −fed_deficit_B (negative = worse)** — the reading used by
Windfall Trust / RAND. The familiar deficit level lives in the "Levels" group.

The builder ASSERTS its own reconciliation (repo discipline): the tax-view net must equal −fed_deficit_B
bit-for-bit up to float summation, and the channel view must reconcile to the combined federal+state net.
Rows are tagged `kind` ∈ {flow, subtotal, net, level, memo}: flows sum into the "Total" column; levels
report their final-year value there; memo rows document untaxed magnitudes and are excluded from nets.
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from .government import RevenueLedger

# (group, label, column expression, scope, kind)
# scope: which baseline the pct_baseline units divide by — fed | state | combined | passthrough (%-GDP)


def _tax_rows(res: pd.DataFrame) -> list:
    r = res
    rev = [
        ("Federal revenue changes", "Income tax", -r["inc_fed_loss_B"], "fed", "flow"),
        ("Federal revenue changes", "Payroll (FICA)", -r["payroll_fed_loss_B"], "fed", "flow"),
        ("Federal revenue changes", "Corporate recovery", r["corp_offset_B"], "fed", "flow"),
        ("Federal revenue changes", "Compute-pool tax", r["compute_pool_tax_B"], "fed", "flow"),
        ("Federal revenue changes", "Survivor wage taxes", r["survivor_gain_fed_B"], "fed", "flow"),
        ("Federal revenue changes", "Overflow corporate tax", r["survivor_overflow_corp_tax_B"], "fed", "flow"),
        ("Federal revenue changes", "Automation (robot) tax", r["automation_tax_B"], "fed", "flow"),
        ("Federal revenue changes", "UBI recapture", r["ubi_recapture_B"], "fed", "flow"),
        ("Federal revenue changes", "Tax on UI benefits", r["ui_tax_fed_B"], "fed", "flow"),
        # baseline tax-regime surcharges (the income/capital/consumption × dials; 0 at current law)
        ("Federal revenue changes", "Income tax surcharge", r["income_surcharge_fed_B"], "fed", "flow"),
        ("Federal revenue changes", "Capital tax surcharge", r["corp_surcharge_fed_B"], "fed", "flow"),
        ("Federal revenue changes", "Excise surcharge", r["excise_surcharge_fed_B"], "fed", "flow"),
    ]
    rev_total = sum(row[2] for row in rev)
    out = [
        ("Federal outlay changes", "Means-tested transfers", r["transfer_fed_B"], "fed", "flow"),
        ("Federal outlay changes", "Unemployment insurance", r["ui_outlay_fed_B"], "fed", "flow"),
        ("Federal outlay changes", "SSDI", r["ssdi_outlay_B"], "fed", "flow"),
        ("Federal outlay changes", "UBI (gross)", r["ubi_outlay_B"], "fed", "flow"),
    ]
    out_total = sum(row[2] for row in out)
    net_fed = rev_total - out_total
    # the C6 identity as a runtime guarantee: the table's net IS the deficit, sign-flipped
    assert np.allclose(net_fed.to_numpy(), -r["fed_deficit_B"].to_numpy(), rtol=1e-9, atol=1e-6), \
        "fiscal summary does not reconcile to fed_deficit_B — a C6 component is missing from the table"

    state_rev = [
        ("State & local", "State income tax", -r["inc_state_loss_B"], "state", "flow"),
        ("State & local", "State consumption tax", -r["cons_state_loss_B"], "state", "flow"),
        ("State & local", "Survivor wage taxes (state)", r["survivor_gain_state_B"], "state", "flow"),
        ("State & local", "State income surcharge", r["income_surcharge_state_B"], "state", "flow"),
        ("State & local", "State corporate surcharge", r["corp_surcharge_state_B"], "state", "flow"),
        ("State & local", "State consumption surcharge", r["cons_surcharge_state_B"], "state", "flow"),
    ]
    state_out = ("State & local", "State transfers (outlay)", r["transfer_state_B"], "state", "flow")
    net_state = -r["state_net_total_B"]

    rows = rev + [("Federal revenue changes", "Δ Federal revenue", rev_total, "fed", "subtotal")]
    rows += out + [("Federal outlay changes", "Δ Federal outlays", out_total, "fed", "subtotal")]
    rows += [("Net", "Net fiscal impact (federal)", net_fed, "fed", "net")]
    rows += [
        ("Levels", "Federal revenue (absolute)", r["fed_revenue_B"], "fed", "level"),
        ("Levels", "Federal deficit (absolute)", r["fed_deficit_abs_B"], "fed", "level"),
        ("Levels", "Federal debt (Δ cumulative)", r["fed_debt_B"], "fed", "level"),
        ("Levels", "Deficit (% of GDP)", r["fed_deficit_abs_pct_gdp"], "passthrough", "level"),
    ]
    rows += state_rev + [state_out]
    rows += [
        ("State & local", "Net fiscal impact (state)", net_state, "state", "net"),
        ("State & local", "Gap states must close", r["state_gap_B"], "state", "memo"),
        ("State & local", "…closed via rate hikes", r["state_rate_hike_B"], "state", "memo"),
        ("State & local", "…closed via spending cuts", r["state_spending_cut_B"], "state", "memo"),
    ]
    return rows


def _channel_rows(res: pd.DataFrame) -> list:
    r = res
    labour_lost = -(r["inc_fed_loss_B"] + r["payroll_fed_loss_B"] + r["inc_state_loss_B"])
    labour_back = r["survivor_gain_fed_B"] + r["survivor_gain_state_B"]
    capital_back = (r["corp_offset_B"] + r["compute_pool_tax_B"]
                    + r["survivor_overflow_corp_tax_B"] + r["automation_tax_B"])
    surcharges = (r["income_surcharge_fed_B"] + r["income_surcharge_state_B"]
                  + r["corp_surcharge_fed_B"] + r["corp_surcharge_state_B"]
                  + r["excise_surcharge_fed_B"] + r["cons_surcharge_state_B"])
    ch1 = labour_lost + labour_back + capital_back
    ch3_taxed = -r["cons_state_loss_B"]
    spending = (r["transfer_fed_B"] + r["transfer_state_B"] + r["ssdi_outlay_B"]
                + (r["ui_outlay_fed_B"] - r["ui_tax_fed_B"])
                + (r["ubi_outlay_B"] - r["ubi_recapture_B"]))
    ch4 = -spending
    combined = ch1 + ch3_taxed + ch4 + surcharges
    # channel partition must reconcile to the combined federal + state net
    target = -(r["fed_deficit_B"] + r["state_net_total_B"])
    assert np.allclose(combined.to_numpy(), target.to_numpy(), rtol=1e-9, atol=1e-6), \
        "channel view does not reconcile to the combined federal+state net"

    return [
        ("⓪ Tax-regime surcharges", "Baseline surcharges (income+capital+consumption dials)",
         surcharges, "combined", "flow"),
        ("① Labour → capital", "Labour taxes lost (displaced)", labour_lost, "combined", "flow"),
        ("① Labour → capital", "Labour taxes gained (survivors)", labour_back, "combined", "flow"),
        ("① Labour → capital", "Capital-side recoveries", capital_back, "combined", "flow"),
        ("① Labour → capital", "Channel 1 net", ch1, "combined", "subtotal"),
        ("② Resident → non-resident", "Offshore leakage (untaxed, memo)", r["offshore_leak_B"],
         "combined", "memo"),
        ("③ Taxable → consumer surplus", "Consumer price gains (untaxed, memo)",
         r["price_reduction_B"] + r["survivor_overflow_price_B"], "combined", "memo"),
        ("③ Taxable → consumer surplus", "Consumption tax change", ch3_taxed, "combined", "flow"),
        ("④ Government spending", "Net new spending (transfers+UI+SSDI+UBI)", spending,
         "combined", "flow"),
        ("Net", "Net fiscal impact (federal + state)", combined, "combined", "net"),
    ]


def build_fiscal_summary(res: pd.DataFrame, ledger: RevenueLedger,
                         grouping: str = "tax", units: str = "busd") -> pd.DataFrame:
    """The summary table: columns [group, label, kind, Year 0..N, Total]. See the module docstring for
    the sign convention. `units="pct_baseline"` re-expresses flows/levels as % of the real 2024 baseline
    revenue (federal rows / fed_revenue0, state / state_revenue0, combined / their sum); %-GDP rows pass
    through untouched."""
    assert grouping in ("tax", "channel") and units in ("busd", "pct_baseline")
    rows = _tax_rows(res) if grouping == "tax" else _channel_rows(res)
    denom = {"fed": ledger.fed_revenue0, "state": ledger.state_revenue0,
             "combined": ledger.fed_revenue0 + ledger.state_revenue0, "passthrough": None}
    years = [f"Year {int(t)}" for t in res["period"]]
    out = []
    for group, label, series, scope, kind in rows:
        vals = np.asarray(series, float)
        if units == "pct_baseline" and denom[scope] is not None:
            vals = vals / denom[scope] * 100.0
        total = float(vals.sum()) if kind in ("flow", "subtotal", "net", "memo") else float(vals[-1])
        out.append({"group": group, "label": label, "kind": kind,
                    **dict(zip(years, vals)), "Total": total})
    return pd.DataFrame(out)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8")
