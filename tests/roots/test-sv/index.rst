SystemVerilog citations
=======================

.. autosvclass:: uart_pkg::uart_cfg
   :members:

.. autosvclass:: uart_pkg::uart_base_test

.. autosvclass:: uart_pkg::uart_rx_mon
   :members:

.. autosvclass:: uart_pkg::uart_tx_mon
   :members:

.. feature:: Baud rate generation
   :id: FEAT-002

   .. env:: ip_simulation

      .. testpoint:: Divisor sweep
         :id: FEAT-002.tp_divisors
         :stage: V2

         .. covers::
            sv:uart_cfg_cg,
            sv:uart_pkg::uart_cfg::uart_cfg_cg,
            sv:no_such_covergroup,
            sv:shared_cg

         .. coverage::
            covergroup: uart_env.uart_cfg_cg
            coverpoint: uart_env.uart_cfg_cg.baud_div_cp
            coverpoint: uart_env.uart_cfg_cg.nonexistent_cp

         .. tests:: uart_baud_test
