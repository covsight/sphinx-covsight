# UART verification plan

:::::{feature} Character framing
:id: FEAT-001
:owner: alice
:tags: uart, framing

The receiver samples each bit at the centre of its bit period and
rejects a start bit that does not survive the half-bit qualification.

```{covers}
rule:UART_1_1_1,
rule:UART_1_1_2
```

::::{env} ip_simulation
:scope: block
:difficulty: 3
:coverage: 8

:::{testpoint} Start bit detection
:id: FEAT-001.tp_start_bit
:stage: V1
:priority: high
:tags: smoke

Confirm that a falling edge on RX starts a character, and that a
glitch shorter than half a bit period does not.

```{covers}
rule:UART_1_1_1
```

```{coverage}
covergroup: uart_env.uart_cfg_cg
coverpoint: uart_env.uart_cfg_cg.parity_cp
```

```{tests}
uart_framing_test, uart_smoke_test
```
:::
::::
:::::

:::::{feature} Baud rate generation
:id: FEAT-002

The transmitter and receiver derive their bit clock from a programmable
divisor.  The divisor is writable while the link is idle and takes effect
at the next character boundary.

```{covers}
rule:UART_3_2_1, rule:UART_3_2_4,
rdl:uart.CTRL.BAUD_DIV
```

::::{env} ip_simulation
:scope: block
:difficulty: 3
:coverage: 8

:::{testpoint} All supported divisor values
:stage: V2
:priority: high

Sweep the divisor across every supported baud rate and confirm bit
timing at each, including the boundary values.

```{covers}
rule:UART_3_2_1
```

```{coverage}
covergroup: uart_env.uart_cfg_cg
coverpoint: uart_env.uart_cfg_cg.baud_div_cp
```

```{tests}
uart_baud_{baud}_test, uart_baud_random_test
```
:::
::::

::::{env} formal
:scope: block
:difficulty: 6
:coverage: 4

:::{testpoint} Divisor write during active transfer is ignored
:id: FEAT-002.tp_divisor_locked
:stage: V2
:na:

A write to the divisor while a character is in flight must not
change the bit clock until the character completes.

```{covers}
rule:UART_3_2_4
```
:::
::::
:::::
