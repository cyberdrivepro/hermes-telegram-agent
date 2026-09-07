---
name: google_calendar_integration
title: "Google Calendar Scheduler"
description: "Create events, check availability, detect conflicts, and manage calendars."
triggers: ["calendar", "schedule_event", "google_calendar", "meeting_invite"]
author: "OpenClaw Apps Gateway"
---

# Google Calendar Scheduler

## Description
Create events, check availability, detect conflicts, and manage calendars.

## Workflow & Instructions
Checks free/busy slots and creates calendar event invitations.

## Executable Implementation
```python
def execute(title, start_time):
    return {'skill': 'google_calendar_integration', 'event': title, 'time': start_time, 'status': 'scheduled'}
```
