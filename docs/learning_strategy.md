# Learning Strategy (MVP)

## Goal

Define how the system:

* splits content into chunks
* processes each chunk
* generates questions
* updates learning state

---

## 1. Chunking Strategy

### General Principle

Chunk must represent a **coherent learning unit**, not arbitrary length.

---

### By Content Type

#### Paper

* Split by:

  * sections (Introduction, Method, etc.)
* If section too long:

  * split by paragraphs

---

#### Blog / Article

* Split by:

  * headings (H1/H2)
* fallback:

  * 800–1200 tokens

---

#### Code (GitHub repo)

* Level 1:

  * file-level chunk

* Level 2 (if needed):

  * class / function level

---

#### Book / PDF

* Split by:

  * chapter → section → paragraph

---

### Constraints

* chunk must be:

  * readable independently
  * ≤ 1500 tokens (preferred)

---

## 2. Chunk Processing

For each chunk:

Input:

* chunk content
* previous learning state

Output:

* summary (short)
* key points
* questions
* optional insights

---

## 3. Question Generation (CRITICAL)

Each chunk MUST generate questions.

---

### Types of Questions

#### 1. Clarification

* What is unclear?
* What is not fully understood?

Example:

* "What exactly does X mean in this context?"

---

#### 2. Connection

* How does this relate to known concepts?

Example:

* "How is this different from RAG?"

---

#### 3. Application

* How can this be used?

Example:

* "Can this be applied to my current project?"

---

### Rules

* At least 1 question per chunk
* Prefer 2–3 questions
* Questions must be:

  * specific
  * actionable
  * tied to chunk

---

## 4. State Update

After each chunk:

Update:

* current_chunk += 1
* append key_points
* append questions
* update progress

---

## 5. Resume Logic

System must:

* read state.json
* locate next chunk
* continue processing

No reliance on:

* chat history
* hidden memory

---

## 6. Output Files

For each document:

* summary.md (cumulative)
* insights.md (high-value ideas)
* qa.md (questions + answers)

---

## 7. Design Principles

* incremental processing
* deterministic behavior
* state-driven learning
* no full reprocessing

---

## 8. Future Extensions

* difficulty-based chunking
* adaptive question generation
* spaced repetition
* knowledge graph linking
