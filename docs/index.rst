sphinx-covsight
===============

Author a verification plan as a Sphinx document, and extract it as a covsight
testplan v1 artifact that is deterministic and byte-stable.

The plan is prose a human reviews *and* a graph a tool walks.  What makes that
work is what the plan does **not** contain: no verification-approach boilerplate,
no exit criteria, no scores, and no quoted specification text.  Policy comes
from ``conf.py``; cited text stays in the specification and is referenced.  A
reviewer reading a diff of the plan sees only decisions.

.. toctree::
   :maxdepth: 2
   :caption: Guides

   guide/writing-a-spec
   guide/extracting-rules
   guide/writing-a-plan
   guide/extracting-a-testplan

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/directives
   reference/configuration

Quickstart
----------

Install the extension and whichever optional citation backends your project
has.  Both are genuinely optional: a plan is usually written before the RTL
exists, and must build without them.

.. code-block:: console

   $ pip install sphinx-covsight
   $ pip install "sphinx-covsight[sv]"     # sv: citations (sphinx-systemverilog)
   $ pip install "sphinx-covsight[rdl]"    # rdl: citations (sphinx-peakrdl)

Enable it, and point it at the specification's published rule catalogue:

.. code-block:: python

   # conf.py
   extensions = ["myst_parser", "sphinx_covsight"]
   myst_enable_extensions = ["colon_fence"]      # for MyST authoring

   covsight_plan_name = "uart"
   covsight_needs_json = "_spec/needs.json"
   covsight_env_policy = {...}

Write a feature:

.. literalinclude:: example/plan/feat_baud.rst
   :language: rst
   :start-after: .. doc:feature-start
   :end-before: .. env:: ip_simulation
   :dedent: 0

Build the documentation as usual — the plan is written as a side effect — or
extract it on its own:

.. code-block:: console

   $ sphinx-build -b html plan/ _build/html
   $ covsight-testplan build plan/ -o testplan.json
   $ covsight-testplan check plan/ --against testplan.json    # the CI gate

Where to go next
----------------

======================================  ===============================================
If you are …                            Read …
======================================  ===============================================
writing the specification the plan       :doc:`guide/writing-a-spec`
cites
wiring the specification's rules into    :doc:`guide/extracting-rules`
the plan repository
writing the plan                         :doc:`guide/writing-a-plan`
consuming the extracted plan             :doc:`guide/extracting-a-testplan`
======================================  ===============================================

The worked example every guide quotes lives in ``docs/example/``: a miniature
UART specification, its register map, its testbench collateral, and the plan
that cites all three.
