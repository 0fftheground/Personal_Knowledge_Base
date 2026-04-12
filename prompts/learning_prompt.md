# Learning Prompt

Read `docs/architecture.md`, `docs/schema.md`, `docs/learning_strategy.md`, and `docs/prompt_spec.md`, then the execution context.

Use raw content plus state files; do not rely on hidden memory.

Rules:

* keep learning user-controlled and resumable
* use the smallest useful local context
* prefer chunk metadata/files for large sources
* do not generate `qa.md` during initialization
* keep pause and consolidation separate unless requested

Mode:

* `outline`: create framework, core summary, processing mode, and initial state
* `deep_dive`: use the focus as intent, learn one focused unit, and keep enough context for later pause
