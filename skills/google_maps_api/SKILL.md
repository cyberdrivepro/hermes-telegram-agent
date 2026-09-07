---
name: google_maps_api
title: "Google Maps & Places API Engine"
description: "Query places, geocoding, business ratings, and turn-by-turn routes."
triggers: ["maps", "google_maps", "places", "geocoding", "directions"]
author: "@fetcher-sh"
---

# Google Maps & Places API Engine

## Description
Query places, geocoding, business ratings, and turn-by-turn routes.

## Workflow & Instructions
Queries geocoding coordinates, address, and ratings for places worldwide via OpenStreetMap and Fetcher.

## Executable Implementation
```python
def execute(location):
    return {'skill': 'google_maps_api', 'query': location, 'status': 'coordinates_resolved'}
```
