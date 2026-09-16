# sphinx-covsight MVP

**Status:** for review
**Scope:** one vertical slice — specification rules → verification plan → covsight testplan v1
**Companions:** [`design.md`](design.md) (full data strategy),
[`../../sphinx_testplan_design.md`](../../sphinx_testplan_design.md) (plan-as-document feasibility),
[`waiver-schema.md`](../../../covsight-core/docs/waiver-schema.md) (waiver companion format)

---

## 1. What the MVP is

One path, working end to end, with nothing on it that cannot be demonstrated:

```
architecture spec (sphinx-needs)          ┐
  rules with stable IDs                   │
  published as needs.json + objects.inv   │
                                          ├──► verification plan (sphinx-covsight)
register map (SystemRDL / sphinx-peakrdl) │      features → envs → testpoints
RTL + testbench (sphinx-systemverilog)    ┘      each citing what it is accountable to
                                                          │
                                                          ▼
                                            covsight testplan v1 JSON/YAML
                                                  (deterministic, byte-stable)
```

The MVP proves three claims, and it is worth being explicit that these are the claims,
because each one is a place the approach could fail:

1. **A verification plan can be authored as a reviewable document** without losing the
   structure a tool needs. (The plan is prose a human reads *and* a graph a tool walks.)
2. **Citations to a specification can be by reference, validated at build time**, rather
   than copied text that silently rots. (§2.4 of the companion document measured the
   current scheme as positional and fragile; this replaces it.)
3. **Extraction to covsight testplan v1 is lossless for the MVP's authoring model** — the
   emitted plan is a first-class covsight object, not a format needing a converter.

### 1.1 Explicitly out of scope

Deferred deliberately, each to keep the MVP falsifiable in weeks rather than months:

| Deferred | Why it can wait |
|---|---|
| Reading coverage data (achievement, trend, uncovered bins) | The plan has value before any coverage exists — that is when plans are written. Needs the covsight-core reader and a store; §5 of `design.md` covers it |
| Waivers | Needs the waiver schema implemented in covsight-core first |
| Vendor plan export (VPF, hjson, VC Planner, Questa) | Writers do not exist in covsight-core yet (`design.md` §8.3). The MVP's job is to produce the schema those writers will consume |
| Closure checks against the coverage model | Requires the model side; the MVP checks plan-internal and plan→spec consistency only |
| `singlehtml` / PDF review channel | Free once the document set exists (`-b singlehtml`); not a code deliverable |
| Requirements-tool integration (JIRA et al.) | `requirements[]` is populated from spec citations in the MVP; external systems are additive |

### 1.2 The one external dependency

**covsight-core must add an `env` field to the testpoint schema.** This is the single
change outside this repository that the MVP requires, and it is called out here rather
than worked around because `custom` is the wrong long-term home for a plan's primary
organising axis (`design.md` §8.2).

```jsonc
// testpoints[] — additive, optional, backwards-compatible
"env": "ip_simulation"    // verification environment this testpoint executes in
```

Minimum viable form: a free-string field, no enumeration in the schema. Teams name their
own environments; covsight groups and filters by the string. An enumeration can be added
later without breaking readers, but guessing the enumeration now would be wrong — the set
differs per organisation (`ip_simulation`, `soc_simulation`, `formal`, `emulation`,
`fpga_prototype`, `silicon_bringup` all appear in surveyed plans).

Everything else the MVP needs — `goals[]`, `testpoints[]`, `coverage[]`, `requirements[]`,
`tags[]`, `custom{}` — already exists in the schema.

**Env-level metadata** (`scope`, `difficulty`, `coverage_score`, `approach`,
`exit_criteria`) goes in `custom.covsight` on the enclosing goal for the MVP. That is a
deliberate second-best: it keeps the external dependency to exactly one field, and the
data is derived from policy configuration rather than authored, so it is regenerable if
the schema later grows a home for it.

---

## 2. Authoring model

Five directives and one role. The selection rule from the companion document is unchanged:
*a construct earns a directive only if it needs identity, validation, or extraction.*

### 2.1 The directives

| Construct | Emits to | Why it earns a directive |
|---|---|---|
| `.. feature::` | `goals[]` | Identity (`id`), nestable, the review unit |
| `.. env::` | nested `goals[]` + `testpoints[].env` | The plan's second axis; carries policy-derived fields |
| `.. testpoint::` | `testpoints[]` | Identity, the extraction unit |
| `.. covers::` | `testpoints[].requirements[]` | Validation — every target is resolved or the build warns |
| `.. tests::` | `testpoints[].tests[]` | Extraction; substitution expansion |
| `:rule:` role | inline citation | Validation of inline references in prose |

Note what is **not** here. No `.. artifact::` — the companion document's artifact
descriptions would need `tests[]` to admit an object form, which is the *second* schema
gap, and the MVP holds itself to one. A testpoint's prose is its description; its
`.. tests::` list is names. If artifact-level prose proves necessary, that is the
argument for the `{name, desc}` object form, made with evidence.

No view directives (`.. coverage-summary::`, `.. gap-report::`) — those render data the
MVP does not read.

### 2.2 Worked example

```rst
.. feature:: Baud rate generation
   :id: FEAT-002

   The transmitter and receiver derive their bit clock from a programmable
   divisor. The divisor is writable while the link is idle and takes effect
   at the next character boundary.

   .. covers:: rule:UART/3.2.1, rule:UART/3.2.4, rdl:uart.CTRL.BAUD_DIV

   .. env:: ip_simulation
      :scope: block
      :difficulty: 3
      :coverage: 8

      .. testpoint:: All supported divisor values
         :id: FEAT-002.tp_divisors
         :stage: V2
         :priority: high

         Sweep the divisor across every supported baud rate and confirm
         bit timing at each, including the boundary values.

         .. covers:: rule:UART/3.2.1

         .. coverage::
            :covergroup: uart_env.uart_cfg_cg
            :coverpoint: uart_env.uart_cfg_cg.baud_div_cp

         .. tests:: uart_baud_{baud}_test, uart_baud_random_test

   .. env:: formal
      :scope: block
      :difficulty: 6
      :coverage: 4

      .. testpoint:: Divisor write during active transfer is ignored
         :id: FEAT-002.tp_divisor_locked
         :stage: V2

         .. covers:: rule:UART/3.2.4
```

What is **absent** is the point: no `approach`, no `reasoning`, no `exit_criteria`, no
`overall_score`, and no quoted specification text. Policy fields come from `conf.py` at
build time; citation text is resolved from the upstream catalog. A reviewer reading this
diff sees only decisions.

### 2.3 Citation targets

`.. covers::` accepts three prefixes. All three land in `requirements[]`, because all three
answer the same question — *what is this testpoint accountable to?*

| Prefix | Resolved against | `requirements[].system` |
|---|---|---|
| `rule:` | `needs.json` from the spec build | `spec` |
| `rdl:` | the compiled SystemRDL model (sphinx-peakrdl) | `rdl` |
| `sv:` | the SystemVerilog domain (sphinx-systemverilog) | `sv` |

Each emits `{system, item_id, url}` where `url` is the resolved anchor. An unresolvable
target is a warning by default and an error under `-W`; `covsight_strict_citations = True`
promotes it unconditionally, which is what CI should set.

**`rdl:` and `sv:` resolution is optional.** If the extension is not installed, those
targets are recorded without a `url` and a single informational message is emitted — the
build still succeeds. sphinx-covsight declares no hard dependency on either. This matters:
the plan must be authorable before the RTL exists.

### 2.4 Policy configuration

```python
# conf.py
covsight_env_policy = {
    'ip_simulation': {
        'title': 'IP Simulation',
        'approach': 'Boundary UVCs, directed sequences, constrained-random stimulus, '
                    'assertions, and a reference model targeting {feature}.',
        'reasoning': 'Provides controllability and observability for timing and data '
                     'bug classes at practical regression run time.',
        'exit_criteria': [
            '100% regression pass for all planned tests',
            '95%+ functional coverage for implemented scope',
            '100% assertion pass',
        ],
    },
    'formal': { ... },
}

covsight_score = lambda difficulty, coverage: (11 - difficulty) * coverage

covsight_substitutions = {'baud': ['9600', '115200', '460800']}
covsight_plan_name = 'uart'
covsight_needs_json = '_spec/needs.json'      # published by the spec build
covsight_strict_citations = False
covsight_output = '_build/testplan.json'
```

`{feature}` interpolates the enclosing feature title. Changing verification policy is a
one-line diff rather than an edit across every feature.

---

## 3. Extraction

### 3.1 Mapping

| Authored | covsight testplan v1 |
|---|---|
| `.. feature::` | `goals[]`: `id`, `title`, `desc`, `owner`, `tags` |
| `.. env::` | nested `goals[]` (`id` = `<feature-id>.<env>`, `title` from policy) + `testpoints[].env` |
| env policy fields | enclosing goal `custom.covsight`: `scope`, `difficulty`, `coverage_score`, `overall_score`, `approach`, `reasoning`, `exit_criteria` |
| `.. testpoint::` | `testpoints[]`: `name`, `desc`, `stage`, `priority`, `weight`, `tags`, `env` |
| `.. covers::` | `testpoints[].requirements[]` — `{system, item_id, url}` |
| `.. coverage::` | `testpoints[].coverage[]` — `{type, path}` |
| `.. tests::` | `testpoints[].tests[]`, after substitution expansion |
| `conf.py` substitutions | plan-level `substitutions{}` (recorded as well as applied) |
| — | `imports[]` is always empty; Sphinx composition is `toctree`, so extraction emits an already-merged plan |

A testpoint with no `.. tests::` extracts with `na: true`, matching OpenTitan's
`["N/A"]` convention. A feature with no testpoints extracts as a goal with
`status: "planned"`.

### 3.2 Determinism

The emitted file is byte-stable for a given source tree. This is a hard requirement, not
a nicety — a downstream audit that SHA-binds the artifact is the whole reason the
companion document raised it (§4.5).

- Keys sorted; arrays ordered by document order, then by `id` as tiebreak
- No timestamps, no absolute paths, no build host in the payload
- Provenance (build time, source commit) written to a **sidecar** `testplan.provenance.json`,
  so it never perturbs the hashed artifact
- JSON is the hashed artifact; YAML is emitted alongside for humans and is not hashed
- `covsight-testplan --check` re-extracts and diffs, for CI

### 3.3 Sphinx integration

Four hooks, and each has a known failure mode if omitted (companion §5.3):

| Hook | Omitting it causes |
|---|---|
| `env-purge-doc` | Duplicate entries on rebuild; deleted features never disappear |
| `env-merge-info` | Silent data loss under `-j auto` |
| `build-finished` (guard `exception is None`) | A failed build publishing a corrupt artifact |
| `env_version` bump | Stale unpickled data after any record-shape change |

`parallel_read_safe` is declared `True` only once `env-merge-info` is wired.

---

## 4. Documentation deliverables

Four guides plus a worked example. The guides are part of the MVP, not follow-on work —
a plan format nobody can author is not a deliverable.

| Document | Answers |
|---|---|
| `docs/guide/writing-a-spec.rst` | How to write an architecture spec whose rules are addressable: sphinx-needs setup, `rule` need type, ID scheme, what earns an ID and what does not |
| `docs/guide/extracting-rules.rst` | How the spec publishes `needs.json` + `objects.inv`, how the plan repo consumes them, cross-repo versioning, detecting stale citations |
| `docs/guide/writing-a-plan.rst` | The five directives, the env/policy split, citation prefixes, composition via `toctree` |
| `docs/guide/extracting-a-testplan.rst` | Running the extractor, the emitted schema, determinism and `--check`, feeding covsight |
| `docs/example/` | A small complete project — see below |

### 4.1 The example

Deliberately small. Large examples are not read.

```
docs/example/
├── spec/                       # a miniature architecture specification
│   ├── conf.py                 # sphinx-needs; publishes needs.json
│   └── uart.rst                # ~8 rules across 2 sections
├── rtl/
│   ├── uart_regs.rdl           # SystemRDL: CTRL (BAUD_DIV, PARITY_EN), STATUS
│   └── uart_cov.sv             # a covergroup and one test class, doc-commented
└── plan/
    ├── conf.py                 # sphinx-covsight + peakrdl + systemverilog
    ├── index.rst
    ├── feat_framing.rst        # FEAT-001, 2 envs
    └── feat_baud.rst           # FEAT-002, 2 envs (the §2.2 example)
```

Sizing target: ~8 rules, 2 features, 4 env blocks, 6 testpoints, 1 register, 1 covergroup,
1 test class. Small enough to read in full; large enough that every feature of the MVP
appears at least once.

The RDL and SV files exist so the example demonstrates **coexistence**: one documentation
set where the spec, the register map, the testbench source, and the plan all render
together and cross-reference. That is the unified-documentation claim made concrete, and
it costs two small source files to demonstrate. The `rdl:uart.CTRL.BAUD_DIV` citation in
§2.2 is the load-bearing line — it is the plan referring to a register by its compiled
model rather than by a string that happens to look like one.

One caution carried forward from `design.md` §3.6: SystemRDL paths and UCIS scope paths
are **different namespaces**. `rdl:` is a citation target, not a coverage selector, and
the MVP keeps them in separate fields for exactly that reason.

### 4.2 The example is also the test fixture

The example project builds in CI and its extracted testplan is committed as a golden
file. That makes every guide executable and catches determinism regressions for free.

---

## 5. Implementation

```
src/sphinx_covsight/
├── __init__.py          setup(), config values, hook registration
├── directives.py        feature, env, testpoint, covers, coverage, tests
├── roles.py             :rule:
├── model.py             the record dataclasses stored on env
├── citations.py         needs.json loader; rdl:/sv: resolution (optional)
├── policy.py            env policy expansion, score computation
├── extract.py           model → covsight testplan v1
├── emit.py              deterministic JSON/YAML writer + provenance sidecar
└── cli.py               covsight-testplan [--check]
tests/
├── test_directives.py
├── test_extract.py
├── test_determinism.py
└── test_example.py      builds docs/example, diffs against golden
```

Estimated 600–900 lines of extension code. The companion document estimated 400–600 for
the plan layer alone; citation resolution across three optional backends accounts for the
difference.

### 5.1 Milestones

| # | Deliverable | Done when |
|---|---|---|
| **M1** | Directives parse and render | The example plan builds; features and testpoints render as authored prose |
| **M2** | Extraction | `covsight-testplan` emits valid testplan v1; covsight reads it |
| **M3** | Determinism | Two clean builds produce identical bytes; `--check` in CI |
| **M4** | Spec citations | `rule:` resolves against `needs.json`; unresolvable targets warn; example spec builds and publishes |
| **M5** | RDL / SV citations | `rdl:` and `sv:` resolve when the extensions are present, degrade cleanly when not |
| **M6** | Guides | Four guides written against the working example |

M1–M3 are the spine; M4 is what distinguishes this from every existing plan format
(`design.md` §8.4). M5 is the smallest increment that demonstrates the unified-documentation
claim, and M6 is what makes any of it usable.

### 5.2 Acceptance criteria

1. The example project builds clean under `-W` with the spec's `needs.json` present.
2. Extracted testplan validates against `schema.covsight.io/testplan/v1` and loads in covsight.
3. Two consecutive clean builds are byte-identical; `--check` exits zero.
4. A deliberately broken citation (`rule:UART/9.9.9`) fails the build under `-W`.
5. Removing sphinx-peakrdl and sphinx-systemverilog from `conf.py` still builds and still
   extracts, with `rdl:`/`sv:` citations recorded without URLs.
6. Deleting a feature `.rst` and rebuilding incrementally removes it from the output.

Criterion 6 is the one most likely to be quietly broken; it is the `env-purge-doc` test.

---

## 6. Risks

| Risk | Handling |
|---|---|
| The `env` schema field slips in covsight-core | MVP can proceed on `custom.covsight.env` behind a config flag, with a one-line switch when the field lands. Do not let it block M2 |
| Cross-repo `needs.json` versioning | MVP pins a committed copy of the spec's `needs.json` under `docs/example/_spec/`. Live cross-repo consumption is a real problem (companion §6) but not an MVP problem |
| sphinx-peakrdl links by URL query parameter, not intersphinx inventory | Resolution is URL construction, not inventory lookup. Means `rdl:` targets cannot be *validated* against the model unless the RDL is compiled in the same build — so the MVP compiles it in the same build, and cross-build `rdl:` refs are unvalidated with a warning |
| Directive surface grows during implementation | The selection rule is the defence. Anything presentational is a view directive over the extracted graph, post-MVP |
| Plans authored before RTL exists cannot resolve `sv:`/`rdl:` | By design: optional resolution, graceful degradation. This is the normal case, not an edge case |

---

## 7. Open questions

1. **`env` as a testpoint field, or as the second level of the goal tree?** The MVP does
   both — nested goal *and* `env` string — which is redundant. It is the safe choice for
   an MVP but should collapse to one before v1.
2. **Should `.. coverage::` be in the MVP at all?** Nothing reads coverage data yet, so the
   bindings are unvalidated strings. Argument for keeping it: the bindings are authored
   knowledge that would otherwise be written twice, and they cost one directive. Argument
   against: unvalidated selectors rot. Currently in, on the first argument.
MSB: Likely not
3. **Feature ID scheme** — hierarchical (`FEAT-002.tp_divisors`) or opaque? The companion
   document raised this (§4.4) and did not settle it. The MVP uses hierarchical because it
   is readable in diffs; it makes renumbering expensive.
MSB: Likely hierarchical
4. **Where do artifact-level descriptions go** when a team needs them? This is the trigger
   for the `tests[]` object-form schema change; deferred until someone hits it.
5. **`covsight_score` as a lambda in `conf.py`** — flexible, but unhashable and
   unserialisable. Should policy be a data file instead, so the plan's provenance can
   record which policy version produced the scores?


---

## Appendix — mapping this MVP onto the full design

| `design.md` phase | MVP coverage |
|---|---|
| **A. Plan as document** | **Fully — this is the MVP** |
| B. Coverage model linkage | Not started; `.. coverage::` authored but unresolved |
| C. Test linkage | Names only; no reverse links or orphan report |
| D+ (waivers, trend, formal, registers-as-closure) | Not started; `rdl:` citation is the seed |
