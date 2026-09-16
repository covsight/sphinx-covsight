// Testbench top level.
//
// Clock, reset, the interface, the design, and the one line that selects which
// of the plan's tests runs.

// Elaborates the design against `uart_if` and runs the test named on the
// command line.
//
// The `+UART_TEST=` plusarg is how a regression selects a test, and the names
// it accepts are exactly the names the verification plan's `tests` bodies
// contain -- see :sv:class:`uart_tb_pkg::uart_base_test`.
module uart_tb;

   import uart_pkg::*;
   import uart_tb_pkg::*;

   localparam int CLK_HZ     = 50_000_000;
   localparam time CLK_PERIOD = 20ns;

   logic clk   = 1'b0;
   logic rst_n = 1'b0;

   always #(CLK_PERIOD / 2) clk = ~clk;

   uart_if #(.CLK_HZ(CLK_HZ)) vif (.clk(clk), .rst_n(rst_n));

   // The register and character interfaces are tied off here.  The plan does
   // not verify the register block -- there is no feature for it -- and an
   // example that wired up collateral no testpoint refers to would be teaching
   // the wrong habit.
   logic [31:0] rdata;
   logic        rx_valid, rx_frame_err, rx_parity_err;
   logic [7:0]  rx_data;

   uart #(.CLK_HZ(CLK_HZ)) dut (
      .clk           (clk),
      .rst_n         (rst_n),
      .cs            (1'b0),
      .we            (1'b0),
      .addr          (8'd0),
      .wdata         (32'd0),
      .rdata         (rdata),
      .tx_start      (1'b0),
      .tx_data       (8'd0),
      .rx_valid      (rx_valid),
      .rx_data       (rx_data),
      .rx_frame_err  (rx_frame_err),
      .rx_parity_err (rx_parity_err),
      .txd           (vif.txd),
      .rxd           (vif.rxd)
   );

   // The property sets the plan's `formal` environment names.  Bound rather
   // than instantiated inside the design so the design compiles without them.
   bind uart_tx uart_baud_lock_props u_baud_lock (.*);
   bind uart_rx uart_framing_error_props u_framing_error (.*);

   uart_base_test test;

   initial begin
      string name;
      if (!$value$plusargs("UART_TEST=%s", name))
         name = "uart_smoke_test";

      // A factory would be the usual way to do this.  A case statement is the
      // honest way to do it in thirty lines, and it puts every name the plan
      // can contain in one place where a reader can check them off.
      case (name)
         "uart_smoke_test":       begin automatic uart_smoke_test       t = new(vif); test = t; end
         "uart_framing_test":     begin automatic uart_framing_test     t = new(vif); test = t; end
         "uart_parity_test":      begin automatic uart_parity_test      t = new(vif); test = t; end
         "uart_baud_9600_test":   begin automatic uart_baud_9600_test   t = new(vif); test = t; end
         "uart_baud_115200_test": begin automatic uart_baud_115200_test t = new(vif); test = t; end
         "uart_baud_460800_test": begin automatic uart_baud_460800_test t = new(vif); test = t; end
         "uart_baud_random_test": begin automatic uart_baud_random_test t = new(vif); test = t; end
         "uart_baud_clamp_test":  begin automatic uart_baud_clamp_test  t = new(vif); test = t; end
         default: $fatal(1, "unknown test '%s'", name);
      endcase

      repeat (4) @(posedge clk);
      rst_n <= 1'b1;
      test.run_test();
      $finish;
   end

endmodule
