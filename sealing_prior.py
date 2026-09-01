#!/usr/bin/env python3
"""Evidence ledger and bounded sealing cases for MicroEngine Beta 2.6.

Public automotive data constrains model structure and broad degradation trends,
but it does not identify an absolute 8.5 mm micro-engine leakage area. The cases
below therefore remain explicit engineering brackets, not a fitted probability
distribution. Hardware data can later replace their weights and ranges without
changing the campaign interface.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any


@dataclass(frozen=True)
class LiteratureAnchor:
    anchor_id: str
    observation: str
    conditions: str
    transfer_use: str
    transfer_limit: str
    source: str


@dataclass(frozen=True)
class SealingCase:
    name: str
    model_class: str
    config_patch: dict[str, Any]
    status: str
    rationale: str


ANCHORS = (
    LiteratureAnchor(
        "koszalka_2004",
        "A ring pack behaves as an unsteady multi-volume labyrinth; ring-side "
        "passages can exceed end-gap area by more than one order of magnitude.",
        "Conventional piston-ring-cylinder geometry; compressible critical and "
        "subcritical flow with heat transfer and ring motion.",
        "Supports an orifice-volume ring-pack alternative and rejects end-gap-only certainty.",
        "Does not report a transferable 8.5 mm effective area.",
        "https://journals.pan.pl/Content/124998/PDF/7_MECHANICAL_51_2004_2_Koszalka_Modelling.pdf",
    ),
    LiteratureAnchor(
        "koszalka_2022",
        "A coupled ring-flow/ring-motion/oil model matched measured blow-by "
        "within 15%; predicted 56-60% blow-by growth from unworn to a "
        "300,000 km wear extrapolation.",
        "84 x 90 mm, CR 12, three-ring gasoline engine, 2000 rpm, 20-168 Nm.",
        "Supports a broad degraded-seal multiplier and multi-stage model structure.",
        "Bore, ring architecture, speed, oil state and residence time are far from the target.",
        "https://doi.org/10.3390/en15249570",
    ),
    LiteratureAnchor(
        "aghdam_2010",
        "Motored experiments varied compression ratio and speed to validate a blow-by model.",
        "Conventional ringed engine under motoring conditions.",
        "Supports validating leakage without combustion and retaining speed/CR dependence.",
        "Public abstract is insufficient to infer the target's absolute flow area.",
        "https://doi.org/10.1016/j.expthermflusci.2009.10.002",
    ),
    LiteratureAnchor(
        "dieselnet_rules",
        "Published full-size rules of thumb vary by roughly 2-3x and are explicitly cautioned.",
        "Rated-power-scaled crankcase flow for conventional engines.",
        "Supports using a wide prior rather than a single borrowed car value.",
        "Power scaling does not preserve bore, rpm, ring path or pressure history.",
        "https://dieselnet.com/tech/engine_crank.php",
    ),
)


def sealing_cases() -> tuple[SealingCase, ...]:
    """Return traceable bracketing cases; no case is called 'measured'."""
    return (
        SealingCase(
            "sealed_reference", "none", {"blowby_mode": "off"},
            "upper-bound reference", "Separates chemical/thermal loss from leakage.",
        ),
        SealingCase(
            "annular_3um_concentric", "ringless-annulus",
            {"blowby_mode": "annular", "annular_radial_clearance_um": 3.0,
             "annular_eccentricity_ratio": 0.0, "annular_skirt_length_mm": 8.0},
            "optimistic engineering bracket", "Lapped-fit hypothesis without piston rock.",
        ),
        SealingCase(
            "annular_3um_e05", "ringless-annulus",
            {"blowby_mode": "annular", "annular_radial_clearance_um": 3.0,
             "annular_eccentricity_ratio": 0.5, "annular_skirt_length_mm": 8.0},
            "central ringless bracket", "Adds the analytic eccentricity multiplier.",
        ),
        SealingCase(
            "annular_5um_e05", "ringless-annulus",
            {"blowby_mode": "annular", "annular_radial_clearance_um": 5.0,
             "annular_eccentricity_ratio": 0.5, "annular_skirt_length_mm": 8.0},
            "degraded ringless bracket", "Tests cubic clearance sensitivity plus piston rock.",
        ),
        SealingCase(
            "ringpack_area_0p002", "ring-pack-orifice",
            {"blowby_mode": "orifice", "blowby_effective_area_mm2": 0.002,
             "blowby_discharge_coefficient": 0.70, "ring_count": 2},
            "optimistic uncalibrated bracket", "Low ring-pack throat-area hypothesis.",
        ),
        SealingCase(
            "ringpack_area_0p006", "ring-pack-orifice",
            {"blowby_mode": "orifice", "blowby_effective_area_mm2": 0.006,
             "blowby_discharge_coefficient": 0.70, "ring_count": 2},
            "central uncalibrated bracket", "Intermediate ring-pack throat area.",
        ),
        SealingCase(
            "ringpack_area_0p015", "ring-pack-orifice",
            {"blowby_mode": "orifice", "blowby_effective_area_mm2": 0.015,
             "blowby_discharge_coefficient": 0.70, "ring_count": 2},
            "pessimistic uncalibrated bracket", "Covers side-path dominance and poor seating.",
        ),
    )


def evidence_payload() -> dict[str, Any]:
    return {
        "interpretation": (
            "Public data defines model alternatives and broad multipliers only. "
            "It does not turn any micro-engine leakage case into a measured prior."
        ),
        "anchors": [asdict(item) for item in ANCHORS],
        "cases": [asdict(item) for item in sealing_cases()],
    }


if __name__ == "__main__":
    print(json.dumps(evidence_payload(), indent=2))

