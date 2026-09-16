Directive reference
===================

The tables below are generated from the directive implementations, so they
cannot drift from them.

The six directives
------------------

.. covsight-directive-table::

Options in detail
-----------------

``feature``
~~~~~~~~~~~

``:id:`` (required)
    Stable identifier.  Authored, not derived: it is what survives retitling.

``:owner:``
    Person or team accountable.  Extracted to ``goals[].owner``.

``:tags:``
    Comma-separated labels.  Sorted at extraction — they are a set.

``:status:``
    ``planned``, ``in_progress``, ``complete`` or ``waived``.  Defaults to
    ``planned`` for a feature with no testpoints beneath it.

``env``
~~~~~~~

``:title:``
    Overrides the title taken from ``covsight_env_policy``.

``:scope:``
    Free string, e.g. ``block``, ``subsystem``, ``chip``.

``:difficulty:``
    Non-negative integer, fed to ``covsight_score``.

``:coverage:``
    Non-negative integer, fed to ``covsight_score``.

``testpoint``
~~~~~~~~~~~~~

``:id:``
    Optional.  Derived as ``<feature-id>.<env>.<slug(title)>`` when omitted.

``:stage:``
    Verification stage: ``V1``, ``V2``, ``V2S``, ``V3``, or any string your
    organisation uses.

``:priority:``
    ``high``, ``medium`` or ``low``.

``:weight:``
    Positive integer; relative importance for rollup.  Omitted from the output
    when it is 1.

``:owner:``
    Person or team accountable for this testpoint.

``:tags:``
    Comma-separated labels.

``:na:``
    Flag.  Marks a testpoint deliberately unmapped to tests, suppressing the
    ``covsight.testpoint-unmapped`` warning.

``covers``, ``coverage``, ``tests``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

No options — by design.  A repeated option key is a hard error in RST and is
silently dropped in MyST, so every list-valued input takes a body instead, one
item per line:

.. code-block:: rst

   .. covers::
      rule:UART_3_2_1,
      rdl:uart.CTRL.BAUD_DIV

   .. coverage::
      covergroup: uart_env.uart_cfg_cg
      coverpoint: uart_env.uart_cfg_cg.baud_div_cp

   .. tests:: uart_baud_{baud}_test, uart_baud_random_test

``covers`` and ``tests`` also accept a single-line argument form, for the common
one-item case.

Coverage binding types
----------------------

``covergroup``, ``coverpoint``, ``cross``, ``assertion``, ``expression``,
``toggle``, ``line``, ``branch``, ``functional`` — the enumeration from covsight
testplan v1.  Leaf-name validation against the ``sv`` domain applies to
``covergroup`` and ``coverpoint`` only; the domain has no object kind for the
others, so checking them would report every one of them as missing.

Roles
-----

``:rule:``
    Inline citation to a specification rule, e.g. ``:rule:`UART_3_2_1```.
    Renders as a link when the rule resolves.  Inline citations are **not**
    extracted into ``requirements[]`` — a citation mid-sentence is evidence, not
    an accountability claim; use ``.. covers::`` for that.

``:covsight:feature:`` and ``:covsight:tp:``
    Cross-references to a feature or testpoint elsewhere in the plan, by id.

Warnings
--------

Every message carries a stable subtype, so a class of message can be silenced
with ``suppress_warnings``:

.. code-block:: python

   suppress_warnings = ["covsight.coverage-binding"]

.. covsight-warning-table::
