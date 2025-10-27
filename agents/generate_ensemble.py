"""Generate multiple candidate responses (ensemble) from the Azure agent and
pick the best with a simple reranker. Intended as a starter: replace the
reranker with a deterministic verifier or a low-temp verifier agent.

Usage: python agents/generate_ensemble.py "Fix test foo"
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.ai.agents.models import ListSortOrder

from agents.config import ENDPOINT, AGENT_ID


def create_client() -> AIProjectClient:
    return AIProjectClient(credential=DefaultAzureCredential(), endpoint=ENDPOINT)


def _single_variant(prompt: str, system_instruction: str) -> Dict:
    project = create_client()
    agent = project.agents.get_agent(AGENT_ID)
    thread = project.agents.threads.create()

    # send system instruction as a message before the user prompt
    project.agents.messages.create(thread_id=thread.id, role="system", content=system_instruction)
    project.agents.messages.create(thread_id=thread.id, role="user", content=prompt)

    run = project.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
    start = time.time()
    while run.status not in ("succeeded", "failed") and time.time() - start < 30:
        time.sleep(0.5)
        run = project.agents.runs.get(run.id)

    result = {"status": run.status, "variant_instruction": system_instruction, "thread_id": thread.id, "messages": []}
    if run.status == "failed":
        result["error"] = str(run.last_error)
        return result

    messages = project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)
    for m in messages:
        if m.text_messages:
            result["messages"].append({"role": m.role, "text": m.text_messages[-1].text.value})

    return result


def generate_ensemble(prompt: str, variants: List[Dict[str, str]], max_workers: int = 4) -> Dict:
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_single_variant, prompt, v["system"]): v for v in variants}
        for fut in as_completed(futures):
            try:
                results.append(fut.result())
            except Exception as e:
                results.append({"status": "error", "error": str(e)})

    # Simple reranker: prefer succeeded runs and longest textual reply. Replace
    # with verifier-based ranking for real usage.
    succeeded = [r for r in results if r.get("status") == "succeeded" and r.get("messages")]
    if not succeeded:
        return {"chosen": None, "candidates": results}

    def score(r: Dict) -> int:
        text = "\n".join(m["text"] for m in r.get("messages", []))
        return len(text)

    chosen = max(succeeded, key=score)
    return {"chosen": chosen, "candidates": results}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="Prompt to send to generator")
    parser.add_argument("--workers", type=int, default=3, help="Parallel variants to run")
    args = parser.parse_args()

    # Define simple variant instructions. These should be replaced with
    # curated system prompts or with agent configurations in Foundry.
    variants = [
        {"name": "low_temp", "system": "You are a precise code generator. Respond concisely. Temperature=0.1"},
        {"name": "medium", "system": "You are a helpful coder. Provide a patch if needed. Temperature=0.3"},
        {"name": "creative", "system": "You are an experimental assistant. Suggest alternative fixes. Temperature=0.7"},
    ]

    out = generate_ensemble(args.prompt, variants, max_workers=args.workers)
    print(json.dumps(out, indent=2))
