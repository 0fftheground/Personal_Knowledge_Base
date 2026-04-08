"""Publish triage and learning outputs into the configured Obsidian vault."""

from __future__ import annotations

import shutil
from pathlib import Path

from scripts import local_config
from scripts import storage


PUBLISH_ROOT_DIR = "pkls"


def publish_triage(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
    if not card_path.exists():
        raise FileNotFoundError(card_path)

    publish_root = _publish_root(base)
    target_path = publish_root / "triage" / f"{item['id']}.md"
    _copy_file(card_path, target_path)
    return target_path


def publish_learning(doc_id: str, root: Path | None = None) -> list[Path]:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    output_dir = storage.get_learning_outputs_root(base) / item["id"]
    if not output_dir.exists():
        raise FileNotFoundError(output_dir)

    publish_root = _publish_root(base)
    destinations: list[Path] = []
    file_mapping = {
        "outline.md": publish_root / "learning" / "outlines" / f"{item['id']}.md",
        "summary.md": publish_root / "learning" / "summaries" / f"{item['id']}.md",
        "insights.md": publish_root / "learning" / "insights" / f"{item['id']}.md",
        "qa.md": publish_root / "learning" / "qa" / f"{item['id']}.md",
    }

    for source_name, target_path in file_mapping.items():
        source_path = output_dir / source_name
        if not source_path.exists():
            continue
        _copy_file(source_path, target_path)
        destinations.append(target_path)

    if not destinations:
        raise FileNotFoundError(f"no learning outputs found for {doc_id}")
    return destinations


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

    if not published_paths:
        raise FileNotFoundError(f"no triage or learning outputs found for {doc_id}")
    return published_paths


def _publish_root(root: Path) -> Path:
    return local_config.get_notes_publish_root(root) / PUBLISH_ROOT_DIR


def _copy_file(source_path: Path, target_path: Path) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, target_path)
