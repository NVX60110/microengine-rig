"""Bounded friction/motoring screen for a complete four-stroke cycle.

This is an input adapter for the future 720-CAD model, not a piston-ring or
tribology solver.  The bracket is expressed as friction mean effective
pressure (FMEP), which is convenient because it scales the displacement work
without pretending that a crank-angle torque trace is known.

Conventions
-----------
``fmep_bar`` is positive loss pressure.  One complete four-stroke cycle spans
``4*pi`` crank radians, so the constant-equivalent torque is::

    W_friction = FMEP * displacement
    tau_equiv  = W_friction / (4*pi)

This constant torque is only a motoring-work equivalent.  Actual friction has
speed, temperature, load, lubrication and crank-angle dependence and must be
replaced by motoring measurements when hardware exists.
"""
from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class FrictionBracket:
    """One explicitly labeled FMEP screening assumption."""

    name: str
    fmep_bar: float
    source: str
    status: str = "project_assumption"
    note: str = "Not a measured miniature-engine friction value."

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("friction bracket name must not be blank")
        if self.fmep_bar < 0.0:
            raise ValueError("fmep_bar must be non-negative")
        if not self.source.strip():
            raise ValueError("friction bracket source must not be blank")


# Deliberately broad screen around the historical, now-retracted exact FMEP
# claim.  These are project assumptions until a motoring test supplies data.
DEFAULT_FRICTION_BRACKETS = (
    FrictionBracket(
        "low", 0.05,
        "Project sensitivity assumption; informed by low mean piston speed, not calibration.",
    ),
    FrictionBracket(
        "central", 0.15,
        "Project sensitivity assumption; midpoint screen, not calibration.",
    ),
    FrictionBracket(
        "high", 0.30,
        "Project sensitivity assumption; conservative screening upper bracket, not calibration.",
    ),
)


def friction_work_J(fmep_bar: float, displacement_m3: float) -> float:
    """Return friction work lost per complete four-stroke cycle [J]."""
    if fmep_bar < 0.0:
        raise ValueError("fmep_bar must be non-negative")
    if displacement_m3 <= 0.0:
        raise ValueError("displacement_m3 must be positive")
    return fmep_bar * 1.0e5 * displacement_m3


def equivalent_friction_torque_Nm(fmep_bar: float, displacement_m3: float) -> float:
    """Return constant torque with the same 720-CAD work loss [N m]."""
    return friction_work_J(fmep_bar, displacement_m3) / (4.0 * math.pi)


def friction_metrics(
    fmep_bar: float,
    displacement_m3: float,
    rpm: float,
) -> dict[str, float]:
    """Return work, equivalent torque, and average friction power.

    ``rpm`` affects power only; FMEP itself is an imposed bracket input.  The
    reported power is shaft work lost per four-stroke cycle times cycles/s,
    namely ``rpm / 120`` for a four-stroke engine.
    """
    if rpm < 0.0:
        raise ValueError("rpm must be non-negative")
    work = friction_work_J(fmep_bar, displacement_m3)
    torque = work / (4.0 * math.pi)
    cycles_per_s = rpm / 120.0
    return {
        "fmep_bar": fmep_bar,
        "displacement_m3": displacement_m3,
        "rpm": rpm,
        "friction_work_J_per_4stroke": work,
        "equivalent_friction_torque_Nm": torque,
        "friction_power_W": work * cycles_per_s,
        "four_stroke_period_s": 120.0 / rpm if rpm > 0.0 else math.inf,
    }


def bracket_metrics(
    displacement_m3: float,
    rpm: float,
    brackets: tuple[FrictionBracket, ...] = DEFAULT_FRICTION_BRACKETS,
) -> list[dict[str, float | str]]:
    """Evaluate a supplied bracket without changing its provenance."""
    return [
        {
            "name": bracket.name,
            "source": bracket.source,
            "status": bracket.status,
            **friction_metrics(bracket.fmep_bar, displacement_m3, rpm),
        }
        for bracket in brackets
    ]

