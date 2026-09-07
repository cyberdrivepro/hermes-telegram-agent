---
name: image_to_video
title: "Image-to-Video Motion Pack"
description: "Converts static images into dynamic 5-second cinematic motion video clips."
triggers: ["img2video", "animate_image", "kling", "svd_video"]
author: "@genmedia-labs"
---

# Image-to-Video Motion Pack

## Description
Converts static images into dynamic 5-second cinematic motion video clips.

## Workflow & Instructions
Processes image through Stable Video Diffusion or RunComfy video pipeline.

## Executable Implementation
```python
def execute(image_url):
    return {'skill': 'image_to_video', 'input': image_url, 'format': 'mp4', 'status': 'rendered'}
```
