"""
================================================================================
  🦅 OpenClaw Autonomous Engine & Universal Integration Gateway
  Autonomous Skill Workshop, SKILL.md Lifecycle, Universal REST APIs & Webhooks
================================================================================
"""

import os
import sys
import json
import time
import re
import datetime
import subprocess
import ast
import hashlib
from autonomous_runner import AutonomousRunner
from self_learner import validate_memory
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional, Tuple

try:
    import requests
except ImportError:
    requests = None


class OpenClawSkill:
    """Represents a single OpenClaw skill backed by a SKILL.md specification."""
    def __init__(
        self,
        name: str,
        title: str,
        description: str,
        triggers: List[str],
        instructions: str,
        code: Optional[str] = None,
        author: str = "OpenClaw Autonomous Engine",
        created_at: Optional[str] = None
    ):
        self.name = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower().strip())
        self.title = title.strip() or self.name.replace("_", " ").title()
        self.description = description.strip()
        self.triggers = [t.lower().strip() for t in triggers if t.strip()]
        self.instructions = instructions.strip()
        self.code = code.strip() if code else ""
        self.author = author
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def to_markdown(self) -> str:
        """Serializes skill to OpenClaw SKILL.md format with YAML frontmatter."""
        triggers_yaml = "[" + ", ".join([f'"{t}"' for t in self.triggers]) + "]"
        md = [
            "---",
            f"name: {self.name}",
            f"title: \"{self.title}\"",
            f"description: \"{self.description}\"",
            f"triggers: {triggers_yaml}",
            f"author: \"{self.author}\"",
            f"created_at: \"{self.created_at}\"",
            "---",
            "",
            f"# {self.title}",
            "",
            "## Description",
            self.description,
            "",
            "## Workflow & Instructions",
            self.instructions,
        ]

        if self.code:
            md.extend([
                "",
                "## Executable Implementation",
                "```python",
                self.code,
                "```"
            ])

        return "\n".join(md)

    @classmethod
    def from_markdown(cls, content: str) -> Optional["OpenClawSkill"]:
        """Parses a SKILL.md file with YAML frontmatter."""
        try:
            frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not frontmatter_match:
                return None

            fm_raw = frontmatter_match.group(1)
            body = frontmatter_match.group(2)

            metadata: Dict[str, Any] = {}
            for line in fm_raw.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if v.startswith("[") and v.endswith("]"):
                        items = [x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
                        metadata[k] = items
                    else:
                        metadata[k] = v

            name = metadata.get("name", "unnamed_skill")
            title = metadata.get("title", name.replace("_", " ").title())
            description = metadata.get("description", "")
            triggers = metadata.get("triggers", [])
            author = metadata.get("author", "OpenClaw Core")
            created_at = metadata.get("created_at", "")

            code = ""
            code_match = re.search(r"```python\s*(.*?)\s*```", body, re.DOTALL)
            if code_match:
                code = code_match.group(1).strip()
                instructions = body[:code_match.start()].strip()
            else:
                instructions = body.strip()

            return cls(
                name=name,
                title=title,
                description=description,
                triggers=triggers,
                instructions=instructions,
                code=code,
                author=author,
                created_at=created_at
            )
        except Exception:
            return None


class OpenClawWorkshop:
    """Core OpenClaw Autonomous Engine managing skills, integrations, and self-learning."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.skills_dir = os.path.join(self.base_dir, "skills")
        self.integrations_file = os.path.join(self.base_dir, "integrations_store.json")
        os.makedirs(self.skills_dir, exist_ok=True)

        self.skills: Dict[str, OpenClawSkill] = {}
        self.integrations: Dict[str, Dict[str, Any]] = {}
        self.code_runner = AutonomousRunner()

        self._load_integrations()
        self._load_skills()
        self._ensure_default_skills()

    def _load_integrations(self):
        """Loads registered integrations from JSON file."""
        if os.path.exists(self.integrations_file):
            try:
                with open(self.integrations_file, "r", encoding="utf-8") as f:
                    self.integrations = json.load(f)
            except Exception:
                self.integrations = {}
        else:
            # Default built-in public integrations
            self.integrations = {
                "coingecko": {
                    "name": "CoinGecko Crypto API",
                    "base_url": "https://api.coingecko.com/api/v3",
                    "description": "Public real-time cryptocurrency prices, market caps, and trading volume (Free, No Auth required).",
                    "status": "connected"
                },
                "github_public": {
                    "name": "GitHub REST API",
                    "base_url": "https://api.github.com",
                    "description": "Access public repositories, user profiles, commits, and stargazers.",
                    "status": "connected"
                },
                "duckduckgo": {
                    "name": "DuckDuckGo Search Engine",
                    "base_url": "https://html.duckduckgo.com/html",
                    "description": "Live web querying and document discovery.",
                    "status": "connected"
                },
                "tavily": {
                    "name": "Tavily AI Search & Deep Research",
                    "base_url": "https://api.tavily.com",
                    "description": "Real-time AI web search, clean content extraction, and cited research.",
                    "status": "connected"
                },
                "webhook_gateway": {
                    "name": "Universal Webhook Dispatcher",
                    "base_url": "https://httpbin.org/anything",
                    "description": "Outbound HTTP webhook relays for n8n, Zapier, Make, Slack, and Discord.",
                    "status": "connected"
                }
            }
            self.integrations["tavily"] = {
                "name": "Tavily AI Search & Deep Research",
                "base_url": "https://api.tavily.com",
                "description": "Real-time AI web search, clean content extraction, and cited research.",
                "status": "connected"
            }
            self._save_integrations()

    def _save_integrations(self):
        """Persists integrations to disk."""
        try:
            with open(self.integrations_file, "w", encoding="utf-8") as f:
                json.dump(self.integrations, f, indent=2)
        except Exception:
            pass

    def _load_skills(self):
        """Reads all SKILL.md files from the skills directory."""
        if not os.path.exists(self.skills_dir):
            return

        for entry in os.listdir(self.skills_dir):
            entry_path = os.path.join(self.skills_dir, entry)
            skill_file = None
            if os.path.isdir(entry_path):
                target = os.path.join(entry_path, "SKILL.md")
                if os.path.exists(target):
                    skill_file = target
            elif entry.endswith(".md"):
                skill_file = entry_path

            if skill_file:
                try:
                    with open(skill_file, "r", encoding="utf-8") as f:
                        skill = OpenClawSkill.from_markdown(f.read())
                        if skill:
                            self.skills[skill.name] = skill
                except Exception:
                    pass

    def _save_skill_to_disk(self, skill: OpenClawSkill) -> str:
        """Writes a skill to its dedicated directory with a SKILL.md file."""
        skill_dir = os.path.join(self.skills_dir, skill.name)
        os.makedirs(skill_dir, exist_ok=True)
        file_path = os.path.join(skill_dir, "SKILL.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(skill.to_markdown())
        return file_path

    def _ensure_default_skills(self):
        """Seeds essential OpenClaw built-in skills if not already present."""
        default_skills = [
            OpenClawSkill(
                name="crypto_market_tracker",
                title="Crypto Market Live Tracker",
                description="Fetches live cryptocurrency prices, market caps, and 24h changes from CoinGecko.",
                triggers=["crypto", "bitcoin", "btc", "eth", "ethereum", "solana", "sol", "token", "coin"],
                instructions=(
                    "1. Identify the requested coin (e.g. bitcoin, ethereum, solana, cardano).\n"
                    "2. Query the CoinGecko public API endpoint `/simple/price?ids={coin}&vs_currencies=usd,inr&include_24hr_change=true`.\n"
                    "3. Format the current price in USD ($) and INR (Rs.) along with the 24-hour percentage change."
                ),
                code="""import urllib.request, json
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
result = "\\n".join(output) if output else "No data returned for specified crypto."
"""
            ),
            OpenClawSkill(
                name="github_repo_scout",
                title="GitHub Public Repo Scout",
                description="Inspects public GitHub repositories, stars, forks, language, open issues, and latest commit.",
                triggers=["github", "repo", "repository", "commits", "stars", "git"],
                instructions=(
                    "1. Extract repository owner and repo name from user query (e.g. 'NousResearch/Hermes-3-Llama-3.1-70B').\n"
                    "2. Call GitHub API `https://api.github.com/repos/{owner}/{repo}`.\n"
                    "3. Return full repository intelligence summary."
                ),
                code="""import urllib.request, json
repo_query = params.get('repo', 'cyberdrivepro/hermes-telegram-agent').strip()
if 'github.com/' in repo_query:
    repo_query = repo_query.split('github.com/')[-1].strip('/')
url = f'https://api.github.com/repos/{repo_query}'
req = urllib.request.Request(url, headers={'User-Agent': 'OpenClaw-Scout/1.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    d = json.loads(r.read().decode())
result = (
    f"🐙 **GitHub Repo: {d.get('full_name')}**\\n"
    f"⭐ Stars: {d.get('stargazers_count', 0):,} | 🍴 Forks: {d.get('forks_count', 0):,}\\n"
    f"💻 Primary Language: {d.get('language', 'Unknown')}\\n"
    f"📝 Description: {d.get('description', 'None')}\\n"
    f"🔗 Link: {d.get('html_url')}\\n"
    f"🕒 Last Updated: {d.get('updated_at', '')[:10]}"
)
"""
            ),
            OpenClawSkill(
                name="universal_webhook_relay",
                title="Universal Webhook Relay",
                description="Dispatches formatted event payloads to external automations like n8n, Zapier, Make, Slack, or Discord.",
                triggers=["webhook", "n8n", "zapier", "make", "slack", "discord", "payload", "relay"],
                instructions=(
                    "1. Collect the target webhook URL and JSON payload.\n"
                    "2. Execute HTTP POST request with Content-Type application/json.\n"
                    "3. Return HTTP delivery status code and server response."
                ),
                code="""import urllib.request, json
url = params.get('url', 'https://httpbin.org/post')
payload = params.get('payload', {'event': 'openclaw_relay', 'timestamp': str(time.time())})
data_bytes = json.dumps(payload).encode('utf-8')
req = urllib.request.Request(url, data=data_bytes, headers={'Content-Type': 'application/json', 'User-Agent': 'OpenClaw/1.0'})
with urllib.request.urlopen(req, timeout=10) as r:
    status = r.status
    body = r.read().decode('utf-8', errors='ignore')[:300]
result = f"✅ Webhook delivered successfully! HTTP Status: {status}\\nResponse snippet: {body}"
"""
            ),
            OpenClawSkill(
                name="executive_news_curator",
                title="Executive News & Trend Curator",
                description="Curates fresh breaking news and summarizes key industry takeaways into executive bullet points.",
                triggers=["news", "trending", "headline", "curator", "digest"],
                instructions=(
                    "1. Search live headlines on DuckDuckGo using current date context.\n"
                    "2. Extract top 4 verified headlines.\n"
                    "3. Formulate an executive briefing highlighting impact and outlook."
                )
            ),
            OpenClawSkill(
                name="code_review_auditor",
                title="Code Quality & Security Auditor",
                description="Audits Python, JavaScript, and shell code for security vulnerabilities, logic flaws, and speed improvements.",
                triggers=["audit", "code_review", "security_scan", "refactor", "bug_hunt"],
                instructions=(
                    "1. Analyze syntax, input validation, and potential security holes (e.g. injection, shell execution).\n"
                    "2. Benchmark algorithmic complexity.\n"
                    "3. Provide refactored snippet with modern best practices."
                )
            )
        ]

        for s in default_skills:
            if s.name not in self.skills:
                self.skills[s.name] = s
                self._save_skill_to_disk(s)

    # -------------------------------------------------------------------------
    # Core Workshop Methods
    # -------------------------------------------------------------------------

    def create_skill(
        self,
        name: str,
        title: str,
        description: str,
        triggers: List[str],
        instructions: str,
        code: Optional[str] = None,
        author: str = "Cyber Master AI (Autonomous)"
    ) -> Tuple[bool, str]:
        """Creates a new skill, writes SKILL.md, and registers it dynamically."""
        try:
            skill = OpenClawSkill(
                name=name,
                title=title,
                description=description,
                triggers=triggers,
                instructions=instructions,
                code=code,
                author=author
            )
            self.skills[skill.name] = skill
            saved_path = self._save_skill_to_disk(skill)
            return True, f"Skill `{skill.name}` successfully created and registered in OpenClaw workshop! Saved at: `{os.path.basename(saved_path)}`"
        except Exception as e:
            return False, f"Failed to create skill: {str(e)}"

    def list_skills(self) -> List[Dict[str, Any]]:
        """Returns catalog of all active OpenClaw skills."""
        out = []
        for s in self.skills.values():
            out.append({
                "name": s.name,
                "title": s.title,
                "description": s.description,
                "triggers": s.triggers,
                "has_code": bool(s.code),
                "author": s.author,
                "created_at": s.created_at
            })
        return out

    def get_skill(self, name_or_keyword: str) -> Optional[OpenClawSkill]:
        """Finds a skill by exact name or matching trigger keyword."""
        key = name_or_keyword.lower().strip()
        if key in self.skills:
            return self.skills[key]

        # Match triggers
        for s in self.skills.values():
            if key in s.triggers or key in s.name:
                return s
        return None

    def run_skill(self, name: str, params: Optional[Dict[str, Any]] = None) -> Tuple[str, bool]:
        """Executes a skill by name. If it has code, runs it; otherwise returns instructions."""
        skill = self.get_skill(name)
        if not skill:
            return f"Error: Skill '{name}' not found in OpenClaw workshop.", False

        params = params or {}

        if skill.code:
            # Execute the manifest as data through the configured code runner.
            # No in-process exec: a Python namespace is not an isolation boundary.
            wrapper = "import json, inspect, time, datetime\nparams = json.loads(" + repr(json.dumps(params)) + ")\n" + skill.code
            wrapper += "\n_fn = globals().get('execute') or globals().get('run')\n"
            wrapper += "if callable(_fn):\n    _sig = inspect.signature(_fn)\n    _args = {k:v for k,v in params.items() if k in _sig.parameters}\n    result = _fn(**_args)\n"
            wrapper += "print(json.dumps(globals().get('result', None), default=str))\n"
            result = self.code_runner.execute_with_auto_heal(wrapper)
            return (result.get("stdout") or str(result.get("error", "No result"))), bool(result.get("success"))
        return (f"Workflow guidance for {skill.title} (not executed):\n{skill.instructions}\nParameters: {json.dumps(params)}", True)

    # -------------------------------------------------------------------------
    # Universal Integrations Gateway (REST APIs & Webhooks)
    # -------------------------------------------------------------------------

    def call_api(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Any] = None,
        params: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Universal REST API caller supporting GET, POST, PUT, DELETE."""
        method = method.upper().strip()
        headers = headers or {}
        if "User-Agent" not in headers:
            headers["User-Agent"] = "OpenClaw-Universal-Agent/2.0"

        try:
            if requests:
                resp = requests.request(
                    method=method,
                    url=url,
                    headers=headers,
                    json=json_data,
                    params=params,
                    timeout=15
                )
                try:
                    parsed_json = resp.json()
                except Exception:
                    parsed_json = None

                return {
                    "success": 200 <= resp.status_code < 300,
                    "status_code": resp.status_code,
                    "response": parsed_json if parsed_json is not None else resp.text[:4000],
                    "headers": dict(resp.headers)
                }
            else:
                full_url = url
                if params:
                    full_url += "?" + urllib.parse.urlencode(params)

                data_bytes = None
                if json_data is not None:
                    data_bytes = json.dumps(json_data).encode("utf-8")
                    headers["Content-Type"] = "application/json"

                req = urllib.request.Request(full_url, data=data_bytes, headers=headers, method=method)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw_body = resp.read().decode("utf-8", errors="ignore")
                    try:
                        parsed_json = json.loads(raw_body)
                    except Exception:
                        parsed_json = raw_body[:4000]

                    return {
                        "success": True,
                        "status_code": resp.status,
                        "response": parsed_json,
                        "headers": dict(resp.headers)
                    }
        except Exception as e:
            return {
                "success": False,
                "status_code": 500,
                "error": str(e),
                "response": None
            }

    def send_webhook(self, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an outbound HTTP POST webhook payload."""
        return self.call_api(
            url=url,
            method="POST",
            headers={"Content-Type": "application/json"},
            json_data=payload
        )

    def list_integrations(self) -> Dict[str, Dict[str, Any]]:
        """Returns all configured integrations."""
        return self.integrations

    def register_integration(self, key: str, name: str, base_url: str, description: str, auth_token: Optional[str] = None) -> str:
        """Registers a new external service or API integration."""
        self.integrations[key.lower().strip()] = {
            "name": name.strip(),
            "base_url": base_url.strip(),
            "description": description.strip(),
            "has_auth": bool(auth_token),
            "status": "configured",
            "registered_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }
        self._save_integrations()
        return f"Integration `{key}` successfully registered in OpenClaw gateway!"

    # -------------------------------------------------------------------------
    # Autonomous Self-Learning Distiller
    # -------------------------------------------------------------------------

    def self_learn_from_chat(self, topic: str, user_instructions: str, code_snippet: Optional[str] = None) -> str:
        """Autonomously extracts and distills user conversation/corrections into a permanent skill."""
        slug = re.sub(r"[^a-zA-Z0-9_-]", "_", topic.lower().strip())
        if not slug:
            slug = f"skill_{int(time.time())}"

        triggers = [slug] + [w.lower() for w in topic.split() if len(w) > 3]

        success, msg = self.create_skill(
            name=slug,
            title=topic.title(),
            description=f"Autonomously learned workflow for {topic} based on user instructions.",
            triggers=triggers,
            instructions=user_instructions,
            code=code_snippet,
            author="OpenClaw Self-Learner (via Telegram Chat)"
        )
        return msg


# ==============================================================================
# 🦅 OPENCLAW v2 ADVANCED RUNTIME EXTENSIONS
# ==============================================================================

class ClawHubRegistry:
    """Public package registry interface for ClawHub (11,211+ skills & community plugins)."""

    def __init__(self, workshop: OpenClawWorkshop):
        self.workshop = workshop
        self.catalog_size = 11211
        # Seeded index of high-demand ClawHub packages
        self.indexed_packages = {
            "@leoyeai/openclaw-master-skills": {
                "name": "openclaw-master-skills",
                "title": "OpenClaw Master Skills Mega Pack (11,211+ Skills)",
                "author": "@leoyeai",
                "description": "Comprehensive curated collection of 11,211+ skills across AI, DevOps, Productivity, Scraping, IoT & Security.",
                "skills_count": 11211,
                "categories": ["AI/LLM", "DevOps", "Productivity", "Marketing", "Security", "IoT", "Finance", "Scraping"]
            },
            "@steipete/apple-notes": {
                "name": "apple_notes",
                "title": "Apple Notes Integration",
                "author": "@steipete",
                "description": "Read, create, search, and manage Apple Notes folders and rich text attachments via native AppleScript bridge.",
                "skills_count": 1
            },
            "@steipete/notion": {
                "name": "notion_workspace",
                "title": "Notion Full Workspace Sync",
                "author": "@steipete",
                "description": "Read pages, query databases, append blocks, and draft structured docs in Notion.",
                "skills_count": 1
            },
            "@steipete/obsidian": {
                "name": "obsidian_vault",
                "title": "Obsidian Vault & Wikilinks Sync",
                "author": "@steipete",
                "description": "Read, query, write, and link markdown documents, daily notes, and frontmatter inside local Obsidian vaults.",
                "skills_count": 1
            },
            "@steipete/github": {
                "name": "github_steipete",
                "title": "GitHub Full Developer Automation",
                "author": "@steipete",
                "description": "Review PRs, inspect commit trees, manage issues, and trigger GitHub Actions.",
                "skills_count": 1
            },
            "@community/home-assistant": {
                "name": "home_assistant",
                "title": "Home Assistant Automation Controller",
                "author": "@community",
                "description": "Control smart home entities, lights, climate, switches, and scenes via Home Assistant REST/WebSocket API.",
                "skills_count": 1
            },
            "@steipete/openhue": {
                "name": "philips_hue",
                "title": "Philips Hue Smart Lighting Engine",
                "author": "@steipete",
                "description": "Control rooms, light strips, color temperatures, brightness, and dynamic light scenes via OpenHue CLI.",
                "skills_count": 1
            },
            "@steipete/spotify-player": {
                "name": "spotify_player",
                "title": "Spotify Connect & Playback Controller",
                "author": "@steipete",
                "description": "Control music playback, search tracks, play playlists, skip, and manage volume across Spotify Connect devices.",
                "skills_count": 1
            },
            "@steipete/sonoscli": {
                "name": "sonos_controller",
                "title": "Sonos Multi-Room Audio CLI",
                "author": "@steipete",
                "description": "Group rooms, manage volume, stream radio feeds, and control multi-room speakers via sonoscli.",
                "skills_count": 1
            },
            "@lamelas/himalaya": {
                "name": "himalaya_email",
                "title": "Himalaya CLI Email Workflow",
                "author": "@lamelas",
                "description": "Manage multi-account IMAP/SMTP mailboxes, read envelopes, send PGP-signed messages, and batch-archive mail.",
                "skills_count": 1
            },
            "@community/twitter": {
                "name": "twitter_x",
                "title": "X / Twitter Automation & Discovery",
                "author": "@community",
                "description": "Monitor timelines, extract tweet metrics, schedule posts, and search keywords on X / Twitter.",
                "skills_count": 1
            },
            "@steipete/1password": {
                "name": "onepassword",
                "title": "1Password Vault & Secret Manager",
                "author": "@steipete",
                "description": "Securely retrieve API tokens, credentials, and secure notes from 1Password vaults using the `op` CLI.",
                "skills_count": 1
            },
            "@steipete/weather": {
                "name": "weather_live",
                "title": "Weather & Meteorological Forecasts",
                "author": "@steipete",
                "description": "Retrieve current temperatures, precipitation, wind speeds, and 7-day atmospheric forecasts.",
                "skills_count": 1
            }
        }

    def search(self, query: str, limit: int = 8) -> List[Dict[str, Any]]:
        """Search ClawHub registry packages by keyword or category."""
        q = query.lower().strip()
        results = []
        for pkg_id, meta in self.indexed_packages.items():
            if not q or q in pkg_id.lower() or q in meta["title"].lower() or q in meta["description"].lower() or any(q in c.lower() for c in meta.get("categories", [])):
                results.append({"package": pkg_id, "source": "bundled_catalog", **meta})
                if len(results) >= limit:
                    break
        return results

    def install(self, package_name: str, global_install: bool = True) -> Tuple[bool, str]:
        """Report the actual local catalog status; remote installation is unconfigured."""
        clean = package_name.strip()
        meta = self.indexed_packages.get(clean)
        if meta and meta.get("name") in self.workshop.skills:
            return True, f"Local workflow `{meta['name']}` is already available. No remote package was installed."
        return False, "Remote ClawHub package acquisition is not configured. Supply a reviewed manifest through the skill workshop."

    def verify(self, skill_name: str) -> Dict[str, Any]:
        """Compute a content digest and syntax check; do not invent signatures or audits."""
        skill = self.workshop.get_skill(skill_name)
        if not skill:
            return {"verified": False, "error": "Skill not found"}
        digest = hashlib.sha256(skill.to_markdown().encode()).hexdigest()
        try:
            if skill.code:
                ast.parse(skill.code)
        except SyntaxError as exc:
            return {"verified": False, "sha256": digest, "syntax_valid": False, "error": str(exc)}
        return {"verified": False, "skill": skill.name, "title": skill.title,
                "sha256": digest, "syntax_valid": True, "manifest_status": "unsigned",
                "security_audit": "not_performed", "executable_sandbox": "configured_runner_required" if skill.code else "workflow_only"}

    def update_all(self) -> str:
        return "No remote update provider is configured; installed skills were not changed."


class SkillWorkshop:
    """
    OpenClaw Skill Workshop (Governance Layer):
    Supports 3 self-learning modes: 'auto', 'propose', 'off'.
    Manages PROPOSAL.md lifecycle: propose -> inspect -> evaluate -> apply/reject/quarantine.
    """

    def __init__(self, workshop: OpenClawWorkshop):
        self.workshop = workshop
        self.mode = "propose"  # 'auto', 'propose', 'off'
        self.proposals_dir = os.path.join(self.workshop.base_dir, "proposals")
        os.makedirs(self.proposals_dir, exist_ok=True)
        self.proposals: Dict[str, Dict[str, Any]] = {}
        self._load_proposals()

    def set_mode(self, mode: str) -> str:
        clean = mode.lower().strip()
        if clean in ["auto", "propose", "off"]:
            self.mode = clean
            return f"🎯 OpenClaw Self-Learning mode set to: `{self.mode.upper()}`"
        return "⚠️ Invalid mode. Choose: `auto`, `propose`, or `off`."

    def _load_proposals(self):
        """Loads pending PROPOSAL.md files from proposals/ directory."""
        if not os.path.exists(self.proposals_dir):
            return
        for f in os.listdir(self.proposals_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(self.proposals_dir, f), "r", encoding="utf-8") as fp:
                        p = json.load(fp)
                        self.proposals[p["id"]] = p
                except Exception:
                    pass

    def create_proposal(self, name: str, workflow: str, reason: str = "durable user correction", author: str = "Self-Learning Review") -> Dict[str, Any]:
        """Creates a PROPOSAL.md entry for Skill Workshop review."""
        prop_id = f"prop_{int(time.time())}_{name[:10]}"
        proposal = {
            "id": prop_id,
            "name": name,
            "title": name.replace("_", " ").title(),
            "workflow": workflow,
            "reason": reason,
            "author": author,
            "status": "pending_review",
            "created_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        }

        # Write proposal file
        with open(os.path.join(self.proposals_dir, f"{prop_id}.json"), "w", encoding="utf-8") as f:
            json.dump(proposal, f, indent=2)

        md_path = os.path.join(self.proposals_dir, f"{prop_id}_PROPOSAL.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(f"# Skill Proposal: {proposal['title']} ({prop_id})\n\n**Reason:** {reason}\n**Workflow:**\n{workflow}\n")

        self.proposals[prop_id] = proposal

        # If in 'auto' mode, automatically approve and promote to active skill!
        if self.mode == "auto":
            self.approve_proposal(prop_id)
            proposal["status"] = "auto_promoted_to_active_skill"

        return proposal

    def list_proposals(self) -> List[Dict[str, Any]]:
        return list(self.proposals.values())

    def approve_proposal(self, proposal_id: str) -> Tuple[bool, str]:
        """Promotes a proposal to an active permanent SKILL.md."""
        p = self.proposals.get(proposal_id)
        if not p:
            return False, f"Proposal '{proposal_id}' not found."

        success, msg = self.workshop.create_skill(
            name=p["name"],
            title=p["title"],
            description=f"Skill approved from Workshop proposal: {p.get('reason')}",
            triggers=[p["name"]],
            instructions=p["workflow"],
            author=f"Skill Workshop ({p['author']})"
        )
        p["status"] = "approved_and_active"
        with open(os.path.join(self.proposals_dir, f"{proposal_id}.json"), "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)

        return True, f"✅ Proposal `{proposal_id}` approved! Skill `{p['name']}` is now live."

    def reject_proposal(self, proposal_id: str) -> Tuple[bool, str]:
        p = self.proposals.get(proposal_id)
        if not p:
            return False, f"Proposal '{proposal_id}' not found."
        p["status"] = "rejected"
        with open(os.path.join(self.proposals_dir, f"{proposal_id}.json"), "w", encoding="utf-8") as f:
            json.dump(p, f, indent=2)
        return True, f"🚫 Proposal `{proposal_id}` rejected."

    def experience_review(self, user_msg: str, bot_reply: str) -> Optional[Dict[str, Any]]:
        """
        Background Experience Review:
        Analyzes conversation for durable corrections or multi-step procedures.
        """
        if self.mode == "off":
            return None

        # Check for explicit correction patterns
        correction_patterns = [
            r"(?:hamesha|always)\s+(?:do|use|run|pehle)\s+(.*)",
            r"(?:next time|aage se)\s+(.*)",
            r"(?:galat hai|wrong|no),\s*(?:actually\s+)?(.*)"
        ]

        for pat in correction_patterns:
            m = re.search(pat, user_msg, re.IGNORECASE)
            if m:
                extracted = m.group(1).strip()
                if len(extracted) > 10:
                    slug = f"learned_rule_{int(time.time())}"
                    prop = self.create_proposal(
                        name=slug,
                        workflow=f"User correction rule: {extracted}",
                        reason=f"Observed user correction: '{user_msg[:60]}...'",
                        author="Experience Review Engine"
                    )
                    return prop
        return None


class StandingOrdersEngine:
    """Manages persistent responsibilities from AGENTS.md and executes Heartbeats."""

    def __init__(self, base_dir: str):
        self.agents_md_file = os.path.join(base_dir, "AGENTS.md")
        self.last_heartbeat = time.time()

    def get_standing_orders(self) -> str:
        """Reads AGENTS.md content to inject into agent system prompt."""
        if os.path.exists(self.agents_md_file):
            try:
                with open(self.agents_md_file, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return "Standing Orders: Maintain memory integrity, verify facts via Tavily, and propose skills upon user corrections."

    def heartbeat(self, workshop: OpenClawWorkshop) -> Dict[str, Any]:
        """Runs periodic ambient monitoring check (every 30 mins or on-demand)."""
        self.last_heartbeat = time.time()
        active_skills = len(workshop.skills)
        active_integrations = len(workshop.integrations)
        pending_proposals = len([p for p in workshop.workshop_governance.list_proposals() if p.get("status") == "pending_review"])

        memory_error = None
        try:
            with open(os.path.join(workshop.base_dir, "self_memory.json"), encoding="utf-8") as stream:
                validate_memory(json.load(stream))
        except FileNotFoundError:
            memory_error = "memory_missing"
        except (OSError, ValueError) as exc:
            memory_error = type(exc).__name__
        return {
            "status": "degraded" if memory_error else "healthy",
            "heartbeat_time": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "skills_online": active_skills,
            "integrations_configured": active_integrations,
            "integrations_online": None,
            "pending_proposals": pending_proposals,
            "memory_integrity": memory_error or "valid_json_schema",
            "delivery_channels": "not_probed",
            "system_recommendation": "Inspect memory integrity" if memory_error else "Local checks passed; external channels not probed"
        }



class ManagedBrowserEngine:
    """Managed Chrome/Chromium Browser Automation Engine (Open, Click, Type, Inspect, Snapshot)."""

    def open(self, url: str) -> Dict[str, Any]:
        return {"action": "browser_open", "url": url, "status": "unavailable", "error": "Interactive browser backend is not configured; inspect supports static text fetch only"}

    def click(self, selector: str) -> Dict[str, Any]:
        return {"action": "browser_click", "status": "unavailable", "error": "Interactive browser backend is not configured"}

    def type(self, selector: str, text: str) -> Dict[str, Any]:
        return {"action": "browser_type", "status": "unavailable", "error": "Interactive browser backend is not configured"}

    def inspect(self, url: str) -> str:
        """Performs lightweight fetch & clean text extraction."""
        import urllib.request
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 OpenClaw-Browser/2.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                raw_html = r.read().decode(errors="ignore")
                clean = re.sub(r"<script.*?</script>", "", raw_html, flags=re.DOTALL)
                clean = re.sub(r"<style.*?</style>", "", clean, flags=re.DOTALL)
                clean = re.sub(r"<[^>]+>", " ", clean)
                clean = " ".join(clean.split())
                return clean[:2000]
        except Exception as e:
            return f"Error inspecting {url}: {e}"


class ToolSearchEngine:
    """Discovers relevant skills and tools across the 11,211+ catalog without context bloat."""

    def __init__(self, workshop: OpenClawWorkshop, registry: ClawHubRegistry):
        self.workshop = workshop
        self.registry = registry

    def search_tools(self, intent_or_keyword: str) -> List[Dict[str, Any]]:
        query = intent_or_keyword.lower().strip()
        matches = []

        # 1. Search locally active skills
        for s in self.workshop.skills.values():
            if query in s.name or query in s.title.lower() or query in s.description.lower() or any(query in t for t in s.triggers):
                matches.append({
                    "source": "active_skills",
                    "name": s.name,
                    "title": s.title,
                    "description": s.description,
                    "executable": bool(s.code),
                    "run_command": f"/runskill {s.name}"
                })

        # 2. Search ClawHub registry
        reg_results = self.registry.search(query, limit=5)
        for r in reg_results:
            matches.append({
                "source": "clawhub_registry",
                "package": r["package"],
                "title": r["title"],
                "description": r["description"],
                "install_command": f"/clawhub install {r['package']}"
            })

        return matches


# Attach extensions to OpenClawWorkshop instance
OpenClawWorkshop.registry = None
OpenClawWorkshop.workshop_governance = None
OpenClawWorkshop.standing_orders = None
OpenClawWorkshop.browser = None
OpenClawWorkshop.tool_search = None

_original_init = OpenClawWorkshop.__init__
def _enhanced_init(self, base_dir: Optional[str] = None):
    _original_init(self, base_dir)
    self.registry = ClawHubRegistry(self)
    self.workshop_governance = SkillWorkshop(self)
    self.standing_orders = StandingOrdersEngine(self.base_dir)
    self.browser = ManagedBrowserEngine()
    self.tool_search = ToolSearchEngine(self, self.registry)

OpenClawWorkshop.__init__ = _enhanced_init

