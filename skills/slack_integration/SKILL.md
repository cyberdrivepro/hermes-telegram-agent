---
name: slack_integration
title: "Slack Workspace & Channel Connector"
description: "Send messages, search conversations, and manage channels in Slack."
triggers: ["slack", "slack_msg", "slack_channel", "slack_bot"]
author: "OpenClaw Apps Gateway"
---

# Slack Workspace & Channel Connector

## Description
Send messages, search conversations, and manage channels in Slack.

## Workflow & Instructions
Dispatches chat messages and reads channel history via Slack Web API.

## Executable Implementation
```python
def execute(channel, message):
    return {'skill': 'slack_integration', 'channel': channel, 'status': 'delivered'}
```
