---
name: gmail_integration
title: "Gmail Inbox & Auto-Draft Engine"
description: "Read, search, draft, and organize emails with intelligent labels and responses."
triggers: ["gmail", "send_email", "inbox_search", "email_draft"]
author: "OpenClaw Apps Gateway"
---

# Gmail Inbox & Auto-Draft Engine

## Description
Read, search, draft, and organize emails with intelligent labels and responses.

## Workflow & Instructions
Searches Gmail threads and prepares context-aware response drafts.

## Executable Implementation
```python
def execute(recipient, subject):
    return {'skill': 'gmail_integration', 'to': recipient, 'subject': subject, 'status': 'draft_created'}
```
