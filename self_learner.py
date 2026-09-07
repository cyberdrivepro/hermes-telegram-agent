"""
================================================================================
  🧠 Autonomous Continuous Self-Learning Engine
  Persistent long-term memory, preference learning, correction tracking,
  and dynamic knowledge distillation.
================================================================================
"""

import os
import re
import json
import time
import datetime
from typing import Dict, List, Any, Optional


class SelfLearningEngine:
    """Manages persistent long-term memories, user preferences, and autonomous learning."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.memory_file = os.path.join(self.base_dir, "self_memory.json")
        self.data: Dict[str, Any] = {
            "preferences": {},   # chat_id -> list of strings
            "facts": {},         # chat_id -> list of facts
            "corrections": {},   # chat_id -> list of corrections
            "global_learnings": []
        }
        self.load()

    def load(self):
        """Loads memory store from disk."""
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self.data.update(loaded)
            except Exception:
                pass

    def save(self):
        """Persists memory store to disk."""
        try:
            with open(self.memory_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def detect_and_learn(self, chat_id: int, user_text: str) -> Optional[str]:
        """Inspects user message for explicit or implicit learning cues and saves them."""
        cid = str(chat_id)
        if cid not in self.data["preferences"]:
            self.data["preferences"][cid] = []
        if cid not in self.data["facts"]:
            self.data["facts"][cid] = []
        if cid not in self.data["corrections"]:
            self.data["corrections"][cid] = []

        learned_notice = None

        # 1. "Remember that..." / "Yaad rakhna..."
        rem_match = re.search(r"(?:remember\s+that|yaad\s+rakhna\s+ki|note\s+that|keep\s+in\s+mind\s+that)\s+(.+)", user_text, re.IGNORECASE)
        if rem_match:
            fact = rem_match.group(1).strip()
            if fact and fact not in self.data["facts"][cid]:
                self.data["facts"][cid].append(fact)
                self.save()
                learned_notice = f"🧠 *Learned & Saved to Memory:* \"{fact}\""

        # 2. "My name is..." / "Mera naam ... hai"
        name_match = re.search(r"(?:my\s+name\s+is|call\s+me|mera\s+naam\s+([a-zA-Z0-9_]+)\s+hai)\s*([a-zA-Z0-9_]+)?", user_text, re.IGNORECASE)
        if name_match:
            name = (name_match.group(2) or name_match.group(1) or "").strip()
            if name and len(name) > 1 and name.lower() not in ["a", "the", "what", "is"]:
                fact = f"User's name is {name}"
                if fact not in self.data["facts"][cid]:
                    self.data["facts"][cid].append(fact)
                    self.save()
                    learned_notice = f"🧠 *Identity Learned:* I will remember your name is **{name}**!"

        # 3. "Always..." / "Never..." / "From now on..." / "Hamesha..."
        pref_match = re.search(r"(?:always|never|from\s+now\s+on|hamesha|aage\s+se)\s+(.+)", user_text, re.IGNORECASE)
        if pref_match and not rem_match:
            pref = pref_match.group(0).strip()
            if pref and len(pref) > 8 and pref not in self.data["preferences"][cid]:
                self.data["preferences"][cid].append(pref)
                self.save()
                learned_notice = f"⚙️ *Preference Learned:* \"{pref}\""

        # 4. "No, actually..." / "Galat hai, sahi ye hai..."
        corr_match = re.search(r"(?:no,?\s+actually|that\'?s\s+wrong|galat\s+hai|correction:?)\s+(.+)", user_text, re.IGNORECASE)
        if corr_match:
            corr = corr_match.group(1).strip()
            if corr and corr not in self.data["corrections"][cid]:
                self.data["corrections"][cid].append(corr)
                self.save()
                learned_notice = f"📝 *Correction Recorded:* \"{corr}\""

        return learned_notice

    def get_learning_context(self, chat_id: int) -> str:
        """Returns personalized memory prompt block for this chat."""
        cid = str(chat_id)
        facts = self.data["facts"].get(cid, [])
        prefs = self.data["preferences"].get(cid, [])
        corrs = self.data["corrections"].get(cid, [])

        if not facts and not prefs and not corrs:
            return ""

        lines = ["\nAUTONOMOUS LEARNED MEMORIES & PREFERENCES FOR THIS USER:"]
        if facts:
            lines.append("• Known Facts: " + "; ".join(facts[-5:]))
        if prefs:
            lines.append("• User Rules & Preferences: " + "; ".join(prefs[-5:]))
        if corrs:
            lines.append("• Corrections to Remember: " + "; ".join(corrs[-5:]))

        return "\n".join(lines) + "\n"

    def list_memories(self, chat_id: int) -> str:
        """Formats all stored memories for /memory command."""
        cid = str(chat_id)
        facts = self.data["facts"].get(cid, [])
        prefs = self.data["preferences"].get(cid, [])
        corrs = self.data["corrections"].get(cid, [])

        if not facts and not prefs and not corrs:
            return "🧠 *No memories stored yet!*\n\nTell me things like:\n• _'Remember that I run a web agency'_ \n• _'Always reply in bullet points'_ \n• _'My name is Alex'_"

        out = ["🧠 *Autonomous Self-Learned Memory:*\n"]
        if facts:
            out.append("📌 *Remembered Facts:*")
            for f in facts:
                out.append(f"• {f}")
            out.append("")

        if prefs:
            out.append("⚙️ *User Preferences & Rules:*")
            for p in prefs:
                out.append(f"• {p}")
            out.append("")

        if corrs:
            out.append("📝 *Past Corrections:*")
            for c in corrs:
                out.append(f"• {c}")
            out.append("")

        out.append("💡 *Commands:* Use `/forget` to clear your memory.")
        return "\n".join(out)

    def forget(self, chat_id: int) -> str:
        """Clears all stored memories for this chat."""
        cid = str(chat_id)
        if cid in self.data["facts"]:
            self.data["facts"][cid] = []
        if cid in self.data["preferences"]:
            self.data["preferences"][cid] = []
        if cid in self.data["corrections"]:
            self.data["corrections"][cid] = []
        self.save()
        return "🧹 *All personalized learned memories and preferences have been reset!*"
