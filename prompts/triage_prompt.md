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

## What To Evaluate

You should determine:

* what the content is mainly about
* whether the main claims appear truthful and evidence-based
* whether the source and argumentation look reliable enough to trust
* whether it deserves deep learning, a quick skim, or a skip

## Required File Updates

You must update:

* records/<source_type>/<doc_id>/metadata.json
* triage/cards/<doc_id>.md
* the published Obsidian triage note when the card is complete

In metadata.json:

* update ai_recommendation
* keep status as candidate
* do not auto-accept the item
* preserve manual_decision unless explicitly instructed otherwise

In the triage card markdown, include:

* summary
* key points
* recommendation
* reason

Treat a triage card as complete only when all four sections above are present
and non-empty. When the card is complete, also publish it to the Obsidian path
provided in the execution context.

## Recommendation Rules

* use `learn` only if the material is worth a focused learning session
* use `skim` if it is useful but not a top-priority study item
* use `skip` if it is unreliable, low-value, or not worth time investment

## Quality Bar

Your triage output should make it easy for the user to answer:

* What is this about?
* Can I trust it?
* Is it worth learning?
