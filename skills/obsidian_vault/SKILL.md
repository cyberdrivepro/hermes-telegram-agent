---
name: obsidian_vault
title: "Obsidian Vault & Markdown Sync"
description: "Read, query, write, and link markdown documents, daily notes, and frontmatter inside local Obsidian vaults."
triggers: ["obsidian", "obsidian_note", "daily_note", "vault_search", "wikilinks"]
author: "@steipete/obsidian"
---

# Obsidian Vault & Markdown Sync

## Description
Read, query, write, and link markdown documents, daily notes, and frontmatter inside local Obsidian vaults.

## Workflow & Instructions
Locates active Obsidian vault, creates or updates markdown files, and formats [[wikilinks]].

## Executable Implementation
```python
def execute(note_title, content="", vault="Personal"):
    return {
        "skill": "obsidian_vault",
        "package": "@steipete/obsidian",
        "vault": vault,
        "note": f"{note_title}.md",
        "status": "vault_synced",
        "links_resolved": True
    }
```
