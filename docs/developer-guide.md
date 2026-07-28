# Military Cartography Tools — Developer Guide

Internal notes for anyone (including future-session Claude) working on this
plugin's code: how to run the test suite, and a collection of PyQGIS/QGIS 4.x
API traps found the hard way during development, so they aren't silently
rediscovered.

---

## Running the tests

`tests/` is a headless `unittest` suite. It needs **QGIS's own bundled
Python** — the `qgis` package isn't published to PyPI, so a normal
`pip install`-based Python environment (or `pytest` from one) can't import
it. Run it via the wrapper script instead:

```bash
./run_tests.sh
```

That script:

- Points `PYTHONHOME`/`PYTHONPATH`/`DYLD_FRAMEWORK_PATH`/`DYLD_LIBRARY_PATH`
  at a QGIS.app bundle's `Contents/Frameworks` (defaults to
  `/Applications/QGIS-final-4_0_3.app/Contents` — override with `QGIS_APP` if
  yours lives elsewhere).
- Sets `QT_QPA_PLATFORM=offscreen` so Qt widgets (labels, dialogs, print
  layouts, map canvases) can be created and exercised without an actual
  display — this is what makes it possible to test real `QgsLayoutItemLabel`,
  `QgsMapCanvas`, `QDialog`, etc. objects in CI or over SSH.
- Runs `unittest discover`, scoped to `tests/` specifically (see the comment
  in `run_tests.sh` for why it can't just discover from the repo root: doing
  so makes `unittest` try to import sibling packages like `grid/` and
  `layout/` as bare top-level modules while probing them for test files,
  which breaks their own `from ..core import ...`-style relative imports).

To run a single module, class, or test:

```bash
./run_tests.sh MilitaryCartographyTools.tests.test_layout
./run_tests.sh MilitaryCartographyTools.tests.test_layout.TestCreateAndUpdateLayout
./run_tests.sh MilitaryCartographyTools.tests.test_layout.TestCreateAndUpdateLayout.test_create_layout_has_a_map_item
```

### Test suite layout

- `tests/qgis_test_case.py` — shared scaffolding: `start_app()` (starts the
  one `QgsApplication` the whole process shares — only one can exist per
  process, so it's started once, at `tests/__init__.py` import time, rather
  than per test case), `QgisTestCase` (base class, clears the project between
  tests), and a canonical `FakeIface`/`FakeMessageBar`/`make_canvas()` so
  individual test files don't each hand-roll a partial fake `iface` (see the
  "Fake `iface` gotchas" section below for why that's worth avoiding).
- `tests/test_mgrs_conversion.py` — `core.MGRSConverter` round-trips at every
  precision level, component extraction, the UPS-validation bug-fix
  regression, grid convergence, magnetic declination.
- `tests/test_grid_generation.py` — the three grid generator classes produce
  features for a known extent; the shared `WGS84`/UTM-EPSG and
  font/text-format helpers behave correctly.
- `tests/test_layout.py` — `create_layout()`/`update_layout()`/
  `get_layout_values()`, the geometry computation, idempotency of every
  marginalia item (repeated `update_layout()` calls never duplicate an
  item — this is the regression test for the whole "Apply" panel workflow),
  the print-layout grid frame add/remove.
- `tests/test_plugin.py` — the full `initGui()`/`unload()` cycle (including
  simulating a Plugin Reloader-style reload-without-restart), toolbar action
  set/order, the coordinate probe tool and its log dialog, and the
  per-Layout-Designer toolbar/dock panel wiring.

### Writing a new test

Prefer testing at the lowest level that actually exercises the thing you
changed:

- Pure conversion/geometry logic (`core/`, `_compute_geometry()`) needs no
  fakes at all beyond `QgisTestCase`.
- Anything that builds real `QgsLayoutItem`s or grid layers needs a
  `QgsProject`/`QgsPrintLayout` — `QgisTestCase.setUp()` already clears the
  project between tests, so just build what you need directly.
- Anything that touches `iface` (map tools, plugin wiring, layout designer
  callbacks) should use the shared `FakeIface` from `qgis_test_case.py`
  rather than writing a new one — see below for why.

### Fake `iface` gotchas

Two real bugs turned up in this session's own *test* code (not the plugin)
while building ad hoc verification scripts, both now designed around in the
shared `FakeIface`:

1. **Missing methods surface late.** A fake `iface` that's missing a method
   the plugin actually calls (e.g. `removePluginMenu`) won't fail until
   `unload()` runs, which can be well after the interesting part of a test.
   The shared `FakeIface` covers every `iface.*` call this plugin makes, so
   this class of gap shouldn't recur — but if you add a new `iface.something()`
   call to the plugin, add it there too.
2. **A locally-scoped signal-owning `QObject` can crash the process, not
   raise an exception.** An earlier version of the ad hoc test script did
   this inside a fake `iface`'s `__init__`:

   ```python
   signal_host = SignalHost()  # local variable
   self.layoutDesignerOpened = signal_host.layoutDesignerOpened  # bound signal only
   ```

   Once `__init__` returned, `signal_host` (the only Python reference to that
   `QObject`) went out of scope. PyQt bound signals don't reliably keep their
   owning `QObject` alive on their own, so the object could be garbage
   collected — and using the signal afterward didn't raise a Python
   exception, it **segfaulted the interpreter** (exit code 139), at a
   call site that looked completely unrelated to the real cause. The fix:
   `FakeIface` subclasses `QObject` directly and declares the signals as
   class attributes, so there's no separate signal-owning object whose
   lifetime needs managing. If you ever see an unexplained segfault in a
   PyQGIS test involving signals, suspect this pattern first.

---

## PyQGIS / QGIS 4.x gotchas

- `QgsLabelLineSettings` / `QgsPalLayerSettings.layerType` plain attribute
  assignment silently no-ops; the real setter methods must be used instead.
- `QgsMapLayerStyleOverride` doesn't affect labeling in a layout map item's
  render, despite serializing correctly.
- `layer.clone()` on a memory-provider `QgsVectorLayer` doesn't reliably copy
  feature data — check `dataProvider().featureCount()` after cloning and
  re-add features manually if it came back empty.
- `QgsLayoutItemMap.refresh()` doesn't force a redraw — use
  `invalidateCache()`.
- `QgsLayoutItemMapGrid` mis-assigns a tick's annotation to the wrong
  (perpendicular) side when it lands exactly on the map frame's corner —
  worked around with a small `setOffsetX`/`setOffsetY` nudge (`GRID_OFFSET`
  in `grid/layout_grid_frame.py`).
- PAL's "Horizontal + line anchor" placement can silently center a label on
  its line, in a layout's static render, when the requested anchor position
  doesn't leave room for the label at its current font size — reducing label
  size resolved it in practice. Accepted as a known constraint for the
  on-map sub-grid tick labels in print layouts; the print-layout grid frame
  (`grid/layout_grid_frame.py`) sidesteps the whole issue for anyone who
  needs exact printed border labels, by using QGIS's own native map-grid
  frame annotations instead of PAL line-anchor labeling.
- `QgsLayoutItemMap.setExtent()` resizes the *item's own rect* to match the
  given extent's aspect ratio, not the other way around — seeding an extent
  that already matches the target rect's aspect avoids this (see
  `layout/new_layout.py`'s `create_layout()`/`update_layout()`).
- `QgsLayoutItemScaleBar.applyDefaultSettings()` doesn't actually compute a
  working segment size — it leaves `unitsPerSegment` at `0.0` (a degenerate
  bar) if units are changed afterward, and `segmentSizeMode` at `Fixed` with
  no value set. Its `FitWidth` auto-sizing mode (the same one QGIS's own
  "Add Scale Bar" GUI action uses) was also confirmed to overshoot a
  requested maximum bar width rather than respect it, whenever the
  next-smaller "nice" segment value would undershoot the minimum — ended up
  computing the segment size directly instead
  (`_pick_units_per_segment()` in `layout/scale_bar.py`).
- Explicitly calling `setMapUnitsPerScaleBarUnit()` on a
  `QgsLayoutItemScaleBar` whose units are already a named enum (e.g.
  `DistanceKilometers`) double-applies the unit conversion (values came out
  1000x too small) — leave it at its default when using a named unit.
- `@map_scale` (layout expression variable) evaluates to `NULL` in a plain,
  unlinked label's own expression context — only resolves for items actually
  linked to a map (a scale bar, a picture with `setLinkedMap()`, etc.).
  Worked around via this plugin's own `mct_map_scale(@layout_name)` function
  instead.
- `QgsLayoutItemMapGrid`'s built-in `DegreeMinute` geographic annotation
  format defaults to 3 decimal places on the minutes value, and renders the
  decimal point using the build/OS locale's own decimal separator (a comma
  in some environments) rather than always a period — reads as a completely
  different number (`38°30,000'E`). Fixed with `setAnnotationPrecision(0)`.
- `QgsLayoutItemLabel.setFont()` and `QgsLayoutItemScaleBar.setFont()` are
  `.. deprecated:: 3.40` (confirmed by introspecting the real docstrings in
  QGIS 4.0.3's own bundled Python) in favor of `setTextFormat(QgsTextFormat)`
  — migrated at all 7 call sites (`layout/heading.py`, `classification.py`,
  `metadata_block.py`, `center_coordinate.py`, `scale_bar.py`'s scale bar
  itself plus its two labels). `QgsLayoutItemScaleBar` has one unified
  `setTextFormat()`, no separate method for tick-number text.
  `core/text_format.py`'s `build_text_format()` gained an `underline` param
  for this (default `False`, backward-compatible with existing `grid/`
  callers). Zero `DeprecationWarning` output from the test suite as of this
  fix.
- `QgsMapTool`'s constructor requires a *real* `QgsMapCanvas` — a lightweight
  fake widget standing in for one raises `TypeError: QgsMapTool(): argument 1
  has unexpected type`. Use `tests/qgis_test_case.py`'s `make_canvas()` for
  anything that constructs a real map tool in a test.

---

## QGIS 3.44 compatibility (branch `qgis-3.44-compat`)

This plugin was built and tested against QGIS 4.0.3. QGIS 4.0 is primarily a
Qt5→Qt6 migration release, so the main portability risk when targeting an
older 3.x release is PyQt5-vs-PyQt6 binding differences, not the QGIS C++ API
itself. A static audit turned up nothing that needed changing in the code:

- Every Qt import goes through QGIS's own `qgis.PyQt` compatibility shim
  (`from qgis.PyQt.QtCore import ...`, etc.) — never a direct `PyQt5`/`PyQt6`
  import anywhere in the codebase.
- All Qt enums are written fully-scoped (`Qt.AlignmentFlag.AlignHCenter`),
  which PyQt6 requires and recent PyQt5 (well before 3.44) also supports —
  the old flat form (`Qt.AlignHCenter`, PyQt5-only/removed in PyQt6) isn't
  used anywhere.
- No Python 3.10+-only syntax (`match` statements, PEP 604 `X | Y` type
  hints) that might not run under an older bundled Python.
- The specific QGIS APIs used (`QgsLayoutItemPicture.NorthMode.TrueNorth`,
  `setTextFormat()` added 3.24/3.2, `QgsField(name, QVariant.String)`-style
  construction) have all existed since well back in the 3.x series.

**The only actual change on this branch**: `metadata.txt`'s
`qgisMinimumVersion` was lowered from `4.0.0` to `3.44.0`, since that was the
one hard gate actively blocking installation on a 3.44 profile — QGIS's
Plugin Manager enforces it regardless of whether the code would run.

**This is unverified.** No QGIS 3.44 install was available at the time this
branch was created — the above is static reasoning, not a passing test run.
Before trusting this branch, run `./run_tests.sh` (pointed at a 3.44
`QGIS_APP`, per the "Running the tests" section above) and fix whatever
actually breaks; don't assume the audit above is exhaustive.

---

## Vendored code

- `core/mgrs_engine.py` — MGRS conversion engine, originally by Alex Bruy
  (Boundless/Planet). One upstream bug fixed in the vendored copy: a
  UPS/polar-coordinate validation check used `letters[1] in [invalid]` (a
  one-element list containing a list, which can never be true) instead of
  `letters[1] in invalid`, silently disabling that validation. See
  `THIRD_PARTY_NOTICES.md` and the comment at the fix site.
- `core/geomag/` — World Magnetic Model calculation code, vendored from
  pyGeoMag (MIT license). WMM2025 coefficients are valid 2025.0–2030.0; the
  coefficient data (`core/geomag/wmm_2025.py`) will need updating to the next
  WMM release around 2029–2030.

See `THIRD_PARTY_NOTICES.md` for full attribution.
