# Question Refine Prompt

You are refining questions produced during learning.

This is a later-stage review prompt, not part of the initial learn / pause / consolidate flow.

## Read

Before refining, read:

* the item's metadata.json
* learning/states/<doc_id>/state.json
* learning/outputs/<doc_id>/qa.md

## Goal

Improve question quality without breaking resumability.

## Required Updates

Update:

* learning/states/<doc_id>/state.json
* learning/outputs/<doc_id>/qa.md

## Rules

* remove vague or generic questions
* keep questions grounded in the document
* prefer questions that support future deep dive or note-making
* preserve useful existing questions instead of rewriting everything
