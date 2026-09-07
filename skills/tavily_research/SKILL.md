---
name: tavily_research
title: "Tavily Multi-Source Deep Research"
description: "Conducts multi-source cited deep research and synthesizes an executive briefing report on any topic."
triggers: ["tavily_research", "deep_research", "investigate", "research_report", "briefing"]
author: "Tavily Agent Setup (Official SKILL.md)"
created_at: "2026-09-07 12:40:00 UTC"
---

# Tavily Multi-Source Deep Research

## Description
Conducts multi-source cited deep research and synthesizes an executive briefing report on any topic.

## Workflow & Instructions
1. Accept research subject or topic from user.
2. Trigger advanced Tavily search with deep multi-source queries.
3. Collate verified facts, synthesized insights, and citations.

## Executable Implementation
```python
from tavily_engine import TavilyEngine
engine = TavilyEngine()
topic = params.get("topic", "Latest advancements in autonomous AI agents")
result = engine.research(topic)
```
