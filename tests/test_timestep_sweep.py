"""Tests for the CFD-01 timestep/Courant sweep runner options (no OpenFOAM required)."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cfd" / "openfoam14" / "cold_flow_tracer" / "scripts"))

import run_timestep_sweep as sweep  # noqa: E402

FINE_TIGHT = ROOT / "cfd" / "results" / "cfd01_scalar_history_fine_tight.csv"
CONTROL_DICT = ROOT / "cfd" / "openfoam14" / "cold_flow_tracer" / "system" / "controlDict"


class TimestepSweepOptionTests(unittest.TestCase):
    def test_case_tag_includes_courant_only_when_changed(self) -> None:
        self.assertEqual(sweep.case_tag(0.25), "dt_0p250")
        self.assertEqual(sweep.case_tag(0.25, 0.15), "dt_0p250")
        self.assertEqual(sweep.case_tag(0.25, 0.45), "dt_0p250_co_0p45")

    def test_configure_control_dict_patches_courant_cap_and_all_write_intervals(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = sweep.prepare("coarse", Path(tmp), False)
            interval = sweep.configure_control_dict(case, 0.25, 0.45)
            text = (case / "system" / "controlDict").read_text()
        self.assertEqual(interval, 2)
        self.assertRegex(text, r"(?m)^maxCo\s+0\.45;")
        self.assertRegex(text, r"(?m)^maxDeltaT\s+0\.25;")
        intervals = set(re.findall(r"(?m)^\s*(?:write|execute)Interval\s+(\d+);", text))
        self.assertEqual(intervals, {"2"})
        # The tracer function object must carry its own write control so the
        # field is not written every step (Issue #10 follow-up).
        tracer_block = re.search(r"tracerTransport\s*\{(.*?)\n\s*\}", text, flags=re.S).group(1)
        self.assertIn("writeControl timeStep;", tracer_block)

    def test_configure_control_dict_rejects_courant_above_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = sweep.prepare("coarse", Path(tmp), False)
            with self.assertRaises(ValueError):
                sweep.configure_control_dict(case, 0.25, 0.6)

    def test_reference_row_from_converged_fine_history(self) -> None:
        row = sweep.reference_row(FINE_TIGHT)
        self.assertEqual(row["status"], "ok")
        self.assertLessEqual(
            float(row["max_tracer_inventory_error_percent"]),
            100.0 * sweep.MAX_TRACER_INVENTORY_DRIFT_REL,
        )
        for target in sweep.TARGETS:
            key = sweep.suffix(target)
            self.assertIn(f"tau_mix_ms_{key}", row)
            self.assertIn(f"delta_c_{key}", row)
        self.assertAlmostEqual(float(row["tau_mix_ms_p0"]), 10.665, delta=0.01)

    def test_answer_gate_uses_external_reference(self) -> None:
        reference = sweep.reference_row(FINE_TIGHT)
        candidate = {
            "status": "ok",
            "max_delta_t_cad": 0.25,
            "max_co_target": 0.45,
        }
        for target in sweep.TARGETS:
            key = sweep.suffix(target)
            candidate[f"delta_c_{key}"] = float(reference[f"delta_c_{key}"]) * 1.02
            candidate[f"tau_mix_ms_{key}"] = float(reference[f"tau_mix_ms_{key}"]) * 0.97
        rows = [candidate]
        sweep.apply_answer_gate(rows, reference)
        self.assertEqual(rows[0]["answer_gate"], "pass")
        self.assertAlmostEqual(float(rows[0]["max_answer_rel_error"]), 0.03, places=6)
        candidate["tau_mix_ms_p0"] = float(reference["tau_mix_ms_p0"]) * 1.08
        sweep.apply_answer_gate(rows, reference)
        self.assertEqual(rows[0]["answer_gate"], "fail")


if __name__ == "__main__":
    unittest.main()
