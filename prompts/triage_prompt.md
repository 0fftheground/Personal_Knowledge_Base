# Triage Prompt

You are helping operate a personal knowledge system through Codex.

Your job is not just to analyze content. You must also update the local files
that represent the triage result.

## Read First

Always read these project files first:

* docs/architecture.md
* docs/schema.md
* docs/prompt_spec.md

Then read:

* the item's metadata.json
* the raw content file

If the content is about a fast-changing product, library, company, model, API,
or standard, verify critical time-sensitive claims from official sources before
making the recommendation.

## User Context

The user is learning:

* LLM application engineering
* agent systems
* AI architecture
* evaluation
* tooling and workflow design

## What To Evaluate

You should determine:

* what the content is mainly about
* whether it contains reusable ideas
* whether it is novel relative to common AI engineering knowledge
* whether it deserves deep learning, a quick skim, or a skip

## Required File Updates

You must update:

* records/auto/<doc_id>/metadata.json
* triage/cards/<doc_id>.md

In metadata.json:

* update ai_recommendation
* keep status as candidate
* do not auto-accept the item
* preserve manual_decision unless explicitly instructed otherwise

In the triage card markdown, include:

* summary
* key points
* relevance
* recommendation
* reason

## Recommendation Rules

* use `learn` only if the material is worth a focused learning session
* use `skim` if it is useful but not a top-priority study item
* use `skip` if it is low-value, redundant, or weakly relevant

## Quality Bar

Your triage output should make it easy for the user to answer:

* What is this about?
* Why does it matter?
* Why should I care now?
