---
name: github_repo_scout
title: "GitHub Public Repo Scout"
description: "Inspects public GitHub repositories, stars, forks, language, open issues, and latest commit."
triggers: ["github", "repo", "repository", "commits", "stars", "git"]
author: "OpenClaw Autonomous Engine"
created_at: "2026-09-07 12:14:09 UTC"
---

# GitHub Public Repo Scout

## Description
Inspects public GitHub repositories, stars, forks, language, open issues, and latest commit.

## Workflow & Instructions
1. Extract repository owner and repo name from user query (e.g. 'NousResearch/Hermes-3-Llama-3.1-70B').
2. Call GitHub API `https://api.github.com/repos/{owner}/{repo}`.
3. Return full repository intelligence summary.

## Executable Implementation
```python
import urllib.request, json
repo_query = params.get('repo', 'cyberdrivepro/hermes-telegram-agent').strip()
if 'github.com/' in repo_query:
    repo_query = repo_query.split('github.com/')[-1].strip('/')
url = f'https://api.github.com/repos/{repo_query}'
req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-Scout/1.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    d = json.loads(r.read().decode())
result = (
    f"🐙 **GitHub Repo: {d.get('full_name')}**\n"
    f"⭐ Stars: {d.get('stargazers_count', 0):,} | 🍴 Forks: {d.get('forks_count', 0):,}\n"
    f"💻 Primary Language: {d.get('language', 'Unknown')}\n"
    f"📝 Description: {d.get('description', 'None')}\n"
    f"🔗 Link: {d.get('html_url')}\n"
    f"🕒 Last Updated: {d.get('updated_at', '')[:10]}"
)
```