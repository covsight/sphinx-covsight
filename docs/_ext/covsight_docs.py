"""Documentation-only directives that generate reference tables from the code.

The configuration and directive references are generated rather than written,
so they cannot drift from the implementation.
"""

from __future__ import annotations

from typing import Any

from docutils import nodes
from docutils.statemachine import StringList
from sphinx.util.docutils import SphinxDirective

from sphinx_covsight import CONFIG_VALUES
from sphinx_covsight.directives import DIRECTIVES


def _table(headings: list[str], rows: list[list[str]], widths: list[int]) -> str:
    """Render a list-table as RST source, so the cells can hold inline markup."""
    lines = [
        ".. list-table::",
        "   :header-rows: 1",
        "   :widths: " + " ".join(str(w) for w in widths),
        "",
    ]
    for row in [headings, *rows]:
        for index, cell in enumerate(row):
            prefix = "   * - " if index == 0 else "     - "
            cell_lines = cell.split("\n")
            lines.append(prefix + cell_lines[0])
            lines.extend("       " + extra for extra in cell_lines[1:])
    return "\n".join(lines)


class _GeneratedTable(SphinxDirective):
    has_content = False

    def render(self) -> str:  # pragma: no cover - overridden
        raise NotImplementedError

    def run(self) -> list[nodes.Node]:
        container = nodes.container()
        self.state.nested_parse(StringList(self.render().splitlines(), source=""), 0, container)
        return container.children


class ConfigTable(_GeneratedTable):
    """Every ``covsight_*`` value, its default, and its effect."""

    def render(self) -> str:
        rows = []
        for name, default, rebuild, doc in CONFIG_VALUES:
            rows.append(
                [
                    f"``{name}``",
                    f"``{default!r}``",
                    f"``{rebuild}``",
                    doc,
                ]
            )
        return _table(["Value", "Default", "Rebuild", "Effect"], rows, [26, 18, 8, 48])


_ARGUMENTS = {
    "feature": "title",
    "env": "environment name",
    "testpoint": "title",
    "covers": "one citation (optional)",
    "coverage": "—",
    "tests": "one test name (optional)",
}

_BODIES = {
    "feature": "prose, then nested ``env``/``testpoint``/``covers``",
    "env": "prose, then nested ``testpoint``",
    "testpoint": "prose, then nested ``covers``/``coverage``/``tests``",
    "covers": "``<prefix>:<target>`` per line or comma-separated",
    "coverage": "``<type>: <path>`` per line",
    "tests": "test names, per line or comma-separated",
}


class DirectiveTable(_GeneratedTable):
    """The six directives with their arguments, options and nesting rules."""

    def render(self) -> str:
        rows = []
        for name, directive in DIRECTIVES.items():
            options = sorted(directive.option_spec or {})
            required = {
                option
                for option, converter in (directive.option_spec or {}).items()
                if getattr(converter, "__name__", "") == "unchanged_required"
            }
            rendered = ", ".join(
                f"``:{option}:``" + (" (required)" if option in required else "")
                for option in options
            )
            parents = ", ".join(
                "document root" if parent is None else f"``{parent}``"
                for parent in directive.allowed_parents
            )
            rows.append(
                [
                    f"``{name}``",
                    _ARGUMENTS[name],
                    rendered or "—",
                    _BODIES[name],
                    parents,
                ]
            )
        return _table(
            ["Directive", "Argument", "Options", "Body", "May appear in"],
            rows,
            [12, 14, 30, 30, 14],
        )


class WarningTable(_GeneratedTable):
    """Every warning subtype, for ``suppress_warnings``."""

    def render(self) -> str:
        from sphinx_covsight.logging import SUBTYPES

        rows = [[f"``covsight.{subtype}``", _SUBTYPE_DOC.get(subtype, "")] for subtype in SUBTYPES]
        return _table(["Subtype", "Emitted when"], rows, [30, 70])


_SUBTYPE_DOC = {
    "nesting": "A directive appears somewhere it cannot attach (an error).",
    "duplicate-id": "Two features or two testpoints share an id.",
    "testpoint-unmapped": "A testpoint has neither ``.. tests::`` nor ``:na:``.",
    "empty-goal": "A feature has no environments, or an environment no testpoints.",
    "substitution": "A ``{key}`` in a test name has no binding.",
    "missing-policy": "An environment has no ``covsight_env_policy`` entry.",
    "citation-id-charset": "A ``rule:`` id contains characters outside ``[A-Za-z0-9_]``.",
    "citation-unresolved": "A citation's backend is present but the target is not found.",
    "citation-syntax": "A ``covers`` line is not ``<prefix>:<target>``.",
    "coverage-binding": "A binding is malformed, or its leaf name is unknown to the ``sv`` domain.",
    "backend-absent": "Reserved for backend-availability reporting.",
    "config": "A configuration value is not usable as given.",
    "internal": "The env denormalization invariant was violated (an extension bug).",
}


def setup(app: Any) -> dict[str, Any]:
    app.add_directive("covsight-config-table", ConfigTable)
    app.add_directive("covsight-directive-table", DirectiveTable)
    app.add_directive("covsight-warning-table", WarningTable)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
