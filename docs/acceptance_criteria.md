# Acceptance Criteria

## General

* System runs locally
* No external infrastructure required
* All data persisted correctly

---

## Storage

* Content item saved with metadata
* Files stored in correct directories
* No data loss on restart

---

## Triage

* Each raw/auto item produces:

  * summary
  * key points
  * recommendation
* Output saved as markdown card
* No automatic learning triggered

---

## Learning

### Chunking

* Content is split correctly
* Chunk size reasonable

### State

* state.json updated after each chunk
* current_chunk increments
* progress updated

### Resume

* system resumes from correct chunk
* no reprocessing from start

---

## Output

Each document must generate:

* summary.md
* insights.md
* qa.md

---

## Queue

* accepted items enter queue
* queue order respected
* status updates correctly

---

## Manual vs Auto

* manual → directly accepted
* auto → must go through candidate

---

## Determinism

* same input + state → same result
* no hidden memory

---

## Failure Handling

* errors logged
* partial progress preserved
