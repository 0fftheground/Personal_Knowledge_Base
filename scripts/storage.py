"""Filesystem and JSON storage for the knowledge system."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from pathlib import Path
from typing import Any

from scripts import local_config


LOGGER = logging.getLogger(__name__)

SOURCE_TYPES = {"auto", "manual"}
CONTENT_TYPES = {"paper", "blog", "github", "book"}
CONTENT_STATUSES = {"candidate", "accepted", "rejected", "learning", "paused", "done", "archived"}
AI_RECOMMENDATIONS = {"skip", "skim", "learn"}
MANUAL_DECISIONS = {None, "accept", "reject", "later"}
STORAGE_TIERS = {"full", "sync_only"}
SYNC_STATUSES = {"none", "active", "inbox"}
LEARNING_STATUSES = {"learning", "paused", "done"}
LEARNING_PROCESSING_MODES = {"single_pass", "chunked"}
QUEUE_STATUSES = {"todo", "doing", "paused", "done"}
QUEUE_STATUS_ORDER = {"doing": 0, "todo": 1, "paused": 2, "done": 3}
LEARNING_STATE_DEFAULTS = {
    "initialized": False,
    "processing_mode": "single_pass",
    "size_metrics": {
        "pages": 0,
        "chars": 0,
        "estimated_tokens": 0,
        "heading_count": 0,
    },
    "current_focus": None,
    "focus_history": [],
    "interaction_count": 0,
    "chunk_manifest_path": None,
    "insights": [],
    "session_notes": [],
    "outline_generated": False,
    "document_outline": [],
    "core_summary": "",
    "ready_to_consolidate": False,
}
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_DOC_ID_LENGTH = 80


class StorageError(ValueError):
    """Raised when storage data does not match the documented schema."""


def get_repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def get_workspace_root(root: Path | None = None) -> Path:
    base = root or get_repo_root()
    workspace_root = local_config.get_workspace_root(base)
    if workspace_root is None:
        raise StorageError("configure workspace_root before using the knowledge workspace")
    return workspace_root


def get_records_root(root: Path | None = None) -> Path:
    return get_workspace_root(root) / "records"


def get_triage_cards_root(root: Path | None = None) -> Path:
    return get_workspace_root(root) / "triage" / "cards"


def get_triage_prompts_root(root: Path | None = None) -> Path:
    return get_workspace_root(root) / "triage" / "prompts"


def get_learning_root(root: Path | None = None) -> Path:
    return get_workspace_root(root) / "learning"


def get_learning_states_root(root: Path | None = None) -> Path:
    return get_learning_root(root) / "states"


def get_learning_outputs_root(root: Path | None = None) -> Path:
    return get_learning_root(root) / "outputs"


def get_learning_prompts_root(root: Path | None = None) -> Path:
    return get_learning_root(root) / "prompts"


def get_consolidation_root(root: Path | None = None) -> Path:
    return get_workspace_root(root) / "consolidation"


def get_consolidation_plans_root(root: Path | None = None) -> Path:
    return get_consolidation_root(root) / "plans"


def get_consolidation_drafts_root(root: Path | None = None) -> Path:
    return get_consolidation_root(root) / "drafts"


def get_consolidation_indexes_root(root: Path | None = None) -> Path:
    return get_consolidation_root(root) / "indexes"


def get_notes_root(root: Path | None = None) -> Path:
    return get_workspace_root(root) / "notes"


def ensure_storage_layout(root: Path | None = None) -> None:
    """Create the documented filesystem layout if it does not exist."""
    workspace_root = get_workspace_root(root)
    directories = [
        workspace_root / "records" / "auto",
        workspace_root / "records" / "manual",
        workspace_root / "triage" / "cards",
        workspace_root / "triage" / "prompts",
        workspace_root / "learning" / "states",
        workspace_root / "learning" / "outputs",
        workspace_root / "learning" / "prompts",
        workspace_root / "consolidation" / "plans",
        workspace_root / "consolidation" / "drafts",
        workspace_root / "consolidation" / "indexes",
        workspace_root / "notes",
    ]

    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        LOGGER.info("Ensured directory exists: %s", directory)

    queue_path = workspace_root / "learning" / "queue.json"
    if not queue_path.exists():
        write_queue([], root)


def create_content_item(
    *,
    doc_id: str,
    title: str,
    source_type: str,
    content_type: str,
    ingest_date: str,
    status: str,
    priority: float,
    ai_recommendation: str,
    manual_decision: str | None,
    storage_tier: str,
    full_raw_relpath: str | None,
    sync_raw_relpath: str | None,
    source_filename: str,
    source_device: str | None,
    content_hash: str | None,
    sync_status: str,
) -> dict[str, Any]:
    item = {
        "id": doc_id,
        "title": title,
        "source_type": source_type,
        "content_type": content_type,
        "ingest_date": ingest_date,
        "status": status,
        "priority": float(priority),
        "ai_recommendation": ai_recommendation,
        "manual_decision": manual_decision,
        "storage_tier": storage_tier,
        "full_raw_relpath": full_raw_relpath,
        "sync_raw_relpath": sync_raw_relpath,
        "source_filename": source_filename,
        "source_device": source_device,
        "content_hash": content_hash,
        "sync_status": sync_status,
    }
    validate_content_item(item)
    return item


def write_content_item(item: dict[str, Any], root: Path | None = None) -> Path:
    validate_content_item(item)
    metadata_path = get_content_item_path(item["source_type"], item["id"], root)
    _write_json(metadata_path, item)
    LOGGER.info("Wrote content item metadata: %s", metadata_path)
    return metadata_path


def get_content_item_path(source_type: str, doc_id: str, root: Path | None = None) -> Path:
    _validate_doc_id(doc_id)
    _validate_choice("source_type", source_type, SOURCE_TYPES)
    return get_records_root(root) / source_type / doc_id / "metadata.json"


def read_content_item(
    source_type: str,
    doc_id: str,
    root: Path | None = None,
) -> dict[str, Any]:
    metadata_path = get_content_item_path(source_type, doc_id, root)
    item = _read_json(metadata_path)
    validate_content_item(item)
    LOGGER.info("Read content item metadata: %s", metadata_path)
    return item


def list_content_items(
    root: Path | None = None,
    source_type: str | None = None,
) -> list[dict[str, Any]]:
    source_types = [source_type] if source_type else sorted(SOURCE_TYPES)
    items: list[dict[str, Any]] = []

    for current_source_type in source_types:
        if current_source_type not in SOURCE_TYPES:
            raise StorageError(
                f"source_type must be one of {sorted(SOURCE_TYPES)}, got {current_source_type!r}"
            )
        records_dir = get_records_root(root) / current_source_type
        if not records_dir.exists():
            continue
        for metadata_path in sorted(records_dir.glob("*/metadata.json")):
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


def ingest_raw_file(
    doc_id: str,
    source_type: str,
    source_path: Path,
    root: Path | None = None,
) -> dict[str, Any]:
    _validate_doc_id(doc_id)
    _validate_choice("source_type", source_type, SOURCE_TYPES)
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)

    base = root or get_repo_root()
    full_root = local_config.get_raw_full_root(base)
    sync_root = local_config.get_raw_sync_root(base)
    device_name = local_config.get_device_name(base)

    if full_root is None and sync_root is None:
        raise StorageError("configure raw_full_root or raw_sync_root before adding content")

    full_raw_relpath = None
    if full_root is not None:
        full_relpath = Path(source_type) / doc_id / source_path.name
        full_target = full_root / full_relpath
        _copy_file(source_path, full_target)
        full_raw_relpath = full_relpath.as_posix()

    sync_raw_relpath = None
    if sync_root is not None:
        sync_relpath = Path("active") / source_type / doc_id / source_path.name
        sync_target = sync_root / sync_relpath
        _copy_file(source_path, sync_target)
        sync_raw_relpath = sync_relpath.as_posix()

    return {
        "storage_tier": "full" if full_raw_relpath is not None else "sync_only",
        "full_raw_relpath": full_raw_relpath,
        "sync_raw_relpath": sync_raw_relpath,
        "source_filename": source_path.name,
        "source_device": device_name,
        "content_hash": compute_file_hash(source_path),
        "sync_status": "active" if sync_raw_relpath is not None else "none",
    }


def ingest_raw_file_to_inbox(
    doc_id: str,
    source_type: str,
    source_path: Path,
    root: Path | None = None,
) -> dict[str, Any]:
    _validate_doc_id(doc_id)
    _validate_choice("source_type", source_type, SOURCE_TYPES)
    if not source_path.exists() or not source_path.is_file():
        raise FileNotFoundError(source_path)

    base = root or get_repo_root()
    sync_root = local_config.get_raw_sync_root(base)
    device_name = local_config.get_device_name(base)

    if sync_root is None:
        raise StorageError("configure raw_sync_root before adding inbox content")
    if device_name is None:
        raise StorageError("configure device_name before adding inbox content")

    sync_relpath = Path("inbox") / device_name / source_type / doc_id / source_path.name
    sync_target = sync_root / sync_relpath
    _copy_file(source_path, sync_target)

    return {
        "storage_tier": "sync_only",
        "full_raw_relpath": None,
        "sync_raw_relpath": sync_relpath.as_posix(),
        "source_filename": source_path.name,
        "source_device": device_name,
        "content_hash": compute_file_hash(source_path),
        "sync_status": "inbox",
    }


def sync_item_to_active(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    base = root or get_repo_root()
    item = read_content_item_by_id(doc_id, base)
    source_path = resolve_raw_path(item, base)
    sync_root = local_config.get_raw_sync_root(base)
    if sync_root is None:
        raise StorageError("configure raw_sync_root before syncing active content")

    sync_relpath = Path("active") / item["source_type"] / item["id"] / item["source_filename"]
    sync_target = sync_root / sync_relpath
    _copy_file(source_path, sync_target)
    item["sync_raw_relpath"] = sync_relpath.as_posix()
    item["sync_status"] = "active"
    if item["storage_tier"] != "full":
        item["storage_tier"] = "sync_only"
    write_content_item(item, base)
    return item


def promote_item_to_full(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    base = root or get_repo_root()
    item = read_content_item_by_id(doc_id, base)
    source_path = resolve_raw_path(item, base)
    full_root = local_config.get_raw_full_root(base)
    if full_root is None:
        raise StorageError("configure raw_full_root before promoting content")

    full_relpath = Path(item["source_type"]) / item["id"] / item["source_filename"]
    full_target = full_root / full_relpath
    _copy_file(source_path, full_target)
    item["full_raw_relpath"] = full_relpath.as_posix()
    item["storage_tier"] = "full"
    write_content_item(item, base)
    return item


def resolve_raw_path(item: dict[str, Any], root: Path | None = None) -> Path:
    validate_content_item(item)
    base = root or get_repo_root()
    full_root = local_config.get_raw_full_root(base)
    sync_root = local_config.get_raw_sync_root(base)

    if item["full_raw_relpath"] is not None and full_root is not None:
        full_path = full_root / Path(item["full_raw_relpath"])
        if full_path.exists():
            return full_path

    if item["sync_raw_relpath"] is not None and sync_root is not None:
        sync_path = sync_root / Path(item["sync_raw_relpath"])
        if sync_path.exists():
            return sync_path

    raise FileNotFoundError(f"raw file not found for item {item['id']}")


def read_raw_text_for_item(item: dict[str, Any], root: Path | None = None) -> str:
    content_path = resolve_raw_path(item, root)
    try:
        text = content_path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        LOGGER.error("Failed to decode raw content as utf-8: %s", content_path)
        raise StorageError(f"raw file is not valid utf-8 text: {content_path}") from exc
    LOGGER.info("Read raw content: %s", content_path)
    return text


def build_doc_id(title: str, source_type: str, root: Path | None = None) -> str:
    _validate_string("title", title)
    _validate_choice("source_type", source_type, SOURCE_TYPES)

    base = root or get_repo_root()
    slug_parts = re.findall(r"[a-z0-9]+", title.lower())
    slug = "-".join(slug_parts) or "item"
    max_slug_length = MAX_DOC_ID_LENGTH - len(source_type) - 1
    if len(slug) > max_slug_length:
        slug = slug[:max_slug_length].rstrip("-")
    slug = slug or "item"
    prefix = f"{source_type}-{slug}"
    doc_id = prefix
    index = 2

    existing_ids = {item["id"] for item in list_content_items(root=base)}
    while doc_id in existing_ids:
        doc_id = f"{prefix}-{index}"
        index += 1

    LOGGER.info("Generated doc id %s for title %s", doc_id, title)
    return doc_id


def find_content_item_by_hash(
    content_hash: str | None,
    root: Path | None = None,
) -> dict[str, Any] | None:
    if content_hash in {None, ""}:
        return None
    _validate_string("content_hash", content_hash)

    for item in list_content_items(root=root):
        if item["content_hash"] == content_hash:
            LOGGER.info("Found existing content item by hash: %s", item["id"])
            return item
    return None


def create_queue_entry(doc_id: str, priority: float, status: str) -> dict[str, Any]:
    entry = {
        "doc_id": doc_id,
        "priority": float(priority),
        "status": status,
    }
    validate_queue_entry(entry)
    return entry


def read_queue(root: Path | None = None) -> list[dict[str, Any]]:
    queue_path = get_learning_root(root) / "queue.json"
    queue = _read_json(queue_path)
    validate_queue(queue)
    queue = _sort_queue(queue)
    LOGGER.info("Read queue: %s", queue_path)
    return queue


def write_queue(queue: list[dict[str, Any]], root: Path | None = None) -> Path:
    validate_queue(queue)
    normalized_queue = _sort_queue(queue)

    queue_path = get_learning_root(root) / "queue.json"
    _write_json(queue_path, normalized_queue)
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
    initialized: bool = False,
    processing_mode: str = "single_pass",
    size_metrics: dict[str, int] | None = None,
    current_focus: str | None = None,
    focus_history: list[str] | None = None,
    interaction_count: int = 0,
    progress: float,
    current_chunk: int,
    chunks_total: int,
    chunk_manifest_path: str | None = None,
    key_points: list[str],
    insights: list[str] | None = None,
    session_notes: list[str] | None = None,
    questions: list[str],
    next_action: str,
    status: str,
    outline_generated: bool = False,
    document_outline: list[str] | None = None,
    core_summary: str = "",
    ready_to_consolidate: bool = False,
) -> dict[str, Any]:
    state = {
        "doc_id": doc_id,
        "initialized": initialized,
        "processing_mode": processing_mode,
        "size_metrics": _normalize_size_metrics(size_metrics),
        "current_focus": current_focus,
        "focus_history": [] if focus_history is None else focus_history,
        "interaction_count": interaction_count,
        "progress": float(progress),
        "current_chunk": current_chunk,
        "chunks_total": chunks_total,
        "chunk_manifest_path": chunk_manifest_path,
        "key_points": key_points,
        "insights": [] if insights is None else insights,
        "session_notes": [] if session_notes is None else session_notes,
        "questions": questions,
        "outline_generated": outline_generated,
        "document_outline": [] if document_outline is None else document_outline,
        "core_summary": core_summary,
        "next_action": next_action,
        "ready_to_consolidate": ready_to_consolidate,
        "status": status,
    }
    validate_learning_state(state)
    return state


def read_learning_state(doc_id: str, root: Path | None = None) -> dict[str, Any]:
    _validate_doc_id(doc_id)
    state_path = get_learning_states_root(root) / doc_id / "state.json"
    state = _normalize_learning_state(_read_json(state_path))
    validate_learning_state(state)
    LOGGER.info("Read learning state: %s", state_path)
    return state


def write_learning_state(state: dict[str, Any], root: Path | None = None) -> Path:
    validate_learning_state(state)
    state_path = get_learning_states_root(root) / state["doc_id"] / "state.json"
    _write_json(state_path, state)
    LOGGER.info("Wrote learning state: %s", state_path)
    return state_path


def learning_state_exists(doc_id: str, root: Path | None = None) -> bool:
    _validate_doc_id(doc_id)
    return (get_learning_states_root(root) / doc_id / "state.json").exists()


def compute_file_hash(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def validate_content_item(item: dict[str, Any]) -> None:
    _validate_keys(
        "content item",
        item,
        {
            "id",
            "title",
            "source_type",
            "content_type",
            "ingest_date",
            "status",
            "priority",
            "ai_recommendation",
            "manual_decision",
            "storage_tier",
            "full_raw_relpath",
            "sync_raw_relpath",
            "source_filename",
            "source_device",
            "content_hash",
            "sync_status",
        },
    )
    _validate_doc_id(item["id"])
    _validate_string("title", item["title"])
    _validate_choice("source_type", item["source_type"], SOURCE_TYPES)
    _validate_choice("content_type", item["content_type"], CONTENT_TYPES)
    _validate_date("ingest_date", item["ingest_date"])
    _validate_choice("status", item["status"], CONTENT_STATUSES)
    _validate_number("priority", item["priority"])
    _validate_choice("ai_recommendation", item["ai_recommendation"], AI_RECOMMENDATIONS)
    _validate_nullable_choice("manual_decision", item["manual_decision"], MANUAL_DECISIONS)
    _validate_choice("storage_tier", item["storage_tier"], STORAGE_TIERS)
    _validate_optional_relpath("full_raw_relpath", item["full_raw_relpath"])
    _validate_optional_relpath("sync_raw_relpath", item["sync_raw_relpath"])
    _validate_string("source_filename", item["source_filename"])
    _validate_optional_string("source_device", item["source_device"])
    _validate_optional_hash("content_hash", item["content_hash"])
    _validate_choice("sync_status", item["sync_status"], SYNC_STATUSES)

    if item["storage_tier"] == "full" and item["full_raw_relpath"] is None:
        raise StorageError("storage_tier='full' requires full_raw_relpath")
    if item["storage_tier"] == "sync_only" and item["sync_raw_relpath"] is None:
        raise StorageError("storage_tier='sync_only' requires sync_raw_relpath")


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
            "initialized",
            "processing_mode",
            "size_metrics",
            "current_focus",
            "focus_history",
            "interaction_count",
            "progress",
            "current_chunk",
            "chunks_total",
            "chunk_manifest_path",
            "key_points",
            "insights",
            "session_notes",
            "questions",
            "outline_generated",
            "document_outline",
            "core_summary",
            "next_action",
            "ready_to_consolidate",
            "status",
        },
    )
    _validate_doc_id(state["doc_id"])
    _validate_bool("initialized", state["initialized"])
    _validate_choice("processing_mode", state["processing_mode"], LEARNING_PROCESSING_MODES)
    _validate_size_metrics("size_metrics", state["size_metrics"])
    _validate_optional_string("current_focus", state["current_focus"])
    _validate_string_list("focus_history", state["focus_history"])
    _validate_int("interaction_count", state["interaction_count"])
    _validate_number("progress", state["progress"])
    _validate_int("current_chunk", state["current_chunk"])
    _validate_int("chunks_total", state["chunks_total"])
    _validate_optional_relpath("chunk_manifest_path", state["chunk_manifest_path"])
    _validate_string_list("key_points", state["key_points"])
    _validate_string_list("insights", state["insights"])
    _validate_string_list("session_notes", state["session_notes"])
    _validate_string_list("questions", state["questions"])
    _validate_bool("outline_generated", state["outline_generated"])
    _validate_string_list("document_outline", state["document_outline"])
    _validate_text("core_summary", state["core_summary"])
    _validate_string("next_action", state["next_action"])
    _validate_bool("ready_to_consolidate", state["ready_to_consolidate"])
    _validate_choice("status", state["status"], LEARNING_STATUSES)


def _copy_file(source_path: Path, target_path: Path) -> None:
    resolved_source = source_path.resolve()
    resolved_target = target_path.resolve(strict=False)
    if resolved_source == resolved_target:
        LOGGER.info("Skipped raw file copy because source and target match: %s", resolved_source)
        return
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
    LOGGER.info("Copied raw file from %s to %s", source_path, target_path)


def _read_json(path: Path) -> Any:
    if not path.exists():
        LOGGER.error("Missing JSON file: %s", path)
        raise FileNotFoundError(path)
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        LOGGER.error("Invalid JSON file: %s", path)
        raise StorageError(f"invalid JSON file: {path}") from exc


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


def _validate_text(name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise StorageError(f"{name} must be a string")


def _normalize_size_metrics(value: dict[str, int] | None) -> dict[str, int]:
    normalized = dict(LEARNING_STATE_DEFAULTS["size_metrics"])
    if value is None:
        return normalized
    normalized.update(value)
    return normalized


def _normalize_learning_state(state: Any) -> Any:
    if not isinstance(state, dict):
        return state
    normalized = dict(state)
    for key, default in LEARNING_STATE_DEFAULTS.items():
        if key in normalized:
            if key == "size_metrics":
                normalized[key] = _normalize_size_metrics(normalized[key])
            continue
        if isinstance(default, list):
            normalized[key] = list(default)
        elif isinstance(default, dict):
            normalized[key] = dict(default)
        else:
            normalized[key] = default
    return normalized


def _sort_queue(queue: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        queue,
        key=lambda entry: (
            QUEUE_STATUS_ORDER[entry["status"]],
            -float(entry["priority"]),
            entry["doc_id"],
        ),
    )


def _validate_nullable_choice(name: str, value: Any, allowed: set[str | None]) -> None:
    if value not in allowed:
        allowed_values = sorted("null" if item is None else item for item in allowed)
        raise StorageError(f"{name} must be one of {allowed_values}, got {value!r}")


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


def _validate_bool(name: str, value: Any) -> None:
    if not isinstance(value, bool):
        raise StorageError(f"{name} must be a boolean")


def _validate_int(name: str, value: Any) -> None:
    if not isinstance(value, int) or isinstance(value, bool):
        raise StorageError(f"{name} must be an integer")


def _validate_optional_string(name: str, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not value.strip():
        raise StorageError(f"{name} must be null or a non-empty string")


def _validate_optional_relpath(name: str, value: Any) -> None:
    _validate_optional_string(name, value)
    if value is None:
        return
    path = Path(value)
    if path.is_absolute():
        raise StorageError(f"{name} must be a relative path")


def _validate_optional_hash(name: str, value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise StorageError(f"{name} must be null or a sha256 hex string")


def _validate_size_metrics(name: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise StorageError(f"{name} must be an object")
    expected_keys = {"pages", "chars", "estimated_tokens", "heading_count"}
    if set(value.keys()) != expected_keys:
        raise StorageError(f"{name} keys must be exactly {sorted(expected_keys)}")
    for key in expected_keys:
        _validate_int(f"{name}.{key}", value[key])
