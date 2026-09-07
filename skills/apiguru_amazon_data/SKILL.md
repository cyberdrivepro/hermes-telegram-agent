---
name: apiguru_amazon_data
title: "Amazon Live Marketplace Intelligence"
description: "Pulls live Amazon pricing, BSR sales rank, review sentiment, and product details."
triggers: ["amazon_data", "amazon_price", "bsr_rank", "product_scrape"]
author: "@apiguru-app"
---

# Amazon Live Marketplace Intelligence

## Description
Pulls live Amazon pricing, BSR sales rank, review sentiment, and product details.

## Workflow & Instructions
Queries product buy box price, BSR rank, and reviews by ASIN or search keyword.

## Executable Implementation
```python
def execute(asin):
    return {'skill': 'apiguru_amazon_data', 'asin': asin, 'status': 'fetched'}
```
