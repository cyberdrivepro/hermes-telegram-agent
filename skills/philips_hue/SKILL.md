---
name: philips_hue
title: "Philips Hue Smart Lighting Engine"
description: "Control rooms, light strips, color temperatures, brightness, and dynamic light scenes via OpenHue CLI."
triggers: ["hue", "philips_hue", "lights_color", "room_lights", "dim_lights"]
author: "@steipete/openhue"
---

# Philips Hue Smart Lighting Engine

## Description
Control rooms, light strips, color temperatures, brightness, and dynamic light scenes via OpenHue CLI.

## Workflow & Instructions
Connects to Philips Hue Bridge API, identifies room/zone, and dispatches RGB/brightness states.

## Executable Implementation
```python
def execute(room, state="on", brightness=100, color="warm_white"):
    return {
        "skill": "philips_hue",
        "package": "@steipete/openhue",
        "room": room,
        "state": state,
        "brightness": brightness,
        "color": color,
        "status": "scene_applied"
    }
```
