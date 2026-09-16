# Configuration reference

Every value below is a `conf.py` setting read by `sphinx_covsight`. The
"rebuild" column is Sphinx's own: `env` values invalidate the parsed
environment when changed, `html` values only affect output writing.

## Plan identity

| Value | Default | Rebuild | Meaning |
|---|---|---|---|
| `covsight_plan_name` | `""` | env | Plan-level `name` in the emitted testplan. |
| `covsight_plan_description` | `""` | env | Plan-level `description`. |
| `covsight_plan_owner` | `""` | env | Plan-level `owner`. |
| `covsight_plan_tags` | `[]` | env | Plan-level `tags`. |

## Policy and scoring

| Value | Default | Rebuild | Meaning |
|---|---|---|---|
| `covsight_env_policy` | `{}` | env | Per-environment `title`, `approach`, `reasoning`, `exit_criteria`. |
| `covsight_env_policy_file` | `None` | env | YAML file holding the same data, relative to `conf.py`. Mutually exclusive with the inline form. |
| `covsight_score` | `"(11 - difficulty) * coverage"` | env | Restricted arithmetic expression giving a goal's `overall_score`. |
| `covsight_substitutions` | `{}` | env | `{key}` bindings expanded in `tests` names, and recorded in the plan. |

`covsight_env_policy` interpolates `{feature}` (the enclosing feature's title)
and `{env}` (the environment name) in `approach` and `reasoning`. Any other
placeholder is a configuration error, raised **once** at `builder-inited`
rather than per feature.

The inline and file forms are equivalent: identical content produces an
identical `policy_sha256` in the provenance sidecar.

`covsight_score` accepts numeric literals, the names `difficulty` and
`coverage`, `+ - * / // % **`, unary sign, and parentheses. Calls, attribute
access, subscripts, comprehensions and the walrus operator are **rejected when
the expression is compiled** — a doc build runs in CI on arbitrary branches, so
an `eval` that can reach `__import__` is a real vulnerability rather than a
theoretical one. It is a string rather than a lambda so it can be hashed into
provenance: scores are derived data, and provenance is what makes them
auditable.

## Citations

| Value | Default | Rebuild | Meaning |
|---|---|---|---|
| `covsight_needs_json` | `None` | env | Path to the specification's `needs.json`, relative to `conf.py`. Enables the `rule:` backend. |
| `covsight_spec_base_url` | `""` | env | URL prefix prepended to resolved `rule:` links. |
| `covsight_doc_base_url` | `""` | env | URL prefix prepended to resolved `sv:` and `rdl:` links. |
| `covsight_strict_citations` | `False` | env | Promote unresolved-citation warnings to build errors. What CI should set. |

`covsight_spec_base_url` is what makes a citation point at the **published**
specification rather than at a path that exists only on a build machine.

`covsight_strict_citations` does **not** affect the absent-backend case: a plan
built without sphinx-peakrdl still builds, because writing a plan before the RTL
exists is the normal case.

## Validation strictness

| Value | Default | Rebuild | Meaning |
|---|---|---|---|
| `covsight_validate_coverage_bindings` | `True` | env | Validate the leaf name of each `coverage` path against the `sv` domain. A no-op when sphinx-systemverilog is absent. |
| `covsight_require_explicit_testpoint_ids` | `False` | env | Warn when a testpoint relies on a derived id, for teams that SHA-bind at testpoint granularity. |

## Output

| Value | Default | Rebuild | Meaning |
|---|---|---|---|
| `covsight_env_in_custom` | `True` | env | Write a testpoint's environment to `custom.covsight.env` rather than a top-level `env` field. |
| `covsight_output` | `"testplan.json"` | html | Where to write the plan, relative to the build output directory. `None` disables emission. |
| `covsight_output_format` | `"json"` | html | `json`, `yaml` or `both`. JSON is the hashed artifact; YAML is for humans. |
| `covsight_provenance` | `True` | html | Write the `*.provenance.json` sidecar next to the plan. |

`covsight_output` resolves against the **build output directory**, so a normal
`sphinx-build -b html` writes the plan alongside the rendered HTML. An absolute
path is honoured as given. `covsight-testplan build` overrides it, which is how
the CLI produces the artifact without producing HTML.

`covsight_env_in_custom = True` is where a testpoint's environment goes until
covsight-core's testpoint schema carries an `env` field. Flipping it changes the
emitted artifact — flip it deliberately and regenerate the golden.

## Interaction with other extensions

| Extension | Effect when enabled |
|---|---|
| `myst_parser` | Plans may be authored in Markdown. Also set `myst_enable_extensions = ["colon_fence"]`. |
| `sphinx_needs` | **Not needed by the plan project.** It is the *specification* project that produces `needs.json`. |
| `sphinx_systemverilog` | Enables the `sv:` citation backend and coverage-binding leaf validation. |
| `sphinx_peakrdl` | Enables the `rdl:` citation backend. A target can only be *validated* when the SystemRDL is compiled in the same build. |

## Silencing a class of message

```python
suppress_warnings = ["covsight.coverage-binding"]
```

Subtypes are public interface: `nesting`, `duplicate-id`, `testpoint-unmapped`,
`empty-goal`, `substitution`, `missing-policy`, `citation-id-charset`,
`citation-unresolved`, `citation-syntax`, `coverage-binding`, `backend-absent`,
`config`, `internal`.
