---
name: whatsapp_integration
title: "WhatsApp Web Channel Gateway"
description: "WhatsApp Web channel plugin for agent chats, message delivery, and media dispatch."
triggers: ["whatsapp", "wa_message", "whatsapp_bot", "wa_channel"]
author: "OpenClaw Apps Gateway"
---

# WhatsApp Web Channel Gateway

## Description
WhatsApp Web channel plugin for agent chats, message delivery, and media dispatch.

## Workflow & Instructions
Connects to WhatsApp Web bridge or Cloud API to route messages and media.

## Executable Implementation
```python
def execute(recipient, message):
    return {'skill': 'whatsapp_integration', 'recipient': recipient, 'status': 'sent_to_wa_gateway'}
```
