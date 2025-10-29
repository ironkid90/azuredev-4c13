"""CLI wrapper to create and run named thread templates (generator/selector/verifier).

Supports a safe --dry-run mode (no network calls) for quick local testing. Designed
to be easy to unit-test (exposes main(argv)).
"""
from __future__ import annotations

import argparse
import json
from typing import List, Optional

from agents.thread_templates import create_client, init_thread, run_agent_once, collect_messages
from agents.config import ENDPOINT, AGENT_ID


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a named thread template against the configured agent")
    parser.add_argument("template", choices=("generator", "selector", "verifier"), help="Template to run")
    parser.add_argument("prompt", nargs="?", default=None, help="User prompt to send")
    parser.add_argument("--endpoint", help="Optional endpoint override")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true", help="Simulate thread creation and run locally without calling Azure")
    args = parser.parse_args(argv)

    if args.dry_run:
        thread_id = "dry-thread-1"
        print(f"[dry-run] Created thread, ID: {thread_id}")
        simulated_messages = [{"role": "assistant", "text": "<simulated reply>"}]
        print(json.dumps({"status": "succeeded", "messages": simulated_messages}, indent=2))
        return 0

    # Real run: create client (may use ENDPOINT from config if override not provided)
    project = create_client(args.endpoint or ENDPOINT)

    thread = init_thread(project, args.template, user_prompt=args.prompt)
    run = run_agent_once(project, thread.id, AGENT_ID)

    messages = collect_messages(project, thread.id)
    print(json.dumps({"status": run.status, "messages": messages}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
