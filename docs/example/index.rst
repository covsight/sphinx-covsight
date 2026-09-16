The worked example
==================

Every snippet in these guides is quoted from one worked example rather than
written for the page, so nothing in the documentation can drift away from
something that builds.  The same example is the extension's test fixture: its
extracted artifact is committed, diffed on every push, and rebuilt twice to
prove it is byte-stable.

It is a miniature UART.  Deliberately miniature — eight rules, two features, six
testpoints — because a large example is not read, and because everything it
demonstrates it demonstrates at this size.

What is in it
-------------

==============================  ==============================================
``docs/example/spec/``          The architecture specification.  Eight ``rule``
                                needs across framing, parity and baud rate, and
                                the ``needs.json`` catalogue they publish.
``docs/example/plan/``          The verification plan.  Two features, two
                                environments, six testpoints, citing all three
                                backends.  One page is reStructuredText and one
                                is MyST, to show the formats compose.
``docs/example/rtl/``           The design: ``uart_regs.rdl``, the register
                                map the plan's ``rdl:`` citations name, and the
                                UART itself — transmitter, receiver, register
                                block, interface, and the two property modules
                                the ``formal`` environment runs.
``docs/example/verif/``         The testbench: the covergroup the plan binds
                                to, and a class for **every** test name the
                                plan mentions.
``docs/example/_golden/``       The extracted ``testplan.json``, committed.
                                CI fails if a fresh extraction differs from it.
==============================  ==============================================

The design and the testbench are real rather than sketched, and the example's
test suite elaborates them.  That is what lets the plan's claims be checked
instead of taken on trust: a ``tests`` body naming a class nobody wrote reads
exactly like one naming a class that exists, and only a build can tell them
apart.

Why it is two Sphinx projects
-----------------------------

Because that is the arrangement the extension is built for, and collapsing it
would demonstrate something nobody has.

A specification and the plan that verifies it are usually owned by different
people, live in different repositories, and release on different cadences.  The
specification publishes a catalogue; the plan consumes it.  Nothing else crosses
the boundary — in particular the plan never copies the specification's text,
which is the whole point of citing by reference.

So ``spec/`` and ``plan/`` each have their own ``conf.py``, their own extension
set, and their own build.  The plan resolves its ``rule:`` citations against a
*pinned copy* of the catalogue at ``plan/_spec/needs.json``, exactly as a real
plan repository would, and a test rebuilds the specification to prove that pin
is current.  See :doc:`../guide/extracting-rules` for the pinned-versus-fetched
trade-off.

Read it
-------

Both projects are published alongside this documentation:

`The UART specification <spec/index.html>`_
   Where a ``rule:`` citation lands.  Every rule id in the extracted plan is an
   anchor on one of these pages.

`The UART verification plan <plan/index.html>`_
   The plan as a reviewer reads it, with its
   `register map <plan/registers.html>`_ compiled from SystemRDL, and the
   `design <plan/design.html>`_ and
   `testbench collateral <plan/testbench.html>`_ documented from SystemVerilog,
   all in the same build.

`The extracted testplan <plan/testplan.json>`_
   What that build emits, one directory from the plan it came from.  Its
   `provenance sidecar <plan/testplan.provenance.json>`_ carries everything that
   would otherwise perturb the hash.

:doc:`traceability` follows a single rule through all of them.

Run it yourself
---------------

The whole site — this documentation and both example projects, nested under it —
builds with one script:

.. code-block:: console

   $ docs/build.sh
   ==> spec
   ==> plan
   ==> main
   documentation:   docs/_build/html/index.html
   example spec:    docs/_build/html/example/spec/index.html
   example plan:    docs/_build/html/example/plan/index.html
   extracted plan:  docs/_build/html/example/plan/testplan.json

Use the script rather than a bare ``sphinx-build docs``: the pages here link
into the two sub-builds with relative hrefs that Sphinx neither resolves nor
checks, so building this project alone produces a doc set whose example links
are dead.

To extract the plan on its own, without producing documentation, and to run the
gate CI runs:

.. code-block:: console

   $ covsight-testplan build docs/example/plan -o testplan.json
   $ covsight-testplan show  docs/example/plan --summary
   $ covsight-testplan check docs/example/plan --against docs/example/_golden/testplan.json

Then change something and watch what happens.  Editing a testpoint's prose
changes the artifact and the ``check`` fails, which is correct — the plan
changed.  Reordering the tags on a testpoint does *not* change it, because tags
are a set and are sorted at emit.  Deleting a rule from the specification and
re-pinning the catalogue leaves the citation dangling and raises
``covsight.citation-unresolved``.

.. toctree::
   :maxdepth: 1
   :hidden:

   traceability
