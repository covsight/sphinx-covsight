One rule, end to end
====================

The claim this extension makes is that a plan can be prose a human reviews *and*
a graph a tool walks, without being written twice.  This page is that claim
checked: one rule from the specification, followed through every representation
it has, in the example that ships with the package.

The rule is ``UART_3_2_1``, *divisor programmability*.  Nothing below is
paraphrased — every block is included from the example's source, and every link
goes to the built page.

1. The rule
-----------

It begins as a normative statement in the specification.  It earns an id because
a testpoint can pass or fail with respect to it; the paragraphs around it do not.

.. literalinclude:: spec/uart.md
   :language: markdown
   :start-at: :::{rule} Divisor programmability
   :end-before: :::{rule} Supported divisor range

Published as `spec/uart.html#UART_3_2_1 <spec/uart.html#UART_3_2_1>`_, and — the
part that matters downstream — as an entry in the ``needs.json`` catalogue that
build emits.

2. The register field that implements it
----------------------------------------

"The divisor" in the specification and "the divisor" in the register map have to
be the same object rather than two strings that happen to look alike.  The
register map is SystemRDL, compiled in the plan's own build:

.. literalinclude:: rtl/uart_regs.rdl
   :language: text
   :start-at: name = "Baud divisor"
   :end-at: BAUD_DIV[15:0]
   :dedent: 8

Rendered at `plan/registers.html <plan/registers.html>`_.

And the logic the rule constrains.  "Shall take effect at the next character
boundary" is a statement about *when* the programmed value is read, so the rule
is satisfied by there being exactly one instant at which it is read:

.. literalinclude:: rtl/uart_tx.sv
   :language: systemverilog
   :start-at: // The one instant at which the programmed configuration is read.
   :end-at: busy        <= 1'b1;
   :dedent: 12

Rendered at `plan/design.html <plan/design.html>`_.  The design is not normally
part of a verification plan's doc set; it is here so that every end of every
citation in this example is a real object rather than a plausible name.

3. The feature accountable for it
---------------------------------

The plan declares a feature and states what it is accountable to.  Two spec
rules and one register field, in one ``covers`` body:

.. literalinclude:: plan/feat_baud.rst
   :language: rst
   :start-at: .. covers::
   :end-at: rdl:uart.CTRL.BAUD_DIV
   :dedent: 3

Three citations, three backends, one syntax.  ``rule:`` resolves against the
pinned catalogue, ``rdl:`` against the compiled register map, and ``sv:``
against the parsed SystemVerilog.  A citation whose target has been deleted or
renumbered raises ``covsight.citation-unresolved``, which is the entire reason
for citing by reference instead of quoting text that cannot go stale visibly.

4. The testpoint
----------------

One verification task.  This is the unit that gets extracted, and the level at
which "did we actually test that?" becomes answerable:

.. literalinclude:: plan/feat_baud.rst
   :language: rst
   :start-at: .. testpoint:: All supported divisor values
   :end-at: .. tests:: uart_baud_{baud}_test, uart_baud_random_test
   :dedent: 6

Note what the testpoint does **not** say.  There is no verification approach, no
reasoning, no exit criteria and no score.  Those belong to the environment, not
to the task, and they come from ``conf.py``:

.. literalinclude:: plan/feat_baud.rst
   :language: rst
   :start-at: .. env:: ip_simulation
   :end-at: :coverage: 8
   :dedent: 3

Two numbers in the plan.  The approach text, the reasoning, the exit criteria
and the arithmetic all live in policy:

.. literalinclude:: plan/conf.py
   :language: python
   :start-at: covsight_score =
   :end-at: covsight_score =

which is why the extracted goal carries ``"overall_score": 64`` — ``(11 - 3) *
8`` — that nobody typed.  Change the scoring policy and every score in the plan
changes together, and the provenance sidecar records which policy produced them.

5. The tests that exercise it
-----------------------------

``.. tests:: uart_baud_{baud}_test, uart_baud_random_test`` is a template.  The
substitution is declared once:

.. literalinclude:: plan/conf.py
   :language: python
   :start-at: covsight_substitutions =
   :end-at: covsight_substitutions =

and the artifact carries the expansion, in authored order, alongside the
template it came from:

.. code-block:: json

   {
     "source_template": "uart_baud_{baud}_test, uart_baud_random_test",
     "tests": [
       "uart_baud_9600_test",
       "uart_baud_115200_test",
       "uart_baud_460800_test",
       "uart_baud_random_test"
     ]
   }

Keeping ``source_template`` is what makes the expansion reviewable: a reader who
sees four tests can see the one line that produced them.  The expansion is
cartesian over sorted substitution keys, and ``tests`` keeps authored order
afterwards, so the list is stable across builds.

All four names are classes in the example's testbench, and each one is a handful
of lines because the plan's distinction between them is a difference of
stimulus, not of structure:

.. literalinclude:: verif/uart_tb_pkg.sv
   :language: systemverilog
   :start-at: // 9600 baud from a 50 MHz reference.
   :end-before: // Random divisors
   :dedent: 3

This is the step that is easiest to skip and worst to skip.  A plan naming
``uart_baud_460800_test`` reads exactly like a plan naming a test nobody ever
wrote — same prose, same review, same green tick.  Building the testbench source
alongside the plan is what tells the two apart, and the example's test suite
fails if any name in a ``tests`` body stops resolving.

A testpoint with no ``tests`` and no ``:na:`` raises
``covsight.testpoint-unmapped``.  That warning is the one that makes "we never
wrote the test" visible, and it is the least suppressible thing in the extension.

6. The coverage that closes it
------------------------------

The covergroup is declared in SystemVerilog and documented in the same build:

.. literalinclude:: verif/uart_cov.sv
   :language: systemverilog
   :start-at: // Divisor values, with the range boundaries called out.
   :end-before: // Parity modes.
   :dedent: 9

The plan binds to it by **UCIS instance path** — ``uart_env.uart_cfg_cg`` — not
by the declaration path ``uart_pkg::uart_cfg::uart_cfg_cg`` that an ``sv:``
citation uses.  Two namespaces, deliberately different: a citation names a
declaration, a binding names a thing that exists at run time and accumulates
data.  Substituting one for the other is the single easiest mistake in this
extension, and the reason the example uses both within a few lines of each other.

The instance path is not a guess, either.  ``option.per_instance`` in the
covergroup and ``option.name`` in the environment's ``build`` are between them
what put ``uart_cfg_cg`` in the coverage database under that name — see
`plan/testbench.html <plan/testbench.html>`_.  A binding is only as good as the
run that produces the database it names, which is why a binding that resolves
to nothing is a warning here and never an error: plans routinely lead the
testbench.

7. What comes out
-----------------

The extraction is a side effect of the plan's own documentation build, so the
page a reviewer reads and the artifact a tool consumes are produced by one pass
over one source.  The rule arrives as a resolved requirement:

.. code-block:: json

   {
     "name": "FEAT-002.tp_divisors",
     "stage": "V2",
     "priority": "high",
     "requirements": [
       {
         "item_id": "UART_3_2_1",
         "system": "spec",
         "url": "https://dvkit.org/covsight/sphinx-covsight/example/spec/uart.html#UART_3_2_1"
       }
     ]
   }

That url is where the specification is published.  Follow it and you are back at
step 1.

Reading it backwards
--------------------

The chain is more useful in the other direction, because that is the direction
the awkward questions arrive from.  Given ``FEAT-002.tp_divisors`` in the
artifact, and nothing else, you can recover:

===============================  ==============================================
what it is accountable to        ``UART_3_2_1``, ``UART_3_2_2`` — with urls to
                                 the published specification
what implements it               ``uart.CTRL.BAUD_DIV``, via the feature's own
                                 ``covers``
which tests exercise it          four, and the template they were expanded from
what closes it                   ``uart_cfg_cg`` and its ``baud_div_cp``
which environment, and how       ``ip_simulation``; approach, reasoning and exit
                                 criteria from policy, with a hash of that
                                 policy in the provenance sidecar
which specification snapshot     ``needs_json_sha256`` in the sidecar
===============================  ==============================================

None of that was authored twice, and none of it is prose that has to be trusted.

Where it can still break
------------------------

Honestly, three places, and the example is arranged so each one is visible:

**The pin goes stale.**  The plan resolves ``rule:`` citations against a
committed copy of the catalogue.  If the specification changes and nobody
re-pins, the plan is verified against a snapshot that no longer exists.  The
example's test suite rebuilds the specification and diffs the catalogue for
exactly this reason.

**A rule is renumbered.**  There is no alias map, by design — renumbering should
not be cheap while anything external references the ids.  The citation goes
unresolved, loudly, and ``covsight_strict_citations = True`` makes it an error.

**A coverage binding names something that does not exist yet.**  This is normal
when the plan leads the RTL, so it is a warning and never an error.  It starts
resolving when the source lands.

What is *not* on that list is the failure this design exists to prevent: the
plan and the specification quietly disagreeing because the plan copied the text.
It cannot, because it never has the text.
