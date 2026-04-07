# AGENTS.md

## Purpose

This repository implements a personal knowledge learning system.

Codex must follow project constraints strictly.

---

## Read First (MANDATORY)

Before any task, read:

* docs/prd.md
* docs/architecture.md
* docs/schema.md
* docs/learning_strategy.md
* docs/task_plan.md

---

## Development Rules

### Scope Control

DO NOT add:

* Web UI
* Cloud deployment
* Vector database / RAG
* Multi-user support
* External frameworks unless required

This is a local MVP system.

---

### Execution Style

For each task:

1. First output a plan
2. Wait or proceed if trivial
3. Then implement
4. Keep changes minimal and focused

---

### Code Principles

* Keep modules small and clean
* Separate:

  * raw layer
  * triage layer
  * learning layer
* No hidden global state
* All logic must be reproducible from:
  raw + state

---

### State Handling

* Always update state.json incrementally
* Never recompute full document unless necessary
* Learning must be resumable

---

### File Rules

* Raw content stays unchanged
* Outputs go to:
  learning/outputs/
* Triage cards go to:
  triage/cards/

---

### Logging

* Print meaningful logs for:

  * processing steps
  * errors
* Do not fail silently

---

### When Unsure

* Ask for clarification
* Or follow docs strictly

Do NOT invent new architecture

---

## Deliverables for Each Task

* Working code
* Example input/output
* Short README or comments
