# Triage Prompt

Read `docs/architecture.md`, `docs/schema.md`, and `docs/prompt_spec.md`, then the execution context.

Make a bounded decision: `learn`, `skim`, or `skip`. Verify fast-changing claims from official sources when needed.

Rules:

* sample large sources; do not do full learning here
* update metadata: set `ai_recommendation`, keep status `candidate`, preserve `manual_decision`
* write and publish the triage card when complete

Card format:

* `## Summary`: 1 sentence
* `## Key Points`: 2-3 bullets, one line each
* `## Recommendation`: exactly `learn`, `skim`, or `skip`
* `## Reason`: 1 sentence

Keep the whole card compact, about 80-140 words unless the source truly needs more.
