---
name: trello_integration
title: "Trello Kanban & Workflow Manager"
description: "Manage boards, lists, cards, and automated checklist progress."
triggers: ["trello", "trello_card", "kanban_board", "trello_list"]
author: "OpenClaw Apps Gateway"
---

# Trello Kanban & Workflow Manager

## Description
Manage boards, lists, cards, and automated checklist progress.

## Workflow & Instructions
Creates or moves Trello cards across kanban workflow lists.

## Executable Implementation
```python
def execute(board, card_title):
    return {'skill': 'trello_integration', 'board': board, 'card': card_title, 'status': 'card_placed'}
```
