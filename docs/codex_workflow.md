# Codex Workflow

## Purpose

This document explains how to use the system when triage and learning are
performed by Codex instead of a directly integrated LLM API.

The repository stores:

* scripts and prompts

Raw content and workspace data live outside the repo in configured local paths.

---

## Core Idea

Codex should always work from:

* record metadata in `<workspace_root>/records/`
* resolved raw content path from `full_raw_relpath` or `sync_raw_relpath`
* `state.json`
* existing output files

Do not rely on hidden chat memory as the source of truth.

---

## Local Setup

Configure machine-local paths first:

```bash
python -m scripts.pkls config set-device-name --name "pc-dev"
python -m scripts.pkls config set-raw-sync-root --path "F:\google drive\PKB\raw_sync_root"
python -m scripts.pkls config set-workspace-root --path "F:\google drive\PKB\workspace"
python -m scripts.pkls config set-obsidian-vault --path "D:\Obsidian\Vault"
python -m scripts.pkls config show
```

On the main archive machine you should also set:

```bash
python -m scripts.pkls config set-raw-full-root --path "/Volumes/pkls_raw_full"
```

These values are stored in `.pkls.local.json` and are not committed.

---

## Command Overview

Use these commands most often:

```bash
python -m scripts.pkls add manual --type <paper|blog|github|book> --path <file> --title "<title>"
python -m scripts.pkls add auto --type <paper|blog|github|book> --path <file> --title "<title>"
python -m scripts.pkls raw inbox-add auto --type <paper|blog|github|book> --path <file> --title "<title>"
python -m scripts.pkls raw promote --id <content_id>
python -m scripts.pkls raw sync --id <content_id>

python -m scripts.pkls triage list
python -m scripts.pkls triage prompt --id <content_id>
python -m scripts.pkls triage accept --id <content_id>
python -m scripts.pkls triage reject --id <content_id>
python -m scripts.pkls triage later --id <content_id>

python -m scripts.pkls learn queue
python -m scripts.pkls learn prompt --id <content_id> --mode outline
python -m scripts.pkls learn prompt --id <content_id> --mode deep_dive --focus "<focus>"

python -m scripts.pkls publish item --id <content_id>
python -m scripts.pkls status --id <content_id>
```

---

## Auto Content Workflow

### 1. Add content into the auto pipeline

```bash
python -m scripts.pkls add auto --type blog --path .\article.md --title "Interesting Article"
```

This will:

* copy the file into configured raw stores
* create `<workspace_root>/records/auto/<doc_id>/metadata.json`
* set `status = candidate`

If you are on a non-archive machine and only want to submit content into the
shared sync area, use:

```bash
python -m scripts.pkls raw inbox-add auto --type blog --path .\article.md --title "Interesting Article"
```

This writes the file into the sync inbox and records `sync_status = inbox`.

### 2. Find candidate items

```bash
python -m scripts.pkls triage list
```

### 3. Generate a prompt for Codex

```bash
python -m scripts.pkls triage prompt --id <content_id>
```

This prompt tells Codex:

* which project docs to read first
* which record metadata file to inspect
* which resolved raw content file to inspect
* which triage card to update

### 4. Give that prompt to Codex

Codex should update:

* `<workspace_root>/records/auto/<doc_id>/metadata.json`
* `<workspace_root>/triage/cards/<doc_id>.md`

### 5. Make the triage decision

```bash
python -m scripts.pkls triage accept --id <content_id>
python -m scripts.pkls triage reject --id <content_id>
python -m scripts.pkls triage later --id <content_id>
```

---

## Manual Content Workflow

### 1. Add content directly into learning

```bash
python -m scripts.pkls add manual --type blog --path .\notes.md --title "My Notes"
```

This will:

* copy the file into configured raw stores
* create `<workspace_root>/records/manual/<doc_id>/metadata.json`
* set `status = accepted`
* add the item to `<workspace_root>/learning/queue.json`

---

## Learning Workflow

Learning is split into two phases.

### Phase 1: Outline First

Run:

```bash
python -m scripts.pkls learn prompt --id <content_id> --mode outline
```

This tells Codex to:

* read the record metadata
* read the resolved raw content
* create or update `state.json`
* generate a document-level outline
* generate a short core summary
* write `<workspace_root>/learning/outputs/<doc_id>/outline.md`

### Phase 2: Deep Dive On Demand

Run:

```bash
python -m scripts.pkls learn prompt --id <content_id> --mode deep_dive --focus "state-driven resumability"
```

This tells Codex to:

* read metadata, raw content, and current state
* use the outline as context
* process one coherent learning unit
* update state incrementally
* update the cumulative output files

---

## Publish To Obsidian

After triage or learning output is ready:

```bash
python -m scripts.pkls publish item --id <content_id>
```

Published files go under:

* `<vault>/pkls/triage/`
* `<vault>/pkls/learning/outlines/`
* `<vault>/pkls/learning/summaries/`
* `<vault>/pkls/learning/insights/`
* `<vault>/pkls/learning/qa/`

This is the recommended mobile reading layer.

---

## Files To Check

When you want to inspect progress, look here:

* `<workspace_root>/records/auto/<doc_id>/metadata.json`
* `<workspace_root>/records/manual/<doc_id>/metadata.json`
* `<workspace_root>/triage/cards/<doc_id>.md`
* `<workspace_root>/learning/states/<doc_id>/state.json`
* `<workspace_root>/learning/outputs/<doc_id>/outline.md`
* `<workspace_root>/learning/outputs/<doc_id>/summary.md`
* `<workspace_root>/learning/outputs/<doc_id>/insights.md`
* `<workspace_root>/learning/outputs/<doc_id>/qa.md`

---

## Notes

Current limitations:

* the full raw archive and sync store are filesystem locations, not database-backed
* sync/inbox orchestration is still manual
* Codex is the analysis engine, not a background service
