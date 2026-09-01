#!/usr/bin/env python3
"""Plot the Beta 2.4 two-zone uncertainty campaign."""
from __future__ import annotations

import csv
import math
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parent


def _read() -> list[dict[str, str]]:
    with (ROOT / "two_zone_campaign.csv").open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def main() -> None:
    rows = _read()
    valid = [row for row in rows if row["status"] == "ok"]
    colors = {"skeletal_39": "#2166ac", "llnl_79": "#d95f02"}
    labels = {"skeletal_39": "Skeletal 39", "llnl_79": "LLNL 79"}
    plt.rcParams.update({"font.size": 8.5, "axes.titlesize": 10})
    fig, axes = plt.subplots(2, 2, figsize=(11.2, 8.2), constrained_layout=True)

    defaults = [
        row for row in valid
        if row["suite"] == "anchor_clearance_eccentricity"
        and _f(row, "annular_radial_clearance_um") == 3.0
        and _f(row, "annular_eccentricity_ratio") == 0.0
    ]
    order = [
        (mechanism, anchor)
        for mechanism in ("skeletal_39", "llnl_79")
        for anchor in ("shared", "lower_overlap", "mechanism_divergent")
    ]
    ordered = [
        next(row for row in defaults
             if row["mechanism_label"] == mechanism and row["anchor"] == anchor)
        for mechanism, anchor in order
    ]
    x = list(range(len(ordered)))
    tick_labels = [
        ("Skel. " if mechanism == "skeletal_39" else "LLNL ")
        + {
            "shared": "\nShared",
            "lower_overlap": "\nLower",
            "mechanism_divergent": "\nDivergent",
        }[anchor]
        for mechanism, anchor in order
    ]

    ax = axes[0, 0]
    ax.bar(
        [value - 0.19 for value in x],
        [100.0 * _f(row, "single_max_fuel_consumed_fraction") for row in ordered],
        width=0.38, color="#999999", label="Single zone",
    )
    ax.bar(
        [value + 0.19 for value in x],
        [100.0 * _f(row, "two_max_fuel_consumed_fraction") for row in ordered],
        width=0.38,
        color=[colors[row["mechanism_label"]] for row in ordered],
        label="Two zone",
    )
    ax.set_xticks(x, tick_labels)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Fuel-consumption proxy [%]")
    ax.set_title("A. Default two-zone model suppresses total conversion")
    ax.grid(axis="y", alpha=0.22)
    ax.legend()

    ax = axes[0, 1]
    ax.bar(
        [value - 0.19 for value in x],
        [_f(row, "single_max_pressure_rise_bar_per_deg") for row in ordered],
        width=0.38, color="#999999", label="Single zone",
    )
    ax.bar(
        [value + 0.19 for value in x],
        [_f(row, "two_max_pressure_rise_bar_per_deg") for row in ordered],
        width=0.38,
        color=[colors[row["mechanism_label"]] for row in ordered],
        label="Two zone",
    )
    ax.axhline(10.0, color="#b2182b", linestyle="--", linewidth=1.0,
               label="Provisional screen")
    ax.set_xticks(x, tick_labels)
    ax.set_ylabel("Maximum pressure rise [bar/deg]")
    ax.set_title("B. Spatial split removes the modeled pressure-rise cliff")
    ax.grid(axis="y", alpha=0.22)
    ax.legend()

    ax = axes[1, 0]
    styles = {0.10: ":", 0.20: "-", 0.30: "--"}
    for mechanism in ("skeletal_39", "llnl_79"):
        for fraction in (0.10, 0.20, 0.30):
            subset = sorted([
                row for row in rows
                if row["suite"] == "zone_mixing_sensitivity"
                and row["mechanism_label"] == mechanism
                and math.isclose(_f(row, "boundary_mass_fraction"), fraction)
            ], key=lambda row: _f(row, "mixing_time_ms"))
            ax.plot(
                [_f(row, "mixing_time_ms") for row in subset],
                [
                    100.0 * _f(row, "two_max_fuel_consumed_fraction")
                    if row["status"] == "ok" else float("nan")
                    for row in subset
                ],
                color=colors[mechanism], linestyle=styles[fraction], marker="o",
                label=f"{labels[mechanism]}, boundary {fraction:.0%}",
            )
    ax.set(xlabel="Inter-zone mixing time [ms]",
           ylabel="Fuel-consumption proxy [%]",
           title="C. Mixing and boundary-zone mass control the outcome")
    ax.set_ylim(0, 105)
    ax.grid(alpha=0.22)
    ax.legend(ncol=2, fontsize=7.2)

    ax = axes[1, 1]
    for mechanism in ("skeletal_39", "llnl_79"):
        for eccentricity, marker, linestyle in ((0.0, "o", "-"), (0.5, "s", "--")):
            subset = sorted([
                row for row in valid
                if row["suite"] == "anchor_clearance_eccentricity"
                and row["mechanism_label"] == mechanism
                and row["anchor"] == "shared"
                and math.isclose(_f(row, "annular_eccentricity_ratio"), eccentricity)
            ], key=lambda row: _f(row, "annular_radial_clearance_um"))
            ax.plot(
                [_f(row, "annular_radial_clearance_um") for row in subset],
                [_f(row, "two_gross_imep_bar") for row in subset],
                color=colors[mechanism], marker=marker, linestyle=linestyle,
                label=f"{labels[mechanism]}, e={eccentricity:.1f}",
            )
    ax.axhline(0.0, color="#555555", linewidth=0.9)
    ax.set(xlabel="Annular radial clearance [µm]", ylabel="Gross IMEP [bar]",
           title="D. Two-zone output remains sealing-sensitive")
    ax.grid(alpha=0.22)
    ax.legend(fontsize=7.5)

    fig.suptitle(
        "MicroEngine Beta 2.4 — experimental two-zone bracket",
        fontsize=14, fontweight="bold",
    )
    output = ROOT / "beta24_two_zone_audit.png"
    fig.savefig(output, dpi=190)
    plt.close(fig)
    print(output)


if __name__ == "__main__":
    main()
