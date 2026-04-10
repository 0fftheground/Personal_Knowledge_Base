# Agent Workflow

## Purpose

This document explains how to use the system when triage, learning, and later knowledge consolidation are performed by an AI agent instead of a directly integrated LLM API.

The repository stores:

* scripts and prompts

Raw content and workspace data live outside the repo in configured local paths.

---

## Core Idea

The AI agent should always work from:

* record metadata in `<workspace_root>/records/`
* resolved raw content path from `full_raw_relpath` or `sync_raw_relpath`
* `state.json`
* existing output files
* the Obsidian structure index and a small candidate set of related notes during consolidation

Do not rely on hidden chat memory as the source of truth.

---

## Local Setup

Configure machine-local paths first:

```bash
python pkls config set-device-name --name "pc-dev"
python pkls config set-raw-sync-root --path "F:\google drive\PKB\raw_sync_root"
python pkls config set-workspace-root --path "F:\google drive\PKB\workspace"
python pkls config set-obsidian-vault --path "D:\Obsidian\Vault"
python pkls config show
```

On the main archive machine you should also set:

```bash
python pkls config set-raw-full-root --path "/Volumes/pkls_raw_full"
```

These values are stored in `.pkls.local.json` and are not committed.

---

## Command Overview

Use these commands most often:

```bash
python pkls add manual --type <paper|blog|github|book> --path <file> [--title "<title>"] [--accept]
python pkls add auto --type <paper|blog|github|book> --path <file> [--title "<title>"] [--accept]
python pkls raw inbox-add auto --type <paper|blog|github|book> --path <file> [--title "<title>"] [--accept]
python pkls raw promote --id <content_id>
python pkls raw sync --id <content_id>

python pkls triage list
python pkls triage prompt --id <content_id>
python pkls triage prompt-batch --limit 5
python pkls triage accept --id <content_id>
python pkls triage reject --id <content_id>
python pkls triage later --id <content_id>

python pkls learn queue
python pkls learn next
python pkls learn --id <content_id>
python pkls learn --id <content_id> --focus "<focus>"

python pkls publish item --id <content_id>
python pkls publish consolidate --id <content_id>
python pkls status --id <content_id>
```

Additional commands:

```bash
python pkls learn pause --id <content_id>
python pkls learn consolidate --id <content_id>
```

---

## Auto Content Workflow

### 1. Add content into the auto pipeline

```bash
python pkls add auto --type blog --path .\article.md
```

If the file content looks like a URL list instead of article text, the CLI detects that automatically:

```bash
python pkls add auto --type blog --path .\url_list.txt
```

This will:

* copy the file into configured raw stores
* create `<workspace_root>/records/auto/<doc_id>/metadata.json`
* derive the title from content or filename when not provided
* set `status = candidate` by default
* set `status = accepted` only when `--accept` is provided
* when the input is detected as a URL list, fetch each URL and create one item per webpage

If you are on a non-archive machine and only want to submit content into the shared sync area, use:

```bash
python pkls raw inbox-add auto --type blog --path .\article.md
```

This writes the file into the sync inbox and records `sync_status = inbox`.

### 2. Find candidate items

```bash
python pkls triage list
```

### 3. Generate a triage prompt for the AI agent

```bash
python pkls triage prompt --id <content_id>
```

This prompt tells the AI agent:

* which project docs to read first
* which record metadata file to inspect
* which resolved raw content file to inspect
* which triage card to update
* which Obsidian triage note path to publish when the card is complete
* to keep triage bounded instead of turning it into full learning

The CLI saves this prompt to:

* `<workspace_root>/triage/prompts/<content_id>.md`

For a small sequential batch of candidate items without triage cards, use:

```bash
python pkls triage prompt-batch --limit 5
```

This saves one batch prompt file under:

* `<workspace_root>/triage/prompts/batch-next-<N>.md`

When you run later `pkls triage ...` commands, the CLI also syncs any complete triage cards into the configured Obsidian publish path.

### 4. Give that prompt to the AI agent

The AI agent should update:

* `<workspace_root>/records/<source_type>/<doc_id>/metadata.json`
* `<workspace_root>/triage/cards/<doc_id>.md`

### 5. Make the triage decision

```bash
python pkls triage accept --id <content_id>
python pkls triage reject --id <content_id>
python pkls triage later --id <content_id>
```

---

## Learning Workflow

The user controls learning sessions. The CLI generates prompts; the actual exploration happens in the AI agent.

### Step 1: initialize or resume a document

Run:

```bash
python pkls learn --id <content_id>
```

Or let the queue choose the next item:

```bash
python pkls learn next
```

This prompt should tell the AI agent to:

* read the record metadata
* read the resolved raw content
* read and update `learning/queue.json`
* create or update `state.json`
* generate a document framework and core summary
* choose `single_pass` or `chunked`
* set metadata status to `learning`

### Step 2: start a focus session

Run:

```bash
python pkls learn --id <content_id> --focus "state-driven resumability"
```

This prompt should tell the AI agent to:

* read metadata, raw content, and current state
* interpret the focus as user intent, not as raw chunk text
* load only the relevant source context
* perform one focused learning pass
* update `state.json`, `summary.md`, and `insights.md`
* suggest the next action

### Step 3: continue the interactive session with the AI agent

The CLI should not force the whole topic session into a single command.

Instead:

* the generated prompt opens the correct local context
* the user continues the exploration with the AI agent
* the AI agent works against repo files and workspace files

### Step 4: pause or consolidate intentionally

At the end of the agent session there are two desired outcomes:

#### Pause

The user wants to stop now and resume later.

Prompt behavior:

* update `state.json`
* append the session summary and insights
* update `next_action`
* preserve the exact resume context

#### Consolidate

The user feels the topic is understood well enough and wants to integrate it into the existing knowledge base.

Prompt behavior:

* read the Obsidian structure index
* read a small candidate set of related notes
* create a consolidation plan
* draft notes adapted to the user's note system

### Step 5: publish

After triage, learning outputs, or consolidation drafts are ready:

```bash
python pkls publish item --id <content_id>
python pkls publish consolidate --id <content_id>
```

Published files go under:

* `<vault>/pkls/triage/`
* `<vault>/pkls/learning/outlines/`
* `<vault>/pkls/learning/summaries/`
* `<vault>/pkls/learning/insights/`
* future consolidated note targets
* the Obsidian index is refreshed automatically for any published note files
* stale published files are removed when their workspace sources disappear

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
* `<workspace_root>/consolidation/plans/<doc_id>.json`
* `<workspace_root>/consolidation/drafts/<doc_id>.md`

---

## Notes

Current limitations:

* the full raw archive and sync store are filesystem locations, not database-backed
* sync/inbox orchestration is still manual
* pause and consolidation prompts generate workflow files, but the interactive session itself still happens in the AI agent rather than inside the CLI
* the AI agent is the analysis engine, not a background service
