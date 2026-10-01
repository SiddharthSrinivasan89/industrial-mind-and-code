import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PublicPackageTests(unittest.TestCase):
    def test_provenance_hashes(self):
        provenance = json.loads((ROOT / "data/PROVENANCE.json").read_text())
        for relative, expected in provenance["artifacts"].items():
            actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
            self.assertEqual(actual, expected, relative)

    def test_primary_results(self):
        analysis = json.loads(
            (ROOT / "results/analysis/detailed-analysis.json").read_text()
        )
        expected = {
            "azure_astra": (0.1519343438671087, [0.03761072766854527, 0.26338838569179124]),
            "ollama_qwen": (0.30273346370998977, [0.18517802782236453, 0.4156902194812412]),
            "ollama_gemma": (0.20928975087926177, [0.09952684159286698, 0.31993168757278956]),
        }
        for key, (effect, interval) in expected.items():
            model = analysis["models"][key]
            self.assertEqual(model["estimable_runs"], 5)
            self.assertEqual(model["positive_Delta_AB_runs"], 5)
            self.assertTrue(model["replication_rule_satisfied"])
            self.assertEqual(model["mean_Delta_AB"], effect)
            self.assertEqual(model["crossed_Delta_AB_uncertainty"]["ci95"], interval)

    def test_operations_census(self):
        operations = json.loads(
            (ROOT / "results/analysis/operations.json").read_text()
        )
        self.assertEqual(operations["run_count"], 15)
        self.assertEqual(operations["logical_observations"], 4860)
        self.assertEqual(operations["attempts"], 4905)
        self.assertEqual(operations["terminal_failures"], 0)


if __name__ == "__main__":
    unittest.main()
