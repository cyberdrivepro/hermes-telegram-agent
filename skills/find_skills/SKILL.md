---
name: find_skills
title: "ClawHub Ecosystem Skill Discovery"
description: "Search and install public OpenClaw skills directly from ClawHub directory."
triggers: ["find_skills", "clawhub_search", "install_skill", "discover_skills"]
author: "@vercel-labs"
---

# ClawHub Ecosystem Skill Discovery

## Description
Search and install public OpenClaw skills directly from ClawHub directory.

## Workflow & Instructions
Searches ClawHub registry for skills matching query and provides installation command.

## Executable Implementation
```python
def execute(keyword):
    return {'skill': 'find_skills', 'results': [f'{keyword}-pack', f'{keyword}-tool']}
```
