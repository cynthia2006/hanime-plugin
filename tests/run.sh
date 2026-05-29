#!/usr/bin/env bash
# E2E test runner. Verifies the test dependencies are importable, then
# delegates to pytest with whatever args were passed through.
#
# Examples:
#   tests/run.sh                                   # all sites, all modes
#   tests/run.sh -k hanime1                        # just hanime1 cases
#   tests/run.sh -k 'no-cookies-no-impersonate'    # only the minimal mode
#   tests/run.sh tests/sites/hanime1/test_hanime1.py::test_video
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PYTHON="${PYTHON:-python3}"

if ! "$PYTHON" -c 'import pytest' 2>/dev/null; then
    echo 'error: pytest is not installed in the active Python environment.' >&2
    echo 'Install the test extras with:' >&2
    echo "    $PYTHON -m pip install -e '.[test]'" >&2
    exit 2
fi

exec "$PYTHON" -m pytest "$@"
