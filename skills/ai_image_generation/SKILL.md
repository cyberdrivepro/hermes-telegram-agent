---
name: ai_image_generation
title: "AI Image Generation (11+ Models)"
description: "Generates cinematic photos, concept art, and logos across Flux, SDXL, and Pollinations."
triggers: ["generate_image", "ai_art", "flux_image", "draw_ai"]
author: "@genmedia-labs"
---

# AI Image Generation (11+ Models)

## Description
Generates cinematic photos, concept art, and logos across Flux, SDXL, and Pollinations.

## Workflow & Instructions
Pass user prompt into Pollinations / SDXL image generator pipeline with custom dimensions.

## Executable Implementation
```python
def execute(prompt, model='flux'):
    import urllib.parse
    url = f'https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model={model}&width=1024&height=1024&nologo=true'
    return {'skill': 'ai_image_generation', 'model': model, 'image_url': url}
```
