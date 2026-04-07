# Architecture (MVP)

## Directory Structure

knowledge-system/

* raw/

  * auto/
  * manual/

* triage/

  * cards/

* learning/

  * queue.json
  * states/
  * outputs/

* notes/  (Obsidian)

* scripts/

---

## Layers

### 1. Raw Layer

Stores original content

### 2. Triage Layer

AI-generated summaries and recommendations

### 3. Learning Layer

Stateful learning process

### 4. Notes Layer

Final knowledge (Obsidian)

---

## Modules

### fetch (future)

* Pull content into raw/auto

### triage

* Read raw/auto
* Generate cards
* Assign recommendation

### decision (manual)

* User updates candidate → accepted/rejected

### learning

* Read accepted items
* Process chunk by chunk
* Update state
* Generate outputs

---

## Storage Strategy

| Type             | Storage    |
| ---------------- | ---------- |
| raw content      | filesystem |
| triage cards     | markdown   |
| learning outputs | markdown   |
| state            | JSON (MVP) |
| queue            | JSON       |

---

## Design Constraints

* No global mutable state outside state files

* All processing must be reproducible from:
  raw + state

* Each document must be independently resumable

---

## Future Upgrade

* Replace JSON state with SQLite
* Add background jobs
* Add API layer
