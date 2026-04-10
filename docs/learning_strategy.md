# Learning Strategy (MVP)

## Goal

Define how the system:

* bounds triage reading
* initializes learning with a document framework
* chooses `single_pass` or `chunked`
* supports user-controlled focus sessions
* pauses and resumes learning safely
* delays question generation until after knowledge has accumulated
* consolidates learned material into Obsidian-compatible notes

---

## 1. Triage Budget

Triage is not full-document learning.

Its job is limited to:

* identifying what the material is about
* estimating reliability and learning value
* deciding `skip | skim | learn`

### Triage Reading Rules

#### Short Blog / Article

* may read the full text when the material is short

#### Paper

* prefer title, abstract, introduction, section headings, and conclusion
* sample extra paragraphs only when needed for a trustworthy recommendation

#### Book / Large PDF

* prefer table of contents, preface, chapter headings, and a few sample pages
* avoid full-text reading during triage

#### GitHub Repo

* prefer README, tree structure, key config files, and entry points
* avoid repository-wide code reading during triage

---

## 2. Learn Initialize

The first `learn --id <doc_id>` run initializes the learning state.

Output:

* document-level framework
* core summary
* processing-size decision
* initial `next_action`

This stage should create enough context for later interactive learning without requiring the user to re-read the source from scratch.

---

## 3. Size-Aware Processing

The system must automatically decide whether a document is small enough for `single_pass` learning or large enough to require `chunked` learning.

### Decision Inputs

* content type
* extracted text length
* estimated token count
* heading count
* page count for PDFs/books

### Modes

#### `single_pass`

Use for short blog posts, short notes, and compact papers.

Behavior:

* no persistent chunk manifest required
* later focus sessions can usually read the whole processed text cheaply

#### `chunked`

Use for large PDFs, books, long papers, and large structured sources.

Behavior:

* create a chunk manifest
* prefer section-level or chapter-level chunks
* use chunk summaries first, then chunk text only when needed

---

## 4. Chunking Strategy

Chunking is a structural learning aid, not an embedding requirement.

Each chunk should be a coherent learning unit with clear provenance.

### By Content Type

#### Paper

* section-level first
* paragraph-level only when a section is too large

#### Blog / Article

* heading-level first
* fallback: 800–1200 tokens

#### Code (GitHub Repo)

* file-level first
* function/class level when needed

#### Book / PDF

* chapter -> section -> paragraph

### Chunk Constraints

* readable independently
* linked to page or section boundaries
* small enough to reread cheaply during a focus session

---

## 5. Focus Sessions

`learn --id <doc_id> --focus "..."` starts or resumes a user-controlled topic session.

`focus` is not raw chunk text.

It should describe user intent, for example:

* a concept
* a chapter
* a question
* an application angle
* a comparison target

Examples:

* `"state-driven resumability"`
* `"chapter 3"`
* `"main argument"`
* `"how this applies to my current project"`

### Focus Session Flow

1. Read current state and document framework
2. Interpret the user focus
3. Select the minimum relevant source context
4. Learn one focused unit
5. Update state and output files
6. Suggest the next action

### Focus Output

A focus session should update:

* `state.json`
* `summary.md`
* `insights.md`

It should not generate `qa.md` by default.

---

## 6. Pause And Resume

Learning sessions are user-controlled and may stop at any time.

When the user pauses, the AI agent should:

* summarize what was covered in the current session
* update `current_focus`
* append to `focus_history`
* update `session_notes`
* update `next_action`
* keep the document resumable from state plus outputs

Resume logic must not depend on hidden chat memory.

---

## 7. Question Generation

Question generation is delayed until the material has been learned enough to justify reflection.

The system should generate questions only after knowledge has accumulated through one or more focus sessions.

### Suitable Triggers

* the user explicitly asks for review questions
* the document is near completion
* the topic is marked ready to consolidate

### Question Types

* understanding checks
* connection questions
* application questions
* unresolved questions

---

## 8. Consolidation Into Obsidian

After enough understanding has been accumulated, the system should move from source learning to knowledge consolidation.

### Consolidation Goals

* adapt learning outputs to the user's existing knowledge system
* align wording with current notes
* decide whether to create a new note or update an existing note
* preserve source references without turning the final note into a raw reading log

### Reading Rules

Consolidation should read:

* the Obsidian structure index
* a small candidate set of relevant notes

It should not read the full vault body on every run.

---

## 9. Output Files

For each document:

* `outline.md`
* `summary.md`
* `insights.md`
* `qa.md` only after reflection/review
* `chunk_manifest.json` for large materials only
* consolidation drafts and plans when the user requests knowledge integration

---

## 10. Design Principles

* bounded triage
* size-aware learning
* user-controlled focus
* incremental state updates
* deterministic behavior
* no hidden-memory dependence
* no full reprocessing unless unavoidable

---

## 11. Future Extensions

* better structural extraction for PDFs
* automatic Obsidian note candidate ranking
* delayed review-question generation
* spaced repetition after consolidation
