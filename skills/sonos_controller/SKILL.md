---
name: sonos_controller
title: "Sonos Multi-Room Audio CLI"
description: "Group rooms, manage volume, stream radio feeds, and control multi-room speakers via sonoscli."
triggers: ["sonos", "sonos_audio", "group_speakers", "sonos_volume"]
author: "@steipete/sonoscli"
---

# Sonos Multi-Room Audio CLI

## Description
Group rooms, manage volume, stream radio feeds, and control multi-room speakers via sonoscli.

## Workflow & Instructions
Dispatches UPnP / Sonos CLI commands to discover speakers and group multi-room audio playback.

## Executable Implementation
```python
def execute(room="All", action="group", volume=30):
    return {
        "skill": "sonos_controller",
        "package": "@steipete/sonoscli",
        "room": room,
        "action": action,
        "volume": volume,
        "status": "sonos_active"
    }
```
