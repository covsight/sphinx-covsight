import os

extensions = ["sphinx_peakrdl", "sphinx_covsight"]

# peakrdl_input_files are resolved against the working directory, not conf.py,
# so make them absolute.
_here = os.path.dirname(__file__)
peakrdl_input_files = [os.path.join(_here, "rtl", "uart_regs.rdl")]

covsight_plan_name = "rdl"
covsight_env_policy = {"ip_simulation": {"title": "IP Simulation"}}

exclude_patterns = ["_build"]
