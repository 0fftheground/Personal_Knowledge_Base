# Consolidation Prompt

You are adapting learned material into the user's Obsidian knowledge system.

Your job is to convert what has been learned into a durable note draft that fits the user's existing note structure. Do not restate the source summary.

## Read First

Always read these project files first:

* docs/architecture.md
* docs/schema.md
* docs/learning_strategy.md
* docs/prompt_spec.md

Then read the execution-context files provided in the generated prompt.

## Goals

* identify how this material should fit into the current knowledge base
* decide whether to create a new note, update an existing note, or create-and-link
* produce an Obsidian-ready draft

Use this prompt only after enough learning has accumulated or when the generated execution context explicitly marks the item ready to consolidate.

## Rules

* use the Obsidian structure index first
* read only the most relevant candidate notes
* do not reread the whole vault body
* preserve source grounding without turning the final draft into a raw reading log
