Getting the specification's rules into the plan
===============================================

**At the end of this guide** the plan repository resolves ``rule:`` citations
against the specification's published catalogue, links to the rendered rule,
and tells you when a citation has gone stale.

**Prerequisites:** a specification that publishes ``needs.json``
(:doc:`writing-a-spec`), and sphinx-covsight installed in the plan project.

What ``needs.json`` contains
----------------------------

sphinx-needs writes a versioned document:

.. code-block:: json

   {
     "current_version": "1.0",
     "versions": {
       "1.0": {
         "needs": {
           "UART_3_2_1": {
             "id": "UART_3_2_1",
             "type": "rule",
             "title": "Divisor programmability",
             "docname": "uart",
             "lineno": 57,
             "content": "The divisor **shall** be writable while the link is idle."
           }
         }
       }
     }
   }

Three fields are load-bearing for sphinx-covsight: ``id`` is what a citation
names, ``title`` becomes the link's tooltip, and ``docname`` builds the link
target.  Note that the body is ``content``, not ``description`` — if you are
writing your own consumer, that is the field.

Configuring the plan project
----------------------------

.. literalinclude:: ../example/plan/conf.py
   :language: python
   :start-at: covsight_needs_json
   :end-at: covsight_spec_base_url

``covsight_needs_json`` is relative to ``conf.py``.  ``covsight_spec_base_url``
is prepended to the generated link, so citations point at the *published*
specification rather than at a path that only exists on a build machine.  A
resolved citation lands in the plan as:

.. code-block:: json

   {"system": "spec",
    "item_id": "UART_3_2_1",
    "url": "https://uart-spec.example/uart.html#UART_3_2_1"}

Pinned copy, or fetched artifact?
---------------------------------

The specification and the plan are usually separate repositories with separate
release cadences, so the catalogue has to cross a boundary.  Two options, and
the trade-off is real:

**A pinned copy committed to the plan repository** (what the example does, at
``docs/example/plan/_spec/needs.json``)

- The plan builds reproducibly, offline, at any commit, forever.
- The plan's git history shows exactly when the specification it was verified
  against changed, which is the audit question people actually ask.
- It goes stale silently unless something updates it.  Add a CI job that rebuilds
  the specification and diffs the catalogue — the example's test suite does
  exactly this in ``test_pinned_needs_json_matches_the_spec``.

**Fetched from the specification's CI artifact at build time**

- Always current.
- The plan's build now depends on the network and on another project's CI
  retention policy, and an old plan commit can no longer be rebuilt as it was.

For an MVP, pin.  The pinned file is a dependency declaration, and treating it
as one — reviewed, diffed, deliberately bumped — is the honest version of what a
fetch does implicitly.

Detecting stale citations
-------------------------

Three failure modes, three behaviours:

===================================  ==================================================
Situation                            What happens
===================================  ==================================================
Rule exists                          ``url`` and ``title`` filled in
Rule deleted or renumbered           ``covsight.citation-unresolved`` warning naming the
                                     citation and the line it is on
``needs.json`` missing entirely      one informational message for the whole build;
                                     every ``rule:`` citation is recorded without a url
===================================  ==================================================

The third row is deliberate.  A plan authored before the specification is
published must still build and still extract — with the citations recorded, so
nothing an author wrote is lost.  What it must *not* do is emit one warning per
citation, because then the build log is unreadable and people stop writing
citations.

In CI, promote the second row to a hard failure:

.. code-block:: python

   covsight_strict_citations = True

Then a deleted rule fails the plan's build, which is the whole point of citing
by reference.

What happens when the specification renumbers
---------------------------------------------

Every affected citation warns, with its file and line.  That is noisy by design:
a renumbering is a change to the interface between two repositories, and it
should cost something.

There is no alias map in the MVP.  It was considered and deferred: an alias map
makes renumbering cheap, and renumbering *should not be* cheap while anything
external references the ids.  If the need arises — a genuine mass migration,
once — the mechanical fix is a search-and-replace over the plan, reviewed as one
commit.

Checking what resolved
----------------------

.. code-block:: console

   $ covsight-testplan show docs/example/plan --summary
   plan:         uart
   coverage:     6
   goals:        6
   requirements: 10
   testpoints:   6
   tests:        10
   citations:    10/10 resolved

The last line is the one to watch over time.  A gradual drift away from 100% is
how citation rot looks before anyone notices it.
