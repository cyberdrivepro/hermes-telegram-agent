---
name: crypto_market_tracker
title: "Crypto Market Live Tracker"
description: "Fetches live cryptocurrency prices, market caps, and 24h changes from CoinGecko."
triggers: ["crypto", "bitcoin", "btc", "eth", "ethereum", "solana", "sol", "token", "coin"]
author: "OpenClaw Autonomous Engine"
created_at: "2026-09-07 12:14:09 UTC"
---

# Crypto Market Live Tracker

## Description
Fetches live cryptocurrency prices, market caps, and 24h changes from CoinGecko.

## Workflow & Instructions
1. Identify the requested coin (e.g. bitcoin, ethereum, solana, cardano).
2. Query the CoinGecko public API endpoint `/simple/price?ids={coin}&vs_currencies=usd,inr&include_24hr_change=true`.
3. Format the current price in USD ($) and INR (Rs.) along with the 24-hour percentage change.

## Executable Implementation
```python
import urllib.request, json
coin_ids = params.get('coin', 'bitcoin,ethereum,solana').lower().replace(' ', '')
url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin_ids}&vs_currencies=usd,inr&include_24hr_change=true'
req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-Agent/1.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    data = json.loads(r.read().decode())
output = []
for c, vals in data.items():
    usd = vals.get('usd', 0)
    inr = vals.get('inr', 0)
    chg = vals.get('usd_24h_change', 0)
    arrow = '📈' if chg >= 0 else '📉'
    output.append(f"{arrow} **{c.upper()}**: ${usd:,} | ₹{inr:,} ({chg:+.2f}%)")
result = "\n".join(output) if output else "No data returned for specified crypto."
```