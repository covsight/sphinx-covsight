// Configuration and functional coverage for the example UART.
//
// The plan cites the covergroup declared here with ``sv:``, and binds coverage
// with ``.. coverage::``.  The two are deliberately different namespaces: a
// citation names a *declaration*, a binding names a UCIS *instance* path.
//
// This package holds only what the plan refers to.  The components that build
// and run a testbench around it are in `uart_tb_pkg.sv`.

package uart_pkg;

   // Configuration sampled once per character.
   class uart_cfg;

      // Programmed clock divisor.
      bit [15:0] baud_div;
      // Programmed parity mode.
      bit [1:0]  parity;

      // Records which link configurations the regression actually exercised.
      covergroup uart_cfg_cg;
         // Per-instance coverage, because the plan binds to an *instance*
         // path.  It has to be set here: the option cannot be modified from
         // outside the covergroup definition.
         option.per_instance = 1;
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

      // Samples the covergroup with the configuration currently programmed.
      //
      // Called by the environment once per character rather than once per
      // test, so a test that reprograms the link mid-run is credited for both
      // configurations.
      function void sample_cfg();
         uart_cfg_cg.sample();
      endfunction

   endclass

endpackage
