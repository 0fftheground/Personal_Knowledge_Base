"""Minimal learning helpers used by the CLI layer."""

from __future__ import annotations

import logging
from pathlib import Path

from scripts import storage


LOGGER = logging.getLogger(__name__)


def view_queue(root: Path | None = None) -> list[dict[str, object]]:
    return storage.read_queue(root)


def start_learning(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = storage.read_content_item_by_id(doc_id, root)
    if item["status"] not in {"accepted", "learning"}:
        raise ValueError(f"item must be accepted before learning starts: {doc_id}")
    if storage.learning_state_exists(doc_id, root):
        raise ValueError(f"learning state already exists for {doc_id}; use resume")
    return _process_next_chunk(item, initialize=True, root=root)


def resume_learning(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = storage.read_content_item_by_id(doc_id, root)
    if not storage.learning_state_exists(doc_id, root):
        raise FileNotFoundError(f"learning state not found for {doc_id}")
    return _process_next_chunk(item, initialize=False, root=root)


def learn_next(root: Path | None = None) -> dict[str, object]:
    base = root or storage.get_repo_root()
    for entry in storage.read_queue(base):
        item = storage.read_content_item_by_id(entry["doc_id"], base)
        if item["status"] == "done":
            continue
        if storage.learning_state_exists(item["id"], base):
            return _process_next_chunk(item, initialize=False, root=base)
        if item["status"] == "accepted":
            return _process_next_chunk(item, initialize=True, root=base)
    raise ValueError("no accepted or learning items available in queue")


def read_status(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = storage.read_content_item_by_id(doc_id, root)
    state = storage.read_learning_state(doc_id, root) if storage.learning_state_exists(doc_id, root) else None
    return {
        "item": item,
        "state": state,
        "open_questions": [] if state is None else list(state["questions"]),
        "next_action": _status_next_action(item, state),
    }


def _process_next_chunk(
    item: dict[str, object],
    *,
    initialize: bool,
    root: Path | None = None,
) -> dict[str, object]:
    base = root or storage.get_repo_root()
    text = storage.read_raw_text_for_item(item, base)
    chunks = _chunk_text(text)

    if initialize:
        state = storage.create_learning_state(
            doc_id=item["id"],
            progress=0.0,
            current_chunk=0,
            chunks_total=len(chunks),
            key_points=[],
            questions=[],
            next_action=_next_action(0, len(chunks)),
            status="learning",
        )
    else:
        state = storage.read_learning_state(item["id"], base)

    if state["current_chunk"] >= state["chunks_total"]:
        state["progress"] = 1.0
        state["status"] = "done"
        state["next_action"] = "Learning complete"
        storage.write_learning_state(state, base)
        item["status"] = "done"
        storage.write_content_item(item, base)
        storage.upsert_queue_entry(
            storage.create_queue_entry(item["id"], item["priority"], "done"),
            base,
        )
        _write_outputs(item, state, base)
        LOGGER.info("Learning already complete for %s", item["id"])
        return {"item": item, "state": state}

    chunk_index = state["current_chunk"]
    chunk = chunks[chunk_index]
    key_point = _extract_key_point(chunk)
    question = f"What should I verify from chunk {chunk_index + 1} of {item['title']}?"

    state["key_points"].append(key_point)
    state["questions"].append(question)
    state["current_chunk"] += 1
    state["progress"] = round(state["current_chunk"] / state["chunks_total"], 3)
    state["status"] = "done" if state["current_chunk"] == state["chunks_total"] else "learning"
    state["next_action"] = _next_action(state["current_chunk"], state["chunks_total"])

    item["status"] = "done" if state["status"] == "done" else "learning"
    queue_status = "done" if state["status"] == "done" else "doing"

    storage.write_learning_state(state, base)
    storage.write_content_item(item, base)
    storage.upsert_queue_entry(
        storage.create_queue_entry(item["id"], item["priority"], queue_status),
        base,
    )
    _write_outputs(item, state, base)

    LOGGER.info(
        "Processed chunk %s/%s for %s",
        state["current_chunk"],
        state["chunks_total"],
        item["id"],
    )
    return {"item": item, "state": state}


def _chunk_text(text: str) -> list[str]:
    chunks = [part.strip() for part in text.split("\n\n") if part.strip()]
    if chunks:
        return chunks
    stripped = text.strip()
    return [stripped] if stripped else ["Empty content."]


def _extract_key_point(chunk: str) -> str:
    line = chunk.splitlines()[0].strip().lstrip("#- ").strip()
    return line or "Empty chunk."


def _next_action(current_chunk: int, chunks_total: int) -> str:
    if current_chunk >= chunks_total:
        return "Learning complete"
    return f"Process chunk {current_chunk + 1} of {chunks_total}"


def _status_next_action(
    item: dict[str, object],
    state: dict[str, object] | None,
) -> str:
    if state is not None:
        if not state["outline_generated"]:
            return f"Run pkls learn prompt --id {item['id']} --mode outline"
        return str(state["next_action"])
    if item["status"] == "accepted":
        return f"Run pkls learn prompt --id {item['id']} --mode outline"
    if item["status"] == "candidate":
        return "Await triage decision"
    if item["status"] == "rejected":
        return "No action required"
    if item["status"] == "archived":
        return "Item is archived"
    if item["status"] == "done":
        return "Review generated learning outputs"
    return "Resume learning"


def _write_outputs(item: dict[str, object], state: dict[str, object], root: Path) -> None:
    output_dir = storage.get_learning_outputs_root(root) / item["id"]
    output_dir.mkdir(parents=True, exist_ok=True)

    if state["outline_generated"] or state["document_outline"] or state["core_summary"]:
        outline = (
            f"# Outline for {item['title']}\n\n"
            "## Core Summary\n\n"
            f"{state['core_summary'] or 'Outline not generated yet.'}\n\n"
            "## Document Outline\n\n"
            + ("\n".join(f"- {point}" for point in state["document_outline"]) or "- Outline not generated yet.")
            + "\n"
        )
        (output_dir / "outline.md").write_text(outline, encoding="utf-8")

    summary = (
        f"# {item['title']}\n\n"
        f"- progress: {state['progress']}\n"
        f"- status: {state['status']}\n\n"
        "## Key Points\n\n"
        + "\n".join(f"- {point}" for point in state["key_points"])
        + "\n"
    )
    insights = (
        f"# Insights for {item['title']}\n\n"
        + "\n".join(f"- Review: {point}" for point in state["key_points"])
        + "\n"
    )
    qa = (
        f"# Questions for {item['title']}\n\n"
        + "\n".join(f"- {question}" for question in state["questions"])
        + "\n"
    )

    (output_dir / "summary.md").write_text(summary, encoding="utf-8")
    (output_dir / "insights.md").write_text(insights, encoding="utf-8")
    (output_dir / "qa.md").write_text(qa, encoding="utf-8")
