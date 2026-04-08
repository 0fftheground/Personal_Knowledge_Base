"""Minimal triage helpers used by the CLI layer."""

from __future__ import annotations

import logging
from pathlib import Path

from scripts import storage


LOGGER = logging.getLogger(__name__)

RECOMMENDATIONS_BY_CONTENT_TYPE = {
    "paper": "learn",
    "blog": "skim",
    "github": "skim",
    "book": "learn",
}


def run_triage(root: Path | None = None) -> list[str]:
    base = root or storage.get_repo_root()
    processed_ids: list[str] = []

    for item in storage.list_content_items(root=base, source_type="auto"):
        card_path = _triage_card_path(item["id"], base)
        if item["status"] != "candidate" or card_path.exists():
            continue

        text = storage.read_raw_text_for_item(item, base)
        summary = _build_summary(text)
        key_points = _build_key_points(text)
        recommendation = RECOMMENDATIONS_BY_CONTENT_TYPE[item["content_type"]]
        reason = f"Deterministic CLI triage for {item['content_type']} content."
        relevance = "Candidate from auto pipeline pending manual decision."

        item["ai_recommendation"] = recommendation
        storage.write_content_item(item, base)
        _write_triage_card(
            card_path=card_path,
            title=item["title"],
            doc_id=item["id"],
            summary=summary,
            key_points=key_points,
            relevance=relevance,
            recommendation=recommendation,
            reason=reason,
        )
        processed_ids.append(item["id"])
        LOGGER.info("Triaged auto item: %s", item["id"])

    return processed_ids


def list_candidates(root: Path | None = None) -> list[dict[str, object]]:
    base = root or storage.get_repo_root()
    return [
        item
        for item in storage.list_content_items(root=base)
        if item["status"] == "candidate"
    ]


def accept_candidate(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = _load_candidate(doc_id, root)
    item["status"] = "accepted"
    item["manual_decision"] = "accept"
    storage.write_content_item(item, root)
    entry = storage.create_queue_entry(item["id"], item["priority"], "todo")
    storage.upsert_queue_entry(entry, root)
    LOGGER.info("Accepted candidate: %s", doc_id)
    return item


def reject_candidate(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = _load_candidate(doc_id, root)
    item["status"] = "rejected"
    item["manual_decision"] = "reject"
    storage.write_content_item(item, root)
    storage.remove_queue_entry(doc_id, root)
    LOGGER.info("Rejected candidate: %s", doc_id)
    return item


def defer_candidate(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = _load_candidate(doc_id, root)
    item["priority"] = 0.0
    item["manual_decision"] = "later"
    storage.write_content_item(item, root)
    LOGGER.info("Deferred candidate by lowering priority to 0.0: %s", doc_id)
    return item


def _load_candidate(doc_id: str, root: Path | None = None) -> dict[str, object]:
    item = storage.read_content_item_by_id(doc_id, root)
    if item["source_type"] != "auto":
        raise ValueError(f"triage decisions only apply to auto items: {doc_id}")
    if item["status"] != "candidate":
        raise ValueError(f"item is not a candidate: {doc_id}")
    return item


def _triage_card_path(doc_id: str, root: Path) -> Path:
    return storage.get_triage_cards_root(root) / f"{doc_id}.md"


def _build_summary(text: str) -> str:
    paragraphs = _content_units(text)
    return paragraphs[0][:240]


def _build_key_points(text: str) -> list[str]:
    points: list[str] = []
    for unit in _content_units(text):
        cleaned = unit.lstrip("#- ").strip()
        if cleaned and cleaned not in points:
            points.append(cleaned[:160])
        if len(points) == 3:
            break
    if not points:
        points.append("No key points extracted.")
    return points


def _content_units(text: str) -> list[str]:
    units = [part.strip() for part in text.split("\n\n") if part.strip()]
    if units:
        return units
    stripped = text.strip()
    return [stripped] if stripped else ["Empty content."]


def _write_triage_card(
    *,
    card_path: Path,
    title: str,
    doc_id: str,
    summary: str,
    key_points: list[str],
    relevance: str,
    recommendation: str,
    reason: str,
) -> None:
    key_points_markdown = "\n".join(f"- {point}" for point in key_points)
    content = (
        f"# {title}\n\n"
        f"- id: {doc_id}\n"
        f"- recommendation: {recommendation}\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## Key Points\n\n{key_points_markdown}\n\n"
        f"## Relevance\n\n{relevance}\n\n"
        f"## Reason\n\n{reason}\n"
    )
    card_path.parent.mkdir(parents=True, exist_ok=True)
    card_path.write_text(content, encoding="utf-8")
