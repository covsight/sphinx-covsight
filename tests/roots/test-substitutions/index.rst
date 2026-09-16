Substitutions
=============

.. feature:: Expansion
   :id: FEAT-001

   .. env:: ip_simulation

      .. testpoint:: Single key
         :id: FEAT-001.tp_single
         :stage: V1

         .. tests:: uart_baud_{baud}_test

      .. testpoint:: Two keys expand cartesian-wise
         :id: FEAT-001.tp_cross
         :stage: V1

         .. tests:: uart_{baud}_{parity}_test

      .. testpoint:: Literal names are untouched
         :id: FEAT-001.tp_literal
         :stage: V1

         .. tests::
            uart_smoke_test,
            uart_regression_test

      .. testpoint:: Unbound placeholder
         :id: FEAT-001.tp_unbound
         :stage: V1

         .. tests:: uart_{stopbits}_test
