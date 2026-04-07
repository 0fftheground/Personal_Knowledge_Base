"""CLI entrypoint for the local MVP knowledge system."""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import date
from pathlib import Path

from scripts import learning
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

    triage_parser = subparsers.add_parser("triage")
    triage_subparsers = triage_parser.add_subparsers(dest="triage_command", required=True)
    triage_subparsers.add_parser("run")
    triage_subparsers.add_parser("list")
    for action in ("accept", "reject", "later"):
        action_parser = triage_subparsers.add_parser(action)
        action_parser.add_argument("--id", required=True)

    learn_parser = subparsers.add_parser("learn")
    learn_subparsers = learn_parser.add_subparsers(dest="learn_command", required=True)
    learn_subparsers.add_parser("queue")
    next_parser = learn_subparsers.add_parser("next")
    next_parser.set_defaults(id=None)
    for action in ("start", "resume"):
        action_parser = learn_subparsers.add_parser(action)
        action_parser.add_argument("--id", required=True)

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--id", required=True)

    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)
    root = storage.get_repo_root()
    storage.ensure_storage_layout(root)

    try:
        if args.command == "add":
            _handle_add(args.source_type, args.content_type, args.path, args.title, root)
        elif args.command == "triage":
            _handle_triage(args, root)
        elif args.command == "learn":
            _handle_learn(args, root)
        elif args.command == "status":
            _handle_status(args.id, root)
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
    relative_path = storage.copy_raw_content(doc_id, source_type, source_file, root)
    status = "accepted" if source_type == "manual" else "candidate"
    recommendation = "learn" if source_type == "manual" else "skim"

    item = storage.create_content_item(
        doc_id=doc_id,
        title=title,
        source_type=source_type,
        content_type=content_type,
        path=relative_path,
        ingest_date=date.today().isoformat(),
        status=status,
        priority=1.0 if source_type == "manual" else 0.5,
        ai_recommendation=recommendation,
        manual_decision=None,
    )
    storage.write_content_item(item, root)

    if source_type == "manual":
        storage.upsert_queue_entry(storage.create_queue_entry(doc_id, item["priority"], "todo"), root)

    print(f"added {source_type} item: {doc_id}")
    print(f"path: {relative_path}")
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

    print(f"id: {item['id']}")
    print(f"title: {item['title']}")
    print(f"source_type: {item['source_type']}")
    print(f"content_type: {item['content_type']}")
    print(f"status: {item['status']}")
    print(f"priority: {item['priority']}")
    print(f"path: {item['path']}")

    if state is None:
        print("learning_progress: not_started")
        return

    print(f"learning_progress: {state['progress']}")
    print(f"current_chunk: {state['current_chunk']}/{state['chunks_total']}")
    print("open_questions:")
    for question in state["questions"]:
        print(f"- {question}")
    print(f"next_action: {state['next_action']}")


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
