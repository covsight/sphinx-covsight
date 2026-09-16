Baud rate generation
====================

This page is authored in reStructuredText while the rest of the plan is MyST,
to demonstrate that the two formats compose in one project and extract
identically.

.. doc:feature-start

.. feature:: Baud rate generation
   :id: FEAT-002
   :owner: uart-verification
   :tags: uart, baud

   The transmitter and receiver derive their bit clock from a programmable
   divisor.  The divisor is writable while the link is idle and takes effect at
   the next character boundary.

   .. covers::
      rule:UART_3_2_1, rule:UART_3_2_2,
      rdl:uart.CTRL.BAUD_DIV

   .. env:: ip_simulation
      :scope: block
      :difficulty: 3
      :coverage: 8

      .. testpoint:: All supported divisor values
         :id: FEAT-002.tp_divisors
         :stage: V2
         :priority: high

         Sweep the divisor across every supported baud rate and confirm bit
         timing at each, including the boundary values 2 and 65535.

         .. covers:: rule:UART_3_2_1, rule:UART_3_2_2

         .. coverage::
            covergroup: uart_env.uart_cfg_cg
            coverpoint: uart_env.uart_cfg_cg.baud_div_cp

         .. tests:: uart_baud_{baud}_test, uart_baud_random_test

      .. testpoint:: Divisor below the supported minimum is clamped
         :id: FEAT-002.tp_divisor_clamp
         :stage: V2
         :priority: low

         Program divisors of 0 and 1 and confirm the bit clock matches a
         divisor of 2, per :rule:`UART_3_2_2`.

         .. covers:: rule:UART_3_2_2

         .. tests:: uart_baud_clamp_test

   .. env:: formal
      :scope: block
      :difficulty: 6
      :coverage: 4

      .. testpoint:: Divisor write during active transfer is ignored
         :id: FEAT-002.tp_divisor_locked
         :stage: V2

         Prove that a write to the divisor while a character is in flight does
         not change the bit clock until the character completes.

         .. covers:: rule:UART_3_2_4

         .. tests:: uart_baud_lock_props

.. doc:feature-end
