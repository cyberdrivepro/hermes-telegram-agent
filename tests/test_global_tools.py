import unittest
from pathlib import Path
from global_tools_engine import GlobalToolsEngine
from virtual_office import VirtualOfficeRouter

class TestGlobalToolsEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GlobalToolsEngine()
        self.router = VirtualOfficeRouter()

    def test_total_count(self):
        self.assertEqual(len(self.engine.tools), 1057)

    def test_categories_count(self):
        expected_counts = {
            "CAD": 127,
            "Design": 134,
            "Video Editing": 126,
            "Coding": 140,
            "Finance": 131,
            "General": 128,
            "Productivity": 132,
            "Research": 139
        }
        for cat, count in expected_counts.items():
            self.assertEqual(len(self.engine.get_category_tools(cat)), count, f"Mismatch for {cat}")

    def test_tool_integrity(self):
        for tool in self.engine.tools:
            self.assertTrue(tool["name"], "Tool name should not be empty")
            self.assertTrue(tool["category"], "Category should not be empty")
            self.assertTrue(tool["open_source"], f"Open source alternative should not be empty for {tool['name']}")
            self.assertTrue(tool["github"].startswith("https://github.com"), f"GitHub URL invalid for {tool['name']}")
            self.assertTrue(tool["best_task_model"], f"Best task model missing for {tool['name']}")
            self.assertTrue(tool["hf_url"].startswith("https://huggingface.co"), f"HF URL invalid for {tool['name']}")
            self.assertEqual(tool["gui_model"], "ByteDance-Seed/UI-TARS-1.5-7B")

    def test_lookups(self):
        autocad = self.engine.get_tool("AutoCAD")
        self.assertIsNotNone(autocad)
        self.assertEqual(autocad["open_source"], "FreeCAD")
        self.assertEqual(autocad["best_task_model"], "ADSKAILab/Zero-To-CAD-Qwen3-VL-2B")

        photoshop = self.engine.get_tool("Photoshop")
        self.assertIsNotNone(photoshop)
        self.assertEqual(photoshop["open_source"], "Krita")
        self.assertEqual(photoshop["best_task_model"], "Qwen/Qwen-Image-Edit")

        premiere = self.engine.get_tool("Premiere Pro")
        self.assertIsNotNone(premiere)
        self.assertEqual(premiere["open_source"], "Shotcut")

        bloomberg = self.engine.get_tool("Bloomberg Terminal")
        self.assertIsNotNone(bloomberg)
        self.assertEqual(bloomberg["open_source"], "OpenBB")
        self.assertEqual(bloomberg["best_task_model"], "SUFE-AIFLM-Lab/Fin-R1")

    def test_search(self):
        results = self.engine.search_tools("video", limit=5)
        self.assertTrue(len(results) > 0)

    def test_router_integration(self):
        worker_key, worker = self.router.route_task("What is the open source alternative to AutoCAD?")
        self.assertEqual(worker_key, "cad")

        worker_key, worker = self.router.route_task("/video create a montage")
        self.assertEqual(worker_key, "video")

if __name__ == "__main__":
    unittest.main()
