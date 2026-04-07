# Personal Knowledge Learning System

## Overview

This project is a local-first AI-assisted learning system.

It supports:

* automatic content ingestion
* AI triage (summarization + recommendation)
* user-driven learning decisions
* resumable learning across devices
* structured knowledge output

---

## Architecture

See:

* docs/architecture.md

Main structure:

* raw/
* triage/
* learning/
* notes/

---

## Core Idea

Learning is:

* state-driven
* incremental
* resumable

NOT based on chat history.

---

## Pipelines

### Auto

raw/auto → triage → candidate → user decision → learning

### Manual

raw/manual → learning

---

## Running (MVP)

Steps:

1. Add content to raw/
2. Run triage
3. Accept selected items
4. Run learning

---

## Docs

* docs/prd.md
* docs/schema.md
* docs/learning_strategy.md
* docs/task_plan.md

---

## Current Status

MVP in development:

* storage layer
* triage
* learning

---

## Future

* SQLite state
* background jobs
* API layer


## Developing prompts

Read the following files first:

- AGENTS.md
- docs/prd.md
- docs/architecture.md
- docs/schema.md
- docs/task_plan.md
- docs/acceptance_criteria.md
- tasks/task_01_storage.md

Task:
Implement task_01_storage.md exactly.

Requirements:
- follow docs/schema.md strictly
- follow docs/architecture.md strictly
- keep implementation minimal and modular
- use filesystem + JSON only (no database)

Process:
1. First output a concise implementation plan
2. Then implement step by step
3. After implementation, perform the Audit Step defined in task_01_storage.md
4. Fix any issues found in audit before finishing

Constraints:
- Do NOT add UI
- Do NOT add cloud logic
- Do NOT add vector database or RAG
- Do NOT modify unrelated modules

Output:
- working code
- example data
- brief explanation of structure