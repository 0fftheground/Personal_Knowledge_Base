# Data Schema (MVP)

## Content Item

{
"id": "string",
"title": "string",
"source_type": "auto | manual",
"content_type": "paper | blog | github | book",
"path": "string",
"ingest_date": "YYYY-MM-DD",
"status": "candidate | accepted | rejected | learning | done",
"priority": 0.0,
"ai_recommendation": "skip | skim | learn",
"manual_decision": null
}

---

## Triage Card

{
"id": "string",
"summary": "string",
"key_points": ["..."],
"relevance": "string",
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
