---
name: grill_me
title: "Socratic Grill-Me Spec Interviewer"
description: "Relentlessly questions the user on architectural decisions and edge cases until fully aligned."
triggers: ["grill", "grilling", "grill_me", "interview_user"]
author: "@mattpocock"
---

# Socratic Grill-Me Spec Interviewer

## Description
Relentlessly questions the user on architectural decisions and edge cases until fully aligned.

## Workflow & Instructions
Presents 3 pointed Socratic questions to probe assumptions and resolve architectural trade-offs.

## Executable Implementation
```python
def execute(topic):
    return {'skill': 'grill_me', 'topic': topic, 'status': 'interview_initiated'}
```
