from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import yaml

from mechanism_gate import load_chemked_points, parent_retention


class MechanismGateTests(unittest.TestCase):
    def test_zero_point_parse_is_a_hard_failure(self):
        document = {
            "common-properties": {
                "ignition-type": {"target": "temperature", "type": "d/dt max"},
            },
            "datapoints": [{
                "temperature": ["800 K"],
                "pressure": ["40 bar"],
                "ignition-delay": ["1 ms"],
                "composition": {"species": []},
            }],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "bad.yaml"
            path.write_text(yaml.safe_dump(document), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "Zero compatible"):
                load_chemked_points([str(path)])

    def test_zhao_skeleton_retains_parent_shape(self):
        metrics, rows = parent_retention(
            "mechanisms/dme_zhao_sk39.yaml",
            "mechanisms/dme_zhao_full.yaml",
            "CH3OCH3:1",
            pressure_bar=40.0,
            temperatures_K=(700, 800, 900, 1000),
        )
        self.assertEqual(len(rows), 4)
        self.assertTrue(metrics["retention_pass"])
        self.assertIn("not experimental validation", metrics["scope"])


if __name__ == "__main__":
    unittest.main()
