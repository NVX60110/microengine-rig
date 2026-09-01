#!/usr/bin/env python3
"""Plot mechanism-robust acceptance counts for the Beta 2.6 pilot."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", default="beta26_uncertainty.json")
    parser.add_argument("--output", default="beta26_uncertainty_audit.png")
    args = parser.parse_args()
    rows = json.loads(Path(args.input).read_text())["rows"]
    seals = [
        "sealed_reference", "annular_3um_e05",
        "annular_5um_e05", "ringpack_area_0p006",
    ]
    seal_labels = ["Sealed", "3 µm, e=0.5", "5 µm, e=0.5", "0.006 mm² orifice"]
    mixes = ["slow", "central", "fast"]
    cr_values = [7.75, 8.0]

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.8), constrained_layout=True)
    image = None
    for axis, cr in zip(axes, cr_values):
        grid = np.zeros((len(seals), len(mixes)))
        for i, seal in enumerate(seals):
            for j, mix in enumerate(mixes):
                group = [row for row in rows if (
                    row["compression_ratio"] == cr
                    and row["sealing_case"] == seal
                    and row["mixing_case"] == mix
                )]
                grid[i, j] = sum(bool(row["acceptable"]) for row in group)
        image = axis.imshow(grid, cmap="RdYlGn", vmin=0, vmax=3, aspect="auto")
        axis.set_title(f"CR {cr:g} at 3.0 bar intake")
        axis.set_xticks(range(len(mixes)), ["Slow\n100 ms", "Central\n12–34 ms", "Fast\n2.4–3.2 ms"])
        axis.set_yticks(range(len(seals)), seal_labels)
        axis.set_xlabel("Dynamic mixing bracket")
        for i in range(len(seals)):
            for j in range(len(mixes)):
                count = int(grid[i, j])
                axis.text(j, i, f"{count}/3", ha="center", va="center",
                          fontsize=12, fontweight="bold",
                          color="white" if count in {0, 3} else "black")
    fig.colorbar(image, ax=axes, label="Mechanisms passing conservative screen",
                 ticks=[0, 1, 2, 3], shrink=0.85)
    fig.suptitle("Beta 2.6: operability depends on both sealing and mixing",
                 fontsize=15, fontweight="bold")
    fig.text(
        0.5, -0.02,
        "Acceptable: positive gross IMEP, 10–90% conversion, Tmax <1600 K, "
        "MPRR ≤10 bar/deg, CA50 −15° to +20°. Public car data does not calibrate the seal values.",
        ha="center", fontsize=9,
    )
    fig.savefig(args.output, dpi=200, bbox_inches="tight")


if __name__ == "__main__":
    main()

