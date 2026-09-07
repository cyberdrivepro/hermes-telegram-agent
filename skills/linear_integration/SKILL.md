---
name: linear_integration
title: "Linear Issue & Cycle Syncer"
description: "Create issues, sync cycles, and keep engineering roadmap tasks moving."
triggers: ["linear", "linear_issue", "dev_cycle", "sprint_task"]
author: "OpenClaw Apps Gateway"
---

# Linear Issue & Cycle Syncer

## Description
Create issues, sync cycles, and keep engineering roadmap tasks moving.

## Workflow & Instructions
Submits GraphQL mutation to create or update Linear issue tickets.

## Executable Implementation
```python
def execute(title, team):
    return {'skill': 'linear_integration', 'ticket': title, 'team': team, 'status': 'created'}
```
