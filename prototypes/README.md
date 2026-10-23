# Prototypes

Working code that is **not part of the plugin yet**. Nothing here is
imported by it, and nothing here ships: `package_plugin.sh` builds from
an explicit allowlist of runtime directories, and this folder is not on
it. Check that list before assuming anything added here is excluded.

| File | Status |
|---|---|
| `range_rings.py` | Geodesic ROA range circles as a standalone `QgsProcessingAlgorithm`. Syntax-checked only - never run in QGIS. See task 6 in `docs/roadmap.md` for the design, what remains to verify, and two corrections to the handoff it arrived with. |
