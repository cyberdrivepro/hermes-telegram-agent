---
name: hyperliquid_place
title: "Hyperliquid Perpetual DEX Trader"
description: "Places, cancels, and audits decentralized perpetual futures orders on Hyperliquid L1."
triggers: ["hyperliquid", "hl_trade", "perp_order", "crypto_leverage"]
author: "@polyparlay"
---

# Hyperliquid Perpetual DEX Trader

## Description
Places, cancels, and audits decentralized perpetual futures orders on Hyperliquid L1.

## Workflow & Instructions
Dispatches signed perpetual futures order to Hyperliquid API.

## Executable Implementation
```python
def execute(action, pair='BTC-USD', size=0.01):
    return {'skill': 'hyperliquid_place', 'action': action, 'pair': pair, 'size': size}
```
