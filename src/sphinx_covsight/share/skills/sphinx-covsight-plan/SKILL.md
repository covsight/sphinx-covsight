---
name: sphinx-covsight-plan
description: Author a verification plan with the sphinx-covsight Sphinx extension - the feature/env/testpoint/covers/coverage/tests directives in both reStructuredText and MyST, testpoint id derivation, the rule:/rdl:/sv: citation prefixes, UCIS coverage-binding paths, conf.py policy (covsight_env_policy, covsight_score, covsight_substitutions, covsight_needs_json, covsight_strict_citations), extracting a deterministic covsight testplan v1 JSON with covsight-testplan build/check/show, the provenance sidecar, and diagnosing covsight.* build warnings. Use when a Sphinx project lists sphinx_covsight in extensions, when a page contains a feature/env/testpoint/covers/coverage/tests directive, when asked to write or review a verification plan or testplan, or when a build emits a covsight.* warning.
---

# sphinx-covsight: authoring a verification plan

A verification plan authored as a Sphinx document renders as a reviewable
document **and** extracts as a machine-readable `covsight testplan v1` JSON.
One source, two consumers — that is the whole premise, and it is why the
extracted artifact must be byte-deterministic.

The specification side (rules with stable ids, `needs.json`) is a separate
project and a separate skill: `sphinx-covsight-spec`.

## The shape of a plan

Three nested constructs, three leaf ones:

```
feature                 what is being verified, and what it is accountable to
  env                   where it is verified
    testpoint           one verification task
      covers            what this testpoint is accountable to
      coverage          which coverage objects close it
      tests             which tests exercise it
```

Nesting is enforced (`covsight.nesting`):

| Directive | May appear in |
|---|---|
| `feature` | document root, or another `feature` |
| `env` | `feature` |
| `testpoint` | `env`, or `feature` directly |
| `covers` | `feature`, `testpoint` |
| `coverage`, `tests` | `testpoint` |

**A construct earns a directive only if it needs identity, validation, or
extraction.** Everything else is prose — and prose is the majority of a good
plan. Do not wrap explanation in a directive to make it look structured.

## The six directives

```rst
.. feature:: Baud rate generation
   :id: FEAT-002
   :owner: uart-verification
   :tags: uart, baud

   The transmitter and receiver derive their bit clock from a programmable
   divisor.

   .. covers::
      rule:UART_3_2_1, rule:UART_3_2_2,
      rdl:uart.CTRL.BAUD_DIV

   .. env:: ip_simulation
      :scope: block
      :difficulty: 3
      :coverage: 8

      .. testpoint:: All supported divisor values
         :id: FEAT-002.tp_divisors
         :stage: V2
         :priority: high

         Sweep the divisor across every supported baud rate and confirm bit
         timing at each, including the boundary values 2 and 65535.

         .. covers:: rule:UART_3_2_1, rule:UART_3_2_2

         .. coverage::
            covergroup: uart_env.uart_cfg_cg
            coverpoint: uart_env.uart_cfg_cg.baud_div_cp

         .. tests:: uart_baud_{baud}_test, uart_baud_random_test
```

Every option of every directive: `references/directives.md`.

### `feature` — the review unit

`:id:` is **required, authored, and stable**: it is what survives retitling and
what anything external references. Features may nest; a feature whose children
carry the content is not itself expected to have testpoints.

### `env` — the second axis

The same feature verified in simulation and in formal is **two environments,
not two features**. `env` carries only the numbers that drive scoring —
`:scope:`, `:difficulty:`, `:coverage:`, and an optional `:title:` override.

What is *absent* is the design: no approach, no reasoning, no exit criteria.
Those come from `covsight_env_policy` in `conf.py`, so changing verification
policy is a one-line diff rather than an edit across every feature. **If you
find yourself writing approach prose into an `env` body, it belongs in the
policy.**

### `testpoint` — the extraction unit

`:id:` is **optional**, derived as `<feature-id>.<env>.<slug(title)>` when
omitted — the right default, since testpoint ids are numerous and nobody wants
to hand-maintain them. A derived id changes when the testpoint is retitled or
moved between environments, which shows up in the extracted diff: the right
place for it to be visible.

Write an explicit `:id:` for any testpoint something external references. Set
`covsight_require_explicit_testpoint_ids = True` to be warned about every
derived one (for teams that SHA-bind at testpoint granularity).

A testpoint with no `tests` extracts with `na: true` and warns
(`covsight.testpoint-unmapped`). If that is deliberate, say so with `:na:` —
which is how "we never wrote the test" stops being invisible. **Do not silence
this class globally to clean up a log.**

### `covers` — the three citation prefixes

All three answer one question, *what is this accountable to?*, so all three land
in `requirements[]`:

| Prefix | Resolved against | Absent when |
|---|---|---|
| `rule:` | `needs.json` from the specification | `covsight_needs_json` unset |
| `rdl:` | the compiled SystemRDL model | sphinx-peakrdl not installed |
| `sv:` | the SystemVerilog domain | sphinx-systemverilog not installed |

When a backend is absent the citation is **still recorded** — without a url —
and the build emits one informational message for the whole backend, not one
per citation. That is what makes it reasonable to cite RTL that does not exist
yet, which is the normal case rather than an edge case.

The inline role `` :rule:`UART_3_2_1` `` renders a link in prose but is **not**
extracted into `requirements[]`: a citation mid-sentence is evidence, not an
accountability claim. Use `covers` for accountability. (`rdl:` and `sv:` have no
covsight inline role — their own extensions already provide `:rdl:doc-ref:`,
`:sv:class:` &c.)

### `coverage` — and the namespace trap

One `<type>: <path>` binding per line. Types: `covergroup`, `coverpoint`,
`cross`, `assertion`, `expression`, `toggle`, `line`, `branch`, `functional`.

**The single easiest mistake in this extension:** a `coverage` path is a **UCIS
instance path** — where the object lives in the coverage database — while an
`sv:` citation names a **SystemVerilog declaration path**. `uart_env.uart_cfg_cg`
is an instance; `uart_pkg::uart_cfg::uart_cfg_cg` is a declaration. Both are
correct, and they are not interchangeable.

Because of that, validation checks the **leaf name only**, against the `sv`
domain, and only for `covergroup` and `coverpoint` (the domain has no object
kind for the rest, so checking them would report every one as missing). A miss
is a warning, never an error, and suppressible with
`covsight_validate_coverage_bindings = False`.

### `tests`

Test names with `{key}` placeholders expanded from `covsight_substitutions`.
With `{"baud": ["9600", "115200", "460800"]}`, one `uart_baud_{baud}_test` line
extracts as three names, and the unexpanded template is preserved in
`source_template`. Multiple keys expand cartesian-wise over **sorted** key
names, so the result never depends on dict ordering.

## Writing in MyST

One directive implementation serves both formats, constrained by two rules that
shape the directive design rather than your authoring:

1. **No repeated options** — a duplicated option key is a hard error in RST and
   is *silently dropped* in MyST. Hence list-valued inputs take a body.
2. **No MyST YAML-block options** — not valid RST, and list values arrive
   flattened anyway.

Markdown fences must be strictly longer than what they contain, so three colon
levels needs `:::::` → `::::` → `:::`. Two conventions keep that manageable:

- **Leaf directives use backtick fences** (```` ```{covers} ````) — backtick and
  colon fences nest independently, which buys a free level.
- **One feature per file** — the composition model anyway, so depth tops out at
  four.

```markdown
:::::{feature} Character framing
:id: FEAT-001

Prose.

```{covers}
rule:UART_1_1_1
```

::::{env} ip_simulation
:difficulty: 3

:::{testpoint} Start bit qualification
:stage: V1

```{tests}
uart_smoke_test
```
:::
::::
:::::
```

Requires `myst_enable_extensions = ["colon_fence"]`.

## conf.py

```python
extensions = ["myst_parser", "sphinx_covsight"]   # + sphinx_systemverilog, sphinx_peakrdl

covsight_plan_name = "uart"
covsight_needs_json = "_spec/needs.json"          # relative to conf.py
covsight_spec_base_url = "https://uart-spec.example/"
covsight_substitutions = {"baud": ["9600", "115200", "460800"]}

covsight_env_policy = {
    "ip_simulation": {
        "title": "IP Simulation",
        "approach": "Constrained-random stimulus and assertions targeting {feature}.",
        "reasoning": "Controllability and observability at practical regression run time.",
        "exit_criteria": ["100% regression pass", "95%+ functional coverage"],
    },
}
covsight_score = "(11 - difficulty) * coverage"
```

`{feature}` interpolates the enclosing feature's title and `{env}` the
environment name, in `approach` and `reasoning`. Any other placeholder is a
configuration error raised once at `builder-inited`, not per feature.

`covsight_score` is an **expression string, not a lambda** — a restricted
arithmetic expression over `difficulty` and `coverage`. Calls, attribute access,
subscripts, comprehensions and the walrus operator are rejected at compile time
(a doc build runs in CI on arbitrary branches, so an `eval` reaching
`__import__` is a real vulnerability). A string is also hashable into the
provenance sidecar, which is what makes derived scores auditable.

Policy may equally live in a YAML file via `covsight_env_policy_file`; the two
forms are mutually exclusive and produce identical `policy_sha256` for identical
content.

All 18 config values: `references/config.md`.

## Composition

There is no plan-level import mechanism, because Sphinx already has one: the
`toctree`. Extraction walks the whole project and emits an already-merged plan,
so `imports[]` in the output is always empty.

## Extracting

```console
$ sphinx-build -b html docs/plan _build/html      # writes testplan.json as a side effect
$ covsight-testplan build docs/plan -o testplan.json          # artifact only, no HTML
$ covsight-testplan build docs/plan -o testplan.json -f both  # + YAML for humans
$ covsight-testplan show  docs/plan --summary
$ covsight-testplan check docs/plan --against golden/testplan.json    # the CI gate
```

JSON is the hashed artifact; YAML is for humans and is not what gets hashed.
`check` exits 1 on drift with a **structural** diff (`goals[1].goals[0].testpoints[0].tests[0]:
'uart_smoke_test' -> 'uart_sanity_test'`) — a byte diff on a 400-testpoint plan
is unreadable. It catches two different problems with the same symptom: someone
edited the artifact without regenerating it, and the build stopped being
deterministic.

Watch the last line of `show --summary`: `citations: 10/10 resolved`. Gradual
drift away from 100% is how citation rot looks before anyone notices it.

The emitted schema, the determinism rules, and the provenance sidecar:
`references/extraction.md`.

## Rules that are easy to get wrong

1. **A `coverage` path is a UCIS instance path, an `sv:` citation is a
   declaration path.** Different namespaces. See above.
2. **Approach and exit criteria are policy, not prose.** If two features
   describe their simulation approach in their own words, the plan has lost the
   property that made policy worth centralising.
3. **Don't hand-write testpoint ids by default.** Derived ids are correct for
   the majority; explicit ids are for testpoints something external names.
4. **An unmapped testpoint is information, not noise.** Mark it `:na:` when
   deliberate; never blanket-suppress `covsight.testpoint-unmapped`.
5. **Write citations for objects that do not exist yet.** `rdl:` and `sv:`
   targets extract as recorded requirements without urls and start resolving the
   day the RTL lands in the same documentation set. Same for coverage bindings
   for covergroups nobody has coded — that is authored knowledge which would
   otherwise be written twice.
6. **Set `covsight_strict_citations = True` in CI**, so a deleted specification
   rule fails the plan's build. It does *not* affect the absent-backend case, so
   it is safe even for a plan that cites RTL that does not exist.
7. **`covsight_env_in_custom` changes the emitted artifact.** Flip it
   deliberately and regenerate the golden.

## Diagnosing

Every message carries a stable subtype, so a class can be silenced:

```python
suppress_warnings = ["covsight.coverage-binding"]
```

Subtypes: `nesting`, `duplicate-id`, `testpoint-unmapped`, `empty-goal`,
`substitution`, `missing-policy`, `citation-id-charset`, `citation-unresolved`,
`citation-syntax`, `coverage-binding`, `backend-absent`, `config`, `internal`.
The names are public interface — renaming one is a breaking change for anyone
who has suppressed it.

Symptom → cause → fix: `references/troubleshooting.md`.

## Verifying your work

```console
$ sphinx-build -W -b html docs/plan _build/plan        # warnings are errors
$ covsight-testplan build docs/plan -o /tmp/a.json
$ covsight-testplan build docs/plan -o /tmp/b.json
$ cmp /tmp/a.json /tmp/b.json                          # determinism is a hard requirement
```

## Reference files

| File | Covers |
|---|---|
| `references/directives.md` | Every directive, argument and option; coverage binding types; roles. |
| `references/config.md` | All `covsight_*` config values with defaults, and the extensions that interact. |
| `references/extraction.md` | The emitted testplan v1 schema field by field, the determinism rules, the CI gate, the provenance sidecar. |
| `references/troubleshooting.md` | Build symptom → cause → fix, per warning subtype. |

Published documentation: <https://dvkit.org/covsight/sphinx-covsight/>
