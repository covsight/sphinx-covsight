Errors
======

Every construct on this page is wrong on purpose; ``test_checks.py`` asserts
which warning each one produces.

.. env:: orphan_env

   An environment outside any feature has nowhere to attach.

.. coverage::

   covergroup: nowhere.to.attach

.. feature:: Duplicated
   :id: FEAT-DUP

   .. env:: ip_simulation

      .. testpoint:: Unmapped testpoint
         :id: FEAT-DUP.tp_unmapped
         :stage: V1

         Neither ``.. tests::`` nor ``:na:``.

      .. testpoint:: Bad coverage and citations
         :id: FEAT-DUP.tp_bad
         :stage: V1

         .. covers::
            rule:UART.1.1.1,
            bogus:whatever,
            not-a-citation

         .. coverage::
            nonsense: uart_env.uart_cfg_cg
            no-colon-here

         .. tests:: sub_{unbound}_test

.. feature:: Duplicated again
   :id: FEAT-DUP

   A second feature with the same id.

   .. env:: ip_simulation

      An environment with no testpoints.

.. feature:: Feature whose environment has no testpoints
   :id: FEAT-NOTP

   .. env:: ip_simulation

      Nothing here yet.

.. feature:: Empty feature
   :id: FEAT-EMPTY

   No environments and no testpoints.
