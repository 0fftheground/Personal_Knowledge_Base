"""Consolidation helpers for adapting learned material into Obsidian notes."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from scripts import local_config
from scripts import storage


LOGGER = logging.getLogger(__name__)
WIKILINK_PATTERN = re.compile(r"\[\[([^\]]+)\]\]")
TAG_PATTERN = re.compile(r"(?<!\w)#([A-Za-z0-9_\-/]+)")
WORD_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]{2,}")
OBSIDIAN_INDEX_FILENAME = "obsidian_index.json"


def build_obsidian_index(root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    vault_root = local_config.get_notes_publish_root(base)
    index_entries: list[dict[str, Any]] = []

    for note_path in sorted(vault_root.rglob("*.md")):
        if any(part.startswith(".") for part in note_path.parts):
            continue
        try:
            text = note_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            LOGGER.warning("Skipping non-utf8 note while building Obsidian index: %s", note_path)
            continue
        entry = _build_index_entry(vault_root, note_path, text)
        index_entries.append(entry)

    target_path = storage.get_consolidation_indexes_root(base) / OBSIDIAN_INDEX_FILENAME
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(index_entries, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Built Obsidian index with %s notes: %s", len(index_entries), target_path)
    return target_path


def update_obsidian_index(
    note_paths: list[Path],
    root: Path | None = None,
    removed_paths: list[Path] | None = None,
) -> Path:
    base = root or storage.get_repo_root()
    vault_root = local_config.get_notes_publish_root(base)
    index_path = storage.get_consolidation_indexes_root(base) / OBSIDIAN_INDEX_FILENAME
    if index_path.exists():
        payload = json.loads(index_path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise storage.StorageError(f"invalid Obsidian index file: {index_path}")
        entries_by_path = {
            entry["path"]: entry
            for entry in payload
            if isinstance(entry, dict) and isinstance(entry.get("path"), str)
        }
    else:
        entries_by_path = {}

    processed_note = False
    processed_removal = False
    changed = False
    for note_path in note_paths:
        if not note_path.exists() or note_path.suffix.lower() != ".md":
            continue
        processed_note = True
        if any(part.startswith(".") for part in note_path.parts):
            continue
        try:
            text = note_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            LOGGER.warning("Skipping non-utf8 note while updating Obsidian index: %s", note_path)
            continue
        entry = _build_index_entry(vault_root, note_path, text)
        entries_by_path[entry["path"]] = entry
        changed = True

    for removed_path in removed_paths or []:
        relative_path = _relative_index_path(vault_root, removed_path)
        if relative_path is None:
            continue
        processed_removal = True
        if relative_path in entries_by_path:
            entries_by_path.pop(relative_path, None)
            changed = True

    if not processed_note and not processed_removal:
        if index_path.exists():
            return index_path
        return build_obsidian_index(base)

    if not changed and index_path.exists():
        return index_path

    target_path = index_path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_entries = [entries_by_path[key] for key in sorted(entries_by_path)]
    target_path.write_text(json.dumps(ordered_entries, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Updated Obsidian index with %s notes: %s", len(ordered_entries), target_path)
    return target_path


def read_obsidian_index(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or storage.get_repo_root()
    index_path = storage.get_consolidation_indexes_root(base) / OBSIDIAN_INDEX_FILENAME
    if not index_path.exists():
        build_obsidian_index(base)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise storage.StorageError(f"invalid Obsidian index file: {index_path}")
    return payload


def rank_candidate_notes(doc_id: str, root: Path | None = None, top_k: int = 5) -> list[dict[str, str]]:
    base = root or storage.get_repo_root()
    state = storage.read_learning_state(doc_id, base) if storage.learning_state_exists(doc_id, base) else None
    item = storage.read_content_item_by_id(doc_id, base)
    index_entries = read_obsidian_index(base)
    query_tokens = _build_query_tokens(item, state)
    ranked: list[tuple[int, dict[str, Any]]] = []

    for entry in index_entries:
        haystack = " ".join(
            [
                entry["title"],
                entry["path"],
                " ".join(entry["tags"]),
                " ".join(entry["wikilinks"]),
            ]
        ).lower()
        score = sum(3 if token in entry["title"].lower() else 1 for token in query_tokens if token in haystack)
        if score <= 0:
            continue
        ranked.append((score, entry))

    ranked.sort(key=lambda row: (-row[0], row[1]["path"]))
    return [
        {
            "path": row["path"],
            "reason": _candidate_reason(query_tokens, row),
        }
        for _, row in ranked[:top_k]
    ]


def build_consolidation_plan(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    state = storage.read_learning_state(doc_id, base) if storage.learning_state_exists(doc_id, base) else None
    candidate_notes = rank_candidate_notes(doc_id, base)
    draft_path = storage.get_consolidation_drafts_root(base) / f"{doc_id}.md"
    action = "create_new_note" if not candidate_notes else "create_and_link"
    focus_scope = [] if state is None else [focus for focus in state["focus_history"] if focus.strip()]
    if state is not None and state["current_focus"]:
        focus_scope = [state["current_focus"], *focus_scope]

    return {
        "doc_id": doc_id,
        "focus_scope": focus_scope[:10],
        "candidate_notes": candidate_notes,
        "action": action,
        "draft_relpath": draft_path.relative_to(storage.get_workspace_root(base)).as_posix(),
        "next_action": f"Review and refine the knowledge draft for {item['title']}",
    }


def write_consolidation_plan(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    plan = build_consolidation_plan(doc_id, base)
    plan_path = storage.get_consolidation_plans_root(base) / f"{doc_id}.json"
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Wrote consolidation plan: %s", plan_path)
    return plan_path


def draft_path_for_doc(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    return storage.get_consolidation_drafts_root(base) / f"{doc_id}.md"


def _build_index_entry(vault_root: Path, note_path: Path, text: str) -> dict[str, Any]:
    frontmatter, body = _split_frontmatter(text)
    tags = _extract_tags(frontmatter, body)
    wikilinks = sorted({link.strip() for link in WIKILINK_PATTERN.findall(body) if link.strip()})
    title = _extract_title(note_path, body)
    relative_path = note_path.relative_to(vault_root).as_posix()
    lower_title = title.lower()
    return {
        "path": relative_path,
        "title": title,
        "tags": tags,
        "wikilinks": wikilinks,
        "modified_time": datetime.fromtimestamp(note_path.stat().st_mtime).isoformat(timespec="seconds"),
        "is_index_note": any(marker in lower_title for marker in ("index", "moc", "map of content")),
    }


def _split_frontmatter(text: str) -> tuple[str, str]:
    if not text.startswith("---\n"):
        return "", text
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return "", text
    return parts[0], parts[1]


def _extract_title(note_path: Path, body: str) -> str:
    for line in body.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return note_path.stem


def _extract_tags(frontmatter: str, body: str) -> list[str]:
    tags: set[str] = set(TAG_PATTERN.findall(body))
    for line in frontmatter.splitlines():
        stripped = line.strip()
        if stripped.startswith("tags:"):
            raw_value = stripped.split(":", 1)[1].strip().strip("[]")
            for tag in re.split(r"[,\s]+", raw_value):
                normalized = tag.strip().lstrip("#")
                if normalized:
                    tags.add(normalized)
    return sorted(tags)


def _build_query_tokens(item: dict[str, Any], state: dict[str, Any] | None) -> set[str]:
    values = [item["title"], item["content_type"], item["source_type"]]
    if state is not None:
        values.extend(
            [
                state["core_summary"],
                state["current_focus"] or "",
                " ".join(state["focus_history"]),
                " ".join(state["key_points"]),
                " ".join(state["insights"]),
            ]
        )
    query_tokens: set[str] = set()
    for value in values:
        for token in WORD_PATTERN.findall(value.lower()):
            query_tokens.add(token)
    return query_tokens


def _candidate_reason(query_tokens: set[str], entry: dict[str, Any]) -> str:
    matched = [
        token
        for token in sorted(query_tokens)
        if token in entry["title"].lower()
        or token in " ".join(entry["tags"]).lower()
        or token in " ".join(entry["wikilinks"]).lower()
    ][:5]
    if matched:
        return f"matched terms: {', '.join(matched)}"
    return "related by note title or structure index"


def _relative_index_path(vault_root: Path, note_path: Path) -> str | None:
    try:
        return note_path.relative_to(vault_root).as_posix()
    except ValueError:
        return None
