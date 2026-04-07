# Prompt Spec (MVP)

## Prompt Files

* prompts/triage_prompt.md
* prompts/learning_prompt.md
* prompts/question_refine_prompt.md

---

## Usage

### Triage Prompt

Used in:

* pkls triage run

Input:

* title
* content type
* raw content

Output:

* summary
* key points
* recommendation
* tags

---

### Learning Prompt

Used in:

* pkls learn start
* pkls learn resume

Input:

* metadata
* current learning state
* one chunk

Output:

* chunk summary
* key points
* questions
* insights
* next action

---

### Question Refine Prompt

Used optionally after learning prompt

Purpose:

* improve generated questions
* remove weak questions

---

## Constraints

* prompts must return structured JSON
* no markdown in model output
* no whole-document summary in chunk learning
* no hidden memory assumptions
