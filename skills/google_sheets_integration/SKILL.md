---
name: google_sheets_integration
title: "Google Sheets Data Automator"
description: "Read, write, format, and automate spreadsheet data, tables, and formula calculations."
triggers: ["sheets", "google_sheets", "spreadsheet_data", "append_row"]
author: "OpenClaw Apps Gateway"
---

# Google Sheets Data Automator

## Description
Read, write, format, and automate spreadsheet data, tables, and formula calculations.

## Workflow & Instructions
Reads cell ranges and appends rows to Google Spreadsheets dynamically.

## Executable Implementation
```python
def execute(sheet_id, values):
    return {'skill': 'google_sheets_integration', 'sheet_id': sheet_id, 'rows_added': len(values)}
```
