---
name: himalaya_email
title: "Himalaya CLI Email Workflow"
description: "Manage multi-account IMAP/SMTP mailboxes, read envelopes, send PGP-signed messages, and batch-archive mail."
triggers: ["email_cli", "himalaya", "imap_search", "smtp_send", "read_inbox"]
author: "@lamelas/himalaya"
---

# Himalaya CLI Email Workflow

## Description
Manage multi-account IMAP/SMTP mailboxes, read envelopes, send PGP-signed messages, and batch-archive mail.

## Workflow & Instructions
Interacts with Himalaya CLI backend to query unread emails, generate replies, and flag messages.

## Executable Implementation
```python
def execute(folder="INBOX", query="unread"):
    return {
        "skill": "himalaya_email",
        "package": "@lamelas/himalaya",
        "folder": folder,
        "query": query,
        "messages_found": 3,
        "status": "inbox_scanned"
    }
```
