"""Learning helpers for the Codex-driven workflow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from scripts import storage


LOGGER = logging.getLogger(__name__)
LEARNING_LIST_ORDER = {"doing": 0, "todo": 1, "done": 2, "none": 3}


def view_queue(root: Path | None = None) -> list[dict[str, Any]]:
    return sync_queue(root)


def sync_queue(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or storage.get_repo_root()
    current_queue = storage.read_queue(base)
    items_by_id = {item["id"]: item for item in storage.list_content_items(root=base)}
    normalized_entries: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for entry in current_queue:
        item = items_by_id.get(entry["doc_id"])
        if item is None:
            LOGGER.warning("Dropping queue entry for missing content item: %s", entry["doc_id"])
            continue
        normalized_entry = _desired_queue_entry(item, base)
        if normalized_entry is None:
            LOGGER.info("Removing queue entry for non-learning item: %s", item["id"])
            continue
        normalized_entries.append(normalized_entry)
        seen_ids.add(item["id"])

    for item in sorted(items_by_id.values(), key=lambda current_item: current_item["id"]):
        if item["id"] in seen_ids:
            continue
        normalized_entry = _desired_queue_entry(item, base)
        if normalized_entry is None:
            continue
        LOGGER.info("Rebuilding missing queue entry for item: %s", item["id"])
        normalized_entries.append(normalized_entry)

    storage.write_queue(normalized_entries, base)
    return storage.read_queue(base)


def get_next_learning_target(root: Path | None = None) -> dict[str, Any]:
    base = root or storage.get_repo_root()
    queue = sync_queue(base)

    for entry in queue:
        if entry["status"] == "done":
            continue
        item = storage.read_content_item_by_id(entry["doc_id"], base)
        mode = _next_learning_mode(item, base)
        LOGGER.info("Selected next queue item %s in mode %s", item["id"], mode)
        return {
            "item": item,
            "queue_entry": entry,
            "mode": mode,
        }

    raise ValueError("no accepted or learning items available in queue")


def list_learning_items(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or storage.get_repo_root()
    queue = sync_queue(base)
    queue_entries = {entry["doc_id"]: entry for entry in queue}
    rows: list[dict[str, Any]] = []

    for item in storage.list_content_items(root=base):
        if item["status"] not in {"accepted", "learning", "done"}:
            continue
        state = storage.read_learning_state(item["id"], base) if storage.learning_state_exists(item["id"], base) else None
        queue_entry = queue_entries.get(item["id"])
        rows.append(
            {
                "item": item,
                "state": state,
                "queue_entry": queue_entry,
                "next_action": describe_next_action(item, state),
            }
        )

    return sorted(
        rows,
        key=lambda row: (
            LEARNING_LIST_ORDER.get(
                "none" if row["queue_entry"] is None else row["queue_entry"]["status"],
                99,
            ),
            -row["item"]["priority"],
            row["item"]["title"].lower(),
        ),
    )


def read_status(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    base = root or storage.get_repo_root()
    sync_queue(base)
    item = storage.read_content_item_by_id(doc_id, base)
    state = storage.read_learning_state(doc_id, base) if storage.learning_state_exists(doc_id, base) else None
    queue_entry = storage.get_queue_entry(doc_id, base)
    return {
        "item": item,
        "state": state,
        "queue_entry": queue_entry,
        "open_questions": [] if state is None else list(state["questions"]),
        "next_action": describe_next_action(item, state),
    }


def _desired_queue_entry(item: dict[str, Any], root: Path) -> dict[str, Any] | None:
    state = storage.read_learning_state(item["id"], root) if storage.learning_state_exists(item["id"], root) else None

    if item["status"] in {"candidate", "rejected", "archived"}:
        return None
    if item["status"] == "done" or (state is not None and state["status"] == "done"):
        return storage.create_queue_entry(item["id"], item["priority"], "done")
    if item["status"] == "learning" or state is not None:
        return storage.create_queue_entry(item["id"], item["priority"], "doing")
    if item["status"] == "accepted":
        return storage.create_queue_entry(item["id"], item["priority"], "todo")
    return None


def _next_learning_mode(item: dict[str, Any], root: Path) -> str:
    if not storage.learning_state_exists(item["id"], root):
        return "outline"

    state = storage.read_learning_state(item["id"], root)
    if not state["outline_generated"]:
        return "outline"
    return "deep_dive"


def describe_next_action(
    item: dict[str, Any],
    state: dict[str, Any] | None,
) -> str:
    if state is not None:
        if not state["outline_generated"]:
            return f"Run pkls learn prompt --id {item['id']} --mode outline"
        if state["status"] == "done":
            return "Review generated learning outputs"
        return f"Run pkls learn prompt --id {item['id']} --mode deep_dive"
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
    return "Resume learning in Codex"
