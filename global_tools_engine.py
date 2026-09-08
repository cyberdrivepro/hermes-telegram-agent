"""
===============================================================================
  🌐 Global Workflow Tools & AI Ecosystem Engine
  - Database of 1,057 Software Tools across 8 Core Workflow Domains
  - 69 Curated Open-Source Alternatives with Direct GitHub Repositories
  - Task-Specialized Hugging Face AI Models for Every Category
  - UI-TARS 1.5 (7B) GUI/Desktop Perception & Automation Layer
===============================================================================
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent
CATALOG_PATH = ROOT_DIR / "tools_catalog.json"

class GlobalToolsEngine:
    """High-speed in-memory engine for querying tools, open-source alternatives, and AI models."""

    def __init__(self, catalog_path: Optional[Path] = None):
        self.catalog_path = catalog_path or CATALOG_PATH
        self.tools: List[Dict[str, Any]] = []
        self.tools_by_name: Dict[str, Dict[str, Any]] = {}
        self.tools_by_category: Dict[str, List[Dict[str, Any]]] = {}
        self.metadata: Dict[str, Any] = {}
        self._load_catalog()

    def _load_catalog(self):
        if not self.catalog_path.exists():
            return

        try:
            data = json.loads(self.catalog_path.read_text(encoding="utf-8"))
            self.metadata = data.get("metadata", {})
            self.tools = data.get("tools", [])

            for t in self.tools:
                clean_name = t["name"].lower().strip()
                self.tools_by_name[clean_name] = t
                
                cat = t.get("category", "General")
                if cat not in self.tools_by_category:
                    self.tools_by_category[cat] = []
                self.tools_by_category[cat].append(t)
        except Exception as e:
            print(f"Error loading tools catalog: {e}")

    def get_tool(self, name: str) -> Optional[Dict[str, Any]]:
        """Exact lookup by tool name (case-insensitive)."""
        clean = name.lower().strip()
        if clean in self.tools_by_name:
            return self.tools_by_name[clean]
        
        # Fuzzy match / prefix match
        for k, v in self.tools_by_name.items():
            if clean in k or k in clean:
                return v
        return None

    def search_tools(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search tools by name, category, or open-source equivalent."""
        q = query.lower().strip()
        results = []
        seen = set()

        for t in self.tools:
            name_lower = t["name"].lower()
            os_lower = t.get("open_source", "").lower()
            cat_lower = t.get("category", "").lower()

            score = 0
            if q == name_lower:
                score = 100
            elif q in name_lower:
                score = 80
            elif q == os_lower:
                score = 70
            elif q in os_lower:
                score = 50
            elif q in cat_lower:
                score = 30

            if score > 0 and t["name"] not in seen:
                seen.add(t["name"])
                results.append((score, t))

        results.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in results[:limit]]

    def get_category_tools(self, category: str) -> List[Dict[str, Any]]:
        """Get all tools in a specific category."""
        for cat, tools in self.tools_by_category.items():
            if cat.lower() == category.lower().strip():
                return tools
        return []

    def get_best_models_overview(self) -> Dict[str, Any]:
        """Get the top recommended Hugging Face model for each domain."""
        return self.metadata.get("best_models_by_workflow", {
            "CAD": {"model": "ADSKAILab/Zero-To-CAD-Qwen3-VL-2B", "use": "Image to executable CadQuery 3D parametric CAD"},
            "Design": {"model": "Qwen/Qwen-Image-Edit", "use": "Semantic, appearance, and text image editing"},
            "Video Editing": {"model": "Wan-AI/Wan2.2-TI2V-5B", "use": "Text/image-to-video generation (720p/24fps)"},
            "Coding": {"model": "Qwen/Qwen3-Coder-30B-A3B-Instruct", "use": "Full-stack agentic coding and debugging"},
            "Finance": {"model": "SUFE-AIFLM-Lab/Fin-R1", "use": "Financial reasoning, calculations, risk and balance sheet QA"},
            "General": {"model": "Qwen/Qwen3-235B-A22B-Instruct-2507", "use": "Complex multi-step general instructions"},
            "Productivity": {"model": "Qwen/Qwen3-VL-30B-A3B-Instruct", "use": "Multimodal screen, doc & slide understanding"},
            "Research": {"model": "Qwen/Qwen3-235B-A22B-Thinking-2507", "use": "Deep reasoning, science, math, academic literature"},
            "GUI_Desktop": {"model": "ByteDance-Seed/UI-TARS-1.5-7B", "use": "Desktop GUI perception, grounding, and interaction"}
        })

    def format_tool_card(self, tool: Dict[str, Any]) -> str:
        """Format a beautiful markdown card for Telegram display."""
        cat_icons = {
            "CAD": "📐",
            "Design": "🎨",
            "Video Editing": "🎬",
            "Coding": "💻",
            "Finance": "📊",
            "General": "🌐",
            "Productivity": "⚡",
            "Research": "🔬"
        }
        icon = cat_icons.get(tool.get("category"), "🛠️")
        
        lines = [
            f"{icon} *{tool['name']}* ({tool['category']})",
            "",
            f"• 🩵 *Open-Source Alternative:* `{tool['open_source']}`",
            f"• 🐙 *GitHub Repo:* [{tool['open_source']}]({tool['github']})",
            f"• 🧠 *Specialized AI Model:* `{tool['best_task_model']}`",
            f"• 🔗 *Model Hub:* [Hugging Face]({tool['hf_url']})",
            f"• 🖥️ *GUI Desktop Agent:* `{tool['gui_model']}`",
            f"• 🤖 *Agent Hub:* [Hugging Face]({tool['gui_hf_url']})"
        ]
        return "\n".join(lines)

    def format_category_summary(self, category: str) -> str:
        """Format a summary of tools in a category."""
        tools = self.get_category_tools(category)
        if not tools:
            available = ", ".join(self.tools_by_category.keys())
            return f"⚠️ Unknown category '{category}'. Available: {available}"

        models = self.get_best_models_overview().get(category, {})
        model_name = models.get("model", "Specialized Model")

        lines = [
            f"📂 *Category: {category} ({len(tools)} Tools)*",
            f"🧠 *Best AI Specialist Model:* `{model_name}`",
            f"🖥️ *Desktop GUI Agent:* `ByteDance-Seed/UI-TARS-1.5-7B`",
            "",
            "*Featured Tools & Open-Source Equivalents:*"
        ]
        for t in tools[:12]:
            lines.append(f"• *{t['name']}* ➔ `{t['open_source']}` ([GitHub]({t['github']}))")

        if len(tools) > 12:
            lines.append(f"\n_...and {len(tools) - 12} more tools. Use `/tool <name>` to inspect any tool._")

        return "\n".join(lines)
