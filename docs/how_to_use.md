# How To Use

## Purpose

This document is the practical operating guide for the current MVP.

Use it when you want to:

* configure a machine
* add new material
* run triage with Codex
* run learning with Codex
* publish readable output to Obsidian

---

## 1. System Layout

The system currently uses four layers:

1. Full raw store
   Long-term archive for original files.
2. Sync raw store
   Active subset shared across devices.
3. User workspace store
   This stores records, triage cards, learning state, outputs, and notes fallback.
4. Obsidian vault
   Mobile reading layer and long-term note layer.

Repo paths:

* `scripts/`
* `docs/`
* `prompts/`

Workspace paths:

* `records/`
* `triage/cards/`
* `learning/states/`
* `learning/outputs/`
* `notes/`

External paths are configured locally in `.pkls.local.json`.

---

## 2. Configure A Machine

Start from the example file:

1. Copy `.pkls.local.example.json` to `.pkls.local.json`
2. Replace the example values with real local paths
3. Keep `.pkls.local.json` uncommitted

Meaning:

* `.pkls.local.example.json` is the git-tracked template
* `.pkls.local.json` is the real machine-local config
* `.pkls.local.json` should only contain actual local paths for the current device

### Minimum setup on a non-archive machine

Set:

```bash
python -m scripts.pkls config set-device-name --name "pc-dev"
python -m scripts.pkls config set-raw-sync-root --path "F:\google drive\PKB\raw_sync_root"
python -m scripts.pkls config set-workspace-root --path "F:\google drive\PKB\workspace"
python -m scripts.pkls config set-obsidian-vault --path "D:\Obsidian\Vault"
python -m scripts.pkls config show
```

### Additional setup on the main archive machine

Also set:

```bash
python -m scripts.pkls config set-raw-full-root --path "D:\pkls_raw_full"
```

Notes:

* `device_name` identifies the machine in `inbox/<device_name>/`
* `raw_sync_root` is the shared active raw store
* `raw_full_root` is optional on secondary machines
* `workspace_root` stores records, triage cards, learning state, outputs, and notes fallback
* `.pkls.local.json` is local-only and should not be committed

---

## 3. Add New Content

### Manual content

Use manual content when you already know the item should enter learning.

```bash
python -m scripts.pkls add manual --type blog --path .\notes.md --title "My Notes"
```

Result:

* raw file is copied into configured raw stores
* record is created under `<workspace_root>/records/manual/<doc_id>/metadata.json`
* item starts as `accepted`
* item is added to `<workspace_root>/learning/queue.json`

### Auto content

Use auto content when the item should be reviewed before learning.

```bash
python -m scripts.pkls add auto --type blog --path .\article.md --title "Interesting Article"
```

Result:

* raw file is copied into configured raw stores
* record is created under `<workspace_root>/records/auto/<doc_id>/metadata.json`
* item starts as `candidate`

---

## 4. Use The Sync Inbox

If you are on a secondary machine and only want to submit material into the
shared sync store, use the inbox command.

```bash
python -m scripts.pkls raw inbox-add auto --type blog --path .\article.md --title "Interesting Article"
python -m scripts.pkls raw inbox-add manual --type paper --path .\paper.pdf --title "Useful Paper"
```

Result:

* raw file is copied into `<raw_sync_root>/inbox/<device_name>/...`
* record is created in `<workspace_root>/records/`
* `sync_status` becomes `inbox`

Other raw operations:

```bash
python -m scripts.pkls raw sync --id <content_id>
python -m scripts.pkls raw promote --id <content_id>
```

Use them when you need to:

* ensure an item exists under `active/...`
* promote an item into the full archive

---

## 5. Triage Workflow

### Step 1: inspect candidates

```bash
python -m scripts.pkls triage list
```

### Step 2: generate a Codex triage prompt

```bash
python -m scripts.pkls triage prompt --id <content_id>
```

Give that prompt to Codex.

Codex is expected to:

* read the project docs named in the prompt
* read the item's metadata from `<workspace_root>/records/`
* read the resolved raw file
* update `ai_recommendation`
* write `<workspace_root>/triage/cards/<content_id>.md`

### Step 3: make the decision

```bash
python -m scripts.pkls triage accept --id <content_id>
python -m scripts.pkls triage reject --id <content_id>
python -m scripts.pkls triage later --id <content_id>
```

Meaning:

* `accept`: move item into learning queue
* `reject`: stop processing
* `later`: keep it as candidate and defer it

---

## 6. Learning Workflow

Learning is designed as:

1. outline first
2. deep dive later

### Step 1: see the queue

```bash
python -m scripts.pkls learn queue
```

### Step 2: generate the outline prompt

```bash
python -m scripts.pkls learn prompt --id <content_id> --mode outline
```

Give that prompt to Codex.

Codex should:

* read metadata and raw content
* create or update `<workspace_root>/learning/states/<content_id>/state.json`
* set `outline_generated = true`
* write `document_outline`
* write `core_summary`
* write `<workspace_root>/learning/outputs/<content_id>/outline.md`

### Step 3: deep dive on demand

```bash
python -m scripts.pkls learn prompt --id <content_id> --mode deep_dive --focus "state-driven resumability"
```

Give that prompt to Codex.

Codex should:

* process exactly one coherent learning unit
* update `state.json` incrementally
* update:
  * `summary.md`
  * `insights.md`
  * `qa.md`

### Optional deterministic local processing

The CLI still contains the minimal local learning commands:

```bash
python -m scripts.pkls learn start --id <content_id>
python -m scripts.pkls learn resume --id <content_id>
python -m scripts.pkls learn next
```

These are rule-based helpers, not the preferred Codex-assisted path.

---

## 7. Check Status

Use:

```bash
python -m scripts.pkls status --id <content_id>
```

This shows:

* metadata
* storage relpaths
* learning progress
* open questions
* next action

---

## 8. Publish To Obsidian

After triage or learning output is ready:

```bash
python -m scripts.pkls publish triage --id <content_id>
python -m scripts.pkls publish learn --id <content_id>
python -m scripts.pkls publish item --id <content_id>
```

Published output goes under:

* `<vault>/pkls/triage/`
* `<vault>/pkls/learning/outlines/`
* `<vault>/pkls/learning/summaries/`
* `<vault>/pkls/learning/insights/`
* `<vault>/pkls/learning/qa/`

Use this as the mobile reading layer on iPhone/iPad.

---

## 9. Typical Daily Flows

### Flow A: add and learn manual material

```bash
python -m scripts.pkls add manual --type blog --path .\notes.md --title "My Notes"
python -m scripts.pkls learn prompt --id <content_id> --mode outline
python -m scripts.pkls learn prompt --id <content_id> --mode deep_dive --focus "main argument"
python -m scripts.pkls publish item --id <content_id>
```

### Flow B: add and triage auto material

```bash
python -m scripts.pkls add auto --type blog --path .\article.md --title "Interesting Article"
python -m scripts.pkls triage prompt --id <content_id>
python -m scripts.pkls triage accept --id <content_id>
python -m scripts.pkls learn prompt --id <content_id> --mode outline
```

### Flow C: submit material from a secondary machine

```bash
python -m scripts.pkls raw inbox-add auto --type blog --path .\article.md --title "Interesting Article"
```

---

## 10. Current Limitations

The current system is usable, but still an MVP.

Not finished yet:

* no automatic fetch pipeline
* no automatic inbox collection
* no fully automated knowledge-note generation
* Codex is still the analysis engine, not a background service
