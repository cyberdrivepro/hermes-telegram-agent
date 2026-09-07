---
name: tavily_extract
title: "Tavily Clean Web Content Extractor"
description: "Extracts clean, readable markdown content from any URL bypassing paywalls, bot blockers, and ads."
triggers: ["tavily_extract", "extract_url", "scrape_clean", "read_page", "extract"]
author: "Tavily Agent Setup (Official SKILL.md)"
created_at: "2026-09-07 12:40:00 UTC"
---

# Tavily Clean Web Content Extractor

## Description
Extracts clean, readable markdown content from any URL bypassing paywalls, bot blockers, and ads.

## Workflow & Instructions
1. Collect the target URL or URLs to extract.
2. Call Tavily `/extract` endpoint.
3. Return cleaned textual content formatted in clean markdown.

## Executable Implementation
```python
from tavily_engine import TavilyEngine
engine = TavilyEngine()
url = params.get("url", "")
if not url:
    result = "Error: No URL provided for extraction."
else:
    res = engine.extract([url])
    if res.get("success") and res.get("results"):
        raw_text = res["results"][0].get("raw_content", "")[:2500]
        result = f"📑 **Extracted Content from {url}:**\n\n{raw_text}"
    else:
        result = f"⚠️ Tavily Extraction Error: {res.get('error', 'No content returned')}"
```
