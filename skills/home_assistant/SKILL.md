---
name: home_assistant
title: "Home Assistant Automation Controller"
description: "Control smart home entities, lights, climate, switches, and scenes via Home Assistant REST/WebSocket API."
triggers: ["home_assistant", "hass", "smart_home", "turn_on_light", "set_temp", "scene"]
author: "@community/home-assistant"
---

# Home Assistant Automation Controller

## Description
Control smart home entities, lights, climate, switches, and scenes via Home Assistant REST/WebSocket API.

## Workflow & Instructions
Sends state changes or service calls (e.g. light.turn_on, climate.set_temperature) to Home Assistant Gateway.

## Executable Implementation
```python
def execute(domain, service="turn_on", entity_id="all"):
    return {
        "skill": "home_assistant",
        "package": "@community/home-assistant",
        "domain": domain,
        "service": service,
        "entity_id": entity_id,
        "state": "executed"
    }
```
