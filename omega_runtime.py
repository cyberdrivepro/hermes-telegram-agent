"""Bounded capability execution and durable, owner-scoped result storage.

Built-ins run in disposable subprocesses for cancellation, not as a security
sandbox. Arbitrary generated code uses AutonomousRunner's separate backend.
"""
from __future__ import annotations

import base64
from contextlib import contextmanager
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import threading
import time
import uuid


MODULES = ("omega_artifacts", "omega_data", "omega_reasoning", "omega_finance")
MAX_REQUEST_BYTES = 12 * 1024 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 48 * 1024 * 1024


def capability_catalog():
    entries = {}
    for name in MODULES:
        try:
            module = importlib.import_module(name)
        except ModuleNotFoundError as exc:
            if exc.name != name:
                raise
            continue
        details = getattr(module, "CAPABILITY_INFO", {})
        for key, handler in module.CAPABILITIES.items():
            entries[key] = {"name": key, "module": name,
                            "description": (handler.__doc__ or key).strip().split("\n")[0],
                            **details.get(key, {})}
    return entries


def confined(root: Path, name: str) -> Path:
    if not isinstance(name, str) or not name or "\\" in name or ":" in name:
        raise ValueError("Expected a relative artifact filename")
    path = root / name
    if Path(name).is_absolute() or ".." in Path(name).parts:
        raise ValueError("Artifact path escapes task workspace")
    for part in Path(name).parts:
        if part.rstrip(" .") != part or part.split(".", 1)[0].upper() in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}:
            raise ValueError("Filename is ambiguous or reserved on Windows")
    if any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
        raise ValueError("Symlink artifacts are not supported")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Artifact path escapes task workspace")
    return path


def worker_environment(workspace: Path):
    env = {key: os.environ[key] for key in ("PATH", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "LANG", "LC_ALL") if key in os.environ}
    env.update({"HOME": str(workspace), "USERPROFILE": str(workspace),
                "TMP": str(workspace), "TEMP": str(workspace), "TMPDIR": str(workspace),
                "PYTHONIOENCODING": "utf-8", "PYTHONNOUSERSITE": "1",
                "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"})
    return env


def terminate_process(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       timeout=10, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        import signal
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


class OmegaRuntime:
    def __init__(self, root=None, *, max_workers=2, timeout=90):
        self.root = Path(root or os.getenv("OMEGA_DATA_DIR", ".omega")).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.jobs = self.root / "jobs"
        self.jobs.mkdir(exist_ok=True)
        self.database = self.root / "tasks.sqlite3"
        self.timeout = float(timeout)
        if not math.isfinite(self.timeout) or not 0 < self.timeout <= 600:
            raise ValueError("timeout must be between 0 and 600 seconds")
        if not 1 <= max_workers <= 16:
            raise ValueError("max_workers must be between 1 and 16")
        self._slots = threading.BoundedSemaphore(max_workers)
        self._active = set()
        self._lock = threading.RLock()
        self._closed = False
        with self._connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, owner TEXT NOT NULL, capability TEXT NOT NULL,
                request_hash TEXT NOT NULL, idempotency_key TEXT, status TEXT NOT NULL,
                created REAL NOT NULL, updated REAL NOT NULL, result TEXT,
                UNIQUE(owner, idempotency_key))""")

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.database, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list_capabilities(self):
        return list(capability_catalog().values())

    def get_task(self, task_id, owner):
        with self._connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=? AND owner=?", (task_id, str(owner))).fetchone()
        if row is None:
            return None
        return json.loads(row["result"]) if row["result"] else {"task_id": task_id, "status": row["status"], "capability": row["capability"]}

    def artifact_path(self, task_id, owner, filename):
        result = self.get_task(task_id, owner)
        if not result or result.get("status") not in {"succeeded", "incomplete"}:
            raise FileNotFoundError("Artifact not found")
        item = next((a for a in result.get("artifacts", []) if a["name"] == filename), None)
        if item is None:
            raise FileNotFoundError("Artifact not found")
        path = confined(self.jobs / task_id, filename)
        if not path.is_file() or path.stat().st_size != item["bytes"] or hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            raise FileNotFoundError("Artifact integrity check failed")
        return path

    def run(self, capability, payload, owner="local", *, idempotency_key=None, inputs=None):
        if capability not in capability_catalog():
            raise ValueError(f"Unknown capability: {capability}")
        if not isinstance(payload, dict) or not isinstance(owner, (str, int)) or not str(owner):
            raise ValueError("payload must be an object and owner must be nonempty")
        if idempotency_key is not None and (not isinstance(idempotency_key, str) or not 1 <= len(idempotency_key) <= 128):
            raise ValueError("idempotency_key must contain 1 to 128 characters")
        inputs = inputs or {}
        if not isinstance(inputs, dict) or len(inputs) > 8:
            raise ValueError("At most 8 base64 input files are supported")
        request = {"capability": capability, "payload": payload, "inputs": inputs}
        encoded = json.dumps(request, sort_keys=True, allow_nan=False).encode()
        if len(encoded) > MAX_REQUEST_BYTES:
            raise ValueError("Request exceeds 12 MiB")
        digest = hashlib.sha256(encoded).hexdigest()
        if not self._slots.acquire(timeout=0.05):
            return {"status": "busy", "error": {"code": "capacity", "message": "Execution capacity is busy; retry later"}}
        task_id = uuid.uuid4().hex
        started = time.monotonic()
        workspace = self.jobs / task_id
        created = False
        try:
            with self._lock:
                if self._closed:
                    raise RuntimeError("Runtime is shutting down")
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                if idempotency_key:
                    old = db.execute("SELECT * FROM tasks WHERE owner=? AND idempotency_key=?", (str(owner), idempotency_key)).fetchone()
                    if old:
                        if old["request_hash"] != digest:
                            raise ValueError("Idempotency key was already used with a different request")
                        return json.loads(old["result"]) if old["result"] else {"task_id": old["id"], "status": old["status"], "capability": old["capability"]}
                db.execute("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)", (task_id, str(owner), capability, digest, idempotency_key, "running", time.time(), time.time(), None))
            created = True
            workspace.mkdir()
            for name, content in inputs.items():
                if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}", name) or name.casefold().rstrip(" .") in {"request.json", "result.json"}:
                    raise ValueError("Input filename must be a simple nonreserved name")
                target = confined(workspace, name)
                target.write_bytes(base64.b64decode(content, validate=True))
            (workspace / "request.json").write_text(json.dumps({"capability": capability, "payload": payload}, allow_nan=False), encoding="utf-8")
            worker = Path(__file__).with_name("omega_worker.py")
            if (workspace / "result.json").exists():
                raise ValueError("Worker result cannot be supplied as input")
            options = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {"start_new_session": True}
            with self._lock:
                if self._closed:
                    raise RuntimeError("Runtime is shutting down")
                process = subprocess.Popen([sys.executable, "-s", str(worker), str(workspace)], cwd=workspace,
                                           env=worker_environment(workspace), stdin=subprocess.DEVNULL,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
                self._active.add(process)
            try:
                try:
                    process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    terminate_process(process)
                    raise TimeoutError(f"Capability exceeded {self.timeout:g} seconds")
            finally:
                with self._lock:
                    self._active.discard(process)
            result_file = workspace / "result.json"
            if process.returncode != 0:
                raise RuntimeError(f"Capability worker exited with code {process.returncode}")
            if not result_file.is_file() or result_file.stat().st_size > MAX_RESULT_BYTES:
                raise RuntimeError("Capability worker exited without a bounded result")
            outcome = json.loads(result_file.read_text(encoding="utf-8"))
            if not outcome.get("ok"):
                result = {"status": "failed", "error": outcome.get("error", {"code": "worker_error", "message": "Worker failed"})}
            else:
                raw = outcome["result"]
                artifacts = []
                if not isinstance(raw, dict) or not isinstance(raw.get("artifacts", []), list) or len(raw.get("artifacts", [])) > 32:
                    raise ValueError("Invalid capability result contract")
                total = 0
                for name in dict.fromkeys(raw.get("artifacts", [])):
                    if name.casefold().rstrip(" .") in {"request.json", "result.json"}:
                        raise ValueError("Reserved runtime artifact name")
                    path = confined(workspace, name)
                    if not path.is_file():
                        raise ValueError("Capability reported a missing artifact")
                    size = path.stat().st_size
                    total += size
                    if size > MAX_ARTIFACT_BYTES or total > 96 * 1024 * 1024:
                        raise ValueError("Artifact size budget exceeded")
                    artifacts.append({"name": name, "bytes": size, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
                status = "incomplete" if capability == "reasoning.plan" and raw.get("data", {}).get("status") == "incomplete" else "succeeded"
                result = {"status": status, "summary": raw.get("summary", "Completed"), "data": raw.get("data", {}), "artifacts": artifacts}
        except Exception as exc:
            if not created:
                raise
            result = {"status": "failed", "error": {"code": type(exc).__name__, "message": str(exc)[:600]}, "artifacts": []}
        finally:
            self._slots.release()
        result.update({"task_id": task_id, "capability": capability, "elapsed_ms": round((time.monotonic() - started) * 1000, 2)})
        with self._connect() as db:
            db.execute("UPDATE tasks SET status=?, updated=?, result=? WHERE id=?", (result["status"], time.time(), json.dumps(result, allow_nan=False), task_id))
        return result

    def recover_stale(self):
        """Mark leases past the hard execution deadline as interrupted after crashes."""
        cutoff = time.time() - self.timeout - 60
        with self._connect() as db:
            rows = db.execute("SELECT id, capability FROM tasks WHERE status='running' AND updated<?", (cutoff,)).fetchall()
            for row in rows:
                result = {"task_id": row["id"], "capability": row["capability"], "status": "interrupted", "error": {"code": "worker_lost", "message": "Execution did not persist a result before its deadline"}, "artifacts": []}
                db.execute("UPDATE tasks SET status='interrupted', result=?, updated=? WHERE id=?", (json.dumps(result), time.time(), row["id"]))
        return len(rows)

    def cleanup(self, max_age_seconds=86400):
        if max_age_seconds < 60:
            raise ValueError("Retention must be at least 60 seconds")
        cutoff = time.time() - max_age_seconds
        with self._connect() as db:
            rows = db.execute("SELECT id FROM tasks WHERE status!='running' AND updated<?", (cutoff,)).fetchall()
            for row in rows:
                path = confined(self.jobs, row["id"])
                if path.is_dir():
                    shutil.rmtree(path)
                db.execute("DELETE FROM tasks WHERE id=?", (row["id"],))
        return len(rows)

    def close(self):
        with self._lock:
            self._closed = True
            for process in list(self._active):
                if process.poll() is None:
                    terminate_process(process)
