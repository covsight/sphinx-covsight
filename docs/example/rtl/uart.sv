// UART top level: the register block and the two datapath halves.
//
// This is the module the testbench elaborates and the plan's `rdl:` citations
// describe.  The register layout here and `uart_regs.rdl` are the same map
// expressed twice -- which is exactly the duplication a citation makes
// checkable rather than merely hoped for.

// Register-mapped UART.
//
// Instantiates :sv:mod:`uart_tx` and :sv:mod:`uart_rx` and exposes them
// through the two registers of `uart_regs.rdl`:
//
// ===========  ======  ==================================================
// Register     Offset  Fields
// ===========  ======  ==================================================
// ``CTRL``     0x0     ``BAUD_DIV[15:0]``, ``PARITY_EN[16]``
// ``STATUS``   0x4     ``TX_BUSY[0]``, ``RX_FULL[1]``
// ===========  ======  ==================================================
//
// :param CLK_HZ: reference clock frequency, passed to both halves.
// :param RX_DEPTH: receive FIFO depth.  ``STATUS.RX_FULL`` reports this FIFO.
module uart #(
   parameter int CLK_HZ   = 50_000_000,
   parameter int unsigned RX_DEPTH = 4
) (
   input  logic        clk,
   input  logic        rst_n,

   // Register access: pulse high for one clock to perform one.
   input  logic        cs,
   // High for a write, low for a read.
   input  logic        we,
   // Word address.  Only bit 2 is decoded: 0x0 is CTRL, 0x4 is STATUS.
   input  logic [7:0]  addr,
   // Write data.  ``CTRL`` occupies bits 16:0; the rest are ignored.
   input  logic [31:0] wdata,
   // Read data, valid the clock after `cs`.
   output logic [31:0] rdata,

   // Pulse high to queue `tx_data` for transmission.
   input  logic        tx_start,
   // The character to transmit.
   input  logic [7:0]  tx_data,
   // Pulse high when a character has been received.
   output logic        rx_valid,
   // The received character, valid with `rx_valid`.
   output logic [7:0]  rx_data,
   // Set with `rx_valid` when the stop bit was low (``UART_1_1_3``).
   output logic        rx_frame_err,
   // Set with `rx_valid` when the parity bit disagreed (``UART_1_2_2``).
   output logic        rx_parity_err,

   // Serial output to the far end.  Idle high.
   output logic        txd,
   // Serial input from the far end.  Idle high.
   input  logic        rxd
);

   // ``CTRL``.  Written by software, read by both halves.  Neither half
   // consults these bits mid-character; see :sv:mod:`uart_tx`.
   logic [15:0] ctrl_baud_div;
   logic        ctrl_parity_en;

   // ``STATUS``.  Driven by hardware, read-only to software.
   logic        tx_busy;
   localparam int unsigned CNT_W = $clog2(RX_DEPTH + 1);
   logic [CNT_W-1:0] rx_count;
   wire              rx_full = (rx_count == CNT_W'(RX_DEPTH));

   always_ff @(posedge clk or negedge rst_n) begin
      if (!rst_n) begin
         // Reset values from `uart_regs.rdl`: 115200 baud from a 50 MHz
         // reference, parity disabled.
         ctrl_baud_div  <= 16'd434;
         ctrl_parity_en <= 1'b0;
         rdata          <= 32'd0;
      end
      else if (cs) begin
         if (we) begin
            if (addr[2] == 1'b0) begin
               ctrl_baud_div  <= wdata[15:0];
               ctrl_parity_en <= wdata[16];
            end
            // STATUS is read-only; a write to it is silently dropped.
         end
         else begin
            rdata <= (addr[2] == 1'b0)
                   ? {15'd0, ctrl_parity_en, ctrl_baud_div}
                   : {30'd0, rx_full, tx_busy};
         end
      end
   end

   // Receive FIFO occupancy.  The FIFO itself is not modelled -- the plan does
   // not verify it, and a queue nobody cites would be dead weight in an
   // example.  The count is enough to make ``STATUS.RX_FULL`` real.
   always_ff @(posedge clk or negedge rst_n) begin
      if (!rst_n)
         rx_count <= '0;
      else if (rx_valid && !rx_full)
         rx_count <= rx_count + 1'b1;
      else if (cs && !we && addr[2] == 1'b0 && rx_count != 0)
         rx_count <= rx_count - 1'b1;
   end

   uart_tx #(.CLK_HZ(CLK_HZ)) u_tx (
      .clk       (clk),
      .rst_n     (rst_n),
      .baud_div  (ctrl_baud_div),
      .parity_en (ctrl_parity_en),
      .start_i   (tx_start),
      .data_i    (tx_data),
      .txd       (txd),
      .busy      (tx_busy)
   );

   uart_rx #(.CLK_HZ(CLK_HZ)) u_rx (
      .clk          (clk),
      .rst_n        (rst_n),
      .baud_div     (ctrl_baud_div),
      .parity_en    (ctrl_parity_en),
      .rxd          (rxd),
      .valid_o      (rx_valid),
      .data_o       (rx_data),
      .frame_err_o  (rx_frame_err),
      .parity_err_o (rx_parity_err)
   );

endmodule
