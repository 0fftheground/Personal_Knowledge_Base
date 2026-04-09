"""Prompt builders for Codex-assisted triage and learning workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts import learning
from scripts import local_config
from scripts import publish
from scripts import storage
from scripts import triage


def build_triage_prompt(doc_id: str, root: Path | None = None) -> str:
    base = root or storage.get_repo_root()
    workspace_root = storage.get_workspace_root(base)
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] != "candidate":
        raise ValueError(f"triage prompt requires a candidate item: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
    publish_path = local_config.get_notes_publish_root(base) / publish.PUBLISH_ROOT_DIR / "triage" / f"{item['id']}.md"
    prompt_path = base / "prompts" / "triage_prompt.md"

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Repository root: {base}\n"
        f"- Workspace root: {workspace_root}\n"
        f"- Prompt file: {prompt_path}\n"
        f"- Metadata file: {metadata_path}\n"
        f"- Raw content file: {raw_path}\n"
        f"- Target triage card: {card_path}\n\n"
        f"- Auto-publish target: {publish_path}\n\n"
        "## Concrete Instructions\n\n"
        f"1. Read {metadata_path} and {raw_path}.\n"
        "2. Judge the content for truthfulness, source reliability, and learning value.\n"
        "3. Update metadata.json so ai_recommendation is correct.\n"
        "4. Keep status as candidate and do not change the queue.\n"
        f"5. Write or update {card_path} with summary, key points, recommendation, and reason.\n"
        f"6. If the triage card is complete, copy it to {publish_path}.\n"
        "7. Return a short confirmation after the file edits are complete.\n"
    )


def write_triage_prompt(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    prompt_path = storage.get_triage_prompts_root(base) / f"{doc_id}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_triage_prompt(doc_id, base), encoding="utf-8")
    return prompt_path


def build_triage_batch_prompt(
    rows: list[dict[str, Any]],
    total_pending: int,
    root: Path | None = None,
) -> str:
    base = root or storage.get_repo_root()
    workspace_root = storage.get_workspace_root(base)
    prompt_path = base / "prompts" / "triage_prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    selected_count = len(rows)
    remaining_count = max(total_pending - selected_count, 0)

    item_sections: list[str] = []
    for index, row in enumerate(rows, start=1):
        item = row["item"]
        metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
        raw_path = storage.resolve_raw_path(item, base)
        card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
        publish_path = local_config.get_notes_publish_root(base) / publish.PUBLISH_ROOT_DIR / "triage" / f"{item['id']}.md"
        item_sections.append(
            f"### Item {index}: {item['id']}\n\n"
            f"- Title: {item['title']}\n"
            f"- Source type: {item['source_type']}\n"
            f"- Priority: {item['priority']}\n"
            f"- Metadata file: {metadata_path}\n"
            f"- Raw content file: {raw_path}\n"
            f"- Target triage card: {card_path}\n"
            f"- Auto-publish target: {publish_path}\n"
        )

    return (
        f"{prompt}\n\n"
        "## Batch Execution Context\n\n"
        f"- Repository root: {base}\n"
        f"- Workspace root: {workspace_root}\n"
        f"- Prompt file: {prompt_path}\n"
        f"- Selected candidate items: {selected_count}\n"
        f"- Total candidate items needing triage cards: {total_pending}\n"
        f"- Remaining after this batch: {remaining_count}\n\n"
        "## Batch Instructions\n\n"
        "1. Process the selected items strictly in the order listed below.\n"
        "2. For each item: read metadata and raw content, update ai_recommendation, keep status as candidate, write the triage card, and publish it to the listed Obsidian path when the card is complete.\n"
        "3. Finish the current item before moving to the next one.\n"
        "4. Do not change the queue.\n"
        "5. Return a short confirmation with the completed item ids and any remaining items still needing triage.\n\n"
        "## Selected Items\n\n"
        + "\n".join(item_sections)
    )


def write_triage_batch_prompt(limit: int, root: Path | None = None) -> tuple[Path, list[str], int]:
    base = root or storage.get_repo_root()
    rows = triage.list_candidates_needing_triage_card(limit, base)
    total_pending = len(triage.list_candidates_needing_triage_card(None, base))
    prompt_path = storage.get_triage_prompts_root(base) / f"batch-next-{len(rows)}.md"
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_triage_batch_prompt(rows, total_pending, base), encoding="utf-8")
    selected_ids = [row["item"]["id"] for row in rows]
    return prompt_path, selected_ids, total_pending


def build_learning_prompt(
    doc_id: str,
    mode: str,
    focus: str | None = None,
    root: Path | None = None,
) -> str:
    base = root or storage.get_repo_root()
    learning.sync_queue(base)
    workspace_root = storage.get_workspace_root(base)
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] not in {"accepted", "learning", "done"}:
        raise ValueError(f"learning prompt requires an accepted or learning item: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    state_path = storage.get_learning_states_root(base) / item["id"] / "state.json"
    output_dir = storage.get_learning_outputs_root(base) / item["id"]
    queue_path = storage.get_learning_root(base) / "queue.json"
    queue_entry = storage.get_queue_entry(item["id"], base)
    outline_path = output_dir / "outline.md"
    summary_path = output_dir / "summary.md"
    insights_path = output_dir / "insights.md"
    qa_path = output_dir / "qa.md"
    prompt_path = base / "prompts" / "learning_prompt.md"

    state_exists = state_path.exists()
    focus_line = focus if focus else "None provided. Default to the next most useful learning step."

    if mode not in {"outline", "deep_dive"}:
        raise ValueError(f"mode must be 'outline' or 'deep_dive', got {mode!r}")

    if mode == "deep_dive" and not state_exists:
        raise ValueError(f"deep_dive mode requires an existing state file; run outline first for {doc_id}")

    if mode == "deep_dive" and state_exists:
        state = storage.read_learning_state(item["id"], base)
        if not state["outline_generated"]:
            raise ValueError(f"deep_dive mode requires outline_generated=true for {doc_id}")
        if state["status"] == "done" or item["status"] == "done":
            raise ValueError(f"learning is already complete for {doc_id}")

    if mode == "outline":
        instructions = (
            "## Concrete Instructions\n\n"
            f"1. Read {metadata_path} and {raw_path}.\n"
            f"2. Read and update {queue_path}.\n"
            "3. If state.json does not exist, create it using docs/schema.md.\n"
            "4. Generate a document-level framework before any deep dive.\n"
            "5. Update metadata.json so item status is learning unless the document is already done.\n"
            "6. Update state.json with outline_generated=true, document_outline, core_summary, and a next_action that asks for a focus area.\n"
            "7. Update queue.json so this item is present with status=doing.\n"
            f"8. Write {outline_path}.\n"
            "9. Do not process the full document chunk by chunk yet.\n"
            "10. Return a short confirmation after the file edits are complete.\n"
        )
    else:
        instructions = (
            "## Concrete Instructions\n\n"
            f"1. Read {metadata_path}, {raw_path}, and {state_path if state_exists else 'the state schema from docs/schema.md'}.\n"
            f"2. Read and update {queue_path}.\n"
            f"3. Use {outline_path} if it exists.\n"
            f"4. User focus request: {focus_line}\n"
            "5. Process exactly one coherent learning unit.\n"
            "6. Update state.json incrementally: progress, current_chunk, key_points, questions, next_action, status.\n"
            "7. Update metadata.json so item status is learning or done, matching the learning state.\n"
            "8. Update queue.json so this item is doing while work remains and done when learning is complete.\n"
            f"9. Update {summary_path}, {insights_path}, and {qa_path}.\n"
            "10. Keep the workflow resumable. Do not reprocess everything.\n"
            "11. Return a short confirmation after the file edits are complete.\n"
        )

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Repository root: {base}\n"
        f"- Workspace root: {workspace_root}\n"
        f"- Prompt file: {prompt_path}\n"
        f"- Mode: {mode}\n"
        f"- Metadata file: {metadata_path}\n"
        f"- Raw content file: {raw_path}\n"
        f"- State file: {state_path}\n"
        f"- Queue file: {queue_path}\n"
        f"- Queue entry: {queue_entry}\n"
        f"- Output directory: {output_dir}\n"
        f"- Outline file: {outline_path}\n"
        f"- Summary file: {summary_path}\n"
        f"- Insights file: {insights_path}\n"
        f"- QA file: {qa_path}\n\n"
        f"{instructions}"
    )
