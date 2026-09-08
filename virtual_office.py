"""
===============================================================================
  🏢 Virtual AI Office & Autonomous Multi-Model Coworker Dispatcher
  - Real-time Task & Domain Scanner (Coding, SQL, CAD, Finance, Security, etc.)
  - Autonomous Model Hunter: Discovers & fetches top Hugging Face models on the fly
  - Specialist routing with availability checked by the model client
===============================================================================
"""

import re
import json
import logging
import urllib.request
import urllib.parse
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger(__name__)

# Global cache for dynamically discovered models from Hugging Face
DYNAMIC_MODELS_CACHE: Dict[str, str] = {}

class AutonomousModelHunter:
    """Autonomously searches Hugging Face Hub for the best model matching any task domain."""

    @staticmethod
    def search_best_model(domain_query: str) -> Optional[str]:
        clean_q = domain_query.lower().strip()
        if clean_q in DYNAMIC_MODELS_CACHE:
            return DYNAMIC_MODELS_CACHE[clean_q]

        try:
            encoded = urllib.parse.quote(clean_q)
            url = f"https://huggingface.co/api/models?search={encoded}&filter=text-generation&sort=downloads&direction=-1&limit=5"
            req = urllib.request.Request(url, headers={"User-Agent": "AutonomousModelHunter/2.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode())
                if data and isinstance(data, list):
                    for m in data:
                        model_id = m.get("id")
                        if model_id and not m.get("gated", False):
                            logger.info(f"🎯 AutonomousModelHunter discovered top model for '{domain_query}': {model_id}")
                            DYNAMIC_MODELS_CACHE[clean_q] = model_id
                            return model_id
        except Exception as e:
            logger.warning(f"Model hunter search warning for '{domain_query}': {e}")

        return None

from global_tools_engine import GlobalToolsEngine

# Registered 24/7 Virtual Coworkers in the AI Office
VIRTUAL_COWORKERS = {
    "coder": {
        "name": "Devin Coder",
        "title": "Senior Staff Software Engineer",
        "icon": "💻",
        "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        "description": "World-class coding specialist. Handles Python, JS, TypeScript, C++, Rust, debugging, refactoring, and agentic system architecture.",
        "triggers": [
            "code", "python", "javascript", "typescript", "c++", "rust", "html", "css",
            "debug", "fix bug", "error", "traceback", "exception", "function", "class", "algorithm",
            "fastapi", "react", "docker", "git", "github", "api", "json", "regex", "script",
            "programm", "coding", "syntax", "compile", "devops", "backend", "frontend", "vscode"
        ],
        "special_instructions": "You are Devin Coder, Senior Staff Software Engineer in the Virtual AI Office. Write ultra-clean, production-ready, highly-efficient code with proper error handling, unit tests, and clear explanations."
    },
    "sql": {
        "name": "Oracle SQL Architect",
        "title": "Lead Database Engineer & Query Optimizer",
        "icon": "🗄️",
        "model": "Qwen/Qwen3-Coder-30B-A3B-Instruct",
        "description": "Database architecture, complex SQL queries, index optimization, schema normalization, PostgreSQL, MySQL, SQLite, and MongoDB.",
        "triggers": [
            "sql", "postgres", "postgresql", "mysql", "sqlite", "mongodb", "database", "query",
            "select", "inner join", "outer join", "foreign key", "primary key", "index", "schema",
            "table", "stored procedure", "ddl", "dml", "dba", "migration", "prisma", "sqlalchemy", "dbeaver"
        ],
        "special_instructions": "You are the Lead Database Engineer. Formulate optimized, index-aware SQL queries, normalize schemas, prevent SQL injection, and provide clear schema definitions."
    },
    "cad": {
        "name": "Tesla CAD Engineer",
        "title": "Principal 3D CAD & Mechanical Designer",
        "icon": "📐",
        "model": "ADSKAILab/Zero-To-CAD-Qwen3-VL-2B",
        "description": "Parametric 3D CAD modeling, OpenSCAD scripts, CadQuery, FreeCAD, STL mesh generation, engineering drawings, and blueprints.",
        "triggers": [
            "cad", "3d model", "openscad", "scad", "autocad", "solidworks", "stl", "obj", "dxf",
            "3d print", "mesh", "extrusion", "parametric", "mechanical", "blueprint", "dimension",
            "gear", "bracket", "enclosure", "cylinder", "bevel", "revit", "fusion 360", "freecad", "inventor"
        ],
        "special_instructions": "You are the Principal CAD & Hardware Design Engineer. Create exact, parametric 3D models using OpenSCAD code or CadQuery Python scripts with precise dimensions and instructions."
    },
    "finance": {
        "name": "Warren Analyst",
        "title": "Chief Financial Officer (CFO & Tally Specialist)",
        "icon": "📊",
        "model": "SUFE-AIFLM-Lab/Fin-R1",
        "description": "Specialist in financial reasoning, Tally ERP, balance sheets, P&L, GST, budgeting, cash flow, EMI, DCF models, and automated Excel exports.",
        "triggers": [
            "tally", "accounting", "balance sheet", "profit and loss", "p&l", "ledger", "voucher",
            "gst", "taxation", "income tax", "budget", "finance", "cash flow", "revenue", "ebitda",
            "roi", "emi", "loan", "investment", "portfolio", "stock", "excel sheet", "spreadsheet", "dcf", "invoice"
        ],
        "special_instructions": "You are Warren Analyst, CFO in the Virtual AI Office powered by Fin-R1. Structure financial statements clearly with Debit/Credit, Ledger summaries, and invoke create_excel_spreadsheet to deliver real .xlsx spreadsheets."
    },
    "video": {
        "name": "Hollywood Director",
        "title": "Executive Video Producer & Editor",
        "icon": "🎬",
        "model": "Wan-AI/Wan2.2-TI2V-5B",
        "description": "Video generation, timeline editing, automated MP4 clipping, subtitle burn-in, Shotcut workflows, and cinematic storytelling.",
        "triggers": [
            "premiere", "davinci", "after effects", "capcut", "video edit", "timeline", "clip video",
            "subtitles", "burn subtitles", "wan2", "text to video", "render video", "shotcut", "ffmpeg"
        ],
        "special_instructions": "You are Hollywood Director, Executive Video Producer. Guide users on video production, editing techniques, and trigger download_video or omega_run media.clip when appropriate."
    },
    "productivity": {
        "name": "Atlas Organizer",
        "title": "Head of Enterprise Productivity & Operations",
        "icon": "⚡",
        "model": "Qwen/Qwen3-VL-30B-A3B-Instruct",
        "description": "Enterprise workflow automation, document processing, Google Workspace, LibreOffice, Notion notes, and task management.",
        "triggers": [
            "notion", "google docs", "google sheets", "word document", "powerpoint", "presentation",
            "project management", "jira", "clickup", "trello", "asana", "schedule", "calendar", "notes"
        ],
        "special_instructions": "You are Atlas Organizer, Head of Enterprise Productivity. Structure workflows efficiently, organize notes, and create professional Word (.docx), PPTX, and PDF documents."
    },
    "researcher": {
        "name": "Curie Scholar",
        "title": "Chief Scientific & Academic Researcher",
        "icon": "🔬",
        "model": "Qwen/Qwen3-235B-A22B-Thinking-2507",
        "description": "Deep academic research, scientific literature synthesis, Zotero reference management, paper summaries, and complex logic.",
        "triggers": [
            "research", "academic", "paper", "literature", "arxiv", "pubmed", "zotero", "hypothesis",
            "study", "scientific", "data science", "experiment", "citation", "deep thinking"
        ],
        "special_instructions": "You are Curie Scholar, Chief Researcher. Conduct thorough, rigorous research, cite reputable sources, and synthesize complex findings clearly."
    },
    "gui_agent": {
        "name": "TARS Desktop Operator",
        "title": "Autonomous Desktop & GUI Agent",
        "icon": "🖥️",
        "model": "ByteDance-Seed/UI-TARS-1.5-7B",
        "description": "Desktop perception, screen grounding, and GUI automation across 1,057 applications.",
        "triggers": [
            "gui", "desktop control", "click on", "ui-tars", "screen control", "automate software", "app control"
        ],
        "special_instructions": "You are TARS Desktop Operator, powered by UI-TARS 1.5. Provide actionable steps to control, automate, and interact with desktop software interfaces."
    },
    "reasoner": {
        "name": "Athena Thinker",
        "title": "Chief Reasoning & Strategy Officer",
        "icon": "🧠",
        "model": "deepseek-ai/DeepSeek-R1",
        "description": "Deep reasoning and logic expert. Solves complex mathematical puzzles, strategic architectures, and multi-step reasoning.",
        "triggers": [
            "think step by step", "deep reason", "logic puzzle", "prove that", "mathematical proof",
            "strategy", "pros and cons", "root cause analysis", "philosophical", "complex problem",
            "deductive", "riddle"
        ],
        "special_instructions": "You are Athena Thinker, Chief Reasoning Officer. Break down every problem step-by-step, verify all deductions, and give mathematically and logically sound conclusions."
    },
    "cybersec": {
        "name": "ZeroDay Auditor",
        "title": "Chief Information Security Officer (CISO)",
        "icon": "🛡️",
        "model": "NousResearch/Hermes-3-Llama-3.1-70B",
        "description": "Vulnerability scanning, ethical penetration testing, OWASP Top 10, malware analysis, firewall rules, and encryption hardening.",
        "triggers": [
            "cyber", "security", "audit", "vulnerability", "exploit", "cve", "xss", "csrf", "sqli",
            "pen test", "penetration", "nmap", "encryption", "firewall", "hardened", "reverse engineering"
        ],
        "special_instructions": "You are ZeroDay Auditor, Chief Information Security Officer. Analyze security architectures, audit code for vulnerabilities, and provide defensive hardening guidelines."
    },
    "designer": {
        "name": "DaVinci Creator",
        "title": "Creative Studio & Visual Director",
        "icon": "🎨",
        "model": "Qwen/Qwen-Image-Edit",
        "description": "Visual arts and design lead. Produces AI images, UI designs, and edits graphics using semantic design AI.",
        "triggers": [
            "draw", "paint", "generate image", "create picture", "photo of", "illustration",
            "logo design", "wallpaper", "artwork", "flux", "visualize", "figma", "canva", "photoshop", "illustrator", "penpot"
        ],
        "special_instructions": "You are DaVinci Creator, Creative Director. Formulate vivid artistic prompts, assist in graphic design, and invoke the image generation tool."
    },
    "audio": {
        "name": "Echo Producer",
        "title": "Sound Engineer & Audio Specialist",
        "icon": "🎙️",
        "model": "openai/whisper-large-v3-turbo",
        "description": "Voice listening, transcription, audio synthesis, and sound design.",
        "triggers": [
            "voice note", "speech to text", "listen audio", "transcribe", "tts", "speak this", "voice message"
        ],
        "special_instructions": "You are Echo Producer, Sound Engineer in the Virtual AI Office. Handle speech transcription and voice synthesis with highest clarity."
    },
    "downloader": {
        "name": "Hermes Dispatcher",
        "title": "Media Logistics & Package Manager",
        "icon": "🎬",
        "model": "UniversalMediaDownloader",
        "description": "Universal video/audio extraction (YouTube, Instagram, TikTok, Twitter/X) and Komi Store open-source app installer.",
        "triggers": [
            "download video", "mp4", "save video", "get song", "youtube link", "instagram reel", "tiktok", "get apk", "install app"
        ],
        "special_instructions": "You are Hermes Dispatcher, Logistics Coworker. Handle media downloads and APK package deliveries directly to the user."
    },
    "general": {
        "name": "Cyber Supervisor",
        "title": "Managing Director & Orchestrator",
        "icon": "🏢",
        "model": "NousResearch/Hermes-3-Llama-3.1-70B",
        "description": "General AI assistance, multi-turn conversation, knowledge retrieval, and tool orchestration across 1,057 tools.",
        "triggers": [],
        "special_instructions": "You are Cyber Supervisor in the Virtual AI Office. Use available tools to produce working artifacts, report actual outcomes, and identify missing prerequisites accurately."
    }
}

class VirtualOfficeRouter:
    """
    Scans user queries, hunts best models autonomously, and routes tasks to the best specialist coworker.
    """

    def __init__(self):
        self.coworkers = VIRTUAL_COWORKERS
        self.hunter = AutonomousModelHunter()
        self.tools_engine = GlobalToolsEngine()

    def list_office_team(self) -> List[Dict[str, Any]]:
        """Return list of all coworkers in the Virtual Office."""
        res = []
        for key, w in self.coworkers.items():
            res.append({
                "key": key,
                "name": w["name"],
                "title": w["title"],
                "icon": w["icon"],
                "model": w["model"],
                "description": w["description"]
            })
        return res

    def lookup_tool(self, name_or_query: str) -> Optional[Dict[str, Any]]:
        """Look up tool details from the 1,057 tools catalog."""
        return self.tools_engine.get_tool(name_or_query)

    def search_tools(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search across 1,057 tools."""
        return self.tools_engine.search_tools(query, limit=limit)

    def route_task(self, user_text: str) -> Tuple[str, Dict[str, Any]]:
        """
        Scans and analyzes user message to determine optimal coworker and model.
        Returns: (coworker_key, coworker_dict)
        """
        text_lower = user_text.lower().strip()

        # Explicit commands
        if text_lower.startswith(("/coder", "/code", "coder:")):
            return "coder", self.coworkers["coder"]
        if text_lower.startswith(("/sql", "sql:")):
            return "sql", self.coworkers["sql"]
        if text_lower.startswith(("/cad", "cad:")):
            return "cad", self.coworkers["cad"]
        if text_lower.startswith(("/finance", "/tally", "finance:")):
            return "finance", self.coworkers["finance"]
        if text_lower.startswith(("/video", "video:")):
            return "video", self.coworkers["video"]
        if text_lower.startswith(("/productivity", "productivity:")):
            return "productivity", self.coworkers["productivity"]
        if text_lower.startswith(("/research", "research:")):
            return "researcher", self.coworkers["researcher"]
        if text_lower.startswith(("/gui", "gui:", "/tars")):
            return "gui_agent", self.coworkers["gui_agent"]
        if text_lower.startswith(("/reason", "/think", "/math")):
            return "reasoner", self.coworkers["reasoner"]
        if text_lower.startswith(("/security", "/audit", "security:")):
            return "cybersec", self.coworkers["cybersec"]

        # 1. Media Download
        if re.search(r"https?://[^\s]+(?:youtube\.com|youtu\.be|instagram\.com|tiktok\.com|twitter\.com|x\.com|reddit\.com)", text_lower):
            return "downloader", self.coworkers["downloader"]

        # 2. SQL & Database
        sql_hits = sum(1 for w in self.coworkers["sql"]["triggers"] if re.search(rf"\b{re.escape(w)}\b", text_lower))
        if sql_hits >= 2 or any(w in text_lower for w in ["write a query", "sql query", "postgres query", "database schema", "create table"]):
            return "sql", self.coworkers["sql"]

        # 3. CAD & 3D Engineering
        cad_hits = sum(1 for w in self.coworkers["cad"]["triggers"] if re.search(rf"\b{re.escape(w)}\b", text_lower))
        if cad_hits >= 2 or any(w in text_lower for w in ["openscad", "3d model", "cad design", "3d print stl", "mechanical drawing"]):
            return "cad", self.coworkers["cad"]

        # 4. Cybersecurity & Audit
        sec_hits = sum(1 for w in self.coworkers["cybersec"]["triggers"] if re.search(rf"\b{re.escape(w)}\b", text_lower))
        if sec_hits >= 2 or any(w in text_lower for w in ["security audit", "vulnerability scan", "penetration test", "owasp"]):
            return "cybersec", self.coworkers["cybersec"]

        # 5. Finance, Tally & Excel
        finance_hits = sum(1 for w in self.coworkers["finance"]["triggers"] if re.search(rf"\b{re.escape(w)}\b", text_lower))
        if finance_hits >= 1 and any(w in text_lower for w in ["tally", "accounting", "balance sheet", "p&l", "profit", "loss", "gst", "invoice", "emi", "budget", "excel"]):
            return "finance", self.coworkers["finance"]

        # 6. Coding & Software Engineering
        coding_hits = sum(1 for w in self.coworkers["coder"]["triggers"] if re.search(rf"\b{re.escape(w)}\b", text_lower))
        has_code_syntax = bool(re.search(r"(def\s+\w+|function\s+\w+|import\s+\w+|const\s+\w+|class\s+\w+|console\.log|print\(|<div|SELECT\s+.*FROM)", user_text))
        if coding_hits >= 2 or has_code_syntax or any(w in text_lower for w in ["write a code", "write a script", "fix this error", "python code", "javascript code", "create an api"]):
            return "coder", self.coworkers["coder"]

        # 7. Deep Reasoning & Logic
        reasoning_hits = sum(1 for w in self.coworkers["reasoner"]["triggers"] if w in text_lower)
        if reasoning_hits >= 1:
            return "reasoner", self.coworkers["reasoner"]

        # 8. Visual / Image Generation
        if any(w in text_lower for w in ["generate image", "create picture", "draw a", "photo of", "image of", "create a wallpaper"]):
            return "designer", self.coworkers["designer"]

        # 9. Dynamic Model Hunter for niche domains
        niche_match = re.search(r"(?:model for|specialist in|expert in)\s+([a-zA-Z0-9_\-]+)", text_lower)
        if niche_match:
            discovered_id = self.hunter.search_best_model(niche_match.group(1))
            if discovered_id:
                custom_worker = dict(self.coworkers["general"])
                custom_worker["name"] = f"HuggingFace Hunter ({niche_match.group(1).title()})"
                custom_worker["model"] = discovered_id
                custom_worker["icon"] = "🎯"
                return "custom", custom_worker

        # 10. Intelligent Global Tools Match (1,057 Tools)
        tool_query = re.search(r"(?:alternative to|similar to|open source|replace|alternative for|model for)\s+([a-zA-Z0-9\.\s\-\+]{2,30})", text_lower)
        if tool_query:
            matched_tool = self.tools_engine.get_tool(tool_query.group(1).strip())
            if matched_tool:
                cat = matched_tool.get("category", "").lower()
                cat_map = {
                    "cad": "cad",
                    "design": "designer",
                    "video editing": "video",
                    "coding": "coder",
                    "finance": "finance",
                    "productivity": "productivity",
                    "research": "researcher"
                }
                w_key = cat_map.get(cat, "general")
                return w_key, self.coworkers.get(w_key, self.coworkers["general"])

        # Default: General Supervisor
        return "general", self.coworkers["general"]
