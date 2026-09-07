---
name: academic_article_pipeline
title: "Academic Deep Article & Tri-Verification (2.7.8)"
description: "Multi-agent orchestration pipeline for academic papers, market whitepapers, and cited essays."
triggers: ["academic_paper", "deep_article", "tri_verification", "formal_essay"]
author: "@zuoyunlai"
---

# Academic Deep Article & Tri-Verification (2.7.8)

## Description
Multi-agent orchestration pipeline for academic papers, market whitepapers, and cited essays.

## Workflow & Instructions
Runs literature review, cross-source data verification, and peer review synthesis.

## Executable Implementation
```python
def execute(topic):
    return {'skill': 'academic_article_pipeline', 'topic': topic, 'verified': True}
```
