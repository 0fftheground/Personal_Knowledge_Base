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

## Phase 2: Triage Pipeline

### Goal

Process auto records into candidate cards

### Tasks

* resolve raw content from external stores
* generate:

  * summary
  * key points
  * recommendation
* write markdown cards

### Output

* triage/cards/*.md

### Non-goals

* no auto queue insertion
* no learning

---

## Phase 3: Learning Pipeline

### Goal

Implement outline-first, chunk-based learning

### Tasks

* chunk content
* generate document outline first
* process one chunk
* update state
* generate:

  * outline.md
  * summary.md
  * insights.md
  * qa.md

### Output

* resumable learning system

### Non-goals

* no full document processing
* no chat history usage

---

## Phase 4: Queue System

### Goal

Control learning order

### Tasks

* read/write queue.json
* pick next item
* update status

---

## Phase 5: CLI Interface

### Goal

Basic commands

### Commands

* add
* raw inbox-add / promote / sync
* triage
* learn
* status
* publish
* config

---

## Phase 6: Stabilization

### Goal

Make system robust

### Tasks

* error handling
* logging
* edge cases
