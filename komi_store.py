"""
================================================================================
  🩵 Komi Store Engine (Open-Source App Store for GitHub Releases)
  - Discover, search, and inspect open-source apps on GitHub, Codeberg & Forgejo
  - Fetch release notes, versions, changelogs, and direct install assets (APK, EXE, ZIP)
  - Autonomously download release packages under 48MB for direct Telegram delivery
================================================================================
"""

import os
import sys
import re
import json
import logging
import tempfile
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Popular curated open-source apps featured on Komi Store
FEATURED_APPS = [
    {
        "name": "Komi Store",
        "repo": "komi-store/komi-store",
        "category": "App Store",
        "desc": "Cross-platform app store for GitHub releases, Codeberg & Forgejo apps.",
        "website": "https://www.komistore.app"
    },
    {
        "name": "Seal",
        "repo": "JunkFood02/Seal",
        "category": "Media Downloader",
        "desc": "Video/Audio downloader for Android powered by yt-dlp.",
        "website": "https://github.com/JunkFood02/Seal"
    },
    {
        "name": "NewPipe",
        "repo": "TeamNewPipe/NewPipe",
        "category": "Media",
        "desc": "Lightweight YouTube & media streaming client for Android without Google Play Services.",
        "website": "https://newpipe.net"
    },
    {
        "name": "Spotube",
        "repo": "KRTirtho/spotube",
        "category": "Audio",
        "desc": "Open source Spotify client that doesn't require Spotify Premium.",
        "website": "https://spotube.krtirtho.dev"
    },
    {
        "name": "Mihon",
        "repo": "mihonapp/mihon",
        "category": "Reader",
        "desc": "Free and open source manga and comic reader for Android (successor to Tachiyomi).",
        "website": "https://mihon.app"
    },
    {
        "name": "KeePassDX",
        "repo": "Kunzisoft/KeePassDX",
        "category": "Security",
        "desc": "Lightweight and secure password manager for Android.",
        "website": "https://www.keepassdx.com"
    },
    {
        "name": "Termux",
        "repo": "termux/termux-app",
        "category": "Developer Tools",
        "desc": "Android terminal emulator and Linux environment application.",
        "website": "https://termux.dev"
    },
    {
        "name": "Syncthing Android",
        "repo": "syncthing/syncthing-android",
        "category": "Productivity",
        "desc": "Continuous decentralized file synchronization program.",
        "website": "https://syncthing.net"
    }
]

class KomiStoreEngine:
    """Discovery and asset download engine for GitHub and open-source app stores."""

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="komi_store_")
        os.makedirs(self.temp_dir, exist_ok=True)
        self.headers = {
            "User-Agent": "KomiStore-HermesAgent/2.0 (OpenClaw Autonomous App Store)",
            "Accept": "application/vnd.github.v3+json"
        }

    def list_featured(self) -> List[Dict[str, Any]]:
        """Return list of featured open-source applications."""
        return FEATURED_APPS

    def search_apps(self, query: str, limit: int = 5) -> Dict[str, Any]:
        """Search GitHub for repositories with releases matching query."""
        try:
            clean_q = urllib.parse.quote(f"{query} in:name,description")
            url = f"https://api.github.com/search/repositories?q={clean_q}&sort=stars&order=desc&per_page={limit}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            items = []
            for r in data.get("items", []):
                items.append({
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "description": r.get("description") or "No description",
                    "stars": r.get("stargazers_count", 0),
                    "url": r.get("html_url"),
                    "language": r.get("language") or "N/A",
                    "latest_release_url": f"{r.get('html_url')}/releases/latest"
                })

            return {
                "success": True,
                "query": query,
                "count": len(items),
                "apps": items
            }
        except Exception as e:
            logger.error(f"Komi Store search error: {e}")
            return {"success": False, "error": str(e), "apps": []}

    def get_latest_release(self, repo: str) -> Dict[str, Any]:
        """
        Fetch latest release details, changelog, and downloadable assets.
        `repo` can be 'owner/repo' or a full GitHub URL.
        """
        clean_repo = self._extract_repo_slug(repo)
        if not clean_repo:
            return {"success": False, "error": f"Invalid repository format: '{repo}'. Expected 'owner/repo'."}

        url = f"https://api.github.com/repos/{clean_repo}/releases/latest"
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            tag_name = data.get("tag_name", "latest")
            name = data.get("name") or tag_name
            body = data.get("body", "").strip()
            published_at = data.get("published_at", "")[:10]
            html_url = data.get("html_url", "")

            assets = []
            for a in data.get("assets", []):
                size_mb = round(a.get("size", 0) / (1024 * 1024), 2)
                assets.append({
                    "name": a.get("name"),
                    "size_mb": size_mb,
                    "download_count": a.get("download_count", 0),
                    "browser_download_url": a.get("browser_download_url"),
                    "content_type": a.get("content_type", "")
                })

            return {
                "success": True,
                "repo": clean_repo,
                "release_name": name,
                "tag": tag_name,
                "published_date": published_at,
                "html_url": html_url,
                "changelog": body[:1200] + ("..." if len(body) > 1200 else ""),
                "assets_count": len(assets),
                "assets": assets
            }
        except Exception as e:
            logger.error(f"Error fetching release for {clean_repo}: {e}")
            return {"success": False, "repo": clean_repo, "error": str(e)}

    def download_asset(self, repo: str, asset_name_or_ext: Optional[str] = None) -> Dict[str, Any]:
        """
        Download the matching release asset (e.g. .apk, .zip, .exe) under 48MB.
        Returns file path and metadata for Telegram delivery.
        """
        rel_info = self.get_latest_release(repo)
        if not rel_info.get("success"):
            return rel_info

        assets = rel_info.get("assets", [])
        if not assets:
            return {"success": False, "error": f"No binary assets found in latest release of {repo}."}

        target_asset = None
        filter_str = (asset_name_or_ext or "").lower().strip()

        # Selection logic
        if filter_str:
            # 1. Exact or substring match
            for a in assets:
                if filter_str in a["name"].lower():
                    target_asset = a
                    break

        if not target_asset:
            # Prefer Android APK, then general packages under 48MB
            for ext in [".apk", ".zip", ".tar.gz", ".exe", ".msi", ".dmg", ".appimage"]:
                for a in assets:
                    if a["name"].lower().endswith(ext) and a["size_mb"] < 48:
                        target_asset = a
                        break
                if target_asset:
                    break

        # Fallback to first asset < 48MB
        if not target_asset:
            for a in assets:
                if a["size_mb"] < 48:
                    target_asset = a
                    break

        if not target_asset:
            return {
                "success": False,
                "error": f"All release assets exceed the 48MB limit for Telegram delivery. You can download directly from {rel_info.get('html_url')}"
            }

        dl_url = target_asset["browser_download_url"]
        fname = target_asset["name"]
        dest_path = os.path.join(self.temp_dir, fname)

        logger.info(f"🩵 Komi Store downloading asset: {fname} from {dl_url}")
        try:
            req = urllib.request.Request(dl_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=120) as resp, open(dest_path, "wb") as out_f:
                out_f.write(resp.read())

            real_size = round(os.path.getsize(dest_path) / (1024 * 1024), 2)
            return {
                "success": True,
                "repo": rel_info["repo"],
                "release_name": rel_info["release_name"],
                "tag": rel_info["tag"],
                "filename": fname,
                "filepath": dest_path,
                "size_mb": real_size,
                "source_url": dl_url
            }
        except Exception as e:
            logger.error(f"Download asset error: {e}")
            return {"success": False, "error": f"Failed to download asset {fname}: {e}"}

    def _extract_repo_slug(self, raw: str) -> Optional[str]:
        """Parse 'owner/repo' from url or string."""
        raw = raw.strip().strip("<>\"'")
        # If full github url
        m = re.search(r"github\.com/([^/]+/[^/#?]+)", raw)
        if m:
            slug = m.group(1).rstrip(".git")
            return slug
        # If format 'owner/repo'
        if "/" in raw and len(raw.split("/")) == 2:
            return raw.strip()
        return None
