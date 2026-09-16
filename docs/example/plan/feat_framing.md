# Character framing

<!-- doc:feature-start -->
:::::{feature} Character framing
:id: FEAT-001
:owner: uart-verification
:tags: uart, framing

A character is one start bit, eight data bits least-significant bit first, an
optional parity bit and one stop bit.  The receiver qualifies the start bit at
the half-bit point, so a glitch shorter than half a bit period must not begin
reception.

```{covers}
rule:UART_1_1_1, rule:UART_1_1_2, rule:UART_1_1_3
```

::::{env} ip_simulation
:scope: block
:difficulty: 3
:coverage: 8

:::{testpoint} Start bit qualification
:id: FEAT-001.tp_start_bit
:stage: V1
:priority: high
:tags: smoke

Drive a falling edge on RX and confirm a character begins; drive a glitch
shorter than half a bit period and confirm none does.  Both polarities of the
line at the sampling instant are checked.

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

:::{testpoint} Parity generation and checking
:id: FEAT-001.tp_parity
:stage: V2
:priority: medium

Sweep both parity polarities against random payloads and confirm the generated
parity bit and the receiver's error reporting agree with the specification.
The parity mode is programmed through the {rdl:doc-ref}`uart.CTRL` register.

```{covers}
rule:UART_1_2_1, rule:UART_1_2_2,
rdl:uart.CTRL.PARITY_EN,
sv:uart_pkg::uart_cfg::uart_cfg_cg
```

```{coverage}
coverpoint: uart_env.uart_cfg_cg.parity_cp
cross: uart_env.uart_cfg_cg.cfg_x
```

```{tests}
uart_parity_test
```
:::
::::

::::{env} formal
:scope: block
:difficulty: 6
:coverage: 4

:::{testpoint} Stop bit framing error is always reported
:id: FEAT-001.tp_framing_error
:stage: V2

Prove that a low stop bit always raises a framing error within one bit period,
for every payload and every parity setting.

```{covers}
rule:UART_1_1_3
```

```{tests}
uart_framing_error_props
```
:::
::::
:::::
<!-- doc:feature-end -->
