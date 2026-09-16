// The UART's serial pin interface.
//
// The testbench drives and samples the link through this interface rather than
// through the module ports directly, so a `virtual uart_if` handle is the only
// thing a driver or monitor needs to know about the design.

// Serial link between the UART and its far end.
//
// `txd` is driven by the design and sampled by the testbench monitor; `rxd` is
// driven by the testbench driver and sampled by the design.  Both are idle
// high, which is what makes the falling edge of the start bit detectable.
//
// :param CLK_HZ: reference clock frequency, used only by the bit-period
//     assertions in :sv:mod:`uart_baud_lock_props`
interface uart_if #(parameter int CLK_HZ = 50_000_000) (input logic clk, input logic rst_n);

   // Serial output from the design.  Idle high.
   logic txd;
   // Serial input to the design.  Idle high.
   logic rxd;

   // Synchronous view for the stimulus driver.
   clocking drv_cb @(posedge clk);
      default input #1step output #1ns;
      output rxd;
      input  txd;
   endclocking

   // Synchronous view for the monitor.  Inputs only: a monitor that can drive
   // is a monitor that can hide a bug.
   clocking mon_cb @(posedge clk);
      default input #1step;
      input rxd;
      input txd;
   endclocking

   modport dut (output txd, input rxd);
   modport drv (clocking drv_cb, input rst_n);
   modport mon (clocking mon_cb, input rst_n);

endinterface
