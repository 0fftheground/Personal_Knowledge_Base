# Task Plan (MVP)

## Phase 1: Storage Layer

### Goal

Implement basic filesystem + JSON storage

### Tasks

* create directory structure
* implement:

  * content item creation
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

Process raw/auto into candidate cards

### Tasks

* read raw/auto
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

Implement chunk-based learning

### Tasks

* chunk content
* process one chunk
* update state
* generate:

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

* add_manual
* run_triage
* start_learning
* resume_learning

---

## Phase 6: Stabilization

### Goal

Make system robust

### Tasks

* error handling
* logging
* edge cases
