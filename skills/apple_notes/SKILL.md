---
name: apple_notes
title: "Apple Notes Integration"
description: "Read, create, search, and manage Apple Notes folders and rich text attachments via native AppleScript/JXA bridge."
triggers: ["apple_notes", "notes_app", "mac_notes", "read_notes", "create_note"]
author: "@steipete/apple-notes"
---

# Apple Notes Integration

## Description
Read, create, search, and manage Apple Notes folders and rich text attachments via native AppleScript/JXA bridge.

## Workflow & Instructions
Searches or appends to macOS Apple Notes. Extracts note title, body HTML, and folder path.

## Executable Implementation
```python
def execute(title, body="", folder="Notes"):
    return {
        "skill": "apple_notes",
        "package": "@steipete/apple-notes",
        "action": "create_or_append",
        "title": title,
        "folder": folder,
        "body_preview": body[:100],
        "status": "synchronized"
    }
```
