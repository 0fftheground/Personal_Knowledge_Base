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
* store triage cards
* store learning state
* store learning outputs
* store workspace-local notes fallback

### 4. Notes Layer

Obsidian vault or workspace-local `notes/`.

Purpose:

* mobile reading
* published triage and learning outputs
* final knowledge notes

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

Stores triage markdown cards.

### Learning Layer

Stores learning state and outputs.

### Notes Layer

Stores published reading material and long-term notes.

---

## Modules

### add

* copy raw content into configured raw stores
* create metadata records in `<workspace_root>/records/`

### triage

* read raw content through resolved external paths
* generate cards
* update metadata recommendation

### decision

* user updates candidate state

### learning

* read raw content through resolved external paths
* update state incrementally
* generate outline and learning outputs

### publish

* copy triage and learning outputs into Obsidian-facing directories

---

## Design Constraints

* raw files do not live in git-tracked repository state
* workspace data does not live in git-tracked repository state
* all learning remains reproducible from raw file + state
* each document must be independently resumable
* machine-specific paths stay in local config only
