"""AI Automation Fiscal Model.

An interactive, user-driven model of the fiscal effects of AI/automation on the
U.S. economy (federal and state-and-local). Every assumption is a user-set lever;
credibility comes from the accounting being correct, not from chosen inputs.

Modules (build order):
    loaders.py   -- load the 8 data files, normalize units, assert control totals
    rates.py     -- tax schedules from tax_side_schedule.xlsx (fed/state income, payroll)
    kernel.py    -- fiscal_delta(): net fiscal delta of displacing one worker
    levers.py    -- exposure -> feasibility -> adoption -> displacement flows
    dynamics.py  -- stock-flow loop (cohorts, UI exhaustion, deficit, state balance)
    validate.py  -- reconciliation vs control totals, quintile incidence, PolicyEngine
"""

__version__ = "0.0.1"
