extensions = ["sphinx_covsight"]

covsight_plan_name = "substitutions"
covsight_substitutions = {
    "baud": ["9600", "115200"],
    "parity": ["none", "even", "odd"],
}
covsight_env_policy = {"ip_simulation": {"title": "IP Simulation"}}

exclude_patterns = ["_build"]
