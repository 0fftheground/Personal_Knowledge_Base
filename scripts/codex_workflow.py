"""Prompt builders for Codex-assisted triage and learning workflows."""

from __future__ import annotations

from pathlib import Path

from scripts import storage


def build_triage_prompt(doc_id: str, root: Path | None = None) -> str:
    base = root or storage.get_repo_root()
    workspace_root = storage.get_workspace_root(base)
    item = storage.read_content_item_by_id(doc_id, base)
    if item["source_type"] != "auto":
        raise ValueError(f"triage prompt only applies to auto items: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    card_path = storage.get_triage_cards_root(base) / f"{item['id']}.md"
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
        "## Concrete Instructions\n\n"
        f"1. Read {metadata_path} and {raw_path}.\n"
        "2. Compare the item against the user's learning goals.\n"
        "3. Update metadata.json so ai_recommendation is correct.\n"
        "4. Keep status as candidate and do not change the queue.\n"
        f"5. Write or update {card_path} with summary, key points, relevance, recommendation, and reason.\n"
        "6. Return a short confirmation after the file edits are complete.\n"
    )


def build_learning_prompt(
    doc_id: str,
    mode: str,
    focus: str | None = None,
    root: Path | None = None,
) -> str:
    base = root or storage.get_repo_root()
    workspace_root = storage.get_workspace_root(base)
    item = storage.read_content_item_by_id(doc_id, base)
    if item["status"] not in {"accepted", "learning", "done", "archived"}:
        raise ValueError(f"learning prompt requires an accepted or learning item: {doc_id}")

    metadata_path = storage.get_content_item_path(item["source_type"], item["id"], base)
    raw_path = storage.resolve_raw_path(item, base)
    state_path = storage.get_learning_states_root(base) / item["id"] / "state.json"
    output_dir = storage.get_learning_outputs_root(base) / item["id"]
    outline_path = output_dir / "outline.md"
    summary_path = output_dir / "summary.md"
    insights_path = output_dir / "insights.md"
    qa_path = output_dir / "qa.md"
    prompt_path = base / "prompts" / "learning_prompt.md"

    state_exists = state_path.exists()
    focus_line = focus if focus else "None provided. Default to the next most useful learning step."

    if mode not in {"outline", "deep_dive"}:
        raise ValueError(f"mode must be 'outline' or 'deep_dive', got {mode!r}")

    if mode == "outline":
        instructions = (
            "## Concrete Instructions\n\n"
            f"1. Read {metadata_path} and {raw_path}.\n"
            "2. If state.json does not exist, create it using docs/schema.md.\n"
            "3. Generate a document-level framework before any deep dive.\n"
            "4. Update state.json with outline_generated=true, document_outline, core_summary, and a next_action that asks for a focus area.\n"
            f"5. Write {outline_path}.\n"
            "6. Do not process the full document chunk by chunk yet.\n"
            "7. Return a short confirmation after the file edits are complete.\n"
        )
    else:
        instructions = (
            "## Concrete Instructions\n\n"
            f"1. Read {metadata_path}, {raw_path}, and {state_path if state_exists else 'the state schema from docs/schema.md'}.\n"
            f"2. Use {outline_path} if it exists.\n"
            f"3. User focus request: {focus_line}\n"
            "4. Process exactly one coherent learning unit.\n"
            "5. Update state.json incrementally: progress, current_chunk, key_points, questions, next_action, status.\n"
            f"6. Update {summary_path}, {insights_path}, and {qa_path}.\n"
            "7. Keep the workflow resumable. Do not reprocess everything.\n"
            "8. Return a short confirmation after the file edits are complete.\n"
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
        f"- Output directory: {output_dir}\n"
        f"- Outline file: {outline_path}\n"
        f"- Summary file: {summary_path}\n"
        f"- Insights file: {insights_path}\n"
        f"- QA file: {qa_path}\n\n"
        f"{instructions}"
    )
