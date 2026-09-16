Configuration reference
=======================

The table below is generated from the ``CONFIG_VALUES`` table in
``sphinx_covsight/__init__.py``, so it cannot drift from the code.

.. covsight-config-table::

Notes on the less obvious ones
------------------------------

``covsight_output``
    Resolved relative to the **build output directory**, so a normal
    ``sphinx-build -b html`` writes the plan alongside the rendered HTML.  An
    absolute path is honoured as given.  ``covsight-testplan build`` overrides
    it, which is how the CLI produces the artifact without producing HTML.

``covsight_score``
    A restricted arithmetic expression over ``difficulty`` and ``coverage``:
    numeric literals, those two names, ``+ - * / // % **``, unary sign, and
    parentheses.  Calls, attribute access, subscripts, comprehensions and the
    walrus operator are rejected when the expression is compiled — a doc build
    runs in CI on arbitrary branches, so an ``eval`` that can reach
    ``__import__`` is a real vulnerability rather than a theoretical one.

    It is a string rather than a lambda so it can be hashed into the provenance
    sidecar.  Scores are derived data, and provenance is what makes them
    auditable.

``covsight_env_policy`` / ``covsight_env_policy_file``
    Mutually exclusive, and equivalent: identical content produces an identical
    ``policy_sha256``.  ``{feature}`` and ``{env}`` interpolate in ``approach``
    and ``reasoning``; any other placeholder is a configuration error, raised
    once at ``builder-inited`` rather than per feature.

``covsight_env_in_custom``
    ``True`` writes a testpoint's environment to ``custom.covsight.env``, which
    is where it goes until covsight-core's testpoint schema carries an ``env``
    field.  ``False`` emits a top-level ``env`` instead.  Flipping it changes the
    emitted artifact, so flip it deliberately and regenerate the golden.

``covsight_strict_citations``
    Promotes an unresolved citation from a warning to a build error.  What CI
    should set.  It does **not** affect the absent-backend case: a plan built
    without sphinx-peakrdl still builds, because writing a plan before the RTL
    exists is the normal case, not an edge case.

``covsight_validate_coverage_bindings``
    Checks the leaf name of each ``covergroup``/``coverpoint`` binding against
    the ``sv`` domain.  A no-op when sphinx-systemverilog is absent.  Only the
    leaf is checked, because ``.. coverage::`` paths are UCIS *instance* paths
    while the ``sv`` domain keys on SystemVerilog *declaration* paths — a
    full-path check would be wrong rather than merely strict.

Interaction with other extensions
---------------------------------

=========================  ====================================================
Extension                  Effect when enabled
=========================  ====================================================
``myst_parser``            Plans may be authored in Markdown.  Add
                           ``myst_enable_extensions = ["colon_fence"]``.
``sphinx_needs``           Not needed by the plan project; it is the
                           specification project that produces ``needs.json``.
``sphinx_systemverilog``   Enables the ``sv:`` citation backend and
                           coverage-binding leaf validation.
``sphinx_peakrdl``         Enables the ``rdl:`` citation backend.  A target can
                           only be *validated* when the SystemRDL is compiled in
                           the same build.
=========================  ====================================================
