"""
================================================================================
  🌐 Tavily Search & Research Engine (Tavily Agent Setup SKILL.md Implementation)
  Real-time web search, content extraction, site mapping, and deep research.
================================================================================
"""

import os
import json
import urllib.request
import urllib.parse
from typing import Dict, List, Any, Optional

DEFAULT_TAVILY_KEY = "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"
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", DEFAULT_TAVILY_KEY).strip()
TAVILY_BASE_URL = "https://api.tavily.com"


class TavilyEngine:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", DEFAULT_TAVILY_KEY).strip()

    def search(
        self,
        query: str,
        search_depth: str = "basic",
        max_results: int = 5,
        include_answer: bool = True
    ) -> Dict[str, Any]:
        """Execute Tavily real-time web search with AI summary answer."""
        url = f"{TAVILY_BASE_URL}/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "search_depth": search_depth,
            "max_results": max_results,
            "include_answer": include_answer
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "CyberMaster-Tavily/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "query": query,
                    "answer": data.get("answer", ""),
                    "results": [
                        {
                            "title": r.get("title"),
                            "url": r.get("url"),
                            "content": r.get("content"),
                            "score": r.get("score")
                        }
                        for r in data.get("results", [])
                    ]
                }
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}

    def extract(self, urls: List[str]) -> Dict[str, Any]:
        """Extract clean markdown content from given URLs without paywalls or bot blockers."""
        url = f"{TAVILY_BASE_URL}/extract"
        payload = {
            "api_key": self.api_key,
            "urls": urls
        }
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "CyberMaster-Tavily/1.0"}
        )

        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return {
                    "success": True,
                    "results": data.get("results", [])
                }
        except Exception as e:
            return {"success": False, "error": str(e), "results": []}

    def research(self, topic: str) -> str:
        """Runs deep multi-source research on a topic and returns formatted summary."""
        res = self.search(topic, search_depth="advanced", max_results=6, include_answer=True)
        if not res.get("success"):
            return f"⚠️ Tavily Research Error: {res.get('error')}"

        answer = res.get("answer")
        results = res.get("results", [])

        out = []
        if answer:
            out.append(f"🧠 **AI Research Synthesis:**\n{answer}\n")

        out.append("📚 **Top Verified Sources & Key Findings:**")
        for i, r in enumerate(results, 1):
            out.append(f"{i}. [{r.get('title')}]({r.get('url')})\n   {r.get('content', '')[:250]}...")

        return "\n\n".join(out)
