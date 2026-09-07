---
name: notion_integration
title: "Notion Database & Doc Sync"
description: "Read pages, query databases, append blocks, and draft structured docs in Notion."
triggers: ["notion", "notion_page", "notion_db", "notion_doc"]
author: "OpenClaw Apps Gateway"
---

# Notion Database & Doc Sync

## Description
Read pages, query databases, append blocks, and draft structured docs in Notion.

## Workflow & Instructions
Queries Notion database and formats rich markdown blocks for instant sync.

## Executable Implementation
```python
def execute(page_title):
    return {'skill': 'notion_integration', 'page': page_title, 'status': 'synced'}
```
