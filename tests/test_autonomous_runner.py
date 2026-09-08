"""Offline tests: real trusted subprocesses, mocked Docker, no pip/network calls."""
import base64
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from autonomous_runner import AutonomousRunner, ExecutionLimits


def backend_result(**payload):
    body = {"returncode": 0, "stdout": "ok\n", "stderr": "", "files": []}
    body.update(payload)
    return {"returncode": 0, "stdout": json.dumps(body), "stderr": "", "timed_out": False}


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="omega_runner_test_")
        self.root = Path(self.directory.name)
        self.environment = patch.dict(os.environ, {"OMEGA_RUNNER_BACKEND": "disabled",
                                                   "OMEGA_RUNNER_TRUSTED_LOCAL": "0"})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.directory.cleanup()

    def runner(self, **kwargs):
        return AutonomousRunner(str(self.root), **kwargs)

    def local(self, **kwargs):
        return self.runner(backend="local", trusted_local=True, **kwargs)

    def test_default_returns_source_without_spawning(self):
        runner = self.runner()
        with patch("autonomous_runner.subprocess.Popen") as spawn:
            result = runner.execute_with_auto_heal("print(42)")
        spawn.assert_not_called()
        self.assertEqual(result["status"], "isolation_unavailable")
        self.assertEqual(result["attempts"], 0)
        self.assertEqual(Path(result["files"][0]["path"]).read_text(), "print(42)")
        self.assertFalse(result["success"])

    def test_local_requires_explicit_trust(self):
        with patch("autonomous_runner.subprocess.Popen") as spawn:
            result = self.runner(backend="local").execute_with_auto_heal("print(42)")
        spawn.assert_not_called()
        self.assertEqual(result["status"], "isolation_unavailable")

    def test_source_validation_and_complexity(self):
        runner = self.local(limits=ExecutionLimits(max_source_bytes=100, max_ast_nodes=8))
        with patch("autonomous_runner.subprocess.Popen") as spawn:
            for code in ("x =", "x=1\ny=2\nz=3", "if True:\n", "\ud800"):
                self.assertFalse(runner.execute_with_auto_heal(code)["success"])
            self.assertEqual(runner.execute_with_auto_heal("#" * 101)["status"], "invalid_source")
            self.assertEqual(runner.execute_with_auto_heal("pass", 0)["status"], "validation_error")
        spawn.assert_not_called()

    def test_distinct_workspaces_and_no_stale_artifacts(self):
        runner = self.local()
        first = runner.execute_with_auto_heal("from pathlib import Path\nPath('first.txt').write_text('one')\nprint('first')")
        second = runner.execute_with_auto_heal("from pathlib import Path\nPath('second.txt').write_text('two')")
        self.assertTrue(first["success"], first)
        self.assertTrue(second["success"], second)
        self.assertNotEqual(first["run_id"], second["run_id"])
        self.assertEqual([f["filename"] for f in first["files"]], ["first.txt"])
        self.assertEqual([f["filename"] for f in second["files"]], ["second.txt"])
        self.assertEqual(Path(first["files"][0]["path"]).read_text(), "one")

    def test_secrets_and_pythonpath_not_inherited(self):
        with patch.dict(os.environ, {"HF_TOKEN": "test_secret", "TELEGRAM_BOT_TOKEN": "test_bot_secret",
                                     "PYTHONPATH": str(self.root), "HTTPS_PROXY": "test_proxy"}):
            result = self.local().execute_with_auto_heal("import os, json\nprint(json.dumps(dict(os.environ)))")
        self.assertTrue(result["success"], result)
        env = json.loads(result["stdout"])
        for name in ("HF_TOKEN", "TELEGRAM_BOT_TOKEN", "PYTHONPATH", "HTTPS_PROXY"):
            self.assertNotIn(name, env)
        self.assertTrue(env["HOME"].startswith(str(self.root)))

    def test_stdout_stderr_unicode_and_output_limits(self):
        runner = self.local(limits=ExecutionLimits(max_output_bytes=128))
        result = runner.execute_with_auto_heal("import sys\nprint('a'*10000)\nprint('b'*10000, file=sys.stderr)")
        self.assertTrue(result["success"], result)
        self.assertEqual(len(result["stdout"]), 128)
        self.assertEqual(len(result["stderr"]), 128)
        self.assertTrue(result["stdout_truncated"])
        self.assertTrue(result["stderr_truncated"])
        unicode_result = self.local().execute_with_auto_heal("print('नमस्ते ✓')")
        self.assertTrue(unicode_result["success"], unicode_result)
        self.assertEqual(unicode_result["stdout"].strip(), "नमस्ते ✓")

    def test_artifact_count_and_size_limits(self):
        runner = self.local(limits=ExecutionLimits(max_artifacts=2, max_artifact_bytes=10,
                                                  max_total_artifact_bytes=12))
        result = runner.execute_with_auto_heal(
            "from pathlib import Path\nPath('a.txt').write_text('123456')\n"
            "Path('b.txt').write_text('123456')\nPath('c.txt').write_text('123456')\n"
            "Path('oversized.txt').write_text('x'*100)")
        self.assertTrue(result["success"], result)
        self.assertEqual(len(result["files"]), 2)
        self.assertLessEqual(sum(Path(f["path"]).stat().st_size for f in result["files"]), 12)
        self.assertTrue(result["warnings"])

    def test_missing_dependency_never_installs_by_default(self):
        runner = self.local()
        with patch.object(runner, "_provision") as provision:
            result = runner.execute_with_auto_heal("import omega_nonexistent_test_dependency", 10)
        provision.assert_not_called()
        self.assertEqual(result["status"], "dependency_unavailable")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["files"][0]["filename"], "task.py")
        with patch("autonomous_runner.subprocess.Popen") as spawn:
            self.assertFalse(runner.install_package("requests"))
        spawn.assert_not_called()

    def test_timeout_terminates_descendant_before_it_writes(self):
        marker = self.root / "descendant_survived.txt"
        child = f"import time; from pathlib import Path; time.sleep(1.5); Path({str(marker)!r}).write_text('alive')"
        source = ("import subprocess, sys, time\n"
                  f"subprocess.Popen([sys.executable, '-c', {child!r}], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
                  "time.sleep(30)")
        started = time.monotonic()
        result = self.local(limits=ExecutionLimits(timeout_seconds=0.5)).execute_with_auto_heal(source)
        self.assertEqual(result["status"], "timeout", result)
        self.assertLess(time.monotonic() - started, 4)
        time.sleep(1.7)
        self.assertFalse(marker.exists(), "A child escaped process-tree termination")

    def test_concurrency_limit_rejects_excess_job(self):
        runner = self.local(limits=ExecutionLimits(max_concurrent_runs=1))
        entered, release = threading.Event(), threading.Event()
        results = []

        def execute(*args, **kwargs):
            entered.set()
            release.wait(5)
            return backend_result()

        with patch.object(runner, "_run_process", side_effect=execute):
            thread = threading.Thread(target=lambda: results.append(runner.execute_with_auto_heal("pass")))
            thread.start()
            try:
                self.assertTrue(entered.wait(3))
                self.assertEqual(runner.execute_with_auto_heal("pass")["status"], "busy")
            finally:
                release.set()
                thread.join(5)
        self.assertTrue(results[0]["success"])

    def test_docker_command_has_isolation_limits_and_readonly_source(self):
        runner = self.runner(backend="docker")
        with patch("autonomous_runner.shutil.which", return_value="docker"):
            command = runner._docker_command(self.root / "source.py", "test-container")
        for flag in ("--network=none", "--read-only", "--cap-drop=ALL", "--pull=never",
                     "--security-opt=no-new-privileges:true", "--pids-limit=64", "--user=65534:65534"):
            self.assertIn(flag, command)
        self.assertIn("size=64m", command[command.index("--tmpfs") + 1])
        mount = command[command.index("--mount") + 1]
        self.assertTrue(mount.endswith(",readonly"))
        self.assertIn("source.py", mount)
        self.assertEqual(command.count("--mount"), 1)

    def test_docker_timeout_always_removes_named_container(self):
        runner = self.runner(backend="docker")
        with patch.object(runner, "_docker_command", return_value=["docker", "run"]), \
                patch.object(runner, "_run_process", return_value={"timed_out": True}), \
                patch.object(runner, "_remove_container") as cleanup:
            result = runner.execute_with_auto_heal("pass")
        self.assertEqual(result["status"], "timeout")
        cleanup.assert_called_once()
        self.assertTrue(cleanup.call_args.args[0].startswith("omega-run-"))

    def test_docker_missing_never_falls_back_to_local(self):
        with patch("autonomous_runner.shutil.which", return_value=None), \
                patch("autonomous_runner.subprocess.Popen") as spawn:
            result = self.runner(backend="docker").execute_with_auto_heal("print('host')")
        spawn.assert_not_called()
        self.assertEqual(result["status"], "backend_error")
        self.assertEqual(result["files"][0]["filename"], "task.py")

    def test_artifact_protocol_rejects_traversal_and_aliases(self):
        runner = self.local()
        for name in ("../outside.txt", "/absolute.txt", "a/../../escape", "C:/drive.txt", "a\\b", "NUL.txt", "a/..", "a. "):
            with self.subTest(name=name):
                payload = backend_result(files=[{"filename": name, "data": base64.b64encode(b"bad").decode()}])
                with patch.object(runner, "_run_process", return_value=payload):
                    result = runner.execute_with_auto_heal("pass")
                self.assertFalse(result["success"])
        self.assertFalse((self.root.parent / "outside.txt").exists())

    def test_pinned_offline_provision_uses_only_run_venv(self):
        runner = self.local(allow_dependency_install=True, dependency_allowlist={"example": "example==1.2.3"},
                            wheelhouse=str(self.root))
        python = self.root / "run_test" / ".venv" / "bin" / "python"
        with patch.object(runner, "_run_process", return_value={"returncode": 0}) as process:
            self.assertTrue(runner._provision("example", python, self.root, time.monotonic() + 10))
            self.assertFalse(runner._provision("unapproved", python, self.root, time.monotonic() + 10))
        process.assert_called_once()
        command = process.call_args.args[0]
        self.assertEqual(command[0], str(python))
        for flag in ("--isolated", "--no-deps", "--no-index", "--only-binary=:all:", "example==1.2.3"):
            self.assertIn(flag, command)
        self.assertNotEqual(command[0], sys.executable)

    def test_invalid_dependency_configuration_and_limits(self):
        for requirement in ("requests", "requests>=2", "https://example.org/a.whl", "requests==1 --index-url evil"):
            with self.assertRaises(ValueError):
                self.local(dependency_allowlist={"requests": requirement})
        with self.assertRaises(ValueError):
            self.local(allow_dependency_install=True)
        for kwargs in ({"timeout_seconds": float("nan")}, {"timeout_seconds": 0}, {"max_attempts": 100}, {"max_artifacts": 1.5}):
            with self.assertRaises(ValueError):
                ExecutionLimits(**kwargs)

    def test_retry_is_bounded_and_repeated_missing_module_stops(self):
        runner = self.local(allow_dependency_install=True, dependency_allowlist={"example": "example==1.2.3"},
                            wheelhouse=str(self.root), limits=ExecutionLimits(max_attempts=2))
        missing = backend_result(returncode=1, stderr="ModuleNotFoundError: No module named 'example'")
        with patch.object(runner, "_run_process", side_effect=[{"returncode": 0}, missing, missing]) as process, \
                patch.object(runner, "_provision", return_value=True) as provision:
            result = runner.execute_with_auto_heal("import example", 100)
        self.assertEqual(result["attempts"], 2)
        self.assertEqual(process.call_count, 3)
        provision.assert_called_once()
        self.assertEqual(result["installed_packages"], ["example==1.2.3"])

    def test_tuple_adapter_returns_source_on_unavailable_backend(self):
        output, files = self.runner().execute_python("print(42)")
        self.assertIn("source is ready", output)
        self.assertEqual(files[0]["filename"], "task.py")


if __name__ == "__main__":
    unittest.main()
