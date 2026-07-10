# DocOS — AI Document Operating System

A visual AI document editor. Users upload a DOCX, it becomes an editable **graph**,
natural-language commands become **validated JSON actions**, the backend **executes**
them and **streams every step** over WebSockets, and a **version engine** provides
undo / redo / rewind / branch / diff.

> DocOS lives alongside the existing Formatly generator. It reuses Formatly's
> multi-provider LLM router (`app/services/router.py`) as its pluggable AI layer.

## Four engines

```
┌──────────────────────────────────────────────────────────────────────┐
│  1. Document Engine   graph model + DOCX parser                        │
│     app/docos/graph, app/docos/parser                                  │
│     DOCX ──parse──▶ DocumentGraph (typed nodes: heading, body, table…) │
├──────────────────────────────────────────────────────────────────────┤
│  2. AI Command Engine   natural language ──▶ structured actions        │
│     app/docos/command                                                  │
│     "highlight all figures" ─LLM(router)+validate─▶ [Action, …]        │
├──────────────────────────────────────────────────────────────────────┤
│  3. Execution Engine   applies actions, streams events                 │
│     app/docos/execution                                                │
│     resolves targets ▶ mutates graph ▶ emits selection/format/… events │
├──────────────────────────────────────────────────────────────────────┤
│  4. Version Engine   history, undo/redo/rewind, branch, diff           │
│     app/docos/versioning                                               │
│     SQLite. Snapshot every 10 versions, replay actions in between.     │
└──────────────────────────────────────────────────────────────────────┘
```

## Request lifecycle

```
user command ─▶ AI Command Engine ─▶ Action[]  (validated JSON)
                                        │
                    Version Engine  ◀── Execution Engine ──▶ Event Hub ─ws─▶ UI
                    (new version)       (mutates graph)       (live animation)
```

1. Client sends a command over `/ws/{document_id}` (or REST `/docos/{id}/command`).
2. **AI Command Engine** turns NL into an `ActionBatch`, validated against the schema.
3. **Execution Engine** resolves each action's target to concrete node ids, applies
   the mutation, and emits granular events (`selection_item`, `format_progress`, …).
4. Events stream to the UI over WebSocket for animation.
5. **Version Engine** commits a new version (parent = current), enabling undo/rewind.

## Design rules

- The **AI never edits the document**. It only emits actions. The Execution Engine
  is the sole mutator. This keeps edits auditable, validatable, and reversible.
- Every action is **validated** (type + target + params) before execution;
  invalid/dangerous batches are rejected and the graph rolls back untouched.
- Everything is **visual**: execution is event-sourced so the UI can animate.

## Module map

| Package                 | Responsibility                                        |
|-------------------------|-------------------------------------------------------|
| `docos/graph`           | Node/DocumentGraph model, typed nodes, traversal      |
| `docos/parser`          | DOCX → DocumentGraph                                   |
| `docos/actions`         | Action language schema + validator                    |
| `docos/execution`       | Execution engine + event definitions                  |
| `docos/versioning`      | SQLite version store, snapshot/replay, diff           |
| `docos/events`          | WebSocket connection hub                               |
| `docos/command`         | AI command engine (NL → actions via router)           |
| `docos/api.py`          | FastAPI router mounted at `/docos`                     |

## Provider layer

Reuses `app/services/router.py` — Groq → Gemini → OpenRouter → HuggingFace(Mistral),
each with per-provider cooldown fallback. The command engine forces strict-JSON output
and validates it, so a provider that returns prose is treated as a failure and the next
provider is tried; deterministic heuristics are the final fallback.
