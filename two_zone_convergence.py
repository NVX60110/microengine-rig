#!/usr/bin/env python3
"""Crank-step convergence for the Beta 2.4 shared two-zone anchor."""
from __future__ import annotations

import argparse

from microengine_rig import write_csv
from two_zone_campaign import _case


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=int, default=4)
    args = parser.parse_args()
    cases = [
        (
            "step_convergence", mechanism, "shared", 3.0, 0.0,
            0.20, 10.0, 5.0e-5, step,
        )
        for mechanism in ("skeletal_39", "llnl_79")
        for step in (0.25, 0.125, 0.0625, 0.03125)
    ]
    if args.jobs == 1:
        rows = [_case(*case) for case in cases]
    else:
        from joblib import Parallel, delayed
        rows = Parallel(n_jobs=args.jobs, backend="loky")(
            delayed(_case)(*case) for case in cases
        )
    write_csv("two_zone_convergence.csv", rows)
    for row in rows:
        print(
            row["mechanism_label"], row["step_deg"], row["status"],
            row.get("two_gross_imep_bar"),
            row.get("two_max_fuel_consumed_fraction"),
            row.get("two_max_pressure_rise_bar_per_deg"),
        )


if __name__ == "__main__":
    main()
