# Personal Knowledge Learning System

## Overview

This project is a local-first knowledge workflow for collecting material,
triaging it, learning it incrementally, and publishing readable outputs into
Obsidian.

The repository stores:

* scripts
* prompts
* docs

Raw files and user workspace data live outside the repository in configured
local directories.

---

## Storage Layers

### Full Raw Store

Long-term archive for original files.

### Active Sync Store

Cross-device active subset and inbox area.

### User Workspace Store

External user data directory.

### Obsidian Notes Layer

Mobile reading and long-term knowledge notes.

---

## Repository Structure

* `scripts/`
* `prompts/`
* `docs/`

---

## Running (MVP)

Before first use:

1. Copy `.pkls.local.example.json` to `.pkls.local.json`
2. Replace the example paths with real machine-local paths
3. Keep `.pkls.local.json` out of git

Then:

1. Configure local paths with `python -m scripts.pkls config ...`
2. Add content with `python -m scripts.pkls add ...`
3. Generate Codex prompts for triage or learning
4. Let Codex update cards, state, and outputs
5. Publish readable outputs to Obsidian

Primary usage guide:

* `docs/how_to_use.md`

---

## Docs

Recommended reading order:

* `docs/how_to_use.md` - end-to-end operating guide
* `docs/codex_workflow.md` - Codex-assisted triage and learning flow
* `docs/cli_spec.md` - CLI command reference
* `docs/prd.md` - product intent
* `docs/architecture.md` - storage and workflow layout
* `docs/schema.md` - JSON structures
* `docs/learning_strategy.md` - learning-stage design

Document addresses:

* `.pkls.local.example.json`
* `docs/how_to_use.md`
* `docs/codex_workflow.md`
* `docs/cli_spec.md`
* `docs/prd.md`
* `docs/architecture.md`
* `docs/schema.md`
* `docs/learning_strategy.md`

---

## Current Status

MVP in development:

* workspace-based state storage
* external raw full/sync stores
* Codex-assisted triage
* Codex-assisted learning
* Obsidian publish path configuration

## Local Config

Use:

* `.pkls.local.example.json` as the git-tracked example
* `.pkls.local.json` as the real local machine config

`.pkls.local.json` is intentionally ignored by git because it contains
machine-specific paths and user-specific workspace locations.
