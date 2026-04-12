"""CLI entrypoint for the local MVP knowledge system."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from scripts import agent_workflow
from scripts import ingest_detection
from scripts import learning
from scripts import local_config
from scripts import publish
from scripts import storage
from scripts import triage
from scripts import url_ingest


LOGGER = logging.getLogger(__name__)
TEXT_PREVIEW_LIMIT = 220
READ_ONLY_LOG_LEVEL = logging.WARNING
MUTATING_LOG_LEVEL = logging.WARNING


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pkls")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add")
    add_subparsers = add_parser.add_subparsers(dest="source_type", required=True)
    for source_type in sorted(storage.SOURCE_TYPES):
        source_parser = add_subparsers.add_parser(source_type)
        source_parser.add_argument("--type", dest="content_type", required=True, choices=sorted(storage.CONTENT_TYPES))
        source_parser.add_argument("--path", required=True)
        source_parser.add_argument("--title")
        source_parser.add_argument("--accept", action="store_true")

    raw_parser = subparsers.add_parser("raw")
    raw_subparsers = raw_parser.add_subparsers(dest="raw_command", required=True)
    inbox_add_parser = raw_subparsers.add_parser("inbox-add")
    inbox_add_subparsers = inbox_add_parser.add_subparsers(dest="source_type", required=True)
    for source_type in sorted(storage.SOURCE_TYPES):
        source_parser = inbox_add_subparsers.add_parser(source_type)
        source_parser.add_argument("--type", dest="content_type", required=True, choices=sorted(storage.CONTENT_TYPES))
        source_parser.add_argument("--path", required=True)
        source_parser.add_argument("--title")
        source_parser.add_argument("--accept", action="store_true")
    promote_parser = raw_subparsers.add_parser("promote")
    promote_parser.add_argument("--id", required=True)
    sync_parser = raw_subparsers.add_parser("sync")
    sync_parser.add_argument("--id", required=True)

    triage_parser = subparsers.add_parser("triage")
    triage_subparsers = triage_parser.add_subparsers(dest="triage_command", required=True)
    triage_subparsers.add_parser("list")
    prompt_parser = triage_subparsers.add_parser("prompt")
    prompt_parser.add_argument("--id", required=True)
    prompt_batch_parser = triage_subparsers.add_parser("prompt-batch")
    prompt_batch_parser.add_argument("--limit", type=int, default=5)
    for action in ("accept", "reject", "later"):
        action_parser = triage_subparsers.add_parser(action)
        action_parser.add_argument("--id", required=True)

    learn_parser = subparsers.add_parser("learn")
    learn_parser.add_argument("--id")
    learn_parser.add_argument("--mode", choices=["outline", "deep_dive"])
    learn_parser.add_argument("--focus")
    learn_subparsers = learn_parser.add_subparsers(dest="learn_command")
    learn_subparsers.add_parser("queue")
    learn_subparsers.add_parser("list")
    next_parser = learn_subparsers.add_parser("next")
    next_parser.add_argument("--focus")
    pause_parser = learn_subparsers.add_parser("pause")
    pause_parser.add_argument("--id", required=True)
    consolidate_parser = learn_subparsers.add_parser("consolidate")
    consolidate_parser.add_argument("--id", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--id", required=True)

    publish_parser = subparsers.add_parser("publish")
    publish_subparsers = publish_parser.add_subparsers(dest="publish_command", required=True)
    for publish_target in ("triage", "learn", "consolidate", "item"):
        publish_target_parser = publish_subparsers.add_parser(publish_target)
        publish_target_parser.add_argument("--id", required=True)

    subparsers.add_parser("gui")

    config_parser = subparsers.add_parser("config")
    config_subparsers = config_parser.add_subparsers(dest="config_command", required=True)
    config_subparsers.add_parser("show")
    set_vault_parser = config_subparsers.add_parser("set-obsidian-vault")
    set_vault_parser.add_argument("--path", required=True)
    set_full_root_parser = config_subparsers.add_parser("set-raw-full-root")
    set_full_root_parser.add_argument("--path", required=True)
    set_sync_root_parser = config_subparsers.add_parser("set-raw-sync-root")
    set_sync_root_parser.add_argument("--path", required=True)
    set_workspace_root_parser = config_subparsers.add_parser("set-workspace-root")
    set_workspace_root_parser.add_argument("--path", required=True)
    set_device_parser = config_subparsers.add_parser("set-device-name")
    set_device_parser.add_argument("--name", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=_default_log_level(args),
        format="%(levelname)s %(message)s",
        force=True,
    )
    root = storage.get_repo_root()

    try:
        if args.command == "gui":
            from scripts import gui

            return gui.main()
        if args.command != "config":
            storage.ensure_storage_layout(root)
        if args.command == "add":
            _handle_add(args.source_type, args.content_type, args.path, args.title, args.accept, root)
        elif args.command == "triage":
            _handle_triage(args, root)
        elif args.command == "learn":
            _handle_learn(args, root)
        elif args.command == "raw":
            _handle_raw(args, root)
        elif args.command == "status":
            _handle_status(args.id, root)
        elif args.command == "publish":
            _handle_publish(args, root)
        elif args.command == "config":
            _handle_config(args, root)
        return 0
    except Exception as exc:
        LOGGER.error("%s", exc)
        return 1


def _default_log_level(args: argparse.Namespace) -> int:
    if args.command == "triage" and args.triage_command in {"list", "prompt", "prompt-batch"}:
        return READ_ONLY_LOG_LEVEL
    if args.command == "learn":
        return READ_ONLY_LOG_LEVEL
    if args.command == "status":
        return READ_ONLY_LOG_LEVEL
    if args.command == "config" and args.config_command == "show":
        return READ_ONLY_LOG_LEVEL
    return MUTATING_LOG_LEVEL


def _handle_add(
    source_type: str,
    content_type: str,
    source_path: str,
    title: str | None,
    accept_mode: bool,
    root: Path,
) -> None:
    source_file = Path(source_path).expanduser().resolve()
    plan = ingest_detection.build_ingest_plan(
        source_type=source_type,
        content_type=content_type,
        source_path=source_file,
        explicit_title=title,
        explicit_accept=accept_mode,
    )

    if plan.is_url_list:
        result = url_ingest.ingest_url_list(
            source_type=source_type,
            content_type=content_type,
            url_list_path=source_file,
            initial_status=plan.initial_status,
            root=root,
        )
        print(f"added {source_type} url items: {len(result['added_items'])}")
        print(f"detected_input: url_list")
        print(f"detected_status: {plan.initial_status}")
        print(f"detection_reason: {plan.detection_reason}")
        for item in result["added_items"]:
            print(f"{item['id']} | {item['title']} | status={item['status']}")
        if result["duplicate_items"]:
            print(f"duplicate urls: {len(result['duplicate_items'])}")
            for item in result["duplicate_items"]:
                print(f"{item['id']} | {item['title']} | existing")
        if result["failures"]:
            print(f"failed urls: {len(result['failures'])}")
            for failure in result["failures"]:
                print(f"{failure['url']} | {failure['error']}")
        return

    content_hash = storage.compute_file_hash(source_file)
    existing_item = storage.find_content_item_by_hash(content_hash, root)
    if existing_item is not None:
        print(f"duplicate item: {existing_item['id']}")
        print(f"title: {existing_item['title']}")
        print(f"status: {existing_item['status']}")
        return
    doc_id = storage.build_doc_id(plan.title, source_type, root)
    stored_file_info = storage.ingest_raw_file(doc_id, source_type, source_file, root)
    status = plan.initial_status
    recommendation = "learn" if status == "accepted" else "skim"

    item = storage.create_content_item(
        doc_id=doc_id,
        title=plan.title,
        source_type=source_type,
        content_type=content_type,
        ingest_date=date.today().isoformat(),
        status=status,
        priority=1.0 if source_type == "manual" else 0.5,
        ai_recommendation=recommendation,
        manual_decision=None,
        storage_tier=stored_file_info["storage_tier"],
        full_raw_relpath=stored_file_info["full_raw_relpath"],
        sync_raw_relpath=stored_file_info["sync_raw_relpath"],
        source_filename=stored_file_info["source_filename"],
        source_device=stored_file_info["source_device"],
        content_hash=stored_file_info["content_hash"],
        sync_status=stored_file_info["sync_status"],
    )
    storage.write_content_item(item, root)

    if status == "accepted":
        storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), root)

    print(f"added {source_type} item: {doc_id}")
    print(f"storage_tier: {item['storage_tier']}")
    print(f"full_raw_relpath: {item['full_raw_relpath']}")
    print(f"sync_raw_relpath: {item['sync_raw_relpath']}")
    print(f"detected_input: {'url_list' if plan.is_url_list else 'file'}")
    print(f"detected_status: {plan.initial_status}")
    print(f"detection_reason: {plan.detection_reason}")
    print(f"status: {status}")


def _handle_raw(args: argparse.Namespace, root: Path) -> None:
    if args.raw_command == "inbox-add":
        _handle_raw_inbox_add(args.source_type, args.content_type, args.path, args.title, args.accept, root)
        return

    if args.raw_command == "promote":
        item = storage.promote_item_to_full(args.id, root)
        print(f"promoted to full: {item['id']}")
        print(f"full_raw_relpath: {item['full_raw_relpath']}")
        return

    item = storage.sync_item_to_active(args.id, root)
    print(f"synced active: {item['id']}")
    print(f"sync_raw_relpath: {item['sync_raw_relpath']}")


def _handle_raw_inbox_add(
    source_type: str,
    content_type: str,
    source_path: str,
    title: str | None,
    accept_mode: bool,
    root: Path,
) -> None:
    source_file = Path(source_path).expanduser().resolve()
    plan = ingest_detection.build_ingest_plan(
        source_type=source_type,
        content_type=content_type,
        source_path=source_file,
        explicit_title=title,
        explicit_accept=accept_mode,
    )
    if plan.is_url_list:
        raise ValueError("raw inbox-add does not support URL list inputs; use pkls add instead")
    content_hash = storage.compute_file_hash(source_file)
    existing_item = storage.find_content_item_by_hash(content_hash, root)
    if existing_item is not None:
        print(f"duplicate item: {existing_item['id']}")
        print(f"title: {existing_item['title']}")
        print(f"status: {existing_item['status']}")
        return
    doc_id = storage.build_doc_id(plan.title, source_type, root)
    stored_file_info = storage.ingest_raw_file_to_inbox(doc_id, source_type, source_file, root)
    status = plan.initial_status
    recommendation = "learn" if status == "accepted" else "skim"

    item = storage.create_content_item(
        doc_id=doc_id,
        title=plan.title,
        source_type=source_type,
        content_type=content_type,
        ingest_date=date.today().isoformat(),
        status=status,
        priority=1.0 if source_type == "manual" else 0.5,
        ai_recommendation=recommendation,
        manual_decision=None,
        storage_tier=stored_file_info["storage_tier"],
        full_raw_relpath=stored_file_info["full_raw_relpath"],
        sync_raw_relpath=stored_file_info["sync_raw_relpath"],
        source_filename=stored_file_info["source_filename"],
        source_device=stored_file_info["source_device"],
        content_hash=stored_file_info["content_hash"],
        sync_status=stored_file_info["sync_status"],
    )
    storage.write_content_item(item, root)

    if status == "accepted":
        storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), root)

    print(f"added inbox {source_type} item: {doc_id}")
    print(f"sync_raw_relpath: {item['sync_raw_relpath']}")
    print(f"sync_status: {item['sync_status']}")
    print(f"detected_status: {plan.initial_status}")
    print(f"detection_reason: {plan.detection_reason}")
    print(f"status: {status}")


def _handle_triage(args: argparse.Namespace, root: Path) -> None:
    publish.sync_complete_triage_cards(root)

    if args.triage_command == "list":
        rows = triage.list_candidate_reviews(root)
        _print_triage_rows(rows)
        return

    if args.triage_command == "prompt":
        prompt_path = agent_workflow.write_triage_prompt(args.id, root)
        print(f"saved triage prompt: {prompt_path}")
        return

    if args.triage_command == "prompt-batch":
        _handle_triage_prompt_batch(args.limit, root)
        return

    if args.triage_command == "accept":
        item = triage.accept_candidate(args.id, root)
        print(f"accepted: {item['id']}")
        return

    if args.triage_command == "reject":
        item = triage.reject_candidate(args.id, root)
        print(f"rejected: {item['id']}")
        return

    item = triage.defer_candidate(args.id, root)
    print(f"deferred: {item['id']}")


def _handle_learn(args: argparse.Namespace, root: Path) -> None:
    if args.learn_command == "queue":
        rows = learning.list_learning_items(root)
        _print_learning_rows(rows)
        return

    if args.learn_command == "list":
        rows = learning.list_learning_items(root)
        _print_learning_rows(rows)
        return

    if args.learn_command == "next":
        target = learning.get_next_learning_target(root)
        prompt_path = agent_workflow.write_learning_prompt(
            target["item"]["id"],
            target["mode"],
            args.focus,
            root,
        )
        print(f"saved learning prompt: {prompt_path}")
        print(f"doc_id: {target['item']['id']}")
        print(f"mode: {target['mode']}")
        _print_initialize_review_hint(target["item"]["id"], target["mode"], root)
        return

    if args.learn_command == "pause":
        prompt_path = agent_workflow.write_pause_prompt(args.id, root)
        print(f"saved learning pause prompt: {prompt_path}")
        print(f"doc_id: {args.id}")
        return

    if args.learn_command == "consolidate":
        prompt_path = agent_workflow.write_consolidate_prompt(args.id, root)
        print(f"saved consolidation prompt: {prompt_path}")
        print(f"doc_id: {args.id}")
        return

    if args.id is not None:
        mode = args.mode or learning.resolve_learning_mode(args.id, root)
        prompt_path = agent_workflow.write_learning_prompt(args.id, mode, args.focus, root)
        print(f"saved learning prompt: {prompt_path}")
        print(f"doc_id: {args.id}")
        print(f"mode: {mode}")
        _print_initialize_review_hint(args.id, mode, root)
        return

    raise ValueError("learn requires queue, list, next, pause, consolidate, or --id")


def _print_initialize_review_hint(doc_id: str, mode: str, root: Path) -> None:
    if mode != "outline":
        return

    output_dir = storage.get_learning_outputs_root(root) / doc_id
    state_path = storage.get_learning_states_root(root) / doc_id / "state.json"
    print("after agent completes initialize, review:")
    print(f"  status: python pkls status --id {doc_id}")
    print(f"  outline: {output_dir / 'outline.md'}")
    print(f"  published_outline: {local_config.get_notes_publish_root(root) / publish.PUBLISH_ROOT_DIR / 'learning' / 'outlines' / f'{doc_id}.md'}")
    print(f"  state: {state_path}")
    print(f"  chunk_manifest: {output_dir / 'chunk_manifest.json'} if processing_mode is chunked")


def _handle_status(doc_id: str, root: Path) -> None:
    result = learning.read_status(doc_id, root)
    item = result["item"]
    state = result["state"]
    queue_entry = result["queue_entry"]
    open_questions = result["open_questions"]
    next_action = result["next_action"]

    print(f"id: {item['id']}")
    print(f"title: {item['title']}")
    print(f"source_type: {item['source_type']}")
    print(f"content_type: {item['content_type']}")
    print(f"ingest_date: {item['ingest_date']}")
    print(f"status: {item['status']}")
    print(f"priority: {item['priority']}")
    print(f"ai_recommendation: {item['ai_recommendation']}")
    print(f"manual_decision: {item['manual_decision']}")
    print(f"storage_tier: {item['storage_tier']}")
    print(f"full_raw_relpath: {item['full_raw_relpath']}")
    print(f"sync_raw_relpath: {item['sync_raw_relpath']}")
    print(f"source_filename: {item['source_filename']}")
    print(f"source_device: {item['source_device']}")
    print(f"sync_status: {item['sync_status']}")
    print(f"queue_status: {queue_entry['status'] if queue_entry is not None else 'none'}")

    if state is None:
        print("learning_progress: not_started")
        print("current_chunk: 0/0")
    else:
        print(f"initialized: {state['initialized']}")
        print(f"processing_mode: {state['processing_mode']}")
        print(f"outline_generated: {state['outline_generated']}")
        print(f"learning_progress: {state['progress']}")
        print(f"current_chunk: {state['current_chunk']}/{state['chunks_total']}")
        print(f"current_focus: {state['current_focus'] if state['current_focus'] is not None else 'none'}")
        print(f"focus_history_count: {len(state['focus_history'])}")
        print(f"interaction_count: {state['interaction_count']}")
        print(f"ready_to_consolidate: {state['ready_to_consolidate']}")

    print("open_questions:")
    if open_questions:
        for question in open_questions:
            print(f"- {question}")
    else:
        print("- none")
    print(f"next_action: {next_action}")


def _print_triage_rows(rows: list[dict[str, object]]) -> None:
    ready_rows = [row for row in rows if row["triage_card"] is not None]
    pending_rows = [row for row in rows if row["triage_card"] is None]

    print(f"candidates: {len(rows)}")
    print("")
    _print_triage_group("ready_for_decision", ready_rows)
    print("")
    _print_triage_group("needs_triage_card", pending_rows)


def _print_triage_group(label: str, rows: list[dict[str, object]]) -> None:
    print(f"{label}: {len(rows)}")
    if not rows:
        print("  - none")
        return

    for row in rows:
        item = row["item"]
        triage_card = row["triage_card"]
        recommendation = item["ai_recommendation"]
        summary = "none"
        reason = ""
        if triage_card is not None:
            recommendation = triage_card["recommendation"] or recommendation
            summary = triage_card["summary"] or "none"
            reason = triage_card["reason"]
        print(f"- {item['id']}")
        print(f"  title: {item['title']}")
        print(f"  source_type: {item['source_type']}")
        print(f"  priority: {item['priority']}")
        print(f"  recommendation: {recommendation}")
        print(f"  decision: {item['manual_decision']}")
        print(f"  summary: {_preview_text(summary)}")
        if reason:
            print(f"  reason: {_preview_text(reason)}")
        if triage_card is None:
            print(f"  next_action: python pkls triage prompt --id {item['id']}")
        print("")


def _print_learning_rows(rows: list[dict[str, object]]) -> None:
    groups = {"doing": [], "todo": [], "paused": [], "done": [], "none": []}
    for row in rows:
        queue_entry = row["queue_entry"]
        status = "none" if queue_entry is None else queue_entry["status"]
        groups[status].append(row)

    print(f"learning items: {len(rows)}")
    non_empty_labels = [label for label in ("doing", "todo", "paused", "done", "none") if groups[label]]
    if not non_empty_labels:
        print("")
        print("  - none")
        return

    print("")
    for index, label in enumerate(non_empty_labels):
        _print_learning_group(label, groups[label])
        if index < len(non_empty_labels) - 1:
            print("")


def _handle_triage_prompt_batch(limit: int, root: Path) -> None:
    if limit <= 0:
        raise ValueError("prompt-batch --limit must be greater than 0")

    rows = triage.list_candidates_needing_triage_card(limit, root)
    if not rows:
        print("no candidate items need triage cards")
        return

    prompt_path, selected_ids, total_pending = agent_workflow.write_triage_batch_prompt(limit, root)
    print(f"saved triage batch prompt: {prompt_path}")
    print(f"selected_items: {len(selected_ids)}/{total_pending}")
    for doc_id in selected_ids:
        print(doc_id)


def _print_learning_group(label: str, rows: list[dict[str, object]]) -> None:
    print(f"{label}: {len(rows)}")
    for index, row in enumerate(rows):
        item = row["item"]
        state = row["state"]
        progress = "not_started" if state is None else f"{state['progress']:.2f}"
        chunk_progress = "0/0" if state is None else f"{state['current_chunk']}/{state['chunks_total']}"
        processing_mode = "unknown" if state is None else state["processing_mode"]
        current_focus = "none" if state is None or state["current_focus"] is None else state["current_focus"]
        print(f"- {item['id']}")
        print(f"  title: {item['title']}")
        print(f"  item_status: {item['status']}")
        print(f"  processing_mode: {processing_mode}")
        print(f"  progress: {progress}")
        print(f"  chunks: {chunk_progress}")
        print(f"  current_focus: {current_focus}")
        print(f"  next_action: {row['next_action']}")
        if index < len(rows) - 1:
            print("")


def _preview_text(text: str) -> str:
    compact = " ".join(text.split())
    if len(compact) <= TEXT_PREVIEW_LIMIT:
        return compact
    return f"{compact[:TEXT_PREVIEW_LIMIT - 3]}..."


def _handle_config(args: argparse.Namespace, root: Path) -> None:
    if args.config_command == "show":
        config_path = local_config.get_local_config_path(root)
        device_name = local_config.get_device_name(root)
        vault_path = local_config.get_obsidian_vault_path(root)
        raw_full_root = local_config.get_raw_full_root(root)
        raw_sync_root = local_config.get_raw_sync_root(root)
        workspace_root = local_config.get_workspace_root(root)
        try:
            publish_root = local_config.get_notes_publish_root(root)
        except Exception:
            publish_root = "not_set"
        print(f"local_config: {config_path}")
        print(f"device_name: {device_name if device_name is not None else 'not_set'}")
        print(f"obsidian_vault_path: {vault_path if vault_path is not None else 'not_set'}")
        print(f"raw_full_root: {raw_full_root if raw_full_root is not None else 'not_set'}")
        print(f"raw_sync_root: {raw_sync_root if raw_sync_root is not None else 'not_set'}")
        print(f"workspace_root: {workspace_root if workspace_root is not None else 'not_set'}")
        print(f"notes_publish_root: {publish_root}")
        return

    if args.config_command == "set-obsidian-vault":
        config_path = local_config.set_obsidian_vault_path(args.path, root)
        vault_path = local_config.get_obsidian_vault_path(root)
        print(f"updated local config: {config_path}")
        print(f"obsidian_vault_path: {vault_path}")
        return

    if args.config_command == "set-raw-full-root":
        config_path = local_config.set_raw_full_root(args.path, root)
        full_root = local_config.get_raw_full_root(root)
        print(f"updated local config: {config_path}")
        print(f"raw_full_root: {full_root}")
        return

    if args.config_command == "set-raw-sync-root":
        config_path = local_config.set_raw_sync_root(args.path, root)
        sync_root = local_config.get_raw_sync_root(root)
        print(f"updated local config: {config_path}")
        print(f"raw_sync_root: {sync_root}")
        return

    if args.config_command == "set-workspace-root":
        config_path = local_config.set_workspace_root(args.path, root)
        workspace_root = local_config.get_workspace_root(root)
        print(f"updated local config: {config_path}")
        print(f"workspace_root: {workspace_root}")
        return

    config_path = local_config.set_device_name(args.name, root)
    device_name = local_config.get_device_name(root)
    print(f"updated local config: {config_path}")
    print(f"device_name: {device_name}")


def _handle_publish(args: argparse.Namespace, root: Path) -> None:
    if args.publish_command == "triage":
        target_path = publish.publish_triage(args.id, root)
        print(f"synchronized triage: {target_path}")
        return

    if args.publish_command == "learn":
        target_paths = publish.publish_learning(args.id, root)
        print(f"synchronized learning files: {len(target_paths)}")
        for path in target_paths:
            print(path)
        return

    if args.publish_command == "consolidate":
        target_paths = publish.publish_consolidation(args.id, root)
        print(f"synchronized consolidation files: {len(target_paths)}")
        for path in target_paths:
            print(path)
        return

    target_paths = publish.publish_item(args.id, root)
    print(f"synchronized files: {len(target_paths)}")
    for path in target_paths:
        print(path)

if __name__ == "__main__":
    sys.exit(main())
