// Coverage and test collateral for the example UART.
//
// The plan cites the covergroup declared here with ``sv:``, and binds coverage
// with ``.. coverage::``.  The two are deliberately different namespaces: a
// citation names a *declaration*, a binding names a UCIS *instance* path.

package uart_pkg;

   // Configuration sampled once per character.
   class uart_cfg;

      // Programmed clock divisor.
      bit [15:0] baud_div;
      // Programmed parity mode.
      bit [1:0]  parity;

      // Records which link configurations the regression actually exercised.
      covergroup uart_cfg_cg;
         // Divisor values, with the range boundaries called out.
         baud_div_cp : coverpoint baud_div {
            bins minimum   = {16'd2};
            bins typical[] = {[16'd3 : 16'd65534]};
            bins maximum   = {16'd65535};
         }
         // Parity modes.
         parity_cp : coverpoint parity;
         // Every parity mode at every divisor class.
         cfg_x : cross baud_div_cp, parity_cp;
      endgroup

      function new();
         uart_cfg_cg = new();
      endfunction

   endclass

   // Base test: brings up the environment and applies the reset sequence.
   class uart_base_test;

      // Runs the reset sequence and hands over to the main sequence.
      virtual task run_test();
      endtask

   endclass

   // Directed test that sweeps the divisor across its supported range.
   class uart_baud_test extends uart_base_test;
   endclass

endpackage
