---
name: tavily_search
title: "Tavily Real-Time Web Search"
description: "Executes real-time AI-augmented web searches using Tavily Search API with direct answer synthesis."
triggers: ["tavily", "search", "google", "web_search", "lookup", "current_events"]
author: "Tavily Agent Setup (Official SKILL.md)"
created_at: "2026-09-07 12:40:00 UTC"
---

# Tavily Real-Time Web Search

## Description
Executes real-time AI-augmented web searches using Tavily Search API with direct answer synthesis.

## Workflow & Instructions
1. Extract search query from user request.
2. Query Tavily API endpoint `/search` with `api_key` and `include_answer=True`.
3. Return synthesized direct answer along with top verified source URLs.

## Executable Implementation
```python
from tavily_engine import TavilyEngine
engine = TavilyEngine()
q = params.get("query", "current AI technology news")
res = engine.search(q, search_depth="basic", max_results=5, include_answer=True)
if res.get("success"):
    ans = res.get("answer", "")
    sources = "\n".join([f"• [{r['title']}]({r['url']})" for r in res.get("results", [])[:4]])
    result = f"🌐 **Tavily AI Search Answer:**\n{ans}\n\n📚 **Sources:**\n{sources}" if ans else f"🌐 **Tavily Sources:**\n{sources}"
else:
    result = f"⚠️ Tavily Search Error: {res.get('error')}"
```
