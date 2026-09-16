// UART receiver.
//
// The interesting half of the design, because three of the framing rules are
// about *when* the line is sampled rather than what is on it.

// Recovers one 8-bit character per start bit.
//
// Sampling instants, and the rules that fix them:
//
// * ``UART_1_1_1`` -- the start bit is re-sampled at its half-bit point, and
//   reception is abandoned if the line has returned high.  This is what makes
//   a glitch shorter than half a bit period harmless, and it is the reason the
//   `QUALIFY` state exists rather than counting a full bit period from the
//   falling edge.
// * ``UART_1_1_2`` -- eight data bits, least-significant first.
// * ``UART_1_1_3`` -- the stop bit is sampled at its centre, and a low sample
//   is reported as a framing error.
//
// Every subsequent bit is sampled a half period after the qualification point
// plus a whole number of bit periods, which centres it.
//
// :param CLK_HZ: reference clock frequency.  Documentation only.
module uart_rx #(parameter int CLK_HZ = 50_000_000) (
   input  logic        clk,
   input  logic        rst_n,

   // Programmed clock divisor.  Sampled only between characters, for the same
   // reason the transmitter does (``UART_3_2_1``, ``UART_3_2_4``).
   input  logic [15:0] baud_div,
   // When set, a parity bit is expected and checked (``UART_1_2_2``).
   input  logic        parity_en,

   // Serial input.  Idle high.
   input  logic        rxd,

   // Pulse high for one clock when `data_o` is valid.
   output logic        valid_o,
   // The recovered character.
   output logic [7:0]  data_o,
   // Set with `valid_o` when the stop bit was low (``UART_1_1_3``).
   output logic        frame_err_o,
   // Set with `valid_o` when the parity bit disagreed (``UART_1_2_2``).
   output logic        parity_err_o
);

   typedef enum logic [1:0] {
      IDLE,      // waiting for a falling edge
      QUALIFY,   // counting to the middle of the start bit
      DATA,      // shifting in data, then parity, then the stop bit
      REPORT     // presenting the result for one clock
   } state_e;

   state_e      state_q;
   // The divisor in force for the character in flight.  Clamped to the
   // specified minimum of 2 (``UART_3_2_2``).
   logic [15:0] div_q;
   logic [15:0] tick_q;
   logic [3:0]  bit_q;
   logic [7:0]  data_q;
   logic        parity_q;
   logic        parity_en_q;
   // Two-flop synchroniser on the asynchronous serial input.
   logic [1:0]  rxd_q;

   wire rxd_sync = rxd_q[1];
   wire falling  = (rxd_q == 2'b10);
   wire bit_done = (tick_q == 16'd1);
   wire clamped  = (baud_div < 16'd2);

   // `bit_q` counts sampling instants after the start bit, not bit positions:
   // 0..7 are the data bits, 8 is the parity bit when one is expected, and the
   // first instant after those is the stop bit.  Counting samples rather than
   // frame positions is what keeps the parity-enabled and parity-disabled
   // frames on one code path.
   localparam bit [3:0] DATA_BITS  = 4'd8;
   localparam bit [3:0] PARITY_POS = 4'd8;

   always_ff @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
         state_q      <= IDLE;
         rxd_q        <= 2'b11;
         div_q        <= 16'd2;
         tick_q       <= 16'd0;
         bit_q        <= 4'd0;
         data_q       <= 8'd0;
         parity_q     <= 1'b0;
         parity_en_q  <= 1'b0;
         valid_o      <= 1'b0;
         data_o       <= 8'd0;
         frame_err_o  <= 1'b0;
         parity_err_o <= 1'b0;
      end
      else begin
         rxd_q   <= {rxd_q[0], rxd};
         valid_o <= 1'b0;

         unique case (state_q)
            IDLE: begin
               if (falling) begin
                  // Latch the configuration for the whole character here.
                  div_q       <= clamped ? 16'd2 : baud_div;
                  parity_en_q <= parity_en;
                  // Half a bit period to the middle of the start bit.
                  tick_q      <= (clamped ? 16'd2 : baud_div) >> 1;
                  parity_q    <= 1'b0;
                  bit_q       <= 4'd0;
                  // Cleared here so a character with parity disabled cannot
                  // report the previous character's parity error.
                  parity_err_o <= 1'b0;
                  frame_err_o  <= 1'b0;
                  state_q      <= QUALIFY;
               end
            end

            // ``UART_1_1_1``.  A glitch shorter than half a bit period has
            // already returned high by now, and is discarded without ever
            // having begun a character.
            QUALIFY: begin
               if (bit_done) begin
                  if (rxd_sync) begin
                     state_q <= IDLE;
                  end
                  else begin
                     tick_q  <= div_q;
                     state_q <= DATA;
                  end
               end
               else begin
                  tick_q <= tick_q - 16'd1;
               end
            end

            // Every sample from here is one full bit period after the previous
            // one, so each lands at the centre of its bit.
            DATA: begin
               if (!bit_done) begin
                  tick_q <= tick_q - 16'd1;
               end
               else begin
                  tick_q <= div_q;
                  if (bit_q < DATA_BITS) begin
                     // ``UART_1_1_2`` -- least-significant bit first.
                     data_q   <= {rxd_sync, data_q[7:1]};
                     parity_q <= parity_q ^ rxd_sync;
                     bit_q    <= bit_q + 4'd1;
                  end
                  else if (parity_en_q && bit_q == PARITY_POS) begin
                     // ``UART_1_2_2`` -- the parity bit must agree with the
                     // parity accumulated over the eight data bits.
                     parity_err_o <= (rxd_sync != parity_q);
                     bit_q        <= bit_q + 4'd1;
                  end
                  else begin
                     // ``UART_1_1_3`` -- the stop bit, sampled at its centre.
                     frame_err_o <= !rxd_sync;
                     state_q     <= REPORT;
                  end
               end
            end

            REPORT: begin
               data_o  <= data_q;
               valid_o <= 1'b1;
               state_q <= IDLE;
            end
         endcase
      end
   end

endmodule
