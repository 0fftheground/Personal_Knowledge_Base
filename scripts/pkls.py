"""CLI entrypoint for the local MVP knowledge system."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from scripts import codex_workflow
from scripts import learning
from scripts import local_config
from scripts import publish
from scripts import storage
from scripts import triage


LOGGER = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pkls")
    subparsers = parser.add_subparsers(dest="command", required=True)

    add_parser = subparsers.add_parser("add")
    add_subparsers = add_parser.add_subparsers(dest="source_type", required=True)
    for source_type in sorted(storage.SOURCE_TYPES):
        source_parser = add_subparsers.add_parser(source_type)
        source_parser.add_argument("--type", dest="content_type", required=True, choices=sorted(storage.CONTENT_TYPES))
        source_parser.add_argument("--path", required=True)
        source_parser.add_argument("--title", required=True)

    raw_parser = subparsers.add_parser("raw")
    raw_subparsers = raw_parser.add_subparsers(dest="raw_command", required=True)
    inbox_add_parser = raw_subparsers.add_parser("inbox-add")
    inbox_add_subparsers = inbox_add_parser.add_subparsers(dest="source_type", required=True)
    for source_type in sorted(storage.SOURCE_TYPES):
        source_parser = inbox_add_subparsers.add_parser(source_type)
        source_parser.add_argument("--type", dest="content_type", required=True, choices=sorted(storage.CONTENT_TYPES))
        source_parser.add_argument("--path", required=True)
        source_parser.add_argument("--title", required=True)
    promote_parser = raw_subparsers.add_parser("promote")
    promote_parser.add_argument("--id", required=True)
    sync_parser = raw_subparsers.add_parser("sync")
    sync_parser.add_argument("--id", required=True)

    triage_parser = subparsers.add_parser("triage")
    triage_subparsers = triage_parser.add_subparsers(dest="triage_command", required=True)
    triage_subparsers.add_parser("run")
    triage_subparsers.add_parser("list")
    prompt_parser = triage_subparsers.add_parser("prompt")
    prompt_parser.add_argument("--id", required=True)
    for action in ("accept", "reject", "later"):
        action_parser = triage_subparsers.add_parser(action)
        action_parser.add_argument("--id", required=True)

    learn_parser = subparsers.add_parser("learn")
    learn_subparsers = learn_parser.add_subparsers(dest="learn_command", required=True)
    learn_subparsers.add_parser("queue")
    next_parser = learn_subparsers.add_parser("next")
    next_parser.set_defaults(id=None)
    learn_prompt_parser = learn_subparsers.add_parser("prompt")
    learn_prompt_parser.add_argument("--id", required=True)
    learn_prompt_parser.add_argument("--mode", required=True, choices=["outline", "deep_dive"])
    learn_prompt_parser.add_argument("--focus")
    for action in ("start", "resume"):
        action_parser = learn_subparsers.add_parser(action)
        action_parser.add_argument("--id", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--id", required=True)

    publish_parser = subparsers.add_parser("publish")
    publish_subparsers = publish_parser.add_subparsers(dest="publish_command", required=True)
    for publish_target in ("triage", "learn", "item"):
        publish_target_parser = publish_subparsers.add_parser(publish_target)
        publish_target_parser.add_argument("--id", required=True)

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
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    root = storage.get_repo_root()

    try:
        if args.command != "config":
            storage.ensure_storage_layout(root)
        if args.command == "add":
            _handle_add(args.source_type, args.content_type, args.path, args.title, root)
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


def _handle_add(
    source_type: str,
    content_type: str,
    source_path: str,
    title: str,
    root: Path,
) -> None:
    source_file = Path(source_path).expanduser().resolve()
    doc_id = storage.build_doc_id(title, source_type, root)
    stored_file_info = storage.ingest_raw_file(doc_id, source_type, source_file, root)
    status = "accepted" if source_type == "manual" else "candidate"
    recommendation = "learn" if source_type == "manual" else "skim"

    item = storage.create_content_item(
        doc_id=doc_id,
        title=title,
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

    if source_type == "manual":
        storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), root)

    print(f"added {source_type} item: {doc_id}")
    print(f"storage_tier: {item['storage_tier']}")
    print(f"full_raw_relpath: {item['full_raw_relpath']}")
    print(f"sync_raw_relpath: {item['sync_raw_relpath']}")
    print(f"status: {status}")


def _handle_raw(args: argparse.Namespace, root: Path) -> None:
    if args.raw_command == "inbox-add":
        _handle_raw_inbox_add(args.source_type, args.content_type, args.path, args.title, root)
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
    title: str,
    root: Path,
) -> None:
    source_file = Path(source_path).expanduser().resolve()
    doc_id = storage.build_doc_id(title, source_type, root)
    stored_file_info = storage.ingest_raw_file_to_inbox(doc_id, source_type, source_file, root)
    status = "accepted" if source_type == "manual" else "candidate"
    recommendation = "learn" if source_type == "manual" else "skim"

    item = storage.create_content_item(
        doc_id=doc_id,
        title=title,
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

    if source_type == "manual":
        storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), root)

    print(f"added inbox {source_type} item: {doc_id}")
    print(f"sync_raw_relpath: {item['sync_raw_relpath']}")
    print(f"sync_status: {item['sync_status']}")
    print(f"status: {status}")


def _handle_triage(args: argparse.Namespace, root: Path) -> None:
    if args.triage_command == "run":
        processed_ids = triage.run_triage(root)
        print(f"triaged items: {len(processed_ids)}")
        for doc_id in processed_ids:
            print(doc_id)
        return

    if args.triage_command == "list":
        candidates = triage.list_candidates(root)
        print(f"candidates: {len(candidates)}")
        for item in candidates:
            print(f"{item['id']} | {item['title']} | priority={item['priority']} | recommendation={item['ai_recommendation']}")
        return

    if args.triage_command == "prompt":
        print(codex_workflow.build_triage_prompt(args.id, root))
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
        queue = learning.view_queue(root)
        print(f"queue items: {len(queue)}")
        for entry in queue:
            print(f"{entry['doc_id']} | priority={entry['priority']} | status={entry['status']}")
        return

    if args.learn_command == "start":
        result = learning.start_learning(args.id, root)
        print(_learning_summary(result))
        return

    if args.learn_command == "prompt":
        print(codex_workflow.build_learning_prompt(args.id, args.mode, args.focus, root))
        return

    if args.learn_command == "resume":
        result = learning.resume_learning(args.id, root)
        print(_learning_summary(result))
        return

    result = learning.learn_next(root)
    print(_learning_summary(result))


def _handle_status(doc_id: str, root: Path) -> None:
    result = learning.read_status(doc_id, root)
    item = result["item"]
    state = result["state"]
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

    if state is None:
        print("learning_progress: not_started")
        print("current_chunk: 0/0")
    else:
        print(f"outline_generated: {state['outline_generated']}")
        print(f"learning_progress: {state['progress']}")
        print(f"current_chunk: {state['current_chunk']}/{state['chunks_total']}")

    print("open_questions:")
    if open_questions:
        for question in open_questions:
            print(f"- {question}")
    else:
        print("- none")
    print(f"next_action: {next_action}")


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
        print(f"published triage: {target_path}")
        return

    if args.publish_command == "learn":
        target_paths = publish.publish_learning(args.id, root)
        print(f"published learning files: {len(target_paths)}")
        for path in target_paths:
            print(path)
        return

    target_paths = publish.publish_item(args.id, root)
    print(f"published files: {len(target_paths)}")
    for path in target_paths:
        print(path)


def _learning_summary(result: dict[str, object]) -> str:
    item = result["item"]
    state = result["state"]
    return (
        f"learning item: {item['id']}\n"
        f"status: {item['status']}\n"
        f"progress: {state['progress']}\n"
        f"current_chunk: {state['current_chunk']}/{state['chunks_total']}\n"
        f"next_action: {state['next_action']}"
    )


if __name__ == "__main__":
    sys.exit(main())
