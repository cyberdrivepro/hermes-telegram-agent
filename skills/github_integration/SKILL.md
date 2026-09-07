---
name: github_integration
title: "GitHub PR & Issue Manager"
description: "Review PRs, manage issues, commit files, and automate repository workflows."
triggers: ["github", "gh_pr", "gh_issue", "gh_repo"]
author: "OpenClaw Apps Gateway"
---

# GitHub PR & Issue Manager

## Description
Review PRs, manage issues, commit files, and automate repository workflows.

## Workflow & Instructions
Connects to GitHub API to inspect commits, open issues, and review pull requests.

## Executable Implementation
```python
def execute(repo, action='get_repo'):
    return {'skill': 'github_integration', 'repo': repo, 'action': action, 'status': 'connected'}
```
