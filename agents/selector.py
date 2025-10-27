"""Lightweight selector that decides whether to call the generator agent.

This starter uses simple heuristics and optional fallback to a selector agent.
"""
from __future__ import annotations

import re
from typing import Dict, Any


def compress_context(file_snippet: str, failing_tests: list | None = None) -> str:
    # Very simple compression: take first/last 40 lines, remove long strings
    lines = file_snippet.splitlines()
    if len(lines) <= 80:
        compressed = "\n".join(lines)
    else:
        compressed = "\n".join(lines[:40] + ["...CONTENTS_TRUNCATED..."] + lines[-40:])

    # remove very long literal strings to save tokens
    compressed = re.sub(r'""".*?"""', '"""<truncated>"""', compressed, flags=re.S)
    return compressed


def should_generate(compressed_context: str, action: str) -> Dict[str, Any]:
    """Rule-based decision. Returns {'route': 'GENERATE'|'NO_OP'|'REFINE', 'confidence': 0-1}.
    Replace with a model-based selector if desired.
    """
    # If action is explicitly a generation request
    if action.lower() in ("generate", "fix", "implement", "patch", "refactor"):
        return {"route": "GENERATE", "confidence": 0.9}

    # If failing tests mentioned, generate
    if compressed_context and "fail" in compressed_context.lower():
        return {"route": "GENERATE", "confidence": 0.75}

    # default: no-op with low confidence
    return {"route": "NO_OP", "confidence": 0.2}


if __name__ == "__main__":
    import argparse, json

    parser = argparse.ArgumentParser()
    parser.add_argument("action", help="Action name")
    parser.add_argument("--snippet", help="File snippet", default="")
    args = parser.parse_args()

    compressed = compress_context(args.snippet)
    decision = should_generate(compressed, args.action)
    print(json.dumps({"compressed": compressed[:2000], "decision": decision}, indent=2))
