"""
================================================================================
  🎬 Universal Media & Video Downloader Engine
  Supports YouTube, Instagram, TikTok, Twitter/X, Reddit, Vimeo & Web MP4s
  Bundles self-contained ffmpeg via imageio-ffmpeg for reliable format merging (<50MB)
================================================================================
"""

import os
import sys
import re
import shutil
import tempfile
import logging
import subprocess
from typing import Dict, Any, Optional, Tuple, List

logger = logging.getLogger(__name__)

def ensure_package(pkg_name: str, import_name: Optional[str] = None) -> bool:
    """Autonomously installs a python package on the fly if missing."""
    mod_name = import_name or pkg_name.replace("-", "_")
    try:
        __import__(mod_name)
        return True
    except ImportError:
        logger.info(f"⚡ Package '{pkg_name}' missing. Autonomously installing via pip...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--no-cache-dir", pkg_name], check=True, timeout=120)
            logger.info(f"✅ Package '{pkg_name}' installed successfully!")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to auto-install '{pkg_name}': {e}")
            return False

class UniversalMediaDownloader:
    """Universal high-speed video/audio downloader with auto-compression for Telegram."""

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="media_dl_")
        os.makedirs(self.temp_dir, exist_ok=True)
        ensure_package("yt-dlp", "yt_dlp")
        ensure_package("imageio-ffmpeg", "imageio_ffmpeg")

    def _get_ffmpeg_path(self) -> Optional[str]:
        """Locates ffmpeg executable from imageio-ffmpeg or system PATH."""
        try:
            import imageio_ffmpeg
            exe = imageio_ffmpeg.get_ffmpeg_exe()
            if exe and os.path.exists(exe):
                return exe
        except Exception:
            pass

        sys_ffmpeg = shutil.which("ffmpeg")
        if sys_ffmpeg:
            return sys_ffmpeg

        return None

    def download(self, url: str, format_type: str = "video") -> Dict[str, Any]:
        """
        Downloads video or audio from YouTube, Instagram, TikTok, Twitter/X, Reddit, or any web link.
        Ensures file stays under 48MB (Telegram bot upload limit).
        """
        if not ensure_package("yt-dlp", "yt_dlp"):
            return {"success": False, "error": "yt-dlp package is required but could not be installed."}

        import yt_dlp

        clean_url = url.strip().strip("<>\"'")
        # Strip playlist parameters to prevent downloading entire playlist
        if "youtube.com" in clean_url or "youtu.be" in clean_url:
            clean_url = re.sub(r"&list=[^&]+", "", clean_url)
            clean_url = re.sub(r"&start_radio=[^&]+", "", clean_url)
            clean_url = re.sub(r"&index=[^&]+", "", clean_url)

        # Output template
        outtmpl = os.path.join(self.temp_dir, "%(title).40s_%(id)s.%(ext)s")
        ffmpeg_exe = self._get_ffmpeg_path()

        if format_type.lower() == "audio":
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": outtmpl,
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }] if ffmpeg_exe else [],
                "quiet": True,
                "no_warnings": True,
                "max_filesize": 48 * 1024 * 1024,
                "noplaylist": True,
            }
        else:
            # Video: target MP4 format, progressive or combined, max 48MB
            ydl_opts = {
                "format": "bestvideo[ext=mp4][filesize<40M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<48M]/best[filesize<48M]/best",
                "outtmpl": outtmpl,
                "quiet": True,
                "no_warnings": True,
                "max_filesize": 48 * 1024 * 1024,
                "merge_output_format": "mp4",
                "noplaylist": True,
            }

        if ffmpeg_exe:
            ydl_opts["ffmpeg_location"] = ffmpeg_exe

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                logger.info(f"🎬 Fetching video info for: {clean_url}")
                info = ydl.extract_info(clean_url, download=True)
                if not info:
                    return {"success": False, "error": "Could not extract video metadata."}

                # Determine downloaded file path
                filename = ydl.prepare_filename(info)

                # If postprocessing changed extension (e.g. mp4 or mp3)
                base, _ = os.path.splitext(filename)
                target_file = None
                for ext in [".mp4", ".mkv", ".webm", ".mp3", ".m4a"]:
                    candidate = base + ext
                    if os.path.exists(candidate):
                        target_file = candidate
                        break

                if not target_file and os.path.exists(filename):
                    target_file = filename

                if not target_file or not os.path.exists(target_file):
                    return {"success": False, "error": "Downloaded file not found on disk."}

                file_size_mb = os.path.getsize(target_file) / (1024 * 1024)
                if file_size_mb > 49.5:
                    return {
                        "success": False,
                        "error": f"Video size ({file_size_mb:.1f} MB) exceeds Telegram bot 50 MB upload limit. Try requesting a shorter clip or audio format."
                    }

                title = info.get("title", "Video")
                duration = info.get("duration", 0)
                uploader = info.get("uploader", "Unknown")

                return {
                    "success": True,
                    "filepath": target_file,
                    "filename": os.path.basename(target_file),
                    "title": title,
                    "duration": duration,
                    "uploader": uploader,
                    "file_size_mb": round(file_size_mb, 2),
                    "type": "audio" if format_type.lower() == "audio" else "video"
                }

        except Exception as e:
            err_msg = str(e)
            logger.error(f"Media download failed: {err_msg}")
            return {"success": False, "error": f"Download failed: {err_msg}"}
