"""Simple CLI wrapper to create and run named threads using `thread_templates`.

Designed to be small and easily unit-testable (provides `main(argv)` that returns
an exit code). The tests in `tests/test_cli.py` mock `agents.thread_templates`.
"""
from __future__ import annotations

import argparse
from typing import List

from agents.thread_templates import create_client, init_thread, run_agent_once, collect_messages
from agents.config import AGENT_ID


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="agents-cli")
    parser.add_argument("role", choices=("generator", "selector", "verifier"), help="Which thread template to run")
    parser.add_argument("prompt", nargs="?", default=None, help="Optional user prompt to send")
    args = parser.parse_args(argv)

    project = create_client()
    thread = init_thread(project, args.role, user_prompt=args.prompt)
    run = run_agent_once(project, thread.id, AGENT_ID)

    if run.status == "failed":
        print(f"Run failed: {getattr(run, 'last_error', 'unknown')}")
        return 2

    messages = collect_messages(project, thread.id)
    for m in messages:
        print(f"{m['role']}: {m['text']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""Simple CLI wrapper to run a named thread template and print collected messages.

This CLI makes it easy to exercise generator/selector/verifier threads locally
and is designed to be tested via unit tests by mocking network operations.
"""
from __future__ import annotations

import argparse
import json
from typing import Optional

from agents.thread_templates import create_client, init_thread, run_agent_once, collect_messages
from agents.config import ENDPOINT, AGENT_ID


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run a named thread template against the configured agent")
    parser.add_argument("template", choices=("generator", "selector", "verifier"), help="Template to run")
    parser.add_argument("prompt", help="User prompt to send")
    parser.add_argument("--endpoint", help="Optional endpoint override")
    args = parser.parse_args(argv)

    project = create_client(args.endpoint or ENDPOINT)

    thread = init_thread(project, args.template, user_prompt=args.prompt)
    run = run_agent_once(project, thread.id, AGENT_ID)

    messages = collect_messages(project, thread.id)
    print(json.dumps({"status": run.status, "messages": messages}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
