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
   uv run datamodel-codegen --input openapi.yaml --input-file-type openapi --output src/<pkg>/models.py --output-model-type pydantic_v2.BaseModel --target-python-version 3.12 --disable-timestamp
   ```
   `--disable-timestamp` is **required**, not cosmetic: without it the generator stamps the current time into the file, every regeneration differs, and the drift check below can never pass.

   The output is a build artifact. Never hand-edit it — the next regeneration silently discards your change.
3. **Run contract tests.** They should fail; nothing implements the spec yet.
4. **Implement the handler** against the generated models until contract tests pass.
5. **Hand over to `tdd`** for behaviour.

## Contract tests

No server required — bind the spec to the ASGI app directly:

```python
import schemathesis
from <pkg>.app import app

schema = schemathesis.openapi.from_path("openapi.yaml")
schema.app = app


@schema.parametrize()
def test_api_obeys_its_contract(case):
    case.call_and_validate()
```

Cases are generated from the spec; do not write them by hand.

Expect the first run to flag status codes your framework emits but the spec never declared — FastAPI answers an unparseable body with `400`, which a spec written by hand will almost always have missed. That is the contract test doing its job. **Fix the spec or the handler; never loosen the test.**

## What each test layer is responsible for

`schemathesis` checks only that the implementation obeys the spec:

- responses match the declared schema
- no undeclared status codes, no undeclared 500s
- declared constraints reject what they say they reject

**It does not check that the behaviour is correct.** An endpoint returning a well-formed, schema-valid, entirely wrong answer passes every contract test — a handler that stores the title it was given and one that stores `"placeholder"` are indistinguishable to the contract.

Business behaviour and regressions are hand-written tests, driven by `tdd`'s red-green-refactor. Write the cases that matter; there is no rule against hand-written tests here. Contract testing narrows the surface those tests have to cover — it does not replace them.

## Drift

Generated code drifts: someone edits the artifact, or amends the spec without regenerating. Guard it in CI and locally — regenerate, then demand no diff:

```bash
uv run datamodel-codegen --input openapi.yaml --input-file-type openapi --output src/<pkg>/models.py --output-model-type pydantic_v2.BaseModel --target-python-version 3.12 --disable-timestamp && git diff --exit-code src/<pkg>/models.py
```

Non-empty diff means the committed artifact does not match the spec. Fix the spec or regenerate — never resolve it by editing the artifact.

Generated files are excluded from the project's lint and format rules. They are artifacts, not source: their style is the generator's business, and a rule you cannot fix without hand-editing the file is a rule that will be broken.

## Changing a published contract

A breaking change to a published endpoint is a hard-to-reverse decision. It does not get made inline: record an ADR via `domain-modeling` first, then change the spec.
