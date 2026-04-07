"""Filesystem + JSON storage for the MVP knowledge system.

This module implements Phase 1 storage only:
- content items
- queue
- learning state

The storage layout follows docs/architecture.md and the JSON shapes follow
docs/schema.md exactly.
"""

from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any


LOGGER = logging.getLogger(__name__)

SOURCE_TYPES = {"auto", "manual"}
CONTENT_TYPES = {"paper", "blog", "github", "book"}
CONTENT_STATUSES = {"candidate", "accepted", "rejected", "learning", "done"}
AI_RECOMMENDATIONS = {"skip", "skim", "learn"}
LEARNING_STATUSES = {"learning", "done"}
QUEUE_STATUSES = {"todo", "doing", "done"}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class StorageError(ValueError):
    """Raised when storage data does not match the documented schema."""


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def ensure_storage_layout(root: Path | None = None) -> None:
    """Create the documented filesystem layout if it does not exist."""
    base = root or get_repo_root()
    directories = [
        base / "raw" / "auto",
        base / "raw" / "manual",
        base / "triage" / "cards",
        base / "learning" / "states",
        base / "learning" / "outputs",
        base / "notes",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Ensured directory exists: %s", directory)

    queue_path = base / "learning" / "queue.json"
    if not queue_path.exists():
        write_queue([], base)


def write_raw_content(
    doc_id: str,
    source_type: str,
    filename: str,
    content: str,
    root: Path | None = None,
) -> str:
    """Persist raw content under the documented raw layer and return its path."""
    _validate_doc_id(doc_id)
    _validate_choice("source_type", source_type, SOURCE_TYPES)

    base = root or get_repo_root()
    target = base / "raw" / source_type / doc_id / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    relative_path = target.relative_to(base).as_posix()
    LOGGER.info("Wrote raw content: %s", target)
    return relative_path


def copy_raw_content(
    doc_id: str,
    source_type: str,
    source_path: Path,
    root: Path | None = None,
) -> str:
    """Copy user-provided raw content into the documented raw layer."""
    _validate_doc_id(doc_id)
    _validate_choice("source_type", source_type, SOURCE_TYPES)
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)

    base = root or get_repo_root()
    target = base / "raw" / source_type / doc_id / source_path.name
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target)
    relative_path = target.relative_to(base).as_posix()
    LOGGER.info("Copied raw content from %s to %s", source_path, target)
    return relative_path


def create_content_item(
    *,
    doc_id: str,
    title: str,
    source_type: str,
    content_type: str,
    path: str,
    ingest_date: str,
    status: str,
    priority: float,
    ai_recommendation: str,
    manual_decision: None,
) -> dict[str, Any]:
    item = {
        "id": doc_id,
        "title": title,
        "source_type": source_type,
        "content_type": content_type,
        "path": path,
        "ingest_date": ingest_date,
        "status": status,
        "priority": float(priority),
        "ai_recommendation": ai_recommendation,
        "manual_decision": manual_decision,
    }
    validate_content_item(item)
    return item


def write_content_item(item: dict[str, Any], root: Path | None = None) -> Path:
    validate_content_item(item)

    base = root or get_repo_root()
    metadata_path = base / "raw" / item["source_type"] / item["id"] / "metadata.json"
    _write_json(metadata_path, item)
    LOGGER.info("Wrote content item metadata: %s", metadata_path)
    return metadata_path


def read_content_item(
    source_type: str,
    doc_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    _validate_doc_id(doc_id)
    _validate_choice("source_type", source_type, SOURCE_TYPES)

    base = root or get_repo_root()
    metadata_path = base / "raw" / source_type / doc_id / "metadata.json"
    item = _read_json(metadata_path)
    validate_content_item(item)
    LOGGER.info("Read content item metadata: %s", metadata_path)
    return item


def list_content_items(
    root: Path | None = None,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    base = root or get_repo_root()
    source_types = [source_type] if source_type else sorted(SOURCE_TYPES)
    items: list[dict[str, Any]] = []

    for current_source_type in source_types:
        if current_source_type not in SOURCE_TYPES:
            raise StorageError(
                f"source_type must be one of {sorted(SOURCE_TYPES)}, got {current_source_type!r}"
            )
        raw_dir = base / "raw" / current_source_type
        if not raw_dir.exists():
            continue
        for metadata_path in sorted(raw_dir.glob("*/metadata.json")):
            item = _read_json(metadata_path)
            validate_content_item(item)
            items.append(item)

    LOGGER.info("Listed %s content items", len(items))
    return items


def read_content_item_by_id(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    _validate_doc_id(doc_id)
    matches = [item for item in list_content_items(root=root) if item["id"] == doc_id]
    if not matches:
        LOGGER.error("Content item not found: %s", doc_id)
        raise FileNotFoundError(doc_id)
    if len(matches) > 1:
        raise StorageError(f"duplicate content item id found: {doc_id}")
    return matches[0]


def read_raw_text_for_item(item: dict[str, Any], root: Path | None = None) -> str:
    validate_content_item(item)
    base = root or get_repo_root()
    content_path = base / item["path"]
    if not content_path.exists():
        LOGGER.error("Missing raw content file: %s", content_path)
        raise FileNotFoundError(content_path)
    text = content_path.read_text(encoding="utf-8")
    LOGGER.info("Read raw content: %s", content_path)
    return text


def build_doc_id(title: str, source_type: str, root: Path | None = None) -> str:
    _validate_string("title", title)
    _validate_choice("source_type", source_type, SOURCE_TYPES)

    base = root or get_repo_root()
    slug_parts = re.findall(r"[a-z0-9]+", title.lower())
    slug = "-".join(slug_parts) or "item"
    prefix = f"{source_type}-{slug}"
    doc_id = prefix
    index = 2

    existing_ids = {item["id"] for item in list_content_items(root=base)}
    while doc_id in existing_ids:
        doc_id = f"{prefix}-{index}"
        index += 1

    LOGGER.info("Generated doc id %s for title %s", doc_id, title)
    return doc_id


def create_queue_entry(doc_id: str, priority: float, status: str) -> dict[str, Any]:
    entry = {
        "doc_id": doc_id,
        "priority": float(priority),
        "status": status,
    }
    validate_queue_entry(entry)
    return entry


def read_queue(root: Path | None = None) -> list[dict[str, Any]]:
    base = root or get_repo_root()
    queue_path = base / "learning" / "queue.json"
    queue = _read_json(queue_path)
    validate_queue(queue)
    LOGGER.info("Read queue: %s", queue_path)
    return queue


def write_queue(queue: list[dict[str, Any]], root: Path | None = None) -> Path:
    validate_queue(queue)

    base = root or get_repo_root()
    queue_path = base / "learning" / "queue.json"
    _write_json(queue_path, queue)
    LOGGER.info("Wrote queue: %s", queue_path)
    return queue_path


def upsert_queue_entry(entry: dict[str, Any], root: Path | None = None) -> Path:
    validate_queue_entry(entry)
    queue = read_queue(root)
    updated = False

    for index, current_entry in enumerate(queue):
        if current_entry["doc_id"] == entry["doc_id"]:
            queue[index] = entry
            updated = True
            break

    if not updated:
        queue.append(entry)

    LOGGER.info("Upserted queue entry for doc %s", entry["doc_id"])
    return write_queue(queue, root)


def remove_queue_entry(doc_id: str, root: Path | None = None) -> Path:
    _validate_doc_id(doc_id)
    queue = read_queue(root)
    filtered_queue = [entry for entry in queue if entry["doc_id"] != doc_id]
    LOGGER.info("Removed queue entry for doc %s", doc_id)
    return write_queue(filtered_queue, root)


def get_queue_entry(doc_id: str, root: Path | None = None) -> dict[str, Any] | None:
    _validate_doc_id(doc_id)
    queue = read_queue(root)
    for entry in queue:
        if entry["doc_id"] == doc_id:
            return entry
    return None


def create_learning_state(
    *,
    doc_id: str,
    progress: float,
    current_chunk: int,
    chunks_total: int,
    key_points: list[str],
    questions: list[str],
    next_action: str,
    status: str,
) -> dict[str, Any]:
    state = {
        "doc_id": doc_id,
        "progress": float(progress),
        "current_chunk": current_chunk,
        "chunks_total": chunks_total,
        "key_points": key_points,
        "questions": questions,
        "next_action": next_action,
        "status": status,
    }
    validate_learning_state(state)
    return state


def read_learning_state(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    _validate_doc_id(doc_id)

    base = root or get_repo_root()
    state_path = base / "learning" / "states" / doc_id / "state.json"
    state = _read_json(state_path)
    validate_learning_state(state)
    LOGGER.info("Read learning state: %s", state_path)
    return state


def write_learning_state(state: dict[str, Any], root: Path | None = None) -> Path:
    validate_learning_state(state)

    base = root or get_repo_root()
    state_path = base / "learning" / "states" / state["doc_id"] / "state.json"
    _write_json(state_path, state)
    LOGGER.info("Wrote learning state: %s", state_path)
    return state_path


def learning_state_exists(doc_id: str, root: Path | None = None) -> bool:
    _validate_doc_id(doc_id)
    base = root or get_repo_root()
    return (base / "learning" / "states" / doc_id / "state.json").exists()


def validate_content_item(item: dict[str, Any]) -> None:
    _validate_keys(
        "content item",
        item,
        {
            "id",
            "title",
            "source_type",
            "content_type",
            "path",
            "ingest_date",
            "status",
            "priority",
            "ai_recommendation",
            "manual_decision",
        },
    )
    _validate_doc_id(item["id"])
    _validate_string("title", item["title"])
    _validate_choice("source_type", item["source_type"], SOURCE_TYPES)
    _validate_choice("content_type", item["content_type"], CONTENT_TYPES)
    _validate_string("path", item["path"])
    _validate_date("ingest_date", item["ingest_date"])
    _validate_choice("status", item["status"], CONTENT_STATUSES)
    _validate_number("priority", item["priority"])
    _validate_choice("ai_recommendation", item["ai_recommendation"], AI_RECOMMENDATIONS)
    _validate_null("manual_decision", item["manual_decision"])

    expected_prefix = f"raw/{item['source_type']}/{item['id']}/"
    if not item["path"].startswith(expected_prefix):
        raise StorageError(
            f"path must stay under {expected_prefix!r}, got {item['path']!r}"
        )


def validate_queue(queue: list[dict[str, Any]]) -> None:
    if not isinstance(queue, list):
        raise StorageError("queue must be a list")
    for entry in queue:
        validate_queue_entry(entry)


def validate_queue_entry(entry: dict[str, Any]) -> None:
    _validate_keys("queue entry", entry, {"doc_id", "priority", "status"})
    _validate_doc_id(entry["doc_id"])
    _validate_number("priority", entry["priority"])
    _validate_choice("status", entry["status"], QUEUE_STATUSES)


def validate_learning_state(state: dict[str, Any]) -> None:
    _validate_keys(
        "learning state",
        state,
        {
            "doc_id",
            "progress",
            "current_chunk",
            "chunks_total",
            "key_points",
            "questions",
            "next_action",
            "status",
        },
    )
    _validate_doc_id(state["doc_id"])
    _validate_number("progress", state["progress"])
    _validate_int("current_chunk", state["current_chunk"])
    _validate_int("chunks_total", state["chunks_total"])
    _validate_string_list("key_points", state["key_points"])
    _validate_string_list("questions", state["questions"])
    _validate_string("next_action", state["next_action"])
    _validate_choice("status", state["status"], LEARNING_STATUSES)


def _read_json(path: Path) -> Any:
    if not path.exists():
        LOGGER.error("Missing JSON file: %s", path)
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.write("\n")


def _validate_keys(name: str, payload: dict[str, Any], expected_keys: set[str]) -> None:
    if not isinstance(payload, dict):
        raise StorageError(f"{name} must be a JSON object")
    actual_keys = set(payload.keys())
    if actual_keys != expected_keys:
        raise StorageError(
            f"{name} keys must be exactly {sorted(expected_keys)}, got {sorted(actual_keys)}"
        )


def _validate_doc_id(value: Any) -> None:
    _validate_string("id", value)


def _validate_string(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise StorageError(f"{name} must be a non-empty string")


def _validate_null(name: str, value: Any) -> None:
    if value is not None:
        raise StorageError(f"{name} must be null")


def _validate_string_list(name: str, value: Any) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise StorageError(f"{name} must be a list of strings")


def _validate_date(name: str, value: Any) -> None:
    _validate_string(name, value)
    if not DATE_PATTERN.match(value):
        raise StorageError(f"{name} must match YYYY-MM-DD")


def _validate_choice(name: str, value: Any, allowed: set[str]) -> None:
    if value not in allowed:
        raise StorageError(f"{name} must be one of {sorted(allowed)}, got {value!r}")


def _validate_number(name: str, value: Any) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise StorageError(f"{name} must be a number")


def _validate_int(name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise StorageError(f"{name} must be an integer")
