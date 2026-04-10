# Data Schema (MVP)

## Content Item

{
"id": "string",
"title": "string",
"source_type": "auto | manual",
"content_type": "paper | blog | github | book",
"ingest_date": "YYYY-MM-DD",
"status": "candidate | accepted | rejected | learning | paused | done | archived",
"priority": 0.0,
"ai_recommendation": "skip | skim | learn",
"manual_decision": "accept | reject | later | null",
"storage_tier": "full | sync_only",
"full_raw_relpath": "string | null",
"sync_raw_relpath": "string | null",
"source_filename": "string",
"source_device": "string | null",
"content_hash": "string | null",
"sync_status": "none | active | inbox"
}

---

## Triage Card

Decision-oriented summary only.

{
"id": "string",
"summary": "string",
"key_points": ["..."],
"recommendation": "skip | skim | learn",
"reason": "string"
}

---

## Learning State

{
"doc_id": "string",
"initialized": false,
"processing_mode": "single_pass | chunked",
"size_metrics": {
  "pages": 0,
  "chars": 0,
  "estimated_tokens": 0,
  "heading_count": 0
},
"current_focus": "string | null",
"focus_history": ["..."],
"interaction_count": 0,
"progress": 0.0,
"current_chunk": 0,
"chunks_total": 0,
"chunk_manifest_path": "string | null",
"key_points": [],
"insights": [],
"session_notes": [],
"questions": [],
"outline_generated": false,
"document_outline": [],
"core_summary": "string",
"next_action": "string",
"ready_to_consolidate": false,
"status": "learning | paused | done"
}

Notes:

* `processing_mode = single_pass` means the item can usually be handled without persistent chunk manifests
* `processing_mode = chunked` means the system should rely on chunk metadata and local chunk files for large materials
* `current_focus` is the active user-controlled topic for the latest learning session
* `questions` should be generated later, after enough knowledge has been accumulated, not during initial learning setup
* `ready_to_consolidate` may be set when the user explicitly moves from learning into consolidation

---

## Chunk Manifest Entry

Used only when `processing_mode = chunked`.

{
"chunk_id": "string",
"title": "string",
"level": 0,
"section_path": ["..."],
"page_start": 0,
"page_end": 0,
"summary": "string",
"keywords": ["..."],
"text_relpath": "string"
}

---

## Learning Queue

[
{
"doc_id": "string",
"priority": 0.0,
"status": "todo | doing | paused | done"
}
]

---

## Consolidation Plan

{
"doc_id": "string",
"focus_scope": ["..."],
"candidate_notes": [
  {
    "path": "string",
    "reason": "string"
  }
],
"action": "create_new_note | update_existing_note | create_and_link",
"draft_relpath": "string",
"next_action": "string"
}

---

## Obsidian Index Entry

{
"path": "string",
"title": "string",
"tags": ["..."],
"wikilinks": ["..."],
"modified_time": "YYYY-MM-DDTHH:MM:SS",
"is_index_note": false
}

---

## Local Config

{
"device_name": "string | null",
"raw_full_root": "string | null",
"raw_sync_root": "string | null",
"workspace_root": "string | null",
"obsidian_vault_path": "string | null"
}
