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

A multimodal Telegram agent with specialist model routing and an Omega capability runtime.

The upgrade adds **15 executable capabilities** for surveys/Excel, CAD, video/subtitles, SQL, math, bounded DAG/MCTS planning, defensive audits, and financial calculations. Start with `/omega` in Telegram or the authenticated `/omega/capabilities` API. See [implementation scope, architecture, setup, and limitations](OMEGA_IMPLEMENTATION.md) and the [source roadmap catalog](upgrade_catalog.json).

```text
python -m venv .venv
# Activate .venv for your shell, then:
python -m pip install -r requirements-dev.txt
python -m pytest -q tests
python scripts/build_upgrade_catalog.py --check
uvicorn app:app --host 127.0.0.1 --port 7860
```

Copy settings from [.env.example](.env.example). Set `TELEGRAM_BOT_TOKEN` for Telegram, `HF_TOKEN` for model inference, `TAVILY_API_KEY` for search, and `OMEGA_API_KEY` for authenticated HTTP tools. Generated Python execution requires a configured runner backend; by default it returns the source artifact without executing it.

Example Telegram requests:

```text
/omega math.calculate {"expression":"sqrt(81)+2**3"}
/omega cad.motor_bracket {"width_mm":60,"depth_mm":60,"thickness_mm":5,"hole_diameter_mm":3.5}
/omega survey.bundle {"title":"Employee feedback","questions":[{"id":"rating","title":"Satisfaction","type":"scale","min":1,"max":5}]}
/omega finance.amortization {"principal":100000,"annual_rate_percent":12,"months":12}
```

Model responses and source roadmap ranges are not evidence of completed work. Task outcomes record success, failure, or incomplete execution and include measured runtime and artifact checksums. The full 2,000+ roadmap remains partially implemented.

## 🚀 Live Telegram Bot
👉 **[@CyberMastetControlAi_bot](https://t.me/CyberMastetControlAi_bot)**

## 🛠 Features & Capabilities
* **Model Brain:** `NousResearch/Hermes-3-Llama-3.1-70B` via Hugging Face Router.
* **Autonomous Tool Use:**
  * 🌐 **Live Web Search:** Real-time web querying via DuckDuckGo.
  * 🧮 **Python Calculation Engine:** Safe mathematical and formula evaluation.
  * ⏰ **Time & Timezones:** Current date, time, and timezone resolution.
* **Memory:** In-process conversation history with `/clear`; user preferences persist in JSON.
* **Deployment:** Docker and Render configurations are provided; uptime depends on hosting and provider availability.

## 🔒 Configuration & Secrets
Set the following secrets in Space Settings (Variables and secrets):
* `HF_TOKEN`: Hugging Face User Access Token
* `TELEGRAM_BOT_TOKEN`: Token for `@CyberMastetControlAi_bot`
* `HF_MODEL`: `NousResearch/Hermes-3-Llama-3.1-70B`
