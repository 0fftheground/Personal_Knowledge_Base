# Stateful Learning Workflow

State-driven learning keeps progress reproducible. Instead of relying on chat
history, the system stores chunk progress, key points, and open questions in a
JSON state file that can be resumed later.

## Outline First

An outline-first pass helps the user see the overall structure before spending
time on detailed study. It should identify the main sections, the core summary,
and the most promising areas for deeper review.

## Incremental Deep Dive

Each deep-dive step should process one coherent chunk only. After each chunk,
the system updates progress, appends key points, appends questions, and writes
summary, insights, and QA files without recomputing the whole document.

## Practical Discipline

The workflow should log each important step and keep outputs deterministic. If
the process stops halfway through, the next run should continue from the next
chunk instead of restarting from the beginning.
