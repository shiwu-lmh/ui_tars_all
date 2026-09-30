import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parent
DEMO_ROOT = ROOT / "demo_medical_system"


class DemoMedicalSystemTests(unittest.TestCase):
    def test_demo_dataset_has_multiple_people_and_multiple_records(self):
        data = json.loads((DEMO_ROOT / "data.json").read_text(encoding="utf-8"))

        self.assertEqual([person["patient_id"] for person in data], ["DEMO-001", "DEMO-002"])
        self.assertEqual(len(data[0]["records"]), 2)
        self.assertEqual(len(data[1]["records"]), 1)
        self.assertTrue(all(person["patient_id"].startswith("DEMO-") for person in data))

    def test_demo_assets_and_instructions_are_present(self):
        self.assertTrue((DEMO_ROOT / "index.html").exists())
        self.assertTrue((ROOT / "start_demo_system.ps1").exists())
        prompt = (ROOT / "demo_test_prompt.md").read_text(encoding="utf-8")
        self.assertIn("127.0.0.1:8765", prompt)
        self.assertIn("DEMO-001", prompt)
        self.assertIn("demo", prompt)


if __name__ == "__main__":
    unittest.main()
