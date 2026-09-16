"""The records stored on the Sphinx environment.

These are plain dataclasses on purpose.  The environment is pickled between
builds, so anything stored here must be picklable and small; in particular no
docutils nodes are retained (they bloat the pickle and break rebuilds).

``ENV_VERSION`` must be bumped whenever one of these shapes changes, otherwise
a stale ``environment.pickle`` unpickles into the new code.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from sphinx.environment import BuildEnvironment

#: Bumped on any change to the record shapes below.
ENV_VERSION = 1

#: Citation prefix -> ``requirements[].system`` value in the emitted plan.
CITATION_SYSTEMS = {
    "rule": "spec",
    "rdl": "rdl",
    "sv": "sv",
}


@dataclass
class Citation:
    """One ``prefix:target`` citation, before or after resolution."""

    kind: str  # "rule" | "rdl" | "sv"
    target: str  # text after the prefix, verbatim
    docname: str = ""
    lineno: int = 0
    url: str | None = None  # filled during resolution
    title: str | None = None
    validated: bool = False  # target was checked against a live backend

    @property
    def system(self) -> str:
        return CITATION_SYSTEMS.get(self.kind, self.kind)

    @property
    def text(self) -> str:
        return f"{self.kind}:{self.target}"


@dataclass
class CoverageBinding:
    """One ``<type>: <path>`` coverage binding."""

    type: str  # covergroup | coverpoint | cross | assertion | ...
    path: str
    desc: str = ""
    docname: str = ""
    lineno: int = 0


@dataclass
class TestpointRecord:
    id: str
    title: str
    desc: str = ""
    feature_id: str = ""
    env: str | None = None
    stage: str | None = None
    priority: str | None = None
    weight: int = 1
    na: bool = False
    explicit_id: bool = False
    owner: str | None = None
    tags: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)  # pre-expansion
    coverage: list[CoverageBinding] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    docname: str = ""
    lineno: int = 0
    order: int = 0  # document order, for deterministic sort


@dataclass
class EnvRecord:
    env: str
    feature_id: str
    title: str | None = None
    scope: str | None = None
    difficulty: int | None = None
    coverage_score: int | None = None
    desc: str = ""
    docname: str = ""
    lineno: int = 0
    order: int = 0


@dataclass
class FeatureRecord:
    id: str
    title: str
    desc: str = ""
    owner: str | None = None
    status: str | None = None
    tags: list[str] = field(default_factory=list)
    parent_id: str | None = None  # features may nest
    citations: list[Citation] = field(default_factory=list)
    docname: str = ""
    lineno: int = 0
    order: int = 0


@dataclass
class PlanStore:
    """All records for the whole project, bucketed by docname.

    Bucketing is what makes ``env-purge-doc`` a single ``pop`` — the single
    most common way an extension like this goes quietly wrong is by leaving
    records of a deleted document in the environment.
    """

    features: dict[str, list[FeatureRecord]] = field(default_factory=dict)
    envs: dict[str, list[EnvRecord]] = field(default_factory=dict)
    testpoints: dict[str, list[TestpointRecord]] = field(default_factory=dict)

    # ── mutation ──────────────────────────────────────────────────────────

    def add_feature(self, rec: FeatureRecord) -> None:
        self.features.setdefault(rec.docname, []).append(rec)

    def add_env(self, rec: EnvRecord) -> None:
        self.envs.setdefault(rec.docname, []).append(rec)

    def add_testpoint(self, rec: TestpointRecord) -> None:
        self.testpoints.setdefault(rec.docname, []).append(rec)

    def purge(self, docname: str) -> None:
        """Forget everything read from *docname*."""
        self.features.pop(docname, None)
        self.envs.pop(docname, None)
        self.testpoints.pop(docname, None)

    def merge(self, other: PlanStore, docnames: Iterable[str] | None = None) -> None:
        """Merge records read by a parallel worker process."""
        names = set(docnames) if docnames is not None else None

        def wanted(docname: str) -> bool:
            return names is None or docname in names

        for docname, features in other.features.items():
            if wanted(docname):
                self.features[docname] = list(features)
        for docname, envs in other.envs.items():
            if wanted(docname):
                self.envs[docname] = list(envs)
        for docname, testpoints in other.testpoints.items():
            if wanted(docname):
                self.testpoints[docname] = list(testpoints)

    # ── iteration ─────────────────────────────────────────────────────────

    def all_features(self) -> Iterator[FeatureRecord]:
        for docname in sorted(self.features):
            yield from self.features[docname]

    def all_envs(self) -> Iterator[EnvRecord]:
        for docname in sorted(self.envs):
            yield from self.envs[docname]

    def all_testpoints(self) -> Iterator[TestpointRecord]:
        for docname in sorted(self.testpoints):
            yield from self.testpoints[docname]

    def all_citations(self) -> Iterator[Citation]:
        for feature in self.all_features():
            yield from feature.citations
        for tp in self.all_testpoints():
            yield from tp.citations

    @property
    def docnames(self) -> set[str]:
        return set(self.features) | set(self.envs) | set(self.testpoints)

    def is_empty(self) -> bool:
        return not (self.features or self.envs or self.testpoints)


def get_store(env: BuildEnvironment) -> PlanStore:
    """Return the plan store on *env*, creating it if necessary."""
    store = getattr(env, "covsight_plan", None)
    if not isinstance(store, PlanStore):
        store = PlanStore()
        env.covsight_plan = store  # type: ignore[attr-defined]
    return store
