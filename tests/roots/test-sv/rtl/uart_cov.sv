// UART coverage and test collateral.
package uart_pkg;

   // Configuration coverage for the UART.
   class uart_cfg;

      bit [15:0] baud_div;
      bit [1:0]  parity;

      // Samples the programmed configuration once per character.
      covergroup uart_cfg_cg;
         // Divisor values actually exercised.
         baud_div_cp : coverpoint baud_div;
         // Parity modes actually exercised.
         parity_cp : coverpoint parity;
      endgroup

   endclass

   // Base test for the UART environment.
   class uart_base_test;
   endclass

   // Two classes declaring the same covergroup leaf name, so that a leaf-only
   // citation to it is genuinely ambiguous.
   class uart_rx_mon;
      bit [7:0] data;
      covergroup shared_cg;
         data_cp : coverpoint data;
      endgroup
   endclass

   class uart_tx_mon;
      bit [7:0] data;
      covergroup shared_cg;
         data_cp : coverpoint data;
      endgroup
   endclass

endpackage
