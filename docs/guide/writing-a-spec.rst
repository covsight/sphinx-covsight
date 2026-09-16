Writing a specification a plan can cite
=======================================

**At the end of this guide** you will have an architecture specification whose
normative statements each carry a stable id, published as a ``needs.json`` that
a verification plan in another repository can resolve citations against.

**Prerequisites:** a Sphinx project for the specification, and
``pip install sphinx-needs``.  sphinx-covsight is *not* needed here — the
specification knows nothing about the plan.

Why rules need ids
------------------

A verification plan that quotes specification text goes stale silently: the
specification is edited, the quotation is not, and nothing in either build
notices.  The alternative is a citation — the plan names a rule, and the build
resolves the name.  When the rule moves, the link follows it; when the rule is
deleted, the plan's build warns.

That only works if the thing being cited has an identity of its own.  A section
number is not an identity: it changes when a section is inserted above it.

What earns an id
----------------

A rule is a statement that can be *verified against*.  Use this test: could a
testpoint pass or fail with respect to it?

Earns an id:

- "The receiver **shall** re-sample the start bit at the half-bit point."
- "A write to the divisor while a character is in flight **shall not** change
  the bit clock until that character completes."

Does not earn an id:

- "The UART transmits and receives 8-bit characters over a two-wire link."
  (explanation — nothing to verify)
- A timing diagram, a register-map table, or an example of use.  (evidence, not
  obligation)

Erring towards fewer, larger rules is the right failure mode.  A plan that cites
one rule per testpoint is readable; a plan that cites nine is not, and usually
means the rules were split along documentation boundaries rather than along
verification boundaries.

The id charset, and why it is narrower than it looks
----------------------------------------------------

**Use ``[A-Za-z0-9_]`` only.**  sphinx-needs' default ``needs_id_regex``
(``^[A-Za-z0-9_]{5,}``) already enforces this, and the temptation is to widen it
so ids can read hierarchically — ``UART/3.2.1``, ``UART-3.2.1``, ``UART.3.2.1``.

Needs with those ids are created successfully and appear correctly in
``needs.json``, so the problem is not visible where you would look for it.  What
fails is the cross-reference role:

.. code-block:: text

   WARNING: linked need UART.3.2.1 not found [needs.link_ref]
   WARNING: linked need UART-3.2.1 not found [needs.link_ref]
   WARNING: linked need UART/3.2.1 not found [needs.link_ref]
   (UART_3_2_1 — no warning)

``.`` is reserved by sphinx-needs for need *parts* (``need_id.part_id``); ``-``
and ``/`` fail in the link parser.  So the specification's own inline
``{need}`` references break, even though the plan's ``rule:`` citations — which
read ``needs.json`` directly — would have resolved.

Get the hierarchy from a prefix convention instead: ``UART_3_2_1``.
sphinx-covsight warns (``covsight.citation-id-charset``) when a ``rule:``
citation target strays outside the charset, precisely so this is caught in the
plan rather than in the specification's rendered output.

Setting up sphinx-needs
-----------------------

One need type, one id scheme, and JSON output:

.. literalinclude:: ../example/spec/conf.py
   :language: python
   :start-at: extensions =
   :end-at: needs_reproducible_json

``needs_reproducible_json`` matters more than it looks: without it the published
catalogue carries a timestamp, so every specification build produces a different
file and the plan repository cannot tell a real change from a rebuild.

Writing rules
-------------

A rule is a directive with a title, an id, and a body.  In MyST:

.. literalinclude:: ../example/spec/uart.md
   :language: markdown
   :start-at: :::{rule} Divisor programmability
   :end-before: :::{rule} Supported divisor range

The same thing in reStructuredText is ``.. rule:: Divisor programmability`` with
the options indented beneath it; both produce identical entries in
``needs.json``.

Keep the body to the obligation.  Rationale, alternatives considered, and worked
examples belong in the surrounding prose, which is not part of the rule and is
not what the plan cites.

Id stability under edit
-----------------------

The id is a promise.  Once a plan cites ``UART_3_2_1``:

- **Editing the rule's wording** is fine; the citation still points at the
  current obligation, which is the point.
- **Splitting a rule** means the old id must survive on one of the halves, or
  every citing testpoint must be revisited deliberately.  There is no automatic
  answer to which half inherits it — that is a review decision.
- **Deleting a rule** must break the plan's build.  That is the feature.  Set
  ``covsight_strict_citations = True`` in the plan's CI so it is an error rather
  than a warning.

Renumbering to make ids "tidy" costs more than it returns.  Ids are for machines;
titles are for people.

Publishing
----------

Two files matter:

``needs.json``
    The rule catalogue.  Written to the build output directory by
    ``needs_build_json = True``.  This is what the plan repository consumes.

``objects.inv``
    Sphinx's standard inventory, for ``intersphinx`` from other documentation.
    Not required by sphinx-covsight, but publish it anyway — it is free.

.. code-block:: console

   $ sphinx-build -b html spec/ _build/spec
   $ ls _build/spec/needs.json

How the plan repository gets hold of that file is the subject of the next
guide: :doc:`extracting-rules`.
