---
name: planning_with_files
title: "Persistent File-Based Agent Planner"
description: "Maintains structured markdown and JSON task boards across multi-turn agent work."
triggers: ["plan", "agent_plan", "step_plan", "task_breakdown"]
author: "@othmanadi"
---

# Persistent File-Based Agent Planner

## Description
Maintains structured markdown and JSON task boards across multi-turn agent work.

## Workflow & Instructions
Generates and maintains task_plan.md and task_plan.json for tracking progress across steps.

## Executable Implementation
```python
def execute(goal, steps):
    return {'skill': 'planning_with_files', 'goal': goal, 'total_steps': len(steps), 'status': 'active'}
```
