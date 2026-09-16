# Testbench collateral

The covergroup the plan binds to, and the tests it names, are documented from
the SystemVerilog source in this same build.

That is the whole reason this page exists.  A plan that names
`uart_baud_460800_test` reads exactly like a plan that names a test nobody ever
wrote — the prose is identical and the review is identical.  Building the plan
and the testbench source together is what makes the difference visible, and the
example's test suite fails if any name in a `tests` body stops resolving to a
class here.

## Configuration and coverage

`uart_cfg` is what a `sv:` citation in the plan points at.  Its covergroup is
also what the `coverage` bindings name — by instance path, not by this
declaration path.

```{eval-rst}
.. autosvclass:: uart_pkg::uart_cfg
   :members:
```

## Components

```{eval-rst}
.. autosvclass:: uart_tb_pkg::uart_xaction
   :members:

.. autosvclass:: uart_tb_pkg::uart_driver
   :members:

.. autosvclass:: uart_tb_pkg::uart_monitor
   :members:

.. autosvclass:: uart_tb_pkg::uart_env
   :members:
   :show-inheritance:
```

## Sequences

```{eval-rst}
.. autosvclass:: uart_tb_pkg::uart_seq
   :members:

.. autosvclass:: uart_tb_pkg::uart_walking_ones_seq
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_bad_stop_seq
   :show-inheritance:
```

## Tests

Every name below appears in a `tests` body somewhere in the plan.  The three
baud tests are written in the plan as one line — `uart_baud_{baud}_test` — and
expanded by `covsight_substitutions`; they are correspondingly thin here.

```{eval-rst}
.. autosvclass:: uart_tb_pkg::uart_base_test
   :members:

.. autosvclass:: uart_tb_pkg::uart_smoke_test
   :members:
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_framing_test
   :members:
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_parity_test
   :members:
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_baud_test
   :members:
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_baud_9600_test
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_baud_115200_test
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_baud_460800_test
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_baud_random_test
   :members:
   :show-inheritance:

.. autosvclass:: uart_tb_pkg::uart_baud_clamp_test
   :members:
   :show-inheritance:
```

## Top level

```{eval-rst}
.. autosvmodule:: uart_tb
```
