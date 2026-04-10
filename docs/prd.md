# Personal Knowledge Learning System (MVP)

## Goal

Build a personal system that:

* Collects information (auto + manual)
* Uses AI to triage and summarize
* Allows user to decide what to learn
* Supports resumable learning across devices
* Outputs structured knowledge for Obsidian

---

## Core Concepts

### Two Pipelines

#### 1. Auto Pipeline

* Input: RSS / GitHub / web content
* Flow:
  external raw store → record → AI triage → candidate → user decision → learning

#### 2. Manual Pipeline

* Input: user-added content (PDF, repo, article)
* Flow:
  external raw store → record → candidate → user decision → learning
  or external raw store → record → accepted → learning (only with explicit ingest override)

---

## State Machine

Each content item must have one of:

* candidate
* accepted
* rejected
* learning
* done
* archived

Rules:

* all content starts as candidate by default
* content starts as accepted only when the user explicitly requests acceptance during ingest

---

## User Flow

### Mobile

* View triage cards
* Decide:

  * accept
  * reject
  * later
* Read summaries

### PC / Mac

* Run learning process
* Continue from previous state
* Generate:

  * document framework
  * focused learning summaries
  * insights
  * later review questions
  * knowledge drafts for Obsidian

---

## Non-Goals (MVP)

* No web UI
* No vector database
* No cloud deployment
* No multi-user support

---

## Output

System should produce:

* triage cards (markdown)
* learning outputs:

  * outline.md
  * summary.md
  * insights.md
  * qa.md (later reflection/review stage)
  * consolidation drafts
* state files
* queue

---

## Key Principle

Learning must be:

* resumable
* state-driven (NOT chat history driven)
