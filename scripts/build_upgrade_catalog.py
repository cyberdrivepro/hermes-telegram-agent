"""Trace source roadmap ranges without counting ranges as implemented features."""
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ("AGI_OMEGA_ULTRA_BLUEPRINT.md", "AGI_ULTRA_UPGRADE_MASTERPLAN.md")

# These are scoped implementations of parts of each source family, not claims
# that every numbered vector in the source range is complete.
MAPPINGS = {
    "Tree-of-Thoughts": ["reasoning.search"],
    "Monte Carlo Tree Search": ["reasoning.search"],
    "Sub-Goal Task Decomposition": ["reasoning.plan"],
    "In-Memory SQLite": ["data.sql"],
    "SQLite Live In-Memory": ["data.sql"],
    "EXPLAIN Query Plan": ["data.sql"],
    "Complex SQL Query": ["data.sql"],
    "Symbolic Mathematics": ["math.symbolic"],
    "Linear Algebra": ["math.linear_algebra"],
    "Automated Video Clips": ["media.clip"],
    "Auto-Captioning": ["media.subtitles", "media.clip"],
    "Google Forms Schema": ["survey.bundle"],
    "Google AppScript": ["survey.bundle"],
    "HTML5 Survey": ["survey.bundle"],
    "Excel": ["survey.bundle"],
    "Parametric OpenSCAD": ["cad.motor_bracket"],
    "Mesh STL/OBJ": ["cad.motor_bracket"],
    "Blueprint": ["cad.motor_bracket"],
    "Financial Modeling": ["finance.dcf"],
    "EMI": ["finance.amortization"],
    "GST": ["finance.invoice"],
    "Source Code": ["security.sast"],
    "Code Security": ["security.sast"],
    "Log Analyzer": ["security.logs"],
}


def build():
    groups = []
    for filename in SOURCES:
        domain = ""
        for number, line in enumerate((ROOT / filename).read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("### ") and "DOMAIN" in line:
                domain = line[4:]
            match = re.match(r"^- \*\*(\d+)-(\d+)(\+?):\s*(.*?)\*\*:\s*(.*)$", line)
            if not match:
                continue
            low, high, open_end, title, description = match.groups()
            capabilities = sorted({cap for token, names in MAPPINGS.items() if token in title for cap in names})
            groups.append({"id": f"{'omega' if 'OMEGA' in filename else 'master'}-{low}-{high}",
                           "source": filename, "source_line": number, "source_domain": domain,
                           "vector_start": int(low), "vector_end": int(high), "open_ended": bool(open_end),
                           "title": title, "requested_scope": description,
                           "status": "partial" if capabilities else "planned_or_legacy_unverified",
                           "implemented_subset": capabilities})
    return {"schema_version": 1,
            "counting_rule": "Each record is a source feature family. Number ranges are not individually specified or implemented tests. Partial means only the capability subset documented in OMEGA_IMPLEMENTATION.md exists.",
            "source_issues": ["The Omega CAD ranges 771-790 and 772-810 overlap in the supplied blueprint.",
                              "Domains 17-20 are grouped together in the supplied Omega blueprint.",
                              "The masterplan title says 500+ while its ranges extend through 850+.",
                              "True AGI, zero refusal, 100% correctness, and universal sub-second acquisition are not measurable completed capabilities."],
            "groups": groups}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = json.dumps(build(), indent=2, ensure_ascii=False) + "\n"
    path = ROOT / "upgrade_catalog.json"
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != output:
            raise SystemExit("Upgrade catalog is stale; run scripts/build_upgrade_catalog.py")
    else:
        path.write_text(output, encoding="utf-8")
    print(f"Catalog contains {len(build()['groups'])} source feature families; no inflated implementation count.")
