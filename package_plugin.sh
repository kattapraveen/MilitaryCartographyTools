#!/usr/bin/env bash
#
# Build a QGIS Plugin Repository-ready zip.
#
# The repository requires the zip's root folder to be named exactly the
# plugin's importable package name (MilitaryCartographyTools), containing
# metadata.txt/__init__.py at its root - not nested another level deeper,
# and not missing that wrapper folder either. This script stages only the
# runtime files (no tests/, run_tests.sh, .git, or other dev-only cruft)
# into that structure and zips it.
#
# Usage:
#   ./package_plugin.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_NAME="MilitaryCartographyTools"

VERSION="$(grep -m1 '^version=' "$REPO_ROOT/metadata.txt" | cut -d= -f2)"
if [ -z "$VERSION" ]; then
    echo "Could not read version= from metadata.txt" >&2
    exit 1
fi

BUILD_DIR="$(mktemp -d)"
STAGE_DIR="$BUILD_DIR/$PLUGIN_NAME"
mkdir -p "$STAGE_DIR"

# Runtime files only.
INCLUDE=(
    __init__.py
    metadata.txt
    plugin.py
    core
    grid
    layout
    expressions
    terrain
    waypoints
    military_symbology
    icons
    docs
    LICENSE
    THIRD_PARTY_NOTICES.md
    README.md
)

for item in "${INCLUDE[@]}"; do
    cp -R "$REPO_ROOT/$item" "$STAGE_DIR/$item"
done

# Strip dev-only cruft that may have been copied along with a directory
# (e.g. a stray __pycache__/ left over from running the test suite).
find "$STAGE_DIR" -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find "$STAGE_DIR" -name "*.pyc" -delete
find "$STAGE_DIR" -name ".DS_Store" -delete

OUT_DIR="$REPO_ROOT/dist"
OUT_ZIP="$OUT_DIR/${PLUGIN_NAME}-${VERSION}.zip"
mkdir -p "$OUT_DIR"
rm -f "$OUT_ZIP"

(cd "$BUILD_DIR" && zip -rq "$OUT_ZIP" "$PLUGIN_NAME")

rm -rf "$BUILD_DIR"

echo "Built: $OUT_ZIP"
echo
echo "Contents:"
unzip -l "$OUT_ZIP"
