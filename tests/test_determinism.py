"""Byte stability, set-field ordering, incremental purge, and parallel merge.

The emitted JSON is the artifact a downstream audit SHA-binds, so everything
here is a hard requirement rather than a nicety.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import find_testpoint
from sphinx_covsight.emit import plan_sha256


def build(make_app, srcdir: Path, **kwargs):
    app = make_app(srcdir=srcdir, **kwargs)
    app.build()
    return app


def plan_bytes(app) -> bytes:
    return (Path(app.outdir) / "testplan.json").read_bytes()


@pytest.mark.sphinx("html", testroot="basic", freshenv=True)
def test_two_builds_are_byte_identical(app, make_app):
    app.build()
    first = plan_bytes(app)

    second_app = make_app(srcdir=app.srcdir, freshenv=True)
    second_app.build()
    assert plan_bytes(second_app) == first


@pytest.mark.sphinx("html", testroot="basic", freshenv=True)
def test_set_fields_are_order_insensitive(app, make_app, sphinx_test_tempdir):
    """Reordering tags, coverage bindings and citations must not change the plan.

    Without this, a cosmetic source reorder produces a spurious plan diff and
    erodes trust in SHA-binding.
    """
    app.build()
    original = json.loads(plan_bytes(app))

    reordered_dir = sphinx_test_tempdir / "basic-reordered"
    shutil.copytree(app.srcdir, reordered_dir, dirs_exist_ok=True)
    index = reordered_dir / "index.rst"
    text = index.read_text(encoding="utf-8")
    text = text.replace(":tags: uart, framing", ":tags: framing, uart")
    text = text.replace(
        "            covergroup: uart_env.uart_cfg_cg\n"
        "            coverpoint: uart_env.uart_cfg_cg.parity_cp",
        "            coverpoint: uart_env.uart_cfg_cg.parity_cp\n"
        "            covergroup: uart_env.uart_cfg_cg",
    )
    text = text.replace(
        "      rule:UART_1_1_1,\n      rule:UART_1_1_2",
        "      rule:UART_1_1_2,\n      rule:UART_1_1_1",
    )
    index.write_text(text, encoding="utf-8")

    reordered = make_app(srcdir=reordered_dir, freshenv=True)
    reordered.build()
    assert json.loads(plan_bytes(reordered)) == original


@pytest.mark.sphinx("html", testroot="basic", freshenv=True)
def test_prose_edit_changes_only_desc(app, make_app, sphinx_test_tempdir):
    app.build()
    original = json.loads(plan_bytes(app))

    edited_dir = sphinx_test_tempdir / "basic-edited"
    shutil.copytree(app.srcdir, edited_dir, dirs_exist_ok=True)
    index = edited_dir / "index.rst"
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "The receiver samples each bit", "The receiver samples every bit"
        ),
        encoding="utf-8",
    )
    edited_app = make_app(srcdir=edited_dir, freshenv=True)
    edited_app.build()
    edited = json.loads(plan_bytes(edited_app))

    from sphinx_covsight.cli import diff_plans

    differences = diff_plans(original, edited)
    assert len(differences) == 1
    assert differences[0].startswith("goals[0].desc")


@pytest.mark.sphinx("html", testroot="basic", freshenv=True)
def test_provenance_is_a_sidecar(app):
    """No timestamp, path or version may perturb the hashed artifact."""
    app.build()
    plan = json.loads(plan_bytes(app))
    text = json.dumps(plan)
    assert "generated_at" not in text
    assert str(app.srcdir) not in text

    sidecar = json.loads(
        (Path(app.outdir) / "testplan.provenance.json").read_text(encoding="utf-8")
    )
    assert sidecar["testplan_sha256"] == plan_sha256(plan)
    assert sidecar["score_expression"] == "(11 - difficulty) * coverage"
    assert set(sidecar["citation_backends"]) == {"rule", "sv", "rdl"}
    assert sidecar["counts"]["testpoints"] == 3


@pytest.mark.sphinx(
    "html", testroot="basic", freshenv=True, confoverrides={"covsight_output_format": "both"}
)
def test_yaml_is_emitted_alongside(app):
    app.build()
    import yaml

    payload = yaml.safe_load((Path(app.outdir) / "testplan.yaml").read_text(encoding="utf-8"))
    assert payload == json.loads(plan_bytes(app))


# ── incremental ───────────────────────────────────────────────────────────────


def private_copy(rootdir: Path, sphinx_test_tempdir: Path, testroot: str, name: str) -> Path:
    """A throwaway copy of a testroot, for a test that edits its sources.

    Every test naming the same ``testroot`` shares one source directory for the
    whole session on Sphinx < 8.2, so a test that deletes a file from it changes
    what a later test reads.  That is exactly how this file's own
    ``test_parallel_read_matches_serial`` came to fail only under an older
    Sphinx, and only when run after the deletion test.
    """
    srcdir = sphinx_test_tempdir / name
    shutil.rmtree(srcdir, ignore_errors=True)
    shutil.copytree(rootdir / f"test-{testroot}", srcdir)
    return srcdir


def test_incremental_delete_feature(make_app, plan_of, rootdir, sphinx_test_tempdir):
    """The env-purge-doc failure is silent and produces stale-but-plausible output.

    This is the highest-value single test in the suite.
    """
    srcdir = private_copy(rootdir, sphinx_test_tempdir, "incremental", "incremental-delete")
    first = make_app(srcdir=srcdir, freshenv=True)
    first.build()
    plan = plan_of(first)
    assert "FEAT-B" in {goal["id"] for goal in plan["goals"]}

    (srcdir / "feat_b.rst").unlink()
    index = srcdir / "index.rst"
    index.write_text(index.read_text(encoding="utf-8").replace("   feat_b\n", ""), encoding="utf-8")

    rebuilt = make_app(srcdir=srcdir)  # NOT freshenv: this is the incremental path
    rebuilt.build()
    after = {goal["id"] for goal in plan_of(rebuilt)["goals"]}
    assert "FEAT-B" not in after
    assert "FEAT-A" in after


def test_incremental_edit_leaves_others_untouched(make_app, plan_of, rootdir, sphinx_test_tempdir):
    srcdir = private_copy(rootdir, sphinx_test_tempdir, "incremental", "incremental-edit")
    first = make_app(srcdir=srcdir, freshenv=True)
    first.build()
    before = plan_of(first)

    feat_a = srcdir / "feat_a.rst"
    feat_a.write_text(
        feat_a.read_text(encoding="utf-8").replace(".. tests:: a_test", ".. tests:: a2_test"),
        encoding="utf-8",
    )
    rebuilt = make_app(srcdir=srcdir)
    rebuilt.build()
    after = plan_of(rebuilt)

    from sphinx_covsight.cli import diff_plans

    differences = diff_plans(before, after)
    assert differences == ["goals[0].goals[0].testpoints[0].tests[0]: 'a_test' -> 'a2_test'"]


@pytest.mark.sphinx("html", testroot="incremental", freshenv=True, parallel=2)
def test_parallel_read_matches_serial(app, make_app, plan_of, sphinx_test_tempdir):
    """env-merge-info omission loses data only under ``-j``."""
    app.build()
    parallel_plan = plan_of(app)

    serial_dir = sphinx_test_tempdir / "incremental-serial"
    shutil.rmtree(serial_dir, ignore_errors=True)
    shutil.copytree(app.srcdir, serial_dir)
    serial = make_app(srcdir=serial_dir, freshenv=True)
    serial.build()

    assert parallel_plan == plan_of(serial)
    assert {goal["id"] for goal in parallel_plan["goals"]} == {
        f"FEAT-{letter}" for letter in "ABCDEFGH"
    }


@pytest.mark.sphinx("html", testroot="basic", freshenv=True)
def test_env_version_is_declared(app):
    from sphinx_covsight import ENV_VERSION

    assert isinstance(ENV_VERSION, int)
    assert app.registry.get_envversion(app)["sphinx_covsight"] == ENV_VERSION


def test_failed_build_publishes_nothing(make_app, rootdir, sphinx_test_tempdir):
    """A failed build must never leave an artifact behind."""
    broken_dir = sphinx_test_tempdir / "basic-broken"
    shutil.copytree(rootdir / "test-basic", broken_dir, dirs_exist_ok=True)
    from sphinx_covsight import on_build_finished

    class Boom(Exception):
        pass

    broken = make_app(srcdir=broken_dir, freshenv=True)
    on_build_finished(broken, Boom("build failed"))
    assert not (Path(broken.outdir) / "testplan.json").exists()


@pytest.mark.sphinx("html", testroot="basic")
def test_testpoint_order_follows_the_document(app, plan_of):
    app.build()
    plan = plan_of(app)
    assert [goal["id"] for goal in plan["goals"]] == ["FEAT-001", "FEAT-002"]
    assert [goal["id"] for goal in plan["goals"][1]["goals"]] == [
        "FEAT-002.ip_simulation",
        "FEAT-002.formal",
    ]
    assert find_testpoint(plan, "FEAT-002.tp_divisor_locked")["stage"] == "V2"
