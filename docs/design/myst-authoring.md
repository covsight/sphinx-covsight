# MyST (Markdown) as the authoring format

**Status:** implemented — every row of §5.1 landed in the MVP. The `coverage` body
form, the dual-format test roots and `test_myst_rst_equivalence` are in the test
suite, and `checks.py` carries the `covsight.citation-id-charset` warning from §6
**Verdict:** Feasible, and cheap — but it forces one change to the directive design, and
that change is an improvement regardless of format.
**Verified against:** myst-parser 5.1.0, Sphinx 9.1.0, sphinx-needs 8.5.0, Python 3.12
**Affects:** [`mvp-design.md`](mvp-design.md) §2, [`mvp-implementation-plan.md`](mvp-implementation-plan.md) §2.3

Everything below was run, not reasoned about. The experiments and their raw results are in
§2; the conclusions and the corrected design are in §3–§5.

---

## 1. Why it is cheap

MyST is a **parser front end**, not a parallel extension API. `myst-parser` translates
Markdown into the same docutils doctree that the RST parser produces, and directives and
roles are invoked through the same `Directive.run()` / role-function interface with the
same `self.arguments`, `self.options`, `self.content`, and `self.lineno`.

Consequence: **sphinx-covsight does not need MyST-specific code.** A directive written
once works in both formats, provided its *syntax contract* is expressible in both. The
whole of the feasibility question reduces to that proviso, which is why §2 tests it rather
than asserting it.

Enabling it is three lines in the consumer's `conf.py`:

```python
extensions = ['myst_parser', 'sphinx_covsight']
myst_enable_extensions = ['colon_fence']      # required for readable nesting
# source_suffix is handled by myst_parser; .rst and .md coexist
```

---

## 2. What was verified

| # | Question | Result |
|---|---|---|
| 1 | Do nested custom directives work? | **Yes.** Three levels (`feature` → `testpoint` → `coverage`) parsed correctly with colon fences |
| 2 | Are arguments with spaces preserved? | **Yes.** `:::{feature} Baud rate generation` → `self.arguments[0] == 'Baud rate generation'` |
| 3 | Do custom roles work? | **Yes.** `` {rule}`UART/3.2.1` `` invoked the role with the correct text |
| 4 | Is raw body source available for `desc`? | **Yes.** `self.content` is verbatim MyST source, including nested fences |
| 5 | Are line numbers accurate for warnings? | **Yes, exact.** Warnings reported `index.md:11` / `index.md:17` matching the source lines |
| 6 | Can `.md` and `.rst` coexist in one project? | **Yes.** A `toctree` in `index.md` pulled in an `.rst` document and its directives ran normally |
| 7 | Do code fences nest inside colon fences? | **Yes.** A ```` ```systemverilog ```` block inside a `:::{rule}` survived verbatim into `needs.json` |
| 8 | Does sphinx-needs work under MyST? | **Yes.** Rules authored as `:::{rule}` produced correct `needs.json` entries with `id`, `title`, `docname`, `lineno`, `content` |
| 9 | **Do repeated options work?** | **No — and differently in each format.** See §3 |
| 10 | Does the YAML `---` option block give real lists? | **Not usefully.** See §3.3 |
| 11 | Does the `{need}` role resolve IDs containing `/`, `.`, `-`? | **No.** Unrelated to MyST; see §6 |

### 2.1 The experiment that matters

Same directive, same `option_spec`, duplicated option key:

```
:::{coverage}
:covergroup: uart_env.uart_cfg_cg
:covergroup: uart_env.uart_other_cg
:coverpoint: uart_env.uart_cfg_cg.baud_div_cp
:::
```

MyST result — build succeeds, **first value silently discarded**:

```python
('coverage', {'covergroup': 'uart_env.uart_other_cg',
              'coverpoint': 'uart_env.uart_cfg_cg.baud_div_cp'})
```

The identical construct in RST:

```
ERROR: Error in "coverage" directive:
invalid option data: duplicate option "covergroup".
```

---

## 3. The one design change

### 3.1 What was wrong

`mvp-implementation-plan.md` §2.3 said:

> Docutils keeps only the last value for a duplicated option key, so `coverage` overrides
> `option_spec` handling to collect a list.

Both halves are wrong. **RST raises a hard error** — duplicate detection happens in
`docutils.utils.extract_extension_options`, before the directive is instantiated, so
overriding `option_spec` cannot intercept it. And **MyST silently keeps the last value**,
which is worse than an error: a plan would extract with a binding missing and no
indication anywhere.

So repeatable options are not merely awkward in MyST — they are unavailable in *either*
format, and the two fail in opposite ways.

### 3.2 The fix: `.. coverage::` takes a body

One binding per line, `type: path`, exactly like `covers`. Verified working in MyST:

```
::::{coverage}
covergroup: uart_env.uart_cfg_cg
covergroup: uart_env.uart_other_cg
coverpoint: uart_env.uart_cfg_cg.baud_div_cp
::::
```

```python
('coverage', 'index.md:11', {},
 ['covergroup: uart_env.uart_cfg_cg',
  'covergroup: uart_env.uart_other_cg',
  'coverpoint: uart_env.uart_cfg_cg.baud_div_cp'])
```

This is strictly better than the option form, independent of MyST:

- Genuinely repeatable, in both formats.
- Order preserved (the option dict never was ordered across duplicates).
- Room for a per-binding description on a continuation line later, without a schema change.
- Consistent with `covers` and `tests`, which already take bodies — three list-valued
  directives, one syntax, instead of two shapes to remember.

The parse is a one-line split on the first `:`, with an unknown type producing
`covsight.coverage-binding` rather than a silent drop.

### 3.3 Rejected: the MyST YAML option block

MyST allows a `---`-delimited YAML block for options, which does admit real lists:

```
:::{coverage}
---
covergroup:
  - listform_a
  - listform_b
---
:::
```

Two reasons not to use it. It is **not valid RST**, so the formats would diverge in
authoring syntax — the thing that makes dual-format support cheap is that they do not. And
with a `directives.unchanged` converter the list arrives **flattened to a string**
(`'- listform_a - listform_b'`), so extracting real lists would mean MyST-aware option
handling in the directive. That is exactly the MyST-specific code §1 says we do not need.

---

## 4. The MyST path, end to end

The §2.2 example from `mvp-design.md`, authored in Markdown. This is the verified syntax,
with the §3.2 correction applied.

````markdown
# Baud rate generation

:::::{feature} Baud rate generation
:id: FEAT-002

The transmitter and receiver derive their bit clock from a programmable
divisor. The divisor is writable while the link is idle and takes effect
at the next character boundary.

::::{covers}
rule:UART_3_2_1, rule:UART_3_2_4,
rdl:uart.CTRL.BAUD_DIV
::::

::::{env} ip_simulation
:scope: block
:difficulty: 3
:coverage: 8

:::{testpoint} All supported divisor values
:id: FEAT-002.tp_divisors
:stage: V2
:priority: high

Sweep the divisor across every supported baud rate and confirm bit
timing at each, including the boundary values. See {rule}`UART_3_2_1`.

```{covers}
rule:UART_3_2_1
```

```{coverage}
covergroup: uart_env.uart_cfg_cg
coverpoint: uart_env.uart_cfg_cg.baud_div_cp
```

```{tests}
uart_baud_{baud}_test, uart_baud_random_test
```
:::
::::
:::::
````

And the spec side, which is sphinx-needs rather than sphinx-covsight, verified to produce
a correct `needs.json`:

````markdown
# UART Specification

## Framing

:::{rule} Divisor programmability
:id: UART_3_2_1
:status: approved
:tags: baud

The divisor **shall** be writable while the link is idle.

```systemverilog
ctrl.baud_div <= 16'd434;
```
:::
````

Produced:

```json
{"id": "UART_3_2_1", "type": "rule", "title": "Divisor programmability",
 "docname": "index", "lineno": 5,
 "content": "The divisor **shall** be writable while the link is idle.\n\n```systemverilog\nctrl.baud_div <= 16'd434;\n```"}
```

Note the field is `content`, not `description` — relevant to `citations.py`'s `rule:`
backend, which reads `needs.json` directly.

### 4.1 Nesting depth is the ergonomic cost

Markdown fences must be *strictly longer* than any fence they contain, so a three-level
plan needs `:::::` → `::::` → `:::`. Adding a level means widening every enclosing fence —
a whole-file edit for a structural change.

Mitigations, in order of preference:

1. **Use ```` ``` ```` fences for leaf directives** (`covers`, `coverage`, `tests`) as in
   §4, since backtick and colon fences nest independently. This buys one free level and is
   what the example above does. Verified.
2. **One feature per file** (already the composition model), so the outermost fence is
   `feature` and depth tops out at four.
3. Accept it. Three levels is the design's maximum; the plan is not arbitrarily deep.

This is a real cost relative to RST, where nesting is indentation and adding a level is
local. It is not a blocker, and it is the only ergonomic regression found.

---

## 5. Recommendation

**Support both formats; make the directive contract format-neutral; author the shipped
example in MyST.**

- *Both*, because the cost is one `conf.py` line for the consumer and a second parametrized
  test root for us, while picking one would exclude teams whose docs are already committed
  to the other.
- *Format-neutral contract*, because that is what keeps the cost at one test root. The rule
  is now explicit: **no repeated options, no YAML-block options, no
  indentation-dependent constructs** — list-valued inputs take a body.
- *Example in MyST*, because Markdown is the lower barrier for the verification engineers
  who will author plans, and because it exercises the harder of the two paths. The test
  suite keeps an RST twin of the same content to prove equivalence.

### 5.1 Changes to the implementation plan

| Item | Change |
|---|---|
| `mvp-implementation-plan.md` §2.3 | `coverage` becomes body-parsed, not option-parsed. Remove the "override `option_spec`" note — it does not work |
| New decision **D7** | Directive syntax contract is format-neutral: no repeated options, no YAML-block options, list inputs take a body |
| T-104 | Implement `coverage` body parsing; drop repeatable-option handling |
| **T-108 (new, M1)** | MyST support: `colon_fence` docs, dual-format test root, backtick/colon fence nesting in the example |
| **T-109 (new, M1)** | `tests/roots/test-myst/` — the `test-basic` content in MyST |
| Test matrix | New row: **every extraction test runs against both an RST and a MyST root and asserts identical extracted plans** (modulo `docname`). This is the single test that keeps format-neutrality true over time |
| Doc plan | `writing-a-plan.rst` shows both syntaxes side by side; the example is MyST with an RST appendix |
| §3.3 "tests that exist because something will break" | Add: **`test_myst_rst_equivalence`** — a directive that quietly depends on RST-only behaviour would otherwise be found by a user, not by CI |

Estimated additional effort: **under a day**, dominated by the dual-format test
parametrization rather than by any extension code.

---

## 6. Incidental finding: sphinx-needs IDs must be `[A-Za-z0-9_]`

Not a MyST issue — it reproduces in RST — but it was surfaced by this work and it
invalidates the ID style used in the design documents so far.

With `needs_id_regex` widened to permit them, needs with IDs `UART.3.2.1`, `UART-3.2.1`,
`UART/3.2.1`, and `UART_3_2_1` were all **created** successfully and all appear correctly
in `needs.json`. But the `{need}` cross-reference role resolves **only** `UART_3_2_1`:

```
WARNING: linked need UART.3.2.1 not found [needs.link_ref]
WARNING: linked need UART-3.2.1 not found [needs.link_ref]
WARNING: linked need UART/3.2.1 not found [needs.link_ref]
(UART_3_2_1 — no warning)
```

`.` is reserved by sphinx-needs for need-parts (`need_id.part_id`); `-` and `/` fail in the
link parser. The default `needs_id_regex` (`^[A-Za-z0-9_]{5,}`) already forbids all three,
so this only bites projects that widen it — which the design documents were heading toward
with `rule:UART/3.2.1`.

Consequences:

1. **The example spec uses `UART_3_2_1`-style IDs**, and `writing-a-spec.rst` states the
   charset restriction with this evidence.
2. sphinx-covsight's `rule:` backend reads `needs.json` directly, so it *could* resolve
   slash IDs — but it should not, because the spec's own inline `{need}` references would
   be broken. `checks.py` gains a `covsight.citation-id-charset` warning when a `rule:`
   target contains a character outside `[A-Za-z0-9_]`.
3. The hierarchical readability that `UART/3.2.1` was providing has to come from a prefix
   convention instead (`UART_3_2_1`), which is what the sphinx-needs `prefix` option is for.

This does **not** affect sphinx-covsight's own IDs (`FEAT-002`, `FEAT-002.tp_divisors`),
which are resolved by our own code, not by sphinx-needs. Worth keeping that separation
clear: two ID namespaces, two sets of rules, only one of them constrained by someone
else's link parser.
