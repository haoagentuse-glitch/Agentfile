---
name: project-docs
description: Maintain the project's durable documentation — what the system is and why it is shaped that way. Use when the system's purpose, scope, or structure has changed and the docs no longer match.
---

# Project docs

Durable knowledge only. What the system **is**, and why it is shaped this way.

## Ownership

This skill owns exactly two files. Everything else belongs to another owner — do not write to them.

| File | Owner |
|---|---|
| `docs/PROJECT.md` | this skill |
| `docs/architecture.md` | this skill |
| `CONTEXT.md` (glossary) | `domain-modeling` |
| `docs/adr/` | `domain-modeling` |
| `openapi.yaml` | `api-contract` |
| Issues | `to-spec` / `to-tickets` |

## PROJECT.md

```
PROJECT.md = purpose, scope, system overview, stable background
           ≠ feature spec
           ≠ task list
           ≠ changelog
```

Never copy a feature spec out of an issue into `docs/`. The issue is the spec. If you find yourself restating what a ticket asks for, stop — that content has an owner already.

Write it only when there is something durable to say. A one-paragraph `PROJECT.md` is a fine `PROJECT.md`.

## architecture.md

Create it lazily — only once the shape is non-obvious from the directory listing. Cover the pieces, what talks to what, and the constraints a newcomer would otherwise violate. Not a file-by-file tour.

## Scale to the project

Small project: `PROJECT.md` alone. Add `architecture.md` when someone has to be told how the pieces fit. Do not pre-create either.

## When to run

Run after the system changes shape, not after every ticket. Triggers: scope moved, a component was added or removed, a constraint changed, or a newcomer asked a question the docs could not answer.

## Before writing

Read `writing-for-agents` and apply it — these files are read by agents on every session, so their length is a recurring cost.

Check what already answers the question. If `CONTEXT.md`, an ADR, or an issue already says it, link instead of restating.

## After writing

Once the docs are written and correct, refresh the semantic index:

```bash
command -v memsearch >/dev/null && memsearch index docs/ || echo "語意索引未更新"
```

The trailing `|| echo` is load-bearing: without it the short-circuit exits 1 when memsearch is absent, which reads as a failed task.

The docs are the deliverable; the index is a cache of them. If memsearch is absent or the index fails, **the task still succeeded** — say "語意索引未更新" in your report and stop there. Never retry, never install anything, never let it turn a finished doc into a failure.
