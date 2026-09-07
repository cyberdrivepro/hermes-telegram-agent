---
name: hyperframes_cli
title: "HyperFrames Motion CLI Runner"
description: "Executes HyperFrames npx commands to compile programmatic video motion templates."
triggers: ["hyperframes", "hyperframes_cli", "motion_graphics"]
author: "@heygen-com"
---

# HyperFrames Motion CLI Runner

## Description
Executes HyperFrames npx commands to compile programmatic video motion templates.

## Workflow & Instructions
Constructs npx hyperframes CLI command for rendering video templates.

## Executable Implementation
```python
def execute(template):
    return {'skill': 'hyperframes_cli', 'cmd': f'npx hyperframes render --template {template}'}
```
