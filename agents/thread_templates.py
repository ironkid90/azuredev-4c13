"""Helpers and ready-made system-message templates for creating agent threads.

Purpose: make it trivial to create properly-initialized threads with the
recommended ordering (system -> user) and standardized role-specific
instructions for generator / selector / verifier threads.

Usage example:
    from agents.thread_templates import create_client, init_thread, run_agent_once
    project = create_client()
    thread = init_thread(project, "generator", user_prompt="Fix failing test X")
    run = run_agent_once(project, thread.id, AGENT_ID)
"""
from __future__ import annotations

import time
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder


DEFAULT_TEMPLATES = {
    "generator": (
        "You are a focused code generator. When appropriate, return a unified-diff patch under a `patch` field."
        " Prioritize correctness and minimal, well-tested changes. Temperature=0.1"
    ),
    "selector": (
        "You are a conservative selector. Inspect the provided compressed context and action."
        " Return JSON with `route`: one of GENERATE, NO_OP, REFINE and `confidence` 0.0-1.0."
    ),
    "verifier": (
        "You are a deterministic verifier. Look for secrets, ensure patches are unified diffs,"
        " and run lightweight static checks. Return JSON with `verdict` (PASS|FAIL), `issues` and `confidence`."
    ),
}


def create_client(endpoint: Optional[str] = None) -> AIProjectClient:
    """Create an AIProjectClient using DefaultAzureCredential.

    If `endpoint` is not provided callers may pass a project-specific endpoint
    from `agents.config.ENDPOINT`.
    """
    if endpoint:
        return AIProjectClient(credential=DefaultAzureCredential(), endpoint=endpoint)
    return AIProjectClient(credential=DefaultAzureCredential())


def get_system_template(name: str) -> str:
    """Return a system instruction by name from DEFAULT_TEMPLATES.

    Raises KeyError if unknown.
    """
    return DEFAULT_TEMPLATES[name]


def init_thread(project: AIProjectClient, system_name: str, user_prompt: Optional[str] = None):
    """Create a thread, send a system message from a named template and optional user prompt.

    Returns the created thread object. Example system names: 'generator', 'selector', 'verifier'.
    """
    system_text = get_system_template(system_name)
    thread = project.agents.threads.create()
    project.agents.messages.create(thread_id=thread.id, role="system", content=system_text)
    if user_prompt:
        project.agents.messages.create(thread_id=thread.id, role="user", content=user_prompt)
    return thread


def run_agent_once(project: AIProjectClient, thread_id: str, agent_id: str, timeout: int = 30):
    """Create and process a run for the given thread and poll until completion.

    Returns the run object. This mirrors the polling behavior used across the repo.
    """
    run = project.agents.runs.create_and_process(thread_id=thread_id, agent_id=agent_id)
    start = time.time()
    while run.status not in ("succeeded", "failed") and time.time() - start < timeout:
        time.sleep(0.5)
        run = project.agents.runs.get(run.id)
    return run


def collect_messages(project: AIProjectClient, thread_id: str):
    """Return a simple list of messages (role, text) from a thread in ascending order."""
    out = []
    messages = project.agents.messages.list(thread_id=thread_id, order=ListSortOrder.ASCENDING)
    for m in messages:
        if m.text_messages:
            out.append({"role": m.role, "text": m.text_messages[-1].text.value})
    return out
