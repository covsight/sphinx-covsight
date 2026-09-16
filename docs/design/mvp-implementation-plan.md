# sphinx-covsight MVP — Implementation, Test, and Documentation Plan

**Status:** for review / tracking
**Implements:** [`mvp-design.md`](mvp-design.md)
**Context:** [`design.md`](design.md) · [`../../sphinx_testplan_design.md`](../../sphinx_testplan_design.md)

This document is the working plan. Section 1 closes the design's open questions so
implementation is unblocked; sections 2–4 specify the code, tests, and documentation;
section 5 is the tracked work breakdown.

---

## 1. Decisions taken on the open questions

Each open question from `mvp-design.md` §7 is closed here with an assumption, a rationale,
and — where the decision could turn out wrong — the signal that would reverse it. None of
these are irreversible before v1.

### D1 — `env` is emitted twice, and that is intentional

**Decision.** Extraction emits both a nested goal per environment *and* a
`testpoints[].env` string. The goal tree is the **canonical structure**; the field is a
**denormalized index**.

**Rationale.** They serve different consumers. The goal tree is what gives rollup and what
every vendor format maps onto; the field is what lets a consumer filter "all formal
testpoints" without walking the tree, and it is the field covsight-core is being asked to
add. Collapsing to one would penalise one consumer to tidy the schema.

**Invariant, enforced by test.** For every testpoint, `env` equals the `env` of its nearest
enclosing env goal. `test_extract.py::test_env_denormalization_consistent` asserts it on
the example and on a synthetic three-level nesting.

**Reversal signal.** If the two ever disagree in a way the invariant test does not catch —
i.e. if a legitimate authoring pattern produces a testpoint outside any env goal — collapse
to the field alone.

### D2 — `.. coverage::` stays, and gains partial validation

**Decision.** Keep the directive. When sphinx-systemverilog is present, validate the
**leaf covergroup/coverpoint type name** against the `sv` domain; warn on no match.

**What changed since the design doc.** Inspection of `sphinx_systemverilog/domain.py`
shows the domain maintains `objects: fullname -> (docname, anchor, kind)` with
`covergroup` and `coverpoint` among the object kinds, plus a `candidates(target)` helper
that matches on the final `::`-separated segment. So the bindings are not entirely
unvalidated after all, which was the whole argument against including them.

**The limit, stated precisely.** The `sv` domain keys on **SystemVerilog declaration
paths** (`uart_pkg::uart_cfg_cg`, `.` normalized to `::`). `.. coverage::` paths are
**UCIS instance paths** (`uart_env.uart_cfg_cg`). These are different namespaces — the
same trap as SystemRDL vs UCIS in `design.md` §3.6. Therefore:

- Validation is **leaf-name only**, via the domain's own `candidates()` matching rule.
- A miss is a warning (`covsight.coverage-binding`), never an error, and is suppressible.
- Full instance-path validation is a post-MVP job for the coverage-model reader.

**Config.** `covsight_validate_coverage_bindings = True` (no-op when the extension is absent).

### D3 — Hierarchical IDs, with testpoint IDs auto-derived

**Decision.** Feature IDs are authored and opaque-ish (`FEAT-002`). Testpoint IDs are
hierarchical and **optional** — when omitted, derived as
`<feature-id>.<env>.<slug(title)>`.

**Rationale.** Authored feature IDs are stable across retitling, which is what renumbering
pain is actually about. Testpoint IDs are numerous and are the ones nobody wants to
hand-maintain; deriving them removes the bulk of the cost while keeping them explicit in
the output. An author who needs a stable testpoint ID can still write one.

**Consequence accepted.** A derived ID changes if the testpoint is retitled or moved
between envs. That is visible in the extracted diff, which is the right place for it to
be visible. `covsight_require_explicit_testpoint_ids = False` flips this for teams that
SHA-bind at testpoint granularity.

**Deferred.** An alias map (`covsight_id_aliases`) for renumbering. Not needed until
something external references these IDs.

### D4 — No artifact-level descriptions

**Decision.** Unchanged from the design: no `.. artifact::`. Confirmed as the boundary
that keeps the external dependency at exactly one schema field.

### D5 — Policy is data, and its hash is recorded

**Decision.** Replace the `conf.py` lambda with two things:

1. `covsight_score` is a **restricted arithmetic expression string**, default
   `"(11 - difficulty) * coverage"`, evaluated over a fixed variable set by a small
   AST-walking evaluator (literals, names from a whitelist, `+ - * / // % ** ()`, unary
   minus — no calls, no attributes, no subscripts, no comprehensions).
2. `covsight_env_policy` may be given inline **or** as `covsight_env_policy_file`
   (YAML). Either way it is canonicalized and hashed, and
   `policy_sha256` + `score_expression` go into the provenance sidecar.

**Rationale.** The design flagged that a lambda is unhashable and unserialisable, so
provenance cannot record which policy produced the scores. Since the scores are derived
data, provenance is the only thing that makes them auditable. An expression string is the
smallest change that fixes it without inventing a policy language.

**Rejected alternative.** Keeping the lambda and hashing its bytecode — bytecode is not
stable across Python versions, so the hash would churn for no semantic reason.

### D6 — Housekeeping decisions not in the design doc

| # | Decision | Rationale |
|---|---|---|
| D6.1 | Distribution `sphinx-covsight`, package `sphinx_covsight`, `src/` layout, `pyproject.toml` with hatchling | Matches the empty `src/`+`tests/` skeleton already in the repo |
| D6.2 | Python ≥ 3.10, Sphinx ≥ 7.0 (dev pin: 3.12 / Sphinx 9.1, per `packages/`) | `match` and PEP 604 unions are used; Sphinx 7 is the oldest with stable typing for `Domain` |
| D6.3 | Hard deps: `sphinx`, `pyyaml`. Optional extras: `sv` → sphinx-systemverilog, `rdl` → sphinx-peakrdl, `docs` → both + furo | Optional-by-design citation resolution (§2.3 of the design) must be structurally enforced, not just intended |
| D6.4 | **No dependency on covsight-core in the MVP.** Extraction writes the schema; it does not import the reader | Keeps the MVP installable and testable standalone. A `covsight` extra is added at M2 purely for the round-trip test |
| D6.5 | Warnings all carry a `type="covsight"` and a subtype, so `suppress_warnings` works at useful granularity | Sphinx convention; needed for the degradation story to be usable |
| D6.6 | Emitted schema version pinned to `https://schema.covsight.io/testplan/v1`, `format_version: 1` | — |

### D7 — The directive syntax contract is format-neutral (RST and MyST)

**Decision.** Both RST and MyST/Markdown are supported, with **one** directive
implementation. To keep that true, the syntax contract is constrained:

- **No repeated options** — they error in RST and are silently dropped in MyST.
- **No MyST YAML-block options** — not valid RST, and lists arrive flattened anyway.
- **List-valued inputs take a directive body**, one item per line (`covers`, `coverage`,
  `tests`).
- No construct that depends on RST indentation semantics.

**Rationale and evidence:** [`myst-authoring.md`](myst-authoring.md). Verified against
myst-parser 5.1.0 — nesting, spaced arguments, roles, raw body capture, exact line
numbers, mixed `.rst`/`.md` projects, and sphinx-needs under MyST all work unchanged.

**Enforced by test**, not by discipline: every extraction test runs against an RST root
and a MyST root and asserts identical extracted plans.

---

## 2. Implementation specification

### 2.1 Module map

```
src/sphinx_covsight/
├── __init__.py       setup(), config values, hook wiring, env_version
├── model.py          record dataclasses + the env store
├── directives.py     feature, env, testpoint, covers, coverage, tests
├── roles.py          :rule:
├── policy.py         env policy loading, score expression evaluator
├── citations.py      CitationResolver + three backends
├── extract.py        model -> testplan v1 dict
├── emit.py           canonical JSON/YAML writer, provenance sidecar
├── checks.py         build-time validations
├── logging.py        warning helpers with stable subtypes
└── cli.py            covsight-testplan entry point
```

### 2.2 `model.py` — the stored records

Plain dataclasses, picklable, no docutils nodes retained (the environment is pickled, so
nodes stored there bloat and break rebuilds).

```python
@dataclass
class Citation:
    kind: str            # "rule" | "rdl" | "sv"
    target: str          # text after the prefix, verbatim
    docname: str
    lineno: int
    url: str | None = None      # filled during resolution
    title: str | None = None

@dataclass
class CoverageBinding:
    type: str            # covergroup | coverpoint | cross | assertion | ...
    path: str
    desc: str = ""

@dataclass
class TestpointRecord:
    id: str
    title: str
    desc: str                     # rendered from the directive body
    feature_id: str
    env: str | None
    stage: str | None
    priority: str | None
    weight: int = 1
    tags: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)   # pre-expansion
    coverage: list[CoverageBinding] = ...
    citations: list[Citation] = ...
    docname: str = ""
    lineno: int = 0
    order: int = 0                # document order, for deterministic sort

@dataclass
class EnvRecord:
    env: str
    feature_id: str
    scope: str | None
    difficulty: int | None
    coverage_score: int | None
    docname: str
    order: int

@dataclass
class FeatureRecord:
    id: str
    title: str
    desc: str
    owner: str | None
    tags: list[str]
    parent_id: str | None         # features may nest
    citations: list[Citation]
    docname: str
    order: int
```

Stored as `env.covsight_plan: PlanStore` with `features`, `envs`, `testpoints` keyed by
docname so `env-purge-doc` is a single `pop`.

`env_version = 1`, bumped on any change to these shapes.

### 2.3 `directives.py`

All six share a small base handling the `order` counter, docname/lineno capture, and
nesting detection.

**Nesting is tracked with an explicit stack on the Sphinx environment**, not inferred from
the doctree. Inferring from node parentage is the tempting approach and it breaks the
moment a directive appears inside a `only::` or a container.

| Directive | Arg | Options | Body | Nests in |
|---|---|---|---|---|
| `feature` | title | `:id:` (req), `:owner:`, `:tags:`, `:status:` | prose + children | doc, `feature` |
| `env` | env name | `:scope:`, `:difficulty:`, `:coverage:`, `:title:` | prose + children | `feature` |
| `testpoint` | title | `:id:`, `:stage:`, `:priority:`, `:weight:`, `:tags:`, `:na:` | prose + children | `env`, `feature` |
| `covers` | — | — | comma/newline-separated targets | `feature`, `testpoint` |
| `coverage` | — | — | `<type>: <path>` per line | `testpoint` |
| `tests` | — | — | comma/newline-separated names | `testpoint` |

Notes that will otherwise be discovered the hard way:

- **`coverage` is body-parsed, not option-parsed** — one `<type>: <path>` per line.
  Repeated options were the original design and **do not work in either format**: RST
  raises a hard error from `extract_extension_options` before the directive is
  instantiated (so `option_spec` cannot intercept it), and MyST silently keeps only the
  last value. Verified both ways; see [`myst-authoring.md`](myst-authoring.md) §3. The
  body form is also better on its own merits — order is preserved, and it matches `covers`
  and `tests`, which already take bodies.
- **`covers` takes a body, not an argument**, so long citation lists wrap cleanly. A
  single-line argument form is also accepted for the common one-citation case.
- **Description rendering.** The directive body is parsed into the doctree for display and
  *separately* captured as raw source text for `desc` in the extracted plan. Serialising
  the rendered doctree back to text is lossy and non-deterministic; raw source is neither.
  Consequence: `desc` in the plan is RST source, which is correct — covsight's schema says
  descriptions are Markdown-ish prose and downstream consumers render it themselves.
- **Misnesting is an error, not a warning** (`covsight.nesting`): an `.. env::` outside a
  feature has nowhere to attach and would silently vanish from extraction.

### 2.4 `citations.py`

```python
class CitationResolver:
    def resolve(self, c: Citation) -> Citation      # returns with url/title filled
    def report_unresolved(self) -> None
```

Three backends, each independently optional:

| Backend | Mechanism | Absent when |
|---|---|---|
| `rule:` | Loads `covsight_needs_json` once at `builder-inited`; index by need `id`; body text is in `content` (**not** `description`); `url = f"{covsight_spec_base_url}{need['docname']}.html#{need['id']}"` | File not configured or not found |
| `sv:` | `env.get_domain("sv").objects` exact hit, else `candidates()` leaf match | sphinx-systemverilog not installed |
| `rdl:` | sphinx-peakrdl's compiled model; link built as URL + query parameter | sphinx-peakrdl not installed |

**Resolution runs at `doctree-resolved`, not at parse time.** The `sv` and `rdl` domains
are not fully populated until all documents are read, so parse-time resolution would
produce spurious misses on incremental builds.

**Degradation ladder**, matching the design's graceful-degradation requirement:

| Situation | Behaviour |
|---|---|
| Backend present, target resolves | `url` + `title` filled |
| Backend present, target missing | warning `covsight.citation-unresolved`; recorded without `url` |
| Backend absent | **one** informational message per backend per build; recorded without `url`, no per-citation noise |
| `covsight_strict_citations = True` | the first two rows' warnings become errors |

The "one message per backend" rule matters — a plan with 400 `rdl:` citations built
without sphinx-peakrdl must not emit 400 warnings, or the mode becomes unusable and
people stop authoring the citations.

**`rdl:` validation caveat carried from the design.** Because sphinx-peakrdl links by URL
query parameter rather than an intersphinx inventory, a `rdl:` target can only be
*validated* when the RDL is compiled in the same build. Cross-build refs resolve to a URL
but are marked `validated: false` internally and reported once in the build summary.

### 2.5 `policy.py`

- `load_policy(app)` → `dict[str, EnvPolicy]` from inline config or YAML file.
- `EnvPolicy`: `title`, `approach`, `reasoning`, `exit_criteria: list[str]`.
- `{feature}` / `{env}` interpolation over `approach` and `reasoning`; unknown placeholders
  are a config error, caught once at `builder-inited` rather than per-feature.
- `ScoreExpression`: compile once with `ast.parse(mode="eval")`, walk and reject any node
  outside the whitelist, then `compile()`. Variables: `difficulty`, `coverage`. Division by
  zero and non-finite results are a config error.
- `policy_fingerprint()` → sha256 over canonical JSON of the policy dict plus the score
  expression string.

### 2.6 `extract.py` / `emit.py`

`extract(store, policy, config) -> dict` builds the plan per the §3.1 mapping table of the
design doc. Ordering rules, which are the substance of determinism:

1. Goals ordered by `(docname, order)` — document order within the toctree.
2. Testpoints ordered by `(feature_id, env, order)`.
3. `requirements[]`, `coverage[]`, `tags[]` sorted lexically. **These are sets, not
   sequences** — authoring order carries no meaning, so sorting them removes a diff source.
4. `tests[]` keeps authored order after substitution expansion; expansion is cartesian over
   sorted substitution keys.
5. All dict keys sorted at emit.

`emit.py`:

- `write_json(path, plan)` — `json.dumps(sort_keys=True, ensure_ascii=False, indent=2)`, LF, trailing newline.
- `write_yaml(path, plan)` — `yaml.safe_dump(sort_keys=True, default_flow_style=False, allow_unicode=True)`.
- `write_provenance(path, ...)` — sidecar `testplan.provenance.json` with `generated_at`,
  `source_commit` (via `git rev-parse HEAD`, best-effort, `null` outside a repo),
  `sphinx_covsight_version`, `policy_sha256`, `score_expression`, `needs_json_sha256`,
  `citation_backends: {rule: bool, sv: bool, rdl: bool}`, `counts`.

**No timestamp, path, hostname, or version in the hashed artifact.** All of it lives in the
sidecar. This is the single rule that makes SHA-binding viable.

### 2.7 `checks.py`

Run at `build-finished` before emission, all as warnings with stable subtypes:

| Check | Subtype |
|---|---|
| Feature IDs unique across the document set | `covsight.duplicate-id` |
| Testpoint IDs unique (after derivation) | `covsight.duplicate-id` |
| Testpoint has at least one `.. tests::` or `:na:` | `covsight.testpoint-unmapped` |
| Feature has at least one env, env has at least one testpoint | `covsight.empty-goal` |
| `.. tests::` substitution placeholder has no binding | `covsight.substitution` |
| Every `env` used has a policy entry | `covsight.missing-policy` |
| `rule:` citation target outside `[A-Za-z0-9_]` (sphinx-needs link-role limit, `myst-authoring.md` §6) | `covsight.citation-id-charset` |
| D1 invariant: `testpoint.env` matches enclosing env goal | `covsight.internal` (error) |

### 2.8 `cli.py`

`covsight-testplan` wraps a Sphinx build so the plan can be produced without a docs build
step in the caller's makefile.

```
covsight-testplan build   <srcdir> -o plan.json [-f json|yaml|both]
covsight-testplan check   <srcdir> --against plan.json      # exit 1 on diff
covsight-testplan show    <srcdir> --summary                # counts, coverage of citations
```

`check` is the CI gate for determinism and for "someone edited the plan without
regenerating it". It diffs parsed JSON, not bytes, and prints a structural diff — a byte
diff on a 400-testpoint plan is unreadable.

### 2.9 Hook wiring (`__init__.py`)

| Event | Handler |
|---|---|
| `builder-inited` | load policy, load `needs.json`, probe optional backends, emit backend-availability notes |
| `doctree-resolved` | resolve citations, render cross-reference links |
| `env-purge-doc` | `store.purge(docname)` |
| `env-merge-info` | `store.merge(other.covsight_plan, docnames)` |
| `build-finished` | `if exception is None:` run checks → extract → emit |

`parallel_read_safe = True`, `parallel_write_safe = True`, declared only after
`env-merge-info` is implemented and its test passes.

---

## 3. Test plan

### 3.1 Structure

```
tests/
├── conftest.py               pytest-sphinx fixtures; make_app over tmp roots
├── roots/                    minimal source trees, one per behaviour
│   ├── test-basic/
│   ├── test-nesting/
│   ├── test-citations/
│   ├── test-no-backends/
│   ├── test-substitutions/
│   ├── test-myst/            the test-basic content, in MyST
│   └── test-errors/
├── test_directives.py
├── test_policy.py
├── test_citations.py
├── test_extract.py
├── test_determinism.py
├── test_checks.py
├── test_cli.py
└── test_example.py           builds docs/example, diffs the golden plan
```

Use `sphinx.testing` (`pytest_plugins = "sphinx.testing.fixtures"`) with `@pytest.mark.sphinx`
roots rather than hand-rolled builds — it gives warning capture and incremental-build
control for free.

### 3.2 Coverage matrix

| Area | Cases |
|---|---|
| **Directives** | Each of the six parses; required options enforced; repeated `:covergroup:` collects a list; `covers` argument form and body form; misnesting errors; `:na:` |
| **Nesting** | feature → env → testpoint; nested features; testpoint directly under feature (env `None`); directive inside a `container`/`only` block still attributes correctly |
| **Policy** | Inline dict and YAML file give identical fingerprints; `{feature}` interpolation; unknown placeholder is a config error; score expression arithmetic; **expression rejects `__import__`, attribute access, calls, subscripts, comprehensions, walrus** |
| **Citations** | `rule:` hit and miss; `sv:` exact fullname; `sv:` leaf-name candidate match; `sv:` ambiguous leaf; `rdl:` hit; all three backends absent; strict mode promotes to error; **absent backend emits exactly one message regardless of citation count** |
| **Extraction** | Full mapping per field; env goal nesting; `custom.covsight` policy block; requirements from all three citation kinds; `na: true` with no tests; empty feature |
| **Determinism** | Two builds byte-identical; **reordering `tags`/`coverage`/`covers` in source produces identical output**; changing only prose changes `desc` and nothing else; sidecar excluded from the hash; parallel build (`-j 4`) matches serial |
| **Incremental** | Delete a feature file → rebuild → gone from output (the `env-purge-doc` test); edit one feature → others unchanged; `env_version` bump forces full re-read |
| **Checks** | Each check fires on a crafted root and is silent on the clean root; suppressible via `suppress_warnings` |
| **CLI** | `build` writes both formats; `check` exits 0 on match, 1 on drift with a readable diff; `show --summary` counts |
| **Schema** | Emitted plan validates against testplan v1; **round-trips through covsight-core's reader** (M2, `covsight` extra) |
| **MyST / format parity** | Every extraction case runs against an RST root and a MyST root with identical extracted plans (modulo `docname`); colon-fence nesting; backtick fences for leaf directives; `.rst` and `.md` in one project; line numbers in warnings point at the right `.md` line |
| **Example** | Builds clean under `-W`; extracted plan equals the committed golden; guides' code blocks match the example sources |

### 3.3 Tests that exist because something specific will break

These are called out separately because they are the ones a reviewer should check are
present, not the ones that follow from the feature list:

1. **`test_incremental_delete_feature`** — the `env-purge-doc` failure is silent and
   produces stale output that looks correct. Highest-value single test in the suite.
2. **`test_parallel_read_matches_serial`** — `env-merge-info` omission loses data only
   under `-j`, so CI must build the example both ways.
3. **`test_set_fields_are_order_insensitive`** — guards decision D1/§2.6 rule 3; without
   it, a cosmetic source reorder produces a spurious plan diff and erodes trust in
   SHA-binding.
4. **`test_score_expression_sandbox`** — parametrized over a list of hostile expressions.
   An `eval` that reaches `__import__` in a doc build is a real vulnerability, not a
   theoretical one, because plans get built in CI from branches.
5. **`test_absent_backend_single_message`** — protects the authoring experience described
   in §2.4; failure mode is "everyone stops writing `rdl:` citations".
6. **`test_env_denormalization_consistent`** — the D1 invariant.
7. **`test_myst_rst_equivalence`** — a directive that quietly depends on RST-only
   behaviour produces output that is wrong only in MyST, and would be found by a user
   rather than by CI. The duplicate-option bug in the original §2.3 is exactly this class
   of mistake, and it was already written into the plan before being caught.

### 3.4 CI

`.github/workflows/ci.yml`:

- Matrix: Python 3.10 / 3.12 × (minimal deps, all extras). The minimal-deps leg is what
  actually proves optional dependencies are optional.
- `ruff check`, `ruff format --check`, `mypy --strict src/`.
- `pytest --cov=sphinx_covsight`, fail under 85%.
- Build `docs/` and `docs/example/` under `-W`; run `covsight-testplan check` against the
  golden.
- Build the example twice and `cmp` the JSON.

---

## 4. Documentation plan

### 4.1 The example, built first

The example is written **before** the guides, because the guides quote it by literalinclude
rather than restating it. That keeps them from drifting and makes the example the single
source of truth for every code block in the docs.

```
docs/example/
├── spec/
│   ├── conf.py              sphinx-needs; needs_types includes `rule`
│   ├── index.md
│   └── uart.md              8 rules, 2 sections; IDs are [A-Za-z0-9_] only
├── rtl/
│   ├── uart_regs.rdl        CTRL{BAUD_DIV, PARITY_EN}, STATUS{TX_BUSY, RX_FULL}
│   └── uart_cov.sv          uart_cfg_cg covergroup + uart_base_test class, doc-commented
└── plan/
    ├── conf.py
    ├── index.md             toctree + policy prose
    ├── feat_framing.md      FEAT-001: ip_simulation, formal
    └── feat_baud.rst        FEAT-002: ip_simulation, formal  (RST twin, proves parity)
```

Sizing: 8 rules, 2 features, 4 env blocks, 6 testpoints, 2 registers / 4 fields, 1
covergroup with 3 coverpoints, 2 test classes. Committed alongside:
`docs/example/_golden/testplan.json`, and `docs/example/_spec/needs.json` (a pinned copy,
per the design's cross-repo risk row).

### 4.2 The four guides

| Guide | Outline | Verified by |
|---|---|---|
| `writing-a-spec.rst` | Why rules need IDs · sphinx-needs setup and `needs_types` · what earns an ID (normative statements) and what does not (explanation, examples) · **the `[A-Za-z0-9_]` ID charset restriction and why** · ID scheme and stability under edit · publishing `needs.json` + `objects.inv` · a 3-rule worked fragment | Example spec builds; fragment is a literalinclude |
| `extracting-rules.rst` | What `needs.json` contains · consuming it from another repo (pinned copy vs. fetched artifact, with the trade-off) · `covsight_needs_json` / `covsight_spec_base_url` · detecting stale citations · what happens when the spec renumbers | `test_citations.py`; the pinned copy in the example |
| `writing-a-plan.rst` | The six directives with full option reference · feature/env/testpoint nesting rules · the three citation prefixes and when each resolves · coverage bindings and the UCIS-vs-declaration-path caveat · policy in `conf.py` · composition with `toctree` · **MyST and RST syntax side by side, with the fence-depth convention** · authoring before the RTL exists | Every snippet a literalinclude from the example |
| `extracting-a-testplan.rst` | Running `covsight-testplan` · the emitted schema, field by field, against the example's golden · determinism and what breaks it · `check` in CI · the provenance sidecar and what to audit · feeding the plan to covsight · what the MVP does *not* emit | Golden diff in CI |

Plus `docs/index.rst` (landing + quickstart), `docs/reference/directives.rst` (generated
option tables), and `docs/reference/configuration.rst` (every `covsight_*` value, default,
and effect).

### 4.3 Documentation rules

- Every RST/Python/SV/RDL block in a guide is a `literalinclude` with `:start-after:` /
  `:end-before:` markers into the example. No retyped code.
- The docs build with `-W` and `nitpicky = True` in CI.
- Each guide opens with what the reader will have at the end, and states its prerequisites.
- The configuration reference is generated from a single `CONFIG_VALUES` table in
  `__init__.py`, so it cannot drift from the code.

---

## 5. Work breakdown

Status key: `[ ]` not started · `[~]` in progress · `[x]` done

### M0 — Skeleton (no functionality)

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-001 | `pyproject.toml`, src layout, extras `sv`/`rdl`/`docs`/`dev` (D6.1–D6.3) | — | `pip install -e .[dev]` works |
| `[x]` T-002 | `setup()` returning version + parallel flags; `logging.py` warning helpers (D6.5) | T-001 | Extension loads in a bare Sphinx project |
| `[x]` T-003 | `conftest.py` + `roots/test-basic`; one smoke test | T-002 | `pytest` green |
| `[x]` T-004 | CI workflow: lint, mypy, pytest, minimal-deps leg | T-003 | Green on a PR |

### M1 — Directives parse and render

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-101 | `model.py` records + `PlanStore` with purge/merge | T-002 | Unit tests on store |
| `[x]` T-102 | Directive base: order counter, nesting stack, source capture | T-101 | — |
| `[x]` T-103 | `feature`, `env`, `testpoint` | T-102 | Parse + render; records stored |
| `[x]` T-104 | `covers`, `coverage`, `tests` — all body-parsed per D7 | T-102 | Multiple bindings of the same type collect, in order |
| `[x]` T-108 | MyST support: `colon_fence` guidance, fence-depth conventions, dual-format docs | T-104 | Example authored in MyST builds |
| `[x]` T-109 | `roots/test-myst` + `test_myst_rst_equivalence` parametrization | T-108 | Identical plans from both roots |
| `[x]` T-105 | Misnesting errors | T-103 | `roots/test-nesting` |
| `[x]` T-106 | HTML rendering: admonition-style blocks, ID anchors, `:tp:`/`:feature:` xref targets | T-103 | Example renders legibly |
| `[x]` T-107 | `test_directives.py` full matrix | T-104 | §3.2 directive + nesting rows |
| **Gate** | Example plan builds; features and testpoints render as authored prose | | |

### M2 — Extraction

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-201 | `policy.py`: loading, interpolation, score expression + sandbox (D5) | T-002 | `test_policy.py` incl. hostile expressions |
| `[x]` T-202 | `extract.py` mapping incl. env double-emission (D1) and derived IDs (D3) | T-101, T-201 | `test_extract.py` |
| `[x]` T-203 | Substitution expansion | T-202 | `roots/test-substitutions` |
| `[x]` T-204 | `emit.py` JSON/YAML + provenance sidecar | T-202 | Files written at `build-finished` |
| `[x]` T-205 | `checks.py` all seven checks | T-202 | `test_checks.py` |
| `[x]` T-206 | `cli.py` `build` / `check` / `show` | T-204 | `test_cli.py` |
| `[~]` T-207 | **External:** `env` field added to covsight-core testplan schema | — | Schema published |
| `[x]` T-208 | Round-trip test through covsight-core's reader | T-204, T-207 | Optional test, skipped without the extra |
| **Gate** | Valid testplan v1 emitted and read by covsight | | |

> **T-207 is the one external dependency.** If it slips, proceed with
> `covsight_env_in_custom = True` writing `custom.covsight.env`, and flip the default when
> the field lands. Do not let it block T-202.

### M3 — Determinism

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-301 | Canonical ordering rules (§2.6) | T-202 | Set-field reorder test passes |
| `[x]` T-303 | `env-purge-doc` / `env-merge-info` / `env_version` | T-101 | T-304 passes |
| `[x]` T-304 | Incremental + parallel tests (§3.3 items 1–2) | T-303 | `-j 4` == serial; deleted feature disappears |
| `[x]` T-305 | `covsight-testplan check` wired into CI | T-206 | Two builds byte-identical in CI |
| **Gate** | Byte-stable across builds, `check` green in CI | | |

### M4 — Spec citations

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-401 | `CitationResolver` skeleton + degradation ladder + single-message rule | T-104 | `test_citations.py` absent-backend cases |
| `[x]` T-402 | `rule:` backend over `needs.json` | T-401 | Resolves in the example |
| `[x]` T-403 | `:rule:` inline role | T-402 | Renders a link |
| `[x]` T-404 | Citations → `requirements[]` | T-402, T-202 | Extraction test |
| `[x]` T-405 | `covsight_strict_citations` | T-401 | Broken citation fails under `-W` |
| `[x]` T-406 | Example spec project + pinned `needs.json` | T-402 | Spec builds, publishes |
| **Gate** | Deliberately broken `rule:` fails the build; valid ones link | | |

### M5 — RDL and SV citations

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-501 | `sv:` backend over the `sv` domain, exact + leaf-candidate | T-401 | Hit, miss, ambiguous cases |
| `[x]` T-502 | Coverage-binding leaf validation (D2) | T-501 | Warns on unknown covergroup |
| `[x]` T-503 | **Spike:** confirm sphinx-peakrdl's model access and link construction | — | Written up; D2/§2.4 caveats confirmed or corrected |
| `[x]` T-504 | `rdl:` backend + same-build validation caveat | T-503 | Resolves in the example |
| `[x]` T-505 | Example `uart_regs.rdl` + `uart_cov.sv`, cross-referenced from the plan | T-502, T-504 | One doc set, all four sources rendering |
| `[x]` T-506 | Minimal-deps CI leg proves both are optional | T-505 | Builds and extracts without either extra |
| **Gate** | Unified doc set renders; removing both extras still builds and extracts | | |

> **T-503 spike — done, and the design's claims hold.** sphinx-peakrdl 0.3.0 is now
> installed via `ivpm.yaml`. Inspection of `sphinx_peakrdl/{domain,build,utils,html}.py`
> confirms:
>
> - The compiled model is a **process global**, `sphinx_peakrdl.design_state.root_node`,
>   populated at `env-before-read-docs` and deliberately not pickled.
> - `sphinx_peakrdl.utils.lookup_rdl_node(target)` resolves a dotted path against it —
>   so a `rdl:` target *can* be validated, but only when the RDL is compiled in the
>   same build, exactly as the design said.
> - Linking is URL construction, not inventory lookup:
>   `peakrdl-html/index.html?p=<path>` for a node, plus `#<field>` for a field. There is
>   no intersphinx inventory.
> - One correction, found by building the example: `peakrdl_input_files` is resolved
>   against the **working directory**, not `conf.py`. The example's `conf.py` makes the
>   paths absolute, and `writing-a-plan` says so.
>
> `citations.py::_resolve_rdl` follows this exactly, and counts an unvalidated target
> once per build rather than per citation.

### M6 — Documentation

| ID | Task | Depends | Done when |
|---|---|---|---|
| `[x]` T-601 | Example finalised + golden committed | T-505 | Golden diff green |
| `[x]` T-602 | `writing-a-spec.rst` | T-406 | — |
| `[x]` T-603 | `extracting-rules.rst` | T-406 | — |
| `[x]` T-604 | `writing-a-plan.rst` | T-601 | Every snippet a literalinclude |
| `[x]` T-605 | `extracting-a-testplan.rst` | T-601 | — |
| `[x]` T-606 | Reference: directives + configuration (generated) | T-601 | Cannot drift from code |
| `[x]` T-607 | Landing page + quickstart; docs build `-W nitpicky` in CI | T-606 | — |
| **Gate** | A reader can go from nothing to an extracted plan using only the docs | | |

### Sequencing

M0 → M1 → M2 → M3 are strictly serial (the spine). M4 and M5 are independent of each
other and both depend only on T-104 + T-401, so they can proceed in parallel once M2 is
done; neither blocks M3. T-207 (external) should be raised against covsight-core at the
**start** of M1 so it has the whole of M1–M2 to land. T-503 (peakrdl spike) can be done at
any point and should be done early, since it is the one place the design rests on
unverified external behaviour.

---

## 6. Risks carried into implementation

| Risk | Trigger | Response |
|---|---|---|
| T-207 slips | covsight-core schema change not merged by end of M2 | `covsight_env_in_custom` fallback; flip later |
| sphinx-peakrdl behaves differently than documented | T-503 spike | Re-scope T-504; worst case `rdl:` becomes a recorded-but-unresolved citation kind, which still extracts correctly |
| `desc` as raw RST source displeases downstream consumers | Review of the first extracted plan | Add `covsight_desc_format = "rst" \| "text"` with a plain-text renderer; the field is already isolated |
| Directive surface grows during M1 | Any new authoring request | Selection rule is the defence: identity, validation, or extraction. Presentational needs become post-MVP view directives |
| Example grows past readability | M5, when RDL/SV land | Hard cap: 6 testpoints, 8 rules. Additional demonstrations become test roots, not example content |
| MyST fence-depth churn when a nesting level is added | Authoring | Leaf directives use backtick fences (one free level); one feature per file caps depth at four |
| Coverage-binding leaf validation produces false warnings | M5 | It is warn-only and config-gated by design; if the noise rate is bad, default `covsight_validate_coverage_bindings` to `False` |

---

## 7. What the implementation changed

Recorded here rather than silently absorbed, because each one is a place the plan was
wrong or under-specified and the next reader will want the reason.

| # | Plan said | Implementation does | Why |
|---|---|---|---|
| 1 | `.. coverage::` leaf validation against the `sv` domain | Validates **`covergroup` and `coverpoint` bindings only** | The `sv` domain has no object kind for `cross`, `assertion` or code-coverage bindings, so checking them reported every one as missing. Found by the example's `cross: uart_env.uart_cfg_cg.cfg_x` binding |
| 2 | §2.3 nesting stack "on the Sphinx environment" | Stack lives in `env.temp_data`, which Sphinx clears per document | A stack on `env` itself would survive a failed parse and leak into the next document |
| 3 | `covers`/`tests` "take a body" | Body **and** argument forms, unified by `body_lines()` | In RST, a list written directly under the marker with no blank line arrives as a multi-line *argument*, not as content. Both formats therefore need one code path — and that path is what makes warning line numbers exact in MyST too |
| 4 | Warning locations unspecified | Per-line source locations for every citation and binding | `self.content.items` carries document offsets in RST and directive-relative offsets in MyST; `line_of()` takes the recorded offset only when it lands after the directive, which resolves both without asking which parser is in play |
| 5 | `covsight_output` relative to `conf.py` (implied by the design's `_build/testplan.json`) | Relative to the **build output directory** | `conf.py`-relative writes outside the build tree, which surprises anybody who expects `sphinx-build` to only touch its outdir. Documented in the configuration reference |
| 6 | `mypy --strict src/` in CI | Plain `mypy src/` | `--strict` against Sphinx's own annotations is a separate piece of work, not an MVP gate. `ruff check`, `ruff format --check` and `mypy` all pass as configured |
| 7 | Feature-level `.. covers::` mapping unstated | `custom.covsight.requirements` on the goal | testplan v1's `goal` has no `requirements[]`. The field stays out of `custom` on testpoints, where the schema does have a home for it |
| 8 | T-207 assumed to land | `covsight_env_in_custom` defaults to **`True`** | The schema's `testpoint` still has `additionalProperties: false` and no `env`, so a top-level `env` would fail validation today. `test_env_as_a_top_level_field` covers the flip |
| 9 | §3.3 "each destructive test edits its own copy" left implicit | `private_copy()` in `test_determinism.py`, used by both incremental tests | Sphinx ≥ 8.2 gives each test its own copy of a testroot; Sphinx 8.1 shares one per session. So the deletion test's `feat_b.rst` removal was still visible to `test_parallel_read_matches_serial`, which asserts all eight features are present — green on the development machine, red on the floor version. Caught by trial-running the Forgejo job in `catthehacker/ubuntu:act-22.04` rather than by CI |

### Status at the end of the MVP

- 145 tests, 96% statement coverage; `ruff`, `ruff format` and `mypy` clean. The suite also
  passes on the oldest supported floor — Python 3.10 with Sphinx 8.1 — with and without the
  optional citation backends.
- The example builds under `-W` as HTML, extracts to the committed golden, and round-trips
  through covsight-core's `Testplan.from_dict` (`test_round_trip_through_covsight_core`).
- The emitted plan validates against `testplan.schema.json` as published.
- `docs/` builds under `-W` with `nitpicky = True`.
- **Open:** T-207 only. Nothing else in this document is outstanding.
