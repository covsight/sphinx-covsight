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

See `docs/` for the full guides, and `docs/example/` for a worked project.

## Licence

Apache-2.0
