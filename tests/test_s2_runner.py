"""Tests for the CFD-02 S2 runner's scalar-solver handling and the inventory audit parser."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cfd" / "openfoam14" / "squish"))
sys.path.insert(0, str(ROOT / "cfd"))

import run_s2_cfd  # noqa: E402
import run_squish_cfd  # noqa: E402
import audit_scalar_inventory  # noqa: E402

BASE_FVSOLUTION = ROOT / "cfd" / "openfoam14" / "cold_flow_tracer" / "system" / "fvSolution"


def tracer_block(text: str) -> str:
    match = run_s2_cfd.TRACER_BLOCK_RE.search(text)
    assert match is not None
    return match.group(2)


class TracerSolverEntryTests(unittest.TestCase):
    def test_base_case_carries_converged_exact_keyword_entry(self) -> None:
        text = BASE_FVSOLUTION.read_text()
        block = tracer_block(text)
        self.assertRegex(block, r"tolerance\s+1e-13;")
        self.assertRegex(block, r"relTol\s+0;")
        self.assertRegex(block, r"maxIter\s+500;")
        self.assertIn("tracerFinal", text)
        self.assertLess(text.index("    tracer\n"), text.index('"rho.*"'))
        # The shared pattern entry must remain for U and e.
        self.assertIn('"(U|e|tracer).*"', text)

    def test_apply_legacy_reproduces_shared_pattern_values(self) -> None:
        text = run_s2_cfd.apply_tracer_solver(
            BASE_FVSOLUTION.read_text(), run_s2_cfd.TRACER_SOLVERS["legacy"]
        )
        block = tracer_block(text)
        self.assertRegex(block, r"tolerance\s+1e-8;")
        self.assertRegex(block, r"relTol\s+0.01;")
        self.assertRegex(block, r"maxIter\s+200;")
        self.assertIn("tracerFinal", text)

    def test_apply_tight_is_idempotent_on_base(self) -> None:
        base = BASE_FVSOLUTION.read_text()
        self.assertEqual(
            run_s2_cfd.apply_tracer_solver(base, run_s2_cfd.TRACER_SOLVERS["tight"]), base
        )

    def test_apply_refuses_case_without_exact_entry(self) -> None:
        stripped = re.sub(
            r"\n[ \t]*tracer[ \t]*\n[ \t]*\{\n.*?\n[ \t]*\}\n", "\n", BASE_FVSOLUTION.read_text(), flags=re.S
        )
        with self.assertRaises(ValueError):
            run_s2_cfd.apply_tracer_solver(stripped, run_s2_cfd.TRACER_SOLVERS["tight"])

    def test_default_mode_is_tight(self) -> None:
        self.assertEqual(next(iter(run_s2_cfd.TRACER_SOLVERS)), "tight")
        self.assertEqual(
            run_s2_cfd.prepare.__defaults__[-1] if run_s2_cfd.prepare.__defaults__ else None,
            "tight",
        )

    def test_prepare_writes_scheme_and_solver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "s2_coarse"
            run_s2_cfd.prepare(case, overwrite=False, tracer_scheme="upwind", tracer_solver="legacy")
            schemes = (case / "system" / "fvSchemes").read_text()
            self.assertIn("div(phi,tracer) Gauss upwind;", schemes)
            solution = (case / "system" / "fvSolution").read_text()
            self.assertRegex(tracer_block(solution), r"relTol\s+0.01;")
            self.assertTrue((case / "-180" / "tracer").exists())
            self.assertTrue((case / "system" / "blockMeshDict").exists())
            self.assertTrue((case / "constant" / "dynamicMeshDict").exists())


class S1RunnerOutputTests(unittest.TestCase):
    def test_sibling_outputs_follow_output_name(self) -> None:
        history = Path("/x/cfd/results/cfd02_s1_tight_scalar_history.csv")
        self.assertEqual(
            run_squish_cfd.sibling_output(history, "_mixing_time.csv").name,
            "cfd02_s1_tight_mixing_time.csv",
        )
        self.assertEqual(
            run_squish_cfd.sibling_output(history, "_metadata.json").name,
            "cfd02_s1_tight_metadata.json",
        )

    def test_prepared_case_inherits_converged_tracer_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case = Path(tmp) / "s1_coarse"
            run_squish_cfd.prepare(case, overwrite=False)
            settings = run_squish_cfd.tracer_solver_settings(case)
            self.assertEqual(settings["tolerance"], "1e-13")
            self.assertEqual(settings["relTol"], "0")
            self.assertEqual(settings["solver"], "PBiCGStab")


class InventoryAuditParserTests(unittest.TestCase):
    def test_patch_values_reads_nonuniform_and_uniform(self) -> None:
        text = """FoamFile { class surfaceScalarField; object phi; }
dimensions [1 0 -1 0 0 0 0];
internalField nonuniform List<scalar> 2(1 2);
boundaryField
{
    piston
    {
        type calculated;
        value nonuniform List<scalar> 3(1e-20 -2e-20 0.5e-20);
    }
    liner
    {
        type calculated;
        value uniform 0;
    }
    axisCore
    {
        type symmetry;
    }
}


// ************************************************************************* //
"""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phi"
            path.write_text(text)
            self.assertEqual(
                audit_scalar_inventory.patch_values(path, "piston"), [1e-20, -2e-20, 0.5e-20]
            )
            self.assertEqual(audit_scalar_inventory.patch_values(path, "liner"), [0.0])
            self.assertIsNone(audit_scalar_inventory.patch_values(path, "axisCore"))
            self.assertIsNone(audit_scalar_inventory.patch_values(path, "cylinderHead"))


if __name__ == "__main__":
    unittest.main()
