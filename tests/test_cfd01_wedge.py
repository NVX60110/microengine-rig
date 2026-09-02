"""Tests for the CFD-01 wedge-axis case generator and initial time-step control (no OpenFOAM required)."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cfd" / "openfoam14" / "cold_flow_tracer" / "scripts"))

import run_cfd01 as cfd01  # noqa: E402
import run_timestep_sweep as sweep  # noqa: E402


class WedgeAxisGeneratorTests(unittest.TestCase):
    def test_wedge_block_collapses_axis_and_uses_wedge_patches(self) -> None:
        text = cfd01.block_mesh_dict_wedge(22, 41)
        self.assertIn("hex (3 4 5 3 0 1 2 0) (22 1 41)", text)
        self.assertNotIn("axisCore", text)
        self.assertEqual(text.count("type wedge;"), 2)
        self.assertIn("faces ((3 4 5 3));", text)  # piston triangle
        self.assertIn("faces ((0 0 2 1));", text)  # head triangle
        vertices = re.findall(r"^\s+\(([-0-9.e]+) ([-0-9.e]+) ([-0-9.e]+)\)$", text, flags=re.M)
        self.assertEqual(len(vertices), 6)
        axis = [v for v in vertices if float(v[0]) == 0.0 and float(v[1]) == 0.0]
        self.assertEqual(len(axis), 2)

    def test_sector_generator_unchanged(self) -> None:
        text = cfd01.block_mesh_dict(22, 3, 41)
        self.assertIn("axisCore", text)
        self.assertIn("type symmetryPlane;", text)
        self.assertIn("(22 3 41)", text)

    def test_prepare_selects_generator_and_tracer_boundaries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = cfd01.prepare("coarse", Path(tmp), False, axis="wedge")
            self.assertIn("type wedge;", (case / "system" / "blockMeshDict").read_text())
        self.assertIn("symmetryMinus { type wedge; }", cfd01.tracer_boundary_field("wedge"))
        self.assertNotIn("axisCore", cfd01.tracer_boundary_field("wedge"))
        self.assertIn("axisCore { type symmetry; }", cfd01.tracer_boundary_field("sector"))
        with self.assertRaises(ValueError):
            cfd01.prepare("coarse", Path(tempfile.gettempdir()) / "never", False, axis="cone")

    def test_initial_delta_t_patch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = cfd01.prepare("coarse", Path(tmp), False)
            cfd01.set_initial_delta_t(case, 0.01)
            text = (case / "system" / "controlDict").read_text()
            self.assertRegex(text, r"(?m)^deltaT\s+0\.01;")
            with self.assertRaises(ValueError):
                cfd01.set_initial_delta_t(case, 0.0)

    def test_sweep_tags_carry_axis_and_initial_step(self) -> None:
        self.assertEqual(sweep.case_tag(0.15), "dt_0p150")
        self.assertEqual(sweep.case_tag(0.15, 0.15, "wedge", 0.01), "dt_0p150_wedge_dt0_0p010")
        self.assertEqual(sweep.case_tag(0.25, 0.45, "wedge"), "dt_0p250_co_0p45_wedge")


if __name__ == "__main__":
    unittest.main()
