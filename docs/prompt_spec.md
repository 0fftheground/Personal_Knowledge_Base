# Prompt Spec (MVP)

## Prompt Files

* prompts/triage_prompt.md
* prompts/learning_prompt.md
* prompts/question_refine_prompt.md

---

## Usage

### Triage Prompt

Used in:

* pkls triage prompt --id <content_id>

Input:

* title
* content type
* record metadata
* resolved raw content path

Codex should:

* read record metadata + raw content
* optionally verify time-sensitive claims from official sources
* update metadata.json
* evaluate truthfulness, reliability, and learning value
* write `<workspace_root>/triage/cards/<id>.md` with summary, key points, recommendation, and reason
* publish the triage card into the Obsidian notes path when the card is complete

---

### Learning Prompt

Used in:

* pkls learn prompt --id <content_id> --mode outline
* pkls learn prompt --id <content_id> --mode deep_dive [--focus "..."]

Input:

* metadata
* queue.json
* current learning state
* resolved raw content
* optional user focus request

Codex should support two modes:

* outline:
  * generate a document-level outline
  * update metadata status to `learning`
  * update `queue.json` status to `doing`
  * write core summary
  * initialize or update state.json
  * write `<workspace_root>/learning/outputs/<id>/outline.md`
* deep_dive:
  * use current state + outline
  * process one chunk or one focused unit
  * update state.json incrementally
  * update metadata status to `learning` or `done`
  * update `queue.json` status to `doing` or `done`
  * update `<workspace_root>/learning/outputs/<id>/summary.md`
  * update `<workspace_root>/learning/outputs/<id>/insights.md`
  * update `<workspace_root>/learning/outputs/<id>/qa.md`

---

### Question Refine Prompt

Reserved for future workflow extensions.

Purpose:

* improve generated questions
* remove weak questions

---

## Constraints

* prompts are for Codex execution, not raw JSON API calls
* Codex must update files directly
* no hidden memory assumptions
* learning remains state-driven from raw + state
