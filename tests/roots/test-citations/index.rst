Citations
=========

.. feature:: Framing
   :id: FEAT-001

   Inline citation in prose: :rule:`UART_1_1_1`.

   .. env:: ip_simulation

      .. testpoint:: Resolvable and unresolvable
         :id: FEAT-001.tp_mixed
         :stage: V1

         .. covers::
            rule:UART_1_1_1,
            rule:UART_9_9_9,
            rdl:uart.CTRL.BAUD_DIV,
            sv:uart_cfg_cg

         .. tests:: mixed_test
