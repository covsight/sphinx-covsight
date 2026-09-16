extensions = ["sphinx_systemverilog", "sphinx_covsight"]

sv_source_dirs = ["rtl"]
sv_doc_style = "native"

covsight_plan_name = "sv"
covsight_doc_base_url = ""
covsight_env_policy = {"ip_simulation": {"title": "IP Simulation"}}

exclude_patterns = ["_build"]
