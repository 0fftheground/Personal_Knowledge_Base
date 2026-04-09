# CLI Spec (MVP)

## Command Groups

* pkls add
* pkls raw
* pkls triage
* pkls learn
* pkls status
* pkls publish
* pkls config

---

## 1. Add

### Add Manual Content

pkls add manual --type <paper|blog|github|book> --path <file> [--title <title>] [--accept]

Behavior:

* copy content into configured raw stores
* create metadata under `<workspace_root>/records/manual/`
* default to `candidate`
* use `accepted` only when `--accept` is provided
* skip creating a new item when the same file hash already exists
* derive a title from content or filename when `--title` is omitted

### Add Auto Content

pkls add auto --type <paper|blog|github|book> --path <file> [--title <title>] [--accept]

Behavior:

* copy content into configured raw stores
* create metadata under `<workspace_root>/records/auto/`
* auto-detect URL list input vs regular file input
* default to `candidate`
* use `accepted` only when `--accept` is provided
* skip creating a new item when the same file hash already exists
* derive a title from content or filename when `--title` is omitted

If the file content looks like a URL list, the CLI automatically:

* reads URLs from the file
* fetches each webpage and stores a text snapshot in configured raw stores
* creates one metadata record per URL under `<workspace_root>/records/`
* uses `candidate` by default
* uses `accepted` only when `--accept` is provided
* skips URLs already present in existing raw snapshots

---

## 2. Raw

### Add To Sync Inbox

pkls raw inbox-add <auto|manual> --type <paper|blog|github|book> --path <file> [--title <title>] [--accept]

Behavior:

* copy content into `<raw_sync_root>/inbox/<device_name>/...`
* create metadata under `<workspace_root>/records/`
* set `sync_status = inbox`
* default to `candidate`
* use `accepted` only when `--accept` is provided
* skip creating a new item when the same file hash already exists
* derive a title from content or filename when `--title` is omitted

### Promote To Full Archive

pkls raw promote --id <content_id>

Behavior:

* copy the resolved raw file into `<raw_full_root>/<source_type>/<doc_id>/`
* update `full_raw_relpath`
* set `storage_tier = full`

### Sync To Active Store

pkls raw sync --id <content_id>

Behavior:

* copy the resolved raw file into `<raw_sync_root>/active/<source_type>/<doc_id>/`
* update `sync_raw_relpath`
* set `sync_status = active`

---

## 3. Triage

### List Candidates

pkls triage list

Behavior:

* show current candidate items from both `auto` and `manual`
* include triage recommendation when available
* include triage summary and reason when a triage card exists

### Generate Codex Triage Prompt

pkls triage prompt --id <content_id>

Behavior:

* write a Codex-ready triage prompt to `<workspace_root>/triage/prompts/<content_id>.md`
* point Codex to the record metadata, resolved raw file, and target card

### Generate Codex Triage Prompts In Batch

pkls triage prompt-batch [--limit <N>]

Behavior:

* select candidate items that do not yet have triage cards
* order them by priority, then title
* write one batch prompt file under `<workspace_root>/triage/prompts/`
* tell Codex which items to process in sequence and where each triage card should be written
* default `--limit` to `5`

### Accept

pkls triage accept --id <content_id>

Behavior:

* set status = accepted
* add to queue

### Reject

pkls triage reject --id <content_id>

Behavior:

* set status = rejected

### Later

pkls triage later --id <content_id>

Behavior:

* keep status = candidate
* mark deferred

---

## 4. Learn

### View Queue

pkls learn queue

Behavior:

* show items already in the learning flow
* include queue status, progress, chunk progress, and next action

### View Learning Progress

pkls learn list

Behavior:

* show items already in the learning flow
* include queue status, progress, chunk progress, and next action

### Generate Prompt For Next Queue Item

pkls learn next [--focus <text>]

Behavior:

* sync queue.json against metadata and learning state
* select the highest-priority actionable item
* print a Codex-ready prompt in `outline` or `deep_dive` mode

### Generate Codex Learning Prompt

pkls learn prompt --id <content_id> --mode <outline|deep_dive> [--focus <text>]

Behavior:

* print a Codex-ready learning prompt
* resolve the raw content path from full/sync stores
* in `outline` mode, instruct Codex to generate document structure first
* in `deep_dive` mode, instruct Codex to process one focused learning step

## 5. Status

### Show Item Status

pkls status --id <content_id>

Behavior:

* show metadata
* show raw storage paths
* show learning progress
* show open questions
* show next action

---

## 6. Publish

### Publish Triage Card

pkls publish triage --id <content_id>

Behavior:

* copy the triage card into the configured Obsidian vault
* publish under `pkls/triage/`

### Publish Learning Outputs

pkls publish learn --id <content_id>

Behavior:

* copy available learning outputs into the configured Obsidian vault
* publish under:
  * `pkls/learning/outlines/`
  * `pkls/learning/summaries/`
  * `pkls/learning/insights/`
  * `pkls/learning/qa/`

### Publish All Available Reading Outputs

pkls publish item --id <content_id>

Behavior:

* publish the triage card if present
* publish learning outputs if present

---

## 7. Config

### Show Local Config

pkls config show

Behavior:

* show local machine config path
* show configured device name
* show configured raw full root
* show configured raw sync root
* show configured workspace root
* show configured Obsidian vault path
* show current notes publish root

### Set Device Name

pkls config set-device-name --name <device_name>

### Set Full Raw Root

pkls config set-raw-full-root --path <directory>

### Set Sync Raw Root

pkls config set-raw-sync-root --path <directory>

### Set Workspace Root

pkls config set-workspace-root --path <directory>

### Set Obsidian Vault Path

pkls config set-obsidian-vault --path <directory>

Behavior:

* save local-only machine paths
* keep machine-specific paths outside git-tracked project settings

---

## CLI Principles

* concise output
* explicit errors
* deterministic behavior
* all write operations persist immediately
