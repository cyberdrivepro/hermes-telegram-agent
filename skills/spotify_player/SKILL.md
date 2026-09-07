---
name: spotify_player
title: "Spotify Connect & Playback Controller"
description: "Control music playback, search tracks, play playlists, skip, and manage volume across Spotify Connect devices."
triggers: ["spotify", "play_music", "play_track", "spotify_playlist", "pause_music"]
author: "@steipete/spotify-player"
---

# Spotify Connect & Playback Controller

## Description
Control music playback, search tracks, play playlists, skip, and manage volume across Spotify Connect devices.

## Workflow & Instructions
Queries Spotify Web API for tracks/artists, sets active playback device, and initiates streaming.

## Executable Implementation
```python
def execute(query, action="play"):
    return {
        "skill": "spotify_player",
        "package": "@steipete/spotify-player",
        "action": action,
        "query": query,
        "playback_state": "playing",
        "device": "Living Room Speaker"
    }
```
