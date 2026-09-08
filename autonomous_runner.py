"""Bounded Python execution and artifact delivery.

Untrusted code requires OMEGA_RUNNER_BACKEND=docker and a locally available
OMEGA_RUNNER_DOCKER_IMAGE (default python:3.12-slim). The container has no network,
no writable host mounts, a read-only root, and a size-limited tmpfs. Install and
maintain Docker/images separately: this module never pulls images. Containers
share the host kernel and are not a virtual-machine security boundary.

Local execution is ONLY for trusted source: backend="local", trusted_local=True,
or OMEGA_RUNNER_BACKEND=local with OMEGA_RUNNER_TRUSTED_LOCAL=1. A temporary folder,
AST validation, clean environment, and virtualenv are NOT security isolation.
Local code can access host files/network; local disk/memory cannot be securely
bounded here. Dependency provisioning is opt-in, local-only, pinned, and uses an
explicit offline wheelhouse inside a per-run virtualenv, never host pip.

The legacy execute_with_auto_heal dictionary/file API remains supported. Failed
or unavailable execution returns deliverable source. Callers own retention of
the unique run directories and should expire them after artifact delivery.
"""
from __future__ import annotations

import ast
import base64
import json
import logging
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Tuple

logger = logging.getLogger(__name__)
MODULE_TO_PIP = {"cv2": "opencv-python", "PIL": "pillow", "bs4": "beautifulsoup4",
                 "sklearn": "scikit-learn", "yaml": "pyyaml", "dotenv": "python-dotenv",
                 "yt_dlp": "yt-dlp", "fitz": "pymupdf", "docx": "python-docx",
                 "pptx": "python-pptx", "dateutil": "python-dateutil"}


@dataclass(frozen=True)
class ExecutionLimits:
    timeout_seconds: float = 120.0
    max_output_bytes: int = 65536  # each stream
    max_source_bytes: int = 131072
    max_ast_nodes: int = 20000
    max_ast_depth: int = 100
    max_artifacts: int = 16
    max_artifact_bytes: int = 4 * 1024 * 1024
    max_total_artifact_bytes: int = 16 * 1024 * 1024
    max_scanned_entries: int = 4096
    max_attempts: int = 3
    max_concurrent_runs: int = 2
    docker_memory_mb: int = 256
    docker_work_mb: int = 64
    docker_pids: int = 64

    def __post_init__(self) -> None:
        for name, value in vars(self).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive")
            if name != "timeout_seconds" and not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
        if self.max_attempts > 10 or self.max_concurrent_runs > 32 or self.timeout_seconds > 3600:
            raise ValueError("Execution limits exceed supervisor maximums")


# The supervisor drains output with bounded memory and returns bounded artifact
# bytes. No host directory is mounted writable in Docker. The start byte lets
# Windows attach its Job Object before user code runs. AST is not a sandbox.
_CHILD_SUPERVISOR = r'''
import base64, json, os, pathlib, stat, subprocess, sys, threading
source, work, raw_config = sys.argv[1:]
config = json.loads(raw_config)
if sys.stdin.buffer.read(1) != b"1":
    raise SystemExit(71)
os.chdir(work)
streams = {"stdout": bytearray(), "stderr": bytearray()}
truncated = {"stdout": False, "stderr": False}
def drain(pipe, name):
    while True:
        block = pipe.read(8192)
        if not block:
            break
        remaining = config["output"] - len(streams[name])
        streams[name].extend(block[:max(remaining, 0)])
        if len(block) > remaining:
            truncated[name] = True
    pipe.close()
child = subprocess.Popen([sys.executable, "-I", "-X", "utf8", "-u", source], stdin=subprocess.DEVNULL,
    stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=work, env=dict(os.environ), close_fds=True)
readers = [threading.Thread(target=drain, args=(getattr(child, name), name), daemon=True)
           for name in ("stdout", "stderr")]
for reader in readers:
    reader.start()
returncode = child.wait()
for reader in readers:
    reader.join(0.5)
if any(reader.is_alive() for reader in readers):
    raise SystemExit(72)  # Descendants retained pipes; parent terminates the job.
files, warnings, total, scanned = [], [], 0, 0
root = pathlib.Path(work).resolve()
stop = False
for current, dirs, names in os.walk(root, followlinks=False):
    dirs[:] = sorted(d for d in dirs if not pathlib.Path(current, d).is_symlink()
                     and d not in ("__pycache__", ".venv"))
    scanned += len(dirs) + len(names)
    if scanned > config["entries"]:
        warnings.append("Artifact scan entry limit reached")
        break
    for name in sorted(names):
        path = pathlib.Path(current, name)
        try:
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                continue
            path.resolve().relative_to(root)
            if len(files) >= config["count"]:
                warnings.append("Artifact count limit reached")
                stop = True
                break
            if info.st_size > config["file"] or total + info.st_size > config["total"]:
                warnings.append("Artifact size limit: " + str(path.relative_to(root)))
                continue
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_BINARY", 0)
            with os.fdopen(os.open(path, flags), "rb") as handle:
                opened = os.fstat(handle.fileno())
                if not stat.S_ISREG(opened.st_mode) or opened.st_ino != info.st_ino:
                    continue
                data = handle.read(min(config["file"], config["total"] - total) + 1)
            if len(data) > config["file"] or total + len(data) > config["total"]:
                continue
            total += len(data)
            files.append({"filename": str(path.relative_to(root)).replace("\\", "/"),
                          "data": base64.b64encode(data).decode("ascii")})
        except (OSError, ValueError):
            continue
    if stop:
        break
result = {"returncode": returncode, "files": files, "warnings": warnings[:32]}
for name, data in streams.items():
    result[name] = bytes(data).decode("utf-8", "replace")
    result[name + "_truncated"] = truncated[name]
print(json.dumps(result, ensure_ascii=True))
'''


class _WindowsJob:
    """Kill-on-close job; source waits until assignment succeeds."""
    def __init__(self, process: subprocess.Popen) -> None:
        import ctypes
        from ctypes import wintypes

        class BASIC(ctypes.Structure):
            _fields_ = [("PerProcessUserTimeLimit", ctypes.c_longlong),
                        ("PerJobUserTimeLimit", ctypes.c_longlong), ("LimitFlags", wintypes.DWORD),
                        ("MinimumWorkingSetSize", ctypes.c_size_t), ("MaximumWorkingSetSize", ctypes.c_size_t),
                        ("ActiveProcessLimit", wintypes.DWORD), ("Affinity", ctypes.c_size_t),
                        ("PriorityClass", wintypes.DWORD), ("SchedulingClass", wintypes.DWORD)]

        class IO(ctypes.Structure):
            _fields_ = [(name, ctypes.c_ulonglong) for name in
                        ("ReadOperationCount", "WriteOperationCount", "OtherOperationCount",
                         "ReadTransferCount", "WriteTransferCount", "OtherTransferCount")]

        class EXTENDED(ctypes.Structure):
            _fields_ = [("BasicLimitInformation", BASIC), ("IoInfo", IO),
                        ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                        ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise OSError(ctypes.get_last_error(), "CreateJobObject failed")
        info = EXTENDED()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if (not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info))
                or not self.kernel.AssignProcessToJobObject(self.handle, wintypes.HANDLE(int(process._handle)))):
            error = ctypes.get_last_error()
            self.close()
            raise OSError(error, "Cannot attach execution to a Windows Job Object")

    def close(self) -> None:
        if self.handle:
            self.kernel.TerminateJobObject(self.handle, 1)
            self.kernel.CloseHandle(self.handle)
            self.handle = None


class AutonomousRunner:
    def __init__(self, workspace_dir: Optional[str] = None, *, backend: Optional[str] = None,
                 trusted_local: bool = False, limits: Optional[ExecutionLimits] = None,
                 docker_image: Optional[str] = None, allow_dependency_install: bool = False,
                 dependency_allowlist: Optional[Mapping[str, str]] = None,
                 wheelhouse: Optional[str] = None):
        self.workspace_dir = str(Path(workspace_dir or tempfile.mkdtemp(prefix="openclaw_auto_")).resolve())
        Path(self.workspace_dir).mkdir(parents=True, exist_ok=True)
        self.backend = (backend or os.getenv("OMEGA_RUNNER_BACKEND", "disabled")).lower()
        if self.backend not in {"disabled", "docker", "local"}:
            raise ValueError("Runner backend must be disabled, docker, or local")
        self.trusted_local = trusted_local or os.getenv("OMEGA_RUNNER_TRUSTED_LOCAL") == "1"
        self.limits = limits or ExecutionLimits()
        self.docker_image = docker_image or os.getenv("OMEGA_RUNNER_DOCKER_IMAGE", "python:3.12-slim")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/:@-]{0,250}", self.docker_image):
            raise ValueError("Invalid Docker image reference")
        self.allow_dependency_install = allow_dependency_install
        self.dependency_allowlist = dict(dependency_allowlist or {})
        for module, requirement in self.dependency_allowlist.items():
            if (not re.fullmatch(r"[A-Za-z_]\w*", module)
                    or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*==[A-Za-z0-9][A-Za-z0-9.!+_-]*", requirement)):
                raise ValueError("Dependencies require module names and exact name==version pins")
        self.wheelhouse = Path(wheelhouse).resolve() if wheelhouse else None
        if allow_dependency_install and (not self.wheelhouse or not self.wheelhouse.is_dir()):
            raise ValueError("Dependency provisioning requires a local offline wheelhouse")
        self.installed_packages: set[str] = set()
        self._slots = threading.BoundedSemaphore(self.limits.max_concurrent_runs)

    def install_package(self, pkg_name: str) -> bool:
        """Compatibility method: direct application-environment installs are disabled."""
        logger.info("Direct package installation is disabled; configure per-run offline dependencies")
        return False

    def _minimal_environment(self, work_dir: Path) -> Dict[str, str]:
        env = {"HOME": str(work_dir), "USERPROFILE": str(work_dir), "TMPDIR": str(work_dir),
               "TMP": str(work_dir), "TEMP": str(work_dir), "LANG": "C.UTF-8",
               "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
               "PYTHONNOUSERSITE": "1", "PIP_CONFIG_FILE": os.devnull}
        if os.name == "nt":
            system_root = os.environ.get("SystemRoot", r"C:\Windows")
            env.update(SystemRoot=system_root, WINDIR=system_root, PATH=str(Path(system_root) / "System32"))
        else:
            env["PATH"] = "/usr/bin:/bin"
        return env

    def _validate_source(self, code: str) -> None:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("Provide non-empty Python source")
        if len(code.encode("utf-8")) > self.limits.max_source_bytes:
            raise ValueError("Python source exceeds the configured byte limit")
        tree = ast.parse(code, filename="task.py", mode="exec")
        pending, count = [(tree, 0)], 0
        while pending:
            node, depth = pending.pop()
            count += 1
            if count > self.limits.max_ast_nodes or depth > self.limits.max_ast_depth:
                raise ValueError("Python source exceeds AST complexity limits")
            pending.extend((child, depth + 1) for child in ast.iter_child_nodes(node))

    def _config_json(self) -> str:
        return json.dumps({"output": self.limits.max_output_bytes, "count": self.limits.max_artifacts,
                           "file": self.limits.max_artifact_bytes, "total": self.limits.max_total_artifact_bytes,
                           "entries": self.limits.max_scanned_entries})

    def _docker_command(self, source: Path, container_name: str) -> List[str]:
        docker = shutil.which("docker")
        if not docker:
            raise RuntimeError("Docker executable is unavailable; source is attached")
        if "," in str(source):
            raise ValueError("Docker source path cannot contain a comma")
        return [docker, "run", "--rm", "--pull=never", "--name", container_name, "--network=none",
                "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges:true",
                f"--memory={self.limits.docker_memory_mb}m", f"--memory-swap={self.limits.docker_memory_mb}m",
                "--cpus=1", f"--pids-limit={self.limits.docker_pids}", "--user=65534:65534",
                "--ulimit=nofile=128:128", "--ulimit=core=0", "--init", "-i",
                "--tmpfs", f"/work:rw,noexec,nosuid,nodev,size={self.limits.docker_work_mb}m,mode=1777",
                "--mount", f"type=bind,src={source},dst=/input/task.py,readonly",
                "--workdir=/work", "--env=HOME=/work", "--env=TMPDIR=/work",
                "--entrypoint=python", self.docker_image, "-I", "-X", "utf8", "-u", "-c", _CHILD_SUPERVISOR,
                "/input/task.py", "/work", self._config_json()]

    @staticmethod
    def _terminate_process_tree(process: subprocess.Popen, job: Optional[_WindowsJob] = None) -> None:
        if job is not None:
            job.close()
        elif os.name != "nt":
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        elif process.poll() is None:
            process.kill()  # Assignment failed before any user source was started.
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def _run_process(self, command: List[str], work: Path, timeout: float, *, start_byte: bool = False,
                     capture_limit: Optional[int] = None) -> Dict[str, Any]:
        limit = capture_limit or self.limits.max_output_bytes
        if timeout <= 0:
            return {"returncode": -1, "stdout": "", "stderr": "", "timed_out": True}
        options: Dict[str, Any] = {"cwd": str(work), "env": self._minimal_environment(work),
                                   "stdin": subprocess.PIPE if start_byte else subprocess.DEVNULL,
                                   "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "close_fds": True}
        if os.name == "nt":
            options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW
        else:
            options["start_new_session"] = True
        process = subprocess.Popen(command, **options)
        job = None
        chunks = {"stdout": bytearray(), "stderr": bytearray()}
        exceeded = threading.Event()
        readers = []

        def drain(pipe: Any, name: str) -> None:
            stream_limit = limit if name == "stdout" else self.limits.max_output_bytes
            try:
                while True:
                    block = pipe.read(8192)
                    if not block:
                        break
                    remaining = stream_limit - len(chunks[name])
                    chunks[name].extend(block[:max(remaining, 0)])
                    if len(block) > remaining:
                        exceeded.set()
            finally:
                pipe.close()

        timed_out = False
        try:
            if os.name == "nt":
                job = _WindowsJob(process)
            for name in ("stdout", "stderr"):
                reader = threading.Thread(target=drain, args=(getattr(process, name), name), daemon=True)
                reader.start()
                readers.append(reader)
            if start_byte:
                process.stdin.write(b"1")
                process.stdin.close()
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if exceeded.is_set():
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    break
                time.sleep(min(0.02, max(0.001, deadline - time.monotonic())))
        finally:
            self._terminate_process_tree(process, job)
            if process.stdin is not None and not process.stdin.closed:
                process.stdin.close()
            for reader in readers:
                reader.join(timeout=2)
        return {"returncode": process.returncode, "stdout": bytes(chunks["stdout"]).decode("utf-8", "replace"),
                "stderr": bytes(chunks["stderr"]).decode("utf-8", "replace"),
                "timed_out": timed_out, "output_limit_exceeded": exceeded.is_set()}

    def _remove_container(self, name: str, work: Path) -> None:
        docker = shutil.which("docker")
        if docker:
            try:
                self._run_process([docker, "rm", "--force", name], work, 10)
            except Exception as exc:
                logger.warning("Container cleanup failed for %s: %s", name, type(exc).__name__)

    @staticmethod
    def _descriptor(path: Path, filename: Optional[str] = None) -> Dict[str, str]:
        extension, kind = path.suffix.lower(), "document"
        if extension in {".jpg", ".jpeg", ".png", ".webp"}:
            kind = "photo"
        elif extension in {".mp4", ".mov", ".mkv", ".webm"}:
            kind = "video"
        elif extension in {".mp3", ".ogg", ".wav", ".m4a"}:
            kind = "audio"
        return {"path": str(path.resolve()), "filename": filename or path.name, "type": kind}

    def _materialize_artifacts(self, records: Any, export_dir: Path) -> List[Dict[str, str]]:
        if not isinstance(records, list) or len(records) > self.limits.max_artifacts:
            raise ValueError("Invalid artifact list from execution backend")
        result, total, seen = [], 0, set()
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("Invalid artifact descriptor")
            name, encoded = record.get("filename"), record.get("data")
            if (not isinstance(name, str) or not name or len(name) > 512 or "\\" in name or ":" in name
                    or any(part in {"", ".", ".."} for part in name.split("/"))
                    or name.startswith("/") or not isinstance(encoded, str)):
                raise ValueError("Invalid artifact path or encoding")
            parts = name.split("/")
            if any(part.endswith((".", " ")) or re.match(r"(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)", part)
                   or any(ord(char) < 32 or char in '*?"<>|' for char in part) for part in parts):
                raise ValueError("Unsupported artifact filename")
            if name.casefold() in seen:
                raise ValueError("Duplicate artifact filename")
            seen.add(name.casefold())
            if len(encoded) > ((self.limits.max_artifact_bytes + 2) // 3) * 4:
                raise ValueError("Artifact exceeds configured size")
            data = base64.b64decode(encoded, validate=True)
            total += len(data)
            if len(data) > self.limits.max_artifact_bytes or total > self.limits.max_total_artifact_bytes:
                raise ValueError("Artifact bytes exceed configured limits")
            destination = export_dir.joinpath(*parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("xb") as handle:
                handle.write(data)
            result.append(self._descriptor(destination, name))
        return result

    def _provision(self, module: str, python: Path, work: Path, deadline: float) -> bool:
        requirement = self.dependency_allowlist.get(module)
        if not self.allow_dependency_install or not requirement or not self.wheelhouse:
            return False
        command = [str(python), "-I", "-m", "pip", "--isolated", "--disable-pip-version-check", "install",
                   "--no-input", "--no-deps", "--no-index", "--find-links", str(self.wheelhouse),
                   "--only-binary=:all:", requirement]
        result = self._run_process(command, work, deadline - time.monotonic())
        if result["returncode"] == 0 and not result.get("timed_out"):
            self.installed_packages.add(requirement)
            return True
        return False

    def execute_with_auto_heal(self, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """Execute; retry only approved dependencies, within one overall deadline.

        max_retries retains its historical meaning of maximum total attempts.
        Source and exported files persist for callers to deliver and expire.
        """
        started = time.monotonic()
        result: Dict[str, Any] = {"success": False, "stdout": "", "stderr": "", "files": [],
                                  "installed_packages": [], "attempts": 0, "backend": self.backend}
        try:
            valid_source = isinstance(code, str) and bool(code.strip()) and len(code.encode("utf-8")) <= self.limits.max_source_bytes
        except UnicodeError:
            valid_source = False
        if not valid_source:
            result.update(error="Provide non-empty Python source within the configured byte limit", status="invalid_source")
            return result
        acquired = False
        try:
            run = Path(tempfile.mkdtemp(prefix="run_", dir=self.workspace_dir))
            source, work, exports = run / "task.py", run / "work", run / "artifacts"
            source.write_text(code, encoding="utf-8")
            work.mkdir()
            exports.mkdir()
            result.update(run_id=run.name, files=[self._descriptor(source)])
            self._validate_source(code)
            if isinstance(max_retries, bool) or not isinstance(max_retries, int) or max_retries < 1:
                raise ValueError("max_retries must be a positive integer")
            if self.backend == "disabled" or (self.backend == "local" and not self.trusted_local):
                result.update(status="isolation_unavailable", error=(
                    "Python source is ready. Configure OMEGA_RUNNER_BACKEND=docker to execute it. "
                    "Local execution requires explicit trust and provides no host isolation."))
                return result
            acquired = self._slots.acquire(blocking=False)
            if not acquired:
                result.update(status="busy", error="Execution concurrency limit reached; source is attached")
                return result
            deadline = started + self.limits.timeout_seconds
            python = Path(sys.executable)
            if self.backend == "local" and self.allow_dependency_install:
                environment = run / ".venv"
                provision = self._run_process([sys.executable, "-I", "-m", "venv", str(environment)],
                                              work, deadline - time.monotonic())
                if provision["returncode"] != 0 or provision.get("timed_out"):
                    result.update(status="dependency_error", error="Could not create the per-run dependency environment")
                    return result
                python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            attempted_modules = set()
            for attempt in range(1, min(max_retries, self.limits.max_attempts) + 1):
                result["attempts"] = attempt
                name = "omega-run-" + uuid.uuid4().hex
                if self.backend == "docker":
                    command = self._docker_command(source, name)
                else:
                    command = [str(python), "-I", "-X", "utf8", "-u", "-c", _CHILD_SUPERVISOR,
                               str(source), str(work), self._config_json()]
                try:
                    protocol_limit = self.limits.max_total_artifact_bytes * 4 // 3 + self.limits.max_output_bytes * 12 + 262144
                    process = self._run_process(command, work, deadline - time.monotonic(),
                                                start_byte=True, capture_limit=protocol_limit)
                finally:
                    if self.backend == "docker":
                        self._remove_container(name, work)
                if process.get("timed_out"):
                    result.update(status="timeout", error=f"Execution exceeded {self.limits.timeout_seconds:g} seconds")
                    return result
                if process.get("output_limit_exceeded"):
                    result.update(status="output_limit", error="Execution backend exceeded its output limit")
                    return result
                if process["returncode"] != 0:
                    result.update(status="backend_error", stderr=process["stderr"],
                                  error=f"Execution backend exited with code {process['returncode']}; source is attached")
                    return result
                payload = json.loads(process["stdout"])
                if not isinstance(payload, dict) or not isinstance(payload.get("returncode"), int):
                    raise ValueError("Invalid execution backend response")
                for stream in ("stdout", "stderr"):
                    value = payload.get(stream, "")
                    if not isinstance(value, str) or len(value.encode("utf-8")) > self.limits.max_output_bytes * 3:
                        raise ValueError("Invalid execution output")
                    result[stream] = value
                    result[stream + "_truncated"] = bool(payload.get(stream + "_truncated"))
                if payload["returncode"] == 0:
                    files = self._materialize_artifacts(payload.get("files", []), exports)
                    warnings = payload.get("warnings", [])
                    result.update(success=True, status="completed", files=files,
                                  warnings=[str(item)[:512] for item in warnings[:32]] if isinstance(warnings, list) else [])
                    return result
                match = re.search(r"No module named ['\"]([^'\"]+)['\"]", result["stderr"])
                module = match.group(1).split(".")[0] if match else None
                if (module and module not in attempted_modules and attempt < min(max_retries, self.limits.max_attempts)
                        and self.backend == "local" and self.allow_dependency_install):
                    attempted_modules.add(module)
                    if self._provision(module, python, work, deadline):
                        result["installed_packages"].append(self.dependency_allowlist[module])
                        continue
                reason = (f"Missing dependency '{module}'. Use a provisioned Docker image or explicit pinned offline wheels."
                          if module else f"Python exited with code {payload['returncode']}: {result['stderr'][:1000].strip()}")
                result.update(status="dependency_unavailable" if module else "execution_error", error=reason)
                return result
            result.update(status="retry_limit", error="Configured execution attempt limit reached")
            return result
        except (SyntaxError, ValueError, RecursionError) as exc:
            result.update(status="validation_error", error=f"Python validation failed: {str(exc)[:1000]}")
            return result
        except Exception as exc:
            result.update(status="backend_error", error=f"Execution supervisor error: {str(exc)[:1000]}")
            return result
        finally:
            result["duration_seconds"] = round(time.monotonic() - started, 3)
            if acquired:
                self._slots.release()

    def execute_python(self, code: str, max_retries: int = 3) -> Tuple[str, List[Dict[str, Any]]]:
        """Adapter for tool dispatchers expecting (output, files)."""
        result = self.execute_with_auto_heal(code, max_retries)
        output = result["stdout"] or "Execution completed without text output."
        if not result["success"]:
            output = result["error"]
        if result.get("stdout_truncated"):
            output += "\n[stdout truncated at the configured limit]"
        return output, result["files"]
