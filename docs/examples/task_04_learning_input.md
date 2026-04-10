# Stateful Learning Workflow

State-driven learning keeps progress reproducible. Instead of relying on chat history, the system stores initialization outputs, focus history, summaries, insights, and next actions in a JSON state file that can be resumed later.

## Learn Initialize

The first learning pass should create a document framework and a core summary. It should also decide whether the material is small enough for `single_pass` handling or large enough to require `chunked` processing.

## User-Controlled Focus Sessions

Each focus session should handle one user-selected topic only. The system should load the minimum relevant source context, update state, append new summary/insight material, and preserve a strong next action.

## Pause And Resume

The user may stop learning at any time. A pause step should record what was covered, what remains unclear, and what should happen next so the next run continues from saved state instead of restarting from the beginning.

## Consolidation Discipline

Once a topic is understood well enough, the system should adapt the learning outputs into the user's Obsidian note structure. This stage should use the Obsidian structure index and a small set of relevant notes rather than reading the whole knowledge base every time.
