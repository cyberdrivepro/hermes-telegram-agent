"""Offline integration and boundary tests for local artifact capabilities."""

import importlib.util
import json
import math
import struct
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import omega_artifacts as artifacts


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temporary.name)

    def tearDown(self):
        self.temporary.cleanup()

    def file(self, result, filename):
        matching = [self.workspace / name for name in result["artifacts"] if Path(name).name == filename]
        self.assertEqual(len(matching), 1)
        self.assertTrue(matching[0].is_file())
        self.assertTrue(matching[0].resolve().is_relative_to(self.workspace.resolve()))
        return matching[0]

    def test_survey_json_and_script_cover_all_supported_types(self):
        questions = [
            {"id": "name", "title": "Name", "type": "short_text", "required": True},
            {"id": "notes", "title": "Notes", "type": "paragraph"},
            {"id": "role", "title": "Role", "type": "multiple_choice", "options": ["Engineer", "Designer"]},
            {"id": "tools", "title": "Tools", "type": "checkboxes", "options": ["Python", "SQL"]},
            {"id": "office", "title": "Office", "type": "dropdown", "options": ["Remote", "HQ"]},
            {"id": "rating", "title": "Rating", "type": "scale", "min": 0, "max": 10},
        ]
        result = artifacts.survey_bundle({"title": "Feedback", "questions": questions, "include_excel": False}, self.workspace)
        create = json.loads(self.file(result, "forms_create.json").read_text())
        requests = json.loads(self.file(result, "forms_batch_update.json").read_text())["requests"]
        self.assertEqual(create, {"info": {"title": "Feedback"}})
        self.assertEqual([request["createItem"]["location"]["index"] for request in requests[1:]], list(range(6)))
        kinds = [request["createItem"]["item"]["questionItem"]["question"] for request in requests[1:]]
        self.assertFalse(kinds[0]["textQuestion"]["paragraph"])
        self.assertTrue(kinds[1]["textQuestion"]["paragraph"])
        self.assertEqual([question["choiceQuestion"]["type"] for question in kinds[2:5]], ["RADIO", "CHECKBOX", "DROP_DOWN"])
        self.assertEqual(kinds[5]["scaleQuestion"], {"low": 0, "high": 10})
        script = self.file(result, "create_survey.gs").read_text(encoding="utf-8")
        self.assertIn("item.setChoiceValues(q.options)", script)
        self.assertIn("FormApp.DestinationType.SPREADSHEET", script)
        self.assertFalse(result["data"]["google_form_created"])

    def test_html_escapes_user_content_and_script_terminators(self):
        attack = '</script><script>alert("bad")</script>'
        result = artifacts.survey_bundle({"title": attack, "include_excel": False, "questions": [
            {"id": "q", "title": attack, "type": "multiple_choice", "options": ['\" onmouseover=alert(1) x=\"', attack]},
        ]}, self.workspace)
        page = self.file(result, "survey.html").read_text(encoding="utf-8")
        self.assertEqual(page.count("<script>"), 1)
        self.assertEqual(page.count("</script>"), 1)
        self.assertNotIn(attack, page)
        self.assertIn("\\u003c/script\\u003e", page)
        self.assertIn("&quot; onmouseover=alert(1)", page)
        self.assertIn("setCustomValidity", page)
        self.assertIn("text = \"'\" + text", page)
        self.assertIn("const csv = '\\uFEFF'", page)

    def test_survey_rejects_invalid_schema_and_response_values(self):
        cases = [
            {"questions": []},
            {"questions": [{"id": "x\"", "title": "Bad"}]},
            {"questions": [{"id": "q", "title": "One"}, {"id": "q", "title": "Two"}]},
            {"questions": [{"title": "Rate", "type": "scale", "min": 2}]},
            {"questions": [{"title": "Rate", "required": "false"}]},
            {"questions": [{"id": "q", "title": "Pick", "type": "multiple_choice", "options": ["Yes", "Yes"]}]},
            {"questions": [{"id": "q", "title": "Rate", "type": "scale"}], "responses": [{"q": 8}]},
            {"questions": [{"id": "q", "title": "Required", "required": True}], "responses": [{}]},
            {"responses": [{"unknown": "answer"}]},
            {"analysis_capacity": 5001},
        ]
        for payload in cases:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                artifacts.survey_bundle(payload, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])

    @unittest.skipUnless(importlib.util.find_spec("openpyxl"), "optional openpyxl unavailable")
    def test_workbook_has_safe_inputs_working_formula_ranges_and_chart(self):
        from openpyxl import load_workbook
        payload = {"title": "=MALICIOUS()", "analysis_capacity": 20, "questions": [
            {"id": "text", "title": "=HEADER()", "type": "short_text"},
            {"id": "rating", "title": "Rating", "type": "scale"},
        ], "responses": [{"text": '=HYPERLINK("https://example.invalid")', "rating": 4}, {"rating": 2}]}
        result = artifacts.survey_bundle(payload, self.workspace)
        workbook = load_workbook(self.file(result, "analysis.xlsx"))
        self.assertEqual(workbook["Responses"]["B1"].data_type, "s")
        self.assertEqual(workbook["Responses"]["B2"].data_type, "s")
        self.assertEqual(workbook["Responses"]["C2"].value, 4)
        self.assertEqual(workbook["Analysis"]["B2"].value, "=COUNT(Responses!A2:A21)")
        self.assertEqual(workbook["Analysis"]["B4"].value, '=COUNTIF(Responses!B2:B21,"<>")')
        self.assertEqual(workbook["Analysis"]["C5"].value, '=IF(COUNT(Responses!C2:C21)=0,"",AVERAGE(Responses!C2:C21))')
        self.assertEqual(len(workbook["Analysis"]._charts), 1)
        self.assertTrue(workbook.calculation.fullCalcOnLoad)
        self.assertEqual(workbook["Responses"].freeze_panes, "B2")
        workbook.close()

    def test_missing_excel_dependency_cleans_partial_bundle(self):
        with patch.object(artifacts, "_survey_workbook", side_effect=artifacts.ArtifactDependencyError("openpyxl missing")):
            with self.assertRaisesRegex(artifacts.ArtifactDependencyError, "openpyxl"):
                artifacts.survey_bundle({}, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_stl_is_closed_oriented_and_has_real_four_hole_volume(self):
        for width, depth, x, y in [(60, 60, 31, 31), (70.25, 53.5, 41, 22.4), (10, 10, 4, 4)]:
            with self.subTest(dimensions=(width, depth, x, y)):
                hole = 2.0
                result = artifacts.motor_bracket({"width_mm": width, "depth_mm": depth, "screw_spacing_x_mm": x,
                    "screw_spacing_y_mm": y, "thickness_mm": 4, "hole_diameter_mm": hole}, self.workspace)
                blob = self.file(result, "motor_bracket.stl").read_bytes()
                count = struct.unpack_from("<I", blob, 80)[0]
                self.assertEqual(len(blob), 84 + 50 * count)
                edges, directed, volume, points = Counter(), Counter(), 0.0, []
                for offset in range(84, len(blob), 50):
                    values = struct.unpack_from("<12fH", blob, offset)
                    normal, a, b, c = tuple(values[:3]), tuple(values[3:6]), tuple(values[6:9]), tuple(values[9:12])
                    points.extend((a, b, c))
                    self.assertAlmostEqual(sum(value * value for value in normal), 1, places=5)
                    for p, q in ((a, b), (b, c), (c, a)):
                        edges[tuple(sorted((p, q)))] += 1
                        directed[(p, q)] += 1
                    volume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6
                self.assertEqual(set(edges.values()), {2}, "Every STL edge must belong to exactly two facets")
                for (p, q), edge_count in directed.items():
                    self.assertEqual(edge_count, directed[(q, p)], "Adjacent facets must have consistent outward winding")
                expected = (width * depth - 4 * math.pi * (hole / 2) ** 2) * 4
                self.assertAlmostEqual(volume, expected, delta=0.1)
                self.assertAlmostEqual(max(p[0] for p in points) - min(p[0] for p in points), width, places=4)
                self.assertAlmostEqual(max(p[1] for p in points) - min(p[1] for p in points), depth, places=4)
                self.assertGreater(result["data"]["maximum_radial_tessellation_error_mm"], 0)
                svg = self.file(result, "motor_bracket.svg").read_text()
                self.assertEqual(svg.count("<circle "), 4)

    def test_cad_invalid_geometry_is_rejected_before_writes(self):
        for payload in [{"width_mm": 20}, {"hole_diameter_mm": 40}, {"segments": 33}, {"thickness_mm": float("nan")}, {"width_mm": True}]:
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                artifacts.motor_bracket(payload, self.workspace)
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_subtitles_have_exact_millisecond_timestamps_and_escaped_text(self):
        result = artifacts.subtitles({"cues": [{"start": 59.9996, "end": 61.23, "text": "<b>Hi</b> & welcome"}]}, self.workspace)
        srt = self.file(result, "captions.srt").read_text()
        vtt = self.file(result, "captions.vtt").read_text()
        self.assertIn("00:01:00,000 --> 00:01:01,230", srt)
        self.assertIn("&lt;b&gt;Hi&lt;/b&gt; &amp; welcome", srt)
        self.assertTrue(vtt.startswith("WEBVTT\n\n"))
        self.assertIn("00:01:00.000", vtt)

    def test_subtitle_overlap_and_injection_rejected(self):
        for cues in [[], [{"start": 0, "end": 2, "text": "First"}, {"start": 1, "end": 3, "text": "Overlap"}],
                     [{"start": 0, "end": 1, "text": "hello\n\n10:00 --> 11:00"}],
                     [{"start": 0, "end": 0.0001, "text": "Too short"}]]:
            with self.subTest(cues=cues), self.assertRaises(ValueError):
                artifacts.subtitles({"cues": cues}, self.workspace)

    def test_media_cannot_read_outside_workspace_or_use_network_input(self):
        for name in ["../outside.mp4", "C:/outside.mp4", "https://example.com/video.mp4", "\\\\server\\video.mp4", "playlist.m3u8"]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                artifacts.media_clip({"input_path": name}, self.workspace)

    def test_media_invokes_fixed_local_ffmpeg_arguments(self):
        (self.workspace / "input.mp4").write_bytes(b"input video")
        captured = {}

        def run(command, **kwargs):
            captured.update(command=command, kwargs=kwargs)
            Path(command[-1]).write_bytes(b"encoded" * 500)
            return subprocess.CompletedProcess(command, 0)

        with patch.object(artifacts, "_ffmpeg", return_value="ffmpeg"), patch.object(artifacts.subprocess, "run", side_effect=run):
            result = artifacts.media_clip({"input_path": "input.mp4", "duration_seconds": 5, "vertical": True,
                "cues": [{"start": 0, "end": 1, "text": "Welcome"}]}, self.workspace)
        command = captured["command"]
        self.assertFalse(captured["kwargs"]["shell"])
        self.assertEqual(command[command.index("-protocol_whitelist") + 1], "file")
        self.assertEqual(command[command.index("-format_whitelist") + 1], "mov,matroska,webm,avi")
        self.assertIn("crop=720:1280", command[command.index("-vf") + 1])
        self.assertIn("filename=captions.srt", command[command.index("-vf") + 1])
        self.file(result, "clip.mp4")
        self.file(result, "captions.srt")

    def test_media_timeout_deletes_partial_output(self):
        (self.workspace / "input.mp4").write_bytes(b"input video")
        with patch.object(artifacts, "_ffmpeg", return_value="ffmpeg"), patch.object(artifacts.subprocess, "run", side_effect=subprocess.TimeoutExpired("ffmpeg", 1)):
            with self.assertRaisesRegex(RuntimeError, "deadline"):
                artifacts.media_clip({"input_path": "input.mp4", "timeout_seconds": 1}, self.workspace)
        self.assertEqual([path.name for path in self.workspace.iterdir()], ["input.mp4"])

    def test_real_ffmpeg_clip_has_expected_frame_count(self):
        try:
            ffmpeg = artifacts._ffmpeg()
        except artifacts.ArtifactDependencyError as exc:
            self.skipTest(str(exc))
        source = self.workspace / "input.mp4"
        subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                        "testsrc2=size=160x120:rate=10:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source)],
                       check=True, capture_output=True, timeout=30)
        result = artifacts.media_clip({"input_path": "input.mp4", "start_seconds": 0.4, "duration_seconds": 0.6}, self.workspace)
        clip = self.file(result, "clip.mp4")
        decoded = subprocess.run([ffmpeg, "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(clip), "-map", "0:v:0", "-f", "framemd5", "-"],
                                 check=True, capture_output=True, text=True, timeout=30)
        frames = [line for line in decoded.stdout.splitlines() if line and not line.startswith("#")]
        self.assertEqual(len(frames), 6, decoded.stdout)


if __name__ == "__main__":
    unittest.main()
