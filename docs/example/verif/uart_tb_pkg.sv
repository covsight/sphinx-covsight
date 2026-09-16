// The UART testbench.
//
// Every name that appears in a `tests` body in the verification plan is a
// class in this package.  That correspondence is the point: a plan that names
// tests which do not exist reads exactly like a plan that names tests which
// do, and only a build can tell them apart.  The example's test suite checks
// it, so the plan and this file cannot drift.
//
// The components are deliberately plain classes rather than UVM ones.  The
// example must build wherever the documentation builds, and a UVM dependency
// would make the whole worked example conditional on a library that is not
// installable from PyPI.

package uart_tb_pkg;

   import uart_pkg::*;

   // ── stimulus ──────────────────────────────────────────────────────────

   // One character on the link, in both directions.
   class uart_xaction;

      // The payload, least-significant bit first on the wire.
      rand bit [7:0] data;
      // Corrupt the stop bit.  Used by the framing-error tests; ``UART_1_1_3``.
      rand bit       bad_stop;
      // Invert the transmitted parity bit.  Used by the parity tests;
      // ``UART_1_2_2``.
      rand bit       bad_parity;

      // Errors are injected on request, not at random, so a regression's pass
      // rate does not depend on the seed.
      constraint c_clean { bad_stop == 1'b0; bad_parity == 1'b0; }

      function string convert2string();
         return $sformatf("data=0x%02h bad_stop=%0b bad_parity=%0b",
                          data, bad_stop, bad_parity);
      endfunction

   endclass

   // A stream of characters to apply.
   //
   // `body` is the only thing a derived sequence has to write.  Randomisation
   // and the mailbox handshake are handled here.
   class uart_seq;

      // Where generated characters are posted for the driver.
      mailbox #(uart_xaction) items;
      // How many characters this sequence generates.
      int unsigned count = 8;

      function new(mailbox #(uart_xaction) items);
         this.items = items;
      endfunction

      // Generates `count` clean characters.  Override to shape the stream.
      virtual task body();
         repeat (count) begin
            uart_xaction item = new();
            void'(item.randomize());
            items.put(item);
         end
      endtask

   endclass

   // Sweeps the payload across the values that exercise every shift position.
   class uart_walking_ones_seq extends uart_seq;

      function new(mailbox #(uart_xaction) items);
         super.new(items);
      endfunction

      virtual task body();
         for (int i = 0; i < 8; i++) begin
            uart_xaction item = new();
            void'(item.randomize() with { data == (8'b1 << i); });
            items.put(item);
         end
      endtask

   endclass

   // Corrupts the stop bit of every character, to prove the error is reported
   // rather than merely reportable.
   class uart_bad_stop_seq extends uart_seq;

      function new(mailbox #(uart_xaction) items);
         super.new(items);
      endfunction

      virtual task body();
         repeat (count) begin
            uart_xaction item = new();
            void'(item.randomize() with { bad_stop == 1'b1; });
            items.put(item);
         end
      endtask

   endclass

   // ── components ────────────────────────────────────────────────────────

   // Drives characters onto `rxd` at the configured bit rate.
   //
   // The driver, not the design, decides where the bit boundaries are: it
   // counts the same divisor the design was programmed with.  A driver that
   // took its timing from the design could not detect a design that gets the
   // timing wrong.
   class uart_driver;

      virtual uart_if vif;
      uart_cfg        cfg;
      mailbox #(uart_xaction) items;

      function new(virtual uart_if vif, uart_cfg cfg, mailbox #(uart_xaction) items);
         this.vif   = vif;
         this.cfg   = cfg;
         this.items = items;
      endfunction

      // Holds the line at `value` for one bit period.
      protected task drive_bit(bit value);
         vif.drv_cb.rxd <= value;
         repeat (cfg.baud_div) @(vif.drv_cb);
      endtask

      // Serialises one character: start, eight data bits least-significant
      // first, optional parity, stop (``UART_1_1_2``).
      protected task drive_item(uart_xaction item);
         bit parity = ^item.data;
         drive_bit(1'b0);
         for (int i = 0; i < 8; i++)
            drive_bit(item.data[i]);
         if (cfg.parity != 2'b00)
            drive_bit(item.bad_parity ? ~parity : parity);
         drive_bit(item.bad_stop ? 1'b0 : 1'b1);
      endtask

      task run();
         uart_xaction item;
         vif.drv_cb.rxd <= 1'b1;
         forever begin
            items.get(item);
            drive_item(item);
         end
      endtask

   endclass

   // Reconstructs characters from `txd` and reports what it saw.
   //
   // Sampling only -- the monitor never drives, because a monitor that can
   // drive is a monitor that can hide a bug.
   class uart_monitor;

      virtual uart_if vif;
      uart_cfg        cfg;
      // Characters observed on the transmit line.
      mailbox #(uart_xaction) observed;
      // How many characters have been reconstructed.  The tests use this as
      // their completion condition.
      int unsigned seen;

      function new(virtual uart_if vif, uart_cfg cfg);
         this.vif      = vif;
         this.cfg      = cfg;
         this.observed = new();
         this.seen     = 0;
      endfunction

      // Waits half a bit period, which is where every sample is taken.
      protected task half_bit();
         repeat (cfg.baud_div / 2) @(vif.mon_cb);
      endtask

      task run();
         forever begin
            uart_xaction item = new();
            // Falling edge of the start bit.
            @(vif.mon_cb iff vif.mon_cb.txd == 1'b0);
            // Centre of the start bit, then the centre of each subsequent bit.
            half_bit();
            for (int i = 0; i < 8; i++) begin
               repeat (cfg.baud_div) @(vif.mon_cb);
               item.data[i] = vif.mon_cb.txd;
            end
            if (cfg.parity != 2'b00)
               repeat (cfg.baud_div) @(vif.mon_cb);
            repeat (cfg.baud_div) @(vif.mon_cb);
            item.bad_stop = (vif.mon_cb.txd == 1'b0);
            observed.put(item);
            seen++;
         end
      endtask

   endclass

   // Assembles a driver, a monitor and the coverage collector around one
   // interface.
   //
   // The environment is where the coverage binding in the plan becomes real.
   // ``.. coverage:: covergroup: uart_env.uart_cfg_cg`` names a UCIS instance
   // path; `build` below is what gives that instance its name.
   class uart_env;

      virtual uart_if vif;
      uart_cfg        cfg;
      uart_driver     drv;
      uart_monitor    mon;
      mailbox #(uart_xaction) items;

      function new(virtual uart_if vif);
         this.vif   = vif;
         this.items = new();
      endfunction

      function void build();
         cfg = new();
         // The plan binds coverage by instance path, not by declaration path.
         // `option.per_instance`, set in the covergroup itself, is what puts a
         // named instance in the database at all; the name set here is the
         // leaf of the bound path, and the scope it hangs under is this
         // environment's own instance name, `uart_env`.
         cfg.uart_cfg_cg.option.name = "uart_cfg_cg";
         drv = new(vif, cfg, items);
         mon = new(vif, cfg);
      endfunction

      // Programs the link and records the configuration as covered.
      function void configure(bit [15:0] baud_div, bit [1:0] parity);
         cfg.baud_div = baud_div;
         cfg.parity   = parity;
         cfg.sample_cfg();
      endfunction

      task run();
         fork
            drv.run();
            mon.run();
         join_none
      endtask

   endclass

   // ── tests ─────────────────────────────────────────────────────────────

   // Base test: brings up the environment and applies the reset sequence.
   //
   // Every test in the plan derives from this one.  `configure` and `main` are
   // the two hooks a derived test fills in, which is why the tests below are
   // each only a few lines: the plan's distinctions between them are
   // differences of stimulus, not of structure.
   class uart_base_test;

      uart_env env;
      uart_seq seq;

      function new(virtual uart_if vif);
         env = new(vif);
         env.build();
      endfunction

      // Programs the link.  The default is 115200 baud from a 50 MHz
      // reference, parity disabled -- the reset values in `uart_regs.rdl`.
      virtual function void configure();
         env.configure(16'd434, 2'b00);
      endfunction

      // The stimulus phase.  Override to change what is driven.
      virtual task main();
         seq = new(env.items);
         seq.body();
      endtask

      // Runs the reset sequence and hands over to the main sequence.
      virtual task run_test();
         configure();
         env.run();
         main();
         wait (env.mon.seen >= seq.count);
      endtask

   endclass

   // Smallest possible pass: a handful of clean characters at the reset
   // configuration.  Tagged `smoke` in the plan.
   class uart_smoke_test extends uart_base_test;

      function new(virtual uart_if vif);
         super.new(vif);
      endfunction

      virtual task main();
         seq = new(env.items);
         seq.count = 4;
         seq.body();
      endtask

   endclass

   // Walks a one through every data-bit position, so a shift-register fault at
   // any position is visible.  ``UART_1_1_1``, ``UART_1_1_2``.
   class uart_framing_test extends uart_base_test;

      function new(virtual uart_if vif);
         super.new(vif);
      endfunction

      virtual task main();
         uart_walking_ones_seq walk = new(env.items);
         seq = walk;
         walk.body();
      endtask

   endclass

   // Sweeps both parity polarities against random payloads.  ``UART_1_2_1``,
   // ``UART_1_2_2``.
   class uart_parity_test extends uart_base_test;

      function new(virtual uart_if vif);
         super.new(vif);
      endfunction

      virtual function void configure();
         env.configure(16'd434, 2'b01);
      endfunction

      virtual task main();
         foreach_parity: for (int unsigned mode = 1; mode <= 2; mode++) begin
            env.configure(16'd434, mode[1:0]);
            seq = new(env.items);
            seq.body();
         end
      endtask

   endclass

   // Directed test that drives characters at one fixed divisor.
   //
   // The three baud tests the plan names are this class with a different
   // `DIV`.  The plan writes them as one line -- ``uart_baud_{baud}_test`` --
   // and the substitution in `conf.py` expands it; the tests themselves are
   // just as thin.
   class uart_baud_test extends uart_base_test;

      // Divisor under test.  Overridden by the derived tests.
      protected bit [15:0] div = 16'd434;

      function new(virtual uart_if vif);
         super.new(vif);
      endfunction

      virtual function void configure();
         env.configure(div, 2'b00);
      endfunction

   endclass

   // 9600 baud from a 50 MHz reference.
   class uart_baud_9600_test extends uart_baud_test;
      function new(virtual uart_if vif);
         super.new(vif);
         div = 16'd5208;
      endfunction
   endclass

   // 115200 baud from a 50 MHz reference.  The reset configuration.
   class uart_baud_115200_test extends uart_baud_test;
      function new(virtual uart_if vif);
         super.new(vif);
         div = 16'd434;
      endfunction
   endclass

   // 460800 baud from a 50 MHz reference: the fastest rate the link supports.
   class uart_baud_460800_test extends uart_baud_test;
      function new(virtual uart_if vif);
         super.new(vif);
         div = 16'd109;
      endfunction
   endclass

   // Random divisors across the whole supported range, including the
   // boundaries 2 and 65535.  ``UART_3_2_2``.
   //
   // This is the test that fills the `typical` bin of `baud_div_cp`; the
   // directed tests above only reach three points in it.
   class uart_baud_random_test extends uart_baud_test;

      function new(virtual uart_if vif);
         super.new(vif);
      endfunction

      virtual task main();
         bit [15:0] candidates[$] = '{16'd2, 16'd65535};
         repeat (6) candidates.push_back(16'($urandom_range(2, 65535)));
         foreach (candidates[i]) begin
            env.configure(candidates[i], 2'b00);
            seq = new(env.items);
            seq.count = 1;
            seq.body();
         end
      endtask

   endclass

   // Programs divisors of 0 and 1 and confirms the bit clock matches a divisor
   // of 2.  ``UART_3_2_2``: a divisor below 2 is treated as 2.
   //
   // Note that the environment is configured with 2 while the design is
   // programmed with 0 -- the testbench's timing is what the design is being
   // measured against, so it must use the clamped value the design is required
   // to adopt.
   class uart_baud_clamp_test extends uart_baud_test;

      function new(virtual uart_if vif);
         super.new(vif);
      endfunction

      virtual task main();
         foreach_programmed: for (int unsigned programmed = 0; programmed <= 1; programmed++) begin
            env.configure(16'd2, 2'b00);
            seq = new(env.items);
            seq.count = 2;
            seq.body();
         end
      endtask

   endclass

endpackage
