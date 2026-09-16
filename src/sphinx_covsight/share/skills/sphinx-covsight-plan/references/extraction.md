# Extraction: the artifact, determinism, and the CI gate

## Running the extractor

The plan is written as a side effect of any documentation build:

```console
$ sphinx-build -b html docs/plan _build/html
$ ls _build/html/testplan.json _build/html/testplan.provenance.json
```

Or on its own, which is what a makefile that only wants the artifact should do:

```console
$ covsight-testplan build docs/plan -o testplan.json
$ covsight-testplan build docs/plan -o testplan.json -f both   # + YAML
$ covsight-testplan show  docs/plan --summary
$ covsight-testplan check docs/plan --against golden/testplan.json
```

Common options on every subcommand: `-c/--confdir`, `-W/--strict` (turn build
warnings into errors), `-v/--verbose` (show the Sphinx build log).

`build` runs a `dummy` builder in a temporary directory, so it produces the
artifact without producing documentation. If no plan is written it exits with
`error: no testplan was written; is sphinx_covsight in .../conf.py extensions?`

## The emitted schema

A `covsight testplan v1` object — not a format needing a converter.

```text
schema           "https://schema.covsight.io/testplan/v1"
format_version   1
name             covsight_plan_name
substitutions    the {key} bindings, recorded as well as applied
imports          always empty: composition happened at build time
goals[]          the feature tree
```

Each feature becomes a goal, each environment a nested goal, and each testpoint
lands in the goal for its environment:

```json
{
  "id": "FEAT-002",
  "title": "Baud rate generation",
  "desc": "The transmitter and receiver derive their bit clock ...",
  "goals": [
    {
      "id": "FEAT-002.ip_simulation",
      "title": "IP Simulation",
      "custom": {"covsight": {
        "env": "ip_simulation",
        "scope": "block",
        "difficulty": 3,
        "coverage_score": 8,
        "overall_score": 64,
        "approach": "Boundary UVCs, directed sequences, ...",
        "exit_criteria": ["100% regression pass for all planned tests"]
      }},
      "testpoints": [
        {
          "name": "FEAT-002.tp_divisors",
          "stage": "V2",
          "priority": "high",
          "desc": "Sweep the divisor across every supported baud rate ...",
          "tests": ["uart_baud_9600_test", "uart_baud_115200_test"],
          "source_template": "uart_baud_{baud}_test, uart_baud_random_test",
          "requirements": [
            {"system": "spec", "item_id": "UART_3_2_1",
             "url": "https://uart-spec.example/uart.html#UART_3_2_1"}
          ],
          "coverage": [
            {"type": "covergroup", "path": "uart_env.uart_cfg_cg"}
          ],
          "custom": {"covsight": {
            "env": "ip_simulation",
            "feature": "FEAT-002",
            "title": "All supported divisor values"
          }}
        }
      ]
    }
  ]
}
```

### Field by field

**`name`** — the testpoint's *id*, authored or derived as
`<feature-id>.<env>.<slug(title)>`. The human title lives in
`custom.covsight.title`, because testplan v1's `name` is the identifier.

**`desc`** — the directive body's prose, as **source text**. Rendering the
doctree back to text is lossy and non-deterministic; raw source is neither.
Downstream consumers render it themselves.

**`env`** — emitted twice, on purpose. The goal tree is the canonical structure
(it is what gives rollup, and what every vendor plan format maps onto); the
field is a denormalized index, so a consumer can filter "all formal testpoints"
without walking the tree. A build-time invariant keeps the two in agreement, and
a violation raises `covsight.internal`. Until covsight-core's schema carries the
field it is written to `custom.covsight.env`; `covsight_env_in_custom = False`
emits a top-level `env` instead.

**`na`** — `true` when a testpoint has no tests, matching OpenTitan's `["N/A"]`
convention.

**`requirements[]`** — one entry per `covers` target: `{system, item_id, url}`.
`system` is `spec`, `rdl` or `sv`. `url` is **absent** when the backend was
absent or the target did not resolve.

**`status`** — `"planned"` on a goal with no testpoints beneath it.

### What the MVP does not emit

No achievement data, no waivers, no vendor plan formats, no closure against a
coverage model. A plan has value before any coverage exists — that is when plans
are written.

## Determinism

The emitted JSON is byte-stable for a given source tree. That is a hard
requirement: it is what lets a downstream audit SHA-bind the artifact.

1. Goals and testpoints are ordered by **document order** — the order a reader
   meets them in, not alphabetical docname order.
2. `requirements[]`, `coverage[]` and `tags[]` are **sorted lexically**. They are
   sets, not sequences: authoring order carries no meaning, so sorting removes a
   diff source. Reordering tags in source does not change the output.
3. `tests[]` keeps **authored order** after expansion; expansion is cartesian
   over sorted substitution keys.
4. Every dict key is sorted at emit.
5. No timestamp, path, hostname or version goes into the hashed artifact.

**What correctly changes the output:** editing prose (`desc`), adding or removing
a citation, renaming a testpoint that has no explicit id, changing policy
(`approach`, `exit_criteria`, `overall_score`), changing a substitution list.

**What does not:** rebuilding, building incrementally, building with `-j 4`,
reordering set-valued fields, or moving a feature to a different file (only its
position in document order matters).

## The CI gate

```console
$ covsight-testplan check docs/plan --against golden/testplan.json
golden/testplan.json: up to date
```

Exit 1 on drift, with a **structural** diff — a byte diff on a 400-testpoint
plan is unreadable:

```text
testplan.json: 1 difference(s)
  goals[1].goals[0].testpoints[0].tests[0]: 'uart_smoke_test' -> 'uart_sanity_test'
```

Exit 2 if the reference file does not exist.

This catches two different problems with the same symptom: someone edited the
committed artifact without regenerating it, and the build stopped being
deterministic.

A minimal workflow:

```yaml
- run: sphinx-build -W -b html docs/spec _build/spec
- run: sphinx-build -W -b html docs/plan _build/plan
- run: covsight-testplan check docs/plan --against golden/testplan.json
- run: |
    covsight-testplan build docs/plan -o /tmp/a.json
    covsight-testplan build docs/plan -o /tmp/b.json
    cmp /tmp/a.json /tmp/b.json
```

## The provenance sidecar

Everything that would perturb the hash lives next door, in
`testplan.provenance.json`:

```json
{
  "generated_at": "2026-09-16T02:03:23.726446+00:00",
  "source_commit": "7a541c430be38fe01c54c83dee830c31c69a5ae3",
  "sphinx_covsight_version": "0.1.0",
  "policy_sha256": "802b9548...",
  "score_expression": "(11 - difficulty) * coverage",
  "needs_json_sha256": "c1f0...",
  "citation_backends": {"rdl": true, "rule": true, "sv": true},
  "counts": {"goals": 6, "testpoints": 6, "requirements": 10,
             "coverage": 6, "tests": 10},
  "testplan_sha256": "54f88d01..."
}
```

What to audit, in order of how often it matters:

- **`citation_backends`** — if `rdl` or `sv` is `false`, those citations in this
  artifact have no urls. The plan is still correct; it is less linked than it
  looks.
- **`policy_sha256` / `score_expression`** — every `overall_score`, `approach`
  and `exit_criteria` derives from these. A score that changed with no source
  diff means the policy changed.
- **`needs_json_sha256`** — which specification snapshot the citations resolved
  against.
- **`source_commit`** — the plan source the artifact was built from; `null`
  outside a git repository.

## Monitoring citation health

```console
$ covsight-testplan show docs/plan --summary
plan:         uart
coverage:     6
goals:        6
requirements: 10
testpoints:   6
tests:        10
citations:    10/10 resolved
```

Gradual drift away from 100% is how citation rot looks before anyone notices it.

## Consuming the plan

```python
from covsight.core.ncdb.testplan import Testplan, iter_testpoints

plan = Testplan.load("testplan.json")
for tp in iter_testpoints(plan):
    print(tp.name, tp.stage, tp.tests)
```

sphinx-covsight declares **no dependency** on covsight-core — it writes the
schema, it does not import the reader — so a plan project installs and builds
without it.
