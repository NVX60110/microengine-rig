#!/usr/bin/env python3
"""Bounded one-cycle quadrature check for 1200-rpm accounting residuals."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cycle720 import simulate_cycle720
from scripts.run_cycle720_1200_accounting import canonical_config, valve_options


def main() -> None:
    records = []
    started = time.perf_counter()
    # Four levels are sufficient to test the observed trapezoidal-rate
    # residual without launching a campaign.  Each row starts from fresh charge
    # and therefore isolates one-cycle quadrature/state accounting.
    for step_deg in (5.0, 2.0, 1.0, 0.5):
        t0 = time.perf_counter()
        result = simulate_cycle720(canonical_config(step_deg), valve_options(step_deg, 1))
        accounting = result["summary"]["cycle_accounting"]
        records.append({
            "step_deg": step_deg,
            "runtime_s": time.perf_counter() - t0,
            "mass_balance_residual_mg": accounting["mass_balance_residual_mg"],
            "mass_balance_residual_rel_cycle_start": accounting["mass_balance_residual_rel_cycle_start"],
            "mass_balance_residual_rel_closed_kernel": accounting["mass_balance_residual_rel_closed_kernel"],
            "closed_kernel_mass_balance_residual_mg": accounting["closed_kernel_mass_balance_residual_mg"],
            "energy_balance_residual_J": accounting["energy_balance_residual_J"],
            "closed_energy_balance_residual_J": accounting["closed_energy_balance_residual_J"],
            "intake_energy_balance_residual_J": accounting["intake_energy_balance_residual_J"],
            "exhaust_energy_balance_residual_J": accounting["exhaust_energy_balance_residual_J"],
        })
    artifact = {
        "experiment": "cycle720-1200-accounting-quadrature-refinement",
        "status": "diagnostic_only",
        "records": records,
        "runtime_s": time.perf_counter() - started,
        "provenance": {
            "measured": False, "literature_derived": False,
            "project_model_assumptions": True,
            "note": "Fresh one-cycle valve-enabled runs; no friction, crank dynamics, motor, CFD or chemistry retuning.",
        },
    }
    output = ROOT / "results" / "cycle720_1200_accounting_refinement.json"
    output.write_text(json.dumps(artifact, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "runtime_s": artifact["runtime_s"]}, sort_keys=True))


if __name__ == "__main__":
    main()
