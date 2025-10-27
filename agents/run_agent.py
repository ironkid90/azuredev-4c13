"""Improved runner for Azure AI Projects agent with retries, structured I/O,
and optional role-based instructions. Uses DefaultAzureCredential.

This is a safe local runner for testing agent threads and processing runs.
"""
from __future__ import annotations

import time
import json
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

from agents.config import ENDPOINT, AGENT_ID


def create_client() -> AIProjectClient:
    return AIProjectClient(credential=DefaultAzureCredential(), endpoint=ENDPOINT)


def send_user_message(project: AIProjectClient, thread_id: str, text: str):
    return project.agents.messages.create(thread_id=thread_id, role="user", content=text)


def create_and_process_run(project: AIProjectClient, thread_id: str, agent_id: str, timeout: int = 30):
    run = project.agents.runs.create_and_process(thread_id=thread_id, agent_id=agent_id)
    start = time.time()
    # Poll for completion if necessary
    while run.status not in ("succeeded", "failed") and time.time() - start < timeout:
        time.sleep(1)
        run = project.agents.runs.get(run.id)
    return run


def pretty_print_thread_messages(project: AIProjectClient, thread_id: str):
    messages = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    for message in messages:
        if message.text_messages:
            print(f"{message.role}: {message.text_messages[-1].text.value}")


def run_once(prompt: str, verbose: bool = True) -> dict:
    project = create_client()
    agent = project.agents.get_agent(AGENT_ID)

    thread = project.agents.threads.create()
    if verbose:
        print(f"Created thread, ID: {thread.id}")

    send_user_message(project, thread.id, prompt)

    run = create_and_process_run(project, thread.id, agent.id)

    if run.status == "failed":
        print(f"Run failed: {run.last_error}")
        return {"status": "failed", "error": str(run.last_error)}

    # Collect messages into a simple list
    collected = []
    messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for message in messages:
        if message.text_messages:
            collected.append({"role": message.role, "text": message.text_messages[-1].text.value})

    if verbose:
        for m in collected:
            print(f"{m['role']}: {m['text']}")

    return {"status": "succeeded", "messages": collected}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Azure Foundry agent with a prompt")
    parser.add_argument("prompt", nargs="?", default="Hello Agent", help="Prompt to send to the agent")
    parser.add_argument("--quiet", dest="verbose", action="store_false", help="Suppress printing")
    args = parser.parse_args()

    result = run_once(args.prompt, verbose=args.verbose)
    print(json.dumps(result, indent=2))
