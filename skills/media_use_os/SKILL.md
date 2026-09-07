---
name: media_use_os
title: "Media Operating System for Agents"
description: "The media operating system for OpenClaw: resolve, generate, mix, and operate multimedia pipelines."
triggers: ["media_use", "media_os", "asset_pipeline", "video_orchestration"]
author: "@heygen-com"
---

# Media Operating System for Agents

## Description
The media operating system for OpenClaw: resolve, generate, mix, and operate multimedia pipelines.

## Workflow & Instructions
Coordinates audio, image, and video generators into unified multimodal productions.

## Executable Implementation
```python
def execute(action, asset):
    return {'skill': 'media_use_os', 'action': action, 'asset': asset}
```
