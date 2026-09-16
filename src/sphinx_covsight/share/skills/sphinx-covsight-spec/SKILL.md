---
name: sphinx-covsight-spec
description: Author a specification whose normative rules a sphinx-covsight verification plan can cite - deciding what earns a rule id, the [A-Za-z0-9_] id charset and why widening it silently breaks cross-references, sphinx-needs setup (needs_types, needs_id_regex, needs_build_json, needs_reproducible_json), writing rule directives in MyST or reStructuredText, id stability under edit/split/delete, and publishing needs.json for a plan repository to resolve rule: citations against. Use when writing or restructuring an architecture/design specification that a verification plan cites, when a project sets needs_build_json, when asked to give specification statements stable ids, or when a plan reports covsight.citation-unresolved or covsight.citation-id-charset.
---

# Authoring a citable specification

The plan cites the specification; the specification knows nothing about the
plan. **sphinx-covsight is not installed here** — this is a plain sphinx-needs
project whose only obligation to the downstream is a published `needs.json`.

```
spec project  --(needs.json)-->  plan project  --(testplan.json)-->  covsight
sphinx-needs                     sphinx-covsight
```

## Why ids at all

A plan that *quotes* specification text goes stale silently: the specification
is edited, the quotation is not, and neither build notices. A plan that *cites*
a rule by id gets a link that follows the rule when it moves, and a build
warning when it is deleted. That only works if the cited thing has an identity
of its own — and a section number is not an identity, because it changes when a
section is inserted above it.

## What earns an id

**The test: could a testpoint pass or fail with respect to this statement?**

Earns an id:

- "The receiver **shall** re-sample the start bit at the half-bit point."
- "A write to the divisor while a character is in flight **shall not** change
  the bit clock until that character completes."

Does not:

- "The UART transmits 8-bit characters over a two-wire link." — explanation,
  nothing to verify.
- A timing diagram, a register-map table, a worked example — evidence, not
  obligation.

**Err towards fewer, larger rules.** A plan that cites one rule per testpoint
reads well; a plan that cites nine usually means the rules were split along
documentation boundaries rather than verification boundaries.

## The id charset — the one rule that bites

**Use `[A-Za-z0-9_]` only.** sphinx-needs' default
`needs_id_regex = r"^[A-Za-z0-9_]{5,}"` already enforces it, and the temptation
is to widen it so ids read hierarchically: `UART/3.2.1`, `UART-3.2.1`,
`UART.3.2.1`.

Do not. Needs with those ids are created successfully and appear correctly in
`needs.json` — so the damage is invisible where you would look for it. What
breaks is the cross-reference role **in the specification's own build**:

```text
WARNING: linked need UART.3.2.1 not found [needs.link_ref]
WARNING: linked need UART-3.2.1 not found [needs.link_ref]
WARNING: linked need UART/3.2.1 not found [needs.link_ref]
(UART_3_2_1 — no warning)
```

`.` is reserved by sphinx-needs for need *parts* (`need_id.part_id`); `-` and
`/` fail in the link parser. Get hierarchy from a prefix convention instead:
`UART_3_2_1`. sphinx-covsight warns `covsight.citation-id-charset` on the plan
side when a `rule:` target strays outside the charset — deliberately, so this
surfaces in the plan rather than in the specification's rendered output.

## conf.py

One need type, one id scheme, reproducible JSON:

```python
extensions = ["myst_parser", "sphinx_needs"]
myst_enable_extensions = ["colon_fence"]

needs_types = [
    {"directive": "rule", "title": "Rule", "prefix": "UART_", "color": "#BFD8D2", "style": "node"},
]

needs_id_regex = r"^[A-Za-z0-9_]{5,}"  # the default. Do not widen it.

needs_build_json = True
needs_reproducible_json = True
```

`needs_reproducible_json` matters more than it looks: without it the published
catalogue carries a timestamp, so every build produces a different file and the
plan repository cannot distinguish a real change from a rebuild.

One need type (`rule`) is usually right. Adding `requirement`, `constraint`,
`assumption` &c. is a real modelling decision — the plan's `rule:` prefix names
the id, not the type, so extra types buy filtering in the specification and
nothing downstream.

## Writing a rule

MyST:

```markdown
:::{rule} Divisor programmability
:id: UART_3_2_1
:status: approved
:tags: baud

The divisor **shall** be writable while the link is idle, and the programmed
value **shall** take effect at the next character boundary.
:::
```

reStructuredText — identical entry in `needs.json`:

```rst
.. rule:: Divisor programmability
   :id: UART_3_2_1
   :status: approved
   :tags: baud

   The divisor **shall** be writable while the link is idle, and the
   programmed value **shall** take effect at the next character boundary.
```

**Keep the body to the obligation.** Rationale, alternatives considered and
worked examples belong in the surrounding prose — which is not part of the rule
and is not what the plan cites. A rule body that opens with two paragraphs of
motivation makes every citing testpoint quote motivation.

## Id stability under edit

The id is a promise. Once a plan cites `UART_3_2_1`:

| Change | What to do |
|---|---|
| **Reword the rule** | Fine, no action. The citation still points at the current obligation — that is the point. |
| **Split a rule** | The old id must survive on one half, or every citing testpoint is revisited deliberately. There is no automatic answer to which half inherits it; it is a review decision. |
| **Delete a rule** | Must break the plan's build. That is the feature — the plan sets `covsight_strict_citations = True` in CI. |
| **Renumber for tidiness** | Don't. Every affected citation warns with file and line, and that cost is intentional: renumbering is a change to the interface between two repositories. There is no alias map, by design. |

Ids are for machines; titles are for people. Retitling is free.

## Publishing

```console
$ sphinx-build -b html spec/ _build/spec
$ ls _build/spec/needs.json
```

Two files cross the boundary:

- **`needs.json`** — the rule catalogue, written by `needs_build_json = True`.
  This is what the plan consumes.
- **`objects.inv`** — Sphinx's standard inventory, for `intersphinx` from other
  documentation. Not required by sphinx-covsight; publish it anyway, it is free.

Three fields in `needs.json` are load-bearing for sphinx-covsight: `id` is what
a citation names, `title` becomes the link tooltip, and `docname` builds the
link target. The rule body is under **`content`**, not `description` — relevant
if you write your own consumer.

## Getting the catalogue to the plan

The plan repository either pins a committed copy of `needs.json` or fetches the
specification's CI artifact at build time. **For anything short of a mature
pipeline, pin.** A pinned file is a dependency declaration; reviewing, diffing
and deliberately bumping it is the honest version of what a fetch does
implicitly, it keeps the plan buildable offline at any commit forever, and the
plan's git history then answers the audit question people actually ask — *when
did the specification we verified against change?*

The cost is that it goes stale silently, so pair it with a CI job that rebuilds
the specification and diffs the catalogue.

## Checklist before publishing

1. Every normative `shall`/`shall not` statement is inside a `rule` directive.
2. No id contains `.`, `-`, `/` or whitespace.
3. `needs_reproducible_json = True`, and two consecutive builds produce a
   byte-identical `needs.json`.
4. The build is clean under `-W` — in particular no `needs.link_ref` warnings.
5. No rule id that a downstream plan cites has been deleted or renumbered
   without that being the intended, reviewed change.

Authoring the plan that consumes this is the `sphinx-covsight-plan` skill.
Published documentation: <https://dvkit.org/covsight/sphinx-covsight/>
