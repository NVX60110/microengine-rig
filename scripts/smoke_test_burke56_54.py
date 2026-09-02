#!/usr/bin/env python3
"""Smoke-test the converted Burke Mech_56.54 phase and write JSON metadata."""
from __future__ import annotations

import json
from pathlib import Path

import cantera as ct


ROOT = Path(__file__).resolve().parents[1]
MECHANISM = ROOT / "mechanisms" / "burke_mech_56_54.yaml"
OUTPUT = ROOT / "data" / "burke2015" / "mech_56_54" / "smoke_test.json"
REQUIRED = ("ch4", "ch3och3", "o2", "n2", "co2", "oh", "ho2", "h2o2")


def main() -> None:
    gas = ct.Solution(str(MECHANISM))
    gas.TPX = 1000.0, 20.0 * ct.one_atm, {
        "ch4": 0.08,
        "ch3och3": 0.02,
        "o2": 0.21,
        "n2": 0.79,
    }
    reactor = ct.IdealGasConstPressureReactor(gas, clone=False)
    network = ct.ReactorNet([reactor])
    network.advance(1.0e-5)
    result = {
        "cantera_version": ct.__version__,
        "mechanism": "mechanisms/burke_mech_56_54.yaml",
        "species_count": gas.n_species,
        "reaction_count": gas.n_reactions,
        "transport_model": gas.transport_model,
        "required_species": {name: name in gas.species_names for name in REQUIRED},
        "smoke_state": {
            "temperature_K": gas.T,
            "pressure_bar": gas.P / 1.0e5,
            "density_kg_m3": gas.density,
            "viscosity_Pa_s": gas.viscosity,
            "advanced_to_s": network.time,
        },
    }
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
