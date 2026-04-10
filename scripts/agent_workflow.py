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
    workspace_root = storage.get_workspace_root(base)
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] != "candidate":
        raise ValueError(f"triage prompt requires a candidate item: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
    publish_path = local_config.get_notes_publish_root(base) / publish.PUBLISH_ROOT_DIR / "triage" / f"{item['id']}.md"
    prompt_path = base / "prompts" / "triage_prompt.md"
    size_metrics = learning.collect_material_profile(doc_id, base)
    reading_budget = _triage_budget_instruction(item["content_type"], size_metrics)

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Repository root: {base}\n"
        f"- Workspace root: {workspace_root}\n"
        f"- Prompt file: {prompt_path}\n"
        f"- Metadata file: {metadata_path}\n"
        f"- Raw content file: {raw_path}\n"
        f"- Target triage card: {card_path}\n"
        f"- Auto-publish target: {publish_path}\n"
        f"- Size metrics: {size_metrics}\n\n"
        "## Concrete Instructions\n\n"
        f"1. Read {metadata_path} and inspect {raw_path} using bounded triage only.\n"
        f"2. Triage reading budget: {reading_budget}\n"
        "3. Judge the content for truthfulness, source reliability, and learning value.\n"
        "4. Update metadata.json so ai_recommendation is correct.\n"
        "5. Keep status as candidate and do not change the queue.\n"
        f"6. Write or update {card_path} with summary, key points, recommendation, and reason.\n"
        f"7. If the triage card is complete, copy it to {publish_path}.\n"
        "8. Return a short confirmation after the file edits are complete.\n"
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
        size_metrics = learning.collect_material_profile(item["id"], base)
        item_sections.append(
            f"### Item {index}: {item['id']}\n\n"
            f"- Title: {item['title']}\n"
            f"- Source type: {item['source_type']}\n"
            f"- Priority: {item['priority']}\n"
            f"- Metadata file: {metadata_path}\n"
            f"- Raw content file: {raw_path}\n"
            f"- Target triage card: {card_path}\n"
            f"- Auto-publish target: {publish_path}\n"
            f"- Size metrics: {size_metrics}\n"
            f"- Bounded reading rule: {_triage_budget_instruction(item['content_type'], size_metrics)}\n"
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
        "2. For each item: read metadata and bounded source context, update ai_recommendation, keep status as candidate, write the triage card, and publish it to the listed Obsidian path when the card is complete.\n"
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
    prompt_path = base / "prompts" / "learning_prompt.md"
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

    prompt = prompt_path.read_text(encoding="utf-8").strip()
    focus_line = focus if focus else (state["current_focus"] if state is not None and state["current_focus"] else "No explicit focus yet.")
    execution_context = (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Repository root: {base}\n"
        f"- Workspace root: {workspace_root}\n"
        f"- Prompt file: {prompt_path}\n"
        f"- Internal mode: {mode}\n"
        f"- Suggested processing mode: {suggested_mode}\n"
        f"- Size metrics: {size_metrics}\n"
        f"- Metadata file: {metadata_path}\n"
        f"- Raw content file: {raw_path}\n"
        f"- State file: {state_path}\n"
        f"- Queue file: {queue_path}\n"
        f"- Queue entry: {queue_entry}\n"
        f"- Output directory: {output_dir}\n"
        f"- Outline file: {outline_path}\n"
        f"- Summary file: {summary_path}\n"
        f"- Insights file: {insights_path}\n"
        f"- Chunk manifest file: {chunk_manifest_path}\n"
        f"- Current focus request: {focus_line}\n\n"
    )

    if mode == "outline":
        return execution_context + (
            "## Concrete Instructions\n\n"
            f"1. Read {metadata_path} and {raw_path}.\n"
            f"2. Read and update {queue_path}.\n"
            "3. If state.json does not exist, create it using docs/schema.md.\n"
            f"4. Decide whether this document should use `single_pass` or `chunked` processing. Suggested mode: {suggested_mode}.\n"
            "5. Generate a document framework and a core summary.\n"
            f"6. Update {state_path} with initialized=true, outline_generated=true, processing_mode, size_metrics, document_outline, core_summary, and a strong next_action.\n"
            "7. Set metadata status to `learning` unless the document is already complete.\n"
            "8. Update queue.json so this item is present with status=doing.\n"
            f"9. Write {outline_path}.\n"
            f"10. If processing_mode is `chunked`, also write {chunk_manifest_path} with structural chunk metadata.\n"
            "11. Do not generate qa.md during initialization.\n"
            "12. Return a short confirmation after the file edits are complete.\n"
        )

    return execution_context + (
        "## Concrete Instructions\n\n"
        f"1. Read {metadata_path}, {raw_path}, and {state_path}.\n"
        f"2. Use {outline_path} as the document framework.\n"
        "3. Treat this prompt as the entry point for a user-controlled focus session.\n"
        "4. Interpret the focus as user intent, not as raw chunk text.\n"
        "5. Load only the minimum relevant source context for the requested focus. For large materials, prefer chunk metadata and local chunk files before wider rereads.\n"
        "6. Guide the user through the topic interactively with the AI agent.\n"
        "7. Keep explanations grounded in the local files and existing state.\n"
        "8. Do not auto-generate qa.md in this step.\n"
        "9. When the user later asks to pause or consolidate, use the dedicated prompt so the session can be saved or integrated intentionally.\n"
        "10. Return a short confirmation that the focus session context is ready.\n"
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
        f"- Repository root: {base}\n"
        f"- Metadata file: {metadata_path}\n"
        f"- State file: {state_path}\n"
        f"- Queue file: {queue_path}\n"
        f"- Summary file: {summary_path}\n"
        f"- Insights file: {insights_path}\n\n"
        "## Concrete Instructions\n\n"
        "1. Use the current learning conversation as the source of truth for what was covered in this session.\n"
        "2. Persist the session into repo state and output files.\n"
        "3. Update state.json with current_focus, focus_history, interaction_count, session_notes, key_points, insights, next_action, and status=`paused` unless the work is clearly complete.\n"
        "4. Update metadata.json so the item status matches the saved learning state.\n"
        "5. Update queue.json so this item becomes `paused` unless the learning is done.\n"
        "6. Update summary.md and insights.md with the net-new learning from this session.\n"
        "7. Do not generate qa.md unless the user explicitly asked for review questions.\n"
        "8. Return a short confirmation with the saved next_action.\n"
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
    candidate_note_lines = "\n".join(
        f"- {candidate['path']}: {candidate['reason']}"
        for candidate in plan["candidate_notes"]
    ) or "- none"

    return (
        f"{prompt}\n\n"
        "## Execution Context\n\n"
        f"- Repository root: {base}\n"
        f"- Metadata file: {metadata_path}\n"
        f"- State file: {state_path}\n"
        f"- Outline file: {outline_path}\n"
        f"- Summary file: {summary_path}\n"
        f"- Insights file: {insights_path}\n"
        f"- Obsidian index file: {obsidian_index_path}\n"
        f"- Consolidation plan file: {plan_path}\n"
        f"- Draft target file: {draft_path}\n"
        f"- Planned action: {plan['action']}\n"
        f"- Focus scope: {plan['focus_scope']}\n"
        f"- Candidate notes:\n{candidate_note_lines}\n\n"
        "## Concrete Instructions\n\n"
        "1. Read the current learning state and outputs.\n"
        "2. Read the Obsidian structure index.\n"
        "3. Read only the most relevant candidate notes listed in the consolidation plan.\n"
        "4. Decide how the learned material should fit into the existing knowledge system.\n"
        f"5. Update {plan_path} if the consolidation action or candidate notes need refinement.\n"
        f"6. Write {draft_path} as an Obsidian-ready knowledge draft adapted to the user's note structure.\n"
        "7. Preserve source grounding, but do not merely restate the reading summary.\n"
        "8. Update state.json so next_action points to draft review or final publishing.\n"
        "9. Return a short confirmation with the draft path and the chosen consolidation action.\n"
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
