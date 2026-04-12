# Learning Pause Prompt

Read `docs/architecture.md`, `docs/schema.md`, `docs/learning_strategy.md`, and `docs/prompt_spec.md`, then the execution context.

Persist the current learning session so it can resume without chat history.

Rules:

* save only stable, useful outcomes
* update state, summary, insights, queue, and `next_action`
* keep saved notes compact and actionable
* do not generate `qa.md` unless explicitly requested
