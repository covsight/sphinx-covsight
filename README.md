# sphinx-covsight

Author a verification plan as a Sphinx document, and extract it as a
[covsight](https://covsight.io) testplan v1 artifact that is deterministic and
byte-stable.

```rst
.. feature:: Baud rate generation
   :id: FEAT-002

   The transmitter and receiver derive their bit clock from a programmable
   divisor.

   .. covers:: rule:UART_3_2_1, rdl:uart.CTRL.BAUD_DIV

   .. env:: ip_simulation
      :scope: block
      :difficulty: 3
      :coverage: 8

      .. testpoint:: All supported divisor values
         :stage: V2
         :priority: high

         Sweep the divisor across every supported baud rate.

         .. tests:: uart_baud_{baud}_test
```

The document is what a reviewer reads; the extracted
`testplan.json` is what a tool walks.  Verification policy (approach,
reasoning, exit criteria, scoring) lives in `conf.py`, so changing policy is a
one-line diff rather than an edit across every feature.

Both reStructuredText and MyST/Markdown are supported by the same directive
implementations.

## Install

```console
pip install sphinx-covsight
```

Optional citation backends, each independently optional:

```console
pip install "sphinx-covsight[sv]"    # sv: citations, via sphinx-systemverilog
pip install "sphinx-covsight[rdl]"   # rdl: citations, via sphinx-peakrdl
```

## Use

```python
# conf.py
extensions = ["sphinx_covsight"]
covsight_plan_name = "uart"
covsight_needs_json = "_spec/needs.json"
covsight_env_policy = {...}
```

```console
sphinx-build -b html plan/ _build/html      # renders the plan, writes testplan.json
covsight-testplan build plan/ -o testplan.json
covsight-testplan check plan/ --against testplan.json
```

See the [guides](https://dvkit.org/covsight/sphinx-covsight/) for the full
documentation.  Every snippet in them is quoted from one worked example — a
miniature UART — which is published alongside them as the two projects it
really is: the
[specification](https://dvkit.org/covsight/sphinx-covsight/example/spec/) and
the [plan](https://dvkit.org/covsight/sphinx-covsight/example/plan/) that cites
it, with the
[extracted testplan](https://dvkit.org/covsight/sphinx-covsight/example/plan/testplan.json)
next door to the plan it came from.  The
[design](https://dvkit.org/covsight/sphinx-covsight/example/plan/design.html) and
[testbench](https://dvkit.org/covsight/sphinx-covsight/example/plan/testbench.html)
are real source, elaborated by the test suite, so every citation in the example
has something on the other end of it.  The source is in `docs/example/`; build
the whole site with `docs/build.sh`.

## Licence

Apache-2.0
