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
  external raw store → record → directly into learning

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

* auto → starts as candidate
* manual → starts as accepted

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

  * summary
  * insights
  * questions

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
  * qa.md
* state files
* queue

---

## Key Principle

Learning must be:

* resumable
* state-driven (NOT chat history driven)
