# UART Verification Plan

This plan is a document a reviewer reads and a graph a tool walks.  Each feature
states what is being verified and what it is accountable to; each testpoint
states how it will be exercised and which tests do the exercising.

What is deliberately **absent** from the feature pages is as important as what
is present: no approach text, no reasoning, no exit criteria, no scores, and no
quoted specification text.  Policy fields come from `conf.py`, and cited text
comes from the specification.  A reviewer reading a diff of these pages sees
only decisions.

```{toctree}
:maxdepth: 2

feat_framing
feat_baud
registers
testbench
```

## Reading the plan

| Directive | Means |
|---|---|
| `feature` | A reviewable unit of functionality, with a stable id |
| `env` | A verification environment the feature is exercised in |
| `testpoint` | One verification task, the unit that gets extracted |
| `covers` | What this is accountable to: a spec rule, a register field, an SV declaration |
| `coverage` | Which coverage objects close this testpoint |
| `tests` | Which tests exercise it, before `{key}` expansion |

Extract the plan with:

```console
$ covsight-testplan build docs/example/plan -o testplan.json
```
