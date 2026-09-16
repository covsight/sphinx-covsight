# UART

The UART transmits and receives 8-bit characters with optional parity over a
two-wire asynchronous link.  Prose like this paragraph is explanation: it does
not earn an id, because nothing can be verified against it.

## Framing

:::{rule} Start bit qualification
:id: UART_1_1_1
:status: approved
:tags: framing

The receiver **shall** re-sample the start bit at the half-bit point and abandon
reception if the line has returned high.
:::

:::{rule} Character length
:id: UART_1_1_2
:status: approved
:tags: framing

A character **shall** consist of one start bit, eight data bits transmitted
least-significant bit first, an optional parity bit, and one stop bit.
:::

:::{rule} Stop bit sampling
:id: UART_1_1_3
:status: approved
:tags: framing

The receiver **shall** sample the stop bit at its centre and **shall** report a
framing error when it is low.
:::

:::{rule} Parity generation
:id: UART_1_2_1
:status: approved
:tags: framing, parity

When parity is enabled the transmitter **shall** emit a parity bit computed over
the eight data bits, using the polarity selected by `CTRL.PARITY_EN`.
:::

:::{rule} Parity checking
:id: UART_1_2_2
:status: approved
:tags: framing, parity

When parity is enabled the receiver **shall** report a parity error for any
character whose parity bit disagrees with the received data.
:::

## Baud rate

:::{rule} Divisor programmability
:id: UART_3_2_1
:status: approved
:tags: baud

The divisor **shall** be writable while the link is idle, and the programmed
value **shall** take effect at the next character boundary.

```systemverilog
ctrl.baud_div <= 16'd434;   // 115200 baud from a 50 MHz reference
```
:::

:::{rule} Supported divisor range
:id: UART_3_2_2
:status: approved
:tags: baud

The divisor **shall** support every value from 2 to 65535 inclusive.  A divisor
below 2 **shall** be treated as 2.
:::

:::{rule} Divisor write during transfer
:id: UART_3_2_4
:status: approved
:tags: baud

A write to the divisor while a character is in flight **shall not** change the
bit clock until that character completes.
:::
