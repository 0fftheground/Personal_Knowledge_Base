# CLI Spec (MVP)

## Command Groups

* pkls add
* pkls triage
* pkls learn
* pkls status

---

## 1. Add

### Add Manual Content

pkls add manual --type <paper|blog|github|book> --path <file> --title <title>

Behavior:

* copy content into raw/manual
* create metadata
* set status = accepted

### Add Auto Content

pkls add auto --type <paper|blog|github|book> --path <file> --title <title>

Behavior:

* copy content into raw/auto
* create metadata
* set status = candidate

---

## 2. Triage

### Run Triage

pkls triage run

Behavior:

* process raw/auto items not yet triaged
* generate triage cards
* update metadata

### List Candidates

pkls triage list

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

## 3. Learn

### View Queue

pkls learn queue

### Start Learning

pkls learn start --id <content_id>

Behavior:

* initialize learning state
* chunk document
* process first chunk

### Resume Learning

pkls learn resume --id <content_id>

Behavior:

* load learning state
* continue from next chunk

### Learn Next

pkls learn next

Behavior:

* select next accepted item from queue
* start or resume learning

---

## 4. Status

### Show Item Status

pkls status --id <content_id>

Behavior:

* show metadata
* show learning progress
* show open questions
* show next action

---

## CLI Principles

* concise output
* explicit errors
* deterministic behavior
* all write operations persist immediately
