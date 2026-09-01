#!/usr/bin/env python3
"""Plot the fine Beta 2.5 two-zone CR transition for both boost levels."""
from __future__ import annotations

import csv

import matplotlib.pyplot as plt


FILES = {
    2.3: "two_zone_transition_2p3.csv",
    3.0: "two_zone_transition_3p0.csv",
}
LABELS = {
    "zhao_sk39": "Zhao sk39",
    "zhao_full55": "Zhao full55",
    "llnl79": "LLNL 79",
}


def load(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(11.5, 7.5), sharex="col")
    for column, (pressure, path) in enumerate(FILES.items()):
        rows = load(path)
        for profile, label in LABELS.items():
            selected = sorted(
                (row for row in rows if row["profile"] == profile),
                key=lambda row: float(row["compression_ratio"]),
            )
            cr = [float(row["compression_ratio"]) for row in selected]
            temperature = [float(row["peak_core_temperature_K"]) for row in selected]
            rise = [float(row["max_pressure_rise_bar_per_deg"]) for row in selected]
            axes[0, column].plot(cr, temperature, marker="o", linewidth=2, label=label)
            axes[1, column].plot(cr, rise, marker="o", linewidth=2, label=label)
        axes[0, column].axhspan(1300, 2200, color="#f7c9c9", alpha=0.35)
        axes[0, column].axhline(1000, color="#777777", linestyle="--", linewidth=1)
        axes[0, column].set_title(f"Intake pressure {pressure:.1f} bar")
        axes[0, column].set_ylim(750, 2150)
        axes[0, column].grid(alpha=0.22)
        axes[1, column].axhline(10, color="#9c2f2f", linestyle="--", linewidth=1)
        axes[1, column].set_ylim(0, 90)
        axes[1, column].grid(alpha=0.22)
        axes[1, column].set_xlabel("Geometric compression ratio")
    axes[0, 0].set_ylabel("Peak core temperature [K]")
    axes[1, 0].set_ylabel("Maximum pressure rise [bar/deg]")
    axes[0, 1].legend(frameon=False, loc="upper left")
    fig.suptitle("Beta 2.5: two-zone branch transition is narrow and mechanism-dependent",
                 fontsize=14, fontweight="bold")
    fig.text(
        0.5, 0.015,
        "8.5 x 7.0 mm, 1200 rpm, phi 0.40, 25/75 DME/CH4, 560 K wall, "
        "3 um annulus, 20% boundary mass, 10 ms mixing, 0.125 deg step",
        ha="center", fontsize=9,
    )
    fig.tight_layout(rect=(0, 0.04, 1, 0.95))
    fig.savefig("beta25_transition_audit.png", dpi=180)


if __name__ == "__main__":
    main()
