---
name: self_improving_agent
title: "Autonomous Self-Improving Learning Engine"
description: "Captures user feedback, corrections, and execution errors to upgrade responses continuously."
triggers: ["self_learning", "learn_correction", "auto_improve", "error_learning"]
author: "@pskoett"
---

# Autonomous Self-Improving Learning Engine

## Description
Captures user feedback, corrections, and execution errors to upgrade responses continuously.

## Workflow & Instructions
Extracts preferences and corrections, saving them to persistent memory for system prompt injection.

## Executable Implementation
```python
def execute(feedback):
    return {'skill': 'self_improving_agent', 'learning': feedback, 'status': 'memorized'}
```
