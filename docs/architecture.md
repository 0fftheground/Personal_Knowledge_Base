# Architecture (MVP)

## Storage Model

The system is split into four layers:

### 1. Full Raw Store

External filesystem location.

Purpose:

* store the complete raw library
* act as the long-term source of truth for original files

### 2. Active Sync Store

External filesystem location.

Purpose:

* store the active subset used across devices
* receive incoming files from other devices

### 3. User Workspace Store

External filesystem location.

Purpose:

* store content records
* store triage cards and prompt files
* store learning state and intermediate outputs
* store consolidation plans and drafts
* store workspace-local notes fallback

### 4. Notes Layer

Obsidian vault or workspace-local `notes/`.

Purpose:

* mobile reading
* published triage and learning outputs
* final knowledge notes adapted to the user's note system

---

## Repository Structure

knowledge-system/

* scripts/
* prompts/
* docs/

---

## Workspace Structure

`<workspace_root>/`

* records/

  * auto/
  * manual/

* triage/

  * cards/
  * prompts/

* learning/

  * queue.json
  * states/
  * outputs/
  * prompts/

* consolidation/

  * plans/
  * drafts/
  * indexes/

* notes/

---

## External Raw Structure

Full raw store:

* `<raw_full_root>/auto/`
* `<raw_full_root>/manual/`

Active sync store:

* `<raw_sync_root>/active/`
* `<raw_sync_root>/inbox/<device_name>/`

---

## Layers

### Raw Layer

Raw files live outside the repository.

### Record Layer

The workspace stores metadata records for each content item.

### Triage Layer

Stores decision-oriented cards for candidate items.

### Learning Layer

Stores learning state, initialization outputs, focus-session outputs, and pause snapshots.

### Consolidation Layer

Stores plans and drafts that adapt learned material into the existing Obsidian knowledge structure.

### Notes Layer

Stores published reading material and long-term notes.

---

## Modules

### add

* copy raw content into configured raw stores
* create metadata records in `<workspace_root>/records/`

### triage

* read raw content through resolved external paths
* use bounded reading only
* generate decision cards
* update metadata recommendation

### decision

* user updates candidate state

### learning

* initialize accepted items with document framework and core content
* classify material as `single_pass` or `chunked`
* run user-controlled focus sessions
* save pause/resume state incrementally

### consolidate

* read the Obsidian structure index and a small set of relevant notes
* generate a consolidation plan
* draft knowledge notes adapted to the user's note system

### publish

* copy triage, learning, and consolidated outputs into Obsidian-facing directories
* incrementally refresh the Obsidian index for published note files
* remove stale published files when their workspace sources no longer exist

---

## Core Workflow

### 1. Triage

Triage is bounded and decision-oriented.

It answers:

* what this item is
* whether it is worth learning
* whether to `skip`, `skim`, or `learn`

It does not perform full-document learning.

### 2. Learn Initialize

The first learning run creates a document-level framework and core summary.

The system also decides whether the material should stay `single_pass` or move to `chunked` processing.

### 3. Learn Focus

The user controls the topic or question to explore.

The system provides the AI agent with:

* the current state
* the document framework
* prior summaries and insights
* only the relevant local content for the requested focus

### 4. Learn Pause

When the user stops a learning session, the AI agent writes the updated state, summaries, insights, and next action so the work is resumable.

### 5. Consolidate

Once the user feels a topic is understood well enough, the AI agent adapts the learned material into the existing Obsidian knowledge structure.

This stage reads:

* the Obsidian structure index
* a small candidate set of related notes

It does not scan the full vault body on every run.

---

## Design Constraints

* raw files do not live in git-tracked repository state
* workspace data does not live in git-tracked repository state
* all learning remains reproducible from raw file + state
* triage must stay bounded; full-document reading belongs to learning
* each document must be independently resumable
* learning sessions are user-controlled, not auto-advanced in the background
* consolidation should use note structure plus selected relevant notes, not full-vault rereads
* machine-specific paths stay in local config only
