# Authoring Test Plans as Sphinx Documents

**Design assessment and recommendation**

| | |
|---|---|
| Subject | Replacing `*_unified_test_plan.json` as the authored artifact with a Sphinx source document |
| Reference artifact | `dut_unified_test_plan.json` (v5, 2026-09-13, `08698126…d4d0bb31`), 3.22 MB |
| Date | 2026-09-15 |
| Status | Draft for review |

---

## 1. Executive summary

**Recommendation: proceed.** Authoring the unified test plan (UTP) as a Sphinx document and
extracting the JSON is feasible, and the feasibility is not marginal — it is comfortable. The
reason is not that Sphinx is a nicer editor. It is that **the JSON is ~87% derived data**, and a
document-with-directives architecture is the mechanism that lets you stop storing it.

Measured against the reference artifact:

| Measure | Value |
|---|---|
| Total file | 3,219,600 bytes |
| Content copied verbatim from upstream sources | **49.8%** |
| Content mechanically derivable from four templates and a policy table | **3.4%** |
| Schema scaffolding (keys, punctuation, structure) | ~33.8% |
| **Genuinely authored narrative prose** | **219,641 chars — 6.8%** |
| Authored citation IDs (a link graph, not prose) | 200,197 chars — 6.2% |

The direction of travel proposed here — write RST, extract JSON — inverts the current pipeline
without changing the JSON contract that downstream audit tooling depends on. The emitted JSON can
be schema-identical to today's.

The three findings that carry the recommendation:

1. **All 13,157 rule citations are byte-exact copies of their source line**, and all 13,157 source
   rules are cited. There is zero authored content in the largest half of the file.
2. **`approach`, `reasoning`, `exit_criteria` and `overall_score` are pure functions of `env`**
   (and, for `approach`, the feature name). 1,620 stored values encode 4 templates, 4 strings, a
   15-row policy table, and one arithmetic expression.
3. **The citation scheme is positionally addressed and structurally fragile.** 424 citations target
   "block N" of a section and 242 target "row N" of a table. Editing the upstream document silently
   re-points them. This is a live correctness risk today, independent of any Sphinx decision.

The work divides cleanly along the repository boundary, and the two halves are different kinds of
effort. On the specification side it is **methodology** — adopt sphinx-needs, configure it for this
environment, and enforce the conventions in review. On the test plan side it is **a new tool** — a
project-owned Sphinx extension that owns the plan schema and emits the byte-stable JSON the audit
contract depends on (§8). The two are coupled by a published file, not a shared framework, so they
can proceed on independent schedules.

The work is not trivial. The principal cost is a one-time labeling pass over the architecture
specification (~230 new anchors, sized in §7), and the principal risk is cross-repository
coordination (§6). Both are addressed below.

---

## 2. What the current artifact actually is

### 2.1 The schema is small and regular

Despite 3.22 MB, the file contains only **eight distinct object shapes** and a three-level
hierarchy:

```
metadata
features[60]
  ├── feature_id, feature_name, description, notes
  ├── spec_references[]           → {ref, content}          14,060 total
  └── verification_environments[4]
        ├── env, scope, approach, reasoning
        ├── difficulty_score, coverage_score, overall_score
        ├── key_artifacts[]        → {name, description}       420 total
        └── exit_criteria[]        → string                    900 total
```

Cardinalities are rigid: every feature has exactly 4 verification environments; `env` takes 4
values, `scope` takes 3. Artifact names are unique (420/420). This regularity is what makes a
directive-based authoring model straightforward — there is no polymorphism to model.

### 2.2 Half the file is a copy of the specification

| Component | Chars | % of file | Authored? |
|---|---:|---:|---|
| Citation content (verbatim from upstream) | 1,603,985 | 49.8% | **No** |
| Citation IDs | 200,197 | 6.2% | Yes |
| Artifact names + descriptions | 194,614 | 6.0% | Yes |
| `exit_criteria` (15-row policy table) | 41,280 | 1.3% | **No** |
| `approach` (4 templates) | 36,104 | 1.1% | **No** |
| `reasoning` (4 fixed strings) | 30,600 | 1.0% | **No** |
| Feature name / description / notes | 25,027 | 0.8% | Yes |

Verified against `rules_complete.renumbered.txt`:

- 13,157 unique `Rule N.N.N` citations; **13,157 match their source line byte-for-byte (100%)**
- **13,157 of 13,157 source rules are cited (100%)** — the catalog is fully consumed
- Duplication factor across features is 1.02; only 233 rules are cited by more than one feature, and
  none by more than three

The `content` field therefore carries no information not present upstream. Its only function is to
save a lookup — at a cost of 1.6 MB, and at the price of making verbatim drift possible.

### 2.3 Four fields are pure functions of `env`

| Field | Stored values | Actual information content |
|---|---:|---|
| `approach` | 240 | 4 templates, parameterised by feature name |
| `reasoning` | 240 | 4 fixed strings |
| `exit_criteria` | 900 | 15 strings in a 4-key policy table |
| `overall_score` | 240 | `(11 − difficulty_score) × coverage_score`, exact for 240/240 |

`exit_criteria` is the clearest case: 15 unique strings, each appearing exactly 60 times — once per
feature. It is a project verification policy that has been photocopied into every record.

`key_artifacts[].description` is the interesting boundary case. All 420 are distinct, so they are
genuinely authored — but they are heavily templated: 420 descriptions share only 269 distinct
60-character prefixes, with three boilerplate families accounting for 151 of them (`Constrained-random
test that varies…` ×60, `Negative test that injects…` ×55, `Retained later-execution-scope test…`
×36). These should stay authored, but the recurring openings suggest a future `:kind:` option.

### 2.4 The citation scheme is positional and fragile

This is the most serious finding, and it is a problem today regardless of what happens to the UTP.

Of 666 distinct prose citations:

| Locator form | Count | Failure mode |
|---|---:|---|
| `…, block N` | 424 | Insert a paragraph → every later citation in the section silently shifts |
| `…table N row M` | 242 | Insert a row → every later citation in the table silently shifts |

Only **68.6%** of prose citation content can currently be located verbatim in
`dut_hardware_specification.md`. The remaining ~31% has already drifted, been reformatted, or
refers to content no longer present in that form. That is not a hypothetical risk; it is
accumulated damage.

The rule-to-prose backlinks show the same pattern in a different form. **All 13,157 rules carry a
trailing `[Ref: …]` pointer** to a specification section — the traceability intent is complete and
consistent. But the encoding is not: across 252 distinct targets, **109 (43%) are non-conforming**
(`10.1a`, `Table 5.1`, `§9.5.2.2`, `5.3 Table 5.2`, `6.2.2.8 item 3`), and separators mix `,` and
`;`. Of the 143 well-formed targets, 96.5% resolve to a real heading — so the data is good and the
syntax is not.

---

## 3. Design principle

> **A citation is a claim about a relationship, not a copy of the cited thing.**

The current JSON conflates the two. Every consequence in this document follows from separating
them.

| | Authored in the document | Derived at build time |
|---|---|---|
| Feature identity, name, description, notes | ✅ | |
| Which environments apply; scope; difficulty; coverage | ✅ | |
| Key artifact names and descriptions | ✅ | |
| **Which rules a feature covers** (IDs only) | ✅ | |
| Rule and prose text | | ✅ resolved from upstream catalog |
| `approach`, `reasoning` | | ✅ from per-`env` templates |
| `exit_criteria` | | ✅ from per-`env` policy table |
| `overall_score` | | ✅ `(11 − difficulty) × coverage` |
| Coverage closure statistics | | ✅ computed |
| Hyperlinks, HTML, indices | | ✅ Sphinx |

Applying this boundary, authored source falls from 3.22 MB to roughly **400–450 KB** — and a
reviewer reads verification intent rather than a wall of duplicated specification text.

### 3.1 What this buys beyond size

- **Verbatim drift becomes structurally impossible.** The audit's V5.7 check produced 583 warnings
  about citation text fidelity. When the text is never copied, the property being checked cannot be
  violated. The check becomes vacuous rather than passing.
- **Dangling citations become build failures.** `sphinx-build -W` turns a typo'd `Rule 1.1.99` into
  a hard error instead of a silently wrong citation.
- **Coverage closure becomes a build product.** "Which of the 13,157 rules are uncited?" is a set
  difference the extension computes on every build — it stops being an audit finding and becomes a
  CI gate.
- **Review happens on intent.** A pull request diff shows the changed verification approach, not
  50,000 lines of re-serialised specification text.

---

## 4. Target architecture

### 4.1 The document graph

```
  ┌─────────────────────────────┐
  │ Architecture Specification  │   (Sphinx; prose + rules co-located)
  │  repo: dut-spec             │
  └──────────┬──────────────────┘
             │  publishes, per released version:
             │    • objects.inv  (link channel)
             │    • needs.json   (content channel)
             ▼
  ┌─────────────────────────────┐
  │ Unified Test Plan           │   (Sphinx; this document's subject)
  │  repo: dut-utp              │   pins a spec version
  └──────────┬──────────────────┘
             │  publishes:
             │    • dut_unified_test_plan.json
             │    • HTML
             │    • coverage.json  (optional back-channel)
             ▼
  ┌─────────────────────────────┐
  │ Audit / closure tooling     │   (unchanged)
  └─────────────────────────────┘
```

### 4.2 Two publishing channels, because one cannot do both jobs

| Channel | Artifact | Carries | Used for |
|---|---|---|---|
| **Link** | `objects.inv` (intersphinx) | id → URL, display name | Cross-document hyperlinks in HTML |
| **Content** | `needs.json` (sphinx-needs) | id → {content, anchor, type, links, content_hash} | Transclusion into HTML; resolution into JSON |

These are separate because `objects.inv` carries no payload — intersphinx can point at an upstream
target but cannot retrieve its text. The link channel is stock Sphinx and theme-aware; the content
channel is sphinx-needs' `needs.json` (§8.1). Both are emitted by the same upstream build.

The content channel needs one addition sphinx-needs does not provide: the per-item **content hash**
that SPEC-IF-5 and the suspect-link mechanism (§6.4) depend on. It is carried as an extra option on
each need, so `needs.json` remains the single content artifact rather than acquiring a sidecar.

One mechanism detail matters operationally. An `intersphinx_mapping` entry's inventory element may
be a URL *or a local file path*, and the two halves resolve differently: **target locations are
relative to the built documentation, inventory locations are relative to the source directory.**
That asymmetry is what lets the test plan consume a locally staged, version-pinned inventory while
still emitting public URLs:

```python
intersphinx_mapping = {
    'spec': ('https://docs.example.com/dut-spec/v2.3', '../_inv/spec/objects.inv'),
}
```

Use it. Pointing `intersphinx_mapping` at a live URL means every build fetches `objects.inv` over
the network, and under `nitpicky` an upstream outage becomes a local CI failure — a documented
failure mode in the wild. Vendoring the inventory at a pinned revision fixes both reproducibility
and availability.

### 4.3 Rendering model

Selected: **link plus collapsed text.** A citation renders as a clickable rule ID with the resolved
text present but collapsed:

```
Covers 374 specification references
  ▸ Rule 1.1.3
  ▾ Rule 1.1.5
      The DUT data path must classify traffic by tagged IOVA [Ref: 3.1, 5.4.1]
  ▸ Rule 1.1.6
```

The page stays readable, the reviewer can drill in without navigating away, and the text remains
present for in-page search. Extracted JSON always receives the full text regardless of rendering
choice.

### 4.4 Identifier scheme

Current IDs are unqualified (`Rule 1.1.3`) and, for prose, positional. Both must change.

```
  rule:DUT/1.1.3                        rule
  spec:DUT/port-transaction-demux       labeled prose block
  spec:DUT/9.5.8.1#i_block_valid        table row, addressed by natural key
  utp:DUT/FEAT-001                      test plan feature
```

Requirements: namespace-qualified (a second IP must not collide); name-based, never positional;
stable within a major version; changes accompanied by alias entries.

#### Numbering style: hierarchical or opaque

A second decision sits underneath the scheme, and the two precedents for rule-based specifications
answer it differently.

| | Hierarchical (`1.1.3`) | Opaque (`R_TTPQK`) |
|---|---|---|
| Precedent | MISRA C — `Rule 10.3` | Arm architecture specifications — `R`/`D`/`I`/`X`/`U` labelled declarative statements |
| Human ordering | Sorts and scans naturally | None — a generated index becomes mandatory |
| Survives a section move | No — the ID *is* the position | Yes, by construction |
| Renumbering cost | Alias maps (§6.2); MISRA needed published mapping tables for C:2004 → C:2012 | None — Arm guarantees an item keeps its identifier across versions once past beta |
| Default `needs_id_regex` | Fails (`.` not permitted) | Passes as authored |

**Recommendation: opaque IDs for new rules.** Hierarchical numbers are positional identifiers in a
name-shaped disguise — they satisfy SPEC-IF-1 to the letter and violate it in spirit, because
inserting a rule renumbers its siblings. Opaque IDs make SPEC-IF-1 and SPEC-IF-3 true by
construction, and *delete* the §6.2 alias machinery rather than automating it. The costs are a
mandatory generated index and a one-time mapping of the 13,157 existing citations — mechanical, and
verified exactly by the Phase 2 round trip.

If hierarchical numbers must be kept for human familiarity, keep them as a **display attribute over
an opaque identity**, never as the identity itself. That is the one arrangement that survives
renumbering without an alias map.

For table rows, natural keys are available and strong — of 242 row citations, 235 have a usable
first-cell key and 190 are strong identifiers (`i_block_valid`, `D2H-Data-RdReq`). The 45 keyed
only by a bare ordinal (from `# | Feature | Description` tables) need real keys assigned.

### 4.5 Deterministic emission — a hard requirement

The audit binds the plan by SHA-256 (`utp_sha256`, plus `source_hashes` for every input). **If the
emitted JSON is not byte-reproducible, that contract is worthless** — the hash churns on every
rebuild and ceases to mean anything.

The extraction step must therefore guarantee: features sorted by `feature_id`; fixed key order
within each object; citations in authored order; fixed indent and `ensure_ascii`; no timestamps or
build paths in the payload. Generation metadata that must vary belongs in a sidecar, not in the
hashed artifact.

This is cheap to get right at the outset and painful to retrofit.

### 4.6 Build orchestration

The graph in §4.1 is acyclic, so a plain topological build works: spec first, test plan second.
Adopting the optional coverage back-channel (SPEC-IF-14) makes it cyclic, and at that point the
established answer is a **two-pass, inventory-first build**:

1. **Pass 1** builds each project with cross-project link warnings suppressed, emitting only
   `objects.inv` and its `needs.json`.
2. **Pass 2** rebuilds with the cross-project configuration enabled and warnings-as-errors.

The value is that it turns a cycle into two acyclic phases whose edges a build system can express
directly: pass 1 *declares* the inventory as an output, pass 2 *declares* it as an input. This is
how the sphinx-needs community handles ~50k-need multi-project builds, and how Eclipse S-CORE wires
its Bazel targets.

The cost is documented and real: each project builds twice for a clean rebuild, and Sphinx cannot
reuse its doctree cache in pass 2 because `conf.py` changed. Cache hit rates also degrade, since a
project with external links must rebuild whenever any referenced project changes.

**Recommendation: stay acyclic for now.** Defer SPEC-IF-14 until the one-way flow is stable; the
two-pass machinery is the price of admission for reciprocity and should be paid deliberately.

---

## 5. Authoring model

### 5.1 Worked example

```rst
.. feature:: System Architecture and Direct Attachment
   :id: FEAT-001

   The DUT is integrated as a module inside the IO subsystem, between the
   device-side IO aggregator and the host-side IOMMU.

   .. notes::

      Semantically clustered from repeated rule catalog topics and matching
      prose; individual rule references are preserved.

   .. covers::

      rule:DUT/1.1.3, rule:DUT/1.1.5, rule:DUT/1.1.6,
      spec:DUT/port-transaction-demux

   .. env:: ip_simulation
      :scope: subsystem
      :difficulty: 5
      :coverage: 8

      .. artifact:: dut_system_basic_test

         Directed test that targets the feature and will instantiate the
         supported top-level parameter sets and route representative
         transactions across all four data port boundaries.

      .. artifact:: dut_system_random_test

         Constrained-random test that varies legal configurations, transaction
         values, and timing while targeting this feature.
```

Note what is *absent*: no `approach`, no `reasoning`, no `exit_criteria`, no `overall_score`, no
citation text. All are supplied at build time from policy configuration and the upstream catalog.
A reviewer sees only decisions.

### 5.2 Configuration

Per-`env` policy lives once in `conf.py`, not 60 times in the data:

```python
tp_env_policy = {
    'ip_simulation': {
        'approach': 'Use boundary UVCs, directed sequences, constrained-random '
                    'stimulus, assertions, and a feature-specific reference '
                    'model to verify {feature}.',
        'reasoning': 'IP simulation provides controllability/observability for '
                     'timing and data bug classes with practical regression '
                     'run time.',
        'exit_criteria': [
            '100% regression pass for all planned tests',
            '95%+ functional coverage for implemented scope',
            '100% assertion pass',
            'X-prop clean on exercised paths',
        ],
    },
    # soc_simulation, formal, emulation …
}
tp_overall_score = lambda difficulty, coverage: (11 - difficulty) * coverage
```

Changing verification policy becomes a one-line diff rather than a 900-cell rewrite.

### 5.3 Composition

Sixty features become sixty `.rst` documents under a `toctree` — real documents with stable URLs,
not `include` fragments. The single-file view a reviewer wants is then a second builder over the
same sources (`-b singlehtml`, or `-b latexpdf` for a PDF deliverable), because single-file
builders inline toctree content by definition. That gives both artifacts with zero duplication, and
answers the "a test plan is a document that needs reviewing" requirement without compromising the
multi-page structure. Reserve `.. include::` for genuinely shared boilerplate, stored with an
extension outside `source_suffix` (`.rst.inc`) plus `exclude_patterns` as backup — otherwise Sphinx
parses the fragment twice, producing a duplicate page and duplicate-label warnings.

Aggregating records from sixty documents into one JSON requires four hooks, and omitting any of
them produces a specific, well-known failure:

| Hook | Signature | Omitting it causes |
|---|---|---|
| `env-purge-doc` | `(app, env, docname)` | Duplicated entries on rebuild; deleted features never disappear — the environment is pickled and reused |
| `env-merge-info` | `(app, env, docnames, other)` | Silent data loss under `-j auto`; parallel reads mutate forked copies of `env` |
| `build-finished` | `(app, exception)` | Correct emission point — **guard on `exception is None`** so a failed build never publishes a corrupt artifact that a downstream project consumes |
| `setup()` → `env_version` | — | Stale unpickled data after any change to the stored schema. Bump it whenever the record shape changes. |

`env_version` is the easy one to miss and produces the most mystifying bugs. `parallel_read_safe`
may only be declared `True` once `env-merge-info` is wired.

Feature ID uniqueness is checked across the whole document set; output ordering is normalised
(§4.5).

### 5.4 Migration direction

No established tooling generates RST from a structured requirements JSON — sphinx-needs'
`needimport` imports needs *into* a build rather than emitting source, and nothing equivalent was
found in StrictDoc or elsewhere. This generator is therefore genuinely bespoke, but it is also
throwaway: it runs once, and its output is verified exactly.

The JSON → RST direction is mechanical and should be scripted once: emit one `.rst` per feature,
writing citation IDs only and discarding the resolved text, templated fields, and derived scores.
Correctness is verified by re-extracting and diffing against the original JSON. That diff is the
acceptance test for the whole migration, and it is exact — the derived fields must regenerate
byte-identically.

---

## 6. Cross-repository coordination

The spec and the test plan live in separate repositories with published artifacts. The governing
idea:

> **Treat specifications as versioned dependencies.**

### 6.1 Mechanics

- The spec repo publishes a semantically versioned `needs.json` + `objects.inv` per release.
- The UTP repo **pins a spec version** in `conf.py` and records the pinned hash.
- A spec upgrade is a pull request *in the UTP repo* that bumps the pin. That PR is where re-review
  happens: the diff shows exactly which citations moved, appeared, or vanished.
- A build whose `needs.json` hash does not match the pin **fails**.

This makes a spec change incapable of silently altering the test plan.

### 6.1.1 Precedent

This is not a novel arrangement. **Eclipse S-CORE** (automotive software platform, Eclipse
Foundation) runs the same scenario at scale — many independently built modules with requirements
traceability, orchestrated through Bazel with `objects.inv` and `needs.json` as declared build
artifacts. Three of its conventions are worth adopting directly:

- **Mount XOR import, never both.** A module's content is either *mounted* (its sources overlaid
  into one build, giving local bidirectional links but no caching) or *imported* (consuming its
  published JSON, cacheable, outbound links only). Doing both double-defines every ID. Our design
  is pure import; the rule matters if aggregation is ever considered.
- **Structural ID uniqueness rather than deduplication.** S-CORE mandates that an ID contain a
  segment matching its owning module and enforces it as a check, rather than detecting collisions
  after the fact. This is the same argument as SPEC-IF-2, and the stronger form: make collision
  unrepresentable instead of detectable.
- **Explicit version-skew allowances.** Named, auditable escape hatches for building against a
  mismatched upstream, with the stated principle that *an allowance makes an integration possible
  during version skew; it does not make the underlying mismatch valid.* Worth copying verbatim as
  policy language.

S-CORE is an excellent reference architecture and a risky direct dependency — its public API
shipped two major versions in roughly three weeks during 2026, and its documentation lags its
releases. Borrow the patterns, not the package.

### 6.2 Renumbering and aliases

Cross-repo renumbering is the painful case. The catalog carries an alias map (`1.1.3 → 1.2.7, since
v6.0`), so a rename resolves with a deprecation warning rather than dangling. Aliases are removed at
the next major version. Without this, every rule renumber is a coordinated two-repo break.

Note that adopting opaque identifiers (§4.4) removes the *cause* rather than managing the symptom:
an ID that encodes no position never needs renumbering. If that recommendation is taken, this
machinery is needed only for the one-time migration off the legacy `N.N.N` numbers, and can be
retired afterwards instead of maintained indefinitely.

### 6.3 Shared tooling

The two layers own different code, so they ship as two versioned internal packages rather than one
shared blob:

| Package | Owner | Contents | Consumed by |
|---|---|---|---|
| `spec-sphinx` | spec team | sphinx-needs configuration profile (`needs_types`, `needs_extra_links`, `needs_id_regex`), the fingerprint/suspect plugin (§6.4), the three build checks | `dut-spec` |
| `utp-sphinx` | verification team | Feature/env/artifact directives, the `needs.json` loader, the deterministic JSON emitter, the plan schema | `dut-utp` |

Neither depends on the other; the coupling is the published `needs.json` contract. The JSON schema
version travels with `utp-sphinx`, and the profile version with `spec-sphinx`, so a change to either
is a visible version bump in the repo that consumes it.

### 6.4 The rule catalog co-maintenance problem

The intent is to move the rule catalog from *generated from prose* to *maintained alongside prose*.
This is a significant change in failure mode: generated artifacts are consistent by construction;
co-maintained artifacts can disagree.

**Recommendation: co-locate rules with the prose they formalise**, so that adjacency is physical
rather than aspirational:

```rst
.. _dataplane-staging:

Data Path
---------

The DUT sits in the IO subsystem between the IO aggregator and the first-level
IOMMU. It processes device data-plane DMAs while they are in flight…

.. rule:: 1.1.3

   The DUT must not stage device data-plane DMAs into host memory before
   processing
```

The `[Ref:]` backlink — currently a hand-typed string with 43% non-conforming syntax — becomes the
containing section, and is unbreakable by construction. Editing the paragraph puts its rules in the
same diff hunk.

**Semantic drift needs a named mechanism.** No schema check can detect "this rule no longer reflects
what the paragraph says." What *can* be mechanised is the review trigger: each rule records the
content hash of the prose block it was written against; when that block changes, every rule bound to
it is flagged **suspect** — not broken, not auto-corrected, surfaced for re-review.

**This must be built; it is not available off the shelf.** Doorstop implements exactly this as
suspect links over item fingerprints, which is the precedent. But sphinx-needs — the obvious
candidate for reuse — is explicitly stateless by design and has **no staleness, version, or
suspicious-link detection**. The feature has been proposed by the maintainer and discussed since
November 2024 (`useblocks/sphinx-needs` discussion #1352), and remains unimplemented as of
September 2026, blocked on version-format and namespacing questions. Notably, at least one
organisation in that thread reports abandoning manual version fields in favour of **SHA-1 content
hashing** — which is the mechanism proposed here, arrived at independently.

The practical consequence: roughly 100 lines of fingerprint-and-compare logic, carried as a small
sphinx-needs plugin in the spec repo (§8.1), and it is the single highest-value piece of custom
tooling in this design. Without it, prose/rule co-maintenance has no drift detection at all.

Three checks the spec build can then enforce:

1. Every normative prose block has at least one rule (nothing normative left unformalised)
2. Every rule sits in a live, labeled block (no orphans)
3. No rule is suspect against its block's current hash (no silent drift)

### 6.5 Detecting stale cross-references

Fingerprinting covers *content* drift. *Structural* drift — a cited ID renumbered or deleted
upstream — needs a different net, and no single tool covers it:

| Mechanism | Catches | Misses |
|---|---|---|
| `nitpicky` (`-n -W --keep-going`) | Every unresolved cross-reference, including intersphinx misses | Raw URLs; references that resolve but are semantically wrong |
| `linkcheck` builder with `linkcheck_anchors = True` | Dead *deep links* into published spec HTML — the renumbered-anchor case | Internal refs, catalog IDs |
| `needs.json` hash pin (§6.1) | Any upstream change at all, deliberately coarse | Nothing — it is the backstop |
| Suspect fingerprints (§6.4) | Content drift behind a stable ID | Structural changes |

Run `nitpicky` with `show_warning_types` in a non-blocking job first, seed `nitpick_ignore_regex`
with genuine external noise, then flip to blocking. Run `linkcheck` as a separate job — it is
network-dependent and should not gate the content build. Add a scheduled, non-blocking job that
re-pins to the spec's newest release and reports the diff; that is how you learn early that
upstream renumbered, rather than at integration time.

---

## 7. Requirements levied on the architecture specification

The UTP is a *consumer*. It does not dictate how the specification is authored; it declares the
interface it needs. The specification is free to satisfy this contract however it chooses.

That separation is deliberate and survives §8's recommendation. §8.1 proposes sphinx-needs as the
means, and shows that most of what follows reduces to configuration — but the contract below is
stated in terms of *what must be published*, not *what tool publishes it*, so a later change of
methodology does not invalidate it.

### 7.1 Identity and addressability

| ID | Requirement |
|---|---|
| SPEC-IF-1 | Every citable construct **shall** have a stable identifier derived from a name, not a position. Locators of the form "block N" or "table N row M" are not acceptable. |
| SPEC-IF-2 | Identifiers **shall** be namespace-qualified (e.g. `rule:DUT/1.1.3`). |
| SPEC-IF-3 | Identifiers **shall** remain stable within a major version of the specification. |
| SPEC-IF-4 | Table rows **shall** be individually addressable by a natural key drawn from row content, not by ordinal position. |

### 7.2 Published interface

| ID | Requirement |
|---|---|
| SPEC-IF-5 | The specification **shall** publish a machine-readable catalog mapping each citable ID to its content, anchor URL, kind, and content hash. |
| SPEC-IF-6 | The specification **shall** publish an intersphinx inventory (`objects.inv`) for the same IDs. |
| SPEC-IF-7 | The catalog **shall** record the semantic version of the specification and the SHA-256 of every source input. |
| SPEC-IF-8 | Catalog emission **shall** be byte-deterministic for identical inputs. |

### 7.3 Content guarantees

| ID | Requirement |
|---|---|
| SPEC-IF-9 | Catalog content for a cited ID **shall** be a complete, self-contained unit requiring no reassembly by the consumer. (Already satisfied today: row citations carry header, separator, and row.) |
| SPEC-IF-10 | Rules **shall** be first-class catalog entries carrying a typed link to the prose block they formalise, plus that block's content hash at time of authoring. |
| SPEC-IF-11 | Terminology **shall** be published as a glossary with stable term IDs. (93 acronyms currently duplicated into `metadata.terminology`.) |

### 7.4 Change discipline

| ID | Requirement |
|---|---|
| SPEC-IF-12 | Identifier changes **shall** ship with alias entries mapping old ID to new, retained for at least one major version. |
| SPEC-IF-13 | Removal of a cited ID **shall** be a breaking change requiring a major version increment. |

### 7.5 Optional reciprocity

| ID | Requirement |
|---|---|
| SPEC-IF-14 | The specification **may** consume the UTP's published coverage artifact to render "verified by" backlinks, closing the traceability loop in both directions. |

### 7.6 Sizing the labeling effort

Satisfying SPEC-IF-1 requires assigning names to currently-positional citation targets. Measured
from the 666 prose citations:

| Category | Count | Effort |
|---|---:|---|
| Block citations in sections with exactly one cited block | 53 | None — section anchor suffices |
| Block citations already carrying a `**Label.**` lead-in | 141 | None — promote to a structured field |
| Block citations requiring a genuinely new label | ~230 | **One-time manual pass** |
| Table row citations | 242 | Mechanical — 235 have a usable first-cell key; 45 weak ordinals need real keys |

The ~230 new labels are the real cost. They also improve the specification independently of this
proposal, since they force the author to name the things worth citing.

### 7.7 Advisory: recommended directive set

Not a requirement — offered as evidence-backed guidance on satisfying §7.1–7.3. The selection rule:
**a construct earns a directive only if it needs identity, validation, or extraction. Everything
else is plain RST plus a label.**

| Directive | Evidence | Rationale |
|---|---|---|
| `rule` | 13,157 rules, 100% cited | Core normative unit |
| keyed table | **242 of 666 prose citations (36%) target a single row** | Stock RST tables have no row anchors; today's addressing is positional |
| `register` | 14 of 58 tables are bitfield definitions in 3 recurring shapes | Highest-value extraction target — RAL, headers, UVM regmodels, RTL checks |
| `submodule` | `**Label.**` record repeated 12–13× across §9.5.x; **141 citations (21%) land on its fields** | It is already a record typed as bold text |
| `parameter` | §9.4 is the most-cited section (23 citations) | Elaboration tests check parameters against RTL |
| `verification-entry-point` | Appears 12×, 9 cited | The spec already declares how to verify things; currently invisible to tooling |
| `spec-block` | — | Deliberate escape hatch: a stable ID for prose with no schema yet |

Use **stock Sphinx** for: terminology (`glossary` + `:term:`), diagrams (mermaid + `:name:`), code
samples (`code-block`), and general prose (paragraph + label). Do not rebuild what Sphinx provides.

Under §8.1 these are not directives to write but **need types to declare** — each row becomes an
entry in `needs_types`, and the `spec-block` escape hatch becomes the untyped default. The selection
rule is unchanged; only the implementation cost drops.

With separate repositories, every type is still a schema commitment across a version boundary.
Start with a small core plus `spec-block`; let constructs graduate to declared types once they prove
themselves.

---

## 8. Toolchain

**Selected: sphinx-needs as the spec-side methodology; a project-owned extension as the UTP tool.**

The two halves of the graph in §4.1 have different problems, and the evidence answers them
differently. Treating them as a single toolchain decision is what made the choice look hard.

| Layer | Problem | Answer | Nature of the work |
|---|---|---|---|
| **Architecture specification** | Author 13,157 flat, typed, individually addressed rules and publish them | **sphinx-needs**, configured for this environment | *Methodology* — adopt, configure, enforce in review |
| **Unified test plan** | Emit a byte-stable JSON whose schema a SHA-bound audit already depends on | **Project-owned Sphinx extension**, ~400–600 lines | *A new tool* — design, build, own |

**The layers are coupled by a file format, not by a framework.** The spec repo publishes
`needs.json` and `objects.inv`; the UTP repo reads them. The UTP extension parses `needs.json` as
plain JSON — it does not import sphinx-needs, and the UTP repo need not have it installed. That is
worth stating explicitly, because it decouples the version problem: **only the spec repo needs the
Python upgrade** (§8.5).

### 8.1 Why the spec side fits sphinx-needs

A rule is precisely the shape sphinx-needs models well — a flat, typed, individually identified item
with a body and typed links to other items. Nothing about it requires a bespoke schema, and the
§7.7 directive set becomes configuration rather than code:

| Capability | Configuration | Satisfies |
|---|---|---|
| Custom item types | `needs_types` — replace the default `req`/`spec`/`impl`/`test` set with `rule`, `spec-block`, `register`, `parameter`, … | §7.7, without writing directives |
| Typed links | `needs_extra_links` — a `formalises` link from rule to prose block | SPEC-IF-10 |
| Publication | `needs.json` + `objects.inv` from one build | SPEC-IF-5, SPEC-IF-6 |
| Determinism | `needs_reproducible_json`, `needs_json_remove_defaults`, `needs_json_exclude_fields` | SPEC-IF-8 |
| Consumption | `needs_external_needs` (`json_path`/`json_url`, `id_prefix`, `version`) | The §4.2 content channel; the only in-tool pinning mechanism |
| Validation and reporting | Schema validation, `needtable`, `needflow` | The §6.4 build checks, and coverage reporting for free |

**One configuration constraint to settle early.** `needs_id_regex` defaults to `^[A-Z0-9_]{5,}` —
uppercase letters, digits and underscore, five characters minimum. Today's `1.1.3` fails it, and so
does a namespace-qualified `rule:DUT/1.1.3`. Either relax the regex or choose identifiers that
satisfy it as authored; §4.4 argues for the latter.

**Staleness detection is still not provided** (§6.4) — sphinx-needs is stateless by design, and the
feature has been open since November 2024. The fingerprint-and-compare logic remains custom, but it
is now a small plugin *on top of* sphinx-needs in the spec repo rather than a component of the UTP
tool. Roughly 100 lines, and still the highest-value custom piece in the design.

### 8.2 Why the UTP side cannot be sphinx-needs

This is the decisive finding for the UTP layer, and it generalises beyond any one tool. The plan's
payload
is a list of **objects** — `key_artifacts[]` is N × `{name, description}` — nested two levels below
the feature. Neither candidate tool can express that:

| | Multi-value fields | List of objects |
|---|---|---|
| **sphinx-needs** | `needs_extra_options` hold strings; multi-value is comma/semicolon-delimited text | Not supported |
| **StrictDoc** | `String`, `SingleChoice`, `MultipleChoice`, `Tag` — the complete set; `MultipleChoice` and `Tag` are comma-separated and single-line | Not supported. Its own feature map concedes "**rudimentary** support of arrays and dictionaries" |

Both therefore encode multi-value data as delimiter-separated text — and this corpus already
demonstrates why that fails. The rule catalog's `[Ref: …]` backlinks are exactly such a field, and
they mix `,` and `;` as separators across 252 targets with 43% non-conforming syntax (§2.4).
Adopting a tool whose only multi-value primitive is delimiter-splitting would rebuild that failure
mode by design, in a field carrying 420 artifact descriptions averaging 460 characters each.

The argument is therefore not "sphinx-needs is the wrong tool" — §8.1 adopts it. It is that **no
established requirements DSL models a list of objects**, so on the UTP side a mapping layer is
unavoidable whichever tool is chosen. Given that, and given a SHA-256-bound audit contract that
requires owning the emitted schema anyway (§4.5), the UTP side is better served by a tool built for
it than by a general one bent around it.

### 8.3 Also evaluated

| Option | Assessment |
|---|---|
| **StrictDoc** (BSD-2) | Standalone requirements tool with its own grammar, exporting to `html`, `rst`, `json`, `excel`, `markdown`, `reqif-sdoc`, `sdoc` and more, with genuinely verified ReqIF round-tripping for its native profile. But it **does not use the Sphinx API at all** — it emits `.rst` you copy in. It is a parallel tool, not a component of a Sphinx stack. |
| **Doorstop** | YAML-per-item plus git. Its suspect-link fingerprinting is adopted directly in §6.4; adopting the tool wholesale means giving up Sphinx as the document layer. |

### 8.4 A constraint on the UTP extension

One hazard found in sphinx-needs' history applies directly to anything we build. Its `list2need`
directive generated RST and re-injected it via `state_machine.insert_input`; that method is not
implemented by myst-parser's mock state machine, so the directive **silently produced no needs
under MyST** until it was fixed in 8.4.0.

**Design rule: do not generate RST and re-inject it into the state machine.** Build docutils nodes
directly, or use `nested_parse` on explicit content. A codegen-by-reinjection design is RST-only
and forecloses the Markdown fallback in §10.

For the record, MyST support in sphinx-needs is real — directives work in `.md`, upstream tests
assert it, and need bodies are parsed by the host format. It is documented in only one place, so
the fallback is viable but under-signposted.

### 8.5 Environment and versions

**Verified on this host:** Python 3.7.3, Sphinx 5.3.0, docutils 0.19; `sphinx_needs` not installed.
For reference, sphinx-needs 8.5.0 requires Python ≥ 3.10 and current Sphinx (9.1.0) requires ≥ 3.12.

The two-layer split makes this tractable, because the constraint no longer applies uniformly:

| Repo | Stack | Upgrade needed |
|---|---|---|
| **dut-utp** | Stock Sphinx + the project extension; reads `needs.json` as plain JSON | **None** — runs on the installed 3.7.3 / 5.3.0 today |
| **dut-spec** | sphinx-needs 8.5.0 | **Python ≥ 3.10**, a hard prerequisite for the spec track |

Phase 0 and Phase 2 (§9) therefore need no upgrade at all, and the Python work gates only the spec
track. Still **confirm the target versions before Phase 0** — extension hook signatures and the
`include-read` event (Sphinx ≥ 7.2.5) differ across the range in play, and the UTP extension should
be written against the version it will eventually run on.

**Explicitly rejected:**

- **`sphinx-multiproject`** — solves shared-`conf.py` duplication, not dependency ordering; says
  nothing about cross-referencing; Read the Docs-specific; last commit October 2024.
- **Read the Docs subprojects** — URL nesting and shared search only. The RTD documentation itself
  defers to intersphinx for cross-project references.
- **`sphinx-collections` git driver** for pinned spec ingestion — its implementation accepts only
  source, target, and name, with no branch/tag/commit checkout, so it cannot pin a revision. Stage
  a checked-out revision with `copy_folder` instead.

---

## 9. Migration path

The two layers migrate on separate tracks that meet at Phase 4. The UTP track needs no toolchain
upgrade and can start immediately; the spec track is gated on Python ≥ 3.10 (§8.5).

| Phase | Track | Work | Exit criterion |
|---|---|---|---|
| **0. Prototype** | UTP | Extension skeleton; directives; JSON emitter; `needs.json` loader | One feature round-trips byte-identically |
| **1. Catalog** | Spec | Stand up sphinx-needs; ingest rules as needs with generated anchors; publish `needs.json` + `objects.inv`; no spec rewrites yet | All 13,157 rule citations resolve; prose resolution rate measured and reported |
| **2. Bulk migration** | UTP | Script JSON → 60 `.rst` files; re-extract; diff | **Extracted JSON is byte-identical to `08698126…d4d0bb31`** |
| **3. Spec labeling** | Spec | ~230 new anchors; promote 141 `**Label.**` blocks; assign 45 table-row keys; settle the ID style (§4.4) | 100% of prose citations resolve by name |
| **4. Federation** | Both | Split repos; version and publish `needs.json`; pin from the UTP repo | Spec bump is a reviewable PR; hash mismatch fails the build |
| **5. Retire JSON as source** | UTP | JSON becomes a build artifact; RST is authoritative | Audit tooling runs unchanged against generated JSON |

Phase 2's exit criterion is the critical one and it is unambiguous: a byte-identical round trip
proves no information was lost, including every derived field regenerating correctly.

Phases 0 and 2 are self-contained, need no upgrade, and deliver most of the review benefit — they
can be executed against a statically staged catalog before the spec track exists. Phase 3 is the
expensive one and can be deferred or staged section by section. Phase 4 depends on organisational
readiness, not technical readiness.

---

## 10. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Emitted JSON not byte-reproducible, breaking the SHA-bound audit contract | **High** | Normalised ordering, fixed key order, no timestamps in payload (§4.5). Enforce in CI. |
| Prose citations unresolvable — 31% already fail verbatim lookup today | **High** | Phase 1 measures and reports the rate before committing; Phase 3 labeling closes it. This risk exists today and is not created by this proposal. |
| Cross-repo renumbering breaks citations | Medium | Alias map (§6.2); pinned versions; build fails rather than silently resolving wrong. |
| Prose↔rule semantic drift once co-maintained | Medium | Suspect-link fingerprinting (§6.4); physical co-location makes drift visible in review. |
| RST escaping corrupts content | **Low** | Measured: authored fields contain zero backticks, asterisks, newlines, or pipes across all 1,680 strings. All hostile content (10,178 underscores, 488 backticks, 433 asterisks, 351 embedded tables) is in citation text — which is never typed into RST under this design. Pull-by-reference eliminates this risk category. |
| Build time at 14,060 citations | Low | `needs.json` is a dict lookup; the 60-document set is small by Sphinx standards. Confirm in Phase 0. |
| Team unfamiliarity with RST | Low | Authoring surface is ~7 directives. MyST/Markdown is a viable fallback — **provided** the extension follows the §8.4 rule and never generates RST via `state_machine.insert_input`. |
| Spec track blocked on a Python upgrade — host runs 3.7.3; sphinx-needs needs ≥ 3.10 | Medium | Scoped to the spec repo only (§8.5); the UTP track runs on the installed stack, so Phases 0 and 2 proceed regardless. Fix target versions before Phase 0. |
| sphinx-needs becomes a load-bearing external dependency of the spec | Medium | The §7 contract is stated as published artifacts, not tooling, so a replacement can satisfy it. Pin the version; the UTP side is insulated because it reads `needs.json` as plain JSON. |
| Data loss under parallel builds (`-j auto`) | Medium | `env-merge-info` wired and `parallel_read_safe` declared only once it is (§5.3). Silent, so must be tested deliberately. |
| Stale collected data after a schema change | Low | Bump `env_version` on every change to the stored record shape (§5.3). |

---

## 11. Open questions

1. **Does the rule catalog remain a separate document, or do rules move inside the specification?**
   §6.4 recommends co-location, but this is an authoring-workflow decision owned by the spec team.
2. **What is the artifact store for published catalogs?** Internal package index, artifact
   repository, or git release assets — affects §6.1 mechanics but not the design.
3. **Who owns the ~230-label pass, and can it be staged?** Sections can be migrated incrementally if
   the catalog reports per-section resolution rates.
4. **What are the target Python and Sphinx versions for the spec repo?** This host runs Python
   3.7.3 / Sphinx 5.3.0; sphinx-needs 8.5.0 needs ≥ 3.10. Gates the spec track only (§8.5), but
   gates it hard.
5. **Hierarchical or opaque rule identifiers?** §4.4 recommends opaque, which eliminates the §6.2
   alias machinery but costs a one-time remap of 13,157 citations and a generated index. Owned by
   the spec team; must be settled before Phase 3.
6. **Should `key_artifacts[].description` gain a `:kind:` option?** Three boilerplate families cover
   151 of 420 descriptions; worth revisiting after Phase 2.

**Closed during this assessment:**

- *Should the UTP publish a coverage back-channel (SPEC-IF-14)?* — Deferred. It makes the build
  graph cyclic and mandates the two-pass build in §4.6. Revisit once the one-way flow is stable.
- *Can suspect-link detection be inherited from existing tooling?* — No. sphinx-needs has no such
  feature and the proposal has been open and unimplemented since November 2024. It must be built,
  now as a plugin on the spec side (§6.4, §8.1).
- *Is sphinx-needs usable at all, given §8.1's list-of-objects finding?* — Yes, on the spec side.
  That finding scopes to the UTP payload, whose `key_artifacts[]` no requirements DSL can model; a
  rule is a flat typed item and fits sphinx-needs directly (§8.1, §8.2).

---

## 12. Conclusion

The proposal is feasible and the economics are strongly favourable. The current JSON is 3.22 MB of
which under 7% is authored prose; half is a verbatim copy of an upstream document, and a further
3.4% is four templates and a policy table stamped out 240 times. A Sphinx source document with
build-time citation resolution reduces the authored artifact by roughly 8× while emitting a
schema-identical JSON, leaving downstream audit tooling untouched.

The strongest argument is not ergonomic but correctness-related. The present citation scheme is
positionally addressed, and ~31% of prose citations already fail verbatim lookup against the
current specification — damage accumulated silently, because nothing in the pipeline can detect it.
Moving to named, build-validated references converts that class of failure from invisible to
impossible. The verbatim-fidelity property that the audit currently checks with 583 warnings
becomes unfalsifiable rather than merely satisfied.

The costs are real and bounded: a one-time labeling pass over roughly 230 specification blocks, a
project-owned extension of modest size, and the coordination discipline that separate repositories
demand. None is a research problem. Splitting the toolchain along the repository boundary —
sphinx-needs as configured methodology for the specification, a purpose-built extension for the test
plan — keeps each side on the tool that fits it, and reduces the amount that has to be built to the
two pieces nothing off the shelf provides: the deterministic plan emitter and the suspect-link
fingerprints.

Recommend proceeding with Phases 0–2, which are low-risk, independently valuable, and gated on an
unambiguous acceptance test — a byte-identical round trip of the existing plan.

---

## Appendix A — Measurement methodology

All figures derive from `dut_unified_test_plan.json` (SHA-256
`08698126345645d21393ffb7786393a7dbbb943d84926519d5b22744d4d0bb31`), `rules_complete.renumbered.txt`
(`176acf4e…`), and `dut_hardware_specification.md` (`daf4c402…`), as listed in `SHA256SUMS`.

- **Schema profile** — recursive walk over all JSON paths, recording type frequency and enumerating
  value sets where cardinality ≤ 14.
- **Verbatim-copy test** — rule catalog source parsed with `^(\d+(?:\.\d+)+)\s+(.*)$`; each `Rule
  N.N.N` citation's `content` compared to the corresponding source line after stripping trailing
  whitespace. 13,157/13,157 exact.
- **Authored/derived split** — per-field character counts summed across all records; a field is
  classified derived if its value set is fully determined by `env` (and feature name), or copied
  from an upstream source.
- **Score formula** — `(11 − difficulty) × coverage` tested against all 240 environment records;
  exact in every case. Three alternative formulations tested and rejected.
- **Prose resolution rate** — each prose citation's `content` searched as a literal substring of the
  architecture specification; 457/666 found.
- **Backlink analysis** — `[Ref: …]` extracted from each rule, split on both `,` and `;`, and tested
  against headings matched by `^#{1,6}\s+([0-9]+(?:\.[0-9]+)*)\s`.
- **Labeling effort** — block citations grouped by section; sections with a single cited block
  counted as satisfiable by section anchor; blocks opening with `**Label.**` counted as promotable.

A partial extension prototype (directives, catalog loader, JSON emitter, RST generator) exists
under `poc/` from the feasibility investigation. It is a sketch, not a deliverable, and predates
the federation design in §4 and §6.

---

## Appendix B — External references

Consulted 2026-09-15. Version and date claims are as published at that time.

**Sphinx core**
- Intersphinx — inventory resolution, local-path inventories, `intersphinx_disabled_reftypes`:
  <https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html>
- Extension development, event callbacks and signatures:
  <https://www.sphinx-doc.org/en/master/extdev/event_callbacks.html>
- "Extending the build process" tutorial — the canonical collect/purge/merge/emit pattern:
  <https://www.sphinx-doc.org/en/master/development/tutorials/extending_build.html>
- `toctree` vs `include`, orphan handling:
  <https://www.sphinx-doc.org/en/master/usage/restructuredtext/directives.html>
- Builders, including `singlehtml` and `linkcheck`:
  <https://www.sphinx-doc.org/en/master/usage/builders/index.html>
- Configuration — `nitpicky`, `nitpick_ignore_regex`, `show_warning_types`, linkcheck options:
  <https://www.sphinx-doc.org/en/master/usage/configuration.html>

**sphinx-needs** (8.5.0, Sep 2026, MIT, useblocks) — **adopted for the specification layer** (§8.1)
- Configuration — `needs_types` (default `req`/`spec`/`impl`/`test`, fully replaceable),
  `needs_id_regex` (default `^[A-Z0-9_]{5,}`), `needs_external_needs`, `needs_extra_links`,
  `allow_dead_links`, reproducibility options:
  <https://sphinx-needs.readthedocs.io/en/latest/configuration.html>
- Builders — `needs.json` structure and the `versions` map:
  <https://sphinx-needs.readthedocs.io/en/latest/builders.html>
- Multi-project builds at ~50k needs; the two-pass inventory-first pattern (§4.6):
  <https://github.com/useblocks/sphinx-needs/discussions/1220>
- Suspicious/versioned links — **proposed Nov 2024, unimplemented as of Sep 2026** (§6.4):
  <https://github.com/useblocks/sphinx-needs/discussions/1352>

**Eclipse S-CORE** — reference architecture for multi-repo requirements traceability (§6.1.1)
- <https://github.com/eclipse-score/docs-as-code>
- Cross-module mount-vs-import rule:
  <https://eclipse-score.github.io/docs-as-code/main/how-to/other_modules.html>
- Version-skew allowances:
  <https://eclipse-score.github.io/docs-as-code/main/how-to/cross_module_compatibility.html>

**Identifier-scheme precedents** (§4.4)
- Arm architecture specifications — rules-based writing; `R`/`D`/`I`/`X`/`U` labelled declarative
  statements with opaque identifiers that are retained across versions once the specification is
  past beta: <https://support.arm.com/documentation/ddi0487/latest>
  (The Conventions boilerplate is shared across Arm specifications; the clearest published statement
  of the identifier-stability guarantee found in this pass was in a sibling document,
  <https://documentation-service.arm.com/static/65f01fbab5e3c10fe1335edf>. Confirm against the
  DDI 0487 front matter before quoting — for that manual the PDF is authoritative over the HTML.)
- MISRA C — hierarchical rule numbering (`Rule 10.3`), and the mapping tables that the
  C:2004 → C:2012 renumbering required: <https://misra.org.uk/>

**Verification-plan formats surveyed** — none models a normative source statement; all link plan
entries to coverage and tests only (§8)
- OpenTitan testplan (Hjson) — `testpoints` and `covergroups`:
  <https://opentitan.org/book/util/dvsim/doc/testplanner.html>
- Cadence vManager / vPlan — sections plus coverage links; requirements arrive from an external
  requirements-management tool:
  <https://www.cadence.com/en_US/home/resources/datasheets/vmanager-ds.html>

**Evaluated and rejected** (§8)
- `sphinx-multiproject` — RTD-specific, dormant since Oct 2024:
  <https://sphinx-multiproject.readthedocs.io/en/latest/limitations.html>
- Read the Docs subprojects — URL/search only, defers to intersphinx:
  <https://docs.readthedocs.com/platform/stable/subprojects.html>
- `sphinx-collections` — git driver cannot pin a revision:
  <https://sphinx-collections.readthedocs.io/en/latest/drivers/git.html>

**StrictDoc** — evaluated (§8); field-type limitations are the basis of §8.1
- <https://strictdoc.readthedocs.io/>

**Prior art borrowed**
- Doorstop — suspect links over item fingerprints, with `review`/`clear` to re-baseline; the model
  for §6.4: <https://doorstop.readthedocs.io/>

**Noted for a later phase**
- `sphinx-test-reports` (useblocks) — ingests JUnit XML into sphinx-needs items, and since 2.0.0
  offers `test-reports build needs <junit.xml> --output needs.json`, which emits a valid
  `needs.json` **without running Sphinx**. Relevant if results are ever fed back against plan items
  as a decoupled, cacheable pre-build step. Note the 2.0.0 install change: base install no longer
  pulls in Sphinx, so `pip install "sphinx-test-reports[sphinx]"` is required.
  <https://sphinx-test-reports.readthedocs.io/en/latest/cli.html>

*Two points could not be fully verified and are flagged where they appear: the exact sphinx-needs
version that introduced JSON schema validation and whether it validates externally imported needs;
and the `linkcheck` status enumeration and `output.json` format against Sphinx 9.1.0 specifically.
Neither affects the recommendation.*
