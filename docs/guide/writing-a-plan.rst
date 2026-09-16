Writing a plan
==============

**At the end of this guide** you will be able to author a verification plan that
renders as a reviewable document and extracts as a covsight testplan, in either
reStructuredText or MyST.

**Prerequisites:** ``pip install sphinx-covsight``.  The citation backends are
optional; write the plan before the RTL exists if that is when the plan is
needed.

The shape of a plan
-------------------

Three nested constructs, and three leaf ones:

.. code-block:: text

   feature                 what is being verified, and what it is accountable to
     env                   where it is verified
       testpoint           one verification task
         covers            what this testpoint is accountable to
         coverage          which coverage objects close it
         tests             which tests exercise it

A construct earns a directive only if it needs **identity, validation, or
extraction**.  Everything else is prose, and prose is the majority of a good
plan.

.. covsight-directive-table::

``feature``
-----------

The review unit.  Features may nest.

.. literalinclude:: ../example/plan/feat_baud.rst
   :language: rst
   :start-after: .. doc:feature-start
   :end-before: .. covers::

``:id:`` is authored and stable — it is what survives retitling, and it is what
anything external references.  Everything else is optional.

``env``
-------

The plan's second axis: the same feature verified in simulation and in formal is
two environments, not two features.  ``env`` carries the numbers that drive
scoring, and nothing else:

.. literalinclude:: ../example/plan/feat_baud.rst
   :language: rst
   :start-at: .. env:: formal
   :end-before: .. testpoint:: Divisor write

What is *absent* is the point.  No approach, no reasoning, no exit criteria:
those come from ``covsight_env_policy`` in ``conf.py``, so changing verification
policy is a one-line diff rather than an edit across every feature.

``testpoint``
-------------

The extraction unit.

.. literalinclude:: ../example/plan/feat_baud.rst
   :language: rst
   :start-at: .. testpoint:: All supported divisor values
   :end-before: .. testpoint:: Divisor below

``:id:`` is **optional**.  When omitted it is derived as
``<feature-id>.<env>.<slug of the title>``, which is the right default: testpoint
ids are numerous, and nobody wants to hand-maintain them.  A derived id changes
if the testpoint is retitled or moved between environments — visible in the
extracted diff, which is the right place for it to be visible.  Write an explicit
``:id:`` for any testpoint something external references, or set
``covsight_require_explicit_testpoint_ids = True`` to be warned about every
derived one.

A testpoint with no ``.. tests::`` extracts with ``na: true``.  If that is
deliberate, say so with ``:na:``; otherwise the build warns
(``covsight.testpoint-unmapped``), which is how "we never wrote the test" stops
being invisible.

``covers`` — the three citation prefixes
----------------------------------------

All three answer one question — *what is this accountable to?* — so all three
land in ``requirements[]``.

============  ==========================================  ====================
Prefix        Resolved against                            Absent when
============  ==========================================  ====================
``rule:``     ``needs.json`` from the specification        ``covsight_needs_json`` unset
``rdl:``      the compiled SystemRDL model                 sphinx-peakrdl not installed
``sv:``       the SystemVerilog domain                     sphinx-systemverilog not installed
============  ==========================================  ====================

.. literalinclude:: ../example/plan/feat_framing.md
   :language: markdown
   :start-at: rule:UART_1_2_1, rule:UART_1_2_2,
   :end-before: ```

``covers`` takes a **body**, one or more targets per line, so a long citation
list wraps cleanly.  A single-line argument form is accepted too:
``.. covers:: rule:UART_3_2_1``.

When a backend is absent the citation is still recorded — without a url — and
the build emits one informational message for the whole backend, not one per
citation.  This is what makes it reasonable to cite RTL that does not exist yet.

``coverage`` — and the namespace caveat
---------------------------------------

One ``<type>: <path>`` binding per line:

.. literalinclude:: ../example/plan/feat_baud.rst
   :language: rst
   :start-at: .. coverage::
   :end-before: .. tests::

The path is a **UCIS instance path** — where the coverage object lives in the
coverage database — while ``sv:`` citations name **SystemVerilog declaration
paths**.  Those are different namespaces, and conflating them is the single
easiest mistake to make here.  ``uart_env.uart_cfg_cg`` is an instance;
``uart_pkg::uart_cfg::uart_cfg_cg`` is a declaration.  They are both correct, and
they are not interchangeable.

Because of that, validation checks the **leaf name only**, against the ``sv``
domain, and only for ``covergroup`` and ``coverpoint`` bindings.  A miss is a
warning, never an error, and is suppressible:

.. code-block:: python

   covsight_validate_coverage_bindings = False     # if the noise is not worth it

``tests``
---------

Test names, with ``{key}`` placeholders expanded from ``covsight_substitutions``:

.. literalinclude:: ../example/plan/feat_baud.rst
   :language: rst
   :start-at: .. tests:: uart_baud_{baud}_test
   :end-at: .. tests:: uart_baud_{baud}_test

With ``covsight_substitutions = {"baud": ["9600", "115200", "460800"]}`` that one
line extracts as three test names, and the unexpanded template is preserved in
``source_template``.  Multiple keys expand cartesian-wise over sorted key names,
so the result does not depend on dictionary ordering.

Policy in ``conf.py``
---------------------

.. literalinclude:: ../example/plan/conf.py
   :language: python
   :start-at: covsight_env_policy = {
   :end-at: covsight_score =

``{feature}`` interpolates the enclosing feature's title and ``{env}`` the
environment name.  ``covsight_score`` is an arithmetic **expression string**, not
a lambda, over ``difficulty`` and ``coverage`` — which is what lets the policy be
hashed into the provenance sidecar, so the derived scores are auditable.  Calls,
attribute access and subscripts are rejected when the expression is compiled.

The policy can equally live in a YAML file (``covsight_env_policy_file``); the
two forms produce identical fingerprints for identical content.

MyST and reStructuredText, side by side
---------------------------------------

One directive implementation serves both.  The same feature in each:

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - reStructuredText
     - MyST
   * - .. code-block:: rst

            .. feature:: Character framing
               :id: FEAT-001

               Prose.

               .. covers::
                  rule:UART_1_1_1

               .. env:: ip_simulation
                  :difficulty: 3

                  .. testpoint:: Start bit
                     :stage: V1

                     .. tests:: uart_smoke_test
     - .. code-block:: markdown

            :::::{feature} Character framing
            :id: FEAT-001

            Prose.

            ```{covers}
            rule:UART_1_1_1
            ```

            ::::{env} ip_simulation
            :difficulty: 3

            :::{testpoint} Start bit
            :stage: V1

            ```{tests}
            uart_smoke_test
            ```
            :::
            ::::
            :::::

Two rules keep this cheap, and they constrain the directive design rather than
your authoring:

1. **No repeated options.**  A duplicated option key is a hard error in RST and
   is *silently dropped* in MyST, so list-valued inputs take a body instead.
2. **No MyST YAML-block options.**  They are not valid RST, and list values
   arrive flattened anyway.

The fence-depth convention
~~~~~~~~~~~~~~~~~~~~~~~~~~

Markdown fences must be strictly longer than anything they contain, so nesting
three levels with colon fences alone needs ``:::::`` → ``::::`` → ``:::``, and
adding a level means widening every enclosing fence.

Two conventions keep that manageable:

- **Leaf directives use backtick fences** — a triple-backtick fence opening
  ``{covers}`` — since backtick and colon fences nest independently.  That buys
  one free level, and the example above relies on it.
- **One feature per file**, which is the composition model anyway, so the
  outermost fence is the feature and depth tops out at four.

Composition
-----------

There is no plan-level import mechanism, because Sphinx already has one:

.. literalinclude:: ../example/plan/index.md
   :language: markdown
   :start-at: ```{toctree}
   :end-before: ```

Extraction walks the whole project and emits an already-merged plan, so
``imports[]`` in the output is always empty.

Authoring before the RTL exists
--------------------------------

This is the normal case, not an edge case.  Write ``rdl:`` and ``sv:`` citations
for objects that do not exist yet; they extract as recorded requirements without
urls, and start resolving the day the RTL lands in the same documentation set.
Write coverage bindings for covergroups that have not been coded — they are
authored knowledge that would otherwise be written twice.
