#!/usr/bin/env bash
#
# Build the whole published documentation set.
#
# There are THREE Sphinx projects here, not one, and the published site nests
# them:
#
#   <out>/                 the sphinx-covsight documentation
#   <out>/example/spec/    the UART specification the example plan cites
#   <out>/example/plan/    the UART verification plan itself
#
# They stay separate projects because that is the topology the extension
# assumes: a specification publishes `needs.json`, and a plan in a different
# repository, with a different release cadence, consumes it. Collapsing them
# into one Sphinx project to make the site build easier would demonstrate an
# arrangement nobody actually has, and would take the example's test fixture
# with it.
#
# USE THIS RATHER THAN A BARE `sphinx-build docs`. The main docs link into the
# two sub-builds with relative hrefs, which Sphinx does not resolve and cannot
# check; building the main project alone produces a doc set whose example links
# are dead. Both CI workflows call this script so that CI and a laptop cannot
# disagree about what "the docs" means.
#
# The pinned `example/plan/_spec/needs.json` means the spec build does NOT have
# to precede the plan build -- the plan resolves citations against the committed
# copy, never against a fresh build. The order below is narrative, not a
# dependency. What keeps the pin honest is a test
# (`test_pinned_needs_json_matches_the_spec`) and a CI step, not this script.
#
# Usage:
#   docs/build.sh [output-dir]      (default: docs/_build/html)

set -euo pipefail

here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
out=${1:-"$here/_build/html"}
mkdir -p "$out"
out=$(cd "$out" && pwd)

# Per-project doctree directories. Sharing one would have three projects with
# different extensions and different config overwrite each other's environment,
# which shows up as confusing cross-project warnings on an incremental build.
doctrees=$(dirname "$out")/doctrees

# Every build is strict. --keep-going reports all warnings rather than the first,
# which is what makes a broken docs build one fix instead of several rounds.
sphinx() {
    local name=$1 src=$2 dst=$3
    echo "==> $name"
    python3 -m sphinx -W --keep-going -b html \
        -d "$doctrees/$name" "$src" "$dst"
}

sphinx spec "$here/example/spec" "$out/example/spec"
sphinx plan "$here/example/plan" "$out/example/plan"
sphinx main "$here" "$out"

echo
echo "documentation:   $out/index.html"
echo "example spec:    $out/example/spec/index.html"
echo "example plan:    $out/example/plan/index.html"
echo "extracted plan:  $out/example/plan/testplan.json"
