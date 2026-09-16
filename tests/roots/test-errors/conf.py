extensions = ["sphinx_covsight"]

covsight_plan_name = "errors"
# Deliberately no policy entry for 'ip_simulation', to fire covsight.missing-policy.
covsight_env_policy = {}

exclude_patterns = ["_build"]
