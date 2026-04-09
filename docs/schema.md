# Data Schema (MVP)

## Content Item

{
"id": "string",
"title": "string",
"source_type": "auto | manual",
"content_type": "paper | blog | github | book",
"ingest_date": "YYYY-MM-DD",
"status": "candidate | accepted | rejected | learning | done | archived",
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
"progress": 0.0,
"current_chunk": 0,
"chunks_total": 0,
"key_points": [],
"questions": [],
"outline_generated": false,
"document_outline": [],
"core_summary": "string",
"next_action": "string",
"status": "learning | done"
}

---

## Queue

[
{
"doc_id": "string",
"priority": 0.0,
"status": "todo | doing | done"
}
]

---

## Local Config

{
"device_name": "string | null",
"raw_full_root": "string | null",
"raw_sync_root": "string | null",
"workspace_root": "string | null",
"obsidian_vault_path": "string | null"
}
