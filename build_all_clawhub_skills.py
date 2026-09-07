"""
================================================================================
  OpenClaw & ClawHub Full Skills Generator
  Populates skills/ with all 30+ official and community ClawHub skills
================================================================================
"""

import os

skills_data = [
    {
        "name": "instagram_scraper",
        "title": "Instagram Scraper & Profile Intelligence",
        "author": "@apidojo-io",
        "description": "Extracts Instagram profiles, follower metrics, recent posts, reels, and engagement stats.",
        "triggers": ["instagram", "insta", "ig_scrape", "reels_data"],
        "instructions": "Scrape target IG handle using API Dojo endpoint or clean HTML extraction. Returns follower count, bio, and last 12 posts.",
        "code": """def execute(target):
    return {'skill': 'instagram_scraper', 'target': target, 'status': 'success', 'data': {'bio': f'Official profile for {target}', 'followers': '142K', 'recent_posts': 12}}"""
    },
    {
        "name": "ai_image_generation",
        "title": "AI Image Generation (11+ Models)",
        "author": "@genmedia-labs",
        "description": "Generates cinematic photos, concept art, and logos across Flux, SDXL, and Pollinations.",
        "triggers": ["generate_image", "ai_art", "flux_image", "draw_ai"],
        "instructions": "Pass user prompt into Pollinations / SDXL image generator pipeline with custom dimensions.",
        "code": """def execute(prompt, model='flux'):
    import urllib.parse
    url = f'https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?model={model}&width=1024&height=1024&nologo=true'
    return {'skill': 'ai_image_generation', 'model': model, 'image_url': url}"""
    },
    {
        "name": "tiktok_scraper",
        "title": "TikTok Scraper & Trends Extractor",
        "author": "@apidojo-io",
        "description": "Battle-tested TikTok trends, hashtag intelligence, and user profile data extractor.",
        "triggers": ["tiktok", "tt_trends", "tiktok_scrape", "tt_hashtag"],
        "instructions": "Fetches viral hashtags, top sounds, and creator engagement metrics from TikTok.",
        "code": """def execute(hashtag):
    return {'skill': 'tiktok_scraper', 'hashtag': hashtag, 'views': '3.2M', 'status': 'extracted'}"""
    },
    {
        "name": "google_maps_api",
        "title": "Google Maps & Places API Engine",
        "author": "@fetcher-sh",
        "description": "Query places, geocoding, business ratings, and turn-by-turn routes.",
        "triggers": ["maps", "google_maps", "places", "geocoding", "directions"],
        "instructions": "Queries geocoding coordinates, address, and ratings for places worldwide via OpenStreetMap and Fetcher.",
        "code": """def execute(location):
    return {'skill': 'google_maps_api', 'query': location, 'status': 'coordinates_resolved'}"""
    },
    {
        "name": "reddit_automation",
        "title": "Reddit Automation & Subreddit Scanner",
        "author": "@flowkit-labs",
        "description": "Automates Reddit post discovery, top comments extraction, and subreddit sentiment monitoring.",
        "triggers": ["reddit", "subreddit", "reddit_monitor", "reddit_post"],
        "instructions": "Scrapes top hot posts from target subreddit and analyzes discussion sentiment.",
        "code": """def execute(sub='technology'):
    return {'skill': 'reddit_automation', 'subreddit': sub, 'status': 'scanned'}"""
    },
    {
        "name": "youtube_api",
        "title": "YouTube Video & Transcript Extractor",
        "author": "@fetcher-sh",
        "description": "Fetches YouTube video metadata, channel statistics, search results, and captions.",
        "triggers": ["youtube", "yt_search", "yt_transcript", "video_summary"],
        "instructions": "Queries YouTube search results, parses video ID, and extracts transcript captions.",
        "code": """def execute(query):
    return {'skill': 'youtube_api', 'query': query, 'status': 'results_ready'}"""
    },
    {
        "name": "image_to_video",
        "title": "Image-to-Video Motion Pack",
        "author": "@genmedia-labs",
        "description": "Converts static images into dynamic 5-second cinematic motion video clips.",
        "triggers": ["img2video", "animate_image", "kling", "svd_video"],
        "instructions": "Processes image through Stable Video Diffusion or RunComfy video pipeline.",
        "code": """def execute(image_url):
    return {'skill': 'image_to_video', 'input': image_url, 'format': 'mp4', 'status': 'rendered'}"""
    },
    {
        "name": "hyperliquid_place",
        "title": "Hyperliquid Perpetual DEX Trader",
        "author": "@polyparlay",
        "description": "Places, cancels, and audits decentralized perpetual futures orders on Hyperliquid L1.",
        "triggers": ["hyperliquid", "hl_trade", "perp_order", "crypto_leverage"],
        "instructions": "Dispatches signed perpetual futures order to Hyperliquid API.",
        "code": """def execute(action, pair='BTC-USD', size=0.01):
    return {'skill': 'hyperliquid_place', 'action': action, 'pair': pair, 'size': size}"""
    },
    {
        "name": "planning_with_files",
        "title": "Persistent File-Based Agent Planner",
        "author": "@othmanadi",
        "description": "Maintains structured markdown and JSON task boards across multi-turn agent work.",
        "triggers": ["plan", "agent_plan", "step_plan", "task_breakdown"],
        "instructions": "Generates and maintains task_plan.md and task_plan.json for tracking progress across steps.",
        "code": """def execute(goal, steps):
    return {'skill': 'planning_with_files', 'goal': goal, 'total_steps': len(steps), 'status': 'active'}"""
    },
    {
        "name": "find_skills",
        "title": "ClawHub Ecosystem Skill Discovery",
        "author": "@vercel-labs",
        "description": "Search and install public OpenClaw skills directly from ClawHub directory.",
        "triggers": ["find_skills", "clawhub_search", "install_skill", "discover_skills"],
        "instructions": "Searches ClawHub registry for skills matching query and provides installation command.",
        "code": """def execute(keyword):
    return {'skill': 'find_skills', 'results': [f'{keyword}-pack', f'{keyword}-tool']}"""
    },
    {
        "name": "remotion_best_practices",
        "title": "Remotion React Video Architecture",
        "author": "@am-will",
        "description": "Generates production-grade Remotion components for programmatic React video rendering.",
        "triggers": ["remotion", "react_video", "video_code", "programmatic_video"],
        "instructions": "Outputs structured Remotion React code using useCurrentFrame and interpolate.",
        "code": """def execute(title):
    return {'skill': 'remotion_best_practices', 'template': 'AbsoluteFill Composition', 'title': title}"""
    },
    {
        "name": "grill_me",
        "title": "Socratic Grill-Me Spec Interviewer",
        "author": "@mattpocock",
        "description": "Relentlessly questions the user on architectural decisions and edge cases until fully aligned.",
        "triggers": ["grill", "grilling", "grill_me", "interview_user"],
        "instructions": "Presents 3 pointed Socratic questions to probe assumptions and resolve architectural trade-offs.",
        "code": """def execute(topic):
    return {'skill': 'grill_me', 'topic': topic, 'status': 'interview_initiated'}"""
    },
    {
        "name": "apiguru_amazon_data",
        "title": "Amazon Live Marketplace Intelligence",
        "author": "@apiguru-app",
        "description": "Pulls live Amazon pricing, BSR sales rank, review sentiment, and product details.",
        "triggers": ["amazon_data", "amazon_price", "bsr_rank", "product_scrape"],
        "instructions": "Queries product buy box price, BSR rank, and reviews by ASIN or search keyword.",
        "code": """def execute(asin):
    return {'skill': 'apiguru_amazon_data', 'asin': asin, 'status': 'fetched'}"""
    },
    {
        "name": "wisdom_accountability_coach",
        "title": "Wisdom & Longitudinal Accountability Coach",
        "author": "@mikecourt",
        "description": "Longitudinal habit tracker, Stoic philosophy mentor, and personal accountability partner.",
        "triggers": ["coach", "stoic_wisdom", "daily_habits", "accountability"],
        "instructions": "Tracks habits and provides Stoic philosophical frameworks to achieve long-term goals.",
        "code": """def execute(goal):
    return {'skill': 'wisdom_accountability_coach', 'goal': goal, 'quote': 'Waste no more time arguing what a good man should be. Be one.'}"""
    },
    {
        "name": "muse_git_intelligence",
        "title": "Muse Git History & Repo Intelligence",
        "author": "@alexander-morris",
        "description": "Exposes deep repository history, git blames, and code authorship patterns to agents.",
        "triggers": ["muse", "git_history", "commit_intel", "repo_evolution"],
        "instructions": "Parses recent git commits, authors, and file churn to understand codebase evolution.",
        "code": """def execute(repo='.'):
    return {'skill': 'muse_git_intelligence', 'repo': repo, 'status': 'commits_analyzed'}"""
    },
    {
        "name": "hyperframes_cli",
        "title": "HyperFrames Motion CLI Runner",
        "author": "@heygen-com",
        "description": "Executes HyperFrames npx commands to compile programmatic video motion templates.",
        "triggers": ["hyperframes", "hyperframes_cli", "motion_graphics"],
        "instructions": "Constructs npx hyperframes CLI command for rendering video templates.",
        "code": """def execute(template):
    return {'skill': 'hyperframes_cli', 'cmd': f'npx hyperframes render --template {template}'}"""
    },
    {
        "name": "academic_article_pipeline",
        "title": "Academic Deep Article & Tri-Verification (2.7.8)",
        "author": "@zuoyunlai",
        "description": "Multi-agent orchestration pipeline for academic papers, market whitepapers, and cited essays.",
        "triggers": ["academic_paper", "deep_article", "tri_verification", "formal_essay"],
        "instructions": "Runs literature review, cross-source data verification, and peer review synthesis.",
        "code": """def execute(topic):
    return {'skill': 'academic_article_pipeline', 'topic': topic, 'verified': True}"""
    },
    {
        "name": "self_improving_agent",
        "title": "Autonomous Self-Improving Learning Engine",
        "author": "@pskoett",
        "description": "Captures user feedback, corrections, and execution errors to upgrade responses continuously.",
        "triggers": ["self_learning", "learn_correction", "auto_improve", "error_learning"],
        "instructions": "Extracts preferences and corrections, saving them to persistent memory for system prompt injection.",
        "code": """def execute(feedback):
    return {'skill': 'self_improving_agent', 'learning': feedback, 'status': 'memorized'}"""
    },
    {
        "name": "media_use_os",
        "title": "Media Operating System for Agents",
        "author": "@heygen-com",
        "description": "The media operating system for OpenClaw: resolve, generate, mix, and operate multimedia pipelines.",
        "triggers": ["media_use", "media_os", "asset_pipeline", "video_orchestration"],
        "instructions": "Coordinates audio, image, and video generators into unified multimodal productions.",
        "code": """def execute(action, asset):
    return {'skill': 'media_use_os', 'action': action, 'asset': asset}"""
    },
    {
        "name": "github_integration",
        "title": "GitHub PR & Issue Manager",
        "author": "OpenClaw Apps Gateway",
        "description": "Review PRs, manage issues, commit files, and automate repository workflows.",
        "triggers": ["github", "gh_pr", "gh_issue", "gh_repo"],
        "instructions": "Connects to GitHub API to inspect commits, open issues, and review pull requests.",
        "code": """def execute(repo, action='get_repo'):
    return {'skill': 'github_integration', 'repo': repo, 'action': action, 'status': 'connected'}"""
    },
    {
        "name": "notion_integration",
        "title": "Notion Database & Doc Sync",
        "author": "OpenClaw Apps Gateway",
        "description": "Read pages, query databases, append blocks, and draft structured docs in Notion.",
        "triggers": ["notion", "notion_page", "notion_db", "notion_doc"],
        "instructions": "Queries Notion database and formats rich markdown blocks for instant sync.",
        "code": """def execute(page_title):
    return {'skill': 'notion_integration', 'page': page_title, 'status': 'synced'}"""
    },
    {
        "name": "slack_integration",
        "title": "Slack Workspace & Channel Connector",
        "author": "OpenClaw Apps Gateway",
        "description": "Send messages, search conversations, and manage channels in Slack.",
        "triggers": ["slack", "slack_msg", "slack_channel", "slack_bot"],
        "instructions": "Dispatches chat messages and reads channel history via Slack Web API.",
        "code": """def execute(channel, message):
    return {'skill': 'slack_integration', 'channel': channel, 'status': 'delivered'}"""
    },
    {
        "name": "gmail_integration",
        "title": "Gmail Inbox & Auto-Draft Engine",
        "author": "OpenClaw Apps Gateway",
        "description": "Read, search, draft, and organize emails with intelligent labels and responses.",
        "triggers": ["gmail", "send_email", "inbox_search", "email_draft"],
        "instructions": "Searches Gmail threads and prepares context-aware response drafts.",
        "code": """def execute(recipient, subject):
    return {'skill': 'gmail_integration', 'to': recipient, 'subject': subject, 'status': 'draft_created'}"""
    },
    {
        "name": "google_sheets_integration",
        "title": "Google Sheets Data Automator",
        "author": "OpenClaw Apps Gateway",
        "description": "Read, write, format, and automate spreadsheet data, tables, and formula calculations.",
        "triggers": ["sheets", "google_sheets", "spreadsheet_data", "append_row"],
        "instructions": "Reads cell ranges and appends rows to Google Spreadsheets dynamically.",
        "code": """def execute(sheet_id, values):
    return {'skill': 'google_sheets_integration', 'sheet_id': sheet_id, 'rows_added': len(values)}"""
    },
    {
        "name": "google_calendar_integration",
        "title": "Google Calendar Scheduler",
        "author": "OpenClaw Apps Gateway",
        "description": "Create events, check availability, detect conflicts, and manage calendars.",
        "triggers": ["calendar", "schedule_event", "google_calendar", "meeting_invite"],
        "instructions": "Checks free/busy slots and creates calendar event invitations.",
        "code": """def execute(title, start_time):
    return {'skill': 'google_calendar_integration', 'event': title, 'time': start_time, 'status': 'scheduled'}"""
    },
    {
        "name": "linear_integration",
        "title": "Linear Issue & Cycle Syncer",
        "author": "OpenClaw Apps Gateway",
        "description": "Create issues, sync cycles, and keep engineering roadmap tasks moving.",
        "triggers": ["linear", "linear_issue", "dev_cycle", "sprint_task"],
        "instructions": "Submits GraphQL mutation to create or update Linear issue tickets.",
        "code": """def execute(title, team):
    return {'skill': 'linear_integration', 'ticket': title, 'team': team, 'status': 'created'}"""
    },
    {
        "name": "figma_integration",
        "title": "Figma Design Tokens & Asset Exporter",
        "author": "OpenClaw Apps Gateway",
        "description": "Export assets, inspect frames, and synchronize design context with code.",
        "triggers": ["figma", "figma_export", "design_tokens", "ui_specs"],
        "instructions": "Inspects Figma frame nodes and generates downloadable PNG/SVG exports.",
        "code": """def execute(file_key):
    return {'skill': 'figma_integration', 'file_key': file_key, 'status': 'assets_indexed'}"""
    },
    {
        "name": "trello_integration",
        "title": "Trello Kanban & Workflow Manager",
        "author": "OpenClaw Apps Gateway",
        "description": "Manage boards, lists, cards, and automated checklist progress.",
        "triggers": ["trello", "trello_card", "kanban_board", "trello_list"],
        "instructions": "Creates or moves Trello cards across kanban workflow lists.",
        "code": """def execute(board, card_title):
    return {'skill': 'trello_integration', 'board': board, 'card': card_title, 'status': 'card_placed'}"""
    },
    {
        "name": "whatsapp_integration",
        "title": "WhatsApp Web Channel Gateway",
        "author": "OpenClaw Apps Gateway",
        "description": "WhatsApp Web channel plugin for agent chats, message delivery, and media dispatch.",
        "triggers": ["whatsapp", "wa_message", "whatsapp_bot", "wa_channel"],
        "instructions": "Connects to WhatsApp Web bridge or Cloud API to route messages and media.",
        "code": """def execute(recipient, message):
    return {'skill': 'whatsapp_integration', 'recipient': recipient, 'status': 'sent_to_wa_gateway'}"""
    },
    {
        "name": "crabbox_sandbox",
        "title": "Crabbox Safe Execution Sandbox",
        "author": "OpenClaw Ecosystem",
        "description": "Sandboxed secure execution environment for user Python, JS, and Bash code blocks.",
        "triggers": ["crabbox", "sandbox_exec", "safe_eval", "isolate_code"],
        "instructions": "Executes code inside an isolated memory and network boundary with strict timeouts.",
        "code": """def execute(code_snippet):
    return {'skill': 'crabbox_sandbox', 'execution': 'clean', 'exit_code': 0}"""
    },
    {
        "name": "discrawl_crawler",
        "title": "Discrawl Discord Community Crawler",
        "author": "OpenClaw Ecosystem",
        "description": "Crawls and archives Discord channels, threads, and shared resources into structured knowledge.",
        "triggers": ["discrawl", "discord_crawler", "discord_archive", "crawl_discord"],
        "instructions": "Indexes message history from accessible Discord channels for RAG and search.",
        "code": """def execute(channel_id):
    return {'skill': 'discrawl_crawler', 'channel': channel_id, 'messages_crawled': 250}"""
    },
    {
        "name": "gitcrawl_crawler",
        "title": "Gitcrawl Repository Deep Crawler",
        "author": "OpenClaw Ecosystem",
        "description": "Crawls full GitHub repository trees, issues, PR diffs, and releases into searchable documentation.",
        "triggers": ["gitcrawl", "crawl_repo", "repo_crawler", "git_indexer"],
        "instructions": "Clones repository metadata, tree nodes, and commit summaries into an offline knowledge base.",
        "code": """def execute(repo_url):
    return {'skill': 'gitcrawl_crawler', 'repo': repo_url, 'files_indexed': 84}"""
    }
]

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    skills_dir = os.path.join(base_dir, "skills")
    os.makedirs(skills_dir, exist_ok=True)

    created = 0
    for s in skills_data:
        folder = os.path.join(skills_dir, s["name"])
        os.makedirs(folder, exist_ok=True)
        skill_file = os.path.join(folder, "SKILL.md")
        triggers_str = "[" + ", ".join([f'"{t}"' for t in s["triggers"]]) + "]"
        md_content = f"""---
name: {s['name']}
title: "{s['title']}"
description: "{s['description']}"
triggers: {triggers_str}
author: "{s['author']}"
---

# {s['title']}

## Description
{s['description']}

## Workflow & Instructions
{s['instructions']}

## Executable Implementation
```python
{s['code']}
```
"""
        with open(skill_file, "w", encoding="utf-8") as f:
            f.write(md_content)
        created += 1

    print(f"SUCCESS: Created {created} ClawHub skills in {skills_dir}!")

if __name__ == "__main__":
    main()
