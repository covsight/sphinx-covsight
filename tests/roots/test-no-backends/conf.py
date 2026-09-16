extensions = ["sphinx_covsight"]

covsight_plan_name = "no-backends"
# No covsight_needs_json, no sphinx-systemverilog, no sphinx-peakrdl: all three
# citation backends are absent, and the build must still succeed quietly.
covsight_env_policy = {"ip_simulation": {"title": "IP Simulation"}}

exclude_patterns = ["_build"]
