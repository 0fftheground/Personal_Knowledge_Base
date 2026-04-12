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

1. Configure local paths with `python pkls config ...`
2. Or open the desktop controller with `python pkls gui`
   It lets you add files by drag-and-drop or file picker, generate triage and learning prompts, and review status in one place
   If you want drag-and-drop support, install the optional `tkinterdnd2` package first
3. Add content with `python pkls add ...`
   The CLI now auto-detects URL-list input, derives titles when omitted, defaults all ingest to candidate, supports explicit `--accept`, and skips duplicate imports
4. Use `python pkls triage list` to review candidate material
5. Use `python pkls learn queue` or `python pkls learn list` to inspect learning progress
6. Use `python pkls triage prompt ...` or `python pkls learn next`
   / `python pkls learn --id ...` to generate agent prompts
   Triage prompts are bounded and decision-oriented. Learning is user-controlled: initialize a document, explore one or more focus sessions with your AI agent, then pause or consolidate intentionally. Prompt files are saved under the workspace and can be resumed later
7. Let the AI agent update cards, state, and outputs
8. Publish readable outputs to Obsidian

Primary usage guide:

* `docs/how_to_use.md`

---

## Docs

Recommended reading order:

* `docs/how_to_use.md` - end-to-end operating guide
* `docs/agent_workflow.md` - agent-assisted triage and learning flow
* `docs/cli_spec.md` - CLI command reference
* `docs/prd.md` - product intent
* `docs/architecture.md` - storage and workflow layout
* `docs/schema.md` - JSON structures
* `docs/learning_strategy.md` - learning-stage design

Document addresses:

* `.pkls.local.example.json`
* `docs/how_to_use.md`
* `docs/agent_workflow.md`
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
* bounded agent-assisted triage
* queue-synced agent-assisted learning initialization
* user-controlled focus learning workflow
* Obsidian publish path configuration

## Local Config

Use:

* `.pkls.local.example.json` as the git-tracked example
* `.pkls.local.json` as the real local machine config

`.pkls.local.json` is intentionally ignored by git because it contains
machine-specific paths and user-specific workspace locations.
