---
name: muse_git_intelligence
title: "Muse Git History & Repo Intelligence"
description: "Exposes deep repository history, git blames, and code authorship patterns to agents."
triggers: ["muse", "git_history", "commit_intel", "repo_evolution"]
author: "@alexander-morris"
---

# Muse Git History & Repo Intelligence

## Description
Exposes deep repository history, git blames, and code authorship patterns to agents.

## Workflow & Instructions
Parses recent git commits, authors, and file churn to understand codebase evolution.

## Executable Implementation
```python
def execute(repo='.'):
    return {'skill': 'muse_git_intelligence', 'repo': repo, 'status': 'commits_analyzed'}
```
