# Task Plan (MVP)

## Phase 1: Storage Layer

### Goal

Implement external raw storage + workspace record storage

### Tasks

* create directory structure
* implement:

  * content record creation
  * raw file ingest into full/sync stores
  * queue read/write
  * state read/write

### Output

* working storage module
* sample data

### Non-goals

* no AI logic
* no triage
* no learning

---

## Phase 2: Bounded Triage Pipeline

### Goal

Process candidate records into decision cards without turning triage into full learning

### Tasks

* resolve raw content from external stores
* classify material type and size roughly
* read bounded source samples only
* generate:

  * summary
  * key points
  * recommendation
* write markdown cards

### Output

* triage/cards/*.md

### Non-goals

* no full-document learning
* no queue auto-advancement beyond accept/reject decisions

---

## Phase 3: Learn Initialize

### Goal

Create a document framework and choose the correct learning mode

### Tasks

* inspect extracted material size
* choose `single_pass` or `chunked`
* generate document outline and core summary
* initialize `state.json`
* create chunk manifests for large materials only

### Output

* resumable learning initialization
* `outline.md`
* initialized state

### Non-goals

* no long interactive session handling yet
* no consolidation into Obsidian notes yet

---

## Phase 4: Interactive Focus Learning

### Goal

Support user-controlled topic sessions on top of initialized learning state

### Tasks

* accept a user `focus`
* retrieve only the relevant local source context
* update:

  * `summary.md`
  * `insights.md`
  * `state.json`
* support pause/resume without hidden memory

### Output

* focused learning sessions
* resumable session state

### Non-goals

* no review-question generation by default

---

## Phase 5: Reflection And Review Questions

### Goal

Generate questions only after enough learning has accumulated

### Tasks

* define readiness signals for review
* generate understanding, connection, and application questions
* write `qa.md`

### Output

* delayed, higher-quality review questions

---

## Phase 6: Consolidation Layer

### Goal

Adapt learned material into the existing Obsidian knowledge system

### Tasks

* build an Obsidian structure index
* rank relevant existing notes
* create consolidation plans
* draft knowledge notes or note updates

### Output

* consolidation/plans/*
* consolidation/drafts/*

### Non-goals

* no full-vault reread on every consolidation run

---

## Phase 7: Queue System

### Goal

Control learning order without forcing automatic deep processing

### Tasks

* read/write queue.json
* pick next item
* support paused items
* update status based on state

---

## Phase 8: CLI Interface

### Goal

Expose the bounded triage + controlled learning workflow

### Commands

* add
* raw inbox-add / promote / sync
* triage
* learn
* status
* publish
* config

CLI additions:

* explicit pause prompt generation
* explicit consolidation prompt generation

---

## Phase 9: Stabilization

### Goal

Make system robust

### Tasks

* error handling
* logging
* edge cases
* consistency checks between state, queue, and outputs
