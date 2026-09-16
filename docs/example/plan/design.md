# The design

The UART itself, documented from the RTL in this same build.

A verification plan does not normally carry the design's documentation, and in
a real project these pages would live in the design's own doc set.  They are
here because the example has to show what a citation *points at*: `rdl:` lands
on a register field, `sv:` lands on a declaration, and both of those are only
meaningful if the thing on the other end is real.

The rule ids in the comments below are the ones the plan cites.  Reading in
this direction — from an implementation detail to the sentence that requires it
— is the direction a designer reads.

```{eval-rst}
The `traceability walkthrough <../traceability.html>`_ in the sphinx-covsight
documentation reads the same chain the other way.  It is written as a plain
external link rather than a cross-reference because it belongs to a different
Sphinx project, which is the arrangement this whole example exists to
demonstrate.
```

## Top level

```{eval-rst}
.. autosvmodule:: uart
   :members:
   :show-instances:
```

## Datapath

The transmitter and the receiver are separate modules with no shared state, so
a divisor write reaches each of them independently.  That is also why both
latch the divisor for themselves rather than sharing a latched copy.

```{eval-rst}
.. autosvmodule:: uart_tx
   :members:

.. autosvmodule:: uart_rx
   :members:
```

## The serial interface

```{eval-rst}
.. autosvmodule:: uart_if
   :members:
```

## Properties

The plan's `formal` environment names these two modules in its `tests` bodies,
the way its simulation environment names test classes.  A "test" is whatever
the environment runs.

```{eval-rst}
.. autosvmodule:: uart_baud_lock_props

.. autosvmodule:: uart_framing_error_props
```
