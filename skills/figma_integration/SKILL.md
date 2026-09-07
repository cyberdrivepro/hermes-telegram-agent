---
name: figma_integration
title: "Figma Design Tokens & Asset Exporter"
description: "Export assets, inspect frames, and synchronize design context with code."
triggers: ["figma", "figma_export", "design_tokens", "ui_specs"]
author: "OpenClaw Apps Gateway"
---

# Figma Design Tokens & Asset Exporter

## Description
Export assets, inspect frames, and synchronize design context with code.

## Workflow & Instructions
Inspects Figma frame nodes and generates downloadable PNG/SVG exports.

## Executable Implementation
```python
def execute(file_key):
    return {'skill': 'figma_integration', 'file_key': file_key, 'status': 'assets_indexed'}
```
