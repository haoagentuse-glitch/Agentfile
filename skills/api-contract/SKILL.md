---
name: api-contract
description: Contract-driven development for HTTP APIs — author the OpenAPI spec first, generate models and contract tests from it. Use when building or changing an HTTP endpoint, or when the API surface is under discussion.
---

# API contract

`openapi.yaml` is the single source of truth for the API surface. Models and contract tests are generated from it. Neither is edited by hand.

## Loop

1. **Write or amend `openapi.yaml`.** This is the design step. Nothing else moves first.
2. **Generate models.**
   ```bash
   uv run datamodel-codegen --input openapi.yaml --output src/<pkg>/models.py
   ```
   The output is a build artifact. Never hand-edit it — the next regeneration silently discards your change.
3. **Run contract tests.** They should fail; nothing implements the spec yet.
   ```bash
   uv run schemathesis run openapi.yaml --url http://localhost:8000
   ```
4. **Implement the handler** against the generated models until contract tests pass.
5. **Hand over to `tdd`** for behaviour.

## What each test layer is responsible for

`schemathesis` checks only that the implementation obeys the spec:

- responses match the declared schema
- no undeclared 500s
- declared constraints reject what they say they reject

**It does not check that the behaviour is correct.** An endpoint returning a well-formed, schema-valid, entirely wrong answer passes every contract test.

Business behaviour and regressions are hand-written tests, driven by `tdd`'s red-green-refactor. Write the cases that matter; there is no rule against hand-written tests here. Contract testing narrows the surface those tests have to cover — it does not replace them.

## Drift

Generated code drifts: someone edits the artifact, or amends the spec without regenerating. Guard it in CI and locally:

```bash
uv run datamodel-codegen --input openapi.yaml --output src/<pkg>/models.py && git diff --exit-code src/<pkg>/models.py
```

Non-empty diff means the committed artifact does not match the spec. Fix the spec or regenerate — never resolve it by editing the artifact.

## Changing a published contract

A breaking change to a published endpoint is a hard-to-reverse decision. It does not get made inline: record an ADR via `domain-modeling` first, then change the spec.
