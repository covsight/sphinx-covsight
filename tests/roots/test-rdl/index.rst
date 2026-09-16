SystemRDL citations
===================

.. rdl:doctree:: uart

.. feature:: Baud rate generation
   :id: FEAT-002

   .. covers:: rdl:uart.CTRL.BAUD_DIV

   .. env:: ip_simulation

      .. testpoint:: Divisor sweep
         :id: FEAT-002.tp_divisors
         :stage: V2

         .. covers::
            rdl:uart.CTRL,
            rdl:uart.CTRL.PARITY_EN,
            rdl:uart.NOSUCH.FIELD

         .. tests:: uart_baud_test
