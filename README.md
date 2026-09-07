---
title: Cyber Master Control AI - Hermes 3 Agent
emoji: 🧠
colorFrom: purple
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# 🧠 Cyber Master Control AI (Hermes 3 Autonomous Agent)

An enterprise-grade autonomous AI Agent powered by **Nous Hermes 3 (Llama 3.1 70B)**, integrated seamlessly with Telegram.

## 🚀 Live Telegram Bot
👉 **[@CyberMastetControlAi_bot](https://t.me/CyberMastetControlAi_bot)**

## 🛠 Features & Capabilities
* **Model Brain:** `NousResearch/Hermes-3-Llama-3.1-70B` via Hugging Face Router.
* **Autonomous Tool Use:**
  * 🌐 **Live Web Search:** Real-time web querying via DuckDuckGo.
  * 🧮 **Python Calculation Engine:** Safe mathematical and formula evaluation.
  * ⏰ **Time & Timezones:** Current date, time, and timezone resolution.
* **Persistent Memory:** Multi-turn session memory per chat with reset capability (`/clear`).
* **24/7 Uptime:** Hosted on Hugging Face Spaces with port 7860 health monitoring.

## 🔒 Configuration & Secrets
Set the following secrets in Space Settings (Variables and secrets):
* `HF_TOKEN`: Hugging Face User Access Token
* `TELEGRAM_BOT_TOKEN`: Token for `@CyberMastetControlAi_bot`
* `HF_MODEL`: `NousResearch/Hermes-3-Llama-3.1-70B`
