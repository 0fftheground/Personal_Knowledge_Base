# Learning Pause Prompt

You are closing or pausing an interactive learning session.

Your job is to persist the useful results of the current session back into local files so the work can resume later without relying on chat history.

## Read First

Always read these project files first:

* docs/architecture.md
* docs/schema.md
* docs/learning_strategy.md
* docs/prompt_spec.md

Then read the execution-context files provided in the generated prompt.

## Goals

* capture what was actually learned in this session
* update local state and summaries
* leave a strong `next_action`
* preserve resumability

## Rules

* use the current learning conversation as the source for session details
* save only stable, useful learning outcomes
* do not generate `qa.md` unless the user explicitly asked for review questions
* keep the saved state compact and actionable
