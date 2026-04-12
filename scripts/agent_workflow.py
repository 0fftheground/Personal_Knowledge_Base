"""Prompt builders for agent-assisted triage, learning, and consolidation workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts import consolidation
from scripts import learning
from scripts import local_config
from scripts import publish
from scripts import storage
from scripts import triage


def build_triage_prompt(doc_id: str, root: Path | None = None) -> str:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] != "candidate":
        raise ValueError(f"triage prompt requires a candidate item: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
    publish_path = local_config.get_notes_publish_root(base) / publish.PUBLISH_ROOT_DIR / "triage" / f"{item['id']}.md"
    size_metrics = learning.collect_material_profile(doc_id, base)
    reading_budget = _triage_budget_instruction(item["content_type"], size_metrics)

    prompt_path = base / "prompts" / "triage_prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Files: metadata={metadata_path}, raw={raw_path}, card={card_path}, publish={publish_path}\n"
        f"- Size metrics: {size_metrics}\n\n"
        "## Instructions\n\n"
        f"1. Inspect bounded context only. Budget: {reading_budget}\n"
        "2. Update metadata, write the compact card, publish it if complete, and confirm.\n"
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
        size_metrics = learning.collect_material_profile(item["id"], base)
        item_sections.append(
            f"### Item {index}: {item['id']}\n\n"
            f"- Title: {item['title']}\n"
            f"- Paths: metadata={metadata_path}, raw={raw_path}, card={card_path}, publish={publish_path}\n"
            f"- Size metrics: {size_metrics}\n"
            f"- Reading rule: {_triage_budget_instruction(item['content_type'], size_metrics)}\n"
        )

    return (
        f"{prompt}\n\n"
        "## Batch Execution Context\n\n"
        f"- Selected candidate items: {selected_count}\n"
        f"- Total candidate items needing triage cards: {total_pending}\n"
        f"- Remaining after this batch: {remaining_count}\n\n"
        "## Batch Instructions\n\n"
        "1. Process the selected items in order.\n"
        "2. For each item: bounded read, update metadata, write compact card, publish if complete.\n"
        "3. Do not change the queue. Confirm completed ids and remaining count.\n\n"
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
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] not in {"accepted", "learning", "paused", "done"}:
        raise ValueError(f"learning prompt requires an accepted, paused, or learning item: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    state_path = storage.get_learning_states_root(base) / item["id"] / "state.json"
    queue_path = storage.get_learning_root(base) / "queue.json"
    queue_entry = storage.get_queue_entry(item["id"], base)
    output_dir = storage.get_learning_outputs_root(base) / item["id"]
    outline_path = output_dir / "outline.md"
    summary_path = output_dir / "summary.md"
    insights_path = output_dir / "insights.md"
    chunk_manifest_path = output_dir / "chunk_manifest.json"
    state_exists = state_path.exists()
    state = storage.read_learning_state(item["id"], base) if state_exists else None
    size_metrics = learning.collect_material_profile(doc_id, base)
    suggested_mode = learning.suggest_processing_mode(doc_id, base)

    if mode not in {"outline", "deep_dive"}:
        raise ValueError(f"mode must be 'outline' or 'deep_dive', got {mode!r}")

    if mode == "deep_dive" and not state_exists:
        raise ValueError(f"deep_dive mode requires an existing state file; run initialization first for {doc_id}")

    if mode == "deep_dive" and state is not None and state["status"] == "done":
        raise ValueError(f"learning is already complete for {doc_id}")

    prompt_path = base / "prompts" / "learning_prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    focus_line = focus if focus else (state["current_focus"] if state is not None and state["current_focus"] else "No explicit focus yet.")
    execution_context = (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Internal mode: {mode}\n"
        f"- Suggested processing mode: {suggested_mode}\n"
        f"- Size metrics: {size_metrics}\n"
        f"- Files: metadata={metadata_path}, raw={raw_path}, state={state_path}, queue={queue_path}\n"
        f"- Queue entry: {queue_entry}\n"
        f"- Outputs: outline={outline_path}, summary={summary_path}, insights={insights_path}, chunk_manifest={chunk_manifest_path}\n"
        f"- Current focus request: {focus_line}\n\n"
    )

    if mode == "outline":
        return execution_context + (
            "## Instructions\n\n"
            f"1. Read {metadata_path}, {raw_path}, and {queue_path}.\n"
            f"2. Create/update state, set metadata to `learning`, queue to `doing`, and write {outline_path}.\n"
            f"3. Choose processing mode. Suggested: {suggested_mode}. If chunked, write {chunk_manifest_path}.\n"
            f"4. Publish the outline to Obsidian now with `python pkls publish learn --id {item['id']}`.\n"
            "   Keep later focus outputs for manual publish.\n"
            "5. Do not generate qa.md. Confirm when done.\n"
        )

    return execution_context + (
        "## Instructions\n\n"
        f"1. Read {metadata_path}, {raw_path}, and {state_path}.\n"
        f"2. Use {outline_path}; treat focus as intent and load only minimum relevant context.\n"
        "3. Guide the focused session. Do not generate qa.md. Confirm context is ready.\n"
    )


def write_learning_prompt(
    doc_id: str,
    mode: str,
    focus: str | None = None,
    root: Path | None = None,
) -> Path:
    base = root or storage.get_repo_root()
    prompt_path = _learning_prompt_path(doc_id, "initialize" if mode == "outline" else "focus", base)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_learning_prompt(doc_id, mode, focus, base), encoding="utf-8")
    return prompt_path


def build_pause_prompt(doc_id: str, root: Path | None = None) -> str:
    base = root or storage.get_repo_root()
    learning.sync_queue(base)
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] not in {"learning", "paused", "accepted"}:
        raise ValueError(f"pause prompt requires an accepted, paused, or learning item: {doc_id}")
    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    state_path = storage.get_learning_states_root(base) / item["id"] / "state.json"
    output_dir = storage.get_learning_outputs_root(base) / item["id"]
    summary_path = output_dir / "summary.md"
    insights_path = output_dir / "insights.md"
    queue_path = storage.get_learning_root(base) / "queue.json"
    prompt_path = base / "prompts" / "learning_pause_prompt.md"
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Files: metadata={metadata_path}, state={state_path}, queue={queue_path}, summary={summary_path}, insights={insights_path}\n\n"
        "## Instructions\n\n"
        "1. Use the current conversation as source of truth.\n"
        "2. Update state, metadata, queue, summary, and insights with net-new learning.\n"
        "3. Mark paused unless complete; do not generate qa.md unless asked.\n"
        "4. Confirm with saved next_action.\n"
    )


def write_pause_prompt(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    prompt_path = _learning_prompt_path(doc_id, "pause", base)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_pause_prompt(doc_id, base), encoding="utf-8")
    return prompt_path


def build_consolidate_prompt(doc_id: str, root: Path | None = None) -> str:
    base = root or storage.get_repo_root()
    item = storage.read_content_item_by_id(doc_id, base)
    if not storage.learning_state_exists(doc_id, base):
        raise ValueError(f"consolidate prompt requires an existing learning state: {doc_id}")
    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    state_path = storage.get_learning_states_root(base) / item["id"] / "state.json"
    output_dir = storage.get_learning_outputs_root(base) / item["id"]
    outline_path = output_dir / "outline.md"
    summary_path = output_dir / "summary.md"
    insights_path = output_dir / "insights.md"
    obsidian_index_path = storage.get_consolidation_indexes_root(base) / consolidation.OBSIDIAN_INDEX_FILENAME
    if not obsidian_index_path.exists():
        consolidation.build_obsidian_index(base)
    plan_path = consolidation.write_consolidation_plan(doc_id, base)
    draft_path = consolidation.draft_path_for_doc(doc_id, base)
    plan = consolidation.build_consolidation_plan(doc_id, base)
    prompt_path = base / "prompts" / "consolidate_prompt.md"
    state = storage.read_learning_state(doc_id, base)
    if not state["ready_to_consolidate"]:
        state["ready_to_consolidate"] = True
        storage.write_learning_state(state, base)

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    candidate_notes = plan["candidate_notes"][:3]
    candidate_note_lines = "\n".join(
        f"- {candidate['path']}: {candidate['reason']}"
        for candidate in candidate_notes
    ) or "- none"
    remaining_candidate_count = max(len(plan["candidate_notes"]) - len(candidate_notes), 0)
    if remaining_candidate_count:
        candidate_note_lines += f"\n- ... and {remaining_candidate_count} more"

    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Files: metadata={metadata_path}, state={state_path}, outline={outline_path}, summary={summary_path}, insights={insights_path}\n"
        f"- Index: {obsidian_index_path}\n"
        f"- Plan: {plan_path}\n"
        f"- Draft: {draft_path}\n"
        f"- Planned action: {plan['action']}\n"
        f"- Focus scope: {plan['focus_scope']}\n"
        f"- Candidate notes:\n{candidate_note_lines}\n\n"
        "## Instructions\n\n"
        "1. Read state, outputs, index, and only relevant candidate notes.\n"
        f"2. Refine {plan_path} if needed, write {draft_path}, update next_action, and confirm.\n"
    )


def write_consolidate_prompt(doc_id: str, root: Path | None = None) -> Path:
    base = root or storage.get_repo_root()
    prompt_path = _learning_prompt_path(doc_id, "consolidate", base)
    prompt_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_path.write_text(build_consolidate_prompt(doc_id, base), encoding="utf-8")
    return prompt_path


def _triage_budget_instruction(content_type: str, size_metrics: dict[str, int]) -> str:
    if content_type == "book":
        return "Prefer table of contents, preface, chapter headings, and a few sample pages. Avoid full-book reading."
    if content_type == "github":
        return "Prefer README, repository structure, and key entry files. Avoid repository-wide code reading."
    if content_type == "paper":
        return "Prefer title, abstract, introduction, headings, and conclusion. Sample extra paragraphs only when needed."
    if size_metrics["estimated_tokens"] <= 2500:
        return "This looks short enough for full reading if needed."
    return "Prefer headings and representative sections first. Avoid full-document reading unless the material is obviously short."


def _learning_prompt_path(doc_id: str, kind: str, root: Path) -> Path:
    return storage.get_learning_prompts_root(root) / f"{doc_id}__{kind}.md"
