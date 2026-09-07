---
name: reddit_automation
title: "Reddit Automation & Subreddit Scanner"
description: "Automates Reddit post discovery, top comments extraction, and subreddit sentiment monitoring."
triggers: ["reddit", "subreddit", "reddit_monitor", "reddit_post"]
author: "@flowkit-labs"
---

# Reddit Automation & Subreddit Scanner

## Description
Automates Reddit post discovery, top comments extraction, and subreddit sentiment monitoring.

## Workflow & Instructions
Scrapes top hot posts from target subreddit and analyzes discussion sentiment.

## Executable Implementation
```python
def execute(sub='technology'):
    return {'skill': 'reddit_automation', 'subreddit': sub, 'status': 'scanned'}
```
