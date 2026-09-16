// UART transmitter.
//
// Implements the framing and baud-rate rules of the specification.  The rule
// ids in the comments below are the ones the verification plan cites, so a
// reader can get from a line of RTL to the sentence that requires it.

// Serialises one 8-bit character per `start_i` pulse.
//
// The bit period is `baud_div` reference clocks.  Two rules shape how that
// divisor is applied, and both are visible in the `div_q` register below:
//
// * ``UART_3_2_1`` -- the divisor is writable while the link is idle and takes
//   effect at the next character boundary.
// * ``UART_3_2_4`` -- a write during a character in flight must not change the
//   bit clock until that character completes.
//
// Latching `baud_div` once, at the transition out of `IDLE`, satisfies both:
// there is exactly one instant at which the programmed value is consulted.
//
// :param CLK_HZ: reference clock frequency.  Documentation only; the divisor,
//     not this parameter, sets the bit rate.
module uart_tx #(parameter int CLK_HZ = 50_000_000) (
   input  logic        clk,
   input  logic        rst_n,

   // Programmed clock divisor.  Sampled only at a character boundary.
   input  logic [15:0] baud_div,
   // When set, a parity bit is emitted after the data bits (``UART_1_2_1``).
   input  logic        parity_en,

   // Pulse high for one clock to begin transmitting `data_i`.
   input  logic        start_i,
   // The character to transmit.
   input  logic [7:0]  data_i,

   // Serial output.  Idle high.
   output logic        txd,
   // High from `start_i` until the stop bit has been driven for a full bit
   // period.  The register block exposes this as ``STATUS.TX_BUSY``.
   output logic        busy
);

   // Bit positions within a frame: one start bit, eight data bits, an optional
   // parity bit, one stop bit (``UART_1_1_2``).
   localparam bit [3:0] BIT_START = 4'd0;
   localparam bit [3:0] BIT_DATA0 = 4'd1;
   localparam bit [3:0] BIT_STOP  = 4'd10;

   // The divisor in force for the character currently in flight.  Clamped to
   // the specified minimum of 2 (``UART_3_2_2``); a divisor of 0 or 1 would
   // otherwise produce a bit period the receiver cannot resolve.
   logic [15:0] div_q;
   // Reference-clock countdown within the current bit.
   logic [15:0] tick_q;
   // Which bit of the frame is being driven.
   logic [3:0]  bit_q;
   // The character latched at the start of the frame.
   logic [7:0]  data_q;
   // Parity over `data_q`, accumulated as the data bits are shifted out.
   logic        parity_q;
   // Parity enable latched with the character, for the same reason `div_q` is.
   logic        parity_en_q;

   // True on the last reference clock of a bit period.
   wire bit_done = (tick_q == 16'd1);
   // The frame ends after the stop bit, whose position depends on whether a
   // parity bit was inserted.
   wire last_bit = (bit_q == (parity_en_q ? BIT_STOP : BIT_STOP - 4'd1));

   always_ff @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
         txd         <= 1'b1;
         busy        <= 1'b0;
         div_q       <= 16'd2;
         tick_q      <= 16'd0;
         bit_q       <= 4'd0;
         data_q      <= 8'd0;
         parity_q    <= 1'b0;
         parity_en_q <= 1'b0;
      end
      else if (!busy) begin
         txd <= 1'b1;
         if (start_i) begin
            // The one instant at which the programmed configuration is read.
            div_q       <= (baud_div < 16'd2) ? 16'd2 : baud_div;
            parity_en_q <= parity_en;
            tick_q      <= (baud_div < 16'd2) ? 16'd2 : baud_div;
            data_q      <= data_i;
            parity_q    <= 1'b0;
            bit_q       <= BIT_START;
            txd         <= 1'b0;   // start bit
            busy        <= 1'b1;
         end
      end
      else if (!bit_done) begin
         tick_q <= tick_q - 16'd1;
      end
      else if (last_bit) begin
         busy <= 1'b0;
         txd  <= 1'b1;
      end
      else begin
         tick_q <= div_q;
         bit_q  <= bit_q + 4'd1;
         case (1'b1)
            // Data bits, least-significant first (``UART_1_1_2``).
            (bit_q >= BIT_START && bit_q < BIT_DATA0 + 4'd7): begin
               txd      <= data_q[bit_q];
               parity_q <= parity_q ^ data_q[bit_q];
            end
            // Parity over the eight data bits (``UART_1_2_1``), or the stop
            // bit when parity is disabled.
            (bit_q == BIT_DATA0 + 4'd7): txd <= parity_en_q ? parity_q : 1'b1;
            // Stop bit.
            default: txd <= 1'b1;
         endcase
      end
   end

endmodule
