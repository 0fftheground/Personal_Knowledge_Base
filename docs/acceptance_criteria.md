# Acceptance Criteria

## General

* System runs locally
* No external infrastructure required
* All data persisted correctly

---

## Storage

* Content item saved with metadata
* Raw files stored in configured full or sync directories
* Records stored under `<workspace_root>/records/`
* No data loss on restart

---

## Triage

* Each candidate record produces:

  * summary
  * key points
  * recommendation
* Output saved as markdown card
* Card is compact enough for quick mobile review
* Triage remains bounded and does not become full-document learning
* No automatic learning triggered

---

## Learning Initialize

* First learning pass creates `outline.md`
* `core_summary` saved in state
* processing mode chosen correctly:

  * `single_pass`
  * `chunked`

---

## Focus Learning

* user can guide learning with a focus
* system reads only the relevant local context for that focus
* `state.json` updated after each focused learning session
* summary and insights updated incrementally

---

## Pause / Resume

* system preserves enough state to continue later
* no reprocessing from start unless necessary
* no reliance on hidden memory

---

## Questions

* `qa.md` is generated only after sufficient learning accumulation or explicit review request

---

## Consolidation

* consolidation can adapt learned material into the Obsidian knowledge structure
* consolidation reads the note index and a small candidate set of relevant notes
* consolidation does not reread the full vault body on every run

---

## Output

Each document must generate as needed:

* outline.md
* summary.md
* insights.md
* qa.md only after reflection/review
* consolidation draft(s) when the user requests knowledge integration

---

## Queue

* accepted items enter queue
* queue order respected
* status updates correctly

---

## Manual vs Auto

* all content defaults to candidate
* explicit `--accept` starts content as accepted

---

## Determinism

* same input + state → same result
* no hidden memory

---

## Failure Handling

* errors logged
* partial progress preserved
