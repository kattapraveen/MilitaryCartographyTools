#!/usr/bin/env bash
#
# Run the headless PyQGIS test suite (tests/) using QGIS's own
# bundled Python - the `qgis` package isn't pip-installable, so a
# regular Python/pytest environment can't run these. See
# docs/developer-guide.md for the reasoning and how to adapt this
# for a different QGIS install location/version.
#
# Usage:
#   ./run_tests.sh                  # run everything
#   ./run_tests.sh MilitaryCartographyTools.tests.test_layout   # one module
#   ./run_tests.sh MilitaryCartographyTools.tests.test_layout.TestCreateAndUpdateLayout.test_create_layout_has_a_map_item

set -euo pipefail

QGIS_APP="${QGIS_APP:-/Applications/QGIS-final-4_2_1.app/Contents}"

if [ ! -d "$QGIS_APP" ]; then
    echo "QGIS app bundle not found at: $QGIS_APP" >&2
    echo "Set QGIS_APP to your QGIS install's Contents directory, e.g.:" >&2
    echo "  QGIS_APP=/Applications/QGIS.app/Contents ./run_tests.sh" >&2
    exit 1
fi

# Auto-detect the bundled Python version/executable rather than
# hardcoding one - different QGIS releases (e.g. 3.44 vs 4.0) bundle
# different Python versions, and hardcoding breaks silently against
# whichever one isn't what was hardcoded.
PYTHON_BIN="$(find "$QGIS_APP/MacOS" -maxdepth 1 -name 'python3.*' -type f | sort -V | tail -1)"
if [ -z "$PYTHON_BIN" ]; then
    echo "Could not find a python3.* executable under: $QGIS_APP/MacOS" >&2
    exit 1
fi
PYTHON_VERSION="$(basename "$PYTHON_BIN")"

export PYTHONHOME="$QGIS_APP/Frameworks"
export PYTHONPATH="$QGIS_APP/Frameworks/lib/$PYTHON_VERSION/site-packages"
export DYLD_FRAMEWORK_PATH="$QGIS_APP/Frameworks"
export DYLD_LIBRARY_PATH="$QGIS_APP/Frameworks:$QGIS_APP/PlugIns"
export QGIS_PREFIX_PATH="$QGIS_APP/MacOS"
export QT_QPA_PLATFORM=offscreen
export PROJ_DATA="$QGIS_APP/Resources/qgis/proj"
export GDAL_DATA="$QGIS_APP/Resources/qgis/gdal"

# Needed for terrain/ (Tanaka contours), which uses QGIS's Processing
# framework: `import processing` resolves to the actual Processing
# plugin (not just the thin qgis.processing helper) only with its
# directory on PYTHONPATH, and gdal:contour/gdal:warpreproject shell
# out to the gdal_contour/gdal_translate-family binaries bundled
# under Contents/MacOS, which needs to be on PATH to be found. Both
# are already set up automatically inside a normally-launched QGIS
# GUI session - only this headless harness needs them added by hand.
export PYTHONPATH="$QGIS_APP/Resources/qgis/python/plugins:$PYTHONPATH"
export PATH="$QGIS_APP/MacOS:$PATH"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The plugin package needs to be importable as
# `MilitaryCartographyTools.<module>` (matching how QGIS itself
# imports an installed plugin) - add the repo's PARENT directory
# to the path, not the repo itself.
export PYTHONPATH="$(dirname "$REPO_ROOT"):$PYTHONPATH"

TARGET="${1:-discover}"

if [ "$TARGET" = "discover" ]; then
    # -s scopes discovery to tests/ only - pointing it at the repo
    # root instead makes unittest also try to import sibling
    # packages (grid/, layout/, ...) as bare top-level modules
    # while probing them for test files, which breaks their own
    # `from ..core import ...`-style relative imports. -t sets the
    # top-level package root one level up, so tests/ resolves as
    # MilitaryCartographyTools.tests (a real subpackage) rather
    # than a bare top-level "tests".
    "$PYTHON_BIN" -m unittest discover \
        -s "$REPO_ROOT/tests" \
        -t "$(dirname "$REPO_ROOT")" \
        -p "test_*.py" -v
else
    "$PYTHON_BIN" -m unittest "$@" -v
fi
