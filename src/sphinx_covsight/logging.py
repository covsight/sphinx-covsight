"""Warning helpers with stable subtypes (D6.5).

Every message emitted by sphinx-covsight carries ``type="covsight"`` and a
subtype, so consumers can silence a class of message with

.. code-block:: python

   suppress_warnings = ["covsight.citation-unresolved"]

The subtypes are part of the public interface: renaming one is a breaking
change for anybody who has suppressed it.
"""

from __future__ import annotations

from typing import Any

from sphinx.util import logging as sphinx_logging

LOGGER = sphinx_logging.getLogger("sphinx_covsight")

#: Every subtype used anywhere in the extension.  ``checks.py`` and the
#: documentation reference this list, so a new subtype must be registered here.
SUBTYPES = (
    "nesting",
    "duplicate-id",
    "testpoint-unmapped",
    "empty-goal",
    "substitution",
    "missing-policy",
    "citation-id-charset",
    "citation-unresolved",
    "citation-syntax",
    "coverage-binding",
    "backend-absent",
    "config",
    "internal",
)


def warn(subtype: str, message: str, *, location: Any = None, **kwargs: Any) -> None:
    """Emit a ``covsight`` warning with *subtype*."""
    assert subtype in SUBTYPES, f"unregistered covsight warning subtype: {subtype}"
    LOGGER.warning(message, type="covsight", subtype=subtype, location=location, **kwargs)


def info(message: str, **kwargs: Any) -> None:
    """Emit an informational message (never a warning; never fails ``-W``)."""
    LOGGER.info("[covsight] " + message, **kwargs)


def verbose(message: str, **kwargs: Any) -> None:
    LOGGER.verbose("[covsight] " + message, **kwargs)
