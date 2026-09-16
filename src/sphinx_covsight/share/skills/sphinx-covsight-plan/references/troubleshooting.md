# Troubleshooting

Every message carries `type="covsight"` and a stable subtype. Fix the cause;
reach for `suppress_warnings` only where the note below says it is reasonable.

## `covsight.nesting`

> `'testpoint' may only appear inside 'env' or 'feature'; found at the document root`

A directive outside its allowed parent. See the nesting table in
`directives.md`. In MyST this is almost always a **fence-depth** mistake: an
enclosing `::::` fence closed early because an inner fence was the same length.
Fences must be strictly longer than what they contain — use backtick fences for
leaf directives (`covers`, `coverage`, `tests`) to buy a level.

Never suppress. A misnested directive is silently missing from the artifact.

## `covsight.duplicate-id`

> `duplicate feature id 'FEAT-001'; first declared at feat_baud:12`

Two features or two testpoints share an id. For features, ids are authored — pick
another. For testpoints, two derived ids collided, which means two testpoints in
the same feature and environment have titles that slugify identically; retitle
one or give it an explicit `:id:`.

Also emitted, with a different message, when
`covsight_require_explicit_testpoint_ids = True` and a testpoint relies on a
derived id.

## `covsight.testpoint-unmapped`

> `testpoint 'FEAT-002.tp_divisors' has no '.. tests::' and is not marked ':na:'`

This is the warning that makes "we never wrote the test" visible. Two correct
responses: add a `tests` body, or add `:na:` if the testpoint is deliberately
unmapped. **Do not blanket-suppress it** — a plan whose unmapped testpoints are
invisible is worth less than no plan.

## `covsight.empty-goal`

> `feature 'FEAT-004' has no environments and no testpoints`
> `environment 'formal' of feature 'FEAT-002' has no testpoints`

Usually a plan still being written; occasionally an `env` left behind after its
testpoints moved. A feature whose *children* carry the content is exempt, so a
pure grouping feature does not warn.

## `covsight.substitution`

> `no substitution binding for {baud}`

A `{key}` in a `tests` line with no entry in `covsight_substitutions`. Either add
the binding, or the brace was literal — in which case rename it, since there is
no escape syntax.

## `covsight.missing-policy`

> `no covsight_env_policy entry for environment 'formal'`

An `env` name that does not key into `covsight_env_policy`. Emitted once per
environment name, not once per use. Usually a typo in the env name, or a new
environment whose policy has not been written; the goal still extracts, but with
no `approach`, `reasoning` or `exit_criteria`.

## `covsight.citation-id-charset`

> `rule id 'UART-3.2.1' contains characters outside [A-Za-z0-9_]`

The specification used an id sphinx-needs' cross-reference role cannot resolve
(`.` is reserved for need parts; `-` and `/` fail in the link parser). The
citation may well resolve here — sphinx-covsight reads `needs.json` directly —
but the *specification's own* `{need}` references are broken. This warning exists
to catch that from the plan side. Fix it in the specification; see the
`sphinx-covsight-spec` skill.

## `covsight.citation-unresolved`

> `rule:UART_3_2_9 not found in needs.json`

The backend is present but the target is not in it. Three real causes: the rule
was deleted, the rule was renumbered, or the pinned `needs.json` is stale. Check
`needs_json_sha256` in the provenance sidecar against a fresh specification
build before assuming the citation is wrong.

Set `covsight_strict_citations = True` in CI to make this an error — that is the
entire point of citing by reference rather than quoting.

There is no alias map for renumbering, by design: renumbering should not be cheap
while anything external references the ids. A genuine mass migration is a
search-and-replace over the plan, reviewed as one commit.

## `covsight.citation-syntax`

A `covers` target that is not `<prefix>:<target>`, or an unknown prefix. Only
`rule:`, `rdl:` and `sv:` exist.

## `covsight.coverage-binding`

> `coverage binding leaf 'uart_cfg_cg' not found in the sv domain`

Only the **leaf name** of a `covergroup` or `coverpoint` path is checked, and
only when sphinx-systemverilog is installed. Causes, in order of likelihood:

1. The covergroup genuinely has not been coded yet — normal when the plan leads
   the RTL. Leave it; it starts resolving when the source lands.
2. The source file is not in `sv_source_dirs`, so the whole domain is thin.
   Check the `indexed N SystemVerilog object(s)` line.
3. A typo.

It is never an error, and
`covsight_validate_coverage_bindings = False` turns it off wholesale if the
noise is not worth it. Note that a `coverage` path is a **UCIS instance path**
(`uart_env.uart_cfg_cg`) while an `sv:` citation is a **declaration path**
(`uart_pkg::uart_cfg::uart_cfg_cg`) — do not "fix" the warning by substituting
one for the other.

## `covsight.backend-absent`

Informational, once per backend per build: sphinx-peakrdl or
sphinx-systemverilog is not installed, or `covsight_needs_json` is unset. Every
citation for that backend is still recorded, without a url.

This is deliberately not one message per citation — a plan authored before the
RTL exists must build quietly, or people stop writing citations. It does not
fail `-W`, and `covsight_strict_citations` does not promote it.

## `covsight.config`

A `conf.py` problem: `covsight_env_policy` and `covsight_env_policy_file` both
set, an unknown placeholder in an `approach`/`reasoning` string, a
`covsight_score` expression that uses a call/attribute/subscript, or an unknown
`covsight_output_format` (JSON is written anyway). Raised once at
`builder-inited` rather than per feature.

## `covsight.internal`

> `env denormalization invariant violated: ...`

The goal tree and the denormalized `env` field disagree. This is a bug in the
extension, not in the plan — report it with the plan source that triggered it.

## Non-warning symptoms

**`error: no testplan was written`** from `covsight-testplan` — `sphinx_covsight`
is missing from `extensions` in the plan's `conf.py`, or `covsight_output` is
`None`.

**The plan is empty / `goals[]` is `[]`** — the pages holding the features are
not in a `toctree`, so Sphinx never read them. Extraction walks the project, not
the filesystem.

**Two consecutive `build` runs differ** — a determinism bug. Compare with
`covsight-testplan check`, which gives a structural diff. Most likely cause is
authored content that carries a timestamp or an absolute path into `desc`.

**MyST options silently missing** — a repeated option key is dropped silently in
MyST (it is a hard error in RST). Every list-valued input in this extension takes
a body for exactly this reason; if you wrote `:tags:` twice, only one survived.
