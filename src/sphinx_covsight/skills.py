"""Agent-skill discovery hooks.

Registered via the ``agent.skills`` entry-point group so that any environment
with sphinx-covsight installed exposes the bundled authoring skills to IVPM's
agents handler, which links them into ``.agents/skills/`` (and the per-tool
mirrors ``.claude/skills/`` and ``.cursor/skills/``).

**One entry point per skill, each returning a single directory.** The handler
names a link after the *entry point*, not after the ``name:`` in the skill's
frontmatter, and uniquifies collisions by appending ``-2``. A single entry point
returning both directories therefore produces ``sphinx-covsight`` and
``sphinx-covsight-2``, where which is which depends on list order. Naming the
entry points after the skills keeps the two in agreement.

Nothing in the extension imports this module; it exists for the entry points.
"""

from __future__ import annotations

import os

#: Directory names under ``share/skills``.  Each must contain a ``SKILL.md``
#: with ``name:`` and ``description:`` frontmatter, or the agents handler skips
#: it with a warning.
SKILLS = ("sphinx-covsight-plan", "sphinx-covsight-spec")


def get_skill_dirs() -> list[str]:
    """Return every bundled agent-skill directory."""
    here = os.path.dirname(os.path.abspath(__file__))
    return [os.path.join(here, "share", "skills", name) for name in SKILLS]


def _one(name: str) -> list[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    return [os.path.join(here, "share", "skills", name)]


def plan_skill_dir() -> list[str]:
    """Authoring a verification plan."""
    return _one("sphinx-covsight-plan")


def spec_skill_dir() -> list[str]:
    """Authoring a specification whose rules a plan can cite."""
    return _one("sphinx-covsight-spec")
