---
name: universal_webhook_relay
title: "Universal Webhook Relay"
description: "Dispatches formatted event payloads to external automations like n8n, Zapier, Make, Slack, or Discord."
triggers: ["webhook", "n8n", "zapier", "make", "slack", "discord", "payload", "relay"]
author: "OpenClaw Autonomous Engine"
created_at: "2026-09-07 12:14:09 UTC"
---

# Universal Webhook Relay

## Description
Dispatches formatted event payloads to external automations like n8n, Zapier, Make, Slack, or Discord.

## Workflow & Instructions
1. Collect the target webhook URL and JSON payload.
2. Execute HTTP POST request with Content-Type application/json.
3. Return HTTP delivery status code and server response.

## Executable Implementation
```python
import urllib.request, json
url = params.get('url', 'https://httpbin.org/post')
payload = params.get('payload', {'event': 'openclaw_relay', 'timestamp': str(time.time())})
data_bytes = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json', 'User-Agent': 'OpenClaw/1.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    status = r.status
    body = r.read().decode('utf-8', errors='ignore')[:300]
result = f"✅ Webhook delivered successfully! HTTP Status: {status}\nResponse snippet: {body}"
```