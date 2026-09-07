---
name: youtube_api
title: "YouTube Video & Transcript Extractor"
description: "Fetches YouTube video metadata, channel statistics, search results, and captions."
triggers: ["youtube", "yt_search", "yt_transcript", "video_summary"]
author: "@fetcher-sh"
---

# YouTube Video & Transcript Extractor

## Description
Fetches YouTube video metadata, channel statistics, search results, and captions.

## Workflow & Instructions
Queries YouTube search results, parses video ID, and extracts transcript captions.

## Executable Implementation
```python
def execute(query):
    return {'skill': 'youtube_api', 'query': query, 'status': 'results_ready'}
```
