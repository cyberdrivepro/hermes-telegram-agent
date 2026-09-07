"""
================================================================================
  🤖 OpenClaw Autonomous Self-Healing Tool & Code Execution Engine
  - Auto-detects missing packages on the fly
  - Installs required pip libraries dynamically
  - Re-executes code until success
  - Delivers real files, data, and outputs without human intervention
================================================================================
"""

import os
import sys
import re
import io
import time
import tempfile
import logging
import subprocess
import traceback
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

# Map common module names to their PyPI package names
MODULE_TO_PIP = {
    "cv2": "opencv-python",
    "PIL": "pillow",
    "bs4": "beautifulsoup4",
    "sklearn": "scikit-learn",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "yt_dlp": "yt-dlp",
    "fitz": "pymupdf",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "dateutil": "python-dateutil",
}

class AutonomousRunner:
    """Supervised execution sandbox with autonomous dependency resolution and self-healing."""

    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or tempfile.mkdtemp(prefix="openclaw_auto_")
        os.makedirs(self.workspace_dir, exist_ok=True)
        self.installed_packages = set()

    def install_package(self, pkg_name: str) -> bool:
        """Installs a pip package dynamically in the current Python environment."""
        pypi_name = MODULE_TO_PIP.get(pkg_name, pkg_name)
        logger.info(f"⚡ Autonomously installing missing dependency: {pypi_name}")
        try:
            cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", pypi_name]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            if res.returncode == 0:
                self.installed_packages.add(pypi_name)
                logger.info(f"✅ Successfully installed {pypi_name}!")
                return True
            else:
                logger.error(f"❌ Failed to install {pypi_name}: {res.stderr}")
                return False
        except Exception as e:
            logger.error(f"❌ Error during pip install {pypi_name}: {e}")
            return False

    def execute_with_auto_heal(self, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Executes python code. If a ModuleNotFoundError occurs, autonomously installs
        the missing library and retries execution automatically up to `max_retries` times!
        """
        script_file = os.path.join(self.workspace_dir, f"auto_task_{int(time.time())}.py")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(code)

        attempt = 0
        installed_any = []

        while attempt < max_retries:
            attempt += 1
            try:
                proc = subprocess.run(
                    [sys.executable, script_file],
                    cwd=self.workspace_dir,
                    capture_output=True,
                    text=True,
                    timeout=120
                )

                if proc.returncode == 0:
                    # Scan for any generated media or export files
                    media_files = self._collect_new_files(script_file)
                    return {
                        "success": True,
                        "stdout": proc.stdout.strip(),
                        "stderr": proc.stderr.strip(),
                        "installed_packages": installed_any,
                        "files": media_files,
                        "attempts": attempt
                    }

                # Check if failure was due to missing module
                stderr = proc.stderr
                missing_mod_match = re.search(r"No module named ['\"]([^'\"]+)['\"]", stderr)
                if missing_mod_match:
                    missing_mod = missing_mod_match.group(1).split(".")[0]
                    logger.warning(f"⚠️ Attempt {attempt}: Missing module detected: '{missing_mod}'")

                    if self.install_package(missing_mod):
                        installed_any.append(missing_mod)
                        continue  # Retry execution with installed package!
                    else:
                        return {
                            "success": False,
                            "error": f"Missing module '{missing_mod}' could not be installed automatically.",
                            "stderr": stderr
                        }

                # If other runtime error, return it
                return {
                    "success": False,
                    "error": f"Execution error (exit {proc.returncode}):\n{stderr.strip()}",
                    "stdout": proc.stdout.strip()
                }

            except subprocess.TimeoutExpired:
                return {"success": False, "error": "Execution timed out after 120 seconds."}
            except Exception as e:
                return {"success": False, "error": f"Execution supervisor error: {str(e)}"}

        return {"success": False, "error": f"Execution failed after {max_retries} auto-healing attempts."}

    def _collect_new_files(self, script_path: str) -> List[Dict[str, Any]]:
        """Collects any output files created during execution."""
        collected = []
        for root, _, files in os.walk(self.workspace_dir):
            for f in files:
                f_path = os.path.join(root, f)
                if f_path == script_path:
                    continue
                # Check modification within last 2 minutes
                if time.time() - os.path.getmtime(f_path) < 120:
                    ext = os.path.splitext(f)[1].lower()
                    m_type = "document"
                    if ext in [".jpg", ".jpeg", ".png", ".webp"]:
                        m_type = "photo"
                    elif ext in [".mp4", ".mov", ".mkv", ".webm"]:
                        m_type = "video"
                    elif ext in [".mp3", ".ogg", ".wav", ".m4a"]:
                        m_type = "audio"

                    collected.append({
                        "path": f_path,
                        "filename": f,
                        "type": m_type
                    })
        return collected
