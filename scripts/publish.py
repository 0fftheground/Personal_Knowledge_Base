"""Publish triage and learning outputs into the configured Obsidian vault."""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts import consolidation
from scripts import local_config
from scripts import storage
from scripts import triage


PUBLISH_ROOT_DIR = "pkls"


def publish_triage(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
    publish_root = _publish_root(base)
    target_path = publish_root / "triage" / f"{item['id']}.md"
    if not card_path.exists():
        if target_path.exists():
            _delete_file(target_path)
            consolidation.update_obsidian_index([], base, removed_paths=[target_path])
            return target_path
        raise FileNotFoundError(card_path)
    card = triage.read_triage_card(doc_id, base)
    if not triage.is_triage_card_complete(card):
        raise ValueError(f"triage card is incomplete and cannot be published: {doc_id}")

    _copy_file(card_path, target_path)
    consolidation.update_obsidian_index([target_path], base)
    return target_path


def publish_learning(doc_id: str, root: Path | None = None) -> list[Path]:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    output_dir = storage.get_learning_outputs_root(base) / item["id"]

    publish_root = _publish_root(base)
    destinations: list[Path] = []
    removed_paths: list[Path] = []
    file_mapping = {
        "outline.md": publish_root / "learning" / "outlines" / f"{item['id']}.md",
        "summary.md": publish_root / "learning" / "summaries" / f"{item['id']}.md",
        "insights.md": publish_root / "learning" / "insights" / f"{item['id']}.md",
        "qa.md": publish_root / "learning" / "qa" / f"{item['id']}.md",
    }

    for source_name, target_path in file_mapping.items():
        source_path = output_dir / source_name
        if not source_path.exists():
            if target_path.exists():
                _delete_file(target_path)
                removed_paths.append(target_path)
            continue
        _copy_file(source_path, target_path)
        destinations.append(target_path)

    if not destinations and not removed_paths:
        if not output_dir.exists():
            raise FileNotFoundError(output_dir)
        raise FileNotFoundError(f"no learning outputs found for {doc_id}")
    consolidation.update_obsidian_index(destinations, base, removed_paths=removed_paths)
    return destinations + removed_paths


def publish_consolidation(doc_id: str, root: Path | None = None) -> list[Path]:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    draft_path = consolidation.draft_path_for_doc(doc_id, base)
    plan_path = storage.get_consolidation_plans_root(base) / f"{item['id']}.json"
    destinations: list[Path] = []
    removed_paths: list[Path] = []
    publish_root = _publish_root(base)

    file_mapping = {
        draft_path: publish_root / "consolidation" / "drafts" / f"{item['id']}.md",
        plan_path: publish_root / "consolidation" / "plans" / f"{item['id']}.json",
    }

    for source_path, target_path in file_mapping.items():
        if not source_path.exists():
            if target_path.exists():
                _delete_file(target_path)
                removed_paths.append(target_path)
            continue
        _copy_file(source_path, target_path)
        destinations.append(target_path)

    if not destinations and not removed_paths:
        raise FileNotFoundError(f"no consolidation outputs found for {doc_id}")
    consolidation.update_obsidian_index(destinations, base, removed_paths=removed_paths)
    return destinations + removed_paths


def publish_item(doc_id: str, root: Path | None = None) -> list[Path]:
    published_paths: list[Path] = []
    try:
        published_paths.append(publish_triage(doc_id, root))
    except FileNotFoundError:
        pass

    try:
        published_paths.extend(publish_learning(doc_id, root))
    except FileNotFoundError:
        pass

    try:
        published_paths.extend(publish_consolidation(doc_id, root))
    except FileNotFoundError:
        pass

    if not published_paths:
        raise FileNotFoundError(f"no triage, learning, or consolidation outputs found for {doc_id}")
    return published_paths


def sync_complete_triage_cards(root: Path | None = None) -> list[Path]:
    base = root or storage.get_repo_root()
    published_paths: list[Path] = []
    removed_paths: list[Path] = []

    for item in storage.list_content_items(root=base):
        card = triage.read_triage_card(item["id"], base)
        if not triage.is_triage_card_complete(card):
            target_path = _publish_root(base) / "triage" / f"{item['id']}.md"
            if target_path.exists():
                _delete_file(target_path)
                removed_paths.append(target_path)
            continue
        published_paths.append(publish_triage(item["id"], base))

    consolidation.update_obsidian_index(published_paths, base, removed_paths=removed_paths)
    return published_paths + removed_paths


def _publish_root(root: Path) -> Path:
    return local_config.get_notes_publish_root(root) / PUBLISH_ROOT_DIR


def _copy_file(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)


def _delete_file(target_path: Path) -> None:
    try:
        target_path.unlink()
    except FileNotFoundError:
        return
