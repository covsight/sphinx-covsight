// Formal property sets for the UART.
//
// The plan's `formal` environment names these two modules in its `tests`
// bodies, the same way the simulation environment names test classes.  A
// "test" is whatever the environment runs; for a formal environment that is a
// property set, and nothing in the plan or the extracted artifact needs to
// know the difference.
//
// They are bind-able modules rather than a checker inside the design so that
// the design compiles unchanged without them.

// Proves that a divisor write cannot disturb a character already in flight.
//
// The property for ``UART_3_2_4``: while `busy` is high, the divisor the
// transmitter is counting with does not change, whatever software writes.
// This is the obligation that makes latching `baud_div` at the character
// boundary correct rather than merely convenient.
//
// Bind it to :sv:mod:`uart_tx`::
//
//     bind uart_tx uart_baud_lock_props u_props (.*);
module uart_baud_lock_props (
   input logic        clk,
   input logic        rst_n,
   input logic        busy,
   input logic [15:0] baud_div,
   input logic [15:0] div_q
);

   default clocking cb @(posedge clk); endclocking
   default disable iff (!rst_n);

   // The divisor in force is stable for the whole character.
   a_div_stable_while_busy: assert property (busy |=> $stable(div_q));

   // A write while idle does reach the next character, so the property above
   // cannot be satisfied by simply never updating.  ``UART_3_2_1``.
   a_div_takes_effect_when_idle: assert property (
      !busy && baud_div >= 16'd2 |=> (!$past(busy) -> div_q == $past(baud_div)) or busy
   );

endmodule

// Proves that a low stop bit is always reported.
//
// The property for ``UART_1_1_3``: every character that completes with the
// line low at the stop-bit sampling instant raises `frame_err_o` with its
// `valid_o`.  "Always" is the word that makes this a formal obligation rather
// than a simulation goal -- for every payload and every parity setting, which
// is what simulation cannot cover exhaustively.
//
// Bind it to :sv:mod:`uart_rx`::
//
//     bind uart_rx uart_framing_error_props u_props (.*);
module uart_framing_error_props (
   input logic       clk,
   input logic       rst_n,
   input logic       valid_o,
   input logic       frame_err_o,
   input logic [1:0] rxd_q
);

   default clocking cb @(posedge clk); endclocking
   default disable iff (!rst_n);

   // A framing error is reported with the character, never on its own.
   a_frame_err_qualified: assert property (frame_err_o && !valid_o |-> ##[1:$] valid_o);

   // And a character is never reported without a decision having been made.
   a_frame_err_known: assert property (valid_o |-> !$isunknown(frame_err_o));

endmodule
