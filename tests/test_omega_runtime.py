import base64
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from omega_runtime import OmegaRuntime, confined, worker_environment


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.runtime = OmegaRuntime(self.temp.name, timeout=20)

    def tearDown(self):
        self.runtime.close()
        self.temp.cleanup()

    def test_process_execution_idempotency_and_owner_isolation(self):
        result = self.runtime.run("finance.amortization", {"principal": 1200, "months": 12}, "alice", idempotency_key="loan-1")
        self.assertEqual(result["status"], "succeeded", result)
        self.assertEqual(result["data"]["monthly_payment"], "100.00")
        self.assertEqual(self.runtime.run("finance.amortization", {"principal": 1200, "months": 12}, "alice", idempotency_key="loan-1"), result)
        with self.assertRaises(ValueError):
            self.runtime.run("finance.amortization", {"principal": 1500}, "alice", idempotency_key="loan-1")
        self.assertIsNone(self.runtime.get_task(result["task_id"], "bob"))
        item = result["artifacts"][0]
        self.assertEqual(len(item["sha256"]), 64)
        with self.assertRaises(FileNotFoundError):
            self.runtime.artifact_path(result["task_id"], "bob", item["name"])
        path = self.runtime.artifact_path(result["task_id"], "alice", item["name"])
        path.write_text("tampered")
        with self.assertRaises(FileNotFoundError):
            self.runtime.artifact_path(result["task_id"], "alice", item["name"])

    def test_validation_failure_has_no_success_artifacts(self):
        result = self.runtime.run("finance.amortization", {"principal": -1})
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("summary", result)
        self.assertEqual(self.runtime.get_task(result["task_id"], "local"), result)

    def test_failed_plan_is_incomplete_and_keeps_diagnostic_artifact(self):
        result = self.runtime.run("reasoning.plan", {"execute": True, "tasks": [
            {"id": "bad", "operation": "math.calculate", "payload": {"expression": "1/0"}}
        ]})
        self.assertEqual(result["status"], "incomplete", result)
        self.assertTrue(self.runtime.artifact_path(result["task_id"], "local", "plan_results.json").is_file())

    def test_input_traversal_and_reserved_files(self):
        for name in ("../escape", "request.json", "RESULT.JSON", "result.json.", "CON", "nul.csv", "C:\\secret"):
            result = self.runtime.run("finance.amortization", {"principal": 10}, inputs={name: base64.b64encode(b"x").decode()})
            self.assertEqual(result["status"], "failed")
        for name in ("../../secret", "C:/secret", "/etc/passwd", "..\\secret"):
            with self.assertRaises(ValueError):
                confined(Path(self.temp.name), name)

    def test_worker_environment_does_not_inherit_tokens(self):
        with patch.dict(os.environ, {"HF_TOKEN": "secret", "TAVILY_API_KEY": "secret", "PYTHONPATH": "/untrusted"}):
            environment = worker_environment(Path(self.temp.name))
        self.assertNotIn("HF_TOKEN", environment)
        self.assertNotIn("TAVILY_API_KEY", environment)
        self.assertNotIn("PYTHONPATH", environment)

    def test_hard_deadline(self):
        self.runtime.timeout = 0.001
        result = self.runtime.run("finance.amortization", {"principal": 1200})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["error"]["code"], "TimeoutError")
        self.assertFalse(self.runtime._active)

    def test_busy_capacity_and_shutdown(self):
        self.runtime._slots.acquire()
        self.runtime._slots.acquire()
        self.assertEqual(self.runtime.run("finance.amortization", {"principal": 10})["status"], "busy")
        self.runtime._slots.release()
        self.runtime._slots.release()
        self.runtime.close()
        with self.assertRaises(RuntimeError):
            self.runtime.run("finance.amortization", {"principal": 10})

    def test_crash_recovery(self):
        with self.runtime._connect() as db:
            db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)", ("lost", "a", "math.calculate", "hash", None, "running", 1, 1, None))
        self.assertEqual(self.runtime.recover_stale(), 1)
        self.assertEqual(self.runtime.get_task("lost", "a")["status"], "interrupted")
