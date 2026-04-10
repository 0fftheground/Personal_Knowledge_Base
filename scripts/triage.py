"""Triage helpers for the agent-driven workflow."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from scripts import storage


LOGGER = logging.getLogger(__name__)
TRIAGE_SECTIONS = {
    "summary": "summary",
    "key points": "key_points",
    "recommendation": "recommendation",
    "reason": "reason",
}


def list_candidates(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or storage.get_repo_root()
    return [
        item
        for item in storage.list_content_items(root=base)
        if item["status"] == "candidate"
    ]


def list_candidate_reviews(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or storage.get_repo_root()
    rows: list[dict[str, Any]] = []

    for item in sorted(
        list_candidates(base),
        key=lambda current_item: (-current_item["priority"], current_item["title"].lower()),
    ):
        rows.append(
            {
                "item": item,
                "triage_card": read_triage_card(item["id"], base),
            }
        )

    return rows


def list_candidates_needing_triage_card(
    limit: int | None = None,
    root: Path | None = None,
) -> list[dict[str, Any]]:
    rows = [
        row
        for row in list_candidate_reviews(root)
        if row["triage_card"] is None
    ]
    if limit is None:
        return rows
    return rows[:limit]


def accept_candidate(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    item = _load_candidate(doc_id, root)
    item["status"] = "accepted"
    item["manual_decision"] = "accept"
    storage.write_content_item(item, root)
    entry = storage.create_queue_entry(item["id"], item["priority"], "todo")
    storage.upsert_queue_entry(entry, root)
    LOGGER.info("Accepted candidate: %s", doc_id)
    return item


def reject_candidate(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    item = _load_candidate(doc_id, root)
    item["status"] = "rejected"
    item["manual_decision"] = "reject"
    storage.write_content_item(item, root)
    storage.remove_queue_entry(doc_id, root)
    LOGGER.info("Rejected candidate: %s", doc_id)
    return item


def defer_candidate(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    item = _load_candidate(doc_id, root)
    item["priority"] = 0.0
    item["manual_decision"] = "later"
    storage.write_content_item(item, root)
    LOGGER.info("Deferred candidate by lowering priority to 0.0: %s", doc_id)
    return item


def read_triage_card(doc_id: str, root: Path | None = None) -> dict[str, Any] | None:
    card_path = storage.get_triage_cards_root(root) / f"{doc_id}.md"
    if not card_path.exists():
        return None

    text = card_path.read_text(encoding="utf-8")
    card = {
        "id": doc_id,
        "summary": "",
        "key_points": [],
        "recommendation": "",
        "reason": "",
    }
    current_section: str | None = None
    section_lines: list[str] = []

    def flush_section() -> None:
        nonlocal current_section, section_lines
        if current_section is None:
            return
        if current_section == "key_points":
            key_points = [
                line.strip()[1:].strip()
                for line in section_lines
                if line.strip().startswith("-") and len(line.strip()) > 1
            ]
            card["key_points"] = key_points
        else:
            value = "\n".join(line.strip() for line in section_lines if line.strip()).strip()
            card[current_section] = value
        current_section = None
        section_lines = []

    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- recommendation:") and not card["recommendation"]:
            card["recommendation"] = stripped.split(":", 1)[1].strip()
            continue
        if stripped.startswith("## "):
            flush_section()
            current_section = TRIAGE_SECTIONS.get(stripped[3:].strip().lower())
            continue
        if current_section is not None:
            section_lines.append(line)

    flush_section()
    return card


def is_triage_card_complete(card: dict[str, Any] | None) -> bool:
    if card is None:
        return False
    summary = card.get("summary", "").strip()
    key_points = [point.strip() for point in card.get("key_points", []) if point.strip()]
    recommendation = card.get("recommendation", "").strip()
    reason = card.get("reason", "").strip()
    return bool(summary and key_points and recommendation and reason)


def _load_candidate(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    item = storage.read_content_item_by_id(doc_id, root)
    if item["status"] != "candidate":
        raise ValueError(f"item is not a candidate: {doc_id}")
    return item
