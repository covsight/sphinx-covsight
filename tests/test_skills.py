"""The bundled agent skills, and the ``agent.skills`` entry points.

IVPM's agents handler skips a skill whose ``SKILL.md`` is missing or whose
frontmatter lacks ``name``/``description`` — with a log line, not an error. So
a typo here costs nothing at install time and simply means the skill never
appears in ``.agents/skills/``. These tests are what makes that loud.

The frontmatter patterns are copied from ``ivpm.handlers.package_handler_agents``
deliberately: the contract is that parser's behaviour, not a YAML parse.
"""

from __future__ import annotations

import re
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from sphinx_covsight import skills

# ivpm.handlers.package_handler_agents._FRONTMATTER_RE / _FIELD_RE
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
FIELD_RE = re.compile(r"^(\w[\w-]*):\s*(.+)$", re.MULTILINE)

ENTRY_POINTS = {
    "sphinx-covsight-plan": skills.plan_skill_dir,
    "sphinx-covsight-spec": skills.spec_skill_dir,
}


def frontmatter(skill_md: Path) -> dict[str, str]:
    match = FRONTMATTER_RE.match(skill_md.read_text(encoding="utf-8"))
    assert match is not None, f"{skill_md}: no '---' delimited frontmatter block"
    return dict(FIELD_RE.findall(match.group(1)))


def test_get_skill_dirs_lists_every_bundled_skill():
    dirs = [Path(p) for p in skills.get_skill_dirs()]
    assert len(dirs) == len(skills.SKILLS)
    for directory in dirs:
        assert (directory / "SKILL.md").is_file(), f"{directory} has no SKILL.md"


@pytest.mark.parametrize("name", skills.SKILLS)
def test_frontmatter_is_complete(name):
    fields = frontmatter(Path(skills.get_skill_dirs()[skills.SKILLS.index(name)]) / "SKILL.md")
    assert fields.get("name") == name, "frontmatter 'name' must match the directory name"
    # The description is the only thing an agent sees when deciding whether the
    # skill is relevant, so a one-liner is not enough.
    assert len(fields.get("description", "")) > 200


@pytest.mark.parametrize("ep_name,accessor", sorted(ENTRY_POINTS.items()))
def test_one_entry_point_per_skill(ep_name, accessor):
    """The handler names each link after the entry point, not the frontmatter.

    An entry point returning more than one directory gets the second link named
    ``<ep_name>-2``, so the accessors must stay one-to-one with the skills.
    """
    returned = accessor()
    assert len(returned) == 1
    assert frontmatter(Path(returned[0]) / "SKILL.md")["name"] == ep_name


def test_entry_points_are_registered():
    registered = {ep.name: ep for ep in entry_points(group="agent.skills")}
    for ep_name in ENTRY_POINTS:
        assert ep_name in registered, (
            f"{ep_name} is not registered; reinstall the package after editing pyproject.toml"
        )
        assert registered[ep_name].load()() == ENTRY_POINTS[ep_name]()


@pytest.mark.parametrize("name", skills.SKILLS)
def test_referenced_reference_files_exist(name):
    """Every ``references/<file>.md`` named in a SKILL.md is shipped."""
    directory = Path(skills.get_skill_dirs()[skills.SKILLS.index(name)])
    body = (directory / "SKILL.md").read_text(encoding="utf-8")
    for referenced in sorted(set(re.findall(r"references/([\w.-]+\.md)", body))):
        assert (directory / "references" / referenced).is_file(), (
            f"{name}/SKILL.md points at references/{referenced}, which does not exist"
        )
