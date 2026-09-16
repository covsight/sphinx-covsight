# Directive reference

Six directives, one inline role, plus two cross-reference roles. One
implementation serves reStructuredText and MyST.

## Nesting

| Directive | Allowed parents | Argument | Body |
|---|---|---|---|
| `feature` | document root, `feature` | title | prose + children |
| `env` | `feature` | environment name | prose + children |
| `testpoint` | `env`, `feature` | title | prose + children |
| `covers` | `feature`, `testpoint` | optional, single-line targets | one or more target lines |
| `coverage` | `testpoint` | — | `<type>: <path>` lines |
| `tests` | `testpoint` | optional, single-line names | test-name lines |

A violation is `covsight.nesting`. Nesting is tracked with an explicit stack on
the Sphinx environment rather than inferred from node parentage, so a directive
still nests correctly inside a `container` or an `only` block.

## `feature`

| Option | Meaning |
|---|---|
| `:id:` | **Required.** Stable identifier, authored not derived — it is what survives retitling. Duplicates warn `covsight.duplicate-id`. |
| `:owner:` | Person or team accountable. Extracted to `goals[].owner`. |
| `:tags:` | Comma-separated labels. **Sorted** at extraction — they are a set, so reordering them in source does not change the artifact. |
| `:status:` | `planned`, `in_progress`, `complete`, `waived`. Defaults to `planned` for a feature with no testpoints beneath it. |

A feature with no environments and no testpoints warns `covsight.empty-goal` —
unless it is a parent whose children carry the content.

## `env`

The argument is the environment name (`ip_simulation`, `formal`, …), which keys
into `covsight_env_policy`. An environment with no policy entry warns
`covsight.missing-policy`, once per environment name.

| Option | Meaning |
|---|---|
| `:title:` | Overrides the title taken from `covsight_env_policy`. |
| `:scope:` | Free string — `block`, `subsystem`, `chip`, … |
| `:difficulty:` | Non-negative integer, fed to `covsight_score`. |
| `:coverage:` | Non-negative integer, fed to `covsight_score`. |

An environment with no testpoints warns `covsight.empty-goal`.

Nothing else belongs here. Approach, reasoning and exit criteria come from
policy in `conf.py`.

## `testpoint`

| Option | Meaning |
|---|---|
| `:id:` | Optional. Derived as `<feature-id>.<env>.<slug(title)>` when omitted — and as `<feature-id>.<slug(title)>` for a testpoint directly under a feature. |
| `:stage:` | `V1`, `V2`, `V2S`, `V3`, or any string your organisation uses. |
| `:priority:` | `high`, `medium`, `low`. |
| `:weight:` | Positive integer, relative importance for rollup. Omitted from the output when it is 1. |
| `:owner:` | Person or team accountable for this testpoint. |
| `:tags:` | Comma-separated labels. Sorted at extraction. |
| `:na:` | Flag. Marks a testpoint deliberately unmapped to tests, suppressing `covsight.testpoint-unmapped` for it. |

## `covers`, `coverage`, `tests`

**No options, by design.** A repeated option key is a hard error in RST and is
silently dropped in MyST, so every list-valued input takes a body instead — one
item per line, commas allowed within a line.

```rst
.. covers::
   rule:UART_3_2_1,
   rdl:uart.CTRL.BAUD_DIV

.. coverage::
   covergroup: uart_env.uart_cfg_cg
   coverpoint: uart_env.uart_cfg_cg.baud_div_cp

.. tests:: uart_baud_{baud}_test, uart_baud_random_test
```

`covers` and `tests` also accept a single-line argument form, for the common
one-item case. `coverage` does not — its entries are `type: path` pairs.

A malformed citation warns `covsight.citation-syntax`; an unresolved one warns
`covsight.citation-unresolved` (an error under `covsight_strict_citations`).

### Citation prefixes

| Prefix | System in `requirements[]` | Backend |
|---|---|---|
| `rule:` | `spec` | `needs.json` via `covsight_needs_json` |
| `rdl:` | `rdl` | sphinx-peakrdl's compiled SystemRDL model |
| `sv:` | `sv` | sphinx-systemverilog's `sv` domain |

An absent backend produces one informational `covsight.backend-absent` message
for the whole build, never one per citation, and the citations are still
recorded — without a `url`.

### Coverage binding types

`covergroup`, `coverpoint`, `cross`, `assertion`, `expression`, `toggle`,
`line`, `branch`, `functional` — the enumeration from covsight testplan v1.

Leaf-name validation against the `sv` domain applies to `covergroup` and
`coverpoint` **only**: the domain has no object kind for the others, so checking
them would report every one of them as missing. A miss warns
`covsight.coverage-binding`; disable with
`covsight_validate_coverage_bindings = False`.

Only the leaf is checked, because `coverage` paths are UCIS *instance* paths
while the `sv` domain keys on SystemVerilog *declaration* paths — a full-path
check would be wrong rather than merely strict.

## `tests` substitution

`{key}` placeholders expand from `covsight_substitutions`. A `{key}` with no
binding warns `covsight.substitution`. Expansion is cartesian over **sorted**
key names, so the result does not depend on dictionary ordering, and the
unexpanded line is preserved in `source_template`.

## Roles

| Role | Meaning |
|---|---|
| `` :rule:`UART_3_2_1` `` | Inline citation to a specification rule; renders as a link when it resolves. **Not** extracted into `requirements[]` — a citation mid-sentence is evidence, not an accountability claim. |
| `` :covsight:feature:`FEAT-001` `` | Cross-reference to a feature elsewhere in the plan, by id. |
| `` :covsight:tp:`FEAT-001.tp_parity` `` | Cross-reference to a testpoint, by id. |

There is deliberately no `:rdl:` or `:sv:` inline covsight role — those
extensions already provide `:rdl:doc-ref:`, `:sv:class:` and friends for prose.

## Not available in a plan

`covsight-directive-table`, `covsight-config-table` and `covsight-warning-table`
appear in sphinx-covsight's own documentation, where they generate the reference
tables from the implementation so the docs cannot drift from the code. They live
in that repository's local `docs/_ext/` extension and are **not** shipped by the
package — `sphinx_covsight` in `extensions` does not provide them.
