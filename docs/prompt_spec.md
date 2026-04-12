# Prompt Spec (MVP)

## Prompt Files

Current prompt files:

* prompts/triage_prompt.md
* prompts/learning_prompt.md
* prompts/learning_pause_prompt.md
* prompts/consolidate_prompt.md
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

The AI agent should:

* read record metadata + bounded source context
* optionally verify time-sensitive claims from official sources
* update metadata.json
* evaluate truthfulness, reliability, and learning value
* write `<workspace_root>/triage/cards/<id>.md` with summary, key points, recommendation, and reason
* publish the triage card into the Obsidian notes path when the card is complete

Triage prompt rule:

* do not turn triage into full-document learning
* keep the item as `candidate`
* keep cards compact by default: 1-sentence summary, 2-3 short key points, exact recommendation, and 1-sentence reason

---

### Learning Start Or Resume Prompt

Used in:

* pkls learn --id <content_id>
* pkls learn --id <content_id> --focus "..."
* pkls learn next [--focus "..."]

Input:

* metadata
* queue.json
* current learning state
* resolved raw content
* optional user focus request

The AI agent should support two internal behaviors:

* initialize:
  * generate a document-level outline
  * write core summary
  * decide `single_pass` or `chunked`
  * initialize or update state.json
  * write `<workspace_root>/learning/outputs/<id>/outline.md`
* focus session:
  * use current state + outline
  * interpret `focus` as user intent, not raw chunk text
  * process one focused learning unit
  * keep the session grounded so it can later be paused or consolidated cleanly

Default rule:

* do not generate `qa.md` during initial setup
* do not treat pause or consolidate as part of this prompt unless the execution context explicitly says so

Expected persisted updates:

* initialize should write `state.json` and `outline.md`, and may write `chunk_manifest.json` for large materials
* focus sessions remain user-controlled and should update persistent files only when the generated execution context explicitly requests that

---

### Learning Pause Prompt

Used in:

* pkls learn pause --id <content_id>

Purpose:

* save the current interactive learning session
* update `state.json`
* update `summary.md`
* update `insights.md`
* write a clear `next_action`
* preserve resumability without relying on chat history

---

### Consolidation Prompt

Used in:

* pkls learn consolidate --id <content_id>

Purpose:

* adapt learned material into the user's Obsidian knowledge system
* read the Obsidian structure index
* read a small candidate set of related notes
* write a consolidation plan
* write a knowledge-note draft

Consolidation prompt rule:

* use this only after enough learning has accumulated or when the execution context explicitly marks the item ready to consolidate

---

### Question Refine Prompt

Reserved for later reflection/review workflows.

Purpose:

* improve generated questions
* remove weak questions
* support delayed `qa.md` generation after knowledge has accumulated

Question refine rule:

* this is not part of the initial `learn -> pause -> consolidate` flow

---

## Constraints

* prompts are for AI-agent execution, not raw JSON API calls
* the AI agent must update files directly
* no hidden memory assumptions
* learning remains state-driven from raw + state
* focus sessions are user-controlled
* consolidation should use note structure and selected notes, not full-vault rereads
* `qa.md` belongs to later reflection/review, not initialization
