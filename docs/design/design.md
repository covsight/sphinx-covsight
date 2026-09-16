
# Sphinx Covsight

sphinx-covsight asks verification engineers to revisit their assumptions
about what "documentation" is. For the most part, documentation creation
is a static process that happens prior to a design being created or 
tests being written. We want documentation to better-reflect the state
of the project -- and to take better advantage of it, and documents
created across the project. For example, the testplan is often written
in a machine-readable format (JSON) with text copied from the 
design specification. We want the testplan to reference a stable 
anchor in the spec and pull in the relevant text during doc generation.
We want to extract the machine-readable testplan format from the 
sphinx document. The testplan will reference covergroups and instance
paths. We want to be able to link to the source documentation for the
relevant covergroup (think sphinx-systemverilog). We might want to 
link to the test classes. We might even want to back-annotate some
coverage data.

---

## 1. Scope of this document

The companion document [`sphinx_testplan_design.md`](../../sphinx_testplan_design.md)
establishes, in detail, that a test plan can be *authored* as a Sphinx document and
*extracted* as machine-readable JSON, and works out the specification-side interface
that makes citation-by-reference possible. That work is assumed here and not repeated.

This document addresses the next question: **once the test plan is a document, what
else belongs in the same document set, and where is the line?** It covers

- the data-cadence model that decides what is in scope (§2),
- an inventory of candidate data sources, each assessed (§3),
- the architecture that makes external data safe to embed (§4–§6),
- the resulting documentation set and its directive surface (§7–§8),
- an incremental adoption path (§9).

The short answer to the scoping question is in §2.3: **sphinx-covsight owns data that
changes at commit rate or merge rate. It does not own data that changes at
run rate.** Regression dashboards are a different tool with a different lifetime, and
this design deliberately links to them rather than replacing them.

---

## 2. The organizing principle: cadence, not subject matter

### 2.1 The failure mode being avoided

The instinct when "documentation should reflect project state" is to keep widening the
aperture until the document set is a verification dashboard rendered by Sphinx. That
fails in a specific and predictable way: a Sphinx build is a *snapshot with a
commit hash*, and its audience reads it days or weeks after it was built. Data whose
value decays in hours becomes actively misleading in that medium — a page that
confidently reports `87.3%` next to a build date three weeks old is worse than a page
that links to the live number.

The complementary failure is treating documentation as immutable prose, which is the
status quo the project exists to fix.

The line between them is not the *subject* of the data — coverage appears on both
sides — but its **cadence** relative to the documentation build.

### 2.2 Cadence classes

| Class | Changes | Examples | Home |
|---|---|---|---|
| **Static** | Per release | Specification prose, normative rules, terminology, architectural intent | Authored in docs |
| **Slow / commit-rate** | Per merged PR | Test plan entries, coverage model shape (covergroups, coverpoints, bins, crosses), testbench architecture, register maps, test catalog, exclusions and their justifications, assertion inventory | Docs — authored, or derived from source at build time |
| **Semi-static / merge-rate** | Per merged nightly, consumed weekly | Coverage achievement per plan item, formal proof status, per-testpoint pass counts, closure trend | Docs — read from the coverage store, with a pinned snapshot for offline and release builds (§5) |
| **Dynamic / run-rate** | Minutes to hours | Individual run logs, waveforms, failure triage, seed-level results, flaky-test churn, queue depth | **Out of scope.** Dashboard; docs link out (§6.4) |

The third row is the interesting one and is the subject of most of this document.
"Semi-static" is not a hedge — it is a real and useful category. Coverage
*achievement* changes every nightly, but the number a human acts on is the merged
weekly figure, and the quantity that actually informs a decision ("are we converging?")
is a trend over months. That is documentation-rate data wearing dashboard clothing.

### 2.3 The scoping rule

> **If the datum is meaningless once stale, it belongs in the dashboard. If staleness
> makes it merely older, it belongs in the documentation — provided it says how old
> it is.**

Every mechanism in §4–§6 exists to make the second half of that sentence enforceable.

---

## 3. Candidate data sources

Each row below is assessed against §2.3. "Verdict" is a recommendation, and the
sections that follow develop the ones marked *adopt*.

### 3.1 Inventory

| # | Source | Cadence | Verdict | §  |
|---|---|---|---|---|
| 1 | Test plan (features, testpoints, environments, artifacts) | Commit | **Adopt** — authored in docs, extracted as covsight testplan v1 | Companion doc + §8.1 |
| 2 | Specification rules and prose | Release | **Adopt** — cited by reference | Companion doc |
| 3 | Coverage model *structure* — covergroups, coverpoints, bins, crosses, instance paths | Commit | **Adopt** — from source via sphinx-systemverilog, or from a UCIS DB's shape | §3.2 |
| 4 | Coverage *achievement* per plan item / covergroup | Per merge | **Adopt** — read via covsight-core, provenance-stamped | §5 |
| 5 | Coverage closure trend | Weekly | **Adopt** — the store already keeps the series | §5.4 |
| 6 | Coverage exclusions / waivers and their justifications | Commit | **Adopt** — high value; format designed in `covsight-core/docs/waiver-schema.md` | §3.3 |
| 7 | Test catalog — test classes, their plan items, their sequences | Commit | **Adopt** — derived from source | §3.4 |
| 8 | Testbench architecture — component tree, agents, config_db, virtual interfaces | Commit | **Adopt** — sphinx-systemverilog already renders these | §3.4 |
| 9 | Assertion / property inventory | Commit | **Adopt** | §3.5 |
| 10 | Formal proof status — proven / bounded (with depth) / CEX / inconclusive, and the assumption set | Per merge | **Adopt** — assumptions are *prose* and belong in docs | §3.5 |
| 11 | Register map (SystemRDL / IP-XACT / RAL) | Commit | **Adopt** — via sphinx-peakrdl; referenced and checked against, not generated | §3.6 |
| 12 | Requirements traceability matrices (safety, DO-254, ISO 26262 style) | Commit | **Adopt** — generated views over the same graph | §7.3 |
| 13 | Per-testpoint test pass/fail counts from the last merged regression | Per merge | **Adopt, narrowly** — count and status only, never per-seed | §5.3 |
| 14 | Individual regression runs, logs, waveforms, triage state | Run | **Reject** — link out | §6.4 |
| 15 | Bin-level uncovered-item listings | Nightly | **Reject by default**; bounded excerpt permitted in closure sections | §5.5 |
| 16 | Lint / CDC / RDC results | Commit-ish | **Defer** — same pattern as #10, different tool; adopt after formal lands | §3.7 |
| 17 | Bug counts, open issues against a feature | Daily | **Defer** — link out; a milestone snapshot is the only defensible form | §3.7 |
| 18 | Performance / area / timing figures | Weekly | **Out of scope** — different audience and toolchain | — |

### 3.2 Coverage model structure — the missing link in the graph

This is the highest-value addition after the test plan itself, and it is the one the
opening paragraph anticipates ("the testplan will reference covergroups and instance
paths").

A test plan entry today says, in prose, "covered by `cg_txn_type`". Nothing checks
that. Nothing links it. Nothing notices when the covergroup is renamed, when its bins
change meaning, or when it is deleted outright. The coverage model is the *contract*
between the plan and the measurement, and it is currently the least formal artifact in
the flow.

Making it a first-class, linkable entity yields four checks that are free once the
link exists:

1. **Dangling plan reference** — a testpoint names a covergroup that no source scope
   declares. Build warning.
2. **Unplanned coverage** — a covergroup exists in the model and no testpoint claims
   it. This is the set-difference dual of the rule-closure check in the companion
   document, and it catches the common real defect: coverage written opportunistically
   and never reconciled with the plan.
3. **Instance-path validity** — a plan entry scoped to
   `tb.env.agent[0].mon.cg_txn` resolves against the elaborated hierarchy (or against
   the UCIS scope tree, §4.2), rather than being a hopeful string.
4. **Shape drift** — the covergroup the annotation was written against no longer has
   the same bins (§6.2).

Two supply routes, and both should be supported because teams differ:

- **From source** (preferred) — sphinx-systemverilog already parses covergroup
  declarations, coverpoints, bins, and the instantiating scope. sphinx-covsight
  consumes its domain objects and cross-references them. No new parser.
- **From a coverage database** — a UCIS DB carries the full scope tree and every
  coverpoint and bin. For flows where the covergroups are generated, parameterized
  beyond static analysis, or written in a language the source parser does not cover
  (PyVSC, cocotb-coverage, `covergroup`s emitted by a generator), the database *is*
  the authoritative shape.

The second route is the reason §5.1 matters: covsight-core reads the scope tree
natively, with vendor databases converted upstream and open-source flows (Verilator,
cocotb-coverage, PyVSC, AVL) ingested directly. The documentation build gets the model
shape from the same API that gives it the numbers, with no vendor tool in the loop —
which is what makes the extension adoptable outside a commercial-tool shop.

**Note the cadence subtlety:** the coverage model *shape* is commit-rate data even
though it arrives inside a per-merge artifact. Shape and achievement are read
separately and treated differently — the shape can gate the build (a missing covergroup
is an error), the achievement cannot (§6.3).

### 3.3 Exclusions and waivers — the best fit in the whole inventory

Coverage exclusions are the clearest case of data that is *already* documentation
pretending to be a tool file. Industry practice is unambiguous on the requirements:
every exclusion carries an author-written justification; a designer signs off on it;
the exclusion file carries a checksum so the tool can detect when the underlying code
has changed out from under it; and the whole set is reviewed at sign-off. That is a
document with a review workflow and a staleness mechanism — stored as an opaque tool
artifact where nobody reads it.

**The format is designed in
[`covsight-core/docs/waiver-schema.md`](../../../covsight-core/docs/waiver-schema.md).**
UCIS carries only *applied* exclusion state — an `excluded` flag, a free-text
`excludedReason`, and provenance bits — so a companion format is required, and the
design note works out what it must hold and how far it can port across vendor tools.
Three points from it bear directly on the documentation layer:

- **The waiver is the reviewed object; the applied flag is derived.** Selector,
  justification, approval, effect and expiry are authored at commit rate; which
  concrete bins were matched is recomputed per merge. Documentation renders the
  authored side and annotates it with the resolved side — the same split as everywhere
  else in this design.
- **`effect` is explicit** — `exclude` removes an object from the denominator,
  `annotate` attributes a known gap without moving the number, `defer` records
  scheduled work. Most real "waivers" are attributions, and rendering them as such is
  the difference between a coverage figure that means something and one that has been
  quietly inflated. The documentation should make `effect` visible wherever a waived
  figure appears.
- **Expiry exists.** No vendor format has it, and it is what turns the register from an
  archive into a working document with a review cadence.

What the documentation layer adds on top:

- The justification rendered as prose next to the feature it concerns, in the medium
  the team already reviews in.
- Sign-off state surfaced per feature: a build check that no unapproved or expired
  waiver props up a testpoint claimed complete.
- **Staleness surfaced where someone will act on it.** The waiver format's
  `match-set-changed` and approval-fingerprint states are instances of the general
  suspect-link mechanism (§6.2); the doc build renders them rather than reimplementing
  them.
- A generated waiver register for the sign-off package (§7.3) — one of the recurring
  deliverables a DV lead assembles by hand today.

The design decision, restated for this layer: **the waiver file is the source of
truth, and the documentation reads it.** Justifications are not retyped into RST, and
Sphinx is not the authoring surface for something the coverage flow has to apply.
A `.. waiver::` directive in a document is a *reference* that pulls the record in,
exactly as `.. covers::` pulls a spec rule.

### 3.4 Test catalog and testbench documentation

These are commit-rate and largely already solved by sphinx-systemverilog, which
renders component trees, `config_db` tables, virtual-interface bindings, factory
overrides, sequence activity, and schematics from source. sphinx-covsight's
contribution is not to re-render them but to **close the loop between the plan and the
implementation**:

- A testpoint names its tests; each resolves to a documented class, with the reverse
  link ("this test serves FEAT-012, FEAT-019") generated on the class page.
- A test with no plan entry is reported — the dual check again, and one that
  reliably finds both dead tests and undocumented plan gaps.
- The `key_artifacts[]` entries in the existing plan schema (420 of them in the
  reference artifact, all hand-named) become *references* to real classes rather than
  strings that may or may not correspond to anything. This is a direct quality
  improvement to the existing plan data, obtained for free.

Test status per testpoint (#13) is a narrow, defensible annotation: *does this test
exist, does it run in the nightly, did it pass in the last merged regression.* Three
states. No seeds, no durations, no history beyond the trend series. The precedent —
sphinx-test-reports ingesting JUnit XML into sphinx-needs items, and Antmicro's
testplanner linking hjson test plans to cocotb results in generated documentation —
shows this is a well-trodden path, and also shows where it stops: those tools present
*last known status*, not a regression console.

### 3.5 Assertions and formal results

The assertion inventory is commit-rate source data and belongs in the doc set for the
same reason the coverage model does: plan entries reference assertions, and nothing
validates the reference.

Formal results are the more interesting case, because **the durable part of a formal
result is not the status — it is the assumption set.** A proof is only as good as its
constraints, and the constraint list is reviewed prose that changes at commit rate.
Bounded-proof sign-off is an established methodology precisely because "proven to
depth 40" plus "under these 12 assumptions" plus "here is why depth 40 is sufficient"
is a *documented argument*, not a number.

So: adopt formal status as a three-part entity — assumptions (authored prose,
commit-rate), proof status and bound (annotated, merge-rate), sufficiency argument
(authored prose). The annotation carries the status; the document carries the
reasoning. This is the same authored/derived split the companion document applies to
the plan, applied to a second domain.

### 3.6 Registers — leverage sphinx-peakrdl

Register maps are already generated from SystemRDL or IP-XACT in most flows and already
produce documentation. sphinx-covsight should **not** generate register documentation.

**Use [sphinx-peakrdl](https://sphinx-peakrdl.readthedocs.io/).** It compiles SystemRDL
listed in `peakrdl_input_files`, provides the `:rdl:ref:` role for cross-referencing
register-map elements by path (`my_soc.thingamabob.ctrl.en`), can inline register
content for offline/PDF builds, and links out to generated PeakRDL-HTML. That is the
whole register-documentation problem, already solved, by the toolchain most teams
authoring SystemRDL already run.

What matters for this design is a point easy to miss: sphinx-peakrdl **compiles the
register model**, so the build has the semantic model, not just link targets. That makes
registers a *source of verification intent* rather than merely a citation target:

- **Plan entries reference registers by path, validated.** A testpoint that says
  "reset values of the control block" writes `:rdl:ref:`my_soc.ctrl`` and the build
  fails on a typo or a removed register — the same guarantee as a spec citation.
- **Register-space closure is a set difference.** "Which registers has no testpoint
  claimed?" is the register-map equivalent of the unplanned-coverage check (§6.1), and
  it is one of the more reliably embarrassing gaps at sign-off.
- **Field properties imply required checks.** SystemRDL already declares `sw`/`hw`
  access, `onread=rclr`, `onwrite=woclr`, volatility, and reset values. A gap report can
  flag fields whose declared behaviour has no corresponding testpoint — a plan-quality
  check that needs no new authored data, only the model that already exists.
- **RAL access coverage joins to it.** Which registers and fields were actually read and
  written is a real coverage metric, and the register model is the natural axis to
  report it against.

Two integration details to settle:

1. **Namespace.** SystemRDL paths are address-map hierarchy; UCIS scope paths are
   design/coverage hierarchy. They are different namespaces naming related things, so
   register references are a distinct selector `type` (§4.2), not a path in the coverage
   tree. Do not conflate them.
2. **Linking mechanism.** sphinx-peakrdl links to PeakRDL-HTML by URL query parameter
   rather than by intersphinx inventory, so cross-document reference goes through the
   role rather than through `objects.inv`. Fine within one doc set; if the register
   documentation lives in a separate Sphinx project, check whether an inventory is
   emitted before assuming intersphinx will reach it.

The boundary stays firm: sphinx-peakrdl owns registers, sphinx-covsight references them.
Do not rebuild what it provides.

### 3.7 Deferred

**Lint/CDC/RDC** are structurally identical to formal (waiver with justification +
status annotation) and should reuse the mechanism once it is proven, not motivate
parallel machinery now.

**Bug counts** are the most-requested and least-defensible item. Daily churn, an
authoritative live UI one click away, and no interpretive value in a stale snapshot.
The single exception worth supporting later is a **milestone snapshot** — "at RTL
freeze, 4 open bugs against this feature, listed" — which is immutable by
construction and genuinely belongs in the sign-off record (§7.3).

---

## 4. Data tiers and the provenance contract

### 4.1 Three tiers

Everything rendered on a page is exactly one of:

| Tier | Definition | Source of truth | Build behaviour if absent |
|---|---|---|---|
| **Authored** | Typed by a human into the document | The document | n/a |
| **Derived** | A pure function of authored content plus configuration | The document | n/a |
| **Annotated** | Joined at build time from an external artifact | The external artifact | **Degrade, do not fail** (§6.3) |

The companion document establishes the authored/derived split for the plan. The
addition here is the third tier and the rule that governs it:

> **Annotated data is never authored.** No coverage percentage, proof status, or test
> result is ever typed into a document. If it cannot be joined, it is not shown.

The consequence is that annotation can never be wrong in the way copied text is wrong —
the failure mode is a *missing* number, which is visible, rather than a *stale* number,
which is not. This is the same argument the companion document makes about citation
text, applied to metrics.

### 4.2 The join key problem

Annotation is a join, and joins need keys. This is where the real engineering is.

| Entity | Key | Risk |
|---|---|---|
| Covergroup type | Namespaced type name | Low — stable, source-visible |
| Covergroup instance | Hierarchical instance path | **High** — paths move with testbench refactors, differ between UVM and non-UVM, and differ *between tools* for generate blocks and arrays |
| Coverpoint / bin | Path + name | Medium — bin names churn with `bins` expressions |
| Assertion | Hierarchical path + label | High, same as instances |
| Test | Class name | Low |
| Waiver | Selector + resolved-set hash | Handled by the waiver format (§3.3) |
| Register / field | SystemRDL path (`my_soc.blk.ctrl.en`) | **Different namespace** — see §3.6 |

Instance paths are the problem. Three mitigations, in order of preference:

1. **Prefer type-level annotation.** Most plan entries mean "this covergroup type,
   wherever instantiated." Aggregate across instances by default and make
   instance-specific scoping the explicit, rarer case.
2. **Support glob scoping** — `tb.env.agent[*].mon.cg_txn` — so that array-cardinality
   changes do not break the plan.
3. **Resolve, then pin.** Record the set of instances a pattern matched at annotation
   time; if a later build matches a different set, that is a reportable change, not a
   silent one.

**The selector is not the extension's to invent.** `testplan_closure.py` already
resolves a `{type, path}` binding with globs against a database and returns the matched
paths, and the waiver format needs the same thing for the same objects. Three consumers,
one grammar, one resolver, extracted into covsight-core — which also settles the
inconsistency that exists today, where the testplan resolver flat-`fnmatch`es dotted
paths while `waivers.py` implements `/`-segment globbing. Neither has external users
yet; this is the moment to unify.

A normalization layer is required regardless, because the UCIS scope tree, the
sphinx-systemverilog source model, and the elaborated simulator hierarchy name the
same things differently. **That layer is the core technical asset** and
should be designed deliberately rather than accreted — it is the piece that determines
whether the extension works on a second project.

### 4.3 The provenance record

Every annotated datum carries, and every rendered view can display:

```
source      dut_nightly_merged            # logical dataset name
tool        covsight-core 0.4 (ncdb)      # reader; original producer recorded upstream
dut_hash    a3f19c2…                      # commit the measurement was taken against
merged_from 412 runs                      # scope of the merge
as_of       2026-09-12T04:17Z             # when measured, not when built
snapshot    2026-w37                      # which pinned snapshot this build resolved
```

Four rules follow from having it:

- **`as_of` is rendered, always.** Not in a footer — adjacent to the number, at a
  glance. A percentage without a date is a defect.
- **Age is a build diagnostic.** `covsight_max_annotation_age` (default: 14 days)
  produces a warning; CI can escalate it. Stale data announces itself.
- **DUT-hash mismatch is reported.** Annotation measured against a commit that is not
  an ancestor of the documented one is flagged. This is the cheapest available check
  against the single most misleading possible page: current plan, old numbers.
- **Provenance is not in the hashed extract.** See §6.5.

---

## 5. Reading the coverage data

### 5.1 We own the data path

The doc build reads coverage through **covsight-core's own APIs** — the NCDB reader, the
in-memory UCIS model, and the Parquet/Iceberg backends — not through a vendor tool and
not through a hand-rolled export. That is a materially different position from the one
most documentation tooling is in, and several constraints that would otherwise shape
this design simply do not apply:

- **No vendor licence is needed at doc-build time.** Vendor databases are converted on
  the way in, by the flow that already converts them; the doc build sees NCDB or
  Parquet.
- **No bespoke exchange format is needed.** The join keys of §4.2 are UCIS scope paths,
  which is the model covsight-core already normalizes to.
- **Structure and achievement come from the same reader.** The coverage model shape
  (§3.2) and the numbers over it are two queries against one object, not two pipelines.
- **The selector engine already exists.** `testplan_closure.py` resolves a
  `{type, path}` binding with globs against a database and returns the matched paths.
  The documentation layer's covergroup references are the same selector, and should
  call the same resolver rather than reimplementing path matching for a third time
  (see the waiver design note, which makes the same argument for a second consumer).

So the rule is: **if the build can reach the coverage store, it reads it directly.**
Everything below is about what to do when it cannot, and about reproducibility — not
about a missing capability.

### 5.2 Snapshots: a lockfile, not a workaround

Direct access answers "can we read it," but not "should every build read it." Two
properties are still worth engineering for, and both are served by writing a small,
flat, sorted **snapshot** of exactly the values the document set renders — kilobytes,
keyed by the same join keys — and committing it to the documentation repository:

```yaml
# covsight/snapshot/coverage.yaml
meta:
  as_of: 2026-09-12T04:17Z
  dut_hash: a3f19c2
  source: dut_nightly_merged
  merged_from: 412
covergroups:
  cg_txn_type:        {coverage: 98.4, bins: 64, hit: 63}
  cg_addr_x_size:     {coverage: 71.2, bins: 256, hit: 182}
testpoints:
  FEAT-012.tp_basic:  {tests: 4, passing: 4, coverage: 98.4}
```

Think of it as a lockfile: the authoritative data lives in the store, and the snapshot
records what a particular build resolved to.

- **Offline and detached builds.** A clean checkout on a laptop, in a customer's
  environment, or in a CI job with no store credentials still produces the complete
  document set. The store is the source; the snapshot is the fallback.
- **Release reproducibility.** A tagged release rebuilds to exactly the numbers it
  shipped with, years later, after the store has been compacted, re-merged, or retired.
  Live reads cannot give you this, and for a sign-off artifact it is the whole point
  (§7.3).

Two secondary benefits come free and are worth having:

- **Coverage changes become reviewable.** A PR that moves a covergroup from 98% to 71%
  shows it in the diff, attributable to the change that caused it, rather than being a
  Tuesday-morning discovery.
- **Bisectability.** "When did this regress?" is `git bisect` over a text file.

Note what the snapshot is **not** for. Trend history does *not* come from git log —
covsight-core already has `history.py`, `multirun.py`, and a Parquet/Iceberg store with
per-merge history and time travel, which is a better series than a weekly commit
cadence can produce (§5.4). Deriving trend from git was the right answer only under the
assumption that the store was unreachable, and it is not.

Cadence: refresh the snapshot weekly and at every milestone. That matches the human
consumption rate and keeps the history readable; builds that want fresher numbers read
the store directly, which is the default whenever it is reachable.

### 5.3 What the documentation renders, and what it does not

This bounds both the snapshot and the direct-read path — the store holds far more than
the document set should show, so the restriction is editorial, not technical.

Rendered: per-covergroup and per-coverpoint achievement; per-testpoint rollup; test
existence and last-merged status; formal proof status and bound; assertion pass counts;
waiver application counts (§3.3).

Not rendered: anything per-seed, per-run, or per-host; durations; failure messages;
individual bin hit counts beyond the aggregate (§5.5); anything that would grow with
the number of runs rather than with the size of the design.

**The size test is the discipline:** what the documentation shows must scale with the
*design*, not with the *regression*. A page that grows when you run more tests has
crossed into dashboard territory — and, usefully, so has a snapshot file.

### 5.4 Trend

Trend is the clearest case of dashboard-shaped data that genuinely belongs in
documentation, because the question it answers — *are we converging, and at what rate?*
— is a planning question asked weekly, not an execution question asked hourly.

The series comes from the coverage store, which already keeps it: `history.py` and
`multirun.py` hold per-merge history inside a single archive, and the Iceberg tier adds
snapshots and time travel over the whole corpus. Trend is therefore a **query at build
time**, not something the documentation has to accumulate. Where the store is
unreachable, the committed snapshots (§5.2) give a coarser weekly series — degraded, not
absent.

Three views:

- A **sparkline** next to each feature's coverage figure: twelve weekly points, no
  axes, no interaction. Its job is to distinguish "flat for six weeks" from "climbing"
  at a glance.
- A **closure chart** at the plan level: planned vs. achieved over time, with milestone
  markers.
- A **stalled-features table** — the genuinely actionable view. Features whose coverage
  has not moved in N weeks and are not at target. This is the one view a DV lead will
  open every week, and it is not available in any vendor dashboard, because the
  dashboard does not know what "planned" means.

A fourth becomes available once waivers are modeled (§3.3): **waived fraction over
time**. A block sitting at 97% whose waived share tripled in a quarter is a finding,
and nothing today surfaces it.

Bound what is rendered — last 12 weekly points plus all milestone snapshots — and link
out for the full series. Sampling the store down to a fixed number of points is the
extension's job, not the reader's.

### 5.5 Uncovered bins

Default: not in the documentation. Bin-level analysis is an interactive task and the
coverage tool is better at it.

The bounded exception: within a *closure* section, for a covergroup below target, render
up to N (default 10) uncovered bin names — enough to say something useful about *why*
the feature is short, with a link out to the full analysis. Above N, render the count
and the link only. Direct store access makes it tempting to drop the cap, since the
data is right there; keep it. The cap is an editorial limit on what a page should say,
and it is what keeps a snapshot of that page the same size as the page.

---

## 6. Correctness mechanisms

### 6.1 The four closure checks

Each is a set difference the build already has both sides of. Together they are the
main reason to integrate the plan and the coverage model in one document set rather
than two.

| Check | Question | Finds |
|---|---|---|
| **Plan → model** | Every referenced covergroup exists? | Renamed or deleted coverage; typos |
| **Model → plan** | Every covergroup is claimed by a plan entry? | Unplanned coverage; plan drift |
| **Plan → tests** | Every named test class exists? | Aspirational plan entries |
| **Tests → plan** | Every test serves a plan entry? | Dead tests; undocumented work |

The two reverse directions are the valuable ones and the ones no existing tool
performs, because no existing tool holds both halves of the graph.

### 6.2 Suspect links, generalized

The companion document develops fingerprint-based suspect links for rule-vs-prose drift
(§6.4 there) and notes it must be built because sphinx-needs is stateless by design.
Once built, it is not a spec-side feature — **it is the general mechanism for "this
authored statement was written against something that has since changed."** It applies
to at least five relationships:

| Authored thing | Written against | Suspect when |
|---|---|---|
| Rule | Prose block | Block content hash changes |
| Testpoint | Spec rule | Rule content hash changes |
| Coverage annotation | Covergroup shape | Bin set or coverpoint set changes (`schema_fingerprint`) |
| Waiver justification | The objects its selector matched | Match-set hash changes (waiver design note §5.2) |
| Formal sufficiency argument | Assumption set | An assumption is added or edited |

One implementation, one review workflow (`review` / `clear` to re-baseline, following
the Doorstop model), five applications — and two of the five already have their
primitives in covsight-core, since `Manifest.schema_fingerprint` exists and the waiver
format defines its own match-set hash on top of it. Designing it as a general facility rather than
a rule-specific one is a small decision now and a large payoff later.

The third row deserves emphasis because it is subtle and currently undetectable: a
covergroup can go from 60 bins to 400 while staying at "98% covered," and the plan
entry that says "this is adequately covered" was written against a claim that no longer
holds. Nothing in any existing flow surfaces that.

### 6.3 Graceful degradation is mandatory

Annotated data is *optional input*. The build must produce a complete, honest document
without it:

The resolution order is **store, then snapshot, then nothing** — each step degrading
rather than failing:

| Condition | Behaviour |
|---|---|
| Store reachable | Read directly; snapshot ignored |
| Store unreachable, snapshot present | Read snapshot; render its `as_of`; informational message naming the fallback |
| Neither | Build succeeds; annotated slots render "not annotated"; one informational message |
| Data present, key missing | Slot renders "no data"; warning naming the key |
| Data stale beyond threshold | Renders with a visible age indicator; warning |
| Data references an unknown covergroup | Warning — the model may have moved |
| `--strict-annotation` (CI/release) | All of the above become errors |

Owning the data path makes the middle rows *more* important, not less. A store that is
reachable from CI and not from a laptop is the normal case, and a build that fails
outside CI is a build nobody runs. The default-lenient, opt-in-strict split is what
allows one set of sources to serve both. Getting it backwards — failing when coverage
data is absent — is the most likely way to make the extension unusable in practice.

### 6.4 Linking out

Where the data is genuinely dynamic, the document's contribution is a **correct,
constructed deep link** — which is not nothing, since assembling one by hand requires
knowing the dashboard's URL scheme and the right identifiers.

Configure URL templates once:

```python
covsight_links = {
  'coverage_detail': 'https://cov.corp/{project}/{build}/cg/{cg_path}',
  'regression':      'https://ci.corp/{project}/runs?test={test}',
  'issues':          'https://jira.corp/issues/?jql=component={feature}',
}
```

Then every covergroup, test, and feature page carries a working link to its live view.
Documentation as the *index* into dynamic data, not a copy of it — which is a more
useful role than either extreme, and one the doc set is uniquely placed to fill because
it is the only artifact that knows the plan structure.

### 6.5 Determinism, and keeping annotation out of the hash

The companion document requires the extracted plan JSON to be byte-reproducible,
because a SHA-256-bound audit contract depends on it. Annotation threatens that
directly: if coverage figures land in the extracted JSON, the plan hash churns every
week for reasons that have nothing to do with the plan.

**Rule: the extracted plan artifact is annotation-free.** Annotation is published as a
*separate* artifact keyed by plan ID:

```
dut_testplan.yaml          # covsight testplan v1 — authored + derived; hash stable
dut_plan_annotation.json   # annotated; changes with every merge
```

Downstream consumers that want both perform the join themselves — using the same keys
the build uses. The plan hash then changes if and only if the plan changed, which is
what it was supposed to mean.

This is also why the plan is extracted as **covsight testplan v1** rather than as an
annotated report: the schema keeps coverage *bindings* (what should be covered) and
coverage *results* (what is) in different artifacts by design. §8.2 works through the
mapping.

The acyclicity argument of the companion document's §4.6 survives unchanged. Reading
the coverage store at build time (§5.1) is an inbound edge from the regression flow,
which produces it; the documentation build writes the plan, and nothing in the coverage
flow reads the documentation build's output to produce that store.

---

## 7. The documentation set

### 7.1 Composition

```
Verification Documentation
├── Overview               scope, environments, methodology, glossary
├── Verification Plan      features → testpoints → coverage refs → tests   [authored]
│   └── (60 feature documents, toctree; singlehtml/PDF for review)
├── Coverage Model         covergroup reference, model structure           [derived]
├── Testbench              architecture, agents, sequences, config         [derived: sphinx-systemverilog]
├── Test Catalog           test classes, plan mapping                      [derived]
├── Assertions & Formal    inventory, assumptions, sufficiency arguments   [authored + annotated]
├── Closure                status matrices, trend, gaps, unplanned         [derived + annotated]
├── Waivers                exclusions with justification and sign-off      [authored + annotated]
└── Traceability           spec ↔ plan ↔ coverage ↔ test matrices          [generated]
```

The first four sections are usable with no annotation at all, which matters for
adoption: a team gets a linked, checked, single-source document set before it wires up
any coverage plumbing.

### 7.2 Audience check

Worth validating the set against who actually reads it, because "documentation" for
verification serves five distinct readers with little overlap:

| Reader | Primary question | Served by |
|---|---|---|
| DV engineer | What am I supposed to build, and what exists already? | Plan, test catalog, testbench, coverage model |
| DV lead | Where are we, what is stuck, what is unjustified? | Closure, trend, stalled features, waiver register |
| Designer | What is being checked about my block, and what is waived? | Plan by feature, waivers, assertions |
| Architect / spec owner | Is every requirement verified, and by what? | Traceability matrices |
| Auditor / safety assessor | Show me the argument and the evidence chain | Traceability, waiver register, sign-off snapshot |
| New team member | How does any of this fit together? | Overview, testbench, plan |

The stalled-features view and the waiver register are the two that no current tool
produces and that a lead assembles by hand today. They are strong candidates for
early delivery — visible value, modest implementation.

### 7.3 Generated views

- **Traceability matrix** — requirement ↔ testpoint ↔ covergroup ↔ test, filterable,
  with per-axis closure percentages. The safety-standard deliverable, generated rather
  than maintained. Bidirectionality is the requirement that matters and is free once
  the graph exists.
- **Verification method summary** — per requirement: simulation / formal / emulation /
  inspection / not-verified. Directly answers the audit question.
- **Gap report** — requirements with no testpoint; testpoints with no coverage; coverage
  below target; tests not in the nightly. One page, four tables, and the most
  frequently useful page in the set.
- **Waiver register** — every waiver with justification, effect, approver, date, expiry
  and staleness state, grouped by feature.
- **Register-space closure** — registers and fields with no claiming testpoint, and
  fields whose declared SystemRDL behaviour has no corresponding check (§3.6).
- **Sign-off snapshot** — an immutable, milestone-tagged build of the closure and waiver
  views with full provenance. This is the artifact that gets attached to a tapeout
  review, and it is exactly the document set plus a git tag.

### 7.4 Directive surface

Keep it small — the companion document's ~7 plan directives plus roughly the same again
for this layer. The selection rule is unchanged: *a construct earns a directive only if
it needs identity, validation, or extraction.*

```rst
.. testpoint:: Back-to-back transactions on all ports
   :id: FEAT-012.tp_b2b

   .. covers:: rule:DUT/1.1.3, spec:DUT/port-transaction-demux

   .. coverage::
      :covergroup: cg_txn_type
      :covergroup: cg_addr_x_size
      :instance: tb.env.agent[*].mon.cg_txn
      :target: 95

   .. tests:: dut_b2b_test, dut_b2b_random_test

   Sustained back-to-back traffic across all four port boundaries, with
   the arbiter under contention.
```

Renders as authored prose, plus — when coverage data is reachable — a provenance-stamped
achievement figure, a sparkline, resolved links to the covergroup and test
documentation, and resolved spec text. With no coverage data, everything but the figure and
sparkline still works.

Roles and views:

| Construct | Purpose |
|---|---|
| `:cg:` / `:covergroup:` role | Link to a covergroup's documentation |
| `:test:` role | Link to a test class |
| `:rdl:ref:` role | Link to a register or field (provided by sphinx-peakrdl) |
| `.. coverage-summary::` | Achievement table, filtered by feature/env/scope |
| `.. coverage-trend::` | Sparkline or chart from the store's history |
| `.. unplanned-coverage::` | Model-minus-plan set difference |
| `.. gap-report::` | The §7.3 four-table view |
| `.. traceability-matrix::` | Configurable axes over the link graph |
| `.. waiver::` | Pull in a waiver record by id; render justification, effect, approval, staleness |
| `.. formal-status::` | Proof status, bound, assumption list |
| `.. waiver-register::` | Generated exclusion table |

Anything that is only presentation — filtering, sorting, grouping — should be a view
directive over the same underlying graph rather than a new entity type. Resist the
temptation to add entities.

---

## 8. Relationship to the surrounding tools

| Tool | Role | Boundary |
|---|---|---|
| **covsight-core** | Coverage data access, testplan schema, waiver schema, selector resolution | **The data layer.** The extension reads coverage through its API (§5.1) and emits its testplan schema (§8.1) |
| **covsight** | CLI, closure computation, reporting | Shares the schema; the documentation is a second front end over the same model |
| **sphinx-needs** | Specification-side rule and requirement authoring | Consumed via `needs.json`; sphinx-covsight does not depend on it |
| **sphinx-systemverilog** | Source-derived coverage model, testbench, test class documentation | Consumed as domain objects; the two extensions cross-reference, and sphinx-covsight does not parse SystemVerilog |
| **sphinx-peakrdl** | Register-map documentation and the compiled SystemRDL model | `:rdl:ref:` for plan→register references; register-space closure and field-property checks ride on its model (§3.6) |
| **pyucis** | UCIS reference implementation | Predecessor to covsight-core's model; relevant for UCIS XML interchange |
| **Vendor exclusion files** (Questa `.do`, VCS `.el`, IMC `.vRefine`) | Interchange | Export reliable, import best-effort — see the waiver design note |
| **sphinx-test-reports** | JUnit ingestion precedent | Pattern reuse |
| **Vendor plan formats** (OpenTitan hjson, vManager VPF, VC Planner, Questa) | Interchange | **Export targets** — reached through covsight's schema, not directly (§8.3) |

### 8.1 The extraction target is covsight testplan v1

The document set does not define a plan format. It **emits the schema covsight-core
already defines** (`schema.covsight.io/testplan/v1`,
[`testplan-schema.md`](../../../covsight-core/docs/testplan-schema.md)), and that choice
carries most of the interchange story with it:

- covsight-core already has readers for OpenTitan hjson, Cadence VPF, Synopsys VC
  Planner, and Questa, and the schema was designed as a **superset** of those four.
  Emitting into it means the documentation inherits that compatibility surface rather
  than re-deriving it.
- Closure computation, coverage binding resolution, goal rollup, and the CLI already
  operate on this model. A plan extracted from the document set is immediately a
  first-class covsight object — not a format that needs a converter written for it.
- It keeps one schema under one owner. A second plan schema living in a Sphinx
  extension would diverge within two releases.

### 8.2 Mapping the authoring model onto the schema

The companion document's authoring model maps cleanly, with two gaps worth naming now.

| Authored construct | covsight testplan v1 | Fidelity |
|---|---|---|
| Feature | `goals[]` — `id`, `title`, `desc`, `owner`, `status`, `tags`, nested | Exact; the hierarchy the schema already models |
| Testpoint | `testpoints[]` — `name`, `stage`, `desc`, `owner`, `priority`, `weight`, `tags`, `na` | Exact |
| `.. tests::` | `testpoints[].tests[]` | Exact |
| `.. coverage::` | `testpoints[].coverage[]` — `{type, path, desc}`, globs supported | Exact — and the same selector the waiver format uses |
| `.. covers::` (spec rules) | `testpoints[].requirements[]` — `{system, project, item_id, url}` | **Good fit.** `system: "spec"`, `item_id: "rule:DUT/1.1.3"`, `url` = the resolved anchor. The schema already has requirements tracing; the citation work fills it with something real |
| Covergroup declarations | `covergroups[]` with `coverpoints[]` and paths | Exact |
| Per-`env` policy output (`approach`, `reasoning`, `exit_criteria`, scores) | `custom: {utp: {…}}` | Namespaced bag, as the convention prescribes |
| **Verification environment** (IP sim / SoC sim / formal / emulation) | `tags[]` + `custom` | **Gap** — see below |
| **Artifact descriptions** | `tests[]` carries names only | **Gap** — see below |

Two schema questions follow, and both are better raised against covsight-core than
worked around in the extension:

1. **Environment is a first-class axis in every plan this design has looked at**, and
   the schema has no field for it. It is not a tag — it is the dimension the plan is
   organised by, with its own scope, difficulty, coverage score, and exit criteria per
   feature. Either a standard `env` field on the testpoint, or a documented convention
   that environments are the second level of the goal tree. Worth deciding deliberately;
   `custom` is the wrong long-term home for the plan's primary axis.
2. **`tests[]` is a list of names, and artifact descriptions have nowhere to go.** The
   reference plan carries 420 of them averaging ~460 characters. Either `tests[]` admits
   an object form (`{name, desc}`) alongside the string form, or they live in `custom`
   and are invisible to every other consumer. The object form is the better answer and
   is backwards-compatible.

Composition differs by direction and is worth stating: the Sphinx side does composition
with `toctree`, so extraction emits a **single already-merged plan** — lossless
outward, but it means an existing plan's `imports[]` structure is flattened if one is
ever migrated *in*. Acceptable, and the migration is one-way anyway.

Determinism (§6.5) applies to the emitted file: sorted keys, fixed ordering, no
timestamps in the payload. JSON for the hashed artifact; YAML additionally, for humans.

### 8.3 Vendor export — a gap in covsight-core, not in this design

The hoped-for property is that a plan authored once reaches whatever tool a team already
uses. **This does not work today**: covsight-core's vendor modules
(`testplan_vpf.py`, `testplan_vc_planner.py`, `testplan_questa.py`, `testplan_hjson.py`)
implement `import_*` only. `testplan_export.py` exports *closure results* — JUnit,
GitHub annotations, markdown summary — not plans. Writers are a required addition, and
they belong in covsight-core where the importers and their test data already are.

The good news is that export is the easy direction, for a structural reason: the schema
was built as a superset of these four formats, so **export is a projection, and every
field that will be lost is known in advance.**

| Target | Fit | Lost on export |
|---|---|---|
| **Questa XML** | Best — has both hierarchy and explicit coverage-path binding (`<metric type= coverage=>`) | Little; closest to lossless |
| **Cadence VPF** | Good — hierarchy plus `<attributes>`, which `custom` maps onto directly | Coverage binding shape differs; `tpCoverPoint` split |
| **VC Planner** | Good for hierarchy, `owner`/`status`/`priority`/`weight`; custom CSV columns carry `custom` | Weaker coverage binding |
| **OpenTitan hjson** | Flat — hierarchy must be flattened | Goals, coverage paths (hjson names covergroups only), owner/priority/weight, requirements |
| **Synopsys HVP** | Not yet imported either; `-userdata` accepts external annotation, which closes the results loop without either side owning the other | — |

Two disciplines make this trustworthy rather than approximate:

- **Every exporter reports what it dropped.** A projection that silently loses
  requirements tracing is worse than one that says it did. This is the mirror image of
  the waiver format's import fidelity ladder — testplans lose information on *export*
  (superset → subset), waivers lose it on *import* (tool-specific → normalized).
- **Round-trip is the acceptance test.** Import a vendor plan → covsight → export to the
  same vendor should be idempotent over the fields that format has. The importers and
  their test data already exist, so the test is cheap to build and it is the thing that
  keeps the exporters honest.

### 8.4 Why the document stays authoritative

Every established verification-plan format — OpenTitan hjson, Cadence vPlan, Synopsys
HVP — links plan entries to *coverage and tests* and expects requirements to arrive
from an external requirements tool. None models a normative source statement. That is
the gap this document set fills, and it is why the flow is one-way: the document is
authoritative, covsight testplan v1 is the extracted contract, and vendor formats are
projections of it. Importing the document *from* a vendor format cannot round-trip,
because the spec linkage has nowhere to live.

---

## 9. Adoption path

Each phase is independently valuable and none requires the next. The ordering is by
value-per-unit-effort, not by architectural layering.

| Phase | Adds | Requires | Delivers |
|---|---|---|---|
| **A. Plan as document** | Companion document's Phases 0–2, emitting covsight testplan v1 | Schema decisions of §8.2 | Authored plan, extracted plan, spec citation by reference |
| **B. Coverage model linkage** | Covergroup entities, `:cg:` role, plan→model and model→plan checks | covsight-core reader; shared selector (§5.1) | The four closure checks; unplanned-coverage report |
| **C. Test linkage** | `.. tests::`, reverse links, orphan-test report | Source parsing | Plan↔implementation loop closed |
| **D. Annotation** | Store reader, join layer, provenance, degradation, snapshots | B | Coverage on plan pages, with dates |
| **E. Trend** | Store history query, sparklines, stalled-features view | D | The weekly lead view |
| **F. Waivers** | `.. waiver::`, register, sign-off gate | Waiver schema v1 in covsight-core | Sign-off package generated, not assembled |
| **G. Formal** | Assumptions, proof status, sufficiency arguments | `ncdb/formal.py` surfacing | Bounded-proof sign-off documented |
| **H. Traceability views** | Matrices, gap report, verification-method summary | B + C | Audit deliverables |
| **J. Registers** | `:rdl:ref:` in plan entries, register-space closure, field-property gap check | sphinx-peakrdl + SystemRDL source | Register coverage gaps found before sign-off, not at it |
| **I. Vendor export** | Plan writers in covsight-core (§8.3) | A | One authored plan reaches any team's existing tool |

Three dependencies run into covsight-core rather than the extension, and are worth
scheduling there: the §8.2 schema decisions (gate A), waiver schema v1 (gates F), and
the plan writers (are I). None blocks B–E.

**B and C before D.** The linkage checks deliver value with no data pipeline at all,
and they are what make the annotation join reliable when it arrives — annotating a
graph whose keys have never been validated is how you get a confidently wrong page.

**E is cheap once D exists** and is the phase most likely to change how the team works
day to day, because it produces the only view that answers "are we going to make it?"

---

## 10. Open questions

1. **Where does `env` live in the testplan schema?** §8.2 — a standard field, or the
   second level of the goal tree. This is the plan's primary organising axis and
   `custom` is the wrong long-term home. Owned by covsight-core; gates extraction.
2. **Does `tests[]` admit an object form?** §8.2 — 420 artifact descriptions in the
   reference plan have nowhere to go otherwise. Backwards-compatible either way.
3. **Snapshot cadence and location.** Weekly into the doc repo is recommended (§5.2),
   but with the store reachable the snapshot is a lockfile rather than the data path,
   so a smaller one taken per release may be sufficient. Measure after a quarter.
4. **Instance-path normalization across tools.** §4.2 identifies this as the core
   technical asset. It needs a concrete survey of how Questa, VCS, Xcelium, Verilator,
   and covsight-core each name array and generate scopes before the API is fixed — and
   it is shared with the waiver selector, so it should be settled once.
5. **Does sphinx-covsight depend on sphinx-systemverilog, or define an interface?**
   An interface is more work and allows non-SystemVerilog flows (PyVSC, cocotb) to
   participate as first-class citizens. Given covsight-core already ingests from those
   flows, the interface is probably worth it — but it should be a deliberate decision.
6. **Target percentages: authored or policy?** Per-covergroup targets in the plan are
   more precise; a policy table by environment (as the companion document does for exit
   criteria) is far less to maintain. Probably: policy default, authored override.
7. **How much of the closure view should be interactive?** Static HTML tables are
   honest and cheap. Client-side filtering is a large usability gain for a large
   matrix. A JS-in-a-static-page approach stays within the "no live queries" rule and
   is likely the right compromise.
8. **Milestone snapshots — mechanism?** Git tag plus a published build is the obvious
   answer, but the sign-off package probably wants the provenance frozen *into* the
   artifact rather than resolved at build time.
9. **Does the plan carry per-testpoint coverage targets, or does the covergroup?**
   Affects whether "below target" is a plan property or a model property, and therefore
   which side of the join owns it.

---

## Appendix — References

Consulted 2026-09-15/16.

**Coverage data and interchange**
- Accellera UCIS 1.0 (June 2012) — data model, C API, XML interchange; working group
  currently inactive: <https://www.accellera.org/downloads/standards/ucis>
- PyUCIS — Python UCIS implementation; XML/SQLite/YAML back ends; imports from
  Verilator, cocotb-coverage, AVL; merge and report CLI:
  <https://fvutils.github.io/pyucis/introduction.html>

**Verification plan formats**
- OpenTitan testplanner — hjson testpoints and covergroups, expanded inline into the DV
  document as a table and annotated with simulation results:
  <https://opentitan.org/book/util/dvsim/doc/testplanner.html>
- Antmicro testplanner (June 2025) — hjson plans linked to RTL, documentation, and
  cocotb results; HTML/XLSX/hjson output; per-plan summaries and a tracking dashboard:
  <https://antmicro.com/blog/2025/06/automating-design-and-dv-tracking-with-testplanner>
- Synopsys HVP — hierarchical plans in XML, URG back-annotation, `-userdata` for
  externally supplied non-coverage data:
  <https://www.design-reuse.com/article/61014-smart-tracking-of-soc-verification-progress-using-synopsys-hierarchical-verification-plan-hvp-/>

**Closure, waivers, sign-off**
- OpenTitan DV methodology — exclusion review at sign-off, checksum-based staleness
  detection, designer sign-off on every exclusion:
  <https://opentitan.org/book/doc/contributing/dv/methodology/index.html>
- Sign-off criteria overview — the sign-off report as coverage + waivers + open bugs +
  regression status: <https://chipverify.com/verification/sign-off-criteria>
- Bounded-proof sign-off with formal coverage — why the assumption set and sufficiency
  argument are the durable artifacts:
  <https://verificationacademy.com/topics/formal-verification/bounded-proof-sign-off-with-formal-coverage/>
- A Coverage-Driven Formal Methodology for Verification Sign-off (DVCon):
  <https://dvcon-proceedings.org/wp-content/uploads/a-coverage-driven-formal-methodology-for-verification-sign-off.pdf>

**Traceability and metrics**
- ISO 26262 bidirectional traceability — hazard → goal → requirement → implementation →
  verification → result:
  <https://www.sodiuswillert.com/en/blog/maintaining-iso-26262-traceability-across-automotive-suppliers>
- No Country For Old Men — a modern take on metrics-driven verification (DVCon);
  dashboard-vs-tool separation:
  <https://dvcon-proceedings.org/wp-content/uploads/no-country-for-old-men-a-modern-take-on-metrics-driven-verification-paper.pdf>
- IP-XACT (IEEE 1685) — register and address-map metadata as a generation source for
  RTL, UVM models, headers and documentation:
  <https://accellera.org/images/downloads/standards/ip-xact/IPXACT-2022_user_guide.pdf>

**Sphinx ecosystem**
- sphinx-peakrdl — `:rdl:ref:` cross-references into a compiled SystemRDL register
  model, inline register content, links to PeakRDL-HTML:
  <https://sphinx-peakrdl.readthedocs.io/>
- PeakRDL — the SystemRDL toolchain the above builds on:
  <https://peakrdl.readthedocs.io/>
- sphinx-test-reports — JUnit XML into sphinx-needs items; the precedent for
  last-known-status annotation: <https://sphinx-test-reports.readthedocs.io/>
- mlx.traceability — `item-list` / `item-matrix` generated traceability views:
  <https://melexis.github.io/sphinx-traceability-extension/>
- Doorstop — suspect links over item fingerprints with `review` / `clear`; the model
  generalized in §6.2: <https://doorstop.readthedocs.io/>
