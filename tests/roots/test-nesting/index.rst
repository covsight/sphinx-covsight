Nesting
=======

Cross-references into the plan: :covsight:feature:`FEAT-P`,
:covsight:tp:`FEAT-P.tp_no_env`, and a deliberately broken one,
:covsight:tp:`FEAT-NOPE`.

.. feature:: Parent feature
   :id: FEAT-P

   A feature that contains another feature.

   .. feature:: Child feature
      :id: FEAT-C

      .. env:: ip_simulation

         .. testpoint:: Child testpoint
            :stage: V1

            .. tests:: child_test

   .. testpoint:: Testpoint with no environment
      :id: FEAT-P.tp_no_env
      :stage: V1

      A testpoint may hang directly off a feature when no environment
      distinction is meaningful.

      .. tests:: parent_test

.. feature:: Feature with directives inside a container
   :id: FEAT-K

   .. container:: note-like

      .. env:: ip_simulation

         .. container:: also-nested

            .. testpoint:: Testpoint inside two containers
               :stage: V2

               .. tests:: container_test
