extensions = ["myst_parser", "sphinx_covsight"]

myst_enable_extensions = ["colon_fence"]

covsight_plan_name = "uart"
covsight_plan_owner = "verification"
covsight_substitutions = {"baud": ["9600", "115200"]}

covsight_env_policy = {
    "ip_simulation": {
        "title": "IP Simulation",
        "approach": "Constrained-random stimulus and assertions targeting {feature}.",
        "reasoning": "Controllability and observability at practical run time.",
        "exit_criteria": [
            "100% regression pass",
            "95%+ functional coverage",
        ],
    },
    "formal": {
        "title": "Formal",
        "approach": "Property proofs over {feature} in the {env} environment.",
        "exit_criteria": ["All properties proven or bounded"],
    },
}

exclude_patterns = ["_build"]
