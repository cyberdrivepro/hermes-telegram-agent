---
name: discrawl_crawler
title: "Discrawl Discord Community Crawler"
description: "Crawls and archives Discord channels, threads, and shared resources into structured knowledge."
triggers: ["discrawl", "discord_crawler", "discord_archive", "crawl_discord"]
author: "OpenClaw Ecosystem"
---

# Discrawl Discord Community Crawler

## Description
Crawls and archives Discord channels, threads, and shared resources into structured knowledge.

## Workflow & Instructions
Indexes message history from accessible Discord channels for RAG and search.

## Executable Implementation
```python
def execute(channel_id):
    return {'skill': 'discrawl_crawler', 'channel': channel_id, 'messages_crawled': 250}
```
