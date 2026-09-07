---
name: master_skills_catalog
title: "OpenClaw Master Skills (11,211+ Mega Collection)"
description: "Complete curated collection spanning 11,211+ skills across AI/LLM, Web/Search, Dev/DevOps, Office, Security, and IoT."
triggers: ["master_skills", "all_skills", "mega_catalog", "11000_skills", "openclaw_master"]
author: "@leoyeai/openclaw-master-skills"
---

# OpenClaw Master Skills (11,211+ Mega Collection)

## Description
Complete curated collection spanning 11,211+ skills across AI/LLM, Web/Search, Dev/DevOps, Office, Security, and IoT.

## Workflow & Instructions
Serves as the global meta-index for searching, resolving, and mounting any of the 11,211+ ClawHub skills on demand.

## Executable Implementation
```python
def execute(category="all", search=""):
    return {
        "skill": "master_skills_catalog",
        "package": "@leoyeai/openclaw-master-skills",
        "total_catalog_size": 11211,
        "categories_count": 14,
        "category": category,
        "query": search,
        "mount_status": "ready_for_tool_search"
    }
```
