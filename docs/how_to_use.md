# How To Use

## Purpose

This document is the practical operating guide for the MVP and the intended next-step learning workflow.

Use it when you want to:

* configure a machine
* add new material
* run bounded triage with an AI agent
* run user-controlled learning with an AI agent
* publish readable output to Obsidian

---

## 1. System Layout

The system currently uses four layers:

1. Full raw store
   Long-term archive for original files.
2. Sync raw store
   Active subset shared across devices.
3. User workspace store
   This stores records, triage cards, learning state, outputs, and consolidation drafts.
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
* `consolidation/plans/`
* `consolidation/drafts/`
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
python pkls config set-device-name --name "pc-dev"
python pkls config set-raw-sync-root --path "F:\google drive\PKB\raw_sync_root"
python pkls config set-workspace-root --path "F:\google drive\PKB\workspace"
python pkls config set-obsidian-vault --path "D:\Obsidian\Vault"
python pkls config show
```

### Additional setup on the main archive machine

Also set:

```bash
python pkls config set-raw-full-root --path "D:\pkls_raw_full"
```

Notes:

* `device_name` identifies the machine in `inbox/<device_name>/`
* `raw_sync_root` is the shared active raw store
* `raw_full_root` is optional on secondary machines
* `workspace_root` stores records, triage cards, learning state, outputs, and consolidation drafts
* `.pkls.local.json` is local-only and should not be committed

---

## 3. Add New Content

### Manual content

Use manual content for files you add yourself. Manual items still default to `candidate` unless you explicitly mark them accepted during ingest.

```bash
python pkls add manual --type blog --path .\notes.md
python pkls add manual --type blog --path .\links.list
python pkls add manual --type blog --path .\notes.md --accept
```

### Auto content

Use auto content when the item should be reviewed before learning.

```bash
python pkls add auto --type blog --path .\article.md
python pkls add auto --type blog --path .\article.md --accept
```

### URL list content

When the input file looks like a URL list, the CLI detects that automatically.

```bash
python pkls add auto --type blog --path .\url_list.txt
python pkls add manual --type blog --path .\url_list.txt
```

---

## 4. Use The Sync Inbox

If you are on a secondary machine and only want to submit material into the shared sync store, use the inbox command.

```bash
python pkls raw inbox-add auto --type blog --path .\article.md
python pkls raw inbox-add manual --type paper --path .\paper.pdf
python pkls raw inbox-add manual --type paper --path .\paper.pdf --accept
```

Other raw operations:

```bash
python pkls raw sync --id <content_id>
python pkls raw promote --id <content_id>
```

---

## 5. Triage Workflow

### Step 1: inspect candidates

```bash
python pkls triage list
```

### Step 2: generate an agent triage prompt

```bash
python pkls triage prompt --id <content_id>
python pkls triage prompt-batch --limit 5
```

Give that prompt to your AI agent.

The AI agent is expected to:

* read the project docs named in the prompt
* read the item's metadata from `<workspace_root>/records/`
* read a bounded portion of the resolved raw file
* update `ai_recommendation`
* write `<workspace_root>/triage/cards/<content_id>.md`
* auto-publish the card to Obsidian when summary, key points, recommendation, and reason are all present

Use `triage prompt-batch` when you want a small batch of prompts for candidate items that still need triage cards.

Prompt files are saved under:

* `<workspace_root>/triage/prompts/<content_id>.md`
* `<workspace_root>/triage/prompts/batch-next-<N>.md`

### Step 3: make the decision

```bash
python pkls triage accept --id <content_id>
python pkls triage reject --id <content_id>
python pkls triage later --id <content_id>
```

Meaning:

* `accept`: move item into learning queue
* `reject`: stop processing
* `later`: keep it as candidate and defer it

---

## 6. Learning Workflow

The intended learning flow is:

1. initialize the document
2. run one or more user-controlled focus sessions
3. pause or consolidate intentionally

The CLI currently handles prompt generation. The interactive exploration itself happens in your AI agent after you open the generated prompt.

### Step 1: see the queue

```bash
python pkls learn queue
python pkls learn list
```

This learning view includes:

* item status
* queue status
* learning progress
* chunk progress when available
* next action

### Step 2: initialize or resume a document

```bash
python pkls learn --id <content_id>
python pkls learn next
```

This should initialize:

* the document framework
* the core summary
* the processing mode: `single_pass` or `chunked`
* the initial `next_action`

### Step 3: start a focus session

```bash
python pkls learn --id <content_id> --focus "state-driven resumability"
```

`focus` means the user topic or question to explore.

It is not raw chunk text.

Examples:

* a concept
* a chapter
* an application angle
* a comparison
* a concrete question

The AI agent should:

* interpret the focus
* load the minimum relevant local content
* update `state.json`
* update `summary.md`
* update `insights.md`

### Step 4: continue the topic conversation with the AI agent

After you open the generated prompt, the detailed exploration can continue directly with the AI agent.

The CLI does not need to represent every sub-step of that session.

### Step 5: end the session intentionally

There are two desired outcomes:

#### Pause

You want to stop now and continue later.

Prompt behavior:

* capture this session's learning
* update `state.json`
* update `summary.md`
* update `insights.md`
* write a strong `next_action`

#### Consolidate

You feel the topic is understood and want to adapt it into your Obsidian knowledge base.

Prompt behavior:

* read the Obsidian structure index
* inspect a small candidate set of related notes
* write a consolidation plan
* write a knowledge-note draft

### Step 6: delayed questions

Do not generate `qa.md` during initialization.

Prefer generating review questions only after:

* several focus sessions
* enough key points and insights
* explicit user request for review/reflection

---

## 7. Check Status

Use:

```bash
python pkls status --id <content_id>
```

`status --id` shows:

* metadata
* storage relpaths
* learning progress
* open questions
* next action

---

## 8. Publish To Obsidian

After triage or learning output is ready:

```bash
python pkls publish triage --id <content_id>
python pkls publish learn --id <content_id>
python pkls publish item --id <content_id>
```

Published output goes under:

* `<vault>/pkls/triage/`
* `<vault>/pkls/learning/outlines/`
* `<vault>/pkls/learning/summaries/`
* `<vault>/pkls/learning/insights/`
* future consolidated note targets

Use this as the mobile reading layer on iPhone/iPad.

---

## 9. Typical Daily Flows

### Flow A: add manual material and start learning

```bash
python pkls add manual --type blog --path .\notes.md --accept
python pkls learn --id <content_id>
python pkls learn --id <content_id> --focus "main argument"
```

### Flow B: add material, triage it, then start learning

```bash
python pkls add auto --type blog --path .\article.md
python pkls triage prompt --id <content_id>
python pkls triage accept --id <content_id>
python pkls learn --id <content_id>
```

### Flow C: finish a topic and prepare knowledge integration

Current target flow:

1. run one or more focus sessions
2. pause or consolidate intentionally with the AI agent
3. publish the resulting outputs

---

## 10. Current Limitations

The current system is usable, but still an MVP.

Not finished yet:

* no automatic fetch pipeline
* no automatic inbox collection
* the CLI generates pause/consolidate prompts, but the actual interactive learning still happens in the AI agent
* no fully automated knowledge-note generation
* the AI agent is still the analysis engine, not a background service
