---
name: komi_store
title: "Komi Store & GitHub App Discovery"
description: "Cross-platform open-source app store for GitHub releases, Codeberg & Forgejo. Discovers apps, retrieves latest release notes, changelogs, and APK/installer assets."
triggers: ["komi", "komistore", "appstore", "github release", "apk", "install app", "open source apps", "download app"]
author: "OpenClaw Autonomous Engine"
created_at: "2026-09-07 19:16:00 UTC"
---

# Komi Store & GitHub App Discovery

## Description
Cross-platform open-source app store for GitHub releases, Codeberg & Forgejo. Discovers apps, retrieves latest release notes, changelogs, and APK/installer assets.

## Workflow & Instructions
1. Parse user query for app name or GitHub repo (e.g. 'komi-store/komi-store', 'Seal', 'Spotube', 'NewPipe').
2. If searching by keyword, query GitHub Search API for popular repositories.
3. If checking a repo, query GitHub Releases API for the latest version tag, release notes, and binary assets (APK, EXE, DMG, AppImage, ZIP).
4. Return formatted app cards with direct install links.

## Executable Implementation
```python
import urllib.request, urllib.parse, json
query = params.get('query', 'komi-store/komi-store').strip()
headers = {'User-Agent': 'KomiStore-OpenClaw/2.0', 'Accept': 'application/vnd.github.v3+json'}

if '/' in query and not ' ' in query:
    slug = query.replace('https://github.com/', '').strip('/')
    url = f"https://api.github.com/repos/{slug}/releases/latest"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode())
        assets = [f"• `{a['name']}` ({round(a['size']/(1024*1024), 1)} MB)" for a in data.get('assets', [])[:6]]
        result = (
            f"🩵 **Komi Store Release: {slug}**\n"
            f"🏷️ Version: `{data.get('tag_name')}` ({data.get('name')})\n"
            f"📅 Released: `{data.get('published_at', '')[:10]}`\n"
            f"🔗 [View Release]({data.get('html_url')})\n\n"
            f"📦 **Downloadable Assets:**\n" + ("\n".join(assets) if assets else "• Source code only")
        )
    except Exception as e:
        result = f"⚠️ Could not fetch release for {slug}: {e}"
else:
    q = urllib.parse.quote(f"{query} in:name,description")
    url = f"https://api.github.com/search/repositories?q={q}&sort=stars&order=desc&per_page=4"
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode())
        cards = []
        for item in data.get('items', []):
            cards.append(
                f"• **[{item['name']}]({item['html_url']})** (`{item['full_name']}`)\n"
                f"  ⭐ {item['stargazers_count']:,} | 💻 {item.get('language') or 'App'}\n"
                f"  _{item.get('description') or 'Open source software'}_\n"
                f"  📥 `/komi {item['full_name']}`"
            )
        result = f"🩵 **Komi Store Search Results for '{query}':**\n\n" + "\n\n".join(cards)
    except Exception as e:
        result = f"⚠️ Search error: {e}"
```
