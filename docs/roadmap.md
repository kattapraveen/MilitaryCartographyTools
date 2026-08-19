# Military Cartography Tools — Roadmap

Source plan: `~/Desktop/rough plan.txt` (uploaded 2026-07-27). This
document tracks the same phases against actual implementation status,
plus additions worth doing that weren't in the original plan. Update
this file as phases complete or priorities shift — it's the durable
record that should survive context compaction between sessions.

**Reorganized 2026-07-31:** completed phases renumbered into sequential
order (1–7, no gaps); Terrain analysis (previously Phase 6) moved to
Phase 8 so it follows all completed work instead of sitting in the
middle of it; the two known cosmetic bugs from the Phase 8 (now Phase 7)
smoke test are marked complete below purely for restructuring purposes —
they have not actually been re-verified as fixed, and should be revisited
before being trusted as closed. Phases 9–10 (planned additions) follow in
sequence after Phase 8.

Status key: ✅ done · 🟡 partial · ⬜ not started

---

## Phase 1 — Finish the MGRS tools

- ✅ MGRS from lat/lon (`mct_mgrs`)
- ✅ Dynamic layout map centre (`mct_map_center_mgrs`, precision param, multi-layout, auto-refresh)
- ✅ Reverse conversion (`mct_mgrs_to_point`, `mct_mgrs_lat`, `mct_mgrs_lon`)
- ✅ MGRS component functions: `mct_mgrs_zone`, `mct_mgrs_square`, `mct_mgrs_easting`, `mct_mgrs_northing`

**Status: Complete.**

---

## Phase 2 — Layout tools

- ✅ `mct_map_scale`, `mct_map_rotation`, `mct_map_width`, `mct_map_height`
- ✅ `mct_map_center_lat`, `mct_map_center_lon`

**Status: Complete.**

---

## Phase 3 — Military grid tools

- ✅ Grid convergence (`mct_grid_convergence`, `mct_map_convergence`)
- ✅ Magnetic declination (`mct_magnetic_declination`, `mct_map_magnetic_declination`) — uses NOAA/NCEI's WMM2025 model via a vendored copy of pyGeoMag (MIT license, see `THIRD_PARTY_NOTICES.md`), self-contained with no network calls at runtime. Valid 2025.0-2030.0; the coefficient data (`core/geomag/wmm_2025.py`) will need updating to the next WMM release around 2029-2030.
- ✅ ~~GZD / 100km square as standalone expression functions~~ — decided not needed; Phase 1's `mct_mgrs_zone(lat, lon)` / `mct_mgrs_square(lat, lon)` already cover this.
- ✅ *(addition)* **Coordinate probe map tool** — `core/coordinate_probe_tool.py`'s `CoordinateProbeTool`, a toolbar-toggled `QgsMapTool` (crosshair icon). While active, left-clicking anywhere on the canvas logs that point's lat/lon and full-precision (1m) MGRS as a new row (newest first) in a persistent, non-modal `CoordinateProbeDialog`, and copies the MGRS string to the clipboard. The dialog survives being closed (hidden, not destroyed) and is reused/reshown on the next click rather than recreated, so its history isn't lost; double-clicking any row re-copies that row's MGRS, so an older reading isn't stranded once a later click overwrites the clipboard. Stays active across repeated clicks like QGIS's own Identify/Measure tools; the toolbar button's checked state stays in sync via `QgsMapCanvas.mapToolSet` even when a different tool (Pan, Identify, etc.) takes over.

- 🐞 **Correctness fix, 2026-08-17: the drawn GZD grid ignored the UTM zone exceptions.** Raised by the maintainer as the first major fix after the experimental tag came off, and rightly so - a plugin claiming stability is claiming exactly this kind of thing. **What was wrong, precisely**: `grid/utm_grid.py` built every grid zone designator cell as a flat rectangle (`west = -180 + (zone - 1) * 6`, `east = west + 6`), with band X's north edge at 84 as the file's only special case. The UTM grid is not a plain 6-degree lattice in two places, both part of the standard itself: in **band V (56-64N)** zone 31V narrows to 3 degrees (0-3E) and 32V widens to 9 (3-12E), so south-west Norway sits in one zone instead of being split; in **band X (72-84N)** zones **32X, 34X and 36X do not exist at all**, and 31X (0-9E), 33X (9-21E), 35X (21-33E) and 37X (33-42E) widen to absorb their ground, keeping Svalbard whole. **What was NOT wrong, and is worth recording so nobody re-fixes it**: `core/mgrs_engine.py` has always applied both exceptions when assigning a zone to a coordinate (`_latLonToUtm()`, the block at ~line 658), so MGRS strings, the coordinate probe and Bearing/Range were correct throughout. The defect was therefore a **disagreement inside the plugin** - ask it for a point's MGRS and you got 32V; draw the grid over the same point and it said 31V. That is worse than a uniform error, because each half looked self-consistent. **Fixed** by moving the geometry into `core/coordinate_utils.py` as `utm_zone_bounds(zone, band)` - returning `None` for the three cells that do not exist, so a caller sweeping zones skips them as a normal part of the sweep rather than having to know in advance - plus `utm_candidate_zones()`, which deliberately casts **one zone wider** on each side than plain arithmetic, because a widened cell reaches into its neighbour's nominal ground (a map showing only 4-5E is in 32V, though the arithmetic says 31). The extras are filtered back out where cells are built, by dropping any whose real bounds miss the extent. **The same arithmetic existed in a second place**: `layout/grid_position.py` carried its own `_required_zones()` and `_zone_lon_bounds()`, so the grid-position diagram printed on every layout had the defect independently; `_required_zones()` now takes the band (which is what decides whether an exception applies at all) and the mosaic leaves a non-existent cell's box unlabelled rather than printing "32X". `grid/mgrs_100k.py` and `grid/mgrs_sub_grid.py` needed **no change** - both read zone and band from the GZD layer's own features, so they inherited the correction. 1303 → 1317 tests on both QGIS 3.44.12 and 4.2.0, in a new `tests/test_utm_zone_exceptions.py`: the six exception cells against numbers written out longhand rather than computed, the three absent ones, a tiling check that the widened cells still cover 0-12E and 0-42E with no gap or overlap, the 4-5E regression, an ordinary-area control, and a test that the drawn grid and the MGRS engine now agree at six points where they used to differ. Verified with headless renders over Norway and Svalbard. **Released in 1.0.3**, live on plugins.qgis.org 2026-08-17.

**Status: Complete.**

---

## Phase 4 — Layout automation

Built as a single connected feature suite, "New Military Layout"
(a new toolbar action, `layout/new_layout.py`) — one dialog that
creates a fully-configured print layout in one step: page size
(Custom/A0/A3/A4/Arch E) + orientation + initial scale + optional
1-2 line heading + optional security classification, then wires
up every marginalia element below automatically. All reserved
margin space (classification bands, heading, bottom band) is
computed upfront so the map item's rect is correct from the very
first `setExtent()` call - no post-hoc resizing needed.

- ✅ Automatic map title — the heading fields (`layout/heading.py`): 1-2 user-entered lines, bold, underlined, 24pt, centred at the top. Space reserved dynamically based on 1 vs 2 lines.
- ✅ Automatic coordinate annotation block — `layout/metadata_block.py` (bottom-left: geodetic datum, projection/GZD, coordinate units, map scale, project file, page size, all live expressions except page size) plus `layout/center_coordinate.py` (independent "Center of Map: <MGRS>" label, bottom-right, split out from the metadata block per request).
- ✅ Automatic north arrow rotation — `layout/north_arrow.py`. Custom-designed SVG icon (`icons/north_arrow.svg` — shaft + arrowhead + "N", confirmed over several design iterations), linked to the map item via QGIS's own native `NorthMode.TrueNorth`, so rotation auto-tracks grid convergence with no manual math - this happened to satisfy the "wire to north arrow rotation" ask for free.
- ✅ ~~Automatic grid reference box~~ — decided not needed 2026-07-27 (see Phase 5's "military coordinate reference box", the same item).
- ✅ ~~Automatic sheet information~~ — decided not needed 2026-07-27.
- ✅ *(addition, not originally in the plan)* **Neatline** — `layout/neatline.py`, the map item's own native frame (`setFrameEnabled`), always exactly tracks the map's rect.
- ✅ *(addition)* **Security classification banners** — `layout/classification.py`, top and bottom, bold all-caps 12pt, selectable dropdown (None/UNCLASSIFIED/RESTRICTED/CONFIDENTIAL/SECRET/TOP SECRET), matching the reference layout's own classification markings.
- ✅ *(addition)* **Geographic (lat/lon) graticule overlay** — `layout/geographic_graticule.py`, a second `QgsLayoutItemMapGrid` (CRS EPSG:4326) drawn as light-brown lines with italic 8pt degree-minute labels, auto-spaced 15'/30'/1° from the map's actual extent - distinct from the plugin's own bold UTM/MGRS grid.
- ✅ *(addition)* **Scale bar** — see Phase 5, built as part of this same suite.
- ✅ *(addition)* **In-designer "Military Layout Settings" panel** — every marginalia `add_*` function was made idempotent (fixed `setId()` per item, a matching `remove_*`, re-add on every call), so `layout/new_layout.py`'s `update_layout()` can re-apply page size/orientation/scale/heading/classification to a layout that's already open instead of only at creation time. `plugin.py`'s `on_layout_designer_opened` now adds a `LayoutOptionsPanel` dock (shares its fields with `NewLayoutDialog` via a common `LayoutFieldsWidget`) alongside the existing grid-frame toolbar; it pre-fills from the layout's current state and applies changes in place, preserving the map's pan position across a resize. Headless-tested: resize + rescale + heading/classification changes, then toggling heading/classification off, left no duplicated or orphaned items.
- ✅ *(addition)* **Margin/spacing pass** — every margin and inter-element gap in the suite (map's own side/top/bottom clearance, classification banner margins/gaps, scale bar's internal line spacing) was re-tuned for maximum map area, several backed by real `QFontMetricsF` measurements rather than guesses (e.g. the map's left/right margin accounts for the print-layout grid frame's actual worst-case label width). Heading text now auto-uppercases regardless of the case typed in, matching the classification banners. Current constants deliberately favour map area over full grid-frame-collision safety at the page edges (top/bottom clearance is 2mm, tight enough that the grid frame's border labels can occasionally sit close to the heading/scale bar text when that frame is enabled) — an accepted, explicit trade-off, not an oversight.

**Status: Complete.** The remaining grid reference box item was decided not needed 2026-07-27.

A reference layout PDF ("EX EXPERIMENT" sketch) was reviewed against this suite earlier in the 2026-07-27 session; three more elements it showed were considered and explicitly not built: a unit badge/crest logo (out of scope entirely), corner coordinate readouts at the four page corners, and 100km-square letter labels at grid corners (decided not needed) — plus an annex reference block (e.g. "ANNEX P TO INDEX 3 / REFERS TO PARA 2", top-right), deliberately deferred rather than ruled out, since it's specific to this one reference document and building it now would over-fit the plugin to one user's exact use case rather than staying broadly usable.

---

## Phase 5 — Cartographic production tools

- ✅ Grid tick generation / border annotation — done via the print-layout grid frame (`grid/layout_grid_frame.py`)
- ✅ ~~Military coordinate reference box~~ — decided not needed 2026-07-27 (same item as Phase 4's "grid reference box").
- ✅ ~~Standard legend layouts~~ — decided not needed 2026-07-27.
- ✅ Scale bars tailored for military mapping — `layout/scale_bar.py`, part of the "New Military Layout" suite (see Phase 4): ticks-up-only style, auto "nice" segment sizing (bypasses QGIS's own FitWidth mode - see the Phase 7 gotcha list), tight inter-line gaps, font sizes matched to the rest of the marginalia text.
- ✅ ~~Grid reference diagrams~~ — decided not needed 2026-07-27.
- ✅ ~~Coordinate conversion tables~~ — decided not needed 2026-07-27.
- ✅ Map marginalia / neatline templates — `layout/neatline.py` (see Phase 4) plus the metadata block/classification banners/heading, all part of the same suite.

**Status: Complete.**

---

## Phase 6 — Data preparation

- ✅ UTM Grid Zone Designator generation (`grid/utm_grid.py`)
- ✅ MGRS 100km square grid (`grid/mgrs_100k.py`)
- ✅ 10km / 5km / 1km sub-grids with labels (`grid/mgrs_sub_grid.py`)
- ✅ Print-layout grid frame with border ticks + coordinate annotations, auto spacing, 100km-prefix disambiguation (`grid/layout_grid_frame.py`)
- ✅ ~~100m grid tier~~ — decided not needed; 1km is fine-grained enough for the intended printed scales.
- ✅ ~~Grid Settings dialog~~ — decided not needed; line colors/widths, label sizes, and frame annotation sizes remain hardcoded module constants (`WIDTH_MAJOR`, `LABEL_SIZE`, `ANNOTATION_SIZE`, `LINE_COLOR`, etc. in `grid/`), but exposing them through the plugin's own UI isn't required — the user can already restyle these layers directly via QGIS's own layer styling panel if needed.

**Status: Complete.** This phase ended up done well out of the plan's suggested order, since it's where most of the recent session's work landed. The on-map PAL label centering limitation for very fine grids in print layouts is a known, accepted constraint (see the gotcha list under Phase 7) rather than an open bug.

---

## Phase 7 — Distribution

- ✅ **Clean the codebase** — done 2026-07-28, backed by a full-codebase audit (all 31 files read and cross-referenced) plus a headless regression pass (imports, MGRS round-trip, grid generation, layout create/update, plugin `initGui()`/`unload()` cycle) and `pyflakes` (zero findings) after every change:
  - Dead code deleted: `core/settings.py` (whole file, superseded by `grid/grid_settings.py`), `layout/center_mgrs.py`'s `CenterMGRS` class (superseded by the expression functions), unused functions in `core/coordinate_utils.py` (`wgs84_to_project`, `project_point_to_utm`), `core/mgrs_converter.py`'s `latitude_band_letter()`, `grid/grid_manager.py`'s unused `self.settings`/`project()`, `grid/utm_grid.py`'s unused `latitude_band()`, and `grid/mgrs_sub_grid.py`'s unused `_point_anchor_settings()` (an abandoned alternate fix attempt, superseded by the accepted-constraint decision already in this phase's gotcha list below).
  - Real bug fixed in the vendored MGRS engine (`core/mgrs_engine.py`): a UPS/polar-coordinate validation check used `letters[1] in [invalid]` (list-containing-a-list, never true) instead of `letters[1] in invalid`, silently disabling that validation - confirmed via regression test that invalid input is now actually rejected. Documented as a deliberate deviation in `THIRD_PARTY_NOTICES.md`.
  - Real leak fixed: `core/layout_refresh.py`'s `connect_layout_refresh()` connections were never disconnected on plugin unload, so a Plugin Reloader cycle stacked duplicate connections on the same map items every time - added `disconnect_layout_refresh()`, wired into `plugin.py`'s `unload()`. Also extended to listen for `QgsLayoutManager.layoutAdded`, so a layout created after plugin load (e.g. via New Military Layout) gets the same refresh wiring, not just layouts that already existed at load time.
  - Duplicated logic consolidated: `WGS84`/UTM-EPSG-from-zone construction (was independently rebuilt in 7+ places) now goes through `core/coordinate_utils.py`'s `WGS84` constant and new `get_utm_crs_from_zone_band()` helper; `QFont`/`QgsTextFormat` construction (9+ ad hoc call sites across `layout/` and `grid/`) now goes through a new `core/text_format.py` (`build_font()`/`build_text_format()`); the byte-identical fill-symbol styling shared by `UTMGridGenerator`/`MGRS100KGenerator` now goes through `grid/_style_utils.py`'s `apply_simple_fill_style()` (a full 3-way base class for all three grid generator classes was considered and deliberately not built - `MGRSSubGridGenerator`'s rule-based rendering is genuinely different, not a variant of the simple-fill pattern, so forcing it under one base class would have added indirection without removing real duplication).
  - Largest file split for readability: `layout/new_layout.py` (was 1047 lines, mixing Qt UI with layout-building logic) is now the layout-building/geometry module only (`create_layout`/`update_layout`/`_compute_geometry`/`_apply_marginalia`/etc.); the Qt dialog/panel classes (`LayoutFieldsWidget`, `NewLayoutDialog`, `LayoutOptionsPanel`) moved to a new `layout/layout_dialogs.py`. `plugin.py`'s `initGui()` (was ~313 lines) and `on_layout_designer_opened()` (was ~139 lines) were broken into smaller private helper methods within the same class (`_build_action()`, `_setup_*()`, `_build_grid_frame_toolbar()`, `_build_layout_settings_panel()`) rather than split into new files, since they're tightly coupled to plugin instance state.
- ✅ **Unit tests for conversion routines** — done 2026-07-28. Formalized the headless PyQGIS test harness used ad hoc all session into a real, checked-in `tests/` suite (45 tests, `unittest`-based, zero extra dependencies needed in QGIS's bundled Python): `tests/test_mgrs_conversion.py`, `tests/test_grid_generation.py`, `tests/test_layout.py` (including a dedicated idempotency regression test — repeated `update_layout()` calls never duplicate a marginalia item), `tests/test_plugin.py` (full `initGui()`/`unload()` cycle, toolbar wiring, coordinate probe tool, layout designer wiring). Shared scaffolding in `tests/qgis_test_case.py` (a canonical `FakeIface`/`FakeMessageBar`/`make_canvas()`, avoiding two real bugs found in this session's own ad hoc test code — see `docs/developer-guide.md`). Run via `./run_tests.sh` at the repo root (needs QGIS's own bundled Python; see the developer guide for why and how).
- ✅ **User documentation** — done 2026-07-28: `docs/user-guide.md` (installation, toolbar tour, every tool's workflow, and three expression-function reference tables verified against the actual source signatures in `expressions/mgrs_functions.py`); `README.md` rewritten from an acknowledgements-only stub into a proper project front page (features, installation, documentation links, license section); `LICENSE` added (GPL v2 text, matching `metadata.txt`'s `license=GPL-2.0+` and the About dialog's existing reference to it — fetched verbatim from gnu.org's canonical text rather than generated inline, after an inline attempt at the full ~340-line license text was blocked by an apparent content-filtering false-positive on large formal/legal boilerplate).
- ✅ **Developer documentation of PyQGIS gotchas** — done 2026-07-28, written up in `docs/developer-guide.md` (test suite usage/structure, every gotcha below plus two new ones found while building the test suite itself: `QgsMapTool` requiring a real `QgsMapCanvas`, and `QgsLayoutItemLabel`/`QgsLayoutItemScaleBar.setFont()` being deprecated in QGIS 4.0 — the latter migrated to `setTextFormat()` at all 7 call sites, done separately, zero `DeprecationWarning` output remaining):
  - `QgsLabelLineSettings` / `QgsPalLayerSettings.layerType` plain attribute assignment silently no-ops; real setters must be used.
  - `QgsMapLayerStyleOverride` doesn't affect labeling in a layout map item's render, despite serializing correctly.
  - `layer.clone()` on a memory-provider `QgsVectorLayer` doesn't reliably copy feature data.
  - `QgsLayoutItemMap.refresh()` doesn't force a redraw — use `invalidateCache()`.
  - `QgsLayoutItemMapGrid` mis-assigns a tick's annotation to the wrong (perpendicular) side when it lands exactly on the map frame's corner — worked around with a small `setOffsetX`/`setOffsetY` nudge (`GRID_OFFSET` in `layout_grid_frame.py`).
  - PAL's "Horizontal + line anchor" placement can silently center a label on its line, in a layout's static render, when the requested anchor position doesn't leave room for the label at its current font size — reducing label size resolved it in practice.
  - `QgsLayoutItemMap.setExtent()` resizes the *item's own rect* to match the given extent's aspect ratio, not the other way around — seeding an extent that already matches the target rect's aspect avoids this (see `new_layout.py`'s `create_layout()`).
  - `QgsLayoutItemScaleBar.applyDefaultSettings()` doesn't actually compute a working segment size — it leaves `unitsPerSegment` at 0.0 (a degenerate bar) if units are changed afterward, and `segmentSizeMode` at `Fixed` with no value set. Its `FitWidth` auto-sizing mode (the same one QGIS's own "Add Scale Bar" GUI action uses) was also confirmed to overshoot a requested maximum bar width rather than respect it, whenever the next-smaller "nice" segment value would undershoot the minimum — ended up computing the segment size directly instead (`_pick_units_per_segment()` in `layout/scale_bar.py`).
  - Explicitly calling `setMapUnitsPerScaleBarUnit()` on a `QgsLayoutItemScaleBar` whose units are already a named enum (e.g. `DistanceKilometers`) double-applies the unit conversion (values came out 1000x too small) — leave it at its default when using a named unit.
  - `@map_scale` (layout expression variable) evaluates to NULL in a plain, unlinked label's own expression context — only resolves for items actually linked to a map (a scale bar, a picture with `setLinkedMap()`, etc.). Worked around via this plugin's own `mct_map_scale(@layout_name)` function instead.
  - `QgsLayoutItemMapGrid`'s built-in `DegreeMinute` geographic annotation format defaults to 3 decimal places on the minutes value, and renders the decimal point using the build/OS locale's own decimal separator (a comma in this environment) rather than always a period — read as a completely different number ("38°30,000'E"). Fixed with `setAnnotationPrecision(0)`.
- ✅ Package for the official QGIS Plugin Repository — **published 2026-07-28**, moderator approved. Live at plugins.qgis.org, plugin ID 5843, listed as experimental (visible to users with "show experimental plugins" enabled in their Plugin Manager settings). `package_plugin.sh` builds `dist/MilitaryCartographyTools-<version>.zip` in the structure the repository requires (verified by extracting it and running the full test suite against the packaged code directly, not the dev checkout — 45/45 pass); `changelog=` added to `metadata.txt`; manual smoke test passed in a real QGIS 3.44 install (toolbar, all grids, coordinate probe, New Military Layout + Layout Settings panel + grid frame — no crashes, no Log Messages panel errors); two cosmetic bugs found, see below. First upload attempt (0.1.0) was automatically reviewed and flagged 40 findings: 1 Flake8 (`E731`, a lambda assignment in `core/layout_refresh.py`) and 39 "Qt6 compatibility" enum-scoping warnings (QGIS enums accessed via their old flat form rather than fully scoped through the enum class, e.g. `QgsLayoutItemMapGrid.GridStyle.FrameAnnotationsOnly` instead of `QgsLayoutItemMapGrid.FrameAnnotationsOnly`) — all fixed and re-verified (45/45 on both 3.44.12 and 4.0.3). The repository rejects re-uploading an already-used version string, so the fixed build went out as **0.1.1** — that's the version actually submitted, not 0.1.0. Uploaded, security scan cleared, **plugin ID 5843** assigned. Version stays `experimental=True` until there's been some real usage/feedback (a deliberate decision, unrelated to the version-number bump forced by re-submission). **0.1.2 uploaded 2026-08-03** with both bug fixes below (100km grid label, scale bar oversizing) — security scans passed. **0.2.0 built 2026-08-05**, bumping the version for Phase 8's whole terrain analysis toolset (Tanaka Contours, Hypsometric Tint, Line of Sight, Combined Hillshade, Viewshed) and rewording `metadata.txt`'s `description=`/`about=` to foreground the plugin's fully-offline, no-external-services design. Caught and fixed a real packaging bug in the process: `package_plugin.sh`'s `INCLUDE` array had never been updated when `terrain/` was added, so every zip built since Phase 8 started (including what would have been the 0.2.0 upload) silently shipped without the `terrain` package at all — `plugin.py` imports from it unconditionally, so the plugin would have failed to load entirely. Fixed by adding `terrain` to `INCLUDE`; verified by extracting the rebuilt `dist/MilitaryCartographyTools-0.2.0.zip` and confirming `terrain/` is present with all 16 files, plus 203/203 tests passing on both QGIS 3.44.12 and 4.2.0 before the rebuild. **Uploaded and pushed 2026-08-05** — plugin ID 5843, still `experimental=True`. **0.2.0's automated review flagged 2 real issues**, fixed as **0.2.1** the same day (the repository rejects re-uploading 0.2.0 itself, same constraint as the 0.1.0→0.1.1 re-submission above): (1) 3 Qt6 enum-scoping errors — `QgsVertexMarker.ICON_CROSS`/`ICON_X` needed to be `QgsVertexMarker.IconType.ICON_CROSS`/`ICON_X`, in `terrain/line_of_sight_tool.py` (both markers) and `terrain/viewshed_tool.py` (observer marker); (2) a **blocking security finding** — `tempfile.mktemp()` (insecure/deprecated: creates a filename with no atomic reservation, a TOCTOU race) used at 9 call sites across `terrain/_dem_utils.py`, `hillshade_combination.py`, `tanaka_contours.py`, and `viewshed.py` to generate `processing.run()` OUTPUT paths. Fixed by switching every one to `QgsProcessing.TEMPORARY_OUTPUT`, the idiomatic QGIS Processing sentinel that lets QGIS itself generate the temp file safely — the correct fix, not just a safer Python temp-file call, since it removes the plugin from temp-path generation entirely. One follow-up bug surfaced by the switch: `native:` algorithms (`native:splitlinesbylength` in `tanaka_contours.py`, `native:extractbyattribute` in `viewshed.py`) resolve `TEMPORARY_OUTPUT` to an already-loaded `QgsVectorLayer` object directly in `result["OUTPUT"]`, unlike GDAL-wrapped algorithms which still return a file path to re-wrap — confirmed live via a `TypeError` when re-wrapping the object in another `QgsVectorLayer()` call; fixed by returning `result["OUTPUT"]` directly for those two call sites. Re-verified 203/203 on both QGIS 3.44.12 and 4.2.0, plus an extracted-zip sweep confirming no remaining `mktemp`/unscoped-enum references, before rebuilding `dist/MilitaryCartographyTools-0.2.1.zip`. **Uploaded 2026-08-05, security checks cleared** — Phase 8's terrain analysis toolset is now live on the official Plugin Repository. **0.3.0 built 2026-08-06**, bundling everything shipped since 0.2.1: Phase 9 in full (Bearing/Range tool, GPX/KML waypoint import/export, Map Sheet Series with its automatic grid-position diagram now standard on every layout), MGRS shown alongside lat/lon in Line of Sight/Viewshed, and the Hypsometric Tint/Tanaka Contours colour fixes (discrete ramp toggle, `LAND_RAMP` hue warm-up, Illuminated Overlay's Soft Light blend). Unlike the 0.2.0 packaging bug, no new top-level package needed adding to `package_plugin.sh`'s `INCLUDE` array this time — every Phase 9 feature lives inside packages already listed (`core/`, `waypoints/`, `layout/`). `metadata.txt`'s `changelog=`/`about=`/`tags=` updated; verified by extracting `dist/MilitaryCartographyTools-0.3.0.zip` and running the full suite against the packaged code directly (not the dev checkout) — 291/291 on both QGIS 3.44.12 and 4.2.0. **Deliberately stays `experimental=True`** — considered flipping it given 83 downloads with no reported issues on 0.2.1, but that signal reflects the *older* core (MGRS/grid/terrain), not this release's own newest, least-battle-tested batch (Map Sheet Series, Bearing/Range, GPX/KML) — decided to wait for this batch to collect its own field exposure before reconsidering the flag on a later release. Built, packaged and **uploaded by the maintainer** — 0.3.0 became the live release (the submission itself needs the maintainer's own OSGeo login, outside what any session can do). *Note added 2026-08-17: this line read "Built and packaged, not yet uploaded" for eleven days after the upload actually happened, and was read back to the maintainer as fact — the same stale-record failure the 2026-08-16 housekeeping pass found seven of. A packaging entry describes a moment; it goes stale the instant the maintainer acts.* **1.0.0 built 2026-08-17 — the first stable release, and the end of `experimental=True`.** Bundles 154 commits since 0.3.0: the whole of Phase 10's MIL-STD-2525D/APP-6 tactical graphics (every control-measure appendix plus the entity-symbol layers), and Phase 8's three closed deferrals (Viewshed's colour picker and outline-only toggle, Tanaka Contours' generation-time caution). **Version number and the experimental flag were decided together, deliberately** - `1.0.0` alongside `experimental=True` says two contradictory things on the same repository page, and the flag was doing real harm: it hides the plugin from anyone who has not ticked "show experimental plugins" in Plugin Manager, so the 200+ existing users found it *despite* that setting rather than because of it. The flag's actual meaning in the repository is "may be unstable or change fundamentally", which no longer describes this plugin. The counter-argument was stated and accepted rather than waved away: Appendix H's symbology has had no field exposure at all, and download numbers reflect the older MGRS/grid/terrain core - the maintainer's own symbol-by-symbol smoke testing plus 1303 tests on two QGIS versions was judged sufficient against that. `metadata.txt`'s `description=`/`about=`/`tags=` now lead with the tactical graphics, which had been absent from all three. Verified the way the 0.2.0 packaging bug taught us to: extracted `dist/MilitaryCartographyTools-1.0.0.zip` and ran the full suite against the **packaged** code, not the dev checkout - 1303/1303 on both QGIS 3.44.12 and 4.2.0 - plus a sweep of the packaged tree for the three findings that have been flagged on past uploads (`tempfile.mktemp()`, unscoped Qt6 enums, `E731` lambda assignment), all clean. No new top-level package needed adding to `package_plugin.sh`'s `INCLUDE` array this time: `military_symbology/` was already listed, and milsymbol.js rides inside it at `military_symbology/vendor/` rather than from the repo-root `milsymbol-3.0.4/` source copy (confirmed present in the zip). **Uploaded by the maintainer 2026-08-17; its automated review returned findings, fixed the same day as 1.0.1** (the repository rejects re-uploading a version string it has already seen - the same constraint that forced 0.1.0→0.1.1 and 0.2.0→0.2.1). Three scanners, one real finding between them. **The real one, from the Qt6 compatibility check**: `military_symbology/symbol_engine.py` imported `QJSEngine` with a `try: from PyQt5.QtQml ... except ImportError: from PyQt6.QtQml ...`, and the check's standing advice is to import from `qgis.PyQt` instead. **That advice cannot be followed literally here, and the first attempt to do so broke the plugin outright** - `qgis.PyQt` does not re-export `QtQml` on either QGIS 3.44.12 or 4.2.0 (verified by listing the shim's own submodules on both: `QtQuick` is present, `QtQml` is not), so `from qgis.PyQt.QtQml import QJSEngine` raises `ModuleNotFoundError` at plugin import time. Caught immediately by the test suite, which is exactly why the standing rule is to run both suites rather than trust a one-line "obvious" fix. What was genuinely wrong was the *guessing*: trying PyQt5 first and falling back on `ImportError` hardcodes a binding preference unrelated to what QGIS is actually running, and only works because PyQt5 happens to be absent under Qt6. Replaced with asking `qgis.PyQt` itself which Qt it resolved to (`QT_VERSION_STR`) and loading that binding's `QtQml` by name via `importlib` - same answer on a correct install, but derived rather than assumed. A side effect worth naming honestly: this also leaves no literal `from PyQt5`/`from PyQt6` statement for a static check to flag (confirmed by a sweep of the packaged tree), so the finding will not recur - but the dynamic import is the correct expression of the intent, not a dodge invented to silence the scanner. **The other four findings are false positives, now annotated in place rather than left to re-flag on every future upload**: Bandit's B311 against `random.Random()` in the mine-scatter placement (seeded deliberately from the shape's own centroid and count so the same polygon draws identically on every redraw and every machine - a cryptographic RNG would defeat that outright), and B105/detect-secrets "possible hardcoded password" against four MIL-STD-2525D entity names containing the word *Secret* - the US Secret Service, entity codes 112109 and 131509. Each carries a `# nosec` / `# pragma: allowlist secret` marker and a comment saying which it is and why. 1303/1303 on both QGIS 3.44.12 and 4.2.0, re-verified against the extracted `dist/MilitaryCartographyTools-1.0.1.zip` rather than the dev checkout.
  - **1.0.2, 2026-08-17: one of 1.0.1's own suppressions did not work, and the B311 finding came straight back on upload.** The four B105 markers landed on the flagged lines and cleared (four findings plus both detect-secrets findings gone); the B311 marker was written as the first line of the *comment block above* `random.Random(...)` instead of on the call line itself, and **Bandit reads `# nosec` only from the line it reports**. Moved onto the call line (`generator = random.Random(  # nosec B311 # noqa: S311`). The real lesson is not the one-line placement but the verification gap: 1.0.1 shipped a scanner fix that had never been run through a scanner, so an upload round-trip became the test. Bandit is pip-installable and takes seconds - **1.0.2 was checked by running Bandit 1.9.4 locally over both the source tree and the extracted zip before packaging** ("No issues identified", 5 suppressions registering), rather than by uploading and waiting. Worth knowing for anyone reading these markers later: a `# nosec` inside a multi-line expression applies to the whole statement node, so the four on the entity dictionaries suppress B105 for those entire dicts rather than for one key each - acceptable here (they hold nothing but MIL-STD-2525D entity names and codes) but not a property to rely on elsewhere. 1303/1303 on both QGIS versions, verified against the extracted `dist/MilitaryCartographyTools-1.0.2.zip`. **Built and packaged; the upload is the maintainer's to make.**
  - **1.0.3 built 2026-08-17.** The first release carrying real correctness work rather than release mechanics. Contents: the drawn GZD grid brought into line with the UTM zone exceptions (see Phase 3's own entry - the plugin's grid layer and its MGRS engine had disagreed with each other over Norway and Svalbard), the three GZD labelling fixes that followed from smoke-testing it (the world-scale pile-up, the label vanishing when panned inside a large zone, and the one-character overhang into the neighbouring zone), Phase 10 closed, the `mgrs_engine.py` dead block deleted, and the GMRT bathymetry pointer written into the user guide. Verified to the checklist the earlier uploads taught: **Bandit 1.9.4 run locally over both the source tree and the extracted zip before packaging** ("No issues identified" both times - not left for the upload to discover, per 1.0.1's lesson), a sweep of the packaged tree for the three findings past reviews have flagged (all clean), and the full suite run against the **packaged** code rather than the dev checkout - 1326/1326 on both QGIS 3.44.12 and 4.2.0. 145 files, `military_symbology/vendor/milsymbol.js` confirmed present. **Built and packaged; the upload is the maintainer's to make.**
  - **1.1.0 built 2026-08-18 - a minor bump, not a patch, and decided that way deliberately.** Everything shipped since 1.0.3 is new, backward-compatible functionality, not bug fixes: the whole of Phase 12 (MIL-STD-2525E/APP-6E support - 978 entities, 226 sector modifiers, the edition-switch toolbar menu, E-8's common-modifier wiring), Land Unit's own sector 1/2 modifiers plus the vendored milsymbol.js icon-selection fix, the Boundary echelon-marker fix, and U-1 (the print layout's own Insert Symbol button) - see each one's own dated entry above. Semver's own MINOR/PATCH distinction is exactly "adds functionality, backward compatible" vs. "fixes only, nothing new" - this release is unambiguously the former, and old projects prove the "backward compatible" half directly (S-3, above: a project saved under 1.0.3 opens and renders correctly against this checkout unchanged). `metadata.txt`'s `version=`/`changelog=` headers moved from `1.0.3`/`1.0.4` (the informal in-progress label used throughout this session's smoke-testing) straight to `1.1.0` - 1.0.4 itself was never released. One packaging-adjacent fix caught by this pass: `tests/test_sidc_2525e.py`'s `TestBlankGenericEntitiesAreRemoved` class imports `tools/extract_2525e_vocabulary.py` (dev-only, not shipped) to cross-check the generated data against the generator's own source list - a real regression guard for the dev checkout, but it errored outright the moment the **packaged** tree's own test run reached it, since `tools/` genuinely is not there. Guarded with `unittest.skipUnless` rather than weakened or deleted, so the dev checkout keeps the real check and the packaged-tree run reports a clean skip instead of a false error - 1414 tests, 3 skipped only when `tools/` is absent. Also caught, in code written this same session: `plugin.py`'s new `_insert_symbol()` used `QgsLayoutItemPicture.FormatSVG`, the enum's old flat-access form - exactly the Qt6-compatibility class of finding four earlier uploads have each had to fix in turn (0.1.0, 0.2.0, 0.2.1) - found and corrected to `QgsLayoutItemPicture.Format.FormatSVG` before it ever reached an upload, by sweeping every `Qgs*`/`Q*` two-level enum access in every file touched this session rather than waiting for the checker to flag it. Verified to the full checklist: **Bandit 1.9.4 and detect-secrets both run locally over the source tree AND the extracted zip** (clean on both, both tools), a sweep of the packaged tree for `mktemp`/hardcoded `PyQt5`/`PyQt6` imports/`E731` lambda-assignments (all clean), and the full suite run against the **packaged** code rather than the dev checkout - 1411 passed, 3 skipped (the `tools/`-dependent ones, by design), on both QGIS 4.2.1 and 3.44.12. 150 files, `military_symbology/vendor/milsymbol.js` and every new U-1/Phase 12 file (`layout_symbol_dialog.py`, `sidc_2525e.py`, `insert_symbol.svg`) confirmed present. **Built and packaged; the upload is the maintainer's to make.**

**Known issues found during the manual smoke test (2026-07-28):**
- ✅ **MGRS 100km grid labels land in the wrong square at some zoom levels** (`grid/grid_labels.py`) — fixed 2026-08-02, then found to have a real remaining bug and fully fixed 2026-08-03 (see below); previously only administratively checked off 2026-07-31.
  - **2026-08-02 fix**: root cause was `GridLabelManager._centered_settings()` applying a fixed `-20mm` screen-space `yOffset` to every 100km square's centred label at *every* zoom level. That offset was sized for when a square fills much of the screen; once zoomed out enough that a square's own on-screen footprint shrinks below ~20mm, the fixed offset overshot the square entirely and landed the label inside the square immediately to the south. A second, related symptom (labels "so big they are all over" when zoomed out) had a separate cause: the centred rule had no scale-based cutoff at all — with `displayAll=True` forcing every label to render regardless of collisions, zooming out far enough to see many squares piled a full-size label onto each one. Fix at the time: split into a "near" rule (offset, zoomed in) and a "far" rule (no offset, smaller font, zoomed out), both active up to a new `center_max_scale`.
  - **2026-08-03: found still broken, with real user screenshots to diagnose against.** Two further real bugs, both confirmed live (not just reasoned about): (1) the "near" centred rule and the four corner-label rules were BOTH active simultaneously whenever zoomed in — by design, per the 2026-08-02 fix's own reasoning ("having both active at once... just means they coexist rather than fighting") — but this read as two conflicting labels for the same square, not a helpful fallback, exactly matching the user's report of corner and center labels appearing together and "not matching". (2) `CORNERS`' `x_sign`/`y_sign` nudge values were computed assuming PAL's `yOffset` is positive-up (map/mathematical convention) — confirmed live, by rendering a single offset label and inspecting the pixels, that it's actually **positive-down** (screen/render convention). Every corner label was therefore nudged OUTWARD into the neighbouring square instead of INWARD into its own — confirmed live by rendering a small 2x2 test grid of squares and watching each one's corner labels land on the wrong side of a shared boundary from its neighbour, matching the user's exact report ("when you pan the map, the bottom square's label comes into the upper one").
  - **Fix**: flipped all four `y_sign` values in `CORNERS` (x_sign was already correct). Removed the near-zoom centred rule entirely so corner and centred labels are strictly mutually exclusive by scale — corner labels only below `corner_scale_threshold`, the (now single) centred label only at or above it. Traded-away edge case: zoomed in far enough that literally none of a square's four corners are on screen (panned to somewhere deep in its interior) now shows no label for that square until you pan enough to see a corner or zoom out past the threshold — considered an acceptable, honestly-flagged trade-off rather than solved with more complex corner-visibility-aware logic. Removed now-dead code this left behind (`CENTER_LABEL_Y_OFFSET_MM`, `_centered_settings()`'s `apply_offset` param, `apply_square_label()`'s unused `center_size` param).
  - Diagnosis method worth noting: an earlier headless verification pass had rendered *nothing* (blank output, no error) - turned out `@map_scale` isn't populated in a bare `QgsMapSettings`/`QgsMapRendererParallelJob` context unless an expression context with `QgsExpressionContextUtils.mapSettingsScope()` is explicitly attached, unlike a real running QGIS canvas which does this automatically. Once fixed, rendering a small synthetic 2x2 grid of labelled squares and inspecting the actual pixels (not just reasoning about the rule tree) is what found both bugs above.
  - Covered by `tests/test_grid_labels.py`: rule-tree structure tests updated for the single-centred-rule design, plus a new `TestCornerOffsetSigns` regression test asserting every corner's nudge direction points inward.
  - **2026-08-03, follow-up cosmetic pass**: after confirming the fix above worked live, two cosmetic mismatches were reported and fixed — the corner labels (24pt) and centred label (14pt) read as different sizes across the `corner_scale_threshold` cutover, now unified under one `GridLabelManager.SQUARE_LABEL_SIZE = 14` constant used by both; and the UTM/GZD grid label (`grid/grid_manager.py`'s `generate_utm()`) was reduced 25% (30pt → 22pt) for better balance against the smaller 100km-square labels. Separately triaged: the user asked whether corner and centred labels can *both* be missing at once at some zoom levels. Confirmed this is the same trade-off already called out above, not a new bug — zoomed in past `corner_scale_threshold` with none of a square's four corners inside the current view (e.g. panned deep into one square's interior), the corner rule's geometry-generated anchor points all fall outside the visible extent, so PAL has nothing to place, and no other rule is active at that scale to fall back to. A real fix needs per-square, per-view "is any corner currently visible" awareness inside a declarative PAL rule tree — plausible (e.g. an `intersects(corner_point, @map_extent)`-gated fallback rule) but meaningfully more complex than the rest of this labeling logic for what's a cosmetic edge case at deep zoom. **Filed as a known minor limitation, not a bug** — not planned unless it turns out to matter more in real use.
  - **2026-08-04, real z-order bug found and fixed**: the user separately reported the 100km label is sometimes rendered but sits *behind* the UTM Grid layer's own polygon fill/GZD label. Root cause, confirmed live by rendering two overlapping memory layers in a known stacking order and inspecting the resulting pixel colour: QGIS renders the first-listed layer in the layer tree on top, and `group.addLayer()` always appends to the end of the group. Since `GridManager.generate_mgrs100k()` always runs after `generate_utm()` (the 100km grid needs the UTM layer to already exist), a plain append put the MGRS 100km Grid layer *below* the UTM Grid layer every time, so the coarser UTM grid painted over the finer 100km label wherever the two visually coincided. An offset-based workaround (as first suggested) wouldn't have fixed this reliably, since the occluding layer would still be on top - fixed the actual stacking order instead: `grid/grid_manager.py`'s `add_layer_to_group()` now takes an optional insertion index, and `generate_mgrs100k()` always inserts its layer right after the "MGRS Sub Grid" subgroup (i.e. above the UTM Grid layer), regardless of which grid was most recently (re)generated. New `tests/test_grid_manager.py` covers the resulting stacking order, including the case where the UTM grid is regenerated *after* the 100km layer already exists (a naive "insert new layers at the top" fix would have broken that case by bumping UTM back above 100km). 76/76 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-05, belt-and-suspenders label fix**: user-tested and confirmed fix for the two labels still occasionally competing for the same screen space even with the z-order fix above. `GridLabelManager.apply_label()` (the UTM/GZD label) now nudges its label up-left from its polygon's centroid (`GZD_LABEL_OFFSET_MM = 12`) instead of sitting exactly on it - a 100km square's own centred label is also anchored at its centroid at matching zoom levels, so this reduces how often the two even land on the same spot in the first place. `apply_square_label()`'s corner/centred rules also got a priority bump (`SQUARE_LABEL_PRIORITY = 5`, up from 1) so the 100km label wins any collision that does still happen, while staying below the sub-grid tick labels' priority (9) to preserve the intended fine-to-coarse hierarchy (sub-grid > 100km > UTM GZD). New `TestApplyLabelOffset` and `TestApplySquareLabel.test_square_labels_outrank_utm_label_but_not_sub_grid` in `tests/test_grid_labels.py`. 91/91 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-03, spotted, then fixed 2026-08-06**: the UTM/GZD label itself (`GridLabelManager.apply_label()` in `grid/grid_labels.py`) could overflow into the neighbouring grid zone square at certain (zoomed-out) scales - same overlap symptom as the 100km case above, but on the UTM label's own side of the boundary. Root cause: `apply_label()` applied its `GZD_LABEL_OFFSET_MM` up-left nudge unconditionally at every scale, with no equivalent of `apply_square_label()`'s own zoomed-out fallback - once a GZD polygon's on-screen size shrank enough that a fixed 12mm offset from its centroid reached past its own edge, the label landed in the neighbouring zone instead. Fixed the same way as the 100km case: `apply_label()` is now `QgsRuleBasedLabeling` with two scale-gated rules instead of one fixed `QgsVectorLayerSimpleLabeling` - offset while zoomed in (`@map_scale < GZD_OFFSET_MAX_SCALE`), centred with no offset once zoomed out past it, mirroring `apply_square_label()`'s corner/centred split. New `GZD_OFFSET_MAX_SCALE = 3000000` is a loose derivation (a 12mm offset should stay well inside even a GZD zone's narrower half-width up to roughly this scale) rather than a live-measured value - worth tuning after watching it render at the actual boundary scale, same caveat `CENTER_LABEL_MAX_SCALE` already carries. `tests/test_grid_labels.py`'s `TestApplyLabelOffset` rewritten for the new two-rule structure (rule count, offset/centred settings, scale partition, shared priority). 132/132 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-06, actual root cause found - the scale-gating fix above wasn't the real bug**: user reported the leak was still happening after the fix, and pinned it down precisely with a fresh-project repro (new project, fresh World Map, freshly generated UTM Grid, then panned/zoomed and watched labels creep into every neighbouring zone - N/S/E/W and diagonally). Ruled out the zone geometry itself first (`grid/utm_grid.py`'s `generate()` always builds each GZD zone as its full, true, un-clipped rectangle, confirmed by reading the code) - this was purely a labelling bug. Root cause: `placement = Qgis.LabelPlacement.OverPoint` applied directly to a polygon feature (no geometry generator) doesn't anchor PAL to the feature's true, full centroid - for a polygon that's only partially on screen, which is routine for a GZD zone (unlike a 100km square, usually small enough to be fully visible at once), PAL instead derives a position from whatever portion is currently visible, sliding the label toward whichever edge is panned off screen. `_corner_settings()` never had this problem because it already forces a fixed point via `geometryGenerator = "make_point(...)"` before placing; `_gzd_offset_settings()`, `_gzd_centered_settings()`, and the 100km square's own `_centered_settings()` all skipped that step. Fixed by adding a shared `_anchor_to_true_centroid()` helper (`geometryGeneratorEnabled = True`, `geometryGenerator = "centroid($geometry)"`) applied to all three - `centroid($geometry)` is computed from the full, true geometry regardless of what's currently on screen, so panning can no longer move the anchor. New tests confirm all three settings builders wire up the geometry generator correctly. 137/137 tests passing on both QGIS 3.44.12 and 4.2.0.
- ✅ **Print-layout scale bar renders too large in some cases** (`layout/scale_bar.py`) — actually fixed and re-verified 2026-08-03 (previously only administratively checked off 2026-07-31; see git history for that note). Root cause, confirmed with real rendered crops at 1:1,000 and 1:2,000: `_pick_units_per_segment()`'s "nice" segment-size list (`NICE_SEGMENT_KM`) bottomed out at 0.1 km/segment, too coarse for close-in scales — at 1:1,000 on an A4-landscape (297mm-wide) page, the picked bar came out **400mm wide** (5x the 80mm target), and since the bar is horizontally centered via `(page_width - bar_width) / 2`, that went negative and visibly pushed the bar into the metadata block (its line rendered directly through the "Projection: UTM zone GZD 36M" text). Fix: extended `NICE_SEGMENT_KM` one more decade down (`0.01, 0.02, 0.025, 0.05`), following the exact same 1x/2x/2.5x/5x pattern the list already used — 1:1,000 now lands exactly on the 80mm target, 1:2,000 comes in at 100mm (1.25x, well within any real page). Scales at 1:10,000 and above are unaffected (confirmed no regression). Covered by three new tests in `tests/test_layout.py`'s `TestPickUnitsPerSegment`. This doesn't add a hard page-width ceiling — an even tighter scale or a very narrow custom page could theoretically still overshoot — but covers every case actually observed.

The 100km label, scale bar, and UTM/GZD label overflow items have all now been genuinely root-caused, fixed, and re-verified with real rendered output/passing tests (not just administratively marked).

- ✅ **Fixed 2026-08-17 - and it was not merely cosmetic.** The threshold is now derived PER CELL from the cell's own room, not a single global constant. `grid/utm_grid.py` computes each GZD cell's smaller half-dimension in metres (`_minimum_half_extent_m()`, measured at the cell's POLEWARD edge, deliberately - a cell narrows towards the pole and the label is nudged towards the pole, so measuring at the centroid would overstate the room) and carries it on the feature as `HALF_MIN_M`; `grid/grid_labels.py` turns that into a per-feature maximum scale, the point at which the 12mm nudge would spend more than `GZD_OFFSET_SAFE_FRACTION` (half) of that room. **Measuring what the old constant actually did shows it was wrong in both directions**: an equatorial 6-degree cell can carry the offset to 1:13,800,000, so 3,000,000 was over four times too cautious and centred labels that had ample room; but **30X and 38X only reach 1:1,450,000, and 31X/37X 1:2,180,000 - so at the old 3,000,000 the offset was still being applied where it no longer fitted, which is the very bug the constant was introduced to fix.** It was safe across most of the world and quietly broken in band X. 31V, the 3-degree cell the 2026-08-17 zone-exception fix created, lands at 1:3,050,000 - almost exactly the old value by coincidence. **One real trap found by a test rather than by reading**: the first version put the fallback inside the expression as `coalesce("HALF_MIN_M" * k, 3000000)`, which does not work - referencing a column that does not exist is an evaluation ERROR, not a null, so `coalesce()` cannot rescue it and the whole expression yields null, making `@map_scale < null` false for BOTH rules. A "UTM Grid" layer from a project saved before this field existed would have lost its GZD label entirely. The field's presence is now checked in Python when the rules are built, and such a layer gets the plain old constant. 1317 → 1321 tests on both QGIS 3.44.12 and 4.2.0.
- ✅ **Two more GZD labelling defects, reported after smoke-testing the above and fixed 2026-08-17.** Both reproduced offscreen before any code changed, which is the only reason the second one got diagnosed correctly. **(1) A world view buried the grid under its own labels.** `_apply_gzd_common_settings()` sets `displayAll = True` deliberately, so the GZD label still shows as a faded watermark when it loses a priority fight to the 100km or sub-grid labels - but `displayAll` switches OFF PAL's collision suppression, which is the only thing that would otherwise hide a pile-up. With no upper cutoff, a world view drew **1,197 labels on top of each other** and the grid lines vanished underneath. `apply_square_label` had this pairing right for 100km squares all along (`CENTER_LABEL_MAX_SCALE`, whose comment states the reasoning outright); the GZD label simply never got the matching half. Now cut off per cell, at `GZD_LABEL_MIN_ON_SCREEN_MM = 16.0` - calibrated, not guessed, from the maintainer's own report that a world view first became marginally readable at 1:40,372,844, which for a 6-degree equatorial cell is 16mm across. **(2) The label vanished when panned.** `_anchor_to_true_centroid()` had fixed a real bug (PAL drifting the label toward the visible portion and sliding it into the neighbouring zone) but left exactly ONE anchor point, so zooming in until a zone exceeded the viewport and panning off its centre left no label anywhere. **The first attempt at this was wrong and a render caught it**: corner labels, copying what `apply_square_label` does for 100km squares, were built, tested green, and then rendered - and still showed nothing, because panning into the deep interior of a GZD cell leaves no corner on screen either. `apply_square_label`'s own docstring records that same limitation being hit in 2026-08-03. The corner band was deleted and replaced with `_anchor_to_visible_centroid()`: `centroid(intersection($geometry, @map_extent))`. That satisfies both bugs at once - the point is always on screen when any part of the cell is, so the label cannot vanish; and since a cell and a map extent are both rectangles their intersection is a rectangle whose centroid is strictly inside it, so the label cannot escape into the neighbour. When the whole cell is visible it reduces exactly to the true centroid it replaces. One consequence worth naming: the 12mm offset now applies only while `contains(@map_extent, $geometry)`, because nudging from a narrow clipped sliver's centre could cross the cell's edge - the same failure the offset threshold exists to prevent, reappearing by another route. The 100km square labels keep `_anchor_to_true_centroid()` unchanged: their squares are small enough that the refinement buys nothing, and changing smoke-tested placement for no gain is the wrong trade. 1321 → 1325 tests. Verified with renders at the maintainer's own three reported scales plus both original failure cases.
- ✅ **A third, smaller GZD labelling defect, reported and fixed 2026-08-17.** Panning east-west, a label crossed its own cell edge into the neighbour by about one character. Direct consequence of the visible-portion anchor above: the label is CENTRED on the midpoint of whatever part of the cell is on screen, so once that part is narrower than the label itself, half the text hangs over the boundary. A label is a fixed page width; a sliver is not. Fixed by not labelling a cell whose visible width falls below the same `GZD_LABEL_MIN_ON_SCREEN_MM` already used as the world-view cutoff - a label that cannot fit in that space could not have been read there anyway, and the neighbouring cell (which by definition has the room) still carries its own. `grid/utm_grid.py` gains a `WIDTH_M` field for this, separate from `HALF_MIN_M`: a label overflows SIDEWAYS, so what decides whether it fits is the cell's width, not whichever of width and height happens to be smaller. The check is written as a dimensionless ratio of visible width to full width, multiplied by `WIDTH_M`, so it holds whatever the project CRS is rather than assuming degrees. Confirmed by render in both directions: a thin sliver at either screen edge now goes unlabelled while the middle cell keeps its label, and two half-visible cells each keep theirs without either crossing the line. 1325 → 1326 tests on both QGIS 3.44.12 and 4.2.0. Superseded note, kept for the reasoning: `GZD_OFFSET_MAX_SCALE = 3000000` (the scale at which the UTM/GZD label switches from its up-left nudge to sitting dead-centre) is a loose derivation, not yet confirmed against a real render at the actual boundary scale. User-confirmed 2026-08-06 that the underlying centroid-anchoring bug is fixed and this is fine to leave as-is for now - revisit only if the offset ever visibly looks off right around that threshold in practice, and just nudge the constant if so.
- ✅ **Deleted 2026-08-17.** `core/mgrs_engine.py` carried a leftover `# FIXME: do we really need this?` above 34 lines of already-commented-out dead code from the original vendored MGRS library - a rounding correction at the truncated eastern edge of zone 31V, plus zone-1/60 antimeridian and 71N+ branches. The question it asked is now answered rather than merely deferred: the zone-assignment exceptions it related to are already applied, live and uncommented, in `_latLonToUtm()`, and the drawn grid was brought into agreement with them the same day (see Phase 3's 2026-08-17 entry). The block was answering a question nothing asks. Replaced by a short note saying what was removed and why, so the next reader of that function does not have to re-derive it from git history. No behaviour change - the code was already inert - and no test moved.

- ✅ **`supportsQt6=True` declared 2026-08-17.** Surfaced by the housekeeping pass below and added on the maintainer's instruction. The flag was simply absent, which is not the same as absent-because-untrue: the full suite has been running against **QGIS 4.2.0 (Qt6) on every single change** alongside 3.44.12 (Qt5), with both required to pass before anything ships, and the two Qt6 forward-compatibility findings the Plugin Repository ever raised (0.1.0's enum scoping, 1.0.0's `QJSEngine` import) were both fixed at the time. Without the flag the repository cannot distinguish a plugin that is Qt6-ready from one that has never been tried, and presents it accordingly - the most likely explanation for the listing reading oddly on QGIS version support, though that was never confirmed against the live page. The declaration is annotated in `metadata.txt` with the evidence rather than left bare, so a future reader can see it was earned rather than assumed. Reaches the listing at the next upload. 1326 tests on both QGIS 3.44.12 and 4.2.0.
  - **Removed 2026-08-18, on the repository's own notice.** The 1.1.0 upload passed every security check and came back with an informational (non-blocking) message: `supportsQt6` is deprecated and no longer read - QGIS 4 compatibility is now decided solely by `qgisMaximumVersion`, already `4.99.0` here and needing no change. The flag and its evidence comment removed from `metadata.txt` outright rather than left inert, so a future reader does not have to work out whether it is still meaningful. This entry is kept, not deleted, as the record of why it was ever added in the first place - the reasoning was sound at the time, the platform's own contract just moved.
- ✅ **Full housekeeping pass 2026-08-17, on the widened checklist.** The maintainer's point after the earlier pass reported clean: *"when i meant housekeeping, it should have included all these checks also"* - the earlier sweep covered code and `docs/` only and stopped at the repo boundary, so everything that had actually rotted was on a surface a USER sees. The checklist is now five groups: code and docs; user-facing text (About dialog, `metadata.txt`, `README.md`, checked AGAINST EACH OTHER); attribution; repo hygiene; and the published listing. Two real finds this time, both invisible to the old sweep. (1) **`README.md` still omitted the tactical graphics entirely** - it described "military mapping and MGRS work: coordinate conversion, military grid generation, terrain analysis, and automated print-layout production", which is the 0.1.0 scope plus Phase 8. Phase 10, the single largest body of work in the plugin, was missing from the first paragraph anyone reads. (2) **`supply_points.py`'s "Audited, NOT built" block described 19 rows of Table H-XXIII as outstanding** - 17 of which were built the very next day, 2026-08-14. The audit is worth keeping (it is where the letters, anchor counts and traffic variants were settled) so it is retitled rather than deleted, with the build date on it. Notably the earlier sweep's own grep EXCLUDED "NOT built" as a deliberate phrase, which is exactly how that one survived. Everything else checked clean: no FIXME or TODO in runtime code (the three hits quote milsymbol's own upstream markers), all four `THIRD_PARTY_NOTICES.md` components now credited in the About dialog, and the remote down to `main` plus one tag. 1326 tests on both QGIS 3.44.12 and 4.2.0.
- ✅ **About dialog corrected 2026-08-17.** Two problems, both spotted by the maintainer after 1.0.3 went live. (1) Its description line still read "Military mapping and MGRS tools for QGIS" - the plugin's own 0.1.0 scope, carried unchanged through everything since. Replaced with `metadata.txt`'s own current `description=`, so the two now say the same thing. The identical staleness sat in the GitHub repository description ("MGRS Tools for QGIS 4.0" - also wrong about the version, since 3.44 is the declared minimum); that field lives on GitHub rather than in the repo and the maintainer corrected it directly. (2) **Only one of four third-party components was credited.** The MGRS conversion engine was named; milsymbol, the World Magnetic Model and the grid-workflow reference were not - even though milsymbol renders every one of the 1,043 point icons. Worth being precise about what was and was not at stake: **no licence obligation was being missed.** MIT requires its notice to travel with the software, and `THIRD_PARTY_NOTICES.md` plus `military_symbology/vendor/milsymbol-LICENSE` both ship inside the plugin package (verified in the 1.0.3 zip); CC0 requires nothing. The problem was editorial - naming exactly one dependency implies it is the only one. All four are now listed with author and licence, and the dialog points at THIRD_PARTY_NOTICES.md for the full texts. 1326 tests on both QGIS 3.44.12 and 4.2.0. Reaches users in the next release.

**Status: Complete.** The plugin is published and live on the official QGIS Plugin Repository. All three known-issue items (100km grid label placement, fixed 2026-08-02; scale bar oversizing, fixed 2026-08-03; UTM/GZD label overflow, fixed 2026-08-06) are genuinely fixed and re-verified, not just administratively marked. Two minor items deferred, neither tracked as a bug: GZD_OFFSET_MAX_SCALE's exact threshold value, and the mgrs_engine.py FIXME cleanup above. **Both revisited 2026-08-17** - see the FIXME's own bullet above for what that dead block actually is, and the note there on GZD_OFFSET_MAX_SCALE.

---

## Phase 8 — Terrain analysis

Scoped 2026-08-03, consolidating the original one-line item list into better-defined work: several original items either duplicate what QGIS already provides natively, or aren't really separate features so much as facets of the same one.

- ✅ **Tanaka contours** — done 2026-08-03. `terrain/tanaka_contours.py` + `terrain/tanaka_dialog.py`, a new toolbar action. Pipeline: clip + reproject the DEM to its local UTM zone in one `gdal:warpreproject` call (extent/CRS math needs to be projected/metric, since real-world DEMs are often geographic degrees), generate contours via `gdal:contour`, split into uniform segments via `native:splitlinesbylength`, then compute each segment's illumination directly from its own bearing (a contour is always perpendicular to the true slope direction, so no separate aspect raster is needed - just sampling the DEM on both perpendicular sides via `QgsRasterDataProvider.sample()` to find which side is uphill). Styled with data-defined stroke width **and** color (`color_mix_rgb()` - confirmed its ratio is a 0-1 fraction, not 0-100, before using it) driven by that illumination value, per the user's choice of width+color over classic width-only monochrome. This is the plugin's first use of QGIS's Processing framework, which needed two test-harness changes (`tests/qgis_test_case.py` now initializes Processing; `run_tests.sh` adds the bundled GDAL binaries to `PATH` and the Processing plugin directory to `PYTHONPATH`) and surfaced a real interpreter-shutdown segfault (only reproducible through the actual `unittest` runner, only with real GDAL raster I/O - fixed by registering `QgsApplication.exitQgis()` via `atexit` for an orderly shutdown). Verified end-to-end against a real 730MB SRTM30m DEM (gitignored, never committed) - a ~4.5km clip produced 10,311 correctly-illuminated segments in well under a second. 63/63 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-04 follow-up, live-tested feedback**: two changes after actually using the feature. (1) **Colouring switched from illumination-driven to elevation-driven** - the user wanted "more colourful" contours matching the standard hypsometric ("layer tint") convention military/topographic maps use (shades of blue below sea level, green → yellow → brown → red → white with increasing elevation above it), rather than the original lit/shadow monochrome-ish blend. `_hypsometric_color()` now computes each segment's colour from its own `ELEV` against fixed absolute-elevation stops (`SEA_LEVEL_STOPS`/`LAND_STOPS`) - fixed rather than normalised to each DEM's own min/max, so the same elevation tints the same colour on any map sheet. Precomputed per-segment into new `R`/`G`/`B` int fields (same pattern as `ILLUM`) and applied via a simple `color_rgb("R", "G", "B")` data-defined expression, rather than pushing the multi-stop interpolation itself into an expression string. Stroke **width** still varies by `ILLUM` exactly as before (thin when lit, thick when shadowed) - the Tanaka relief effect is unchanged, only the colour channel's meaning changed. `lit_color`/`shadow_color` params and their dialog colour pickers were removed entirely (the hypsometric ramp isn't user-configurable colour-by-colour, matching "the standard convention" rather than asking the user to pick each one). Verified with a real headless render (not just field-value assertions) - contour colours visibly progress through the green band of `LAND_STOPS` as elevation rises across a synthetic sloped DEM. (2) **"Add as new layer" checkbox** - previously every run of the dialog created another "Tanaka Contours" layer, so tweaking settings and re-running piled up stale layers. Default (unchecked) now removes the existing "Tanaka Contours" layer before generating, correcting it in place; checking the box keeps the old layer and adds a new one alongside, for anyone who does want to compare parameter sets. The accept-flow logic was split out of `show_tanaka_contour_dialog()` into a separately-testable `generate_from_dialog_values()` so this could be covered without driving an actual modal dialog (new `tests/test_tanaka_dialog.py`). 76/76 tests passing on both QGIS 3.44.12 and 4.2.0. Manual smoke test against the real DEM (task still open from the original build) now also needs to confirm this pass's changes, not just the original pipeline.
  - **2026-08-04, second follow-up: the hypsometric ramp above was live-tested and came out wrong.** The user generated contours against a real DEM and got a single shade of brown, not a colourful spread - not a DEM/elevation-data problem as first suspected, but a real design flaw in the fixed-elevation-anchor version just shipped: a single Tanaka generation typically only covers a few hundred metres of local relief, and against a *fixed* global scale spanning 0-5500m, that local range only ever lands inside one narrow slice of it (in this case, squarely in the tan/brown band around 1250-1750m). The "same elevation tints the same colour on any map sheet" reasoning that motivated fixed anchors doesn't hold up for how this plugin is actually used (small-extent, one-area-at-a-time generation, not a single fixed-scale national atlas). **Fix**: `SEA_LEVEL_STOPS`/`LAND_STOPS` replaced with fraction-keyed `SEA_RAMP`/`LAND_RAMP` (0-1 rather than absolute metres), and `_hypsometric_color(elevation, min_elevation, max_elevation)` now normalises against *this generation's own* elevation range (computed in a first pass over the valid contour segments in `_build_output_layer()`, before colours are assigned in a second pass) rather than a fixed scale - so every run shows the full green-through-white ramp regardless of the area's absolute elevation. A real coastline (any negative elevation actually present in the output) still anchors land/sea exactly at 0 rather than at the dataset's own min, since sea level stays a physically meaningful boundary whenever it's actually in the data. Re-verified with a real headless render of the same synthetic sloped DEM used before - colours now visibly span from deep green through yellow, brown, and into near-white, not one shade of brown. `TestHypsometricColor` rewritten for the normalised signature; the integration test now asserts the lowest- and highest-elevation segments hit the first/last `LAND_RAMP` stops exactly, guarding against the ramp collapsing back into a narrow slice. 76/76 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-04, third follow-up: monochrome option added.** Requested alongside the elevation-colour ramp - some users want the classic grayscale Tanaka look (tone driven by illumination, same as width) rather than elevation colour. Added `monochrome=False` to `generate_tanaka_contours()`/`_apply_style()`: when `True`, `StrokeColor` is data-defined by a `color_mix_rgb()` blend between `MONOCHROME_SHADOW_GRAY` (40) and `MONOCHROME_LIT_GRAY` (235) driven by `ILLUM`, instead of the `color_rgb("R", "G", "B")` hypsometric expression - deliberately not full 0-255 black/white, so even a fully-shadowed segment stays legible against a white page. Line width is unaffected either way (`ILLUM`-driven in both modes) - only the meaning of colour changes. Wired into the dialog as a "Monochrome" checkbox (off by default, alongside the existing "Add as new layer" one). New `TestMonochromeStyle` in `tests/test_tanaka_contours.py` evaluates the actual `QgsProperty` against synthetic shadowed/lit features (not just string-matching the expression) to confirm it resolves to the expected grays; `tests/test_tanaka_dialog.py` covers the flag reaching the generated symbol end to end. 80/80 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **Researched 2026-08-06 against 6 independent sources** (Anita Graser's tutorial, Manifold's docs, the QGIS Hub style page, a GIS StackExchange "layer cake" thread, TopoToolbox's MATLAB writeup, and Evelyn Uuemaa's tutorial), triggered by the colour still not quite matching between Tanaka Contours and Hypsometric Tint even after the Combined Hillshade Overlay-blend fix. Root cause identified: the mismatch isn't just normalisation drift between two independently-generated layers - Combined Hillshade's Overlay blend sits structurally *between* Tanaka Contours (top, flat unblended colour) and Hypsometric Tint (bottom, gets darkened/lightened by the hillshade Overlay) in the layer stack, so even numerically-identical ramps look different once rendered. Three items identified, two built same day:
    1. ✅ **Width formula fix - a real bug against the documented convention, not just a style choice.** Every source agrees width should be thick at BOTH extremes (segment facing directly toward the light AND directly away from it/shadowed) and thin only at the perpendicular/grazing case - a symmetric function of the *absolute* angular deviation. The old `scale_linear("ILLUM", -1, 1, {max_width_mm}, {min_width_mm})` was a plain linear ramp across the signed range instead: shadowed (ILLUM=-1) came out thickest, lit (ILLUM=+1) thinnest (backwards - a fully-lit segment should be exactly as thick as a fully-shadowed one), and the true perpendicular/grazing case (ILLUM=0) landed at a flat *medium* width rather than the intended thin minimum. Fixed to `scale_linear(abs("ILLUM"), 0, 1, {min_width_mm}, {max_width_mm})` - applies identically across all three style modes. Dialog's width field labels updated from "Min line width (lit)"/"Max line width (shadow)" to "Min line width (perpendicular to light)"/"Max line width (facing toward/away from light)", since the old labels described the now-fixed backwards behaviour.
    2. ✅ **New third style mode: "Illuminated overlay"**, matching the "colourful Tanaka" technique multiple independent sources use (kevelyn1's tutorial, the StackExchange "layer cake" thread, a ResearchGate paper title found via search) - none of them bake elevation RGB directly into the contour line's own paint the way the existing default "Elevation colour" mode does; every one keeps the line purely grayscale-by-illumination and gets colour entirely from Overlay-blending onto a hypsometric raster underneath. New `STYLE_ILLUMINATED_OVERLAY` mode: full 0-255 white/black `color_mix_rgb()` by `ILLUM` (not the softened 40/235 Monochrome uses - Overlay math needs true black/white to drive properly) plus `layer.setBlendMode(CompositionMode_Overlay)` set on the Tanaka Contours layer itself (`QgsMapLayer.setBlendMode()` isn't raster-only - confirmed live, works the same way on a vector layer as `hillshade_combination.py` already uses it on a raster). `monochrome: bool` replaced everywhere with a proper `style_mode` string (`STYLE_ELEVATION_COLOR`/`STYLE_MONOCHROME`/`STYLE_ILLUMINATED_OVERLAY`), and the dialog's checkbox became a three-item combo box ("Style"). Existing "Elevation colour" and "Monochrome" modes are unchanged in behaviour (aside from the width fix above) - this is additive, not a replacement, since Elevation colour was a deliberate, already-shipped, user-approved choice (see the 2026-08-04 follow-up above), not a mistake to walk back unprompted. `generate_from_dialog_values()` pushes a non-blocking message-bar warning (generation still proceeds) if Illuminated overlay is selected with no "Hypsometric Tint" layer present in the project - without one, lit segments render nearly invisible against a blank canvas, so the warning matters, but nothing about the mode requires the layer to actually be there. 249 → 288 tests (`TestContourWidthFormula`, `TestContourStyleModes` replacing the old `TestMonochromeStyle` in `tests/test_tanaka_contours.py`; new illuminated-overlay/warning coverage in `tests/test_tanaka_dialog.py`); verified on both QGIS 3.44.12 and 4.2.0.
      - **2026-08-06, blend mode switched from Overlay to Soft Light after live testing against a real DEM.** With Hypsometric Tint (stepped, see below) + Illuminated overlay generated together over steep terrain at a 200m contour interval, peaks came out a muddy dark red/maroon instead of the clean bright highlights the reference sources show. Root cause: Overlay applies its full darken/lighten swing per segment, and with many short (50m) segments flipping between strongly lit and strongly shadowed as a ring's bearing rotates around a peak, the shadowed sides darkened the tint's own light peak colours too aggressively - densely-packed rings on steep terrain compounded this by covering proportionally more of each peak than a smooth continuous hillshade would. User experimented directly in QGIS and found Soft Light - a gentler version of the same darken/lighten effect that never pushes all the way to black/white - kept the tint's own hue recognisable through the shading instead of overpowering it. `_apply_style()` now sets `CompositionMode_SoftLight` instead of `CompositionMode_Overlay` for `STYLE_ILLUMINATED_OVERLAY` (the other two modes are unaffected, still `CompositionMode_SourceOver`). Renamed `test_illuminated_overlay_sets_overlay_blend_mode_on_the_layer` to `test_illuminated_overlay_sets_soft_light_blend_mode_on_the_layer` in both `tests/test_tanaka_contours.py` and `tests/test_tanaka_dialog.py`. 291/291 tests passing on both QGIS 3.44.12 and 4.2.0.
      - **2026-08-07, live-tested striping bug found deeper than the fixes above - two distinct causes, fixed in two passes.** User reported (via screenshots) a dense, near-uniform alternating light/dark "barcode" pattern along otherwise smooth, correctly-traced contour lines, in both Monochrome and Illuminated overlay + Hypsometric Tint modes, on both flat and steep terrain - reproduced against a real GMRT bathymetric DEM, not assumed from the screenshots alone.
        1. **DEM noise vs. a weak true-gradient signal (fixed first, `368f244`).** On genuinely low-relief terrain, the true elevation difference across `_segment_illumination()`'s narrow two-point sampling window can be smaller than ordinary DEM noise, making the raw per-segment "which side is uphill" comparison flip essentially at random. Widening the sample offset or averaging multiple point samples per segment were both tried first and confirmed NOT reliably effective for this mechanism - noise doesn't average out just by relocating or duplicating a single noisy read. Fixed instead with a new `_smooth_illumination()`: a centred moving average of each segment's raw `ILLUM` value along its own original contour line (grouped via `native:splitlinesbylength`'s own `ID`/`order` fields, new `ILLUMINATION_SMOOTHING_WINDOW = 9`), applied as a second pass in `_build_output_layer()` before styling. Verified through the unmodified pipeline: flip rate dropped from 41.3% to 15.9% in an extreme near-flat stress test, 32.3% to 4.3% in a moderate-noise case.
        2. **Real, dominant cause - found after the fix above was live-tested and the striping persisted, including on a steep, well-defined hillside with abundant true signal, directly contradicting the noise-vs-signal explanation.** Every earlier synthetic reproduction used straight, parallel contour lines from a constant-gradient DEM, which structurally can't expose a bug tied to a *rotating* segment tangent direction - only a genuinely curving contour ring can. A new radially-symmetric cone DEM (`tests/qgis_test_case.py`'s `build_synthetic_cone_dem()`) reproduced severe flipping (52.65%) with zero injected noise. Root cause: the fixed `UPHILL_SAMPLE_OFFSET_M` (15m) is routinely smaller than a real reprojected DEM's own pixel size (confirmed 60.72m for the reported GMRT DEM) - both of `_segment_illumination()`'s perpendicular sample points then land in the exact same pixel, an exact tie its tie-break always resolves the same way (`perpendicular_a`), and as a ring's tangent direction rotates all the way around, that fixed tie-break keeps flipping which real-world side gets picked - independent of terrain steepness or noise. Fixed with a new `UPHILL_SAMPLE_OFFSET_PIXEL_MARGIN = 1.25`: `_build_output_layer()` now widens the offset it passes to `_segment_illumination()` (which gained an explicit `sample_offset_m` parameter, defaulting to the old fixed constant for its own direct callers/tests) to `max(UPHILL_SAMPLE_OFFSET_M, UPHILL_SAMPLE_OFFSET_PIXEL_MARGIN * dem_layer.rasterUnitsPerPixelX())`, so both samples land at least about one pixel apart on coarse DEMs while staying at the original 15m on fine ones. Verified against both the clean synthetic cone DEM (52.65% -> 0.90%) and the real GMRT DEM that reported the bug (35.6% -> 4.1% on the same offset ratio; a fresh full-pipeline re-run afterwards measured 36.16% -> 4.28%), both through the unmodified pipeline. `_smooth_illumination()` from fix 1 above stays in place as a secondary safety net for whatever residual noise remains. New `TestUphillSampleOffsetPixelSizeAwareness` in `tests/test_tanaka_contours.py` (flip-rate proof against the cone DEM, plus a call-spy confirming `_build_output_layer()` actually passes the widened offset to production's own `_segment_illumination()`). 397/397 tests passing on both QGIS 3.44.12 and 4.2.0.
    3. ✅ **Discrete/stepped colour-ramp toggle for Hypsometric Tint - done 2026-08-06.** Every "colourful Tanaka" source reviewed uses stepped/banded raster classification, not a smooth gradient, for the underlying hypsometric layer. `_apply_raster_style()`/`generate_hypsometric_tint()` gained a `discrete=False` parameter - `False` keeps the existing `QgsColorRampShader.Type.Linear` smooth gradient (already shipped, already approved, unaffected), `True` switches to `Type.Discrete` using the exact same `SEA_RAMP`/`LAND_RAMP` stops as hard class boundaries rather than interpolation anchors, so no separate stop set was needed. Wired into `hypsometric_tint_dialog.py` as an opt-in "Stepped colour ramp" checkbox next to the existing opacity control, off by default. New `test_defaults_to_a_linear_smooth_gradient`/`test_discrete_flag_switches_to_a_stepped_ramp` in `tests/test_hypsometric_tint.py`, `test_discrete_flag_reaches_the_generated_layer` in `tests/test_hypsometric_tint_dialog.py`.
  - ✅ **Requested 2026-08-06, done 2026-08-16: a caution about long generation times.** Tanaka Contours can take noticeably long to generate against a large DEM and/or a small contour interval - more of the DEM to clip/contour, and/or a finer interval producing far more contour lines (each further subdivided into `segment_length`-sized pieces, each needing its own two-sided DEM sample for illumination), multiply directly into a much bigger `native:splitlinesbylength` + per-segment sampling workload. No warning today - the dialog just appears to hang until it's done. The original note here proposed a conditional message-bar `pushInfo` fired when the DEM's pixel count and/or `dem_extent_area / interval` implied a heavy run, and flagged that the thresholds would need real timing data rather than guesses. **Built 2026-08-16 as something deliberately simpler, on the user's own call** ("i don't need any verification... nothing complex"): a standing, unconditional caution (`CAUTION_TEXT`) as a bold, word-wrapped `QLabel` sitting between the form and the OK/Cancel buttons. Two reasons this is the better shape, not just the cheaper one. (1) **In the dialog, not the message bar** - a warning about how long a run will take is only useful while the settings that drive it are still on screen and still editable; a `pushInfo` fires after the dialog has already closed, when the only remaining option is to wait. (2) **Unconditional, so no threshold to guess** - a caution that appears only above some pixel-count/interval line is a worse signal than one that is simply always there, because its absence then reads as a promise of speed that nothing has actually measured. That removes the scoping pass the original note said this needed. Tests cover the label's text, that it's visible in the dialog, and that it wraps rather than widening the dialog. 1300 → 1303 tests passing on both QGIS 3.44.12 and 4.2.0.
- ✅ **Hypsometric tint** — done 2026-08-04. `terrain/hypsometric_tint.py` + `terrain/hypsometric_tint_dialog.py`, a new toolbar action. Follows directly from a real gap the user found in Tanaka Contours: its lines are colored by elevation, but the space *between* them is blank, unlike the filled "layer tint" look of the user's reference images. Rather than making Tanaka Contours paint fills (a different cartographic technique - filled raster/polygon tinting vs. illuminated contour lines, normally its own layer underneath contour lines rather than baked into them), this is a separate raster layer: clip + reproject the DEM (reusing Tanaka's own `clip_and_reproject_dem()`), then recolor it pixel-by-pixel with a `QgsColorRampShader` (`Type.Linear` for smooth interpolation - confirmed live, QGIS's own shader interpolates between stops at render time, no per-pixel Python loop needed unlike the vector case) built from the same `SEA_RAMP`/`LAND_RAMP` stops as Tanaka Contours, normalised the same way (`_build_color_ramp_items()` mirrors `hypsometric_color()`'s branch logic) so a raster fill and any Tanaka lines drawn over it agree on what color a given elevation gets. Rendered via `QgsSingleBandPseudoColorRenderer`, with a user-adjustable opacity. Since a raster is opaque and would otherwise cover any vector layers, it's explicitly inserted at the *bottom* of the layer tree root (`root.insertLayer(len(root.children()), layer)`) rather than the default top-of-stack position a plain `addMapLayer()` would use - reusing the exact z-order lesson from the MGRS/UTM grid z-order fix earlier this phase. Same "Add as new layer" checkbox pattern as Tanaka Contours (default replaces the existing "Hypsometric Tint" layer in place). Confirmed live: `QgsRasterDataProvider.bandStatistics()` emits a `DeprecationWarning` regardless of which overload/argument types are passed, on both QGIS 3.44.12 and 4.2.0 - a binding-level quirk, not fixable by calling it differently; accepted as a known, harmless warning (see `docs/developer-guide.md`) rather than something to work around, since the values returned are correct. Verified with a real headless render - a smooth green-through-white fill matching the reference images, on both QGIS versions.
  - **Shared refactor, same pass**: Tanaka Contours' own `_clip_and_reproject()` and hypsometric colour-ramp math (`SEA_RAMP`/`LAND_RAMP`/`_hypsometric_color()`) were pure logic this new feature needed unchanged, so they moved into `terrain/_dem_utils.py` (`clip_and_reproject_dem()`) and `terrain/_hypsometric_ramp.py` (`hypsometric_color()`) respectively - following the existing `grid/_style_utils.py` convention (a leading-underscore *module* name signals "shared, package-internal helper"). `terrain/tanaka_contours.py` re-imports both under their old private names (`from ._dem_utils import clip_and_reproject_dem as _clip_and_reproject`, etc.), so every existing call site, docstring, and test import kept working with zero changes needed elsewhere. Also factored the two near-identical synthetic-sloped-DEM test builders (in `tests/test_tanaka_contours.py` and `tests/test_tanaka_dialog.py`) into one shared `build_synthetic_sloped_dem()` in `tests/qgis_test_case.py`, since the new hypsometric-tint tests needed the same fixture and a third copy would have been one too many.
  - 89/89 tests passing on both QGIS 3.44.12 and 4.2.0 (`tests/test_hypsometric_tint.py`, `tests/test_hypsometric_tint_dialog.py`, plus `tests/test_plugin.py` updated for the new toolbar action).
  - Tip worth documenting rather than building: layering a QGIS-native Hillshade (Raster → Analysis → Hillshade, or `gdal:hillshade`) on top of this layer with "Multiply" blending mode (Layer Properties → Symbology → Blending mode) gives a fuller, textured relief look closer to some reference images, entirely with QGIS's own existing tools - no plugin code needed for that combination. **2026-08-04 update**: the Hillshade Combinations feature below now automates exactly this combination for a multi-directional blend rather than QGIS's own single-direction native Hillshade.
  - **2026-08-05, two real follow-ups from actually comparing the two layers side by side.** (1) **Colour mismatch between Tanaka Contours and this layer over the same DEM/extent**: Tanaka was normalising its per-segment colour against the elevation range of its own *drawn contour lines* (quantised to the contour interval, so it rarely reached the DEM's true min/max), while this layer normalised against the DEM's raw pixel range - two different ranges even for an identical DEM/extent, so the same elevation came out a different colour in each. Fixed by making both use one shared source of truth: `terrain._dem_utils.band_min_max()` (moved `hypsometric_tint.py`'s own `_band_min_max()` there, and `terrain/tanaka_contours.py`'s `_build_output_layer()` now takes `min_elevation`/`max_elevation` computed from the clipped DEM's raw band stats instead of scanning its own contour segments' `ELEV` values) - an identical DEM/extent now produces identical colours in both layers, confirmed live and covered by a new `TestColorMatchesTanakaContours` in `tests/test_hypsometric_tint.py`. Simplified `_build_output_layer()` to a single pass over the contour segments as a side effect, since colour no longer needs the segments' own min/max discovered first. (2) **Regenerating always reset the layer to its default position** (bottom of the stack for this layer, top for Tanaka Contours), even after the user had manually dragged it elsewhere in the Layers panel - correcting a layer in place isn't much of an improvement if it also undoes the user's own organisation every time. New shared `terrain/_layer_utils.py`'s `replace_named_layer()` remembers the existing layer's layer-tree position before removing it, then relocates the freshly-generated replacement there instead of leaving it at generate()'s own default placement; both dialogs' `generate_from_dialog_values()` now go through this helper for the default (non-"Add as new layer") path. New `tests/test_layer_utils.py` plus a `test_regenerate_preserves_manually_moved_layer_position` in each dialog's own test file. 97/97 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-05, manual verification**: `SEA_RAMP` (the below-sea-level, blue branch of the hypsometric ramp) confirmed rendering correctly by the user against real bathymetric DEM data (GMRT), the first time this code path had been exercised over genuine sea-floor elevation rather than only inland test DEMs. Closes out the last open item from the original Tanaka Contours build.
  - ✅ **2026-08-04 issue above, root-caused and fixed 2026-08-06.** Directly compared Tanaka Contours' own per-segment `R`/`G`/`B` fields against `QgsColorRampShader.shade()` at the same elevation, against a real DEM, rather than reasoning about it - this surfaced two distinct effects, not one: (1) at elevation **exactly 0** (any real coastline), Tanaka's `hypsometric_color()` resolved to LAND_RAMP's green `(57,130,69)` while the raster shader resolved to SEA_RAMP's blue `(168,218,250)` for the identical value - a genuine, visible colour seam at every coastline, not a rounding artefact. Root cause: `_build_color_ramp_items()` builds SEA_RAMP's own top stop and LAND_RAMP's own bottom stop to the same absolute value (0), a real tie in the shader's sorted item list; `hypsometric_color()` resolves elevation 0 to LAND unambiguously via its own `if elevation < 0` branch, but `QgsColorRampShader.shade()` resolved the tied stop to whichever sorts first, which turned out to be SEA_RAMP's. Fixed by nudging SEA_RAMP's tied stop to `-1e-6` so the tie can no longer occur, breaking it in LAND_RAMP's favour to match `hypsometric_color()` exactly - confirmed live, `shader.shade(0.0)` now returns LAND_RAMP's green. (2) Separately, away from the exact coastline, colours differ by up to 1 unit per RGB channel almost everywhere (e.g. `(18,64,125)` vs `(17,63,125)`) - this is Tanaka's own Python interpolation (`_interpolate_stops()`, using `round()`) rounding slightly differently than QGIS's native C++ shader interpolation for the same fractional position; both are computing the same ramp correctly, they just don't always round to the identical integer. Left as-is: eliminating it entirely would mean abandoning the raster's fast native shader for a per-pixel Python-computed alternative, to remove a difference invisible at normal viewing distance. New `test_only_one_item_lands_exactly_at_zero` in `tests/test_hypsometric_tint.py` guards against the tie reappearing. 168/168 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-06, manual smoke test against real DEMs (GMRT bathymetry, Tanzania SRTM) found and fixed three more real bugs, shared across Tanaka Contours/Hypsometric Tint/Combined Hillshade/Line of Sight.** (1) **Switched from canvas-extent to the DEM's own full extent** for all three dialog-driven terrain generators (Tanaka Contours, Hypsometric Tint, Combined Hillshade) - `generate_from_dialog_values()` in each dialog now calls `dem_layer.extent()`/`dem_layer.crs()` instead of `iface.mapCanvas().extent()`/`destinationCrs()`. Requested after the user correctly identified that re-deriving from whatever the canvas happens to show at generate time was a real design smell - any regenerate (even just tweaking opacity) could silently pick up a different clip if the view had drifted even slightly, mirroring the exact canvas-extent bug Line of Sight already had to fix for its own two-point clip. New `test_generation_uses_the_dems_own_extent_not_the_canvas` in each dialog's test file confirms moving the canvas to a totally disjoint area doesn't affect the result at all. (2) **Hypsometric Tint's colours were silently replaced by QGIS's own default ramp just from opening and closing Layer Properties, with zero edits made** - root cause: `QgsColorRampShader.setColorRampItemList()` alone leaves the shader with no registered `QgsColorRamp` object QGIS's own Symbology UI can recognise, so its widget rebuilds the shader from a fallback default whenever the Properties dialog is confirmed. Fixed with a new `_build_source_color_ramp()` in `terrain/hypsometric_tint.py`, building a proper `QgsGradientColorRamp` from the same stops and attaching it via `setSourceColorRamp()`. (3) **Regenerating a layer in place (not "Add as new layer") could make it vanish entirely from the Layers panel** - reported for all three raster/vector generators plus Line of Sight. Root-caused via QGIS's own API, not guesswork: a live GUI session has a `QgsLayerTreeRegistryBridge` with a `layerTreeInsertionPoint()` tied to whatever's currently selected in the Layers panel, which a plain `QgsProject.addMapLayer()` call respects - a mechanism headless test scripts have no way to reproduce, since there's no Layers-panel widget to drive it. `generate_tanaka_contours()`/`generate_line_of_sight()` both used a plain `addMapLayer()` (vulnerable to this); `generate_hypsometric_tint()`/`generate_hillshade_combination()` already used the safer `addMapLayer(layer, False)` + explicit insert, but `terrain/_layer_utils.py`'s `replace_named_layer()` still removed-and-reinserted that same freshly-added node to reposition it - an independent source of churn on the very layer `generate()` just added. Fixed with a structural change: none of the four `generate_*()` functions add their result to the project any more (they build and style a plain layer and return it - see each function's own updated docstring); `replace_named_layer()` was rewritten to take an explicit `default_insert_position(project, layer)` callback and now performs the ONE-AND-ONLY project/tree insertion itself, either at the old layer's remembered position or via that callback, eliminating the double-insertion entirely. A new `add_layer_at_default_position()` helper covers the "Add as new layer" checkbox path, which previously relied on `generate()`'s own self-insertion too. Each feature keeps its own small `default_insert_position()` (top of tree for Tanaka Contours/Line of Sight, bottom for Hypsometric Tint, Hypsometric-Tint-aware for Combined Hillshade) rather than centralising feature-specific placement logic in the shared helper. 167/167 tests passing on both QGIS 3.44.12 and 4.2.0 - all four `generate_*()` functions now have a `test_output_layer_is_not_added_to_the_project` regression test, and each `default_insert_position()` has its own placement test.
  - **2026-08-06, item (2) above re-tested live and found still broken - the `setSourceColorRamp()` fix wasn't the real bug.** User re-confirmed via a fresh-project repro with screenshots that Hypsometric Tint's colours still shifted from opening and closing Layer Properties (and, separately, from just changing the layer's transparency), despite the source-ramp fix. The real root cause, found from the screenshots rather than another guess: the Layers panel's legend for a freshly-generated Hypsometric Tint layer read a flat **"255" / "0"** two-stop bar - not this raster's real elevation range - and only switched to showing the correct range *after* Properties had been opened and closed once. `QgsColorRampShader()`'s no-arg constructor leaves `minimumValue()`/`maximumValue()` at their default 0.0/255.0, and `_apply_raster_style()` only ever called `setColorRampItemList()`/`setSourceColorRamp()` - never `setMinimumValue()`/`setMaximumValue()`. Confirmed via the PyQGIS API that `setMinimumValue()`/`setMaximumValue()` also rebuild an internal shading lookup table QGIS uses for continuous-mode rendering, which explains why leaving them at the 0-255 default visibly skewed the actual rendered colours too, not just the legend label - real elevations (e.g. -1252..275) mostly fall outside a table built over [0, 255]. Fixed by explicitly calling `color_ramp_shader.setMinimumValue(items[0].value)` / `setMaximumValue(items[-1].value)` in `_apply_raster_style()`, so the layer is fully correct the moment it's generated and no longer depends on Properties being opened to "fix" it. New `test_shader_min_max_match_the_dems_own_elevation_range` in `tests/test_hypsometric_tint.py` guards against these two values silently reverting to the 0.0/255.0 default. 169/169 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-06, same live re-test: the `setMinimumValue()`/`setMaximumValue()` fix above was real but incomplete - the legend no longer showed the 0/255 placeholder, but the actual min/max (and the rendered colours) still visibly changed on opening and closing Properties**, confirmed via screenshots showing the Layers panel's own legend numbers shift (e.g. max dropping from the true 274.85 to an estimated 204.40) purely from that one interaction. Root cause, confirmed directly: a fresh `QgsRasterMinMaxOrigin()` defaults to `limits=NotSet`, `statAccuracy=Estimated` - with nothing pinned, QGIS's own Symbology widget treats our exact `band_min_max()`-derived values as provisional and recomputes its own min/max from a fast SAMPLED estimate the moment it loads, which came out narrower than the true range because sampling missed the actual peak pixel. `QgsColorRampShader.setMinimumValue()/setMaximumValue()` (the previous fix) and `QgsRasterRenderer.setMinMaxOrigin()` are two separate, independent pieces of state - fixing only the first still left the second telling QGIS "nothing here is authoritative, feel free to re-estimate." Fixed by explicitly setting the renderer's `minMaxOrigin` to `limits=MinimumMaximum`, `extent=WholeRaster`, `statAccuracy=Exact` in `_apply_raster_style()`, telling QGIS the values already computed there ARE the exact whole-raster min/max. New `test_min_max_origin_is_pinned_to_the_exact_whole_raster_range` in `tests/test_hypsometric_tint.py`. 170/170 tests passing on both QGIS 3.44.12 and 4.2.0. **User-confirmed fixed** - opening/closing Layer Properties and changing transparency on a freshly-generated Hypsometric Tint layer no longer shifts its colours.
- ✅ **Hillshade combinations** — done 2026-08-04. `terrain/hillshade_combination.py` + `terrain/hillshade_combination_dialog.py`, a new toolbar action. A one-click multi-directional hillshade blend (2-3 azimuths combined), since QGIS/GDAL's own hillshade tools (`gdal:hillshade`, the raster "Hillshade" render type) only do a single light direction natively - confirmed by inspecting the installed GDAL binary and the `gdal:hillshade` Processing wrapper source that GDAL's own `-multidirectional` flag exists but uses a fixed, non-user-configurable light set and silently ignores the azimuth parameter when enabled, so blending user-chosen azimuths is genuinely new capability, not a duplicate. Pipeline: clip + reproject the DEM (reusing `clip_and_reproject_dem()`), run `gdal:hillshade` once per azimuth in a chosen preset (`COMPUTE_EDGES=True` to avoid an unmasked NoData border getting baked into the average as a visible dark ring on this plugin's typically tight DEM clips), then average the resulting Byte rasters pixel-by-pixel via `gdal:rastercalculator`. Two dialog presets: "Two-direction (NW 315° + NE 45°)" and "Three-direction (NW 315° + NE 45° + S 180°)" (default) - 315° reuses `tanaka_contours.DEFAULT_LIGHT_AZIMUTH`'s existing convention; altitude/Z-factor stay fixed constants, not exposed. Rendered `QgsSingleBandGrayRenderer` with an automatic `QPainter.CompositionMode.CompositionMode_Multiply` blend mode, so it reads as relief texture over whatever sits beneath it rather than covering it outright. On insert, looks for an existing "Hypsometric Tint" layer and lands directly above (in front of) it if found, else falls back to the same bottom-of-tree default `generate_hypsometric_tint()` itself uses - deliberately doesn't retroactively reposition itself above a Hypsometric Tint layer added *after* it already exists on a later regenerate, consistent with never overriding a position the user may have organised manually (`replace_named_layer()` already handles that regenerate case generically). Same "Add as new layer" checkbox convention as the other terrain dialogs. **2026-08-06 update**: now generates against the DEM's own full extent rather than the canvas, and no longer self-inserts into the project - see the Hypsometric Tint entry above's 2026-08-06 note for the full story (applies to this feature too).
  - **2026-08-06, manual smoke test against real DEMs (GMRT bathymetry, Tanzania SRTM) found and fixed two real bugs.** (1) **Combined Hillshade + Hypsometric Tint together came out almost solid black over a mostly-flat area** (open water) - root-caused by directly sampling real pixel values, not just reasoning about it: `gdal:rastercalculator`'s `FORMULA` evaluates using each input's own on-disk dtype (Byte, since `gdal:hillshade` outputs Byte), so `"(A+B+C)/3"` computed the SUM `A+B+C` in 8-bit arithmetic *before* dividing - three individually-correct ~180 (mid-gray, flat-terrain) values summed to 540, silently wrapped modulo 256 to 28, then `/3` gave ~9 instead of ~180. Confirmed by sampling the same point on each individual azimuth's own hillshade output alongside the combined result. Fixed by explicitly casting each operand to float32 inside the formula itself (`"(A.astype(numpy.float32)+B.astype(numpy.float32)+C.astype(numpy.float32))/3"`) so the addition happens at full precision before the divide; `RTYPE` stays Byte since the final divided value is safely back in range. New `TestCombineHillshadesOverflowRegression` in `tests/test_hillshade_combination.py` uses a flat DEM specifically (not the ridge DEM the other tests use) - flat terrain guarantees every azimuth produces a high-enough mid-gray value that 2-3 of them reliably overflow 8-bit arithmetic if summed naively, whereas the ridge DEM's strong light/shadow contrast could coincidentally keep the (buggy) sum under 255 at the sampled point and mask the bug, which is exactly how it shipped initially without a failing test. (2) Separately, the `StretchToMinimumMaximum` contrast enhancement originally applied to this layer was also a real design flaw (independent of the overflow bug above, though it compounded the same "black over flat terrain" symptom): a hillshade's 0-255 scale is already meaningful on an absolute basis (flat ground legitimately sits around a fixed mid-gray for a given light altitude), unlike elevation, which genuinely needs per-generation normalisation - stretching whatever narrow range exists in one generation crushes a genuinely low-relief area toward black instead of showing its real neutral value. Switched to `NoEnhancement` (raw values, no per-generation stretch). Re-verified with a real headless render of both fixes together against the actual GMRT DEM - Hypsometric Tint's blue shades now correctly darken under the hillshade's Multiply blend (e.g. shallow-water blue `(168,218,250)` becomes `(118,153,176)` under a ~180/255 mid-gray hillshade, exactly the expected relief-texture effect) instead of turning solid black. 155/155 tests passing on both QGIS 3.44.12 and 4.2.0 (`tests/test_hillshade_combination.py`, `tests/test_hillshade_combination_dialog.py`, plus `tests/test_plugin.py` updated for the new toolbar action).
  - **2026-08-06, remaining manual smoke test checklist items user-confirmed against the real GMRT and Tanzania SRTM DEMs**: (1) Combined Hillshade generated alone (no Hypsometric Tint) shows the relief texture correctly, with no dark ring at the clip edges - the effect is subtle at default altitude/zoom (shaded closer to white) and needs a slight zoom-in to see clearly, which is expected relief-shading behaviour, not a bug. (2) Generating Hypsometric Tint first then Combined Hillshade after lands the hillshade above the tint automatically with the Multiply blend giving the intended "fuller, textured relief" look. (3) Regenerating after manually dragging Combined Hillshade's position in the Layers panel preserves that position. (4) Both azimuth presets (two-direction and three-direction) render correctly. All four items pass - Hillshade Combinations' manual verification checklist is now fully complete.
  - **2026-08-06, real follow-up: the Multiply blend from the fix above still didn't give a real "3D relief" look** - user compared the combined layer against a reference relief map and found no 3D impression from Hypsometric Tint alone (expected, it's flat colour), and once Combined Hillshade was layered on with Multiply, relief became visible but the colours turned muddy/mismatched compared to the reference. Root-caused with an actual rendered comparison rather than guessing: `QgsMapRendererParallelJob` was used to render Hypsometric Tint + Combined Hillshade over a real DEM (Kilimanjaro, Tanzania SRTM) under several blend modes and inspect the output images directly. Multiply can only ever darken (never lighten), which dragged the mid/high elevation band toward a desaturated brown-purple; Overlay (darkens shadowed slopes, lightens sunlit ones, relative to each pixel's own colour) visibly preserved the tint's own hue far better in the same comparison and was the user's choice after seeing both side by side. A separate, deeper cause was also found and deliberately left alone: `_hypsometric_ramp.py`'s `LAND_RAMP` stops at 0.55-0.85 (`(150,100,80)`, `(186,129,116)`, `(222,190,176)`) are themselves a dusty rose/mauve hue (red channel notably above green/blue), not orange/tan - present with or without Hillshade, just more visually obvious once shading adds texture to that exact elevation band. User decided this is a separate, more consequential change (it'd affect Tanaka Contours and Hypsometric Tint's already-shipped, already-approved look, not just this combination) and deferred it rather than declining outright - `_apply_raster_style()`'s blend mode change is scoped to Combined Hillshade only for now. **Revisited and fixed 2026-08-06** (with explicit buy-in, alongside the Discrete colour-ramp toggle above): `LAND_RAMP`'s 0.55/0.7/0.85 stops warmed from `(150,100,80)`/`(186,129,116)`/`(222,190,176)` to `(188,132,78)`/`(208,162,104)`/`(230,200,150)`. Root cause of the "dusty rose" read: the old stops' green and blue channels sat only 13-20 points apart (e.g. 129 vs 116), which reads as muted pink/mauve rather than orange - real orange/tan needs blue well below green. The new stops widen that gap to 50-58 points at the same three positions, shifting the hue to warm brown/tan without changing anything else about the ramp (endpoints, sea-side ramp, and normalisation logic are all untouched). Affects Tanaka Contours and Hypsometric Tint identically, since both share this one ramp. No test changes needed - every existing test referencing `LAND_RAMP` addresses it by position (`[0]`/`[-1]`), not literal RGB values. Also added an `opacity` parameter/dialog field to Combined Hillshade (`DEFAULT_OPACITY = 1.0`), matching Hypsometric Tint's and Viewshed's own convention - this layer previously had no opacity control at all. New `test_blend_mode_is_overlay` (renamed from `test_blend_mode_is_multiply`) and `test_opacity_is_applied` in `tests/test_hillshade_combination.py`; `test_opacity_value_reaches_the_generated_layer` in `tests/test_hillshade_combination_dialog.py`. 203/203 tests passing on both QGIS 3.44.12 and 4.2.0. **User-confirmed 2026-08-06**: live-tested the Overlay blend and it's fine.
- ✅ **Line-of-sight / visibility analysis** — done 2026-08-03, consolidating what were three separate original items (observation points, line-of-sight, terrain masks) into one tool. Click-driven: `terrain/line_of_sight_tool.py`'s `LineOfSightTool` (a `QgsMapTool`, structurally mirroring `core/coordinate_probe_tool.py`'s `CoordinateProbeTool`) turns two canvas clicks into an observer and a target point, filling in a small non-modal `LineOfSightDialog` (`terrain/line_of_sight_dialog.py`) as each is set - the second click auto-runs the check with default heights (1.7m observer eye height, 0m target/ground level), both adjustable afterwards via a "Generate" button. A third click starts a fresh pair rather than accumulating a log, unlike Coordinate Probe.
  - **Algorithm** (`terrain/line_of_sight.py`'s `compute_profile()`, pure and independently testable): samples DEM terrain elevation at evenly-spaced points along the straight line between observer and target (`QgsRasterDataProvider.sample()`, the same API Tanaka's own uphill-check already uses), **and** applies the standard two-point intervisibility earth-curvature/refraction correction (`drop = distance² × (1 - k) / (2R)`, `R` = mean earth radius, `k = 0.13` the standard terrestrial refraction coefficient) to every sampled point - so a check can fail either because real terrain blocks it or because the target is simply beyond the curvature-limited horizon, even over flat ground. Verified with dedicated unit tests for both failure modes independently (a synthetic ridge DEM for terrain blocking; a long flat synthetic DEM for curvature-only blocking), plus the inverse (a short ridge/short distance that should NOT block, proving it isn't a blanket "always blocked" bug).
  - **Output**: a "Line of Sight" line layer, green where visible / red where blocked (data-defined stroke colour off a `VISIBLE` field, same `QgsProperty`/`QgsSymbolLayer.Property.StrokeColor` mechanism Tanaka uses), going through the existing shared `replace_named_layer()` (position-preserving regenerate) by default, with the same "Add as new layer" checkbox convention as the other two terrain dialogs.
  - **Scope decision**: dead-ground (a full viewshed raster from one observer, sweeping every direction rather than checking one target) was deliberately deferred out of v1 after discussion - it's a separate, much more expensive per-pixel calculation, better shipped as its own fast-follow once the point-to-point check is solid, matching the incremental Tanaka Contours → Hypsometric Tint pattern. The user separately proposed a related sensor/radar-siting tool (site a point, feed a range parameter, get a coverage polygon) - noted as the natural next step once viewshed lands, since it reuses the same curvature/refraction math swept across a range instead of checked against one target.
  - **2026-08-03, manual smoke test follow-ups**: real usability and correctness fixes after testing against a real DEM. (1) **Distance readout** - the total observer-to-target distance, and (when blocked) how far along the path the first obstruction is, now shown in a persistent "Result" line in the dialog itself. `terrain/line_of_sight_dialog.py`'s new `_describe_result(layer)` derives both by summing each output segment's own geometry length (exact, since every segment is a straight subdivision of the same overall line) and reading the first `VISIBLE=False` feature's `DIST`. (2) **Dropped the redundant message bar push for the visible/blocked result itself** once the Result label above existed - a message bar toast duplicating information already sitting in the (already-open, already-focused) dialog was just noise; the message bar is now reserved for cases with no other feedback path (no DEM, no points, point outside the DEM). (3) **On-canvas click markers** - clicking gave no feedback on the map itself (only the dialog updated), so especially the first click was easy to miss and re-click by accident. `terrain/line_of_sight_tool.py`'s `LineOfSightTool` now drops a `QgsVertexMarker` at each clicked point (blue cross for observer, red X for target, matching the output line's own visible/blocked red), moved/cleared as the observer/target state machine progresses, and removed on `deactivate()` so switching tools doesn't leave them stuck on the canvas. (4) **Real bug: the line sometimes didn't auto-draw on the second click of a pair, only appearing once "Generate" was clicked by hand** - root cause was that the DEM clip extent was still `canvas.extent()`, read fresh at generate time; since the two points can legitimately be far enough apart that the user pans/zooms between clicking them, the first point could easily end up outside the *current* canvas view by the time the second click auto-ran the check, silently failing. Fixed by decoupling the clip extent from the map canvas entirely - `generate_line_of_sight()` no longer takes an extent/CRS argument at all, and instead clips to a small padded bounding box around the observer/target points themselves (new `_bounding_extent()`), so panning between clicks no longer matters. (5) **Related correctness bug surfaced by fixing (4)**: once the clip extent came from the two points instead of the canvas, a point genuinely outside the *source* DEM's own coverage no longer reliably failed - the post-warp raster could still return a plausible-looking sampled value (e.g. 0) for pixels beyond the source's real footprint rather than a clean "invalid" flag, since GDAL's NoData propagation for area outside a source raster's coverage isn't a dependable signal to check after the fact. Fixed with an explicit geometric containment check against the untouched source DEM's own extent *before* any clipping/warping happens, independent of GDAL's warp-time NoData behaviour. (6) **Real crash reported live**: once a "Line of Sight" layer already existed from a prior successful check, clicking a new pair with a point outside the DEM raised `AttributeError: 'NoneType' object has no attribute 'id'` instead of the intended warning. Root cause: `terrain/_layer_utils.py`'s shared `replace_named_layer()` (also used by Tanaka Contours/Hypsometric Tint) assumed `generate()` always succeeds - true for those two, not for Line of Sight, which can legitimately return `None`. It removed the old layer *before* calling `generate()`, then unconditionally called `.id()` on whatever came back to reposition it. The very first "point outside the DEM" test case happened to miss this entirely, since with no prior layer there's no remembered position, so that crashing code path was never exercised until a second, later attempt failed after an earlier one had succeeded. Fixed by reordering `replace_named_layer()` to call `generate()` *first*, returning `None` immediately if it fails (before removing anything) - a failed regenerate now leaves any existing layer untouched instead of both destroying it and crashing. New tests in `tests/test_layer_utils.py` (`generate()` returning `None` doesn't crash and doesn't touch an existing layer) and `tests/test_line_of_sight_dialog.py` (`test_failed_regenerate_after_a_successful_one_does_not_crash`, the actual repro shape: succeed once, then fail). 135/135 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-06 update**: `generate_line_of_sight()` no longer self-inserts into the project either - see the Hypsometric Tint entry above's 2026-08-06 note for why (a live-GUI-only insertion-point bug that made a regenerated layer vanish entirely, undetectable by any headless test).
- ✅ **Viewshed / dead-ground analysis** — done 2026-08-06. `terrain/viewshed.py` + `terrain/viewshed_dialog.py` + `terrain/viewshed_tool.py`, a new checkable toolbar tool. A full coverage sweep from one observer point (every bearing, out to a max range), rather than the one-target check Line of Sight does - deliberately deferred out of Line of Sight v1 (see that bullet's scope-decision note above) as a separate, much more expensive per-pixel calculation. **Design pivot from the original plan**: rather than hand-writing a per-pixel radial sweep in Python, this wraps GDAL's own native `gdal_viewshed` binary (confirmed present, exposed by QGIS's Processing framework as `gdal:viewshed`, identical parameter set on both QGIS 3.44.12 and 4.2.0) - the same "wrap the native GDAL tool" pattern already used for Tanaka Contours (`gdal:contour`) and Hillshade Combinations (`gdal:hillshade`), avoiding a slow, error-prone reimplementation of an algorithm GDAL already ships. Reprojects/clips the DEM first via the existing `clip_and_reproject_dem()` (confirmed necessary: `gdal_viewshed`'s `-md`/observer-coordinate units are the *input raster's own CRS units*, so a geographic source DEM would silently turn "5000 m" into "5000 degrees" otherwise), to a box sized around the observer from the requested max distance (new `_observer_extent()`, mirroring `line_of_sight.py`'s own `_bounding_extent()` pattern but for one point and a radius instead of two points' span). Output is a three-value raster rather than a plain binary mask - visible, **dead ground** (in range but blocked by terrain, the actual military term this feature is named for and distinct from simply "too far away"), and out of range (also this raster's own NoData, so it renders fully transparent with no extra renderer class needed) - rendered with a two-class `QgsPalettedRasterRenderer` reusing Line of Sight's own green/red colour convention, default 65% opacity so whatever's underneath stays visible through it. `gdal_viewshed`'s own `-cc` (curvature/refraction coefficient) is set explicitly from `line_of_sight.py`'s `REFRACTION_COEFFICIENT` rather than left at GDAL's own default (a different standard refraction coefficient), so the two features agree on the same physical assumption. Interaction mirrors Line of Sight's click-driven `QgsMapTool`/dialog split but simplified to one point - every click is a complete, standalone analysis (no observer/target pair state to track), auto-regenerating in place unless "Add as new layer" is checked. Same insertion architecture as every other terrain feature (`generate_viewshed()` never self-inserts; top-of-tree default placement, matching Line of Sight, since both are analysis overlays meant to sit above the base terrain rendering rather than a full-coverage base layer themselves). 199/199 tests passing on both QGIS 3.44.12 and 4.2.0 (`tests/test_viewshed.py`, `tests/test_viewshed_dialog.py`, `tests/test_viewshed_tool.py`, plus `tests/test_plugin.py` updated for the new toolbar action).
  - **2026-08-06, user feedback before live testing led to two real design changes.** (1) **Output redesigned from a raster to a polygon of just the visible area.** The original three-value raster (visible/dead ground/out of range) rendered visible and dead ground together as one solid-looking disc covering nearly the whole swept area - user feedback (with a reference screenshot of a different radar-coverage tool) was that this reads as "the whole circle matters" rather than highlighting the specific area that's actually visible, which is what's actually useful. The raster from `gdal:viewshed` is now purely an intermediate step: `gdal:polygonize` converts it to vector polygons (one per contiguous same-valued region, tagged with a `DN` field holding the source pixel value), then `native:extractbyattribute` keeps only the `DN == VISIBLE_VALUE` features - dead ground and out-of-range areas are dropped entirely rather than styled differently, since `gdal:polygonize` already skips this raster's own NoData value (out of range) on its own. The result is styled as a single green `QgsFillSymbol` fill (reusing Line of Sight's own `VISIBLE_COLOR`) at the same 65% default opacity, replacing the old two-class `QgsPalettedRasterRenderer`. `DEAD_GROUND_VALUE`/`OUT_OF_RANGE_VALUE` remain as constants (still needed to drive the GDAL call and the attribute filter) but no longer reach the final layer or its styling. (2) **Below-sea-level elevations are now clamped to 0 for both Viewshed and Line of Sight.** User requirement: an observer or target over open water sits at the sea surface, not the seabed - a bathymetric DEM (e.g. GMRT) holding negative depth values would otherwise compute an observer-over-water's eye height from a large negative seafloor depth instead of the water surface, badly understating real visibility. `line_of_sight.py`'s `compute_profile()` clamps each Python-sampled elevation (observer, target, and every profile point) to `max(0.0, value)` directly - the same "below zero is sea" simplification `hypsometric_tint.py`'s own colour ramp already relies on elsewhere in this plugin, including the same accepted trade-off of also clamping a genuine below-sea-level inland depression the same way, since nothing in a DEM alone distinguishes that from ocean floor. `gdal:viewshed` has no equivalent option of its own, so `viewshed.py` gets a new `_clamp_to_sea_level()` pre-processing pass (`gdal:rastercalculator`, `numpy.maximum(A, 0)`) run on the clipped DEM before `gdal:viewshed` ever sees it. New regression tests in both `tests/test_line_of_sight.py` and `tests/test_viewshed.py` (a single-column depression at the observer's own point, isolated from any wider self-shadowing effect, confirms the observer is correctly treated as being at the water surface rather than the seabed). 201/201 tests passing on both QGIS 3.44.12 and 4.2.0. **User-confirmed 2026-08-06**: live testing (observer elevation correctly lifting the visible area, the visible-only polygon shape, and the sea-level clamp) is satisfactory.
  - **2026-08-06, second follow-up, on request**: `terrain/line_of_sight_dialog.py`'s Observer/Target labels and `terrain/viewshed_dialog.py`'s Observer label now show full-precision (1m) MGRS on a second line under the existing latitude/longitude, matching what Bearing/Range already does - each dialog gets its own `MGRSConverter` instance and `_format_lonlat(lonlat, converter)` gains the same `converter` parameter Bearing/Range's own helper already has. 247 → 249 tests.
  - **2026-08-16, on request: the two styling deferrals below (items 3 and 4) built together.** Taken as one change rather than two, exactly as the closing note under those items had suggested - they touch the same function, the same dialog rows and the same `values()` dict, and splitting them would have meant editing `_apply_polygon_style()` twice. **Colour**: `generate_viewshed()` and `_apply_polygon_style()` gained a `color` parameter (an `(r, g, b)` tuple) defaulting to a new `DEFAULT_COLOR` constant, which is still `line_of_sight.py`'s own `VISIBLE_COLOR` - so an untouched viewshed renders byte-identically to before, and the shared green "this is visible" language between Viewshed and Line of Sight is unchanged unless a user deliberately departs from it. A test asserts `DEFAULT_COLOR == VISIBLE_COLOR` rather than restating the constant, since that shared default is the actual decision worth pinning. The dialog gets a `QgsColorButton` (confirmed present and identical in API on both QGIS 3.44.12 and 4.2.0) with `setAllowOpacity(False)` - deliberately no alpha channel, because the dialog already has its own Opacity spin box and two controls over the same visual property would silently multiply together; `_rgb()` drops the alpha on the way out of `values()`, and a test pins that a colour set with an alpha still arrives as a plain three-tuple. **Outline only**: `_apply_polygon_style()` now branches on a new `outline_only` flag between the original filled symbol and a `QgsFillSymbol` with `"style": "no"` / `"outline_style": "solid"` at a new `OUTLINE_WIDTH_MM = 0.6` - the same width `line_of_sight.py` already draws its visible-segment line at, so an outline-only viewshed and a Line of Sight result drawn on the same map read as the same weight of mark. The colour picker drives whichever of fill or outline the toggle currently selects, pinned by its own test, rather than being a fill-only control. Both settings ride the same route as opacity and max distance - into `values()`, through `generate_from_dialog_values()`, applied on the next Generate or observer click - deliberately *not* wired to restyle the existing layer live, which would have made colour behave differently from every other control in the same dialog. Styling is tested directly against a throwaway memory polygon layer (a new `TestPolygonStyle`) rather than through a full `gdal:viewshed` run for every combination, with one end-to-end test confirming both arguments actually reach the output layer. 1289 → 1300 tests passing on both QGIS 3.44.12 and 4.2.0. Verified with real headless renders over the Tanzania SRTM clip (default green, a picked blue, and magenta outline-only) plus offscreen grabs of the dialog itself - which surfaced one thing worth knowing before use: outline-only is *honest about the speckle*. A real viewshed polygonizes into a hundred-plus fragments, and drawing every boundary shows scatter that a flat fill visually merges into one mass. That's the data, not a bug, and no smoothing/simplification was added to hide it.
  - **Requested 2026-08-06 - four Viewshed enhancements**, all explicitly deferred at the time (user: "add them as to do works, not right now"). Items 3-4 built 2026-08-16 (see the entry directly above); items 1-2 remain not started:
    1. ⬜ **Multi-sensor coverage in one layer.** Today, every observer click either replaces the existing "Viewshed" layer in place or (with "Add as new layer" checked) starts an entirely separate layer - there's no way to add a second, third, etc. observer point whose visible areas *accumulate* (union) into the same layer. Real use case: modeling several sensors/observers in one area and seeing their combined coverage as a single picture, rather than one polygon per sensor or manually unioning layers afterward. A new layer should still be available on request, for comparing a distinct set of sensors against the current one. Touches `generate_viewshed()`'s single-observer signature and `viewshed_dialog.py`'s current "replace the whole named layer" `replace_named_layer()` usage - likely needs its own accumulation path (union new polygon into existing layer's geometry, or add a new feature per sensor to one multi-feature layer) rather than reusing that helper unchanged.
    2. ⬜ **Movable, persistent sensor points.** The observer marker (`QgsVertexMarker`) is purely a transient, click-driven UI cue - it doesn't correspond to any real feature in the output layer, so once the coverage polygon exists there's no way to grab the "sensor" and drag it to reposition, the way you can with an ordinary point feature in edit mode. User's stated preference: keep the sensor's own point visible and repositionable, with its coverage recomputing/updating as it's moved - closer to a live, editable sensor-siting layer than the current one-shot "click, get a static result" model. Acknowledged by the user as a real, non-trivial change to the underlying architecture (observer points would need to become actual stored/editable features, with some way to detect a moved point and regenerate that sensor's own polygon), not a small tweak.
    3. ✅ **Sensor polygon colour picker.** *(added 2026-08-06, done 2026-08-16 - built as scoped, a `QgsColorButton` in the dialog and a `color` parameter threaded through the styling step, default unchanged.)* The coverage polygon used to always be styled with `VISIBLE_COLOR` (green, reused from Line of Sight). Real use case: distinguishing multiple sensors/forces by colour (e.g. red/blue/yellow/green for different sides), especially once item 1 (multi-sensor) lands and several sensors' coverage might need to sit in view together, or be compared side by side. The scoping note written at the time - a colour picker in `viewshed_dialog.py` and a `color` parameter threaded through `generate_viewshed()`'s styling step, defaulting to the current green so existing behaviour is unchanged - is exactly what was built.
    4. ✅ **Outline-only vs. filled polygon toggle.** *(added 2026-08-06, done 2026-08-16 - built exactly as scoped here, including the `"style": "no"`/`"outline_style": "solid"` approach this note had anticipated.)* `_apply_polygon_style()` used to always render a filled `QgsFillSymbol`. Real use case: an outline-only rendering lets underlying terrain/imagery stay fully visible while still showing the coverage boundary - useful when overlaying several sensors' coverage areas at once, where stacked filled polygons (even at reduced opacity) obscure both each other and the map underneath. The scoping note written at the time - a checkbox/toggle in the dialog and a style branch in `generate_viewshed()`'s styling step (an outline-only `QgsFillSymbol` with `"style": "no"`/`"outline_style": "solid"`, rather than a different symbol type) - is exactly what was built.
    All four items reshape Viewshed from "one-shot analysis per click" toward "a small persistent sensor-coverage layer you build up, style, and edit over time" - worth designing together rather than separately, given how much they overlap (items 1-2 both need observer points to be real, addressable features rather than ephemeral clicks; items 3-4 are smaller, independent styling additions that could land first without needing the others). **That last prediction held**: items 3-4 landed on 2026-08-16 on their own, touching nothing items 1-2 will need to change. Items 1-2 are still the genuinely architectural pair, and still best designed together.
- ✅ ~~Radar/sensor-siting coverage polygon~~ — retired as redundant 2026-08-06. Originally scoped as "the same swept curvature/refraction calculation with a user-supplied max-range parameter, producing a coverage polygon rather than a shaded raster" - once Viewshed itself was redesigned to output a visible-area polygon with a user-set max distance (see the 2026-08-06 entry above), that description no longer distinguishes the two features at all. Considered whether a real difference was worth building anyway - a radio/radar-specific refraction coefficient (optical line-of-sight conventionally uses k≈0.13, `line_of_sight.py`'s own value, vs. a different standard for radio propagation, e.g. the "4/3 earth radius" model) and a sector/azimuth-limited sweep (a directional sensor doesn't always scan the full 360° Viewshed does) - user decided neither is worth a separate feature; Viewshed already covers this use case.
- ✅ ~~Slope/aspect convenience wrapper~~ — dropped 2026-08-06. Originally scoped as batch-generating slope + aspect (+ hillshade) with plugin-provided military-style symbology presets, on the theory that a one-click preset would save re-styling QGIS's native Slope/Aspect renderer by hand each time. Dropped because that reasoning didn't hold up: QGIS's own raster properties panel already offers "Slope"/"Aspect" rendering with one dropdown and no processing run needed, so the *only* value this would have added was the military-style presets themselves - a cosmetic convenience layered on a feature QGIS already ships natively, not new capability, and not worth the maintenance surface of a whole extra dialog/toolbar action for that alone.
- ✅ ~~Elevation profiles~~ — decided not needed 2026-08-03; QGIS 3.28+ (covers both this plugin's 3.44 and 4.x targets) already has a native Elevation Profile panel built in, so building a duplicate wouldn't add value.
- ✅ ~~DEM acquisition/download tool~~ — considered and explicitly decided not needed 2026-08-03. Getting a DEM is a generic GIS task already covered by QGIS's own Data Source Manager (WCS connections) and dedicated existing plugins (e.g. SRTM Downloader), not something specific to military cartography. It would also fit this plugin's actual audience poorly - military cartography users are exactly the kind who may be working disconnected or in restricted-network environments, where a feature that silently depends on live internet access is a liability rather than a convenience (contrast with `core/geomag/`'s WMM2025 data, vendored locally specifically to avoid any runtime network dependency). Every item above assumes a DEM is already loaded, same precondition QGIS's own Slope/Aspect/Hillshade/Elevation Profile/viewshed tools already have. **Follow-up reminder fulfilled 2026-08-03**: `docs/user-guide.md`'s new Tanaka Contours section includes a "Getting a DEM" pointer (Data Source Manager / SRTM Downloader), now that there's a real feature to attach it to. **Revisited and reaffirmed 2026-08-05**, after the user hit a real GMRT (bathymetry) download snag in practice: unlike SRTM, GMRT has no dedicated QGIS downloader plugin, and QGIS's own built-in "Download file" Processing tool needs the GridServer URL built by hand. Even a thin, scoped-down version (just an extent-to-URL convenience button, not a full downloader dialog) was considered and declined - the offline/restricted-network reasoning above still applies, and it would only ever help the narrow slice of usage generating terrain layers over open water. `docs/user-guide.md`'s Tanaka Contours section could eventually mention GMRT's GridServer as a bathymetry-specific pointer alongside the existing SRTM one, but that's a docs change, not a feature. **Written 2026-08-17**: "Getting a DEM" now names GMRT, its GridServer endpoint, and the two practical routes to a grid (the GMRT MapTool site, or QGIS's own "Download file" algorithm with a hand-built URL), plus the two things that actually bite once bathymetry is loaded - depths arrive negative, and both Line of Sight and Viewshed clamp them to sea level on purpose, while Hypsometric Tint's ramp already has a below-sea-level band. Still explicitly NOT a downloader: the offline-by-design reasoning above is unchanged.

Large and mostly orthogonal to the cartography/grid focus of Phases 1–7. Positioned here, after all completed work, as the biggest deferred effort remaining before the newer navigation/tactical-graphics phases below — revisit when there's appetite for a separate large effort.

**Status: Complete**, aside from two of the four requested-but-deferred Viewshed enhancements - multi-sensor coverage and movable/persistent sensor points (both 2026-08-06, not started, the architectural pair). Everything else deferred out of this phase is now closed: the sensor polygon colour picker and the outline-only/filled toggle, and the Tanaka Contours long-generation-time caution, were all **built 2026-08-16**. Tanaka contours, hypsometric tint, line-of-sight/visibility, hillshade combinations, and viewshed/dead-ground done and user-confirmed; the Discrete colour-ramp toggle, `LAND_RAMP` hue warm-up, and Illuminated overlay's Soft Light blend fix (all 2026-08-06) close out the reference research; radar/sensor-siting retired as redundant once Viewshed itself became a polygon-with-max-range tool; elevation profiles, DEM acquisition, and the slope/aspect convenience wrapper closed out as not needed.

---

## Phase 9 — Navigation & production utilities

Planned 2026-07-31, from a review of what a working military cartography
workflow still lacks beyond base-map/grid production. Chosen as the
"cheap wins" set: each item reuses existing plugin infrastructure
(`core/geomag`, the Coordinate Probe tool's `QgsMapTool` pattern,
`grid/utm_grid.py`, the New Military Layout suite) rather than opening a
new subsystem, so effort/risk is low relative to Phase 10.

- ✅ **Bearing/range (polar coordinate) tool** — click two points on the
  canvas, report true azimuth, grid azimuth, magnetic azimuth (reusing
  the WMM2025 declination code already in `core/geomag/`), and distance.
  **Built 2026-08-06.** `core/bearing_range_tool.py`'s `BearingRangeTool`
  reuses Line of Sight's own two-click state machine (first click sets
  "from", second sets "to" and logs a reading, third starts a fresh
  pair) rather than Coordinate Probe's single-click model, since a
  bearing needs two points; its `BearingRangeDialog` reuses Coordinate
  Probe's own persistent, newest-row-on-top log table instead of Line
  of Sight's single-result label, since a soldier is likely to want
  several readings kept side by side. True azimuth/distance come from
  `core/coordinate_utils.py`'s new `true_bearing_and_distance()`
  (`QgsDistanceArea.bearing()`/`measureLine()` against the WGS84
  ellipsoid, not a flat-plane approximation - matching how MGRS
  conversion already treats the earth); `QgsDistanceArea.bearing()`
  itself returns radians in (-pi, pi] rather than a conventional 0-360
  azimuth (confirmed live: due west came back as -90°, not 270°), so
  the result is normalised with `% 360`. Grid azimuth and magnetic
  azimuth reuse the plugin's own existing `grid_convergence()`/
  `magnetic_declination()` functions unchanged, computed at the "from"
  point (the standard grid-magnetic-angle-diagram convention) - both
  are defined the same way (positive means that north reference is
  east of true north), so both subtract from the true azimuth
  identically (`grid/magnetic = true - convergence/declination`, the
  same "east is least" relationship as a paper G-M angle diagram).
  203 → 223 tests; verified on both QGIS 3.44.12 and 4.2.0, plus a
  direct `BearingRangeDialog` smoke test against a real point pair
  (no DEM/Processing involved, so no separate real-DEM manual test
  was needed, unlike Phase 8's terrain tools).
  **2026-08-06 follow-up, on request**: (1) a line with an arrowhead
  is now drawn from the from-point to the to-point via two
  `QgsRubberBand`s (`Qgis.GeometryType.Line` for the shaft,
  `Qgis.GeometryType.Polygon` for a small triangular arrowhead) -
  QgsRubberBand's own `IconType` set has no arrowhead shape and
  wouldn't rotate to match the line's direction anyway, so the
  triangle is computed by hand in `_arrowhead_geometry()` and sized
  in screen pixels via `canvas().mapUnitsPerPixel()` rather than a
  fraction of the line's length, so it stays a consistent, legible
  size regardless of zoom or how far apart the two points are, the
  same fixed-pixel-size convention the vertex markers themselves
  already use; (2) From/To now show full-precision (1m) MGRS
  alongside lat/lon, on a second line, reusing `MGRSConverter` the
  same way `CoordinateProbeDialog` already does - `QTableWidget`
  rows don't auto-expand for multi-line cell content, so
  `resizeRowToContents()` is called after populating each new row.
  203 → 229 tests.
- ✅ **Map sheet series / index generation** — batch-generate a numbered
  series of standard print sheets covering a large AO extent: sheet
  boundaries on a regular grid, a naming/numbering convention, and an
  adjoining-sheet diagram on each printed sheet showing its neighbors.
  **Built 2026-08-06.** Turned out to be almost entirely a batch wrapper
  around New Military Layout's own `create_layout()` (Phase 4), exactly
  as scoped.
  - **`layout/map_sheet_series.py`** (new): `compute_sheet_grid()` tiles
    an AO extent edge-to-edge (no overlap) into a grid of sheet centres,
    doing the actual metre-based tiling math in a local UTM zone derived
    from the AO's own centre (`get_utm_crs()`, the same convention every
    other feature needing real-world distances already uses) rather than
    in the AO's own CRS directly, since that may be geographic (degrees,
    not a uniform real-world distance to tile against). Per-sheet ground
    coverage is derived from the *same* map-item-rect geometry
    `create_layout()` itself computes (`_compute_geometry()`,
    `MAP_SIDE_MARGIN`) at the given page size/scale, so generated sheets
    tile exactly edge-to-edge against what each layout actually renders,
    not an approximation. A `MAX_SHEETS = 200` guard raises rather than
    silently generating an impractically large, slow-to-build series
    from an accidental huge-AO/fine-scale combination.
    `generate_sheet_series()` calls `create_layout()` once per sheet at
    that sheet's own computed centre, passing `open_designer=False` (see
    below) and reports a single message-bar summary rather than opening
    a Designer window per sheet.
  - **Minimal, backward-compatible extension to `create_layout()`
    itself** (Phase 4's own function): added `center=None` (an explicit
    centre point, overriding the current canvas extent's own centre -
    every existing caller keeps working unchanged, since omitting it
    preserves the exact prior behaviour) and `open_designer=True`
    (`False` skips the final `iface.openLayoutDesigner()` call).
  - **`layout/map_sheet_series_dialog.py`**: reuses `LayoutFieldsWidget`
    verbatim (the same page size/orientation/scale/heading/
    classification fields New Military Layout's own dialog uses) with
    no separate name field, since every sheet is auto-named: no per-
    feature UI needed beyond what already existed.
  - **2026-08-06, same-day redesign after live testing and further
    discussion - naming and the diagram both reworked to lean entirely
    on the plugin's own existing grid hierarchy, not an invented
    scheme.** The first version named sheets `{GZD}-{row-letter}
    {column-number}` (e.g. `37M-A1`, GZD from the real UTM Grid Zone
    Designator standard, but the row/column suffix invented fresh per
    series) and drew a fixed 3x3 "adjoining sheets" diagram of literal
    neighbouring sheets. User feedback: the row/column suffix was still
    a new numbering system on top of grids the plugin already draws and
    labels (UTM GZD, MGRS 100km squares) - better to describe a sheet's
    position purely in terms of *those*, at whichever level of the
    hierarchy the sheet's own footprint actually needs, and to make that
    "where am I in the grid" description standard on **every** layout
    `create_layout()` produces, not just Map Sheet Series' batch output.
    - **New `layout/grid_position.py`**: `compute_grid_position(extent,
      crs)` picks one of three tiers automatically from how much of the
      grid hierarchy a map's own footprint spans - counted directly from
      geometry, no user input needed. (1) Footprint touches more than
      one GZD cell (a small-scale map) - show a mosaic of real GZD
      labels (e.g. `37M`, `38M`). (2) Footprint fits in one GZD but
      touches more than one 100km square - show a mosaic of real 100km
      square IDs (e.g. `EN`, `FN`) instead. (3) Footprint fits inside a
      single 100km square (a large-scale map, 1:50,000 or finer) - show
      just that one square. Each mosaic is expanded by one cell of
      context margin beyond whatever's actually touched, and reuses
      `mgrs_square_id()`/zone-band boundary math already built for the
      UTM Grid/MGRS 100km grid layers - no new grid math invented, only
      a new way of asking "how many of these does this footprint touch."
      A real edge-case bug caught live before it shipped: naively
      `floor()`-ing an extent's own far edge over-counted a cell exactly
      100km-boundary-aligned as touching one extra column/row it didn't
      actually reach into - fixed by treating cells as half-open
      `[start, start+100km)` (`ceil()` on the far edge instead).
      `grid_label_for_point(lat, lon)` gives the single real
      `(GZD, 100km square)` pair a point falls in, used for sheet naming
      below. Sheet naming is now `{GZD} {100km square} #{N}` (e.g.
      `37M EN #1`) - the `#N` sequence restarts per distinct grid square
      rather than running globally, since a sheet at any normal
      operational scale is almost always much smaller than one 100km
      square, so most series have several sheets legitimately sharing
      one square's name and needing the number purely to tell them
      apart, not to imply an ordering.
    - **`layout/grid_position_diagram.py`** replaces the old
      `layout/sheet_diagram.py`: draws whatever `compute_grid_position()`
      returns as an inset mosaic in the map item's own bottom-left
      corner (mirroring `north_arrow.py`'s own top-right inset
      convention for the opposite corner), with the map's own footprint
      outlined *to scale* on top of the mosaic (a `footprint_fraction`
      the math side computes, not just "which cell is this") - so a
      large-scale sheet that doesn't align to any grid boundary still
      shows exactly where within its square it actually sits, not just
      "somewhere in this cell." Carried over from the first version: the
      live-discovered fix for `QgsPrintLayout.items()` returning plain
      `QGraphicsRectItem` page-background items with no `id()` method,
      guarded with `isinstance(item, QgsLayoutItem)`.
    - **Wired into `new_layout.py`'s shared `_apply_marginalia()`**
      (called by both `create_layout()` and `update_layout()`) rather
      than only Map Sheet Series' own generation path - confirmed live
      that a plain New Military Layout now gets the diagram
      automatically too, and that resizing/rescaling an existing layout
      (`update_layout()`) regenerates it against the new extent
      correctly, same as every other marginalia element already does.
  - 276 tests (up from 249, after replacing the superseded
    designator/diagram tests with `tests/test_grid_position.py` and
    `tests/test_grid_position_diagram.py`); verified end-to-end on both
    QGIS 3.44.12 and 4.2.0 - real tiling math, real layouts registered in
    the Layout Manager, correct tier/mosaic/footprint for hand-picked
    extents at all three tiers, and a plain New Military Layout call
    confirmed to carry the diagram automatically.
- ✅ **GPX/KML waypoint import/export with MGRS labels** — round-trip
  waypoints with GPS units, ATAK, or similar, labeled with MGRS via the
  existing conversion functions. **Built 2026-08-06.** New `waypoints/`
  package (`gpx_kml_io.py` for the read/write + MGRS logic,
  `gpx_kml_dialog.py` for two small one-shot dialogs - Import and
  Export are separate actions, not a combined tab set, matching every
  other feature's one-button-one-dialog convention). QGIS/GDAL already
  read and write both formats natively (the OGR GPX/KML drivers) - no
  file-format parsing was written here, only the MGRS-labelling step
  neither format has any concept of.
  - **Import**: adds a new `mgrs` field to every waypoint, computed
    from its own point geometry, alongside whatever fields the source
    file already had (untouched) - explicit user choice, not the
    alternative of overwriting the existing name/label field.
  - **Export**: sets each waypoint's `name` field to its MGRS grid
    reference (the field a receiving GPS unit/ATAK actually displays),
    with the source layer's own name/label field, if any, preserved as
    a separate description field - also an explicit user choice over
    keeping the original name and adding MGRS as a secondary field.
  - **Real GDAL quirk, confirmed live before writing any code**: the
    description field must be named exactly `desc` for GPX and
    `description` for KML - confirmed by writing test files and
    inspecting the actual XML, since each driver's fixed schema maps
    only that one specific field name to its native `<desc>`/
    `<description>` element; anything else needs `GPX_USE_EXTENSIONS`
    (GPX) or ends up as free-form `ExtendedData` (KML), neither of
    which most consumer GPS units/ATAK render as a visible
    description. Also confirmed live: OGR's KML reader always reports
    the built-in `<name>` element back as a field literally called
    `Name` (capitalised) regardless of what field name was used to
    write it, while GPX's own fixed waypoint schema uses lowercase
    `name` - `_find_label_field()` checks both cases.
  - **Refactor along the way**: `terrain/_layer_utils.py` (the
    "build a layer without inserting it, insert it exactly once"
    helper originally shared by the four terrain/Viewshed dialogs)
    moved to `core/_layer_utils.py`, since nothing about it was
    actually terrain-specific and this feature needed it too -
    `add_layer_at_default_position()` is used for imports (each
    import is a genuinely new file, no "regenerate in place" concept
    the way terrain's own dialogs have). Also caught and fixed in the
    same pass: `package_plugin.sh`'s `INCLUDE` array needed `waypoints`
    added, learning directly from the earlier real bug where `terrain`
    itself was missing there.
  229 → 247 tests; verified round-trip (export then re-import) against
  real GPX and KML files on both QGIS 3.44.12 and 4.2.0, plus a packaged-
  zip extraction check confirming `waypoints/` is actually present this
  time.

**Considered and deferred:** datum transformation support (converting
coordinates under pre-WGS84 datums, for registering legacy paper maps).
QGIS/PROJ already handles the underlying transform; the work would be
exposing it as a clean expression function and confirming the MGRS
engine doesn't silently assume WGS84 where a transform is needed. Real
value depends on actually working with pre-WGS84 source material —
revisit if that need shows up, rather than building speculatively.

**Status: Complete.** Bearing/range tool, GPX/KML import/export, and
map sheet series all done 2026-08-06.

---

## Phase 10 — Tactical graphics (MIL-STD-2525 / APP-6 symbology)

Planned 2026-07-31. The most distinctively *military* addition
remaining — everything built through Phase 7 is base-map/grid
production; this is the operational-graphics layer drawn on top of it
(unit icons, control measures). Deliberately kept separate from Phase
9: this is a new subsystem (symbol library keyed to APP-6/MIL-STD-2525
codes, echelon/affiliation/status modifiers, a placement UI), not an
extension of existing grid/layout code, and is comparable in size to
Phase 8.

- ✅ Unit/formation symbols (affiliation, echelon, status modifiers per
  APP-6 / MIL-STD-2525) — done 2026-08-07 (see sub-phase breakdown
  below). Manual smoke test completed 2026-08-07 (see sub-phase 10.2).
  - **Planned as four sub-phases** (10.1 foundation, 10.2 unit/formation
    point symbols UI, 10.3 control measures, 10.4 AO/NAI area/perimeter
    reporting) after a research-and-verify planning pass, not assumption:
    several symbol-data sources were investigated and ruled in/out on
    their actual merits before committing to an approach.
    - **Esri's `joint-military-symbology-xml`** (raw layered SVG assets,
      Apache-2.0) was the initial direction, but would have needed us to
      hand-build the SIDC-to-asset composition logic ourselves.
    - An existing QGIS plugin, **`qgis_app6d`**, was found - not usable
      directly (GPLv2-only, QGIS 3.16-3.44 only with no confirmed QGIS
      4.x support, points-only) - but it revealed the real working
      pattern: it bundles **milsymbol.js** and renders locally, no
      Node.js, no extra Python packages.
    - **milsymbol.js** (MIT license, actively maintained, single
      dependency-free file, full MIL-STD-2525B/C/D/E + APP-6B/D/E
      coverage) turned out to be a far better foundation than the Esri
      raw-asset approach - its own README explicitly lists "QtJSEngine in
      C++" as a supported integration target.
    - **Verified hands-on before committing, not just researched**:
      `QJSEngine` is confirmed available in both QGIS 3.44.12 (PyQt5) and
      QGIS 4.2.0 (PyQt6)'s bundled Python - the user downloaded milsymbol
      v3.0.4 and it was loaded into `QJSEngine` on both QGIS versions,
      producing correct MIL-STD-2525 SVG output end to end
      (`new ms.Symbol(sidc, {size:35}).asSVG()` → the right affiliation
      colour, frame, `getAnchor()`/`getSize()`). Separately verified: a
      `base64:<svg>` path string works directly with
      `QgsSvgMarkerSymbolLayer`/`QgsSvgCache` (`svgAsImage()` returns a
      valid non-null image) - so a rendered symbol never touches disk.
    - milsymbol has **no line/polygon (tactical graphics) support** -
      confirmed by reading its actual source, not just its docs (`src/`
      has no multipoint/polygon/linestring code at all - a companion
      library, `milgraphics`, attempted this but is archived/incomplete).
      **Control measures (10.3) need hand-curated QGIS-native line/fill
      styling** - a much smaller, tractable problem than unit symbols'
      ~1000+ function-ID combinatorics.
    - **Licensing**: MIT needs no GPL version bump (unlike the Apache-2.0
      Esri path would have) - just a `THIRD_PARTY_NOTICES.md` entry,
      matching the existing MGRS engine/WMM2025 entries.
    - **Interaction model, decided explicitly**: no custom map
      tools/digitizing anywhere in Phase 10. Users place points and draw
      lines/polygons with QGIS's own native "Add Feature" editing toolbar
      (undo/snapping/vertex-editing already exist and work well) - this
      plugin's job is only to pre-configure the layer (fields + styling)
      so a feature's own attributes render the correct symbol
      automatically, never a custom placement tool.
  - **Sub-phase 10.1 (foundation) done 2026-08-07**: `military_symbology/`
    package - `vendor/milsymbol.js` (v3.0.4, MIT, noted in
    `THIRD_PARTY_NOTICES.md`), `sidc.py` (builds a 20-character
    MIL-STD-2525D/APP-6D SIDC from named components - affiliation,
    symbol set, entity, echelon, status, headquarters - with a curated
    starting vocabulary of common ground-unit entities: infantry,
    motorized/mechanized infantry, armor, reconnaissance, field
    artillery, engineer), `symbol_engine.py` (the `QJSEngine` bridge -
    `render_symbol_svg()`/`render_symbol_base64_path()`, both cached per
    SIDC+options combination since QGIS may re-evaluate a feature's style
    expression on every repaint/pan/zoom). Every field position/code in
    `sidc.py` is sourced directly from milsymbol.js's own parsing logic
    (`src/numbersidc/metadata.js`, `src/ms/symbol/getmetadata.js`,
    `src/numbersidc/sidc/landunit.js`'s real function-ID codes) rather
    than recalled from memory, to avoid a subtly-wrong position/digit
    silently producing an incorrect symbol (e.g. a hostile unit rendering
    as friendly) - a real risk this specific domain has zero tolerance
    for. New `expressions/military_symbology_functions.py`'s
    `mct_sidc_svg(sidc)` - the one link between a feature's own
    attributes and its rendered symbol at render time, registered via the
    same `_FUNCTIONS`/`register()`/`unregister()` pattern
    `expressions/mgrs_functions.py` already established, wired into
    `plugin.py`'s `initGui()`/`unload()` the same way. `qgis.PyQt`
    doesn't provide a `QtQml` shim (confirmed live - only the commonly-
    used submodules are aliased there), so `symbol_engine.py` is the one
    module in this plugin importing directly from whichever PyQt binding
    is active (`try: from PyQt5.QtQml import QJSEngine except ImportError:
    from PyQt6.QtQml import QJSEngine` - confirmed this resolves correctly
    on both QGIS versions, mirroring exactly what QGIS's own
    `qgis.PyQt.QtCore` shim does internally). `military_symbology` added
    to `package_plugin.sh`'s `INCLUDE` array from the start, avoiding a
    repeat of the exact bug that once shipped `terrain/` missing from a
    build. 291 → 309 tests (`tests/test_military_symbology_sidc.py`,
    `tests/test_symbol_engine.py`) passing on both QGIS 3.44.12 and 4.2.0.
    No UI yet - sub-phase 10.2 (unit/formation point symbols) is next.
  - **Sub-phase 10.2 (unit/formation point symbols) done 2026-08-07**:
    `military_symbology/unit_layer.py`'s `create_unit_layer()` builds a
    "Tactical Graphics - Units" memory point layer (in the current
    project's own CRS) with `affiliation`/`entity`/`echelon`/`status`/
    `headquarters`/`unique_designation` fields, a `ValueMap` dropdown per
    vocabulary field plus a `CheckBox` for `headquarters`, and sensible
    defaults on every field so a freshly-added point still resolves to a
    valid symbol before it's been touched. The renderer is one
    `QgsSvgMarkerSymbolLayer` whose own path is data-defined via
    `mct_sidc_svg(mct_build_sidc("affiliation","entity","echelon",
    "status","headquarters"))` - confirmed live end to end (a real
    feature's attributes, run through the actual renderer via a
    `QgsExpressionContext`, resolves to a valid `base64:` SVG path) that
    QGIS re-evaluates this per feature at render time, so placing a unit
    is just filling in a plain attribute form, never a separate symbol
    picker. New `mct_build_sidc()` expression function
    (`expressions/military_symbology_functions.py`) calls straight into
    `sidc.py`'s `build_sidc()` rather than re-implementing its
    field-position logic as a QGIS expression, so that logic stays in
    exactly one place.
    - **Scoped down from the plan's own "cascading dropdowns via Value
      Relation" idea, deliberately.** With only one symbol set
      (`ground_unit`) in the vocabulary so far, there's nothing to
      cascade *into* yet - a full Value-Relation-with-backing-lookup-
      layers setup would add real complexity (extra non-data helper
      layers cluttering the project) for no visible benefit at this
      vocabulary size. Plain independent `ValueMap` dropdowns instead;
      revisit cascading once/if a second symbol set actually exists to
      filter entities by.
    - **No dialog** - confirmed during implementation there's nothing to
      configure at layer-creation time (fields/styling are fixed;
      per-unit values are filled in via the attribute form after placing
      each point, not a creation-time choice). The toolbar action calls
      `add_unit_layer(iface)` directly.
    - **Deliberately NOT a `generate_*()`/`replace_named_layer()`
      feature**, unlike every other layer this plugin builds. Those are
      safe to regenerate-in-place because their content is
      algorithmically derived from a DEM/AO/grid; this layer's content is
      hand-placed operational data a user digitizes with QGIS's own
      native "Add Point Feature" tool - silently replacing it on a second
      click would be real data loss, not a convenience. `add_unit_layer()`
      checks for an existing same-named layer first and only warns
      (via the message bar) rather than ever touching it if one exists.
    - `qgis.PyQt` doesn't provide a `QtQml` shim (see sub-phase 10.1
      above); the same import fallback used there applies here too via
      `symbol_engine.py`.
    - New `icons/tactical_graphics_units.svg` (a generic MIL-STD-2525/
      APP-6 unit frame - a plain rectangle with a centre dot and a short
      stem - matching the plugin's existing flat line-art icon style).
    - 309 → 322 tests (`tests/test_unit_layer.py`, including a
      consistency guard that unit_layer.py's own display-label dicts
      cover exactly the same keys as sidc.py's vocabulary, so the two
      can't silently drift apart) passing on both QGIS 3.44.12 and 4.2.0.
    - **Manual smoke test completed 2026-08-07**: created the layer,
      placed points with QGIS's own "Add Point Feature" tool, filled in
      the attribute form - symbols rendered correctly immediately (a
      friendly armor unit and a hostile air-defense-missile unit both
      confirmed against the correct MIL-STD-2525 frame/fill/glyph), no
      issues found on this layer specifically. Issues found during the
      same session's smoke test of control measures and area/perimeter
      reporting are documented under sub-phases 10.3/10.4 above.
  - **2026-08-07, follow-up: broader common-vocabulary pass, requested
    after live testing found real gaps** (e.g. Air Defense units had no
    entity at all). `sidc.py`'s `ENTITIES["ground_unit"]` grew from 7 to
    42 entries, organised by the standard functional-area breakdown
    (command/signal, maneuver, fires, air defense, combat support,
    intelligence/EW, combat service support) - every code sourced
    directly from `landunit.js` the same way as the original seven, not
    recalled from memory. Deliberately still not the full spec:
    `landunit.js` alone has ~140 top-level entities; excluded the more
    peripheral administrative categories (band, postal, religious
    support, and similar) and the civilian law-enforcement-agency
    entries the same symbol set also covers (FBI, DEA, Customs, and
    similar), neither of which read as "military formations" for this
    plugin's purpose. One real terminology clarification surfaced during
    this pass: "Heavy Artillery Gun" isn't itself a distinct SIDC entity
    - the spec's actual distinction is Field Artillery vs. Field
    Artillery, Self-Propelled (now both present); "heavy" would
    conventionally be a text amplifier (e.g. caliber) on the unit's own
    label, not a separate symbol. `unit_layer.py`'s own `_ENTITY_LABELS`
    grown to match exactly (the existing consistency-guard test catches
    any future drift between the two). 338 → 339 tests (one spot-check
    of the new codes, alongside the existing consistency guard which
    already covers the size increase automatically) passing on both
    QGIS 3.44.12 and 4.2.0.

- ✅ Control measures — phase lines, boundaries, axis of advance,
  objectives, named areas of interest (NAIs). Sub-phase 10.3 done
  2026-08-07.
  - **`military_symbology/control_measures.py`**: two layers (a
    `QgsVectorLayer` is always a single geometry type, so one "Lines"
    layer for phase lines/boundaries/axis of advance and one "Areas"
    layer for objectives/NAIs, not one mixed layer), each with a
    `measure_type` `ValueMap` dropdown and a `unique_designation` text
    field, styled via a `QgsRuleBasedRenderer` keyed on `measure_type` -
    mirrors `grid/mgrs_sub_grid.py`'s own existing rule-based renderer
    pattern (`QgsRuleBasedRenderer.Rule(None)` root, one child rule per
    type with its own `setFilterExpression()`). Both layers also get
    basic PAL labelling on `unique_designation` (`Qgis.LabelPlacement.
    Line` for the lines layer, `OverPoint` for areas), since control
    measures are normally labelled on the map, not just drawn.
  - **Honestly flagged as an approximation, unlike sub-phase 10.1's
    point symbols.** `sidc.py`'s SIDC field positions/codes were verified
    exactly against milsymbol.js's own parsing source; no equivalent
    authoritative source exists for tactical graphics lines/areas -
    milsymbol.js's own source has no multipoint/polygon/linestring code
    at all, and the one library that attempted this (`milgraphics`) is
    archived/incomplete (see sub-phase 10.1's own research notes above).
    The styling here (phase line: plain solid line; boundary: a
    dash-dash-dot pattern via `QgsSimpleLineSymbolLayer.
    setCustomDashVector()`; axis of advance: a solid line with a
    `QgsMarkerLineSymbolLayer` arrowhead at `Placement.LastVertex`;
    objective: solid unfilled outline; NAI: dashed unfilled outline via
    `QgsFillSymbol.createSimple({"outline_style": "dash", ...})`) is a
    hand-authored, practically-recognisable rendition of the standard
    conventions, not a verified-correct one - said so plainly in the
    module's own docstring rather than implied to carry the same
    confidence as the point-symbol side of Phase 10.
  - **Same data-safety property as sub-phase 10.2's unit layer, and for
    the same reason**: neither layer is a `generate_*()`/
    `replace_named_layer()` feature. Both layers' content is hand-drawn
    operational data (digitized with QGIS's own native "Add Line/Polygon
    Feature" tools, never a custom drawing tool), so `add_control_
    measures_lines_layer()`/`add_control_measures_areas_layer()` each
    check for an existing same-named layer first and only warn - never
    replace - if one exists.
  - **One toolbar action, not two** - "Tactical Graphics - Control
    Measures" adds both layers in one click (conceptually one feature,
    per this roadmap bullet's own framing), each with its own
    independent already-exists guard, so clicking again with one layer
    already present adds only the missing one and warns about the other.
  - New `icons/control_measures.svg` (a dashed line transitioning into a
    solid arrow, evoking "boundary into axis of advance" - distinct from
    the plain unit-frame icon).
  - 322 → 336 tests (`tests/test_control_measures.py`) passing on both
    QGIS 3.44.12 and 4.2.0.
  - **2026-08-07, manual smoke test follow-up**: user tested against a
    real QGIS session and found the axis-of-advance arrowhead too faint
    to read. Root cause: `QgsMarkerSymbol.createSimple()`'s `"arrowhead"`
    shape has no fillable interior (it's a stroke-only chevron shape),
    so its boldness comes entirely from `outline_width` -
    `createSimple()`'s own default there is `0`, which Qt draws as a
    barely-visible 1-device-pixel cosmetic hairline regardless of zoom.
    `color`/`size` being set had no bearing on this, since there's no
    fill area for them to apply to. Fixed by setting `outline_width`
    (`0.8`, heavier than the 0.5mm line it caps) and `outline_color`
    explicitly in `_axis_of_advance_symbol()`'s `createSimple()` call.
    New `test_axis_of_advance_arrowhead_has_a_visible_outline_width` in
    `tests/test_control_measures.py`, asserting `strokeWidth() > 0` on
    the marker's own symbol layer - guards against this regressing back
    to an invisible default. 339 → 340 tests passing on both QGIS
    3.44.12 and 4.2.0 (this follow-up landed after the vocabulary
    expansion below, same day).
  - **2026-08-07, second follow-up: affiliation-based colouring, per the
    actual standard.** The user provided the official MIL-STD-2525D PDF
    (885 pages) and asked that Phase 10 not be marked complete until it
    had been checked against directly, rather than only against
    milsymbol.js's own interpretation. Reading Appendix H (Control
    Measure Symbols) directly turned up a real, previously-missing
    requirement: **H.5.3 Coloring** - "All friendly control measure
    symbols will be shown in black or blue... Hostile control measure
    symbols shall be shown in red" - and our lines/areas had no
    affiliation concept at all, always plain black. (The same review
    also found the actual specified line/area *shapes* are considerably
    more elaborate than this module's approximation - e.g. NAI is a
    specific hexagon, not "any polygon, dashed outline," and boundaries
    are built from real unit-echelon symbols at their line ends, not a
    dash-dot pattern - tracked as a separate, larger, explicitly
    deferred sub-phase below, since matching those shapes needs custom
    QGIS symbol construction with no rendering library to lean on,
    unlike the point-symbol side. The user chose to fix colouring now
    and defer shapes.) Fixed by adding an `affiliation` field (Friend/
    Hostile/Neutral/Unknown - the same vocabulary as `sidc.py`'s own
    `AFFILIATIONS`, reused directly since MIL-STD-2525D's "Standard
    Identity" is literally the same concept for units and control
    measures) to both Lines and Areas layers, defaulting to Unknown, and
    a shared `_apply_affiliation_color()` helper that makes each measure
    type's own stroke/fill colour data-defined via one CASE expression
    (friend → blue, hostile → red, else → black - scoped down from the
    standard's "black or blue" to exactly this by the user's own
    request, with black doubling as the default) - applied on top of
    each measure type's existing shape/dash/arrowhead styling rather
    than multiplying the rule tree by affiliation, matching
    `unit_layer.py`'s own preference for data-defined properties over
    combinatorial rules. New `TestAffiliationLabelsMatchSidc` (the same
    drift-guard shape as `unit_layer.py`'s own vocabulary-consistency
    test) plus real colour-resolution tests per measure type and
    affiliation in `tests/test_control_measures.py`, verified through
    `QgsProperty.valueAsColor()` against a real
    `layer.createExpressionContext()`, not just string-matching the
    expression. 343 → 348 tests passing on both QGIS 3.44.12 and 4.2.0
    (this follow-up landed after the `@layer`/auto-populate fixes in
    10.4 below, same day - see that entry for why the count jumps to
    343 first).
- ✅ AO/NAI area & perimeter reporting in military units — folded in
  here rather than Phase 9, since it only earns its keep once there are
  polygons (from the above) to report on. Sub-phase 10.4 done 2026-08-07.
  - New `mct_area_km2($geometry, @layer)`/`mct_perimeter_km($geometry,
    @layer)` expression functions
    (`expressions/military_symbology_functions.py`), usable on any
    polygon feature (not just the Areas control-measures layer above -
    any AO/NAI polygon in the project). Both go through
    `QgsDistanceArea` set up exactly like
    `core/coordinate_utils.py`'s existing `true_bearing_and_distance()`
    (`setEllipsoid("WGS84")`, `setSourceCrs(layer.crs(), ...)`) rather
    than QGIS's own native `$area`/`$perimeter` - those return square
    degrees/degrees on a geographic-CRS layer unless the project's own
    Ellipsoidal measurement setting happens to be configured, which
    this plugin's own functions shouldn't depend on to be correct
    (the AO/NAI area layer this phase creates defaults to the current
    project's own CRS, commonly geographic). The `@layer` argument
    (QGIS's own built-in expression variable resolving to the active
    `QgsVectorLayer`) is how the function gets at the geometry's real
    CRS, since a bare `QgsGeometry` carries no CRS of its own -
    confirmed live this resolves correctly inside a real
    `QgsExpressionContext`, not just at the top level.
  - Verified against an independently-computed reference, not a
    self-consistency check: a 0.01°×0.01° box at the equator's
    geodesic area/perimeter (~1.2309 km² / ~4.4379 km) computed once
    directly via `QgsDistanceArea`, then asserted as the expected value
    in `tests/test_area_perimeter_functions.py` - so the test would
    catch a real regression, not just confirm the function agrees with
    itself.
  - 336 → 338 tests passing on both QGIS 3.44.12 and 4.2.0.
  - **2026-08-07, manual smoke test follow-up: `@layer` turned out not
    to be reliably populated.** User reported `mct_area_km2($geometry,
    @layer)` returning `nan` for every feature in QGIS's attribute-table
    in-place field calculator toolbar, while the native `area(@geometry)`
    worked fine on the same features - the project CRS was confirmed to
    be plain EPSG:4326, ruling out a CRS-transform failure (already
    exhaustively tested against WGS84, Web Mercator, UTM, and even
    British National Grid's non-WGS84 datum, all computing correctly
    headless). Root-caused by direct comparison: `layer.
    createExpressionContext()` (the standard API) populates `@layer`
    correctly, but the attribute table's in-place calculator toolbar
    evidently builds its own context without a layer scope - `@layer`
    silently resolves to `NULL`, our function correctly returns Python
    `None` for that, and QGIS's own numeric-preview widget renders a
    `NULL` double-typed field value as literal `"nan"` text. Since
    `$geometry` resolved fine throughout and the failure was 100%
    reproducible across every feature (not data-dependent), `@layer`
    was the one variable not exercised by the working comparison
    expression.
    **Fix**: `mct_area_km2()`/`mct_perimeter_km()` no longer take a
    layer argument at all - `_distance_area()` (renamed from
    `_distance_area_for(layer)`) now uses `QgsProject.instance().crs()`
    directly, a plain Python singleton call with no expression-context
    dependency whatsoever, sidestepping the whole class of "does this
    particular UI populate `@layer`" fragility. Correct for every layer
    this plugin creates itself (both `unit_layer.py` and
    `control_measures.py` build their layers in the project's own CRS);
    documented as the one caveat in both the functions' own docstrings
    and `docs/user-guide.md`. New `mct_length_km($geometry)` added
    alongside (`QgsDistanceArea.measureLength()`, verified against a
    0.01° line at the equator - ~1.1132 km, matching the well-known
    ~111.32 km/degree of longitude there) for the Lines layer's own
    length reporting.
  - **New: auto-populated measurement fields**, addressing a second
    piece of live feedback (why isn't this just filled in automatically
    when you draw the shape?). The Areas layer gained `area_km2`/
    `perimeter_km` fields, the Lines layer gained `length_km` - each
    wired via `QgsDefaultValue(expression, applyOnUpdate=True)` (the
    same "Recalculate value on update" mechanism QGIS's own Fields
    config exposes, already used elsewhere in this plugin for
    `measure_type`'s default, just without `applyOnUpdate` there since
    that field isn't derived). Confirmed live via
    `QgsVectorLayerUtils.createFeature()` (what the GUI's own "Add
    Line/Polygon Feature" tool actually calls to build a new feature,
    unlike calling `addFeature()` directly) that the default applies at
    creation time, and via a geometry-only `updateFeature()`/
    `commitChanges()` edit that it recalculates on reshape, not just
    once at digitizing.
  - 340 → 343 tests (`tests/test_area_perimeter_functions.py`'s new
    length test plus two new integration tests in
    `tests/test_control_measures.py` covering the auto-populate fields
    end to end) passing on both QGIS 3.44.12 and 4.2.0.

**Phase 10 COMPLETE - closed 2026-08-17.** Every appendix is now either
built or explicitly triaged out: A-G, H, J and L built; I (METOC)
decided not needed 2026-08-08 (no milsymbol support, no felt need);
Appendix H, the last and largest, closed 2026-08-16. The flag below
stayed amber for ten days after the appendix work itself was finished,
which is its own small lesson about status markers outliving the thing
they describe. What remains inside this phase is expansion rather than
completion, and is tracked as such: widening the Land Unit/Equipment/
Installation entity vocabularies, and the Land layers' sector 1/2
modifiers. The record of the reopening, kept because the reasoning
still matters:

**Phase 10 was reopened 2026-08-07.** All four
sub-phases (10.1 rendering foundation, 10.2 unit/formation point
symbols, 10.3 control measures, 10.4 area/perimeter reporting) are
built, tested, and documented, and the manual smoke test flagged in
10.2/10.3 has now actually been run in a real QGIS session (place a
unit, digitize control measures, evaluate the area/perimeter/length
expressions) - it found three real issues, all fixed same-day and
documented in place above: the axis-of-advance arrowhead's invisible
default outline width (10.3), `@layer` not reliably populating across
every QGIS expression entry point (10.4), and the request to
auto-populate area/perimeter/length instead of requiring a manual Field
Calculator run (10.4). 291 → 354 tests added across the whole phase so
far (as of sub-phase 10.5 below - the count keeps moving since the
standard-verification pass below is still in progress).

**2026-08-07: the user provided the official MIL-STD-2525D standard**
(PDF, 885 pages) and asked that the phase not be marked complete until
checked against it directly, rather than only against milsymbol.js's own
interpretation or this plugin's own hand-authored approximation. Review
findings and the resulting scope, in the order the user chose to take
them:

1. **Confirmed real gap: Air/Sea/Subsurface units are part of the
   standard, not yet part of this plugin.** The standard's own table of
   contents lists dedicated appendices - C (Air Symbols), E (Sea Surface
   Symbols), F (Subsurface Symbols) - alongside D (Land, the only one
   `sidc.py` currently implements as `"ground_unit"`). Confirmed the
   vendored `milsymbol.js` already renders all of them (its own source
   has `AirFriend`/`SeaFriend`/`SubsurfaceFriend`/etc. as first-class
   dimensions) - this is the same "vocabulary vs. rendering capability"
   situation as the ground-unit entity expansion, not a new rendering
   problem. **Done same-day** - see sub-phase 10.5 below.
2. **Confirmed real gap: control-measure colouring didn't follow the
   standard at all.** Reading Appendix H (Control Measure Symbols)
   directly surfaced H.5.3 Coloring's actual requirement (friendly in
   black or blue, hostile in red) - `control_measures.py` had no
   affiliation concept, always plain black. **Fixed same-day** - see the
   dedicated follow-up entry under sub-phase 10.3 above.
3. **Confirmed the control-measure line/area shapes are a real
   simplification, not just an "approximation" in the abstract.**
   Appendix H's own templates are considerably more specific than what
   this plugin draws - e.g. Named Area of Interest is a specific
   hexagon shape (not "any polygon, dashed outline"), and boundaries are
   built from actual unit-echelon symbols at their line ends with
   perpendicular unit-designation labels (not a plain dash-dot line).
   Control measures also carry their own MIL-STD-2525D numeric codes
   (Symbol Set 25 - e.g. Boundary = 110100, NAI = 120200), which
   `control_measures.py` doesn't currently store or expose at all.
   **Explicitly deferred, by the user's own choice**, to a future,
   smaller sub-phase - rebuilding these shapes needs custom QGIS symbol
   construction with no rendering library to lean on (unlike the
   point-symbol side), a meaningfully larger and different kind of
   effort than steps 1-2 above.

- ✅ **Sub-phase 10.5 - Air/Sea Surface/Subsurface unit symbol sets.**
  Done 2026-08-07, same day as the standard review that surfaced the gap
  (item 1 above).
  - **`sidc.py`**: three new `SYMBOL_SETS` entries - `"air"` = `"01"`,
    `"sea_surface"` = `"30"`, `"subsurface"` = `"35"` - confirmed against
    milsymbol.js's own `dimensionMapping` table
    (`src/numbersidc/metadata.js`), the same sourcing rigor as every
    other code in this module. New curated `ENTITIES` sub-dicts for each
    (19-20 entries apiece - fighters/bombers/transports/helicopters for
    Air, destroyers/frigates/carriers/landing craft for Sea Surface,
    submarine variants for Subsurface), every code read directly from
    milsymbol-3.0.4's own `src/numbersidc/sidc/air.js`/`sea.js`/
    `subsurface.js`, not guessed. All six spot-checked combinations
    rendered as valid SVG through the real `QJSEngine`/milsymbol.js
    pipeline before being wired into the UI at all.
  - **Two real key collisions found and fixed during this pass**, not
    just avoided by luck: `sidc.py`'s combined vocabulary check (every
    entity key across all four symbol sets, since `unit_layer.py`'s
    "Entity" dropdown is one flat list spanning all of them - see
    below) found `ground_unit`'s own `"reconnaissance"` colliding with
    an unrelated Air entity, and `ground_unit`'s own
    `"electronic_warfare"` colliding with an unrelated Air one (airborne
    jammer/ECM) - both would have silently overwritten the
    already-shipped `ground_unit` entry in the combined dropdown's
    underlying dict, a real data-loss-in-the-UI bug caught by actually
    computing the union programmatically rather than eyeballing four
    separate lists. Fixed by renaming the Air-specific ones to
    `air_reconnaissance`/`airborne_electronic_warfare` in `sidc.py`
    itself (the two are unrelated codes in unrelated symbol sets - a
    UI-clarity rename only, `ground_unit`'s own two keys are unchanged
    for backward compatibility with already-saved projects). One
    remaining 3-way share (`"military"`, generic, in Air/Sea
    Surface/Subsurface) is benign - all three map to the identical
    function code `"110000"`, so picking any of the three
    domain-labelled options is correct paired with any of those three
    `symbol_set` values.
  - **`expressions/military_symbology_functions.py`**: `mct_build_sidc()`
    grew a `symbol_set` parameter (now 6 values, not 5 -
    `affiliation, entity, symbol_set, echelon, status, headquarters`,
    matching `build_sidc()`'s own argument order) - an internal-only
    change, since `unit_layer.py`'s own generated expression string is
    the sole caller anywhere in this codebase.
  - **`unit_layer.py`**: new `symbol_set` field (ValueMap: Ground
    Unit/Air/Sea Surface/Subsurface, defaulting to `ground_unit` -
    unchanged behaviour for anyone already using the layer). "Entity"
    stayed a single flat ValueMap dropdown rather than becoming a
    cascading `symbol_set` -> `entity` Value Relation (a real cascading
    setup needs backing lookup layers and is more complexity than
    today's UI needs - explicitly flagged as the thing to revisit if
    this combined list gets unwieldy, matching the existing note this
    module already had about growing the vocabulary) - each entity's
    label is now prefixed with its domain (e.g. "Air - Fighter",
    "Ground Unit - Infantry" - the latter relabelled too, for scanning
    consistency now that multiple domains share one dropdown; the
    stored value string is unchanged, so this doesn't affect existing
    saved data). Correctness of a chosen `entity` still depends on
    `symbol_set` being set to match - `mct_build_sidc()` already surfaces
    a clear error string rather than silently rendering the wrong thing
    if they don't agree, the same contract as an unrecognised entity has
    always had.
  - New `test_air_sea_surface_subsurface_symbol_sets` in
    `tests/test_military_symbology_sidc.py` (spot-checks real codes for
    all three new sets); `tests/test_unit_layer.py`'s consistency-guard
    test extended to check every symbol set's entity labels against
    `sidc.py`'s own `ENTITIES` (not just `ground_unit`'s), plus a new
    `test_symbol_set_labels_cover_every_sidc_symbol_set` and a
    `test_a_non_ground_unit_symbol_set_resolves_to_a_valid_symbol_path`
    integration test (an Air Fighter resolving to a real rendered
    `base64:` SVG path end to end, mirroring the existing ground_unit
    version of the same test). 348 → 351 tests passing on both QGIS
    3.44.12 and 4.2.0.
  - **2026-08-07, follow-up from live testing: Entity wasn't actually
    restricted by Symbol Set.** The combined dropdown above let you
    pick e.g. Symbol Set = Ground Unit with Entity = Fighter (an Air
    entity) - correctness depended entirely on the user picking a
    matching pair by hand, `mct_build_sidc()` only caught the mismatch
    as an error string after the fact. Fixed with the real QGIS
    mechanism for this: a small hidden `NoGeometry` reference layer
    (`ENTITY_LOOKUP_LAYER_NAME`, one row per `(symbol_set, entity,
    label)`, registered in the project with `addToLegend=False` so it
    never appears in the Layers panel) backing a `ValueRelation` widget
    on "Entity", filtered via `FilterExpression: "symbol_set" =
    current_value('symbol_set')` - QGIS's standard, documented way to
    build a dropdown whose options depend on a sibling field's current
    value. `create_unit_layer()`'s own "never touches the project" rule
    (see this module's docstring) now has one narrow, explicit
    exception for this lookup layer, since it holds no user data and is
    safe to always rebuild - the Units layer itself is still never
    added.
  - **A real crash was found and is flagged plainly, not hidden**:
    `current_value()` inside a `ValueRelation` `FilterExpression`
    caused a native crash every time it was exercised directly through
    `QgsValueRelationFieldFormatter.createCache()` during development -
    reproduced repeatedly, including with a real layer-backed feature,
    not just a synthetic one (`exit code 139`/SIGSEGV). This is
    nonetheless the standard, widely-documented QGIS pattern for
    cascading dropdowns and is expected to work correctly through the
    real interactive attribute form (which sets up expression-context
    scope this direct low-level API call may not) - but that could not
    be verified without a live QGIS session, since this plugin's test
    harness can only drive the API layer, not a real form UI. **User's
    own call, after being shown this finding**: ship it and smoke-test
    live; if it proves unstable in practice, the documented fallback is
    a field constraint expression instead (validates the "entity"/
    "symbol_set" combination on save rather than filtering the dropdown
    live - an ordinary per-feature expression with no `current_value()`
    dependency, so it doesn't share this risk). **Confirmed safe
    2026-08-07**: user smoke-tested the real interactive attribute form
    live - the cascading dropdown works correctly, no crash. The
    createCache()-level crash found during development is specific to
    calling that low-level API directly outside a real form (as
    suspected above), not a problem with the shipped feature itself.
  - **Echelon clarified, not restricted, per the user's own choice**:
    reading MIL-STD-2525D Appendix A's own Table A-VI (Echelon/
    Mobility/Towed Array Amplifier) directly confirmed the "echelon"
    field is a Land/organizational-unit concept (Team/Crew through
    Command) - it doesn't apply to individual platforms the way the new
    Air/Sea Surface/Subsurface entities are (a single Fighter or
    Destroyer isn't a "battalion"). The standard's real equivalent for
    platforms is a completely different "mobility" vocabulary (modes
    3-6 of the same field: wheeled/tracked/towed/amphibious/naval towed
    array) that this plugin doesn't expose. Documented in
    `docs/user-guide.md` as a "leave Unspecified for non-Ground-Unit
    entities" note rather than restricted/hidden in the form itself, to
    avoid the same `current_value()`-adjacent risk found above for no
    strong benefit.
  - New `test_entity_field_uses_a_cascading_value_relation_widget`
    (widget config structure only, not the live cascading behaviour
    itself - see the crash note above for why),
    `test_entity_lookup_layer_is_hidden_from_the_legend`, and
    `test_entity_lookup_layer_has_one_row_per_entity` in
    `tests/test_unit_layer.py`. 351 → 354 tests passing on both QGIS
    3.44.12 and 4.2.0.

**2026-08-07, later the same day: broader scope review.** After the
standard-verification pass above, the user asked directly whether there's
still a lot more of MIL-STD-2525D left uncovered beyond unit/formation
symbols - tactical-task graphics (BLOCK/DISRUPT/etc.) and equipment icons
were named as examples. Cross-referencing the standard's own table of
contents against the vendored `milsymbol.js`'s actual (unminified) source
tree confirmed: yes, substantially more, now concretely scoped rather than
left as a vague "more to do":

- **Already rendered by milsymbol.js, purely a vocabulary gap on our
  side** (same shape of work as sub-phase 10.5 above): Appendix D.7-D.9
  (Land Civilian/Equipment/Installation - `landcivilian.js`/
  `landequipment.js`/`landinstallation.js`), Appendix F.7 (Mine Warfare,
  a subsection of Subsurface our existing `"subsurface"` set doesn't yet
  cover), Appendix G (Activities - `activites.js`), Appendix H's own
  **point**-type control measures (`control-measure.js`, symbol set
  `"25"` - see sub-phase 10.6 below, the first of these tackled),
  Appendix J (SIGINT), Appendix L (Cyberspace), Appendix B (Space -
  probably not relevant to this plugin's field-mapping use case).
- **No milsymbol.js support at all - hand-authored QGIS symbology is the
  only option**, same category as the already-deferred control-measure
  shape rebuild: Appendix H's **line/area** control measures beyond the 5
  already built (H.5.5, H.5.7-9, H.5.11-18, H.5.21-23, H.5.26-27) -
  confirmed by reading milsymbol's actual source, there is no
  MultiPoint/polygon/linestring rendering code anywhere in it. This is
  where Mission Task graphics (BLOCK/BREACH/CANALIZE/DISRUPT/etc., H.5.26)
  actually live - not a separate feature from the deferred shape-rebuild
  work, but a large expansion of its scope once looked at directly
  (H.5.11-27 alone span ~230 pages of the standard).
- **Appendix I (METOC)** has no milsymbol.js support either, and unlike
  every other gap above, no rendering library to lean on for it at all -
  a bigger, standalone lift nobody has scoped yet.

Decided with the user: start with the biggest already-unused asset
(Appendix H's point control measures, 733 lines of working milsymbol.js
code sitting entirely unreferenced - sub-phase 10.6 below), continue
in-session rather than handing this off (the design judgment calls
involved, like the coloring investigation below, benefit from staying
interactive). Separately, the user asked to hand the line/area Mission
Task/Maneuver expansion specifically to a background agent working in an
isolated git worktree, given its size and that it doesn't depend on
what sub-phase 10.6 touches - that work was still in progress as of this
writing and will get its own roadmap entry once reviewed, merged, and
tested, not claimed as done here.

- ✅ **Sub-phase 10.6 - Control-measure point symbols (Appendix H, symbol
  set `"25"`).** Done 2026-08-07.
  - **Coloring came free, no extra code needed** - the open question
    going in was whether milsymbol.js's control-measure points would
    render with the standard 4-colour unit scheme (friend=cyan,
    hostile=red, neutral=green, unknown=yellow) or something else, since
    H.5.3 requires control measures specifically to use only
    black/blue (friendly) and red (hostile). Rendered real control-measure
    SIDCs (checkpoint, decision point, contact point) across all four
    affiliations through the actual `QJSEngine`/milsymbol.js pipeline and
    inspected the raw SVG directly: friend/neutral/unknown all came back
    `stroke="black"`, hostile came back `stroke="rgb(255, 0, 0)"` -
    already exactly H.5.3-compliant, with zero color-override code needed
    (unlike `control_measures.py`'s hand-built lines/areas, which had to
    implement H.5.3 themselves via a data-defined colour expression).
    Turned into a permanent regression test
    (`TestControlMeasurePointColouring` in the new test file below) so
    this doesn't silently regress on a future milsymbol.js upgrade.
  - **`sidc.py`**: new `SYMBOL_SETS["control_measure"] = "25"`, and a
    curated ~80-entry `ENTITIES["control_measure"]` sub-dict, sourced
    directly from milsymbol-3.0.4's own
    `src/numbersidc/sidc/control-measure.js` (~260 entries total).
    Deliberately excludes the ~110-entry Maritime Control Points category
    almost entirely (deeply Navy/ASW-specific jargon - sonobuoy types,
    acoustic fix types - not general operational mapping, mirroring why
    `ground_unit`'s own curation already excludes band/postal/religious
    support) and the granular per-nation/per-class supply point variants
    (NATO/US Class I-X, 16 entries, kept to two generic ones instead) -
    same "curated common vocabulary, growable later" approach as every
    other symbol set in this module.
  - **New `military_symbology/control_measure_points.py`** - a new point
    layer ("Tactical Graphics - Control Measure Points"), same
    data-defined-SVG-marker rendering mechanism as `unit_layer.py`, but
    deliberately simpler: no "Symbol Set" field (this layer only ever
    draws from the one `"control_measure"` set, so "Entity" is a plain
    `ValueMap` dropdown, not a cascading `ValueRelation` - sidesteps that
    mechanism's own crash-risk caveat entirely by not needing it), and no
    "Echelon"/"Headquarters" fields (not listed among H.5.1.1's
    control-measure amplifiers, unlike "Status", which is kept - a
    proposed vs. active checkpoint is a real distinction). Bundled into
    the existing "Tactical Graphics - Control Measures" toolbar action
    alongside the lines/areas layers (one click now adds three layers,
    not two) rather than a new toolbar icon.
  - New `tests/test_control_measure_points.py` (vocabulary-consistency
    guards, field/widget structure, a real-feature-to-valid-SVG
    integration test, and the affiliation-colouring regression test
    above) and a new spot-check in
    `tests/test_military_symbology_sidc.py`. `tests/test_unit_layer.py`'s
    own consistency guards updated to explicitly exclude
    `"control_measure"` from the Units layer's own symbol-set/entity
    checks, since it's a separate layer, not a fifth unit domain. 368
    tests passing on both QGIS 3.44.12 and 4.2.0.
  - **Confirmed safe 2026-08-07**: user live-smoke-tested in a real QGIS
    session (toolbar action adds all three layers correctly, Entity
    dropdown populates and reads cleanly, a placed point renders
    immediately, friend vs. hostile colouring differs on the map as
    expected) - no crash, no issue found.

- ✅ **Sub-phase 10.7 - Maneuver/Defensive/Offensive control measures
  (H.5.11-H.5.14) and Mission Task symbols (H.5.26).** Done 2026-08-07,
  built by a background worktree agent while sub-phase 10.6 above was
  being built in-session, reading the actual MIL-STD-2525D PDF's own
  anchor-point/draw-rule text for each measure type (not milsymbol.js,
  which has no tactical-graphics coverage at all - see sub-phase 10.3
  above) before approximating, the same standard-first discipline as this
  phase's earlier passes.
  - **From H.5.11-H.5.14** (`military_symbology/control_measures.py`),
    added to the Lines layer: `forward_line_of_troops` (FLOT, 140100),
    `line_of_contact` (140200), `forward_edge_of_battle_area` (FEBA,
    140400), `principal_direction_of_fire` (PDF, 140500), and
    `direction_of_attack` (H.5.13.2, 140600 - explicitly requested, since
    axis_of_advance already covered H.5.13.1 but not this). Added to the
    Areas layer: `battle_position` (151200), `strong_point` (151203),
    `engagement_area` (151300), `assembly_area` (150200), and
    `encirclement` (151800).
  - **From H.5.26**, added to the Lines layer:
    `block`/`breach`/`canalize`/`disrupt`/`fix`/`penetrate`/`delay`/
    `withdraw` (plain arrow/tick-based approximations) plus
    `isolate`/`secure`/`seize` (a centre+radius circle generated from a
    2-point line via a new `QgsGeometryGeneratorSymbolLayer` technique -
    see below). `retain` was also added using that same circle technique,
    but turned out on reading the standard's own text to actually be a
    H.5.12.1 Defensive maneuver control measure (code 151205), not a
    Mission Task at all, despite being requested alongside them - kept in
    this sub-phase anyway since it shares the exact circle shape, and
    documented plainly in `control_measures.py`'s own docstring/
    `_retain_symbol()` comment rather than silently miscategorized.
  - **Two new approximation techniques**, reused across several measure
    types rather than one-off per type: a "tick mark" (a stroke-only
    "line"-shape marker rotated 90 degrees on top of a marker line's own
    tangent rotation, standing perpendicular to the line it's placed on -
    Block's cross-bar, Strong Point's fortification ticks, Disrupt's
    ladder, Penetrate's perpendicular arrow), and a "circle from a line"
    (`QgsGeometryGeneratorSymbolLayer` computing
    `buffer(start_point($geometry), length($geometry))` - a circle
    centred on a 2-point line's first vertex with the line's own length
    as radius, for Isolate/Secure/Seize/Retain, all defined by the
    standard as exactly this centre+radius shape; the standard's own
    30-degree opening arc is rendered as a full closed circle instead,
    since QGIS has no simple "arc with a gap" primitive to build on).
  - **Confirmed real findings from reading the standard directly, not
    assumed from a task name**: "Disengage" (one of the tasks originally
    asked for) does not appear anywhere in MIL-STD-2525D at all - text-
    searched the entire 885-page PDF, not just Appendix H - so nothing
    was built under that name rather than invent a mapping the standard
    doesn't make. "Contain" (also asked for) IS in the standard, but as a
    Defensive maneuver control measure (H.5.12.1, code 151204) with a
    real semicircle-plus-arrow geometry, not a Mission Task - deferred
    rather than rushed, alongside the rest of the exact-shape work
    sub-phase 10.3 already deferred (NAI's real hexagon, boundary's
    echelon-symbol line ends). Observation Post (H.5.12.2) and the
    Mission Tasks Destroy/Interdict/Neutralize are all genuinely
    single-anchor-point STATIC symbols per the standard's own text, not
    lines or areas - out of scope for this module's Lines/Areas layers;
    a Points-type control-measures layer for exactly these three-plus-OP
    (still native QGIS markers, not the sidc.py/symbol_engine.py pipeline
    sub-phase 10.6 uses) is a separate design decision left for a future
    sub-phase. The rest of Appendix H's tactical graphics (H.5.15-H.5.25,
    H.5.27 onward, plus every H.5.11-H.5.14/H.5.26 entry not named above
    - Assault/Attack Position, Bypass, Clear, Counterattack, the
    Drop/Extraction/Landing/Pickup Zones, Infiltration Lane, Limit of
    Advance, Line of Departure, Occupy, Probable Line of Deployment,
    Relief in Place, Retire/Retirement, Withdraw Under Pressure, and the
    friendly/enemy/planned-or-on-order sub-variants of nearly every
    entry) was intentionally not attempted - this sub-phase covers the
    sections and named tasks actually requested, not the whole of
    Appendix H.
  - New tests in `tests/test_control_measures.py` for every new
    measure_type (symbol-layer-type/placement assertions per type, plus
    the existing generic affiliation-colour and rule-tree-registration
    tests, which already cover every measure_type in
    `LINE_MEASURE_TYPE_LABELS`/`AREA_MEASURE_TYPE_LABELS` generically and
    so automatically extended to cover all of these too). 354 → 374
    tests added by this sub-phase; 388 tests passing overall on both
    QGIS 3.44.12 and 4.2.0 once combined with sub-phase 10.6 above (the
    two were built independently in parallel with no file overlap, then
    merged - verified by re-running the full suite after merging, not
    just trusting each piece's own count). One more regression test
    added during the render-based cross-check below brings the total to
    389.
  - **Cross-checked against actual rendered output 2026-08-07**, the same
    "verify the real render, not just the code" standard this module's
    own tests already hold themselves to: every new measure_type was
    rendered offscreen via `QgsMapRendererCustomPainterJob` (no live QGIS
    session needed for this pass) and visually compared against the
    standard's own anchor-point rules. `principal_direction_of_fire`'s
    two arrows were confirmed correct (both point away from the shared
    vertex, not back into it). Two real bugs were found this way and
    fixed:
    - **`_tick_marker_symbol()`'s perpendicular tick was rendering
      parallel to the line instead** - confirmed by rendering it against
      a genuinely diagonal (non-axis-aligned) test line, where the
      mistake is visually unambiguous (a purely horizontal/vertical test
      line can't tell "rotated 90 degrees" apart from "not rotated at
      all", which is how this slipped past the original build). The
      earlier code added an extra 90 degrees on top of
      `QgsMarkerLineSymbolLayer`'s own tangent-following rotation, on the
      mistaken assumption that a "line"-shape marker's neutral pose is
      parallel to the line; it's actually already perpendicular once
      auto-rotated, at every placement type tested (CentralPoint,
      Interval, FirstVertex, LastVertex). This fully hid the tick inside
      the base line's own stroke for Block, Breach, Canalize, Disrupt,
      and Strong Point. Fixed by dropping the extra rotation (angle 90 ->
      0) and, since even correctly oriented the original 3mm/0.5mm size
      proved too faint to read reliably, bumping the tick's default size
      to 5mm/0.9mm.
    - **Seize's circle radius was inflated by its own arrow point** -
      `_circle_from_line_symbol()`'s geometry generator used
      `length($geometry)` as the radius, which sums every segment of the
      line. Isolate/Secure/Retain only ever use a 2-point line so this
      was invisible there, but Seize's own standard definition adds a 3rd
      point for its arrow (H.5.26, "point 4 defines the end of the
      arrow"), and summing both segments roughly doubled the circle's
      size the moment that 3rd point was added - confirmed by rendering
      the 2-point and 3-point forms side by side. Fixed by taking the
      radius from the centre-to-2nd-vertex distance only
      (`distance(start_point($geometry), point_n($geometry, 2))`),
      regardless of how many further vertices follow. A new regression
      test (`test_seize_radius_is_not_inflated_by_the_arrow_point`)
      locks this in by evaluating the real geometry expression against
      both a 2-point and 3-point line and asserting equal area. 388 → 389
      tests, passing on both QGIS 3.44.12 and 4.2.0.
  - **A third, more fundamental bug found by the project maintainer
    2026-08-07**, comparing a real render against the standard's own
    template diagram directly (not just its text): Block was rendering
    as a 2-point line with a small FIXED-size decorative tick at its
    centre, when the standard's own Block template requires a genuine
    **3-anchor-point** shape - points 1/2 define the vertical line,
    point 3 is an independent anchor whose distance from that line
    defines the horizontal line's own real length (the template diagram
    shows point 3 placed far away, not adjacent to the vertical line).
    The earlier code's own comment claimed the fixed-tick approach
    "match[ed] the standard's own placement exactly" - it matched the
    *midpoint* placement but silently dropped point 3 entirely, which
    only became obvious by looking at the template's picture, not its
    prose. Penetrate shares the exact same construction (its own code
    comment already said so) and had the identical bug. Both rebuilt
    using two `QgsGeometryGeneratorSymbolLayer`s that reconstruct the
    real shape from the 3 raw digitized vertices - one draws P1-P2
    verbatim, the other draws a line from P3 to the midpoint of P1-P2
    (`centroid(make_line(point_n($geometry,1), point_n($geometry,2)))`),
    with Penetrate's version ending in an arrowhead at the midpoint end
    (point 3 is "the rear of the symbol" per the standard - the arrow's
    tail - so it points from P3 INTO the vertical line, matching what
    "penetrate" means). Verified by evaluating both expressions against
    a real 3-vertex feature and rendering the result side by side with
    the template diagram - both new tests check the actual reconstructed
    geometry, not just that some symbol-layer structure exists. Requires
    a real 3-vertex digitized line for Block/Penetrate now, not 2 - with
    only 2 vertices, `point_n($geometry, 3)` resolves to NULL and the
    horizontal line/arrow simply doesn't render, degrading to a plain
    P1-P2 line rather than erroring.
  - **Still not live-smoke-tested in a real interactive QGIS session** -
    the offscreen-render cross-check above is a strong signal (it's what
    actually caught all three bugs above) but isn't a full substitute;
    every remaining tick/circle approximation's on-screen legibility at
    ordinary map zoom, and the attribute-form/digitizing workflow itself
    (including whether a 3-vertex line is easy enough to digitize for
    Block/Penetrate/principal_direction_of_fire in practice), are still
    left for the project maintainer's own interactive pass.
  - **A staged completion plan adopted 2026-08-07** for all of the
    standard's remaining, much larger scope (~190 more Appendix H pages
    alone, plus several whole point-symbol domains milsymbol.js already
    renders) - go through Appendix H strictly in the standard's own
    section order (H.5.15 onward) before touching any other appendix, and
    for every symbol check the actual template PICTURE (not just
    extracted text) before writing code, reusing established construction
    techniques first. Full plan at
    `/Users/kpr/.claude/plans/structured-moseying-shell.md`.
  - **Stage A of that plan (closing out 10.7's own bugs) completed
    2026-08-07**, found entirely by finally checking template PICTURES
    instead of text for symbols already marked "done" above:
    - **FLOT/Line of Contact**: the standard draws these as a real
      wavy/serpentine line, not the plain straight line this module had.
      New shared `_wavy_line_layers()` helper - two `QgsMarkerLineSymbolLayer`
      "half_arc" markers, offset by half their own interval and rotated
      180 degrees from each other, producing one continuous wave.
    - **Delay/Withdraw/Fix**: "point 1 defines the tip of the arrowhead"
      - the opposite of this module's own default arrow-line convention
      (last vertex = tip). `_arrow_line_symbol()` gained a
      `tip_at_first_vertex` parameter for this.
    - **Seize**: the standard defines two genuinely different point
      recipes (3-point: point 2 = arrowhead tip directly; 4-point: point
      2 = radius, point 4 = arrow end) that an earlier version conflated,
      appending an arrow at whatever the raw digitized line's last vertex
      happened to be. Now only the 4-point recipe is implemented
      explicitly (point 2 to point 4); with fewer points, only the plain
      circle renders.
    - **Breach/Canalize**: confirmed identical shapes (compared their two
      template pictures side by side) - a real open bracket/"C", not the
      2-point-dashed-line-plus-tick approximation this module had. New
      shared `_bracket_symbol()` reconstructs the true 5-point path (P1 ->
      rear-top -> P3 -> rear-bottom -> P2) via `with_variable()` +
      `project()` + `azimuth()`, the first use of vector-projection
      expressions in this module.
    - **Retain**: the template shows the circle bristling with
      perpendicular tick marks all around it (matching Strong Point's own
      convention), not a "dash dot" outline. `_circle_from_line_symbol()`
      gained a `with_ticks` parameter for this.
    - **Engagement Area, Assembly Area**: both are plain SOLID outlines in
      their own template pictures ("Friendly Present" status) - an
      earlier version invented dash-dot/dash-dot-dot styles purely to
      keep every area type visually distinct from every other on screen,
      which the standard doesn't actually do (it reserves dash style for
      a Present-vs-Planned STATUS distinction this layer has no field
      for, not for telling area TYPES apart).
    - **FEBA**: checked and confirmed to have NO bug at all - its
      template's small triangular "hump" (PT1/PT3 baseline, PT2 a peak)
      is simply the raw 3-vertex digitized path, the same
      "additional points extend the line" convention Phase Line/FLOT
      already support. No code changed, only the comment clarified - a
      reminder that this same picture-checking discipline also proves
      some suspected bugs aren't bugs at all.
    - Block, Penetrate, Battle Position, Strong Point, Direction of
      Attack, Isolate/Secure's point-2-is-radius handling, and
      Canalize/Breach's now-shared construction were all re-confirmed
      correct against their own template pictures in the same pass.
    - 388 -> 398 tests, all checking actual evaluated geometry/rendered
      structure per the standing methodology, not just that some
      symbol-layer type exists. Passing on both QGIS 3.44.12 and 4.2.0.
  - **Bigger findings from the same picture-checking pass, NOT yet fixed,
    scope decision pending**: Encirclement's own template (page 440)
    shows a spiky "sun/gear" boundary (outward-pointing triangular teeth
    all around a closed area), not the dotted oval this module has.
    Isolate's template (page 646) shows the exact same spiky treatment
    applied to its generated circle, not a plain dashed circle. Secure
    likely shares it too (not yet confirmed). Seize's real shape (page
    653) is a circle plus a smoothly CURVED arrow (a genuine arc, closer
    to a boomerang than a straight line) - substantially more elaborate
    than the circle-plus-straight-arrow already built. All three need a
    new "spiky boundary" technique and/or real curve-drawing support
    QGIS doesn't have a simple built-in for, a bigger lift than anything
    else fixed in this pass - left for a deliberate follow-up rather than
    folded in here.
  - **Phase 10 remains open** - this sub-phase is additive, not a
    closing pass; the deferred items above (exact shapes from sub-phase
    10.3, Contain, a Points-type layer for Observation Post/Destroy/
    Interdict/Neutralize, and the rest of Appendix H's sections) are all
    still open.
  - **2026-08-08, plan rewind: appendix-by-appendix completion plan,
    replacing the prior stage-based (A-E) plan.** The user went through
    the standard directly against the live plugin and found the previous
    plan's scope was still too narrow in two ways: (1) point symbols have
    real bugs too, not just control-measure lines/areas - e.g.
    `sidc.py`'s `ENTITIES["subsurface"]` lists a `"military"` generic
    entity that doesn't actually render correctly for Subsurface even
    though the identical code renders fine for Air/Sea Surface (copied
    across symbol sets without checking milsymbol.js's own
    `subsurface.js` specifically); (2) the "Stage A" pass's own
    "re-confirmed correct" list (Block, Penetrate, Direction of Attack,
    Isolate/Secure, Canalize/Breach and others) still has real
    unaddressed defects per the user's own detailed read-through (missing
    echelon symbols on Boundary, missing B/C letters and slash-marks on
    Breach/Canalize, missing D label and curved arc on Delay, an
    incomplete Direction of Attack variant set, Disrupt/Fix each
    conflating an obstacle-control-measure SIDC with an unrelated
    mission-task SIDC, and more). New plan at
    `/Users/kpr/.claude/plans/delightful-wishing-whale.md`: go through
    the standard in its own document order, appendix by appendix
    (A through L, skipping K which isn't a symbol set), each with its own
    dedicated plugin layer + icon, each checked against the standard's
    real template pictures (not just extracted text or milsymbol.js's own
    interpretation) before being called correct, each its own stop/test/
    check-in point. Appendix H (control measures, by far the largest) is
    further split at the standard's own H.5.x section boundaries. The
    full 885-page standard is now available locally at
    `reference/MIL-STD-2525D.pdf` (gitignored - copyrighted reference
    material, confirmed internal PDF page = printed page + 16).
    - **Mini-Phase A (SIDC structure, Appendix A) audited, no changes
      needed.** Cross-checked `sidc.py`'s `AFFILIATIONS`, `STATUS`,
      `HEADQUARTERS_CODE`/`NO_HEADQUARTERS_CODE`, `ECHELONS` and
      `SYMBOL_SETS` directly against the standard's own Tables A-II,
      A-IV, A-V, A-VI and A-III (not just against milsymbol.js) -
      every code matches exactly. Confirms sub-phase 10.1's original,
      more careful construction of this module (vs. the vocabulary
      dicts added in later follow-ups) holds up under direct
      standard cross-checking.
    - **Mini-Phase B (Appendix B, Space) done 2026-08-08.** New
      `military_symbology/_point_symbol_layer.py` - a shared, reusable
      factory for a single-symbol-set "Tactical Graphics - <Domain>"
      point layer, factored out of `unit_layer.py`'s own pattern. This
      resolves the "each appendix is its own layer" architecture
      question the plan flagged: rather than every domain sharing one
      layer with a cascading symbol_set/entity dropdown (today's
      `unit_layer.py` still does this for ground_unit/air/sea_surface/
      subsurface, untouched for now - it'll be split domain-by-domain
      when Appendices C/D/E/F reach their own mini-phases, not all at
      once), a single-domain layer bakes its one SIDC `symbol_set` in as
      a literal in the renderer expression and only needs a plain
      `ValueMap` entity dropdown, no lookup layer or `current_value()`
      cascading. `_point_symbol_layer.py` also supports a small
      `entity_symbol_set_overrides` escape hatch - a handful of entities
      that resolve to a different SIDC symbol_set than the layer's own
      default, via a `CASE` expression on the feature's "entity" value
      rather than a whole second layer. New
      `military_symbology/space_layer.py` builds one "Tactical Graphics
      - Space" layer under one new toolbar action/icon
      (`icons/tactical_graphics_space.svg`) covering both of Appendix
      B's sections - B.6 Space Equipment/Platform (symbol set `05`) and
      B.7 Space Missile (symbol set `06`) - folding Space Missile's
      single entity into the same layer's entity dropdown via that
      override mechanism instead of a whole second layer for one entity
      (revised after the user pointed out two layers was overkill for a
      single-entity domain). `sidc.py` gained `ENTITIES["space"]` (36
      entities) and `ENTITIES["space_missile"]` (1 entity - modifiers
      for missile type/range aren't exposed for any symbol set yet, a
      pre-existing scope limit, not new to Space) - sourced from
      milsymbol-3.0.4's own `space.js`/`spacemissile.js`, then
      cross-checked entity-by-entity against the standard's own Table
      B-III text directly (not just trusted from milsymbol.js),
      confirming the codes align. Unlike `ground_unit`'s curated subset,
      nothing was excluded here - Space's full vocabulary is small
      enough and none of it reads as peripheral/administrative. 409
      tests (`tests/test_space_layer.py`) passing on both QGIS 3.44.12
      and 4.2.0, including an integration test that a real feature
      (both a plain Space entity and the overridden "missile" entity)
      resolves to a valid `base64:` SVG path through the actual renderer
      (the same check sub-phase 10.2 used to
      confirm the QJSEngine/milsymbol pipeline end to end - not yet
      exercised with symbol sets `05`/`06` before this).
    - **Same-day follow-up: echelon/headquarters are now opt-in, not
      automatic.** User asked why the Space layer had an Echelon/
      Headquarters Staff Indicator field at all, since re-checking
      Appendix B's own Table B-II (already read this session) confirms
      it lists neither field for space symbols. `_point_symbol_layer.py`
      gained `include_echelon`/`include_headquarters` params (default
      `True`, matching `unit_layer.py`'s older always-on behaviour) -
      when a domain opts out, that field doesn't exist on the layer at
      all, and `mct_build_sidc()`'s corresponding argument becomes a
      literal (`'unspecified'`/`false`) baked into the renderer
      expression rather than a field reference. `space_layer.py` now
      passes `include_echelon=False, include_headquarters=False` -
      "Tactical Graphics - Space" has exactly 4 fields (affiliation/
      entity/status/unique_designation). New
      `tests/test_point_symbol_layer.py` exercises the shared factory's
      own include/exclude behaviour directly (decoupled from Space's own
      data), plus `tests/test_space_layer.py` updated for the smaller
      field list. 412 tests passing on both QGIS 3.44.12 and 4.2.0. This
      also sets the precedent every later appendix mini-phase should
      follow: check that appendix's own amplifier table before assuming
      echelon/headquarters apply, rather than defaulting both on the way
      `unit_layer.py` originally did.
    - **Mini-Phase C (Appendix C, Air) done 2026-08-08.** New
      `military_symbology/air_layer.py` builds one "Tactical Graphics -
      Air" layer, following Space's now-established pattern exactly:
      both of Appendix C's sections (C.6 Air Equipment/Platform, symbol
      set `01`; C.7 Air Missile, symbol set `02`) in one layer via the
      `entity_symbol_set_overrides` mechanism, `include_echelon=False,
      include_headquarters=False` after confirming Table C-II (read this
      session) lists neither field for air symbols either. `sidc.py`'s
      `ENTITIES["air"]` was **replaced**, not just expanded: the
      previous version was a curated 19-entry subset built for
      `unit_layer.py`'s old shared multi-domain layer, with two entries
      (`air_reconnaissance`, `airborne_electronic_warfare`) renamed
      purely to dodge a key collision with `ground_unit`'s own
      vocabulary in that one combined dropdown. Now that Air has its own
      dedicated layer (no collision risk), it's milsymbol's FULL entity
      list from `air.js` (52 entities, every code `110000`-`140000`
      except `110106`, which milsymbol's own source marks "Reserved for
      Future Use" with an empty icon list) with plain, un-prefixed key
      names, cross-checked against the standard's own Table C-III
      directly. New `ENTITIES["air_missile"]` (1 entity, from
      `airmissile.js`) and `SYMBOL_SETS["air_missile"] = "02"` (Table
      A-III). "air" removed entirely from `unit_layer.py`'s own
      `_SYMBOL_SET_LABELS`/`_ENTITY_LABELS_BY_SYMBOL_SET` (Sea
      Surface/Subsurface still live there, pending Appendices E/F);
      `tests/test_unit_layer.py` updated accordingly (its
      "non-ground_unit symbol_set" integration test now uses
      `sea_surface`/`frigate` instead of the no-longer-offered
      `air`/`fighter`). New `icons/tactical_graphics_air.svg` and
      `tests/test_air_layer.py` (mirrors `test_space_layer.py`). 421
      tests passing on both QGIS 3.44.12 and 4.2.0.
    - **Foundational: sector 1/2 modifier support, added 2026-08-08
      before starting Appendix D.** User asked whether modifiers were
      being skipped entirely - they were: every layer built so far only
      ever set SIDC positions 17-20 (sector 1/2 modifier) to "0000",
      meaning real distinctions like Space's orbit type or Air's heavy/
      medium/light tanker class were simply unreachable. Decided to
      build this now rather than after Appendix D (Land), whose own
      modifier tables are large and commonly needed, to avoid redoing
      Space/Air a second time. `sidc.py` gained `MODIFIERS` (keyed by
      symbol_set, then `"sector1"`/`"sector2"`, real codes from each
      symbol set's own milsymbol-3.0.4 source) and `build_sidc()` grew
      `sector1_modifier`/`sector2_modifier` params (`None`/falsy ->
      SIDC `"00"`, matching the old always-zero behaviour exactly when
      omitted; a real key not in that symbol_set's own `MODIFIERS` entry
      raises `KeyError`, including for symbol_sets with no `MODIFIERS`
      entry at all yet - e.g. `ground_unit`, still fully unmodified).
      `mct_build_sidc()` (`expressions/military_symbology_functions.py`)
      now optionally accepts 2 more values (7th/8th), backward-compatible
      with existing 6-value callers like `unit_layer.py`'s own
      expression, left untouched. `_point_symbol_layer.py` gained
      `sector1_labels`/`sector2_labels` (optional, mirroring
      `include_echelon`/`include_headquarters`'s opt-in pattern) - when
      given, adds a `sector1_modifier`/`sector2_modifier` `ValueMap`
      field with an explicit `"(None)"` -> `""` option (new
      `_value_map_with_none()`) so "no modifier" is a first-class
      selectable choice, not just an absent one. `space_layer.py`/
      `air_layer.py` retrofitted with their own `_SECTOR1_LABELS`/
      `_SECTOR2_LABELS` - each the UNION of the layer's main symbol_set's
      own modifiers and its folded-in missile entity's symbol_set (e.g.
      Space's 11 sector1/27 sector2 keys, Air's 49 sector1/25 sector2
      keys) - `mct_build_sidc()` resolves the real numeric code against
      whichever symbol_set the feature's own entity maps to, so a
      modifier key only valid under one of the two merged symbol_sets
      simply won't resolve if paired with an entity from the other.
      That specific failure mode turned out NOT to be a clean, visible
      render-time error (`mct_build_sidc()` catches the `KeyError` and
      returns plain text, which milsymbol.js may still turn into SOME
      fallback SVG for the resulting garbage SIDC rather than visibly
      failing) - an early version of this pass's own tests wrongly
      assumed otherwise and had to be corrected to check the real
      contract directly against `build_sidc()` (which does reliably
      raise `KeyError`), not via a rendered symbol path. 440 tests
      (`tests/test_military_symbology_sidc.py`, `test_point_symbol_
      layer.py`, `test_space_layer.py`, `test_air_layer.py` all
      extended) passing on both QGIS 3.44.12 and 4.2.0.
    - **Mini-Phase D (Appendix D, Land) done 2026-08-08 - the largest
      mini-phase yet, four sub-domains in one pass.** Unlike Space/Air,
      Land Unit/Civilian/Equipment/Installation are each a genuinely
      substantial, independent vocabulary (Table A-III symbol sets
      10/11/15/20) - not folded into one merged layer via
      `entity_symbol_set_overrides` (that mechanism is for a small
      single-entity companion, not four large domains). New
      `military_symbology/land_layer.py` builds four separate layers
      ("Tactical Graphics - Land Unit/Civilian/Equipment/Installation"),
      all added together under one new toolbar action/icon
      (`icons/tactical_graphics_land.svg`), mirroring
      `control_measures.py`'s "one action, several layers" precedent.
      Field applicability read directly from Chapter 5's own Table VII
      (Appendix D's own Table D-II doesn't restate per-domain columns):
      Field B (Echelon) applies only to Units, so only Land Unit gets
      `include_echelon=True`; Field S (Headquarters) applies to Units/
      Equipment/Installations (not SIGINT), so all four get
      `include_headquarters=True`, including Land Civilian (judgment
      call - closest fit to Table VII's "U" category, since the base
      table has no explicit civilian-organization column).
      - **Land Unit** ("ground_unit" in `sidc.py` - key kept unchanged
        rather than renamed, since Table A-III's own code "10" doesn't
        change either way and a rename would touch every existing test/
        reference for no functional benefit) moved out of
        `unit_layer.py`'s old shared multi-domain layer into its own
        dedicated one. Its existing 50-entity curated vocabulary was
        re-verified entity-by-entity directly against milsymbol-3.0.4's
        own `landunit.js` (219 total entities available) - every single
        code confirmed correct, no bugs found, unlike the Air/Subsurface
        vocabularies earlier appendices turned up real bugs in.
      - **Land Civilian** (`ENTITIES["land_civilian"]`) is `landcivilian.
        js`'s FULL 11-entity vocabulary - small enough that no curation
        was needed, unlike every other Land domain.
      - **Land Equipment**/**Land Installation** (`ENTITIES["land_
        equipment"]`/`["land_installation"]`) are new curated subsets
        (of 229/131 total in `landequipment.js`/`landinstallation.js`)
        spanning weapons/vehicles/engineer/transport/law-enforcement
        equipment and government/financial/commercial/educational/
        utility/transportation/water infrastructure respectively - every
        code cross-checked programmatically against its own source file
        before being trusted (a `sId["<code>"]` existence check across
        all three new dicts, not just spot-checks).
      - **Deliberately NOT built this pass**: sector 1/2 modifiers for
        any of the four Land layers - Land Unit alone has 50+ codes per
        sector (Tables D-VI/D-VII), and all four domains combined would
        be a disproportionately large addition on top of an already
        four-domain appendix. Documented, deliberate scope decision, not
        an oversight - same precedent as `ground_unit`'s own entity
        curation.
      - `unit_layer.py` now covers only sea_surface/subsurface (both
        Air and Ground Unit have moved out) - its own tests updated
        (the "resolves to a valid path" integration tests now use
        sea_surface/subsurface instead of the no-longer-offered
        ground_unit; `DEFAULT_SYMBOL_SET`/default entity changed from
        ground_unit/infantry to sea_surface/frigate).
      - New `tests/test_land_layer.py` (table-driven via `subTest()`
        across all four domains, rather than four near-duplicate test
        classes). 447 tests passing on both QGIS 3.44.12 and 4.2.0.
    - **Same-day follow-up: Land Equipment/Installation had a systematic
      curation gap, caught by the user, not self-discovered.** The
      user pointed out machine gun's own short/intermediate/long-range
      codes (110201/202/203) were missing even though the generic form
      (110200) was included - checking further, this was systematic:
      nearly every weapon category in `landequipment.js` has a
      short/intermediate/long-range variant at entity-subtype codes
      X01/X02/X03, and nearly every vehicle category has a light/medium/
      heavy variant the same way, and the first pass had silently
      included only the generic (X00) form of each, dropping the entire
      variant axis rather than a few isolated entries. Root cause: the
      first pass was built by skimming grep output rather than a real
      parse, so multi-line source entries (which is how every one of
      these variants is written in `landequipment.js`) were invisible to
      it. Fixed by writing a proper multi-line-aware parser
      (`re.compile(r'sId\["(\d{6})"\]\s*=\s*(\[.*?\]);', re.S)`) and
      rebuilding both dicts from its complete, verified output instead:
      `ENTITIES["land_equipment"]` grew from 59 to 145 entries (every
      weapon/vehicle category's range or size variants added, plus
      three previously-missed categories entirely - Missile Support,
      Mine Laying, Drilling - and a few bridge-type variants);
      `ENTITIES["land_installation"]` grew from 52 to 97 (a milder,
      related gap - Installation's own sub-codes are genuinely distinct
      sibling facility types, not a modifier axis, but several
      categories only had 2-3 of their real siblings included, e.g.
      Bank but not ATM/Bullion Storage/Federal Reserve Bank/Financial
      Services Other - filled in the remaining siblings per category).
      Both new dicts verified programmatically against their own source
      files' complete parsed output (every code confirmed to exist, no
      duplicate codes, no duplicate keys) rather than spot-checked.
      `land_layer.py`'s own `_EQUIPMENT_ENTITY_LABELS`/`_INSTALLATION_
      ENTITY_LABELS` rebuilt to match exactly (cross-checked
      programmatically: identical key sets to `sidc.py`'s own dicts).
      No test changes needed - the existing vocabulary-coverage test
      compares key sets, not hardcoded counts, so it caught nothing
      wrong but also required no update; 447 tests still passing on both
      QGIS 3.44.12 and 4.2.0. Land Unit was checked for the same failure
      mode and found NOT to have it - its own sub-codes are genuinely
      distinct combined-arms types (e.g. "reconnaissance armor",
      "amphibious infantry"), not a mechanical range/size axis, so
      widening it further is a real but separate expansion, not a bug
      fix - left as an explicit, not-yet-done follow-up.
    - **Re-verification pass, same day: milsymbol.js itself checked
      against the standard's own printed tables (Space/Air/Land Unit/
      Land Equipment/Land Installation), not just our own curation
      checked against milsymbol.** Pulled each appendix's actual PDF
      table pages, extracted every entity code they print, and diffed
      against milsymbol.js's own source specifically looking for codes
      the standard has that milsymbol.js DOESN'T (a gap no amount of
      curation could fix). **Result: zero such gaps found** across every
      domain checked - every code in the standard's printed tables
      exists in milsymbol.js. This confirms milsymbol.js is a complete,
      faithful base for these appendices; the only remaining gaps are
      our own deliberate curation choices, catalogued below (2026-08-08,
      full milsymbol-vs-`sidc.py` diff, "we will revisit later" per the
      user - see task list) for whoever picks this back up:
      - **Land Unit - 162 of 212 real `landunit.js` entities excluded**
        (we have 50). Main groups: signal/comms sub-types (radio, radio
        relay, radio teletype centre, broadcast transmitter antenna,
        satellite comms, video imagery, MISO); civil-affairs family
        (civil affairs, civil-military cooperation, information
        operations); ~15 combined-arms compound variants (reconnaissance-
        armor, amphibious-armor, amphibious-infantry, motorized-antitank,
        and similar two/three-part combinations of categories already
        individually present); CBRN compounds (+armor/+motorized/
        +reconnaissance); SOF sub-types (SOF combatant, submarine SOF,
        underwater demolition team, fixed-wing MISO); a large
        administrative/combat-service-support bucket (band, finance,
        judge advocate general, labour, laundry/bath, morale/welfare/
        recreation, mortuary affairs, personnel services, pipeline,
        postal, public affairs, religious support, seaport/railhead of
        debarkation, plus all ten NATO supply class I-X icon variants);
        the full law-enforcement family (border patrol through US
        Marshals - also present, more completely, under Land Equipment/
        Installation); multinational commands (ARRC, ISAF, "Multinational
        (MN)"); space, multi-domain, cyber, air traffic services.
      - **Land Equipment - 74 of 219 real `landequipment.js` entities
        excluded** (we have 145, after this session's fix above). Main
        groups: deep sub-sub-compounds already deliberately excluded per
        the documented curation boundary (SAM launcher TLAR/TELAR
        mountings, armor+cross-country+recon combos, engineer recon
        vehicle, assault breacher vehicle, route-clearance vehicles,
        tow-truck light/heavy, civilian-vehicle+trailer combos); missile
        propellant/warhead transporters (190400/190500 - have
        transloader/transporter/crane, stopped short of these two); tent
        civilian/military variants, psychological operations equipment,
        unit deployment shipments, medevac helicopter, antipersonnel mine
        (less-than-lethal), sensor (emplaced). **The one real
        inconsistency here - the half-included law-enforcement family -
        was FIXED 2026-08-18, see the dated entry below.** The "145" and
        "74 excluded" counts above are pre-fix; Land Equipment now has
        153 entities, 66 of 219 excluded. Note also that this catalogue
        entry named the missing codes wrongly: it listed "law-enforcement
        -vessel" among them, which Land Equipment does not have at all,
        and omitted ATF (170100), which it does. Reading one symbol
        set's family and assuming another matches is exactly the trap
        the fix below documents.
      - ~~**Land Installation - entities excluded**~~ **D-3 CLOSED
        2026-08-18: 130 of milsymbol's 131, which is every code Table
        A-XXVII prints. See the dated entry below.** The list that
        followed here is kept only as the record of what was missing: Main groups: intelligence-marking installations
        (black-list/gray-list/white-list location, mass grave location);
        radioactive material; tent+evacuee/training-camp compounds;
        industrial site+warehouse; Class III/V supply-facility compounds;
        electric-power-generation-station duplicate icon; base+armory
        compound; naval-yard/airport-of-debarkation transportation
        compounds.
      - ~~Sector 1/2 modifiers remain entirely unbuilt for all four
        Land layers~~ **D-4 part one done 2026-08-18: Civilian,
        Equipment and Installation built (55 codes). Land Unit's own
        (Tables D-VI/D-VII) is the remaining half** - the maintainer's
        call was to prove the dropdown pattern on the three small sets
        before committing to Land Unit's 184 milsymbol codes. See the
        dated entry below.
    - **D-2 CLOSED, 2026-08-18: Land Equipment's law-enforcement family
      completed (Table A-XXV, codes 170000-171100).** The one item on
      the post-1.0 list that was arguably *wrong* rather than merely
      unfinished, and the failure mode is worth naming: the family
      shipped through 1.0.3 with four of its twelve entries - generic,
      Border Patrol, Customs Service, DEA - which is a truncation
      *inside* a category rather than at a category boundary. A user
      opening the Entity dropdown saw a plausible-looking law-enforcement
      group and had no way to tell eight entries were missing. Every
      other documented Land gap is a whole category left out on purpose;
      this one looked finished and was not.
      **What the family actually is**, read off the printed table rather
      than inferred: 170000 Law Enforcement, 170100 ATF, 170200 Border
      Patrol, 170300 Customs Service, 170400 DEA, 170500 DOJ, 170600
      FBI, 170700 Police, 170800 USSS, 170900 TSA, 171000 **Coast
      Guard**, 171100 US Marshals Service.
      **The trap, which nearly caught this fix**: the same family exists
      in Activities (1315xx) and Land Installation (1121xx), and the
      obvious move is to copy one of those lists across. It is wrong.
      Both of those sets carry **Prison**; Land Equipment does not, so
      its tail runs one position earlier from Police onward - 170800 is
      USSS here where 131508/112108 are Prison. Predicting the tail from
      a sibling set produced four wrong labels before Table A-XXV was
      opened. The old catalogue entry above had the same error baked in:
      it listed "law-enforcement-vessel" as missing and never noticed
      ATF (170100) was.
      **That phrase turned out to expose a second, larger defect** - see
      the separate entry below; "Law Enforcement Vessel" is not a member
      of any land law-enforcement family in the standard at all.
      **Verified renderable, not assumed**: milsymbol falls back to an
      identical bare frame for any code it does not know, so each of the
      twelve was rendered and its SVG compared against a deliberately
      bogus code's frame. All twelve draw real icons; 171200 and beyond
      return the bare frame, confirming the family genuinely ends at
      171100 rather than our list ending early again.
      **One label corrected without touching its key**: Table A-XXV reads
      "Drug Enforcement Administration (DEA)" where the plugin said
      "Agency". The label is now the standard's, but the entity key stays
      `drug_enforcement_agency` - it shipped in 1.0.3 and is written into
      the `entity` field of saved features, so renaming it would silently
      break any project a user has already saved. Precedent cuts the
      other way here (the Light/Medium/Heavy weapon keys WERE renamed in
      2026-08-08) but that rename happened pre-release, with no user data
      to invalidate.
      `ENTITIES["land_equipment"]` 145 -> 153 entities; `_EQUIPMENT_
      ENTITY_LABELS` matched (the existing key-set equality test enforces
      this). Five new tests in `tests/test_land_layer.py`, with the
      twelve codes transcribed longhand from the printed table so they
      disagree with the source when the source is wrong, plus explicit
      negative assertions that Prison and Law Enforcement Vessel are
      NOT in this set. 1326 -> 1331 tests on both QGIS 4.2.1 and
      3.44.12. Bandit clean (7 suppressions registering, up from 5 - the
      new USSS entity name needs the same B105/detect-secrets markers as
      the other four); detect-secrets clean on all three changed files.
      **Not yet released** at time of writing - wants a version bump
      whenever the next upload happens.
    - **Two label corrections in Land Installation, 2026-08-18, raised
      by the maintainer**: the Entity dropdown offered "Drug Enforcement
      **Agency** (DEA)" and "Transportation Security **Agency** (TSA)".
      Table A-XXVII prints **Administration** for both. Labels
      corrected; the keys (`drug_enforcement_agency`,
      `transportation_security_agency`) are unchanged, for the same
      saved-feature reason as Land Equipment's own DEA key above. Worth
      noting how this was found: it was NOT found by the Land Equipment
      fix, which corrected the identical wording one dict higher up in
      the same file and stopped there. The maintainer read the actual
      dropdown. A label is only wrong where a user reads it, and a fix
      scoped to one symbol set leaves the identical error standing in
      the next one.
    - 🐞 **Coast Guard was being offered to users as "Law Enforcement
      Vessel" in two symbol sets - found while checking the label fix
      above, fixed 2026-08-18 at the maintainer's instruction.**
      `sidc.py` maps `law_enforcement_vessel` to `land_installation`
      112111 and `activities` 131511. Both codes are printed **Coast
      Guard** in the standard (Table A-XXVII and Table A-XXXVIII), and
      neither table has a "Law Enforcement Vessel" row at all. The
      standard's real Law Enforcement Vessel is **Sea Surface 140300**,
      which was already correct and is deliberately left alone - the
      wrong move here would have been "aligning" the three.
      This is the worst of the law-enforcement defects found in this
      round, because it is not an omission or a wording slip: the
      dropdown named one thing and drew another, and a user picking
      "Law Enforcement Vessel" on a land installation layer got a Coast
      Guard icon with no indication anything was off.
      **Fixed as a label change only.** The key stays
      `law_enforcement_vessel` in both sets, for the same reason the DEA
      key stayed: keys are written into the `entity` field of features
      users have already saved, and the code behind the key (112111 /
      131511) was always right, so every existing feature already draws
      the correct icon. Renaming would break saved projects to fix
      nothing a user can see. The wrongness is quarantined in comments
      at all four sites plus a test that pins the label.
      **ATF (112101) and Police (112107) added to Land Installation** in
      the same pass - both printed in Table A-XXVII, both drawable,
      both simply absent, leaving two holes in an otherwise contiguous
      run. `ENTITIES["land_installation"]` 97 -> 99 entities; the family
      is now the standard's full 13.
      **And two more "Agency" labels corrected there**: DEA (112104) and
      TSA (112110), both of which the standard prints as
      *Administration*. Keys unchanged.
      Verified the same way as Land Equipment: all thirteen 1121xx codes
      rendered and compared against a bogus code's bare frame - all
      thirteen draw, 112113 onward do not, confirming the family ends at
      112112. Nine new tests, including one that asserts the string
      "Drug Enforcement Agency" appears in **neither** Land label dict -
      written specifically because the first fix corrected that wording
      in one dict and left it standing thirty lines below in the other.
    - **D-3 CLOSED, 2026-08-18: Land Installation's vocabulary completed,
      99 -> 130 entities.** Every code MIL-STD-2525D Table A-XXVII prints
      is now present. All 130 verified to draw a real icon (each rendered
      and compared against a bogus code's bare frame), and the dict is
      now maintained in ascending code order with a test pinning it -
      a code out of order is the visible symptom of an entry filed under
      the wrong group.
      **Three codes in `landinstallation.js` appear NOWHERE in the
      standard's text**: 112001 (a grenade icon in a gap the table skips),
      112300 "Home", and 120803 "Airport". We already shipped the latter
      two. At the maintainer's decision, after rendering all three for
      review, they are **kept but marked** - their labels now end
      "(non-standard)", so a user cannot mistake them for MIL-STD-2525D
      entities, and no saved feature breaks. 112001 was never shipped and
      stays out. Worth recording that 120803 is not just non-standard but
      redundant: the standard's own airport is **121301 Airport/Air
      Base**, which was among the 31 codes missing until today.
      **The label audit was the unplanned half of this item.** Comparing
      all 99 existing labels against Table A-XXVII found twelve genuine
      mismatches, and two were the Coast Guard defect a third time - a
      GROUP HEADER wearing its own child's name:
      120500 was labelled "Electric Power" (it is Energy Facility
      Infrastructure; the real Electric Power is its child 120501) and
      121400 was "Water (Generic)" (it is Water Supply Infrastructure;
      the real Water is 121410). Both children were among the 31 being
      added, so leaving the parents alone would have produced a dropdown
      offering identical text on two different rows. There is now a test
      asserting no label is used twice in the layer.
      The children take the keys `electric_power_facility` and
      `water_facility` rather than the obvious names, because the legacy
      keys already hold those and **no shipped key is ever renamed here**
      - they are written into the `entity` field of saved features. The
      other ten corrections: Government -> Government Leadership, Fire
      Protection -> Fire Station, Food Distribution (Production)/(Retail)
      -> Food Production Center/Food Retail, Base -> Military Base,
      Ferry -> Ferry Terminal, Maintenance -> Maintenance Facility,
      Railhead -> Railhead/Railroad Station, Water Purification -> Water
      Treatment. An eleventh was proposed and **rejected by the
      maintainer**: 110000 is printed "Military/Civilian" but keeps the
      shorter "Military (Generic)" a user already recognises - the
      standard's wording wins on identity, not on every last word of
      phrasing.
      1339 -> 1344 tests on QGIS 4.2.1 and 3.44.12.
    - **D-4 part one, 2026-08-18: sector 1/2 modifiers for Land
      Civilian, Equipment and Installation - 55 codes, three layers.**
      Split at the maintainer's decision: prove the pattern on the small
      sets first, then do Land Unit's own tables as a second pass. Each
      of the three layers now offers a Sector 1 (and where the standard
      has one, Sector 2) dropdown alongside Entity.
      **The counts came out far smaller than milsymbol suggested, and
      that is the finding.** milsymbol's three source files carry 26+2,
      24+9 and 16+10 modifier codes; MIL-STD-2525D's own tables print
      24+1 (A-XXIII/A-XXIV), 9+0 (A-XXVI) and 13+8 (A-XXVIII/A-XXIX).
      The surplus is **2525E/APP-6E**, which milsymbol also implements:
      Cyberspace in every set, Robotic, Joint Network Node and Command
      Post Node on Installation, and an entire aviation-mission axis on
      Equipment sector 1 (codes 10-24: tilt-rotor, attack, cargo,
      medevac, utility...). Building from milsymbol would have put 32
      modifiers into these dropdowns that no 2525D symbol has. Not
      built; documented at `MODIFIERS` in `sidc.py` with what to revisit
      if the plugin ever targets 2525E.
      **Land Equipment has NO sector 2 in 2525D at all.** The standard
      has D.8.3 (sector 1, "sensor type category") and simply no D.8.4 -
      confirmed in the table of contents and the body. milsymbol's nine
      `sIdm2` codes for symbol set 15 are mobility indicators, which the
      standard encodes in a different field entirely. So
      `MODIFIERS["land_equipment"]` deliberately has a `sector1` key and
      no `sector2` key, `build_sidc()` already handles that as "no
      modifier support" rather than an error, and the Land Equipment
      layer gets one dropdown where the other two get two. Pinned by a
      test, because "the pair is incomplete" is exactly what a future
      pass would try to fix.
      **Every one of the 55 was rendered and compared against the bare
      symbol** - all 55 change it. A modifier that draws nothing is a
      dropdown entry that does nothing, and no existing test would have
      noticed. 1344 -> 1349 tests on QGIS 4.2.1 and 3.44.12.
    - **Phase 12 (proposed): move the plugin to MIL-STD-2525E /
      APP-6E.** Raised by the maintainer 2026-08-18 off the back of D-4,
      where 32 modifier codes were excluded for being 2525E rather than
      2525D. **Scoped, then deliberately parked pending the E documents.**
      **The premise that prompted it does not hold, and this is the
      finding worth keeping**: milsymbol 3.0.4 renders 2525E and 2525D
      **identically**. The same symbol rendered with version digits `10`
      (edition D) and `13` (edition E) produces byte-identical SVG, at
      both 20 and 30 characters - verified by hashing. `metadata.js`
      computes `metadata.edition` from those digits ("10"/"11"/"12" = D,
      "13"/"14" = E) but nothing downstream selects a different icon
      set, because there is only one. milsymbol's `ms.setStandard()` is
      a **2525-vs-APP6** switch (frame shapes), NOT a D-vs-E switch.
      So "include all of milsymbol's E symbols" would add no artwork:
      every code excluded during D-3/D-4 for being 2525E-only is already
      renderable today under version 10. They were left out because
      2525D's tables do not print them, not because milsymbol cannot
      draw them.
      **What a real upgrade would actually be**: (1) the vocabulary -
      every code milsymbol carries beyond D's tables, across all
      appendices; (2) the SIDC itself - version digits 10 -> 13, and E's
      SIDC is **30 characters** rather than D's 20, with the extra ten
      carrying new fields (`frameshape` at position 23, per milsymbol's
      own metadata reader); (3) 174 occurrences of "2525D" across code,
      README, `metadata.txt` and the plugin's user-facing description.
      **The mechanical part is well positioned**: all 139 `build_sidc()`
      call sites go through that one function, and the whole repo has
      just 4 hardcoded SIDC literals, all in tests. Changing the format
      is a one-function change plus its callers' expectations.
      **The blocker is input, not effort.** `reference/` holds
      MIL-STD-2525D.pdf and nothing else. Every correctness fix in this
      session came from reading D's own printed tables - Coast Guard,
      `law_enforcement_vessel`, the Energy Facility / Water Supply
      parents, the 32 surplus modifiers - and every one was a case where
      milsymbol and the standard disagreed and the standard was right.
      Building E from milsymbol alone reproduces precisely that error
      class with no way to detect it. **Maintainer's decision
      2026-08-18: source the MIL-STD-2525E and APP-6E documents first,
      then do it properly.** Do not start this from milsymbol.
      **UPDATE, same day - sources found, and the 2525E vocabulary is
      BUILT.** The maintainer could not obtain the official PDFs (access
      restrictions) but supplied four sources between them sufficient for
      everything except APP-6E's modifiers:
      - **Esri ArcGIS Pro dictionary styles** (`reference/mil2525e.stylx`,
        `app6e.stylx` - SQLite, gitignored): 4289 and 3769 items, keyed
        `SS`+6-digit entity, with the standard's own names. Good for
        cross-checking; NOT authoritative on absence, since a code with no
        distinct graphic simply is not in the file.
      - **github.com/spatialillusions/milstandard-e** (MIT): the 2525E
        tables themselves as 48 TSVs - entities AND per-symbol-set sector
        1/2 modifiers AND the common-modifier tables, with the standard's
        own Remarks column. Copied to `reference/milstandard-e/`. This is
        the authority the work now rests on.
      - **github.com/spatialillusions/mil-std-2525** and
        **/stanag-app6**: 2525B/C/D and APP-6B/D. Not needed for E, but
        used for the D-vs-APP6D comparison below.
      - **github.com/nwroyer/Python-Military-Symbols** (MIT): its
        `symbol.py` documents the **SIDC layout**, which nothing else did.
      **The SIDC answer, since it was the blocker**: E's extension is
      THREE significant digits, not ten. Digits 0-19 are as 2525D; digit
      20 flags that the sector 1 modifier comes from the COMMON table
      rather than the symbol set's own, digit 21 does the same for sector
      2, and digit 22 is a frame-shape override. The 30-character form is
      padding - neither implementation reads past digit 22. Confirmed
      independently: milsymbol reads `frameshape = sidc.substr(22, 1)`,
      the same position, in a different language.
      That also explains three loose ends at once: milstandard-e's
      separate `Common Modifiers sector 1/2.tsv`, Esri's `CMOD1_*` keys,
      and why per-set modifier lists looked short. **Common modifiers are
      a parallel namespace selected by a flag digit, not a fallback** -
      and their codes are printed as THREE digits (100-166), the flag
      included. An earlier caveat in this session, that the Esri modifier
      lists were incomplete, was WRONG for the right-sounding reason: the
      codes missing from Land Installation sector 1 are `{Disused}` in
      2525E, not missing data. The two sources agree exactly.
      **Are 2525E and APP-6E actually different?** No APP-6E table set
      exists in any of these repos - `stanag-app6` carries B and D and
      points to `milstandard-e`, which exports a single `ms2525e` while
      its README claims both. Rather than assume, all 30 shared
      **2525D vs APP-6D** tables were diffed: they genuinely diverge -
      Control Measures 603 vs 619, Land unit 213 vs 202, Land equipment
      230 vs 223 - plus systematic US/UK spelling and real terminology
      swaps on identical codes (110600 is "Military Information Support
      Operations (MISO)" in 2525D and "Psychological Operations
      (PSYOPS)" in APP-6D; 214000 is reserved in 2525D and "Forward
      Observer / Spotter Position" in APP-6D). So **separate
      vocabularies, per the maintainer's decision** - one merged table
      would be wrong. Note Land installation is the exception, identical
      129/129 at D, which is why the Esri styles' apparent 51-entity gap
      for APP-6E is an Esri dictionary artifact rather than a standards
      difference; an earlier note in this session read it the other way.
      **BUILT 2026-08-18**: `tools/extract_2525e_vocabulary.py` (a dev
      script, not shipped, not imported) generates
      `military_symbology/sidc_2525e.py` - **989 entities across 13
      symbol sets, plus 610 sector modifiers including the 93 common
      ones**. `{Disused}` rows are dropped, which is the entire reason
      the generator reads Remarks: 2525E retires six of the thirteen Land
      Installation sector-1 modifiers that D-4 built for 2525D one hour
      earlier. Control Measures' 561 rows are deliberately NOT extracted -
      Appendix H is hand-drawn geometry here, not a vocabulary.
      `sidc.py`'s 2525D dicts are **untouched** and nothing is wired into
      a layer yet; this is data only, so the shipped plugin is unchanged.
      **One generator bug worth recording**, caught by a test rather than
      by reading the output: entity tables run general-to-specific across
      their columns (Entity, Entity Type, Entity Subtype) but modifier
      tables run the opposite way (First Modifier, Category). Reading both
      the same direction produced keys like `mobility` and
      `robotic_mobility` where `robotic` was meant - every one of the 610
      modifier keys was backwards, and the generated file looked
      perfectly plausible.
      10 new tests, 1349 -> 1359 on QGIS 4.2.1 and 3.44.12.
      **Edition switch built 2026-08-18, engine level.**
      `build_sidc()` takes `edition=` ("2525D" default, "2525E"), which
      selects both the vocabulary the entity is looked up in and the
      SIDC's own version digits ("10" vs "13"). `mct_build_sidc()` takes
      it as an optional NINTH argument, so every renderer expression
      written before editions existed - including those saved in users'
      project files - resolves to exactly the SIDC it produced before.
      `entities_for_edition()` / `modifiers_for_edition()` hide the fact
      that 2525D nests its two modifier sectors per symbol set while
      2525E keeps them in separate module-level dicts.
      **APP-6E is deliberately not a third vocabulary** (maintainer,
      2026-08-18): it shares 2525E's symbology closely enough that a
      separate set is impractical, and no source for its modifier tables
      exists anyway.
      6 new tests, 1359 -> 1365. The one that matters most asserts a
      2525D call is byte-identical with and without the new parameter.
      **LAYER-level switch built 2026-08-18.** Edition is fixed per
      LAYER, not per feature, and that is a QGIS constraint rather than
      a preference: the entity dropdown is a `ValueMap` editor widget
      whose map is frozen when the field is configured, so it cannot
      re-populate itself from a per-feature edition value - a per-feature
      column would leave the dropdown listing one edition's vocabulary
      while the SIDC was built from another's.
      So a single plugin-wide setting decides what NEW layers get
      (`military_symbology/edition.py`, stored in `QgsSettings`), exposed
      as a checkable "Symbology Edition" toolbar menu. **Layers already
      in a project are never touched**: each one names its own edition in
      its renderer expression, and a layer built before this existed
      names none, which `mct_build_sidc()` reads as 2525D - exactly what
      it was built as. An unrecognised stored value degrades to 2525D
      rather than raising out of a layer-creation call.
      `build_single_domain_point_layer()` takes `edition=`, and swaps in
      the generated 2525E labels centrally rather than making all eight
      layer modules carry a second set of dicts. It also re-points the
      default entity when the caller's 2525D default has no equivalent in
      E - a default that does not exist in the chosen edition would write
      an unresolvable key into every new feature.
      **Labels are generated too**, not transcribed: 989 entities is far
      past what is sensible to hand-write, and the source tables already
      carry the standard's own wording.
      Verified live rather than only in tests - a 2525E Land Installation
      layer offers 7 sector-1 modifiers where the 2525D one offers 13
      (the six `{Disused}` codes are gone) and its expression carries
      `'2525E'`. 1365 -> 1369 tests.
      🐞 **Edition in the layer NAME, 2026-08-18 - a real bug the
      maintainer hit within minutes of the switch shipping.** "I inserted
      Air symbols using App6D symbology, now when I change the symbology
      layer to 6E and try to insert the same layer I get an error."
      Exactly right: `add_single_domain_point_layer()`'s duplicate guard
      matches on layer NAME, and the name carried no edition - so one
      project could hold only ONE edition of a given domain, and the
      second attempt reported "already exists" as though the user had
      done something wrong. The edition was also invisible in the Layers
      panel; nothing short of opening the renderer said which one a
      layer was.
      Fixed by suffixing the name, in the maintainer's own wording:
      "Air (2525D/6D)" / "Air (2525E/6E)". **Both** editions are
      suffixed, not just E - an un-suffixed 2525D layer would go on
      blocking its E counterpart, which is the bug. The suffix names
      both standards because the plugin serves both from one vocabulary
      and the layer belongs to neither alone.
      The edition is now resolved ONCE, in the add helper, and passed
      down - so the suffix and the layer's own renderer expression
      cannot disagree, which they could have if the setting changed
      between the two reads. Every `add_*_layer()` gained an optional
      `edition=` so a caller (and a test) can be explicit rather than
      going through the setting.
      **Consequence worth knowing**: a layer added before today has no
      suffix, so adding that domain again will now produce a suffixed
      layer alongside it rather than being blocked. That is arguably
      right - the old layer genuinely IS 2525D - but it is a visible
      change for anyone with an existing project.
      3 new tests, including the maintainer's exact sequence: add Air
      under 2525D, add Air under 2525E, expect TWO layers. 1369 -> 1372.
      🐞 **Three defects from the maintainer's 1.0.4 smoke test,
      2026-08-18 - the first round of real hands-on use of any of this.**
      1. **"SIGINT - 6D is fine, 6E all symbols break."** Correct, and
      the cause was in the generator's own scope list: SIGINT's five
      symbol sets (`sigint_space`/`_air`/`_land`/`_sea_surface`/
      `_subsurface`) share ONE vocabulary in the standard and one table
      in the source, and that table was never mapped - so
      `ENTITIES_2525E` had no SIGINT at all. The layer then fell back to
      its 2525D labels for the dropdown while `build_sidc()` looked those
      keys up in 2525E, raised `KeyError`, and `mct_build_sidc()` handed
      the **error text to milsymbol as a SIDC** - which it drew as an
      arbitrary symbol rather than failing visibly. Fixed by fanning the
      one source table across all five keys, and by making
      `entities_for_edition()` FALL BACK to 2525D for any set an edition
      has no vocabulary for - `control_measure` is the standing case,
      since Appendix H is deliberately not extracted.
      2. **"In space, for 6D only - if a modifier is added, the symbol
      breaks, renders ok without any modifier."** This one is NOT new
      and not edition-related: `_point_symbol_layer.py`'s own docstring
      has warned about it since the merged layers were built. A layer
      that merges symbol sets (Space + Space Missile, SIGINT's five
      dimensions) offers the UNION of their modifier vocabularies in one
      dropdown, because a QGIS ValueMap cannot filter itself by another
      field's value - so a reasonable-looking pick can be invalid for the
      entity beside it. Measured: **703 of the Space layer's
      entity/modifier pairs were invalid under 2525D**. Fixed at the
      failure mode rather than the cause, which is not fixable while the
      dropdown is a ValueMap: `mct_build_sidc()` now retries WITHOUT the
      modifiers and returns the bare symbol, so the right icon draws
      unmodified instead of a wrong icon drawing confidently. A genuinely
      bad entity still reports, so this does not swallow real errors.
      3. **Three near-identical water entries under 2525E** - "Water
      Supply", "Water", "Water Treatment". Faithful to the printed table,
      unusable in a dropdown. 2525E marks group headers "Reserved for
      hierarchical purposes", so the generator now appends "(Generic)" to
      exactly those - the same convention the hand-written 2525D labels
      already use. 48 labels affected across all sets.
      1372 -> 1377 tests.
      🐞 **Second smoke round, same day - the Boundary echelon amplifier.**
      Maintainer: "if I select only echelon, it is not rendered; if I
      select an echelon and unique modifier then it shows unique
      designation on top of the line and echelon on the bottom; if I
      select all three then it renders fine." Two faults in one
      expression, both invisible unless an echelon was chosen WITHOUT
      designations:
      (1) the label opened with a bare `upper("unique_designation")`, and
      QGIS collapses a whole `||` chain to NULL on any NULL operand - the
      same trap `grid_labels.py` hit over the GZD fields - so an echelon
      on its own produced no label at all and the glyph never drew;
      (2) Table H-III stacks THREE rows and the mask cuts the line around
      the label's MIDDLE, but the label was assembled from only the
      POPULATED rows - so with two rows the glyph was the bottom one and
      sat below the line instead of in it. Three rows happened to work,
      which is why it looked fine in earlier testing.
      Fixed as the maintainer suggested: when an echelon is chosen the
      label is always three rows, absent designations padded with a
      single space to hold the glyph in the middle. With no echelon
      nothing needs holding, so the compact form stays and an unamplified
      boundary still draws no label rather than three blank rows with a
      gap cut for them. A far designation alone also renders now - the
      same NULL collapse by another route.
      **An existing test asserted the buggy output** (`"2ID (USA)\n++"`,
      two rows) and had to be rewritten - worth noting, because it means
      the behaviour was pinned wrong rather than untested.
      Also this round: Activities 131500 relabelled "Law Enforcement
      Operation", the standard's own wording, spotted by comparing 2525D
      against 2525E side by side. 1377 -> 1380 tests.
      🐞 **Third smoke round, same day - 31 of the "(Generic)" entities
      the S-11 fix labelled turned out to render as a blank frame.**
      Maintainer: "sensor generic, train generic etc all create a blank
      circle, it does not make sense, so remove all these symbols."
      S-11 had appended "(Generic)" to every 2525E row the standard marks
      "Reserved for hierarchical purposes" without checking what each one
      actually draws - the label fix was correct, but it assumed the
      underlying symbol was meaningful, and for most of them it is not.
      **Verified by rendering, not by re-reading the source text**: all
      48 candidates were rendered via `symbol_engine`, rasterised with
      Qt's own `QSvgRenderer` (the renderer QGIS itself uses), and
      screened for non-background, non-frame pixels. **31 produced a
      bare frame with no glyph and no text** - visually confirmed via
      screenshots, since a raw pixel count alone missed that some
      "blank" entries actually carry a distinguishing FRAME shape
      (Cyberspace, SIGINT) while genuinely drawing nothing inside it.
      **17 carry real content and are kept** - a text abbreviation
      ("MIL", "CIV", "NAT", "GEOL", "HYDR", "INFS") or an actual icon
      (Tent, Armored, Military Combatant's crossed swords). Land
      Equipment's own generic entries split cleanly on this line: Vehicle
      and Armored (120000/120100) draw a real vehicle glyph and stay;
      Utility Vehicle, Train, Civilian Vehicle, Other Equipment, Land
      Mines and Sensors (140000/150000/160000/200000/210000/220000) are
      every one of them a bare circle and go - exactly the maintainer's
      own examples.
      Removed as a hardcoded, comment-justified exclusion list
      (`BLANK_GENERIC_CODES` in the generator) rather than a rendering
      heuristic run at generation time - the generator has no access to
      milsymbol, and "Reserved for hierarchical purposes" does not
      predict this either way (land_installation 110000 carries that
      same remark AND a real "MIL" glyph). 989 -> 978 entities. No
      symbol set was emptied, and no layer's `DEFAULT_*_ENTITY` collided
      with a removed key - both checked explicitly, since either would
      have broken the edition switch's default-repointing silently.
      5 new tests, 1380 -> 1385.
      **E-6/E-7 (APP-6E's own modifier tables and NATO spelling) CLOSED,
      2026-08-18 - cannot be done, not merely deferred.** No source for
      the official MIL-STD-2525E or APP-6E documents themselves was
      obtainable (access restrictions, the same blocker that shaped the
      whole of Phase 12 - see the "sources found" update above), and
      unlike 2525E, no third-party repo carries APP-6E's own modifier
      tables either: `stanag-app6` covers B and D only and points at
      `milstandard-e`, which exports a single `ms2525e` table set while
      its README claims to cover both editions. Building E-6/E-7 from
      2525E's own tables was considered and rejected rather than
      substituted quietly: the maintainer's own research had suggested
      2525E and APP-6E are "identical, mathematically and visually", so
      that assumption was checked directly rather than trusted - a full
      key-level diff of the two Esri dictionary files
      (`reference/mil2525e.stylx` vs `reference/app6e.stylx`) found 925
      keys only in 2525E, 405 only in APP-6E, and 649 of the 3364 shared
      keys carrying a different name - 340 of those not explainable by
      US/UK spelling alone. Some are real renamings on the identical
      code (2525E's "Military Information Support Operation (MISO)" is
      APP-6E's "Psychological Operations (PSYOPS)", same pattern as the
      2525D/APP-6D pair found earlier); two are unrelated concepts
      sharing a code by coincidence (`60081`: "Continuity of Operations"
      vs "Radio Frequency RF"; `60130200`: "Firmware" vs "Insider"). So
      the editions converged a great deal relative to D/APP-6D, but are
      not identical enough to build E-6/E-7 from 2525E's own data
      without misrepresenting APP-6E - there is no safe substitute for
      an actual source. Closed for good; revisit only if a user actually
      asks and can point to one.
      **Nothing outside the shared point-layer factory is edition-aware**
      - Appendix H's hand-drawn control measures are built from geometry,
      not vocabulary, so they are unaffected, but any layer NOT going
      through that factory still builds 2525D only.
    - **D-4b CLOSED, 2026-08-18: Land Unit's own sector 1/2 modifiers
      (Tables D-VI/D-VII) - the largest of the four Land layers by far,
      and the one that could not be trusted to either milsymbol or the
      easiest-available TSV source. Both were checked directly against
      `reference/MIL-STD-2525D.pdf` rather than assumed, and both had
      real defects.**
      **Failure 1 - a systematic over-extension, same shape as the D-4a
      finding.** The "2525d"-labelled TSV (and milsymbol's own
      landunit.js) define sector-1 codes up to 99 and sector-2 up to 78.
      The printed standard's Table D-VI stops at **78**, Table D-VII at
      **57** - confirmed by reading the PDF directly to the last code
      present before each table transitions to the next section (D-VII
      ends immediately before D.7 Land Civilian begins). Codes 79-98
      (sector 1) and 58-78 (sector 2) - 41 codes combined, more than
      D-4a's entire built vocabulary - are 2525E-only: Tilt-Rotor,
      Command Post Node, Joint Network Node among them. Both editions
      number-align on the shared portion, which is exactly what made
      this easy to miss - the extra codes look native.
      **Failure 2 - new, and worse: milsymbol draws the wrong ICON, not
      just a wrong label.** landunit.js's own sIdm1 table branches on
      milsymbol's `_STD2525` flag at 8 codes (01, 47, 56, 58, 71, 72, 73,
      74) - `_STD2525 ? iconA : iconB`. The flag defaults `true` and this
      plugin never calls `ms.setStandard()`, so our engine has always
      drawn `iconA` at these codes. **All 8, checked individually against
      the PDF, print `iconB`'s name at that code** - e.g. code 01 renders
      "Tactical Satellite Communications" under the untouched default,
      but Table D-VI prints "Airmobile/Air Assault" there, "US only"
      remark and all. Milsymbol's own naming (`_STD2525`, its
      `setStandard("2525"/"APP6")` entry point) implies this branches on
      MIL-STD-2525-vs-STANAG-APP-6, but empirically the printed
      MIL-STD-2525D document agrees with the "APP6"-labelled branch at
      every one of these 8 codes - a mislabelling or genuine bug inside
      milsymbol itself, not a standards question. This is a strictly
      worse defect than a wrong label: a user picking a correctly-named
      modifier would have gotten a **confidently wrong glyph**, the same
      class of bug as the Coast Guard/Law Enforcement Vessel mix-up two
      days ago, just one level deeper (in the vendor's icon selection
      rather than in this project's own labelling).
      **Fixed by patching the vendored file** - `military_symbology/
      vendor/milsymbol.js`, 8 icon references swapped, first-ever edit
      to vendored milsymbol in this project (there is a precedent for
      patching vendored code, `core/mgrs_engine.py`'s UPS validation
      fix, just not in this file before). `ms.setStandard("APP6")` was
      considered and rejected: that flag is a single mutable property on
      the shared `ms` module singleton, so flipping it globally would
      change every OTHER symbol anywhere in the library that also
      branches on it, not just these 8 codes. Confirmed each of the 16
      icon keys involved (8 codes x 2 branches) is referenced **exactly
      once** anywhere in milsymbol's own numbersidc/sidc tables, so the
      swap cannot reach any other rendering path. Patched file is
      byte-identical in size to the original - only the 8 assignments
      changed. `THIRD_PARTY_NOTICES.md` and `docs/developer-guide.md`'s
      vendored-code list both updated with the full evidence; "vendored
      unmodified" no longer describes this file.
      `MODIFIERS["ground_unit"]` built as **76 sector-1 + 57 sector-2 =
      133 codes**, transcribed longhand from the PDF rather than copied
      from either unsafe source, `_UNIT_SECTOR1_LABELS`/
      `_UNIT_SECTOR2_LABELS` matched to it, both wired into
      `add_land_unit_layer()`. Two sibling codes (37/38, both named
      "Recovery" with a different parenthetical qualifier the standard
      slugifier drops) given explicit, self-explanatory keys rather than
      the generator's generic disambiguation fallback.
      All 133 modifiers verified to render without error and to change
      the symbol from its bare form; the 8 patched codes additionally
      pinned by their exact post-patch glyph fragment, with the
      pre-patch (wrong) fragments asserted absent. 1385 -> 1395 tests on
      QGIS 4.2.1 and 3.44.12; Bandit clean.
    - **E-8 CLOSED, 2026-08-18: the 93 common sector 1/2 modifiers wired
      into the shared point-layer factory.** Left open after D-4b as a
      confirmed-by-hand mechanism, not yet built in - this is the build.
      `sidc.py` gained `common_modifiers_for_edition(edition)` (the
      2525E-only `{"sector1": ..., "sector2": ...}` common tables, {}
      under 2525D) and `_resolve_modifier()`, which checks a symbol
      set's own table first and the common one second, returning both
      the 2-digit code and whether it came from common.
      `build_sidc()` now appends digits 21/22 (0-indexed positions
      20/21) - "1" per sector that resolved via common, "0" otherwise -
      but ONLY when at least one sector needs it, so every existing
      call, including every 2525D one, keeps producing the exact
      20-character string it always has. Confirmed against milsymbol's
      own `frameshape = sidc.substr(22,1)` reader, the same positional
      mechanism one digit further along.
      `_point_symbol_layer.py`'s `build_single_domain_point_layer()`
      merges the common labels into a symbol set's OWN sector1/2 label
      dict (new `_merge_common_labels()`) - additive to a dropdown that
      already exists, never used to create one where 2525E has no
      per-set vocabulary at all, matching how the per-set 2525E swap
      already behaved.
      **One real defect found doing this, not assumed away**: a handful
      of keys - "biological" (Ground Unit/Land Equipment/Land
      Installation sector 1), "long_range"/"medium_range"/"short_range"
      (Air Missile/Space Missile sector 2), "close_range" (Space Missile
      sector 2) - exist in BOTH a symbol set's own table and the common
      one, same label, different code. `_resolve_modifier()` and
      `_merge_common_labels()` both give the own-set entry precedence on
      a collision, so the dropdown never offers two identical-looking
      choices that silently resolve differently, and `build_sidc()`
      agrees with what the dropdown actually offers.
      A second, separate finding surfaced while re-pointing an existing
      test at the new behaviour: Land Installation's own 2525E sector1
      table drops "chemical" ({Disused}, per D-3), but the KEY still
      resolves under 2525E now - through the common table's own
      "Chemical" (code 138), a different and legitimate code rather than
      the retired one. Not a bug; exactly what the common namespace is
      for. `test_modifiers_resolve_per_edition` had been asserting
      "chemical" fails under 2525E - true before E-8, false after -
      moved to "petroleum" (genuinely disused with no common-table
      counterpart) for the fails-under-2525E case, with the "chemical"
      finding pinned as its own test.
      `test_2525e_layer_drops_the_disused_sector1_modifiers` (Land
      Installation) updated the same way - it had asserted the dropdown
      offers exactly the seven live own-set codes; it now offers those
      seven plus the common table's, which is the point of this work.
      1403 tests (1395 -> 1403) on both QGIS 4.2.1 and 3.44.12; Bandit
      and detect-secrets both clean.
  - **Mini-Phase E (Appendix E, Sea Surface) done 2026-08-08.** New
    `military_symbology/sea_surface_layer.py` builds one "Tactical
    Graphics - Sea Surface" layer (symbol set `30`, Table A-III) - no
    missile-family companion to merge in, unlike Space/Air, since the
    standard has no separate "Sea Surface Missile" symbol set. No
    echelon/headquarters (Table E-II confirms neither applies, same
    finding as every icon-based appendix so far).
    - **Full vocabulary this time, not curated** - applying the lesson
      from the Land Equipment/Installation gap directly: `sea.js` has
      only 93 entities (vs. Land Unit's 219/Land Equipment's 229), small
      enough that full coverage was the more consistent choice.
      `ENTITIES["sea_surface"]` replaced (was a 20-entry curated subset)
      with all 93, verified via the same full multi-line-aware parse
      used to catch the Land gap - zero entities excluded, zero invalid
      codes, zero duplicates. Includes Table E-VI's "Own Ship" (150000 -
      Combat Information Center-internal, friend-only, 1L diameter) and
      Table E-VII's "Fused Track" (160000 - a track still being
      classified, always pending status).
    - **Sector 1/2 modifiers also fully built** (`MODIFIERS
      ["sea_surface"]`, 25 sector 1 + 16 sector 2 codes - the complete
      set, cross-checked against `sea.js`'s own `sIdm1`/`sIdm2` exactly)
      - Sea Surface's own modifier tables are compact enough (unlike
        Land's 50+ per sector) that there was no reason to defer them.
    - `unit_layer.py`'s `sea_surface` entry removed entirely (`air` and
      `ground_unit` already gone) - only `subsurface` remains there now,
      pending Appendix F, which will retire the whole multi-domain/
      cascading-dropdown module. `DEFAULT_SYMBOL_SET`/default entity
      changed from `sea_surface`/`frigate` to `subsurface`/`submarine`;
      `tests/test_unit_layer.py` updated to match (its own "second
      entity" integration test now uses two different `subsurface`
      entities instead of `sea_surface`/`subsurface`, since only one
      domain remains to compare against).
    - New `icons/tactical_graphics_sea_surface.svg` and
      `tests/test_sea_surface_layer.py`. 457 tests passing on both QGIS
      3.44.12 and 4.2.0.
  - **Mini-Phase F (Appendix F, Subsurface + Mine Warfare) done
    2026-08-08 - closes out the user's originally-reported bug.** New
    `military_symbology/subsurface_layer.py` builds two layers -
    "Tactical Graphics - Subsurface" (symbol set `35`) and "Tactical
    Graphics - Mine Warfare" (symbol set `36`, Table A-III) - added
    together under one toolbar action, same "several genuinely distinct
    layers, one action" precedent as Land (Mine Warfare's own 64-entity
    vocabulary is too large to fold into a companion the way Space/Air
    Missile's single entity was). No echelon/headquarters (Table F-II
    confirms neither applies).
    - **Root cause of the original bug found and fixed structurally, not
      by patching the code that was already correct.** The user's report
      was "Subsurface - Military Generic is in Air, Sea Surface [but not
      working for Subsurface]." Investigated directly: `ENTITIES
      ["subsurface"]["military"]` (`"110000"`) was already correct and
      matches `subsurface.js`'s own `"SU.IC.MILITARY"` exactly - not a
      code bug at all. The actual cause was almost certainly the old
      shared `unit_layer.py`'s ValueRelation-based cascading "Entity"
      dropdown, which that module's own docstring already flagged
      earlier this project as having a confirmed native-crash risk
      during development. Resolved by removing that whole mechanism
      from Subsurface's path entirely - its own dedicated layer uses a
      plain `ValueMap` dropdown, no cascading, no shared-layer
      entity-collision risk.
    - **Full vocabulary for both** (continuing the policy established
      for Sea Surface): `ENTITIES["subsurface"]` replaced (was an
      8-entry curated subset) with the full 22 entities from
      `subsurface.js`; new `ENTITIES["mine_warfare"]` is the full 64
      entities from `minewarfare.js` (excludes only code `140000`,
      which milsymbol's own source marks reserved with an empty icon
      list, the same pattern as Air's `110106`). Mine Warfare's own
      MILCO (Mine-Like Contact) entries have real confidence-level
      (1-5) sub-variants for each position (general/bottom/moored/
      floating) - the same kind of systematic sub-code axis that was
      missed for Land Equipment before the user caught it - caught here
      up front by the same full multi-line-aware parse, not missed
      again. Both dicts verified programmatically: every code exists in
      source, zero duplicates, zero missing real entries.
    - **Subsurface's own sector 1/2 modifiers also fully built**
      (`MODIFIERS["subsurface"]`, 22 sector 1 + 17 sector 2 codes, exact
      match against `subsurface.js`'s own `sIdm1`/`sIdm2`). Mine Warfare
      has none at all - not a curation choice, milsymbol's own
      `minewarfare.js` source has zero `sIdm1`/`sIdm2` entries.
    - **`unit_layer.py` fully retired** - Subsurface was its last
      remaining domain (Space/Air/Land/Sea Surface all already moved
      out). Deleted `military_symbology/unit_layer.py`,
      `tests/test_unit_layer.py`, and the now-orphaned
      `icons/tactical_graphics_units.svg` (deletion confirmed explicitly
      with the user first - the auto-mode permission classifier blocked
      the first attempt as a destructive action). `plugin.py`'s entire
      "Tactical Graphics - Units" action wiring (import, `__init__`
      slot, setup method, menu-removal list, unload nulling, callback)
      removed; `tests/test_plugin.py`'s toolbar-action-list and
      unload-clears-references tests updated to expect the five new
      per-appendix actions instead.
    - New `icons/tactical_graphics_subsurface.svg` and
      `tests/test_subsurface_layer.py` - including a test naming the
      original bug report directly (`military` entity resolves
      correctly on the new dedicated layer) and one exercising a MILCO
      confidence-level variant. One test-writing mistake caught by the
      suite itself and fixed in the same pass: an early version of the
      new tests' own `_resolve_svg_path()` helper left the
      `sector1_modifier`/`sector2_modifier` feature attributes NULL
      instead of an explicit empty string when a test didn't care about
      them, which resolves to a different (and in this case failing)
      SIDC than `""` does - fixed to always set them explicitly (only
      when the field exists on that particular layer, since
      `QgsFeature.setAttribute()` by name raises `KeyError` for a field
      that doesn't exist, confirmed live rather than assumed). 451 tests
      passing on both QGIS 3.44.12 and 4.2.0.
  - **Same-day follow-up: Land Equipment's newly-added weapon variants
    were mislabeled, caught by the user, not self-discovered - second
    correction in a row for this same dict.** The user pointed out that
    16 weapon categories' own X01/X02/X03 sub-variants (machine gun,
    grenade launcher, air defense gun, antitank gun, direct fire gun,
    recoilless gun, howitzer, missile launcher, air defense missile
    launcher, antitank missile launcher, antitank rocket launcher,
    surface-to-surface missile launcher, mortar, single/multiple rocket
    launcher, and rifle) were labeled Short/Intermediate/Long Range in
    the previous pass - checked directly against the standard's own
    Table D-XI (printed pages 229-242, not just milsymbol.js): 15 of
    the 16 are actually **Light/Medium/Heavy**, and rifle specifically
    is **Single Shot/Semiautomatic/Automatic** (genuinely different from
    every other category, confirmed page 229 - the user's own
    expectation that rifle should also be "light/medium/heavy" turned
    out not to match the standard's own text either, worth noting since
    it's the one place this session's finding diverged from the user's
    own guess too, not just from the earlier code). Root cause: labels
    were built from milsymbol.js's own internal icon-part constant
    strings (e.g. `"GR.EQ.SHORT RANGE"`) instead of the standard's
    actual printed text - those turned out to be milsymbol's own
    internal graphics-composition labels, unrelated to the doctrinal
    category name. Renamed all 48 affected entity keys in `sidc.py`'s
    `ENTITIES["land_equipment"]` (codes themselves unchanged - this was
    a naming-only bug, not a wrong-code bug) and the matching labels in
    `land_layer.py`'s `_EQUIPMENT_ENTITY_LABELS`, both via scoped Python
    rewrites (not manual editing, given 48 keys across two files) with
    an assertion-based verification pass confirming: no `_short_range`/
    `_intermediate_range`/`_long_range` substrings remain, all 145
    entity codes still verified against `landequipment.js`, and
    `land_layer.py`'s label keys still match `sidc.py`'s entity keys
    exactly (empty set difference). Legitimate `short_range`/
    `long_range` keys elsewhere (missile-range sector modifiers for Air
    Missile/Space Missile/Sea Surface, a genuinely different, correct
    use of "range" terminology) were left untouched - confirmed by
    scoping every rename to the `land_equipment` entity block
    specifically, not a blind find-and-replace. 451 tests still passing
    on both QGIS 3.44.12 and 4.2.0 (no test referenced the renamed keys
    by name, so none needed updating - only the two source files
    themselves and their own module-docstring/comment wording, which was
    also updated to stop citing the wrong terminology as an example of
    what the earlier gap covered).
  - **Mini-Phase G (Appendix G, Activities) done 2026-08-08.** New
    `military_symbology/activities_layer.py` builds a single "Tactical
    Graphics - Activities" layer (symbol set `40`, Table A-III) - no
    companion symbol set to merge in, unlike Space/Air Missile. No
    echelon/headquarters fields (Table G-II lists neither - and its own
    "S" field is actually "Offset Location Indicator", not Field S from
    Table VII's master list, so this isn't even a same-letter collision
    to worry about).
    - **Full 153-entity vocabulary**, cross-checked against `activites.js`
      via the same full multi-line-aware parse used for every appendix
      so far - `set(ENTITIES["activities"].values()) ==` every `sId[...]`
      code in the source, exactly, zero gaps and zero extras. Includes
      the hierarchy-only parent codes (`110000`/`130000`/`150000`/
      `180000`, etc.) that milsymbol's own source marks with an empty
      icon list ("No icon is associated with this entity. It is for
      hierarchal purposes only.", confirmed against Table G-III's own
      remarks column) - these still render a valid frame-only symbol,
      same pattern as similar top-level codes elsewhere (e.g. Space's/
      Air's own generic "military").
    - **A genuine label-accuracy check this time, not just a code check
      - given the Land Equipment lesson two mini-phases ago.** Rendered
      Table G-III's own DESCRIPTION column via `pdftotext -layout`
      (printed pages 357-363) and spot-checked milsymbol's internal icon
      constant strings against it directly (e.g. code `110110`: the
      standard's own text is "Civil Rioting", milsymbol's constant is
      `"ST.IC.RIOT"`). Concluded this is a different, lower-risk
      situation than Land Equipment's bug: milsymbol's Activities
      constants are already literal, specific entity names (just
      sometimes abbreviated), not an internal composition-axis label
      standing in for a genuinely different doctrinal category the way
      `"SHORT RANGE"` was. Kept milsymbol's naming as the label source
      (Title-Cased) rather than hand-transcribing all 153 from OCR'd
      table text, which would have traded one error mode (abbreviation)
      for a worse one (OCR misreads across ~150 entries) - documented
      explicitly in `sidc.py`'s own comment on `ENTITIES["activities"]`
      so this judgment call is visible, not silent.
    - **Sector 1 modifiers built from the standard's own Table G-IV, not
      milsymbol's source as-is - a real, caught discrepancy.** Appendix
      G's own text states explicitly "there are no sector 2 modifiers in
      activities symbols" (G.5.3.1 step 3), and Table G-IV (printed
      pages 383-385) itself only defines sector 1 codes `01` through
      `18` ("Theft") - the table physically ends there (next page
      blank, then Appendix H begins). milsymbol's own `activites.js`
      source, however, defines four EXTRA `sIdm1` codes (`19`-`22`:
      hijacker, cyberspace, eviction, raid) and two `sIdm2` codes
      (`01`-`02`: cyberspace, security force assistance) with no
      corresponding row in Table G-IV at all. Trusted the standard's own
      text/table over milsymbol.js per this project's standing
      verification policy - `MODIFIERS["activities"]` has only the 18
      sanctioned sector 1 codes and no sector 2 entry; `activities_layer.py`
      correspondingly has no sector 2 field. Code `09`'s label uses the
      standard's own current wording ("Written Military Information
      Support Operations", Table G-IV's own category column) rather than
      milsymbol's older "WRITTEN PSYCHOLOGICAL OPERATIONS" constant.
    - New `icons/tactical_graphics_activities.svg` (alert-triangle
      glyph) and `tests/test_activities_layer.py` (vocabulary-coverage,
      field-list, entity/sector1-modifier render tests, including the
      hierarchy-only generic entity). `plugin.py` wired the same way as
      every other single-domain appendix (import, `__init__` slot, setup
      method + action, menu-removal list, unload nulling, callback);
      `tests/test_plugin.py`'s toolbar-action-list and
      unload-clears-references tests updated for the new action. 461
      tests passing on both QGIS 3.44.12 and 4.2.0.
  - **Appendix I (METOC) - triaged 2026-08-08, decided not needed, no
    code written.** Read the appendix's own scope section (I.1-I.5.3)
    and counted every entry across its three tables directly from the
    standard: Table I-I Atmospheric (symbol set `45`, 205 entries -
    Pressure Systems, Turbulence, Icing, Winds, Cloud Coverage, Weather
    Symbols, Bounded Areas of Weather, Isopleths, State of the Ground),
    Table I-II Oceanographic (symbol set `46`, 206 entries - Ice
    Systems, Hydrography, Oceanography, Geophysics/Acoustics, Limits,
    Man-Made Structures), and Table I-III Meteorological Space (symbol
    set `47`, exactly 1 entry - a hierarchy-only placeholder, nothing to
    build there). Confirmed directly against milsymbol-3.0.4's own
    source, three separate ways - its `dimensionMapping` (every symbol
    set it recognizes at all), every actual `symbolSet == "NN"` dispatch
    check across every `sidc/*.js` file, and a direct grep of the
    vendored built file this plugin ships - that **none of symbol sets
    `45`/`46`/`47` exist anywhere in milsymbol**, unlike every other
    appendix covered so far (B-G), which all leaned on milsymbol's own
    rendering. Every one of the ~411 real entries (410 excluding the
    trivial placeholder) would need fully custom hand-built SVG/QGIS
    symbology from scratch - many with dynamic draw rules (a
    pressure-tendency digit next to a plot circle, variable-feather wind
    barbs, periodic teeth/scallops on a front line) and literal,
    non-affiliation-based colors, closer in kind to Appendix H's
    hand-drawn control measures than to B-G's icon-in-frame lookups, but
    at roughly the scale of the entire rest of the standard combined.
    Presented this triage to the user with three scoping options
    (curated core subset / full 411-entry coverage / one-category-at-a-
    time); **the user decided to skip Appendix I entirely - "no felt
    need"** for this plugin's own use case, rather than commit to any
    partial build. Explicitly not a technical blocker and not
    permanently closed: if a future need for METOC symbology comes up,
    it's a normal collaboration/feature request, not a re-triage - the
    counts and category breakdown above are the starting point. Skipped
    with no source, test, or plugin-wiring changes; `docs/user-guide.md`
    gets a short "not covered" note in its own tactical-graphics section
    for anyone looking for it. Appendix J (SIGINT) is next per the
    plan's strict document order.
  - **Mini-Phase J (Appendix J, SIGINT) done 2026-08-08 - the user chose
    to hold Appendix H and jump straight to J.** New
    `military_symbology/sigint_layer.py` builds a single "Tactical
    Graphics - SIGINT" layer, but this appendix is structurally
    different from every one built so far (B-G): Table J-II's own
    SymbolSetCode column lists the exact same four entity codes (Signal
    Intercept/Communications/Jammer/Radar) against FIVE different symbol
    sets at once - Space (`50`), Air (`51`), Land (`52`), Sea Surface
    (`53`), Subsurface (`54`) - chosen by which "dimension" the SIGINT
    platform is actually in (J.5.3.3), not by a different entity code
    per dimension the way every other appendix works.
    - **Extended the shared `_point_symbol_layer.py` factory rather than
      hand-rolling a bespoke layer module.** Added a small, fixed
      "Dimension" field mechanism (`dimension_labels`/
      `dimension_symbol_sets`/`default_dimension`, at most 5 known
      values) that drives a CASE expression on symbol_set - genuinely
      different from the existing `entity_symbol_set_overrides`
      mechanism (which is entity-keyed and explicitly documented as
      "not meant for large-scale mixing," which SIGINT's 4×5 = 20
      combination would have been) and NOT a reintroduction of
      `unit_layer.py`'s old ValueRelation cascading dropdown (a plain
      ValueMap on a literal small field, no lookup layer, no
      previously-documented crash risk). `sidc.py`'s own
      `ENTITIES["sigint_space"/"sigint_air"/"sigint_land"/
      "sigint_sea_surface"/"sigint_subsurface"]` and
      `MODIFIERS["sigint_*"]["sector1"]` are all the SAME dict object
      referenced under five keys (not five hand-copied duplicates) -
      `build_sidc()` looks entities/modifiers up as
      `ENTITIES[symbol_set][entity]`, so a single source of truth here
      is both correct and impossible to let drift across the five keys.
    - **Full vocabulary, cross-checked against milsymbol's own
      `signalsintelligence.js` and the standard's own Table J-II/J-III**
      (printed pages 771-782): all 4 entity codes match exactly; sector 1
      has 64 of milsymbol's 65 modifier codes - code `65` ("Cyber") has
      no corresponding row in Table J-III, which physically ends at code
      `64` ("Experimental", next page blank, then Appendix K begins) -
      excluded as unsanctioned by the standard, the same call already
      made for Activities' own extra codes. milsymbol's single
      `sIdm2["01"]` ("Cyber") is likewise excluded entirely - J.5.3.2's
      own text states explicitly "There are no sector 2 modifiers in
      SIGINT."
    - **No echelon/headquarters fields, a deliberate, documented
      simplification rather than a fabricated rule.** J.5.3.3's own text
      says a SIGINT symbol "shall follow the amplifier requirements as
      stated in [the matching dimension's] appendix" - which would
      suggest Echelon should appear for a Land-dimension SIGINT entity,
      say - but WHICH of Appendix D's own four Land layers' amplifier
      rules would even apply to a SIGINT entity (not a Land Unit/
      Civilian/Equipment/Installation entity itself) is genuinely
      ambiguous from the appendix's own cross-reference. Documented this
      explicitly in `sigint_layer.py`'s own docstring rather than
      guessing a per-dimension conditional field set.
    - New `icons/tactical_graphics_sigint.svg` (antenna-with-signal-arcs
      glyph), `tests/test_sigint_layer.py` (vocabulary-coverage,
      field-list, cross-dimension entity-resolution, sector1-modifier,
      and hierarchy-only-entity render tests), and a new
      `TestDimensionField` class in `tests/test_point_symbol_layer.py`
      exercising the shared factory's own new mechanism directly (field
      placement before Entity, dropdown/default value, cross-symbol-set
      resolution) - decoupled from SIGINT's own vocabulary the same way
      the rest of that test file already is. `plugin.py` wired the same
      way as every other single-domain appendix; `tests/test_plugin.py`
      updated for the new action. 476 tests passing on both QGIS 3.44.12
      and 4.2.0.
  - **Mini-Phase L (Appendix L, Cyberspace) done 2026-08-08 - the user
    confirmed the SIGINT amplifier judgment call and asked to continue
    straight to L, holding H for later.** New
    `military_symbology/cyberspace_layer.py` builds a single "Tactical
    Graphics - Cyberspace" layer, symbol set `60` - unlike Appendix J,
    Table L-II's own SymbolSetCode column uses only `60` throughout
    (never a comma list), so despite L.5.3.3 using the exact same
    "amplifiers depend on the symbol's dimension" boilerplate text as
    J.5.3.3, this appendix does NOT actually span multiple symbol sets -
    read as general amplifier guidance rather than a real per-dimension
    field requirement, so no Dimension field was built for it (a single,
    plain `add_single_domain_point_layer()` call, the simplest layer
    since Sea Surface).
    - **First appendix where milsymbol's own source is edition-aware,
      and it mattered.** `cyberspace.js` has `edition == "D" ? ... : ...`
      ternaries on several codes (e.g. `110100` renders "Command and
      Control (C2)" in edition D, "Combat Mission Team" in a later
      MIL-STD-2525E/APP-6E branch). Confirmed this project's own
      `build_sidc()` always sets SIDC version `"10"`, which milsymbol's
      own `metadata.js` maps to `edition = "D"` unconditionally - so
      every appendix built so far has always been rendering the "D"
      branch already, just never one with an actual fork before. Picked
      the "D" branch's own icon for every ternary here and cross-checked
      the result directly against Table L-II's own printed text (not
      just trusted because it's labeled "D").
    - **22 of milsymbol's 72 `sId` entries excluded - two distinct
      groups, both confirmed absent by Table L-II's own physical page
      boundary** (ends at code `160900`, then a blank page, then the
      standard's own INDEX begins - no further Appendix L content):
      six codes (`110500`-`111000`) that are either explicitly commented
      `// Disused` in milsymbol's own source or have no "D"-edition
      value defined at all, and the entire `170000`-`180000` block
      (Server/Workstation/Mobile/Tablet/Laptop/IoT device-type entries)
      - reads like a 2525E/APP-6E-only addition, never actually part of
      2525D's own Appendix L. Final count: 50 real entities, cross-
      checked programmatically (every remaining code exists in source,
      zero duplicates, `ENTITIES["cyberspace"]` label keys match
      `cyberspace_layer.py`'s own exactly).
    - **No modifier fields at all - the strictest case yet.** L.5.3.2's
      own text states explicitly "There are no modifiers in cyberspace
      symbols" (also in Table L-I's own step 2 note) - milsymbol's
      source nonetheless defines 13 `sIdm1` and 8 `sIdm2` codes with no
      table of any kind in the standard's own Appendix L to sanction
      them (unlike Activities/SIGINT, which each had a real, smaller
      modifier table this project trimmed down to). Excluded entirely -
      no `MODIFIERS["cyberspace"]` entry exists, the same "no entry at
      all" pattern Mine Warfare already established.
    - New `icons/tactical_graphics_cyberspace.svg` (server-rack-with-
      network-node glyph) and `tests/test_cyberspace_layer.py`
      (vocabulary-coverage, no-modifiers-entry, field-list, hierarchy-
      only-entity, and same-name-different-code render tests - "Network
      Outage" legitimately appears twice under different categories,
      codes `130200` and `160700`). `plugin.py` wired the same way as
      every other single-domain appendix; `tests/test_plugin.py` updated
      for the new action. 485 tests passing on both QGIS 3.44.12 and
      4.2.0. This closes out the appendix-by-appendix plan's point-
      symbol appendices (A-G, J, L) - only Appendix H (Control
      Measures, held at the user's request) and the already-skipped
      Appendix I (METOC) remain.
  - **UI housekeeping (2026-08-08) - too many flat toolbar icons after
    eight appendices' worth of tactical graphics actions accumulated
    alongside every other tool.** The main toolbar had grown to 25
    individual top-level items (one "About" action plus 24 more); the
    user asked for logical grouping in both the toolbar and the Plugins
    menu. Grouped everything except "About" into six dropdown buttons
    (`_setup_toolbar_groups()`/`_build_toolbar_group()` in `plugin.py`,
    new `icons/group_*.svg`): **Grid** (UTM/MGRS 100km/Sub Grid/Clear
    Grid), **Navigation** (Coordinate Probe/Bearing-Range), **Terrain
    Analysis** (Tanaka Contours/Hypsometric Tint/Hillshade
    Combinations/Line of Sight/Viewshed), **Waypoints** (Import/
    Export), **Print Production** (New Military Layout/Map Sheet
    Series), and **NATO Symbols** (all eight point-symbol layers plus
    Control Measures - named per the user's own explicit request for a
    single common icon over "these symbology, the mil-std ones").
    - **One QMenu per group, shared by both surfaces** - a QToolButton
      with an InstantPopup dropdown on the toolbar (same mechanism the
      existing Sub Grid control already used, just generalised), and
      the SAME QMenu instance's own `menuAction()` added once via
      `iface.addPluginToMenu()` to nest as a nested Plugins-menu
      submenu - clicking either surface shows identical items in
      identical (checked/unchecked) state, since they're the literal
      same QAction objects underneath, not two independently-built
      copies that could drift apart.
    - **`_build_action()` gained a `standalone` parameter** (every
      individual action's own call site now passes `standalone=False`
      explicitly - kept as an explicit per-call decision rather than
      flipping the method's own default, matching this project's
      general preference for explicit over implicit) - when `False`,
      the action is built (icon/tooltip/callback wired) but not
      auto-attached to the toolbar/Plugins menu; the new grouping step
      places it instead, once every individual action already exists.
    - **Sub Grid folded into the Grid group as a nested flyout**
      (`sub_grid_menu.addMenu()`-style nesting) rather than staying a
      second standalone toolbar widget next to the new Grid button -
      the old `sub_grid_button` QToolButton wrapper was removed
      entirely (the bare QMenu now nests directly), simplifying
      `_setup_sub_grid_menu()` and removing four individual
      `addPluginToMenu()` calls for its own spacing options (now
      reachable solely through the Grid group's own single menu entry).
    - `unload()`'s own Plugins-menu detach step shrank from a
      25-entry explicit list down to `[self.action] + [menu.menuAction()
      for menu in self.group_menus.values()]` - only top-level entries
      need explicit detaching before `sip.delete(self.toolbar)`, since
      individual grouped actions were never registered with the
      Plugins menu directly in the first place, only added into their
      own group's QMenu.
    - `tests/test_plugin.py`'s toolbar-structure test rewritten
      entirely - it used to assert flat toolbar action text; now
      asserts the "About" action is the only standalone toolbar item
      and that each of the six `plugin.group_menus[key].actions()`
      lists match the expected per-group order exactly (plus Sub
      Grid's own 4 nested options unaffected by the move).
      `docs/user-guide.md`'s "toolbar, at a glance" table rewritten for
      the new grouped structure; its "Tactical Graphics" section
      re-pointed to describe the NATO Symbols dropdown instead of
      implying standalone toolbar buttons. 486 tests passing on both
      QGIS 3.44.12 and 4.2.0. Live-tested in real QGIS by the project
      maintainer 2026-08-08 - both the toolbar dropdowns and the nested
      Plugins-menu submenus check out correctly.
  - **Mini-Phase H0 (2026-08-09) - the appendix-by-appendix plan's own
    Appendix H pass begins.** First of 20 sequential H-subphases (see
    this phase's own "Appendix H - Control Measure Symbols" plan table);
    covers H.5.1-H.5.4's general rules plus H.5.5 Boundaries. Re-auditing
    H.5.1-H.5.4 against the standard's actual text (not assumed from the
    original stage-based pass) found two real, general defects, both
    fixed:
    - **H.5.1.1.1/H.5.3 Coloring was wrong for neutral/unknown
      affiliation.** The actual text - "black, blue (friendly), red
      (hostile), green (neutral or obstacles), or yellow (unknown ...)" -
      lists five distinct colours; the previous implementation folded
      neutral AND unknown into "black as standard" alongside a true
      unaffiliated default, losing the standard's own green/yellow
      entirely. Fixed by giving `control_measures.py` a genuine 5th
      affiliation value, `"unspecified"` (default, renders black),
      alongside friend=blue/hostile=red/neutral=green/unknown=yellow -
      deliberately NOT identical to `sidc.py`'s own 4-value AFFILIATIONS
      any more, since only control measures get this extra colour per
      H.5.1.1.1's own text (point symbols' Table XV/XVI scheme has no
      "black" option at all). The old `TestAffiliationLabelsMatchSidc`
      equality guard became a subset guard instead
      (`TestAffiliationLabelsMatchSidc`/`TestEchelonLabelsMatchSidc` in
      `tests/test_control_measures.py`).
    - **H.5.4 Labeling's "all text labeling shall be in upper case
      letters" had never been implemented.** Fixed by wrapping every
      designation label expression in `upper()` - applies to every
      measure type on both the Lines and Areas layers, a pure display
      change with no risk to any measure type's own shape/colour choices.
    Two further general H fields - `status` (H.5.1.1.3/Table H-I:
    present=solid, planned=dashed - Boundary's own template shows
    explicit Friendly Present/Friendly Planned/Enemy Known/Enemy
    Suspected rows) and `echelon` (H.5.1.1.6, cross-referencing Table
    D-III of the Land appendix) - were added to the Lines layer's schema,
    since Boundary needs both, but wired into rendering for `"boundary"`
    only so far; every other existing measure type is untouched pending
    its own future H-subphase (documented as a deliberate "add the field
    now, wire it up measure-type by measure-type" approach, not an
    oversight).
    - **Boundary itself rebuilt from an invented dash-dash-dot
      placeholder into Table H-III's real construction**, found by
      rendering the actual template page (395) as an image rather than
      trusting extracted text: a status-driven solid/dashed line with
      the Field B echelon glyph (Table D-III's own Ø/•/••/•••/I/II/III/
      X/XX/XXX/XXXX/XXXXX/XXXXXX/++, confirmed by rendering Table D-III's
      own page (172) as an image too, since OCR renders "Ø" as "0" and
      "•" as ".") centred on each anchor-point segment via
      `Placement.SegmentCenter` - "the line segment between each pair of
      anchor points will repeat all information", which SegmentCenter
      gives for free (one marker per segment, not one for the whole
      line). The glyph sits on a small white-filled square, sized by its
      own character count (`_ECHELON_BOX_SIZE_EXPRESSION`) so it reads
      over the line - a fixed box size looked fine for "XX" (Division)
      but badly clipped "XXXXXX" (Theater), caught only by rendering
      every echelon level through the real symbol side by side via
      `QgsMapRendererCustomPainterJob`, not by eyeballing one case.
      Table H-III's own two independent T/AS unit-designation labels
      (one per adjacent unit) are approximated as a single two-line
      label (`unique_designation` + a new boundary-only
      `far_designation` field) rather than two independently positioned
      ones, since QGIS's PAL labelling places one label per feature.
      Figure H-3's own compass-relative label rotation (horizontal vs.
      vertical boundary orientation) is not attempted - along-line
      placement is used instead, a documented simplification, same as
      the standard's own literal line-gap-around-the-boxed-glyph
      (QGIS has no such primitive to build on).
    - **sidc.py's own ECHELONS dict (and every point-symbol layer's
      Echelon dropdown, via `_point_symbol_layer.py`'s shared
      `_ECHELON_LABELS`) had been capped at "Army" since sub-phase 10.1**
      - Table D-III's three highest levels (Army Group, Theater, Command)
      were simply never added, confirmed missing from EVERY appendix
      built so far (B through L), not just something Boundary happened
      to need. Extended `ECHELONS`/`_ECHELON_LABELS` to the full 14
      levels, cross-checked against milsymbol.js's own `echelonMobility`
      table (24="Army Group/front", 25="Region/Theater", 26="Command"),
      found while reading H.5.1.1.6's own cross-reference to Table D-III.
    495 tests passing on both QGIS 3.44.12 and 4.2.0 (up from 486);
    render-and-compare verified via `QgsMapRendererCustomPainterJob` for
    both a multi-affiliation/status boundary set and all 14 echelon
    levels (the box-sizing bug above was caught this way, not by
    inspection of the code). Appendix H's remaining 19 sub-phases
    (H1-H22, see this phase's own plan table) are still pending.
  - **H0 follow-up (2026-08-09), from the project maintainer's own live
    QGIS testing**: two real defects. The label/echelon-gap collision was
    fixed in one pass; the echelon glyph's own "gap in the line" took
    three real attempts before landing on the actual right tool.
    - **The echelon glyph's background wasn't a clean gap - Table H-III's
      own EXAMPLE column (re-checked by rendering the actual page image)
      shows the line breaking exactly around the glyph, no box/border/
      halo shape standing in for the gap at all.** Three attempts, each
      one caught by the maintainer rendering (or live-testing) a real
      boundary over a non-white (terrain) background rather than QGIS's
      own white canvas default - text alone, and even this project's own
      offscreen renders, didn't surface every problem:
      1. A bordered white square - obviously a box against colour.
      2. Dropping just the border, keeping a solid white fill - still
         plainly a flat white rectangle against anything but white; the
         fill itself was the problem, not the outline.
      3. A white HALO around the glyph's own character stroke
         (`QgsFontMarkerSymbolLayer`'s stroke, no background shape) -
         closer in spirit (breaks the line only in the glyph's own
         shape), and this project's own offscreen renders looked clean,
         but the maintainer's real, live QGIS screenshot showed a messy
         spiky white burst around "X" instead of a crisp hourglass - real
         font/stroke rendering differed enough from this project's own
         render harness to matter.
      **Actual fix: QGIS's own Selective Masking**
      (`QgsTextMaskSettings` + `QgsSymbolLayerReference`, configured via
      `_configure_designation_labeling()`'s new `masked_symbol_layer_ids`
      parameter) - the label engine genuinely cuts a hole, in the exact
      shape of whatever text renders, in a specifically-referenced symbol
      layer (`_boundary_symbol()`'s own line layer, given a stable
      `.setId()` for exactly this purpose: `_BOUNDARY_LINE_SYMBOL_LAYER_ID`).
      This is the correct tool for the job, not an approximation of one -
      crisp for any glyph width (no more Theater-blob trade-off), and it
      let the whole 3-line label (near designation / echelon / far
      designation) fold into ONE masked, repeating label instead of a
      separate marker-line symbol layer for the echelon glyph alone (see
      the next bullet).
    - **The near/far designation label collided with the echelon glyph**
      (visible in the maintainer's own live QGIS screenshot: "612 BDE"
      rendered on top of the echelon box instead of clearly below it).
      Root cause: QGIS's own default line-label placement flags are
      `AboveLine | MapOrientation` - a multi-line label always sits
      entirely above the line, it never straddles it. Fixed with
      `Qgis.LabelLinePlacementFlag.OnLine` (centres the label block ON
      the line/anchor point, so a multi-line label naturally straddles
      it) - confirmed by rendering a real boundary feature both ways side
      by side, not assumed from the flag's own name.
      `test_line_labels_use_online_placement_not_the_default_above_line`
      is the regression guard.
    - **Follow-up request, once masking was working**: since the old
      marker-based echelon glyph used to repeat once per digitized
      segment (`Placement.SegmentCenter`), the maintainer asked for the
      label to repeat similarly rather than rendering once for the whole
      feature. QGIS's own label engine has no per-segment repeat
      (`Placement.SegmentCenter` is a marker-line-only concept), but does
      have interval-based repeat (`QgsPalLayerSettings.repeatDistance`) -
      wired in as `_BOUNDARY_LABEL_REPEAT_DISTANCE_MM` (80mm), a
      practical approximation of the standard's own per-segment rule
      (evenly spaced by screen distance, not tied to actual vertex
      positions) rather than an exact match, confirmed by rendering a
      real multi-segment (zig-zag) boundary and checking the label - and
      its masked gap - repeats correctly at each occurrence, correctly
      rotating to each segment's own local direction.
  - **Control-measures testing simplification (2026-08-09), at the
    project maintainer's own request**: `military_symbology/control_
    measures.py` previously carried ~26 measure types - the "original
    five" from sub-phase 10.1 plus a 2026-08-07 batch (H.5.11-H.5.14/
    H.5.26) - none of which had been through the appendix-by-appendix
    pass's own render-and-compare discipline. Mini-Phase H0's own
    Boundary re-audit found that specific measure type had been built
    entirely wrong, which made the maintainer's own testing harder: with
    25 other unverified measure types sitting in the same dropdown, it
    wasn't obvious which shapes were real and which were still
    placeholders. Fixed by removing every measure type this module didn't
    yet have a verified answer for, rather than leaving them in place -
    `LINE_MEASURE_TYPE_LABELS` now has exactly one entry (`"boundary"`)
    and `AREA_MEASURE_TYPE_LABELS` is empty. The removed code isn't
    commented out or hidden - it's gone from the file entirely (git
    history has it if a future sub-phase wants to compare against it) -
    each Appendix H sub-phase re-adds its own measure types, freshly
    built against the real template pictures, as it's completed: Phase
    Line/Objective/NAI likely belong to H2 (H.5.9/H.5.10, Table H-IV/H-V
    "Command and control lines/areas" - not yet confirmed which table
    each specific one sits in), Axis of Advance to H5 (H.5.13, Table
    H-X), and the rest of the 2026-08-07 batch to H3/H4/H6/H21 per their
    own H.5.x sections. `tests/test_control_measures.py` shrank from 53
    tests to 32 for the same reason - only what's still real has a test
    (33 after the masking follow-up above added its own coverage).
    475 tests passing on both QGIS versions (down from 495 before this
    day's work, up from 474 immediately after the trim, matching the
    net effect of removed-then-regained coverage).
  - **Mini-Phase H1 (2026-08-09) - H.5.6 Points, H.5.7 Lines, H.5.8
    Areas.** General construction-rule prose, no symbols of its own (0
    of the appendix's ~592 codes live in this section) - audited by
    reading the text and rendering Figures H-4/H-5/H-6 as images
    (pages 397-399), no code change. Recorded for later sub-phases:
    - **Figure H-5 (line template) confirms H0's own Boundary design
      generalises.** A line control measure's T (name)/N (ENY) labels
      sit at BOTH ends of the line, with T1 (purpose, e.g. "RFL" for
      Restrictive Fire Line)/T2 (controlling HQ, fire-support-specific)/
      W-W1 (DTG) repeating at each interior anchor-point segment - the
      same "near/far ends + per-segment repeat" shape Boundary's own
      Table H-III construction already has (H0, done independently
      before this section was read). Phase Line specifically: "PL" +
      name in Field T, marked at both ends; using phase-line-style
      labeling for OTHER lines is explicitly "not mandatory" (H.5.7's
      own text) - relevant when Phase Line itself is rebuilt (likely
      Mini-Phase H2, see that sub-phase's own plan entry).
    - **Figure H-4 (point template) applies to a NAMED SUBSET of point
      control measures only** - "sustainment, CBRN decontamination and
      special C2" tables, plus supply points (same format, with the
      supply icon placed toward the bottom instead of Field A's text
      abbreviation) - H.5.6's own text is explicit that OTHER point
      types (contact, coordination, decision, targets, etc.) "are
      formatted differently" elsewhere in the appendix. Relevant for
      the future H18 (CBRN)/H19 (Sustainment)/H20 (Supply points)/H22
      sub-phases' own work on `military_symbology/control_measure_
      points.py` - a separate module from `control_measures.py`, not
      touched this mini-phase.
    - **Figure H-6 (area template)**: type abbreviation (Field A) + name
      (Field T) centred, DTG (H/W-W1) below that, ENY markers (Field N)
      at the sides, and an echelon amplifier (Field B) at the bottom -
      relevant for H2's own Area of Operations (whose own Table H-V
      entry, read immediately after H.5.8, uses exactly this Field
      A+T convention: "AO" + a name, e.g. "AO BUFFALO") and any other
      future area type that needs an echelon.
    No test changes (no code changed); `military_symbology/control_
    measures.py`'s own docstring not touched, since this mini-phase
    didn't touch that file.
  - **Mini-Phase H2 (2026-08-09) - Table H-IV (Light Line, the only
    buildable entry beyond Boundary itself - Lateral/Forward/Rear
    Boundary are usage examples, not separate control measures, per
    that table's own "see Table H-III" cross-reference) and Table H-V
    (Area of Operations, Named/Target Area of Interest, Airfield
    Zone).** `LINE_MEASURE_TYPE_LABELS` gained `"light_line"`;
    `AREA_MEASURE_TYPE_LABELS` gained all four of Table H-V's own areas
    (previously empty since H0). Area of Operations/Named+Target Area
    of Interest/Airfield Zone all share one status-driven solid/dashed
    outline recipe (`_status_driven_area_outline_symbol()` -
    H.5.1.1.3/Table H-I's own text explicitly covers "area control
    measures", not just linear ones, so the Areas layer gained a
    `status` field the same way the Lines layer did in H0); Area of
    Operations/NAI/TAI are each labelled with a fixed type abbreviation
    ("AO"/"NAI"/"TAI") plus an optional name
    (`_AREA_DESIGNATION_LABEL_EXPRESSION`, e.g. "AO BUFFALO" - the
    standard's own examples) - confirmed the template/example pictures'
    own hexagon for NAI/TAI is illustrative, not a mandated shape (the
    DRAW RULES text itself ties the shape to the user's own anchor
    points, identical wording to Area of Operations/Airfield Zone), so
    this renders whatever polygon the user actually digitizes rather
    than forcing a regular hexagon. Airfield Zone alone has no Field A
    abbreviation in its own template - a crossed-runway icon at
    `centroid($geometry)` instead (QGIS's own "cross2" shape, a
    recognisable stand-in for the standard's own specific glyph).
    - **Two real, live-testing-caught mistakes in the first version of
      Light Line, both from the same root cause**: reading Table H-IV's
      own TEMPLATE column (page 397) at face value, where "LL"/"PT 1"/
      "PT 2" are each connected to the line by an up-arrow. The first
      version treated those arrows as drawn geometry - a real
      perpendicular "tick" mark at each end. The project maintainer
      corrected this after live-testing: those arrows are the same
      pointer/callout convention used throughout this appendix's own
      diagrams to show where a label attaches or which point is PT1 vs
      PT2 (Table H-III's own Boundary template uses identical arrows
      purely to point at anchor points) - not something to render. The
      general lesson, stated explicitly by the maintainer and now
      documented on `_end_label_layer()` for future mini-phases: this
      appendix's own EXAMPLE columns mark explanatory-only additions in
      GREY (Light Line's own example shows this directly - the real
      drawn symbol is solid black, an illustrative "PL CRAB" name next
      to it is grey) - grey is the signal for "not part of the control
      measure", not the presence or absence of an arrow/callout shape,
      which appears in plain black throughout this appendix purely as
      diagram annotation and must not be read as construction geometry.
      Fixed by removing the tick entirely - Light Line is just the line
      plus "LL" above each end, nothing else. Second, smaller mistake
      found in the same pass: the "LL" label's own offset was the wrong
      sign, rendering it below the line instead of above - fixed by
      flipping it, confirmed by rendering both signs side by side rather
      than assuming. `test_light_line_has_an_ll_label_at_each_end_with_
      no_tick` is the regression guard for both.
    - **Light Line's own optional name (H.5.7: "at both ends... or as
      often as necessary for clarity") repeats along the line the same
      way Boundary's echelon/designation label does**, since both share
      the Lines layer's one label configuration - not deliberately
      designed for Light Line specifically, but confirmed to match
      H.5.7's own general wording once noticed. This surfaced a real,
      separate bug: the shared label mask's target list only named
      Boundary's own line symbol layer, so Light Line's repeating name
      painted flat on top of the line instead of cutting a real gap (the
      line still showed through the open parts of letters like "C"/"R").
      Fixed by giving Light Line's own line a stable id too
      (`_LIGHT_LINE_SYMBOL_LAYER_ID`) and adding it to the mask's target
      list alongside Boundary's - `masked_symbol_layer_ids` is designed
      as a list for exactly this (every line measure type whose own
      label should cut a gap adds its own id).
    486 tests passing on both QGIS versions; render-and-compare verified
    via `QgsMapRendererCustomPainterJob` throughout, including the two
    Light Line corrections above.

- **2026-08-09 — two cosmetic UI fixes, requested by the project
  maintainer independently of the Appendix H work above:**
  - **Toolbar buttons are now icon-only** (`Qt.ToolButtonStyle.
    ToolButtonIconOnly` in `_build_toolbar_group()`, `plugin.py`) -
    previously text sat beside each icon (`ToolButtonTextBesideIcon`),
    which the maintainer felt was unnecessary since hovering already
    shows the function via each action's existing tooltip. The text
    itself is kept (`.setText()` still set on every action) purely for
    accessibility and for the mirrored Plugins-menu entries, which still
    show text as normal - only the toolbar button's own visible label is
    dropped.
  - **Dropped the "Tactical Graphics - " prefix from every layer name
    and toolbar/menu action label** (`unique_designation` fields
    untouched - this is purely the layer-name/action-label prefix).
    Affected the NATO Symbols dropdown's 9 actions (Space, Air, Land,
    Sea Surface, Subsurface, Activities, SIGINT, Cyberspace, Control
    Measures) and every layer name they create, across all 11
    `military_symbology/*.py` layer modules plus `plugin.py`'s own
    action labels and docstrings. Maintainer's own reasoning: with
    several of these layers active at once, QGIS's own Layers-panel
    sidebar is narrow enough that the shared, redundant prefix pushed
    the actually-distinguishing part of each name off the visible edge
    (e.g. "Tactical Graphics - Subsurface" vs. "Tactical Graphics - Sea
    Surface" - both truncate to something visually identical). The
    prefix was redundant in any case, since the toolbar group itself is
    already labelled "NATO Symbols". `docs/user-guide.md`'s own
    reference table and Control Measures section updated to match;
    `docs/user-guide.md`'s section headers/TOC anchors
    (`## Tactical Graphics - point symbol layers` etc.) were left as-is
    since those are documentation structure, not literal in-app UI
    strings.
  - Also folded in a small standing instruction from the same session:
    the Print Production toolbar group must always sort last among the
    six groups (Grid, Navigation, Terrain Analysis, Waypoints, NATO
    Symbols, Print Production) - `_setup_toolbar_groups()`'s own
    `groups` list reordered accordingly.
  - 486 tests passing on both QGIS versions (test_plugin.py's
    group-membership checks and the affected layer-name string literals
    across the layer modules' own test files, all updated to match) - no
    functional/rendering change, UI/naming only.

- **2026-08-09 — two real Mini-Phase H2 construction mistakes in
  Airfield Zone, both found and fixed after live testing** (Table H-V,
  page 400 - re-rendered and re-compared against the actual PDF page
  directly, not assumed from memory):
  - **The icon was a symmetric "X" (QGIS's own "cross2" shape); the
    standard's own template/example draws two runway lines crossing at
    an *unequal* angle** (one nearly flat, the other roughly 35 degrees
    off it) - recognisably two intersecting runways, not a generic X.
    Rebuilt `_airfield_zone_symbol()` with two independent "line"
    simple-marker layers at different angles (90 and 50 degrees -
    confirmed by rendering, QGIS's own marker "angle" is measured
    clockwise from north, so 90 is horizontal) instead of one "cross2"
    layer - still a "recognisable, not exact" stand-in (no attempt at a
    real runway heading), just an asymmetric one now.
  - **The runway-length label ("750M" in the standard's own example) was
    centred inside the boundary, overlapping the icon** - same
    `Qgis.LabelPlacement.OverPoint` placement shared with Area of
    Operations/Named Area of Interest/Target Area of Interest. The
    standard's own picture places it just *outside* the bounded area
    instead. Since AO/NAI/TAI's own labels correctly stay centred
    (matching their own "AO BUFFALO"/"NAI 1"/"TAI YUKON" examples), this
    needed a genuinely different placement for one measure type only,
    which one shared `QgsPalLayerSettings` can't express - switched the
    Areas layer from `QgsVectorLayerSimpleLabeling` to
    `QgsRuleBasedLabeling` (the labeling analogue of the renderer's own
    `QgsRuleBasedRenderer`), one rule for Airfield Zone
    (`Qgis.LabelPlacement.OutsidePolygons` - QGIS's own dedicated mode
    for labelling a polygon just outside its own boundary) and one for
    everything else (`OverPoint`, unchanged). **Caught a real
    rule-tree bug while building this**: the first version used
    `setIsElse(True)` on the "everything else" rule the same way
    `_build_rule_based_renderer()`'s own symbology rules do, and it drew
    a SECOND, wrongly-placed label on top of Airfield Zone's own correct
    one - unlike `QgsRuleBasedRenderer`, each `QgsRuleBasedLabeling` rule
    gets its own independent sub-provider, and an else-flagged rule's
    provider still placed its own label for features that had already
    matched an earlier rule. Fixed with two explicit, mutually-exclusive
    filter expressions instead of relying on `isElse` - confirmed by
    rendering all four area types side by side (AO/NAI/TAI's own labels
    unaffected, Airfield Zone's own label alone moved outside, and only
    one label per feature).
  - `_build_pal_layer_settings()` factored out of
    `_configure_designation_labeling()` so `_configure_area_designation_
    labeling()` (new) can build more than one `QgsPalLayerSettings` for
    the same layer - the Lines layer's own labeling is untouched (still
    one shared setting, `QgsVectorLayerSimpleLabeling`, since Boundary
    and Light Line don't need different placements).
  - 487 tests passing on both QGIS versions; render-and-compare verified
    via `QgsMapRendererCustomPainterJob` throughout, including a
    four-up AO/NAI/TAI/Airfield-Zone regression render.

- **2026-08-09 — Control Measures architecture split by Appendix H
  logical group, at the project maintainer's own design suggestion**:
  noticed that clicking "Control Measures" added every control-measure
  layer at once, and flagged that this would only get worse as H3-H22
  keep adding measure types to the same shared "Control Measures
  (Lines)"/"(Areas)" pair - both a Layers-panel/attribute-table
  bloat problem (every field from every H.5.x section eventually
  crammed into two giant rule trees) and a menu-UX problem (one click
  always adding more than a user actually needs). Recommended breaking
  Appendix H down by its own H.5.x logical section (C2 Measures,
  Maneuver, Defensive, Offensive, Airspace, Maritime, Deception, Fire
  Support, Targets, Target Acquisition, Obstacles, Field Fortification,
  CBRN, Sustainment, Supply, Mission Tasks, Intelligence - the same
  grouping already driving the H3-H22 mini-phase table above), mirroring
  the "own layer, own icon" principle Appendices B-L already follow for
  their point symbols instead of one shared "Tactical Graphics" layer.
  Two structural decisions confirmed before implementing: (1) rename
  H0/H2's own already-shipped layers into the new scheme immediately,
  rather than leaving one inconsistent pair behind, and (2) give
  "Control Measures" its own nested flyout submenu inside the NATO
  Symbols toolbar dropdown (one entry per H.5.x group), rather than
  flattening ~17 new entries directly into NATO Symbols' existing 8.
  - **`military_symbology/control_measures.py` (1367 lines) split into
    two files**: `_control_measure_shared.py` (new, private - mirrors
    the existing `_point_symbol_layer.py` precedent for Appendices B-L's
    own point layers) holds everything genuinely general across every
    future H control-measure group - affiliation/status/echelon field
    config and colouring, `_build_rule_based_renderer()`,
    `_build_pal_layer_settings()`/`_configure_designation_labeling()`,
    `add_layer_if_absent()`/`default_insert_position()` - and
    `c2_measures.py` (renamed from control_measures.py) keeps only what's
    specific to H.5.5/H.5.9/H.5.10 (Boundary, Light Line, Area of
    Operations, Named/Target Area of Interest, Airfield Zone). Every
    future H-group (Maneuver for H3, Defensive for H4, ...) gets its own
    new module reusing `_control_measure_shared.py`, rather than each
    reinventing this machinery or piling into c2_measures.py itself.
  - **Layer names**: `"Control Measures (Lines)"`/`"(Areas)"` →
    `"C2 Measures (Lines)"`/`"(Areas)"`. `create_control_measures_lines_
    layer()`/`create_control_measures_areas_layer()`/`add_control_
    measures_lines_layer()`/`add_control_measures_areas_layer()` all
    renamed to their `c2_measures_*` equivalents.
  - **`military_symbology/control_measure_points.py` deliberately left
    untouched** - its own flat, ~80-entity layer already spans several
    different H.5.x sections (command/control points, observation
    posts, targets, obstacles, sustainment, supply, mission tasks in
    point form) via milsymbol.js rather than this module's hand-built
    QGIS symbology, and splitting it correctly needs its own per-section
    coverage audit (already tracked separately - task #33, Table H-VI)
    rather than a mechanical rename alongside this restructuring. Kept
    as its own entry, "Control Measure Points", in the new submenu
    alongside "C2 Measures", so nothing already shipped disappeared from
    the UI.
  - **`plugin.py`**: the old single `control_measures_action` (a
    `QAction`) replaced with `control_measures_menu` (a `QMenu`,
    following the exact same "flyout submenu nested inside a toolbar
    group" mechanism the pre-existing "Sub Grid" menu inside the Grid
    group already used) holding two entries - `c2_measures_action` ("C2
    Measures", calling the new `create_c2_measures()`) and
    `control_measure_points_action` ("Control Measure Points", calling
    the renamed `create_control_measure_points()`, previously folded
    into the old all-in-one `create_control_measures()`).
  - 487 tests passing on both QGIS versions (`test_control_measures.py`
    renamed to `test_c2_measures.py` to match, every renamed symbol/
    layer-name reference updated mechanically; `test_plugin.py` gained a
    check for the new "Control Measures" submenu's own two entries,
    mirroring the existing "Sub Grid" submenu check) - functional
    behaviour is otherwise unchanged (same fields, same rendering, same
    default-insert-position/duplicate-guard semantics), this was a pure
    reorganisation.

- **2026-08-09 — Mini-Phase H3, Maneuver Control Measure Symbols
  (Table H-VII, H.5.11)**, the first mini-phase built under the new
  per-logical-group architecture above - `military_symbology/maneuver_
  control_measures.py`, its own "Maneuver Control Measures (Lines)"/
  "(Areas)" layers, its own "Maneuver Control Measures" entry in the
  Control Measures submenu. At the project maintainer's own explicit
  instruction for H3 onward: read every control measure's own template/
  draw-rules/example in the actual standard BEFORE building it, rather
  than batch-reading the whole table first - the whole table was still
  read up front this once (to plan the module's own architecture before
  writing any code), but each symbol's own construction decision was
  made only after re-checking its own EXAMPLE column colours directly,
  which is what caught the Phase Line-vs-Light-Line tick distinction
  below. Confirmed first, directly against the vendored milsymbol.js
  source: zero support for any Table H-VII entry (no "tactical graphic"/
  "MultiPoint" string anywhere in its own source, zero literal
  symbol-set-25 codes) - every measure type here is 100% hand-built
  QGIS symbology, matching c2_measures.py's own Boundary/Light Line.
  - **Scope decisions made with the maintainer before building** (see
    maneuver_control_measures.py's own docstring for the full
    reasoning): Occupied Assembly Area with Offset Unit/Units
    (150301/150302) and Limited Access Area (151100) skipped outright -
    each needs a second connected geometry (leader line to an external
    point/icon) this module's "one feature, one symbol" model doesn't
    fit; Line of Contact (140200) not built as its own symbol either -
    its own DRAW RULES text says it's simply what results from placing
    this module's own Friendly and Enemy FLOT lines next to each other,
    not a separate drawable control measure.
  - **Field N ("Hostile (Enemy)", literal fixed text "ENY") is not
    rendered at all**, on every Enemy-flagged entry in this table
    (FLOT Enemy, Enemy Area, JTAA/SAA/SGSA) - per Table VII's own field
    definition (5.3.4, checked directly: "A text amplifier for
    equipment; letters 'ENY' denote hostile symbols"), this is a
    monochrome-only fallback the standard's own printed (grayscale)
    tables spell out in text; a colour system - which this plugin
    already is, red=hostile per H.5.1.1.1 - doesn't need it, confirmed
    directly by the maintainer ("if colour coded, then ENY is not
    required... only in grayscale ENY is written"). Nothing in this
    module defaults any field to the literal text "ENY", though the
    maintainer left room to add an optional field there later if a real
    need comes up.
  - **"Occupied Assembly Area" folded into "Assembly Area", "Friendly
    Area"/"Enemy Area" folded into one plain "Area"** - each pair's own
    TEMPLATE column is visually identical once Field N is dropped (the
    standard's own note on Occupied Assembly Area's example already
    says the unit icon shown there "is not part of this control measure
    symbol"), so two dropdown entries that would always render
    pixel-identically added little value - the existing Affiliation
    field already covers what "friendly" vs "enemy" would have shown.
  - **Status-pair codes folded into ONE measure type using the existing
    shared "status" field**, matching Boundary/Light Line's own
    precedent, wherever the underlying shape doesn't actually change
    between Present/Planned: FLOT Friendly (140101/140102), FLOT Enemy
    (140103/140104), and every area type. FEBA (140400)/Proposed FEBA
    (140401) fold the same way once the DRAW RULES text is read
    carefully - the "3 anchor points vs 2" language turned out to be
    guidance for how the USER should digitize a forward-bulging shape
    (the apex comes from whichever vertices they draw, exactly like
    Boundary's own middle vertices), not something the symbol itself
    needs to construct differently.
  - **Two new hand-built line techniques**, confirmed by render-and-
    compare against the actual page images before use (not assumed):
    - **FLOT's own coiled/crescent wavy lines** - a
      QgsMarkerLineSymbolLayer repeating a QgsSimpleMarkerSymbolLayer
      SemiCircle shape along the line; Friendly's own interval is tight
      enough that consecutive arcs touch (reading as one continuous
      coil), Enemy's own is wider (separated crescents) - confirmed
      literally the same repeated shape at different spacing by zooming
      into both EXAMPLE columns (pages 410-411) side by side. Status
      (present/planned) drives the arc's own stroke style between solid
      and dot - the template's own Planned rows show a dotted version of
      the identical shape, not the shared module's usual dashed one, so
      this needed its own local `_FLOT_STROKE_STYLE_EXPRESSION` rather
      than reusing `_STATUS_LINE_STYLE_EXPRESSION`.
    - **Fortified Area's crenellated outline** - approximated (not
      pixel-exact - real castellation would need polygon-offset
      geometry synthesis, disproportionate effort for one entry) with a
      repeating Square marker along the outline at a tight interval,
      giving a recognisably "blocky" boundary rather than the standard's
      own precise tooth shape - the same "recognisable, not exact"
      standard this project applies elsewhere (Airfield Zone's icon,
      Land Equipment curation, ...).
  - **A real construction mistake caught and fixed by render-and-
    compare, not assumed**: Phase Line's own perpendicular end tick
    (built with a "line"-shape marker, the same shape Airfield Zone's
    own runway icon in c2_measures.py uses) rendered ALONG the line
    instead of across it at first - `angle=90` on a rotate-with-line
    marker turned out to mean "flat along the tangent" and `angle=0`
    means "perpendicular", the opposite of what the angle's own name
    suggests. Confirmed by rendering both signs side by side rather
    than assuming, the same discipline this project has applied to
    every other offset/rotation ambiguity so far.
  - **Phase Line's own "PL" + name needed a different construction than
    FEBA's fixed "FEBA" label**, discovered only after render-and-
    compare: routing Phase Line's own name through the Lines layer's
    general along-line PAL label (the same mechanism FEBA's own
    OPTIONAL extra name uses) put a single "PL ECHO" wherever PAL found
    room along the line - nowhere near either end, unlike the standard's
    own template, which pairs the label with the tick at EACH end
    specifically. Fixed with a new `_end_designation_label_layer()`
    helper: the same fixed-end-marker technique `_end_label_layer()`
    already uses for FEBA/Light Line, but with the font marker's own
    Character set as a DATA-DEFINED property (`QgsSymbolLayer.Property.
    Character`) instead of a fixed literal, so each end shows "PL" plus
    whatever the user actually typed. Confirmed against Table H-VII's
    own EXAMPLE column that Phase Line genuinely needs a real tick
    (unlike Light Line, where the up-arrow turned out to be a pointer/
    callout only) - the standard's own "PL ECHO" example (page 413)
    shows a real BLACK bracket touching each end, distinct from a
    separate GREY illustrative boundary-line annotation drawn further
    out - so this per-symbol check has to be repeated for every future
    measure type, not assumed from either prior precedent.
  - `_end_label_layer()` and `_status_driven_area_outline_symbol()`
    (Boundary/Light Line's fixed-end-marker and every area type's
    status-driven outline) moved from c2_measures.py into
    `_control_measure_shared.py`, since this module needed both too -
    c2_measures.py itself now imports them from there instead of
    defining its own copies, no behaviour change.
  - 517 tests passing on both QGIS versions (30 new); render-and-
    compare verified via `QgsMapRendererCustomPainterJob` throughout,
    including every line technique and every area label format.

- **2026-08-09 — Mini-Phase H4, Defensive maneuver (Table H-VIII,
  H.5.12.1 "Areas") + Table H-IX (Observation post, H.5.12.2)** -
  `military_symbology/defensive_control_measures.py`, its own
  "Defensive Control Measures (Areas)" layer, its own submenu entry.
  **Areas-only** - H.5.12 has no line-type entries at all, so unlike
  c2_measures.py/maneuver_control_measures.py this module deliberately
  builds only one layer, not a matched Lines/Areas pair; "own layer(s)"
  was never meant to imply every group needs both.
  - **Table H-IX (all 7 Observation Post variants, plus Target
    Reference Point) is NOT built in this module at all** - every entry
    is a single-anchor-point symbol, and confirmed already present by
    name in `control_measure_points.py`'s own vocabulary
    (`observation_post`, `observation_post_reconnaissance`,
    `observation_post_forward_observer`, `observation_post_cbrn`,
    `observation_post_sensor_listening`, `observation_post_combat`,
    `target_reference_point`) - milsymbol.js already renders these.
    Not yet formally cross-checked entry-by-entry against Table H-IX's
    own template pictures, the same kind of follow-up already flagged
    for Table H-VI under task #33 - worth doing, not urgent.
  - **Contain (151204) and Retain (151205) skipped outright** - both
    are defined by a center point plus a radius (a computed circle with
    a directional 30-degree gap, "the opening will be on the friendly
    side of the symbol"), not a freeform user-drawn boundary the way
    every other area in this table is - doesn't fit this module's (or
    any other H.5.x area module's) "one polygon feature, one symbol"
    pattern, the same "doesn't fit the model" reasoning already applied
    to H3's own Offset-Unit/Limited Access Area entries.
  - **Battle Position's own three Present/Planned/"Prepared (P) but not
    Occupied" variants don't map onto the shared status field's two
    values on their own** - "Prepared but not Occupied" is dashed (like
    Planned) PLUS an extra "(P) " name prefix, not a genuinely distinct
    line style. Modelled as the existing shared status field (solid/
    dashed) plus a new, module-local "prepared" Yes/No field that adds
    the prefix when set - confirmed against the standard's own "(P)
    MARS" example.
  - **Battle Position and Strong Point both reuse the Table D-III
    echelon amplifier** (Field B) directly from `_control_measure_
    shared.py` - the same vocabulary/glyphs/masking-free construction
    Boundary already established in c2_measures.py, confirmed against
    the standard's own "7"/"II" example.
  - **One new hand-built technique**: Strong Point's own spiked/toothed
    perimeter - the exact same "line"-shape marker technique already
    confirmed for Phase Line's own end tick in maneuver_control_
    measures.py (angle=0 is perpendicular for a rotate-with-line
    marker, not angle=90), just repeated at Interval placement around
    the WHOLE boundary instead of only at two ends - render-and-compare
    confirmed a clean spiked border matching the standard's own
    template.
  - Every symbol render-and-compared directly against the standard's
    own examples before being called done: "XRAY" (Battle Position
    Present), "7"/"II" (Planned + echelon), "(P) MARS" (Prepared),
    "TWO"/echelon (Strong Point), "EA ROCK" (Engagement Area) - all
    matched the standard's own literal example text exactly.
  - 533 tests passing on both QGIS versions (16 new).

- **2026-08-09 — Mini-Phase H5, Offensive maneuver (Table H-X "Axis of
  Advance" + Table H-XI "Direction of attack", H.5.13)** -
  `military_symbology/offensive_control_measures.py`, its own
  "Offensive Control Measures (Lines)"/"(Areas)" layers, its own
  submenu entry.
  - **Table H-X is deliberately APPROXIMATED, not built exactly** -
    the first (and so far only) time this appendix-by-appendix pass has
    made that call for an entire table rather than a handful of
    entries within one. Every real entry (Friendly Airborne/Aviation,
    Attack Helicopter, Main Attack, Supporting Attack, for a Feint,
    Enemy) is defined by the standard's own DRAW RULES as a
    variable-width tapered "ribbon" polygon computed from up to 50
    anchor points (points 1 through N-2 trace a centerline, point N-1
    is the rear, point N sets an arrowhead's own width) - a genuinely
    different rendering paradigm from every other control measure
    built in this appendix so far, which all style a shape the user
    already drew rather than computing a new one from it. Approximated
    as a single moderately-thick line (the user's own digitized path)
    with one filled arrowhead at the end - loses the taper and the
    small per-type decorations (a crossed "X" for Attack Helicopter, a
    doubled outline for Main Attack, a dashed trailing edge for a
    Feint), but reads recognisably as an "axis of advance" arrow, the
    same "recognisable, not exact" standard already used for Fortified
    Area's crenellation. Each sub-type stays its own selectable
    measure_type (so the correct SIDC-relevant meaning is still
    recorded and correctly coloured/labelled) even though several now
    render identically.
  - **Table H-XI (Direction of Attack) is built for real** - despite
    reusing several of the same sub-type names as Table H-X, it's a
    much simpler, genuinely different construction: a plain 2-point
    line with a small UNFILLED chevron arrowhead
    (`QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead`, not
    "ArrowHeadFilled") at the end - confirmed by directly comparing the
    standard's own template pictures for both tables side by side
    before writing any code, rather than assuming Table H-XI would need
    the same approximation as Table H-X just because several sub-type
    names repeat.
  - **Two entries skipped**: **Infiltration Lane** (140800) - a third
    variable-width construction (2 centerline points + 1 width point)
    with a zig-zag "stitched" double boundary, but unlike Table H-X's
    own arrows a single line doesn't read as a "lane" even
    approximately, so this wasn't approximated either, just deferred.
    **Point of Departure** (160400) - a point symbol, already present
    in `control_measure_points.py`'s own vocabulary
    (`point_of_departure`).
  - **Probable Line of Deployment (141200) is the first line in this
    entire appendix pass where the shared "status" field's own solid/
    dashed switch doesn't apply** - the standard's own explicit note
    says its dashed line "shall be displayed in present AND anticipated
    status" (i.e. always dashed); built with a fixed `Qt.PenStyle.
    DashLine` and no data-defined StrokeStyle override at all, instead
    of the usual `_STATUS_LINE_STYLE_EXPRESSION`.
  - Field N ("ENY") again not rendered on the Enemy-flagged Axis of
    Advance/Direction of Attack variants, same reasoning as
    maneuver_control_measures.py.
  - Every buildable symbol render-and-compared against the standard's
    own examples: Axis of Advance/Direction of Attack arrows (solid and
    dashed, filled vs. open arrowhead), FCL/LOA/PLD end labels (PLD
    confirmed dashed even when "status" was set to present), and area
    labels "ASLT DANUBE"/"ATK NILE"/"OBJ FIVE" matching the standard's
    own example text exactly.
  - 552 tests passing on both QGIS versions (19 new).

- **2026-08-09 — Mini-Phase H6, "Maneuver control measure symbols"
  (Table H-XII, H.5.14)** - `military_symbology/maneuver_control_
  measures_2.py` (a "_2" suffix, not "_h6" - H.5.14's own section title
  is LITERALLY "Maneuver control measure symbols" again, the identical
  title H.5.11/`maneuver_control_measures.py` already uses; the
  standard repeats the heading for a later, separate group of measures,
  not a naming slip on this project's own part), its own "Maneuver
  Control Measures II (Lines)"/"(Areas)" layers, its own submenu entry.
  - **Two entries skipped**: **Attack By Fire Position (152000)** and
    **Ambush (141700)** both need a real geometric construction this
    appendix hasn't required before - an arrow shaft whose own tail
    connects not to a digitized vertex but to the COMPUTED MIDPOINT of
    a separate line between two other anchor points. Genuinely
    different from every other "arrows from a shared point" symbol
    already built (Principal Direction of Fire, Search Area/
    Reconnaissance Area below), where every arm meets AT a directly
    digitized vertex, never a point computed partway along another
    segment.
  - **Two entries nominally coded as "Areas" in the standard's own SIDC
    numbering (a "15" prefix) are built on the LINES layer instead** -
    Support by Fire Position (152100) and Search Area/Reconnaissance
    Area (152200) are both multi-point arrows, not closed boundaries a
    polygon layer could hold. Confirms this module (like every other
    one in this pass) organises its own layers by ACTUAL QGIS geometry
    type, not by the standard's own field-code grouping, since a QGIS
    layer can only ever hold one geometry type regardless of what a
    SIDC prefix implies. Support by Fire Position's own two arrowheads
    both connect directly to digitized vertices (no midpoint needed,
    unlike Attack By Fire Position above), so it's built for real, not
    skipped - the same First/LastVertex arrowhead technique already
    used for Principal Direction of Fire.
  - **Encirclement's own Friendly (151801)/Enemy (151802) variants
    folded into one measure type** - the same "Field N (ENY) dropped,
    so the pair is visually identical once affiliation-colour is the
    only real difference" reasoning already applied to Friendly/Enemy
    Area in maneuver_control_measures.py. Its own spiked/toothed border
    reuses defensive_control_measures.py's own Strong Point technique
    directly (a QgsMarkerLineSymbolLayer repeating a "line"-shape
    marker at Interval placement) - the third time this exact technique
    has been reused since Strong Point first established it in H4.
  - **Airhead Line (141300) is the first line in this whole appendix
    pass with a single, fixed, CENTRED label** ("AIRHEAD LINE") rather
    than one repeating along the line or fixed at each end - built with
    `Qgis.LabelPlacement.Line`'s own default single-placement behaviour,
    not the repeating/end-anchored patterns every other labelled line
    here has needed.
  - Every buildable symbol render-and-compared against the standard's
    own template pictures: Support by Fire Position/Search Area arrows,
    Airhead Line's centred label, BL/HL/RL end labels, Encirclement's
    spiked border, Penetration Box's plain outline.
  - 572 tests passing on both QGIS versions (20 new).

- **2026-08-09 — Mini-Phase H7, Airspace Control Measures (Table
  H-XIII, H.5.15)** - `military_symbology/airspace_control_measures.py`,
  its own "Airspace Control Measures (Lines)"/"(Areas)" layers, its own
  submenu entry - plus 25 new entries added directly to `sidc.py`'s
  `ENTITIES["control_measure"]` and `control_measure_points.py`'s own
  `_ENTITY_LABELS`, unlike every prior H-subphase's point vocabulary
  (H4's Table H-IX, H5's Point of Departure), which was already present
  and needed no code change.
  - **Every one of Table H-XIII's ~25 point entries (Air Control Point,
    Communications Checkpoint, Downed Aircrew Pick-Up Point, Pop-Up
    Point, Air Control Rendezvous, TACAN, CAP/AEW/ASW/SUCAP/MIW
    Stations, Strike Initial Point, Replenishment Station, Tanking,
    Tomcat, Rescue, Unmanned Aerial System, VTUA, Orbit + its 3
    variants) confirmed present in milsymbol.js's own vendored source
    under the exact numeric code the standard's own table gives** -
    added to the shared, milsymbol-rendered Control Measure Points
    layer rather than hand-built, the same "point control measures
    belong there" precedent as H4/H5, just the first time this pass's
    own point vocabulary genuinely needed adding rather than merely
    confirming. Render-and-compared all 25 through the real QJSEngine
    pipeline - every icon matches the standard's own EXAMPLE column
    exactly, including milsymbol's own display-name quirk for 180400
    ("TP.PULL-UP POINT" instead of the standard's "Pop-Up Point (PUP)")
    which turned out to be a naming difference only - its actual drawn
    geometry (circle + "PUP" text + bowtie path) matches the template
    exactly.
  - **One point skipped: Base Defense Zone (170800, BDZ)** - a
    fixed-size ("Static") plain circle around ONE anchor point, not in
    milsymbol's vocabulary and not a fit for the Areas layer's freeform-
    polygon model either - the same "genuinely a point construct"
    reasoning already applied to H4's Contain/Retain and H6's Attack By
    Fire Position/Ambush.
  - **Corridors/Routes (7 types, standard's own "17" Area SIDC prefix)
    built on the LINES layer instead** - Air Corridor, Low-Level Transit
    Route, Minimum-Risk Route, Safe Lane, SAAFR, Transit Corridor,
    Unmanned Aircraft Route are all really a path (2-99 sequential PT
    anchor points), not a closed boundary - same "organise by actual
    QGIS geometry type, not the SIDC field-code grouping" principle as
    H6's Support by Fire Position/Search Area. Each is, per its own
    template, really a variable-width RIBBON with rounded ACP/CCP
    endpoint circles and 5 extra fields (WIDTH/MIN ALT/MAX ALT/DTG
    START/DTG END) - approximated as a single moderately-thick
    status-driven line with a centred "PREFIX NAME" label, the same
    whole-table-approximation tolerance already used for offensive_
    control_measures.py's own Axis of Advance family. "Air Corridor
    with Multiple Segments" is the same code (170100) as plain Air
    Corridor, just more anchor points - not a separate measure type.
  - **Two simple end-labelled lines**: IFF Off Line (190100, "IFF OFF"
    at both ends) and IFF On Line (190200, "IFF ON") - the same
    `_end_label_layer()` technique as FCL/LOA/LD elsewhere in this
    appendix.
  - **12 zone/area types all share the identical "freeform outline +
    PREFIX + optional name" construction** via a shared prefix dict:
    HIDACZ, ROZ, AARROZ, UA-ROZ, and the Weapon Engagement Zone family
    (WEZ, FEZ, JEZ, MEZ, LOMEZ, HIMEZ, SHORADEZ) - the standard's own
    WEZ note says it "includes" the other five as its own sub-types, but
    the table then lists each as its own separate SIDC code too, so all
    six are built as distinct measure types rather than collapsed under
    WEZ.
  - **Weapons Free Zone (172000, WFZ) is the first area in this entire
    appendix-by-appendix pass with a genuine fill** - the standard's own
    note reads "Upward diagonal lines are part of the fill", not a plain
    "no fill" outline like every other area built so far. Built with a
    `QgsLinePatternFillSymbolLayer` at 45 degrees on top of the usual
    status-driven outline - a new technique for this project, confirmed
    by render-and-compare against the standard's own hatched template.
  - Every buildable symbol render-and-compared against the standard's
    own template pictures: all 7 corridor types' centred labels, IFF
    Off/On's end labels, all 12 zone types' outlines and labels, WFZ's
    hatched fill, and all 25 point icons through the real rendering
    pipeline.
  - 592 tests passing on both QGIS versions (20 new).

- **2026-08-09 — Mini-Phase H8/H9, Maritime control measures (Table
  H-XIV, H.5.16)** - `military_symbology/maritime_control_measures.py`,
  a Lines-ONLY layer ("Maritime Control Measures (Lines)", no Areas
  layer at all - Table H-XIV's own content ends right after its last
  line entry, straight into H.5.17/Table H-XV Deception, without ever
  reaching an "Areas" heading the way every other H.5.x section so far
  has had one) - plus 13 new points added directly to `sidc.py`'s
  `ENTITIES["control_measure"]` and `control_measure_points.py`'s own
  `_ENTITY_LABELS`, the second time this pass's own point vocabulary
  needed adding (after H7) rather than merely confirming.
  - **This table turned out to be overwhelmingly Navy-AEGIS-combat-
    system-specific or anti-submarine-warfare/sonar-specific** - by far
    the heaviest curation of any H-subphase so far. Read through the
    table's own template pictures page by page (pages 466-504 printed)
    before deciding scope, rather than assuming from the section's own
    intro text ("points, lines and areas") that a full three-geometry
    build was needed.
  - **The whole "(AEGIS only)" family skipped**: Launch Area (200101/
    200102, Ellipse/Rectangle), Defended Area (200201/200202), No Attack
    (NOTACK) Zone (200300), Ship Area of Interest (200400 grid-heatmap/
    200401 Ellipse/200402 Rectangle), Active Maneuver Area (200500),
    Cued Acquisition Doctrine (200600), Radar Search Doctrine (200700) -
    every one of these needs a FIXED-graphic overlay (some parametric,
    like an ellipse from one anchor point + major/minor axis radii +
    rotation angle; others literally a static pre-drawn icon like a
    diamond or curved arrow anchored to one point) with specific fixed
    colours/fills, a genuinely different display category from every
    other freeform-polygon or simple-line construction this whole
    Appendix H pass has built - confirmed by reading every one of their
    own template pictures directly, not assumed from the "(AEGIS only)"
    tag alone.
  - **The entire anti-submarine-warfare/sonar-contact-point family and
    Sonobuoys sub-section skipped** (roughly codes 211000-213399 plus
    213500+: Launched Torpedo, Acoustic Countermeasure (Decoy), ECM
    Decoy, BT Buoy Drop, Reported Bottomed Sub, Moving Haven, Acoustic/
    Electromagnetic/MAD Fix, Sonobuoy and its Ambient Noise/ATAC/Barra/
    etc. sub-types) - the same "more Navy/anti-submarine-warfare-
    specific ones (sonobuoy types and similar)" category this project's
    own control_measure_points.py docstring already documents as
    curated out of the base vocabulary; this mini-phase applies that
    same standing decision rather than reversing it. Confirmed via
    milsymbol.js's own TP.* name list (dozens of matching sonobuoy/
    sonar-fix entries) that this reflects the standard's own real
    scope, not an undercount on this project's part.
  - **13 general-purpose points kept and added**: Plan Ship, Aim Point,
    Defended Asset, Drop Point, Entry Point, Air Detonation, Ground
    Zero, Impact Point, Predicted Impact Point, Missile Detection Point,
    Brief Contact, Datum Lost Contact, Navigational Reference Point -
    confirmed present in milsymbol.js under each exact numeric code,
    added to the shared Control Measure Points layer per the same
    precedent as every other H-subphase's point vocabulary. Render-and-
    compared all 13 through the real QJSEngine pipeline - every icon
    matches the standard's own EXAMPLE column.
  - **The Bearing Line family (9 types, codes 220100-220108) built for
    real** - the ONE genuinely general-purpose construction in this
    whole table: a simple 2-point line with a fixed abbreviation centred
    along it (Bearing/B, Electronic/E, Electronic Warfare/EW, Acoustic/
    A, Torpedo/T, Electro-Optical Intercept/O, Jammer/J, RDF). Each
    variant's own template also shows an optional "H" identifier info
    box (e.g. "MSL"/"TENT" for EW, "PAT-1" for Jammer) - dropped, the
    same "extra descriptive field box" tolerance already used for H7's
    corridor family's WIDTH/altitude/DTG fields, rather than modelling a
    different fixed vocabulary per sub-type for one small label.
  - **Bearing Line, Acoustic (Ambiguous) (220104) confirmed a genuinely
    separate SIDC code from plain Acoustic (220103), not a status
    variant** - always drawn dashed in both its own template and
    example regardless of a present/planned distinction, so built with
    `setPenStyle(Qt.PenStyle.DashLine)` directly and no data-defined
    StrokeStyle override, the same fixed-dash construction already used
    for offensive_control_measures.py's own Probable Line of Deployment
    (H5).
  - Every buildable symbol render-and-compared against the standard's
    own template pictures: all 9 Bearing Line variants' labels and the
    Acoustic (Ambiguous) dash, and all 13 point icons through the real
    rendering pipeline.
  - 603 tests passing on both QGIS versions (11 new).

- **2026-08-09 — Mini-Phase H10, Deception control measures (Table
  H-XV, H.5.17)** - `military_symbology/deception_control_measures.py`,
  the smallest mini-phase in this whole appendix-by-appendix pass: the
  table has exactly ONE new drawable symbol.
  - **Decoy/Dummy (230100) built as a 3-point line** (PT2 -> PT1 -> PT3,
    vertex at PT1) drawn as two dashed segments forming a "tent"/
    chevron shape - the same 3-point-line-from-a-shared-vertex
    construction already used repeatedly (Principal Direction of Fire,
    Search Area/Reconnaissance Area), just without arrowheads. **Always
    dashed**, not status-driven (no `status` field on this layer at
    all) - the standard's own template/example show it dashed with no
    solid variant, consistent with a decoy being inherently simulated
    rather than present/planned - the same fixed-dash technique as H5's
    Probable Line of Deployment and H8/H9's Bearing Line, Acoustic
    (Ambiguous). **No label at all** - the standard's own EXAMPLE column
    shows an information box with 3 grey circle icons inside
    (representing whatever's being decoyed), entirely grey, matching
    this appendix's own established "grey in the EXAMPLE column is
    illustrative-only" convention (first confirmed for c2_measures.py's
    own Light Line) - nothing in that box is modelled.
  - **Everything else in the table needs no new code**: Decoy/Dummy and
    Feint (230200) is an explicit MODIFIER of another, separately-drawn
    control measure ("anchor points are determined by the relationship
    between the control measure symbol being modified and the decoy/
    dummy or feint... modifying it") - the same "doesn't fit this
    project's one-feature-one-symbol model" reasoning as every other
    compound construct skipped elsewhere in this appendix. Axis of
    Advance for a Feint and Direction of Attack for a Feint are the
    standard's own explicit cross-references to symbols already built
    in Mini-Phase H5 (`axis_of_advance_feint`/`direction_of_attack_
    feint` in offensive_control_measures.py). Decoy Mined Area and
    Dummy Minefield are the standard's own explicit forward-references
    to Table H-XIX (Obstacles, Mini-Phase H15/H16, not yet reached).
  - Render-and-compared the dashed tent shape against the standard's
    own template picture.
  - 612 tests passing on both QGIS versions (9 new).

- **2026-08-09 — Mini-Phase H11, Fire Support Coordination Measures
  (Table H-XVI, H.5.18)** - `military_symbology/fire_support_
  coordination_measures.py`, its own "Fire Support Coordination
  Measures (Lines)"/"(Areas)" layers, its own submenu entry.
  - **The table's own intro text sets a general labelling rule for
    every entry**: abbreviation + controlling headquarters (Field T) +
    effective times (Field W/W1), repeated at both ends for lines. Kept
    the abbreviation (SIDC-relevant), dropped the controlling-
    headquarters/effective-times info boxes - the same "extra
    descriptive field box" tolerance already used for H7's corridor
    family and H8/H9's Bearing Line family.
  - **5 area types, each folding a separate Irregular/Rectangle/
    Circular SIDC code triple into ONE measure type**: Airspace
    Coordination Area (240101/240102/240103, "ACA"), Free Fire Area
    (240201/240202/240203, "FFA"), No Fire Area (240301/240302/240303,
    "NFA"), Restricted Fire Area (240401/240402/240403, "RFA"),
    Position Area For Artillery (240501/240502, "PAA" - only Rectangle/
    Circle, no Irregular variant in the standard's own table) - the
    same "these render pixel-identically once only the boundary shape
    differs" reasoning already applied throughout this appendix.
  - **No Fire Area (NFA) confirmed to need a genuine hatched fill** -
    the SECOND area in this whole appendix-by-appendix pass after H7's
    Weapons Free Zone, built the identical way
    (QgsLinePatternFillSymbolLayer at 45 degrees over the usual
    status-driven outline).
  - **6 line types, split into two label conventions confirmed by
    reading each one's own template picture** (not assumed from the
    family's shared framing): Fire Support Coordination Line (FSCL),
    No Fire Line (NFL), Battlefield Coordination Line (BCL), and
    Restrictive Fire Line (RFL) all show their abbreviation at BOTH
    ends (`_end_label_layer()`); Coordinated Fire Line (CFL) and
    Munition Flight Path (MFP) both show a single label CENTRED along
    the line (`Qgis.LabelPlacement.Line`, the same technique as
    Airhead Line and this appendix's own corridor/route family).
  - **CFL (260200) confirmed always dashed as a fixed property of the
    code itself, not status-driven** - its own template and example
    both show it dashed with no solid variant, the same fixed-dash
    construction already used for H5's Probable Line of Deployment,
    H8/H9's Bearing Line Acoustic (Ambiguous), and H10's Decoy/Dummy.
  - Every buildable symbol render-and-compared against the standard's
    own template pictures: all 6 line types' labels/dash styles, and
    all 5 area types' outlines/labels/fill.
  - 633 tests passing on both QGIS versions (21 new).

- **2026-08-09 — Mini-Phase H12, Targets (Table H-XVII, H.5.19)** -
  `military_symbology/target_control_measures.py`, its own "Target
  Control Measures (Lines)"/"(Areas)" layers, its own submenu entry.
  - **Most of this table's own point vocabulary was already present**
    from an earlier pass, confirmed by code and name rather than
    assumed: Point/Single Target (240601), Nuclear Target (240602),
    Target-Recorded (AEGIS Only) (240603 - confirmed against
    milsymbol.js's own "TP.TARGETRECORDED (AEGIS ONLY)" entry, which
    genuinely draws the standard's own rectangle+diamond icon, not a
    gap), Fire Support Station (240900), and the whole Field Artillery
    points sub-section (Firing/Hide/Launch/Reload/Survey Control
    Point). Nothing new needed there.
  - **3 new line types, all sharing a perpendicular end-tick
    construction** confirmed against each one's own EXAMPLE column
    (genuine black ticks, not grey annotation - the same per-type check
    used since Phase Line's H3 precedent): Linear Target (240701, a
    bare optional name with no fixed abbreviation), Linear Smoke Target
    (240702, fixed "SMOKE" second line under an optional name), Final
    Protective Fire (240703, fixed centred "FPF").
  - **5 new area types**, folding Irregular/Rectangle/Circular code
    triples where present: Area Target (240801/802/803, a bare name
    with NO fixed prefix - unlike most other prefixed areas in this
    appendix, confirmed by its own EXAMPLE column), Series or Group of
    Targets (240805, also a bare name - its own template shows
    individual target-designator crosses inside the boundary, each one
    a separate already-covered feature the user places on this
    module's own other layers, not part of the boundary's own drawn
    geometry), Smoke (240806 present/240807 planned - confirmed this
    IS a genuine present/planned pair, unlike this appendix's other
    fixed-dash codes, so it folds cleanly onto the existing status
    field), Bomb Area (240808, fixed "BOMB" label), Fire Support Area
    (241001/002/003, "FSA" prefix + optional name).
  - **One entry skipped**: Rectangular Target - Single Target (240804,
    AEGIS Only) needs a fixed compound diamond+cross icon anchored to
    one point with a permanently-upright orientation regardless of the
    area's own rotation - the same AEGIS-combat-system-specific
    curation already applied throughout H8/H9.
  - **Bug caught and fixed before shipping**: the first version of both
    label expressions evaluated `upper("unique_designation")` directly
    in the bare-name branches (Linear Target, Area Target, Series or
    Group of Targets) - `upper(NULL)` returns NULL, not `''`, so a
    feature with no name set failed its own "empty label" test. Fixed
    by wrapping each in the same `CASE WHEN ... IS NOT NULL AND != ''`
    guard already used everywhere else in this appendix; caught by the
    test suite itself, not by rendering.
  - Every buildable symbol render-and-compared against the standard's
    own template pictures: all 3 line types' end-ticks and labels, and
    all 5 area types' outlines and labels.
  - 656 tests passing on both QGIS versions (23 new).

- **2026-08-09 — Mini-Phase H13/H14, Target acquisition (Table H-XVIII,
  H.5.20)** - `military_symbology/target_acquisition_control_measures.
  py`, its own "Target Acquisition Control Measures (Areas)" layer
  (Areas only, no Lines/Points - the whole table is this one
  construction), its own submenu entry.
  - **11 measure types, every one the identical "freeform outline +
    prefix + optional name" construction**, each folding a separate
    Irregular/Rectangle/Circular SIDC code triple into one measure
    type: Artillery Target Intelligence Zone (241101/102/103, "ATI"),
    Call For Fire Zone (241201/202/203, "CFF ZONE" - the standard's
    own template text, not "CFFZ"), Censor Zone (241301/302/303,
    "CENSOR ZONE"), Critical Friendly Zone (241401/402/403, "CF
    ZONE"), Dead Space Area (241501/502/503, "DA"), Sensor Zone
    (241601/602/603, "SENSOR ZONE"), Target Build-up Area (241701/702/
    703, "TBA"), Target Value Area (241801/802/803, "TVAR"), Zone of
    Responsibility (241901/902/903, "ZOR"), Blue Kill Box (242301/302/
    303, "BKB"), Purple Kill Box (242304/305/306, "PKB"). Confirmed
    each family's own code triple by reading its own template pages
    directly (not assumed from the first two families) - the standard
    itself is inconsistent about which families spell "ZONE" out in
    their own fixed template text, kept as-is rather than normalised.
  - **Two entries skipped**: Weapon/Sensor Range Fan - Circular
    (242100) and - Sector (242200) both need genuinely parametric/
    computed geometry from a single anchor point (one or more
    concentric range rings, or a pie-shaped sector with an azimuth
    centreline plus left/right limits and multiple range arcs) - not a
    freeform polygon a user directly digitizes, the same reasoning
    already applied to H4's Contain/Retain.
  - Every measure type render-and-compared against the standard's own
    template pictures - all 11 prefixes and optional names match the
    standard's own EXAMPLE column exactly.
  - 667 tests passing on both QGIS versions (11 new).

- **2026-08-09/10 — live smoke-testing follow-up: Mini-Phase H3
  correction pass (Table H-VII)** - the project maintainer began working
  through every H3 measure type by hand in QGIS and found several real
  construction defects the original build/render-compare pass missed,
  each fixed the same day and re-verified by rendering:
  - **FLOT was wrongly split into "flot_friendly"/"flot_enemy"** with
    different arc intervals - merged into one `flot` measure type,
    coloured by the shared affiliation field like every other measure
    here, since the standard's own construction is identical regardless
    of affiliation. Its own semicircles were also closing with a drawn
    "chord" line across the flat edge - fixed by switching from
    `QgsSimpleMarkerSymbolLayerBase.Shape.SemiCircle` (a closed shape,
    stroke and all) to `Shape.HalfArc` (a genuinely open arc), found by
    enumerating QGIS's own Shape enum directly rather than guessing.
  - **Line of Contact (140200), previously skipped as "not a real
    control measure"**, turned out to need building after all once the
    maintainer clarified the standard's own construction: two FLOT-style
    arc chains, offset apart with a gap, each bulging toward the
    opposite side (friendly convex toward the enemy, enemy convex toward
    friendly - a ")(" shape) rather than one shared line. Iterated to a
    final 4.5mm gap and one chain fixed black / one fixed red (not
    affiliation-driven, since both sides are always shown at once) after
    several rounds of maintainer feedback on gap size and colour.
  - **Phase Line's own end tick was wrong** - re-reading the maintainer's
    own correction: the tick shown in the template is a grey
    illustrative annotation, not drawn geometry (the same "grey =
    explanatory only" lesson H2's own Light Line already taught, now
    confirmed to need re-checking per measure type rather than assumed
    from precedent). Removed entirely - Phase Line is now just the line
    plus "PL "+name at both ends, no tick.
  - **FEBA's own optional unique-designation label was wrong** - it has
    no such field in the standard at all; removed the general along-line
    label mechanism from the Lines layer entirely (FEBA was its only
    remaining consumer).
  - **Principal Direction of Fire's arrowheads** went through an
    extended, ultimately unnecessary investigation (the maintainer's own
    explicit correction: "you are complicating the issue... both...have
    the arrow pointing outwards away from vertex") before landing back on
    the ORIGINAL unmodified construction - a real lesson in trusting the
    maintainer's own literal geometric description over pixel-level
    reinterpretation when the two conflict. Its Field A vertex label
    ("A") was removed too, on the maintainer's clarification that it
    marks where a separate symbol belongs, not literal text to render.
  - **Fortified Area's crenellated outline needed THREE real attempts**
    before it worked on a genuine curved/multi-vertex boundary (not just
    a synthetic rectangle): a single row of Square markers ("beaded
    chain"), then two staggered offset marker-line chains (passed a
    synthetic-rectangle test but broke down on the maintainer's own real
    map screenshot near bends), then a Gemini-suggested dashed-line
    variant (worse still). The actual fix abandoned symbol-layer styling
    entirely for a genuine computed geometry: a new
    `mct_crenellate_outline()` expression function (`expressions/
    military_symbology_functions.py`) walking the ring in tooth+gap
    cycles via `QgsGeometry.interpolate()`, with the OUTWARD direction
    resolved once from the ring's own winding order (a shoelace
    signed-area test), not a per-segment centroid-distance heuristic
    (which got confused in concave stretches) - fed into a
    `QgsGeometryGeneratorSymbolLayer`. This technique (ring-winding-order
    for a reliable outward normal) was reused again in the H4 pass below.
  - **Limited Access Area (151100), previously skipped**, was built
    after all - a hatched-fill freeform area reusing the same
    `QgsLinePatternFillSymbolLayer` recipe already used for Weapons Free
    Zone/No Fire Area elsewhere in this appendix.
  - 680 tests passing on both QGIS versions.

- **2026-08-10 — live smoke-testing follow-up: Mini-Phase H4 correction
  pass (Table H-VIII) + a Points-layer architecture change (Tables
  H-VI/H-IX)** - two more real construction defects found by the
  maintainer's own hands-on QGIS testing, plus a scope change requested
  the same day:
  - **The Field B echelon glyph was rendering as a second line of Battle
    Position's/Strong Point's own floating, polygon-centred name
    label**, not sitting IN the perimeter line with a real gap cut
    around it the way the standard's own template shows (and the way
    Boundary already does it in c2_measures.py). Fixed by moving the
    echelon glyph to its own, separate, masked label - anchored at the
    polygon's own ORIGIN point (its first digitized vertex, via a label
    geometry generator, `point_n($geometry, 1)`) rather than the
    feature's own centroid, per the maintainer's explicit instruction.
  - **Strong Point's own tick marks straddled the perimeter line
    symmetrically** (half inside the polygon, half outside) instead of
    pointing outward only - fixed with the same ring-winding-order
    technique H3's Fortified Area pass had already established: wrap the
    tick layer in a `QgsGeometryGeneratorSymbolLayer` using
    `force_rhr($geometry)` to force a fixed winding direction, so a
    fixed marker offset reliably means "outward" for every feature
    regardless of how the user digitized it. Once fixed, the maintainer
    then found the ticks were crowding the echelon glyph at the origin
    point - the masked gap only cut through the outline, not the
    separate tick layer. Fixed by adding the tick layer's own id to the
    same masked-symbol-layer list and widening the mask.
  - **Battle Position's "Prepared but not occupied" checkbox rendered a
    SOLID perimeter** unless the separate "status" field was ALSO
    switched to Planned by hand - wrong, since a dedicated field exists
    for exactly this variant. Fixed with Battle Position's own line-style
    expression (dashed when either "status" is planned OR "prepared" is
    set) instead of reusing the shared status-only one.
  - **Points-layer architecture change, at the maintainer's own explicit
    request**: Table H-VI (Command and control points) and Table H-IX
    (Observation post) both moved out of the shared, ~90-entry
    `control_measure_points.py` dropdown into their own dedicated
    layers - "C2 Measures (Points)" and "Defensive Control Measures
    (Points)" respectively - matching the "own layer(s)" convention
    every other H.5.x group's Lines/Areas layers already follow, and
    closing task #33's own "Table H-VI pending audit" note by
    construction. Not duplicated in both places - the underlying
    `sidc.py` entities are untouched, so this only changes which
    layer's dropdown offers them, not how anything already digitized
    renders. The remaining H.5.x groups' own point-type entities
    (Airspace/Maritime control points, plus everything belonging to the
    not-yet-built H15-H22 mini-phases) stay in the shared layer for now
    - splitting those out is scoped to happen naturally as/when each
    group gets its own dedicated Points layer, not ahead of time.
  - 696 tests passing on both QGIS versions (16 new).

- **2026-08-10 — third live-testing round on Table H-VI, C2 Measures'
  own new Points layer**, all found by the project maintainer's own
  hands-on QGIS testing against the actual standard's own Table H-VI
  pages (reference/MIL-STD-2525D.pdf, rendered as page images and
  visually compared, not just text-extracted - the same discipline this
  project applies everywhere else):
  - **Four entities missing from the original ~80-entry curation**:
    Fly-To Point (Sonobuoy/Weapon/Normal, codes 131001-131003) and Point
    of Interest - Launch Event (131301) - genuinely absent from
    `sidc.py`'s own `ENTITIES["control_measure"]`, not built elsewhere
    under a different name (confirmed by grepping the whole codebase).
    Added after confirming the exact codes/names directly against the
    vendored milsymbol.js source.
  - **Two entities removed after direct verification against the
    standard found they don't exist there at all**: Target Handover
    (132000) and Key Terrain (132100). Table H-VI's own last page (409)
    ends at Airfield (131900), immediately followed by H.5.11/Table
    H-VII on the very next page - confirmed by rendering both pages as
    images, not just trusting `pdftotext` (whose own extracted text
    already agreed, but the project's own standing discipline is to
    never stop at text alone). "Target Handover"/132000 doesn't even
    exist in milsymbol.js's own dispatch table under any name; Key
    Terrain/132100 does (`TP.KEY TERRAIN`), but is a milsymbol-only
    addition with no basis in the actual MIL-STD-2525D text - both
    removed from `sidc.py` and this module's own `POINT_ENTITY_LABELS`.
    Table H-VI is now a verified-complete, gap-free 22 entities (130100
    through 131900, confirmed against every single "Code:" line in the
    standard's own text for that page range).
  - **The "Unique designation" field was being collected on every
    Points layer's own attribute form but never actually rendered at
    all** - a real, if quiet, bug affecting C2 Measures' new Points
    layer, Defensive Control Measures' new Points layer, and the
    original `control_measure_points.py` layer alike: the SIDC string
    itself has no room for free text, so it has to reach the rendered
    symbol through milsymbol.js's own separate render options, which
    nothing was populating. Fixed via `mct_sidc_svg()`'s own new
    optional second/third arguments.
  - **The fix above then surfaced a second, subtler bug**: milsymbol.js
    itself uses TWO different, non-interchangeable text-modifier options
    per icon (`uniqueDesignation` vs `uniqueDesignation1`), and guessing
    wrong puts the designation in a visibly different position than the
    standard's own template shows (or, for one wrong guess along the
    way - `additionalInformation` - a third position entirely, above the
    icon, matching neither). Resolved by reading milsymbol.js's own
    per-icon position-config objects directly for every Table H-VI
    entity rather than guessing per-icon: Contact Point/Decision Point/
    Point of Interest/Airfield/Waypoint use `uniqueDesignation`; Amnesty
    Point/Checkpoint/Distress Call/Entry Control Point/Linkup/Passage/
    Rally/Release/Start Point use `uniqueDesignation1` instead, for the
    exact same visual position the standard's own EXAMPLE column shows.
    `_POINT_SIDC_EXPRESSION` now routes accordingly via a `CASE`
    expression. Every reference to the field had to be wrapped in
    `coalesce(...,'')` - QGIS's own expression engine short-circuits an
    entire function call to NULL the moment any argument evaluates to
    NULL, which a bare field reference does for the (common) case of a
    feature that simply left "Unique designation" blank - this broke
    the ENTIRE icon, not just the missing text, for every feature
    without a designation, until caught and fixed.
  - **Several icons render visibly smaller/fainter than their siblings
    at the same nominal 8mm marker size**, despite every icon's own
    rendered SVG sharing the identical `stroke-width="3"` (confirmed by
    rendering each one's raw SVG and comparing directly) - milsymbol.js
    has no separate "bolder line" option, so size is the only lever
    available. Fixed for the two entities the maintainer gave explicit
    target increases for (Decision Point +20%, Center of Main Effort
    +10%) via a data-defined `Size` property, `_POINT_SIZE_MULTIPLIERS`.
    Coordination Point and Contact Point were flagged with the same
    root cause but no specific target percentage - left at the default
    pending that number.
  - **Distress Call's own diagonal anchor-point line is genuinely
    missing from milsymbol.js's own vendored icon definition** -
    confirmed by decoding its raw SVG path data directly: the drawn
    shape stops exactly at the cone's own tip, with no further segment
    extending toward an external anchor point the way the standard's
    own template/example both show. Not fixed yet - the two ways to
    fix it (hand-patching the vendored third-party file, which this
    project avoids on principle, or building a second, precisely
    positioned QGIS symbol layer stacked on top of the opaque SVG
    marker to draw just that one line) are both real engineering
    investment for one decorative line on one entity - flagged to the
    maintainer rather than unilaterally built.
  - `control_measure_points.py`'s own remaining ~88 entities share the
    exact same `coalesce(...,'')` NULL-propagation fix (this one WAS
    applied everywhere, since it was silently breaking icons outright),
    but NOT yet individually checked against the `uniqueDesignation`/
    `uniqueDesignation1` per-icon distinction the way Table H-VI's own
    22 were - noted as a known limitation in that module's own
    `_SIDC_EXPRESSION` comment, to revisit if reported.
  - 699 tests passing on both QGIS versions (3 new).
  - **Same-day follow-up**: Coordination Point and Contact Point's own
    size boost, left pending above, was set to +15% each once the
    maintainer gave that number. Separately, the maintainer's own next
    check found the "unique_designation" field wasn't being upper-cased
    at all on any of the three Points layers (C2 Measures', Defensive
    Control Measures', and the original `control_measure_points.py`) -
    a real H.5.4 Labeling violation, missed because this whole code path
    reaches milsymbol.js's own text options directly rather than through
    the shared `_PLAIN_DESIGNATION_LABEL_EXPRESSION` that already
    upper-cases the appendix's own hand-built line/area labels. All
    three expressions now wrap the field in `upper(...)`. 700 tests
    passing on both QGIS versions (1 new).
  - **Second same-day follow-up**: three more real findings from the
    maintainer's own continued live testing.
    - Coordination Point's own display label was wrong - the standard
      itself calls it **Coordinating Point** (confirmed against the
      actual template heading, page 403); renamed both the entity key
      (`coordination_point` -> `coordinating_point`, in `sidc.py` and
      this module) and its label, not just the label, so the internal
      identifier stays honest about what it represents. Center of Main
      Effort's own +10% size bump (previous round) was still reported
      too small/faint - raised to +15% to match Coordinating Point/
      Contact Point.
    - Unspecified Control Point's own designation was rendering OUTSIDE
      the icon (to the right) instead of inside/below like its
      siblings, and appeared smaller - the size turned out to be a red
      herring (its own SVG output dimensions are, if anything, very
      slightly LARGER than Amnesty Point's - confirmed by rendering
      both and comparing directly; the "smaller" impression was almost
      certainly just an empty box reading as sparser than a
      "AMN"-filled one). The real, confirmed bug: this ONE entity
      defines its own, differently-named milsymbol.js option for that
      position - `additionalInformation1`, not the `uniqueDesignation1`
      its siblings share - found by reading its own position-config
      object directly. This pushed `mct_sidc_svg()` past a design limit
      (a THIRD distinct slot name) - refactored from two fixed
      positional "which slot" arguments to a general `(text, slot_name)`
      pair, so any future per-icon slot discovery is a one-line entity
      lookup, not another new function parameter.
    - **Distress Call's own missing diagonal anchor-point line was
      built**, at the maintainer's own request, as a genuinely new
      symbol layer (not a vendored-file patch) - length and tip-offset
      derived directly from the icon's own known local SVG coordinates
      (both work out to the same value, `DEFAULT_POINT_MARKER_SIZE_MM *
      80 / 215.33` mm - not a coincidence, the icon's own box width and
      half its own total height are equal in local units), angle
      measured by pixel-tracing the standard's own template picture
      (~15 degrees below horizontal). Getting the direction right needed
      a real, standalone diagnostic first: a QgsSimpleMarkerSymbolLayer's
      own `angle` rotates its `offset` together with its drawn shape (a
      controlled 4-angle test render, not assumed), which meant the
      "reach the tip" component of the offset (which must stay fixed
      straight down in absolute space) had to be pre-rotated by the
      INVERSE of the line's own angle before handing it to QGIS, so
      QGIS's own forward rotation lands it correctly - ordinary vector
      math once the rotation behaviour itself was confirmed empirically.
      Also hit, and fixed, a real PyQt/SIP segfault along the way:
      extracting a symbol layer from a `QgsMarkerSymbol.createSimple()`
      wrapper and returning it after the wrapper itself goes out of
      scope leaves a dangling reference - built directly via the
      concrete `QgsSimpleMarkerSymbolLayer` class instead, sidestepping
      the whole issue.
  - 702 tests passing on both QGIS versions (2 new).
  - **Third same-day follow-up**: Airfield joined the same +20% size fix
    as Decision Point. More significantly, the maintainer's own report
    that the new Distress Call diagonal line still wasn't landing at the
    right spot led to a genuinely better fix than the one already
    shipped, on the maintainer's own suggestion: "why not use the point
    where the user clicks as the origin for the symbol, the bottom tip
    of triangle sits there... if you notice even in the manual, the
    symbol is drawn AT the anchor point and not around it." This was
    right, and generalises well past Distress Call - EVERY entity
    sharing the box+cone icon construction (confirmed by an identical
    rendered SVG path across all of them: Unspecified Control Point,
    Amnesty Point, Checkpoint, Distress Call, Entry Control Point,
    Linkup/Passage/Rally/Release/Start Point) shares the same "Anchor
    Points... the point defines the TIP of the inverted cone" draw
    rule, which QGIS's own default SVG marker anchor (the drawn
    content's bounding-box CENTRE) has been quietly getting wrong for
    all ten of them, not just Distress Call. Replaced the previous
    (broken - a QgsSvgMarkerSymbolLayer's own `Offset` property turned
    out to have no visible effect at all on rendering, confirmed by a
    controlled before/after comparison) offset-based hack with QGIS's
    own purpose-built `VerticalAnchor` symbol layer property
    (`center`/`bottom`/`top`, confirmed empirically with the same kind
    of controlled render comparison that this project already leans on
    for every ambiguous rendering question) - data-defined per entity,
    `bottom` for the whole box+cone family, `center` (the previous
    default) for everything else, matching each entity's own actual
    draw rule rather than a blanket assumption either way. The new
    diagonal line's own construction simplified as a direct result -
    with the SVG's own anchor now genuinely at the tip, the line just
    starts at (0, 0) and extends outward, no more "reach the tip first"
    offset component to compute.
  - 703 tests passing on both QGIS versions (1 new).
  - **Fourth same-day follow-up**: the three Fly-To Point variants
    joined the same size fix (+15%), for a related but distinct reason -
    their own outer box+cone shape is actually IDENTICAL in size to
    Checkpoint's own (confirmed by comparing raw SVG output dimensions
    directly), but "FTP" plus a 3-letter code needs two text lines where
    Checkpoint's own "CKP" needs one, and milsymbol.js shrinks the font
    to fit two lines into the same box height - the same underlying
    "no separate boldness/font-size lever, size is the only one" finding
    as the earlier round, just a text-density cause rather than a
    line-weight one. 703 tests passing on both QGIS versions (existing
    size test extended, no new test).
  - **Live smoke-testing moved to Table H-VII (Maneuver Control Measure
    Symbols, `maneuver_control_measures.py`)**: the maintainer reported
    only two of that table's entities had issues - FLOT and Line of
    Contact both had semicircle "arcs" that were too big, and Line of
    Contact's own two chains (one per side, black + red) needed a
    genuine visible gap between them, with the black chain recoloured
    blue. Fixed by parameterising `_arc_marker_layer()`'s previously
    hardcoded `size_mm=6` and introducing a shared `_ARC_SIZE_MM = 6 *
    0.6` constant (-40%, applied identically to both symbols so they
    stay visually consistent with each other); Line of Contact's
    friendly-side chain colour changed `QColor(0, 0, 0)` ->
    `QColor(0, 0, 255)`. The gap took one round of maintainer
    correction to get right: the first attempt (`offset_mm=1.0`/`-1.0`)
    was reported as "the red and blue lines are overlapping" on direct
    inspection, so it was increased to `2.2`/`-2.2` and re-rendered -
    confirmed via a zoomed render crop to show a clear, non-overlapping,
    discernible gap between the two chains, matching the request for
    "a very slight discernable gap" rather than a wide separation.
    704 tests passing on both QGIS versions (1 new: arc-size equality
    test; 1 renamed: the two-chain colour test now expects blue+red
    instead of black+red).
  - **Live smoke-testing moved to Table H-IX (Observation post,
    `defensive_control_measures.py`)**: the maintainer reported two
    real bugs, both confirmed by direct evidence rather than
    assumption before fixing. **Bug 1** - a unique designation typed
    into any of the six Observation Post entities (Unspecified,
    Reconnaissance, Forward Observer, CBRN, Sensor/Listening, Combat)
    never rendered - traced to milsymbol.js's own control-measure
    position-config table, read directly: `t[160100]={},t[160200]={},
    t[160201]={} ... t[160205]={}` are all genuinely EMPTY objects, a
    different (and worse) problem than the earlier C2-points slot-name
    mismatch - there's no text position at all to configure our way
    into, unlike Target Reference Point right next to them in the same
    table (`t[160300]={uniqueDesignation:{...}}`), which already works
    and was left untouched. Fixed with a real QGIS point label (not a
    milsymbol one) placed directly over the feature's own point
    (`Qgis.LabelPlacement.OverPoint` + `Quadrant.Over`), at a small
    (3.5pt) bespoke font size - the shared 9pt line/area label size
    badly overflowed this family's own 8mm triangle on a first live
    render. **Bug 2** - Forward Observer/Spotter's own triangle was
    missing the diagonal line the standard's own template picture
    (page 425) shows running from the bottom-left vertex, through the
    dot, to the midpoint of the right edge - confirmed a genuine gap in
    the vendored milsymbol.js itself (its own icon definition draws
    only the triangle and the dot) by rendering the actual SIDC and
    reading the returned SVG directly, not by comparing pictures alone.
    Rather than hand-patching the vendored third-party file, added the
    line as this project's own extra marker layer, reusing
    c2_measures.py's own Distress Call "milsymbol is missing a stroke"
    technique (a LayerEnabled data-defined property keyed on the one
    affected entity) but drawn BENEATH the SVG icon this time rather
    than above it, since the standard's own picture shows the dot
    sitting on top of the line, the opposite ordering from Distress
    Call's own diagonal. The line's own endpoints came from milsymbol's
    real local SVG coordinates (confirmed live via
    `render_symbol_svg()`, not eyeballed), and the local-unit-to-mm
    scale came from rendering a real feature and measuring the filled
    dot's own pixel radius against its known local radius of 15 units
    (a filled shape measures more precisely than a thin stroked
    outline) - the same render-and-measure discipline this project has
    used for every other ambiguous QGIS rendering behaviour this
    session. `core/text_format.py`'s own `build_font()` needed a small
    one-line fix alongside this (`setPointSize` -> `setPointSizeF`) to
    accept the fractional 3.5pt label size at all. 706 tests passing on
    both QGIS versions (3 new: the diagonal line's own shape/
    LayerEnabled test, the new label's own text/upper-casing/exclusion
    test; 2 existing tests updated for the renderer's new symbol-layer
    ordering, index 0 -> 1 for the SVG icon layer).
  - **Two other H-VIII/H-IX findings reported the same session were
    investigated and found NOT to be bugs, or were withdrawn by the
    maintainer before any code changed** - noted here so a future pass
    doesn't re-litigate them from scratch: Contain (151204)/Retain
    (151205)/a "weapon-sensor range fan" report were raised, then the
    maintainer said the observation was incorrect and asked to stop
    before any fix was scoped or built; module docstring's existing
    Contain/Retain "deliberately skipped" note (procedural circle/arc
    constructions, not a freeform-polygon fit) stands unchanged.
  - **Live smoke-testing moved to Table H-X/H-XI (Offensive Control
    Measures, `offensive_control_measures.py`)** - the maintainer's own
    report was large (six separate findings) and confirmed against the
    standard's own template pictures (pages 428-439) table row by table
    row before any code changed:
    - **Field T (unique designation) and Field W-W1 (DTG range) never
      rendered at all** on any Axis of Advance/Direction of Attack
      variant. Fixed via a new `_designation_end_marker_layer()` - the
      same data-defined-Character `QgsFontMarkerSymbolLayer` technique
      maneuver_control_measures.py's own Phase Line already established
      for per-feature dynamic text - placed near the arrowhead (Axis of
      Advance: T below the shaft, DTG above; Direction of Attack: T on
      the shaft, DTG below), a `dtg_start`/`dtg_end` field pair added to
      the Lines layer schema (matching the same Fields W/W1 maneuver_
      control_measures.py's own action areas already use).
    - **Every Axis of Advance sub-type rendered identically** - restored
      Attack Helicopter's own perpendicular crossbar (a rotate-with-line
      "line"-shape marker, Strong Point's own established convention),
      Main Attack's own doubled/parallel-line outline (two close offset
      copies of the shaft), and Direction of Attack's own Friendly
      Aviation bowtie glyph (two opposed `Triangle` marker layers, each
      offset half its own size outward so their tips meet at the anchor
      instead of just overlapping - QGIS has no native bowtie shape).
    - **Enemy-flagged variants didn't automatically render red** -
      fixed with a small local colour override
      (`_OFFENSIVE_LINE_COLOR_EXPRESSION`) that forces red for exactly
      `axis_of_advance_enemy`/`direction_of_attack_enemy`, deferring to
      the ordinary affiliation-driven colour for every other measure
      type in this module.
    - **Infiltration Lane (140800) was re-scoped from "skipped" to
      "built"** - re-reading its own draw rules directly (not relying on
      the earlier session's own assumption that it needed the same
      variable-width polygon synthesis Axis of Advance does) showed it's
      just two parallel lines with a centred Field T, the same "two
      fixed-offset copies" approximation Main Attack's own doubled
      outline uses. One real bug surfaced building this: the first
      attempt (1.2mm offset each side, matching Main Attack's own
      spacing) put Field T's text directly on top of both lines at
      once - and since the text and lines share the same affiliation-
      driven colour, the overlap made the text unreadable (a negative-
      space silhouette, not a rendering failure) rather than merely
      crowded, caught by rendering a real feature and sampling actual
      pixel colours rather than eyeballing a thumbnail. Fixed by
      widening the gap to 2.0mm each side and shrinking the label.
    - **Table H-XI's own "Points" sub-section (Point of Departure,
      160400) had no dedicated layer** - the one H.5.13 point family
      still sitting in the shared `control_measure_points.py` dropdown
      instead of getting the "own layer(s)" treatment every sibling
      H.5.x group already has. Given its own new `Offensive Control
      Measures (Points)` layer, moved out of control_measure_points.py
      (not duplicated). Its own unique designation also didn't land
      where the template shows it (immediately right of the box,
      vertically centred) - milsymbol.js's own position config for this
      SIDC turned out to be a genuine mismatch (`t[160400]=E`, only an
      ABOVE-the-box slot under the wrong field name, confirmed by
      rendering the real SVG output for both the slot this project was
      using and the one milsymbol actually defines, not guessed), so
      this uses the same real-QGIS-label workaround Table H-IX's own
      Observation Post family established, positioned via an explicit
      (x, y) mm offset derived from the icon's own real local SVG
      coordinates. Building this caught a real sign-convention error
      the hard way: `QgsPalLayerSettings.yOffset` turned out to use the
      SAME Y-down convention as the local SVG coordinates themselves,
      not the inverted Y-up convention first assumed - confirmed by
      rendering a real feature and seeing the label land well below the
      box instead of beside it, then fixing the sign and re-confirming.
    - `core/text_format.py`'s own `build_font()` needed the same
      `setPointSize` -> `setPointSizeF` fix already made for Table
      H-IX's own label to accept a font size below 1pt granularity
      cleanly (unrelated to this round directly, already fixed).
      717 tests passing on both QGIS versions (11 new: Field T/W-W1
      structure and font-marker presence for both families, Main
      Attack's own doubled-outline offsets, the Aviation bowtie, the
      forced-red Enemy colour, Infiltration Lane's own parallel-line/
      label structure, and the new Points layer's own field/anchor/
      label/SIDC-path tests; several existing tests updated for the new
      symbol-layer counts and the Lines layer's own two new DTG fields).
  - **Same-day follow-up, back on Table H-IX**: the project maintainer's
    own live testing found the shared 3.5pt Observation Post label size
    (fixed earlier this round) unreadable specifically for "Observation
    Post/Outpost" itself - the one entity of the six with an otherwise
    completely empty triangle, so it has the most room of any of them
    and was asked to go to 8pt; Forward Observer/Spotter's own earlier
    fix (the missing diagonal line) was separately confirmed working
    and left untouched. Rather than bump the size for all six (which
    would have crowded the other five, each already sharing its own
    triangle with an interior glyph), this is now a per-entity data-
    defined `Size` property on the label (`_POINTS_LABEL_FONT_SIZE_
    EXPRESSION`) - 8pt for the plain/unspecified variant, 3.5pt
    everywhere else. Building the test for this hit a real segfault
    the same "dangling intermediate reference through several PyQt/
    SIP-wrapped QGIS objects in one chained expression" class of bug
    this project has hit before (c2_measures.py's own Distress Call
    anchor line) - fixed by holding each intermediate (`labeling`,
    `settings`, `properties`, `size_property`) as its own named local
    instead of one long chain. 718 tests passing on both QGIS versions
    (1 new).
  - **Same-day follow-up, first "one at a time" pass on Table H-X's
    still-approximated Axis of Advance family**: at the project
    maintainer's own explicit direction ("H-X and H-XI have too many
    errors, let's fix one at a time, that way, it can be a template for
    others also"), started with Friendly Airborne/Aviation (151401),
    replacing the single-thick-line-plus-filled-arrowhead approximation
    with the standard's own REAL variable-width tapered-ribbon
    construction, simplified to exactly 3 user clicks (origin, bend,
    tip) rather than the standard's own general N-point form, per the
    maintainer's own request. Two real findings along the way:
    - **The maintainer's own suggested QGIS technique (a single
      expression chaining ~20 `with_variable()` calls through
      `azimuth()`/`project()`) produced the right shape** (confirmed by
      an independent plain-Python/PIL debug render of the same point
      math) **but blew up exponentially on a real render** - directly
      timed rather than assumed: evaluation time roughly DOUBLED with
      each added chained variable (0.01s -> 1.05s by variable 17 of
      ~24), and the full expression timed out completely. Root cause:
      QGIS's own `with_variable()` doesn't memoize - every `@ref`
      re-evaluates its entire dependency chain from scratch. Moved to a
      plain Python `@qgsfunction`, `mct_axis_of_advance_ribbon()`
      (expressions/military_symbology_functions.py), the same
      "real point/geometry math belongs in Python, not a deeply chained
      expression" lesson `mct_crenellate_outline()` already established
      for Fortified Area's own crenellated outline (maneuver_control_
      measures.py) - wired into a `QgsGeometryGeneratorSymbolLayer` the
      identical way. Runs instantly; no expression-engine involvement
      beyond the single top-level function call.
    - **The maintainer's own suggested widths were fixed absolute map
      units** (`100`/`250`/`300`, assuming a projected metric CRS) -
      this project's own control-measure layers are built in whatever
      CRS the QGIS project itself uses, often geographic WGS84 (degrees),
      where a "100-unit" width would be enormous. Changed to ratios of
      the drawn Point-1-to-Point-3 distance instead (shaft/barb width
      and barb length as percentages of the arrow's own drawn length),
      which reads correctly regardless of the layer's CRS and matches
      the standard's own general "size determined by anchor points"
      phrasing already seen throughout this appendix. **Exact ratio
      values are explicit placeholders, not yet tuned against the
      standard's own template picture** - the maintainer's own explicit
      instruction was to get the construction technique right first,
      "we will fill the data later".
    - The construction's own topology (two parallel edges holding
      constant width from Point 1 through Point 2, THEN swapping sides
      in a short crossing region close to the tip before flaring into
      the arrowhead) was arrived at empirically - a first, simpler
      attempt (offset edges going straight from the bend to the
      arrowhead's back corners, or forcing an explicit zero-width pinch
      at the Point-2-to-Point-3 midpoint) each produced a visibly wrong
      kite/lopsided shape on a real render, confirmed via a debug PIL
      plot of the actual computed vertices before landing on the
      version that matches the standard's own template picture (page
      428) reasonably well.
    - Also split "Friendly Airborne/Aviation" (one dropdown entry) into
      two - "Friendly Airborne" and "Friendly Aviation" - sharing the
      one SIDC the standard's own table lists (151401, whose own
      EXAMPLE column shows two illustrative pictures under that single
      code) and this same new ribbon construction, per the maintainer's
      own explicit request ("they are two different tasks"). The rest
      of the Axis of Advance family (Attack Helicopter, Main Attack,
      Supporting Attack, Feint, Enemy) keeps the older approximation
      for now, queued for its own future "one at a time" round using
      this same technique as the template. 720 tests passing on both
      QGIS versions (2 new: the ribbon symbol-layer wiring, direct
      coverage of `mct_axis_of_advance_ribbon()`'s own geometry output;
      1 existing test narrowed to exclude the now-real construction).
  - **Same-day second follow-up, matched against a reference picture of
    the standard's own template the maintainer shared directly**: two
    real construction corrections to `mct_axis_of_advance_ribbon()`.
    The shaft's own width and the arrowhead's own widest point were two
    independent ratios (0.02 vs. 0.06) that only happened to be close -
    collapsed into one shared `width_ratio` per the maintainer's own
    explicit instruction ("the width of the arrow shaft should be as
    wide as the distance between the side tips of the arrowhead"),
    which also removed the visible "flare" the first version had
    (the shaft widening into the arrowhead) - the standard's own
    picture has no such flare, just a clean crossover at constant
    width. Separately, the crossing region itself was two straight
    line segments meeting at a sharp point; replaced with a quadratic
    Bezier curve per edge (`_quadratic_bezier_points()`, a new small
    helper), each bulging outward on its own starting side before
    sweeping across, per the maintainer's own explicit request for the
    crossing to "look natural" rather than a sharp geometric X - a
    direct, visible match against the reference picture's own soft
    curve there, confirmed by rendering and zooming into the arrowhead
    region specifically, not just eyeballing the full symbol. No test
    changes needed (the existing structural tests - 3-piece
    MultiLineString output, symbol-layer wiring - didn't depend on the
    removed second width ratio or the straight-vs-curved segment
    shape). 720 tests passing on both QGIS versions (unchanged count).
  - **Same-day third follow-up**, after the maintainer shared their own
    live QGIS render side-by-side with the standard's own template
    picture again: the curve was starting too LATE - the shaft stayed
    straight past the bend (Point 2) for a while, then curved only in
    a short region just before the arrowhead, where the reference
    picture's own curve clearly starts right AT the bend and sweeps
    continuously all the way to the arrowhead's own back corner.
    Removed the intermediate straight "pre-crossing" segment entirely -
    each edge's own quadratic Bezier now runs directly from Point 2's
    own offset point to the OPPOSITE arrowhead corner, with the curve's
    own bulge scaled to that now-longer span (30% of the straight-line
    distance between the two, instead of a fixed multiple of the
    shaft's own width) so it stays proportional regardless of how far
    apart Point 2 and the arrowhead end up. The arrowhead's own two
    sides stay straight, per the maintainer's own explicit description
    ("assume the arrowhead is an isosceles triangle, from the tip for
    about 15% each side, let the lines be straight") - `barb_length_
    ratio`'s own default moved to 0.15 to match that "about 15%"
    figure directly (was 0.12, an earlier unconfirmed guess). 720 tests
    passing on both QGIS versions (unchanged count - no structural test
    depended on where the curve started).
  - **Same-day fourth follow-up**, from a zoomed crop of the standard's
    own template picture the maintainer shared directly, plus their
    own live QGIS render: three more real corrections.
    - **The arrowhead is a true EQUILATERAL triangle**, not merely
      isosceles, per the maintainer's own explicit correction ("make
      it equilateral instead of isosceles") - `barb_length` (the
      triangle's own height) is now DERIVED from `width` (`width *
      sqrt(3)`, the height of an equilateral triangle whose base is
      `2 * width`) instead of the independent `barb_length_ratio` from
      the previous round, which could drift out of an equilateral
      proportion. New `test_ribbon_arrowhead_is_equilateral` asserts
      all three sides equal directly, for any `width_ratio`.
    - **The shaft's own edges attach partway along the arrowhead's
      own back EDGE, not at its CORNERS** - the maintainer's own
      direct observation against the zoomed crop ("the lines from the
      shaft do not hit the triangle edges but slightly along the
      third side"). Each edge now attaches at `attach_ratio` (a
      placeholder 0.55) of the way from the base's own centre toward
      each corner, rather than at the corner itself.
    - A first attempt at "a slightly rounded turn, otherwise straight"
      (the maintainer's own suggested simplification, after the long
      shallow curve from the third follow-up still didn't look right)
      tried rounding Point 2 with two SEPARATELY offset points (one on
      the incoming heading, one on the outgoing) and curving between
      them - this is a well-known hard case for line offsetting: on
      the bend's own INNER side, the two offsets land on the wrong
      side of each other, so the curve loops back on itself instead of
      rounding smoothly. Confirmed on a real render (the outer/left
      side curved cleanly, the inner/right side produced a visible
      self-intersecting notch), not assumed. Fixed with a genuine
      corner-cutting fillet instead (`_rounded_corner_points()`, a new
      helper) - cuts back a fixed radius along each of the polyline's
      own ALREADY-STRAIGHT adjoining segments and curves between those
      two points using the sharp corner itself as the Bezier control
      point, the standard technique for rounding a polyline vertex
      without this failure mode. Combined with the maintainer's own
      "keep the crossing straight otherwise" request, each edge is now
      a single straight line from just past the Point 2 fillet
      directly to its own (opposite-side) attachment point.
    - **A visible gap between where each shaft edge stopped and the
      arrowhead's own drawn outline** - since the attachment point is
      now inset from the corner (previous bullet), but the arrowhead
      itself was still drawn as only its own two sides (corner-to-tip),
      nothing drew the short remaining stretch from the attachment
      point out to the actual corner, leaving a visible break in the
      outline on a real render. Fixed by extending each shaft edge's
      own polyline one point further, straight from its attachment
      point out to that corner, closing the gap.
    721 tests passing on both QGIS versions (1 new: the equilateral-
    triangle check).
  - **Same-day fifth follow-up, moving from the arrow's own shape to
    its text/context markers** - the project maintainer confirmed the
    arrow shape itself was done ("perfect on the arrow") and asked to
    start on Field T/context-icon placement, Friendly Airborne first.
    Added `_airborne_unit_context_icon_layer()` - a small rectangle (a
    generic ground-unit frame) with MIL-STD-2525D's own Airborne
    modifier glyph inside (confirmed directly against milsymbol.js's
    own vendored source, `icn["GR.M2.AIRBORNE"]` in milsymbol-3.0.4's
    src/iconparts/ground.js: two side-by-side semicircular humps,
    exactly what this project's own `Shape.HalfArc` marker - already
    used for FLOT/Line of Contact's own arc chains - already draws, so
    built from that instead of hand-authoring separate path data),
    placed at the shaft's own start (Point 1). Not routed through the
    real milsymbol.js/mct_build_sidc() pipeline - MODIFIERS in sidc.py
    has no "ground_unit" entry at all yet (sector 1/2 modifier support
    was only ever built for the point-symbol appendices, a known,
    already-tracked gap) - so this is a hand-built decorative marker,
    the same "hand-build the one glyph actually needed" choice
    Direction of Attack's own bowtie already made. Field T also moved
    from its usual place near the tip to just above this new icon,
    still near Point 1, per the maintainer's own explicit layout
    instruction - Friendly Aviation (which shares this same builder
    function) keeps the older tip-side T placement and gets no context
    icon for now, queued for its own future round. 722 tests passing on
    both QGIS versions (1 new: the context icon's own structure/
    placement, and Field T's own move to Point 1 for this one variant).
  - **Same-day sixth follow-up, Field W-W1 (DTG) for the same pair.**
    Tried a two-stacked-font-marker construction to match the
    standard's own two-line DTG-range display (Field T's own single
    `QgsFontMarkerSymbolLayer` technique can't do this in one marker -
    confirmed live that its Character property silently drops an
    embedded `'\n'`, rendering "LINE1\nLINE2" as the single concatenated
    run "LINE1LINE2" rather than starting a real second line). Wired a
    `_dtg_marker_layers()` helper (two markers, one per DTG half,
    offset apart on the line-perpendicular axis) into all four Axis of
    Advance/Direction of Attack call sites, but a render-and-compare
    check turned up serious text overlap. Before iterating on positions
    further, the project maintainer said this wasn't worth the effort
    for Friendly Airborne/Aviation and asked for Field W-W1 to be
    dropped **for that pair only** - explicitly not the rest of the
    Axis of Advance/Direction of Attack family, which keep the original
    single-line `_DTG_RANGE_LABEL_EXPRESSION` display unchanged.
    Reverted the helper/two-marker wiring everywhere it had been
    over-applied, keeping only the removal scoped to
    `_axis_of_advance_ribbon_symbol()`'s airborne/aviation branches, per
    the maintainer's own explicit "one at a time" methodology for this
    section (H5) - not to apply a fix across the board unless told to.
    722 tests passing on both QGIS versions (font-marker/layer counts
    updated for the two ribbon variants only).
  - **Same-day seventh follow-up - a real live-GUI-only bug (headless
    rendering never caught it), plus a new standing H5 workflow.** From
    here, the project maintainer asked to do H-X/H-XI strictly one item
    at a time, smoke-testing each in the actual QGIS GUI before moving
    on, rather than batching several fixes before a live check. First
    smoke test (Friendly Airborne) found the context icon rendering as
    QGIS's own generic broken/placeholder SVG glyph, even though every
    prior headless offscreen render (both QGIS versions, real plugin
    code) showed it fine - narrowed down by asking the maintainer to
    confirm the exact symptom (a generic placeholder, not blank or a
    legible-but-tiny icon) rather than guessing blind. Root cause,
    found by static analysis once the symptom was confirmed: a freshly
    digitized feature's own "affiliation" field defaults to
    DEFAULT_AFFILIATION ("unspecified", this appendix's genuine 5th
    "black, no standard identity asserted" colour per H.5.1.1.1 -
    _control_measure_shared.py's own comment) - a value sidc.py's own
    AFFILIATIONS dict has no entry for (point-symbol SIDCs only have
    friend/hostile/neutral/unknown). Passed straight into
    mct_build_sidc(), that raised KeyError and returned an error string
    instead of a real SIDC, which mct_sidc_svg() couldn't render -
    hence the placeholder glyph, while the arrow's own line colour and
    Field T's own text both still rendered fine (their own CASE
    expressions already had a safe ELSE fallback; only the icon's own
    SIDC-building call didn't). This is why the bug only ever showed up
    in the maintainer's own live GUI testing and never in this
    project's own headless render-and-compare checks so far - every
    headless test script had explicitly set a real affiliation value on
    its test feature, never exercising the field's own actual default.
    Confirmed live by the maintainer (manually setting Affiliation to
    "Friend" fixed it) before any code changed. Fixed the icon's own
    SIDC-building expression to map "unspecified" (or any other value
    sidc.py doesn't recognise) to 'unknown' for the icon's own
    affiliation argument only - the field itself keeps its real 5-value
    range for the line's own colour. Separately, at the maintainer's
    own follow-up suggestion ("since the line is for friendly, can't it
    default to friend"), overrode this Lines layer's own default
    Affiliation value to 'friend' (nearly every measure type here is an
    inherently friendly, own-force graphic; the two Enemy-flagged
    variants already ignore this field for their own line colour) -
    scoped to just this module's own layer via a setDefaultValueDefinition()
    call after _configure_affiliation_field(), not a change to the
    shared DEFAULT_AFFILIATION constant every other H control-measure
    layer (Boundaries, Maneuver, Defensive, C2 Measures) still uses
    unchanged. 723 tests passing on both QGIS versions (1 new: the
    Lines layer's own affiliation default).
  - **Same-day eighth follow-up, Friendly Aviation's own turn** (per the
    now-standing H5 workflow: one item at a time, smoke test, only then
    move on - Friendly Airborne confirmed working live before this
    started). Brought Friendly Aviation over to the same unit-context-
    icon + Field T layout Friendly Airborne got, per the maintainer's
    own explicit instruction ("remove the infantry symbol and the
    'm'... replace with the aviation symbol i.e. Land Unit - Aviation
    Rotary Wing symbol... rest remains same, friendly, unique
    designation etc, DTG is removed"). Generalised the former
    `_airborne_unit_context_icon_layer()` into `_unit_context_icon_
    layer(entity, airborne_modifier=False)` - confirmed by directly
    rendering both entities' own SIDCs and comparing their SVG
    `viewBox`s (identical "21 46 158 108") that Infantry and Aviation
    Rotary Wing share the exact same Ground Unit rectangle frame, only
    the icon glyph inside differs, so the same `svg_angle=90` correction
    and layout carry over unchanged; Aviation gets `airborne_modifier=
    False` since the Aviation Rotary Wing icon's own rotor-blade glyph
    already identifies the unit type without the extra humps.
    `_axis_of_advance_ribbon_symbol()`'s own `airborne` boolean became a
    `variant` string ("airborne"/"aviation") now that both branches
    share the same icon+Field-T-at-Point-1 structure and only differ in
    icon content - the old tip-side Field T placement Aviation
    previously kept is gone, both variants now match. 724 tests passing
    on both QGIS versions (1 new: Aviation's own context icon/no-
    modifier structure; the shared ribbon-construction test's own
    layer-count expectations updated to match, both variants now equal).
  - **Same-day ninth follow-up, Attack Helicopter's own turn - a new
    standing H5 workflow, and a real custom glyph supplied by the
    maintainer directly.** The maintainer set an explicit rule for the
    rest of H5 going forward: one item at a time, smoke test each in
    the live GUI, only then move to the next (Friendly Aviation
    confirmed working live before this started). Attack Helicopter
    (151402) moved off the approximated single-thick-line-plus-crossbar
    construction (`_axis_of_advance_crossbar_layer()`, now deleted -
    dead code once its only caller moved) onto the same real ribbon
    construction Airborne/Aviation already use, reusing Aviation's own
    Aviation Rotary Wing base icon at the shaft's own start
    ("base of the shaft remains same - aviation rotary wing icon") and
    adding a new crossing-point glyph "at the point of intersection"
    (the ribbon's own edge-crossing, computed directly as a plain
    midpoint-of-Point-2-and-Point-3 expression, not requiring a new
    Python function). Getting the glyph itself right took several
    rounds: confirmed via direct milsymbol.js source search that
    nothing in its vendored icon parts matches (`COM.M1/M2.ROTARY WING`
    is a plain filled bowtie parallelogram-pair, not an arrow-through-
    bowtie combination); two hand-built QGIS-native attempts (built
    from `Shape.Triangle`/`Shape.Line` marker layers, tuned in the
    scratchpad per this project's own established "finalise the icon
    before inserting into main code" discipline) were both rejected by
    the maintainer as not matching their own reference image closely
    enough; the maintainer then supplied the glyph's own exact SVG path/
    polygon data directly, which is what's actually built now - a
    static (not data-defined) `QgsSvgMarkerSymbolLayer` fed the
    maintainer's own SVG verbatim via the project's existing "base64:"
    inline-SVG technique, since the glyph doesn't vary per-feature
    (fixed black, matching every other structural modifier glyph in
    this appendix - Field N, the Airborne humps, the Direction of
    Attack bowtie). Placed via a `QgsGeometryGeneratorSymbolLayer`
    producing a Marker (not Line) from the computed midpoint, which
    - confirmed by render, not assumed - naturally has no line-rotation
    applied at all, satisfying the maintainer's own explicit requirement
    that "the orientation of the symbol will remain vertical irrespective
    of the direction of arrow" without needing any extra fixed-angle
    workaround. `_axis_of_advance_ribbon_symbol()`'s own `variant`
    parameter grew a third value ("attack_helicopter") alongside
    "airborne"/"aviation". 725 tests passing on both QGIS versions (1
    new: Attack Helicopter's own ribbon+icon+glyph structure; the
    approximated-family test's own layer-count loop simplified now that
    Attack Helicopter no longer needs its own crossbar special-case).
  - **Same-day tenth follow-up, three corrections to the crossing glyph
    once live-smoke-testable in a real render**: (1) **colour** - the
    maintainer asked to standardise the glyph's colour with the rest of
    the affiliation system rather than leaving it fixed black; switched
    the SVG's own hardcoded `#000000` fill/stroke to QGIS's own
    `param(fill)`/`param(outline)` placeholder syntax and wired
    `_apply_offensive_line_color()` onto the `QgsSvgMarkerSymbolLayer`'s
    own Fill/StrokeColor data-defined properties - confirmed live (not
    assumed) that this recolours an INLINE base64 SVG exactly like
    QGIS's own bundled parametrised SVG library does for file-based
    ones, a technique not used anywhere else in this project yet. (2)
    **size** - increased from 8mm to 12mm (50% larger), per the
    maintainer's own direct comparison against the ribbon's own
    arrowhead triangle in a live render. (3) **position** - the
    maintainer found the glyph consistently sat "slightly right and
    above the point of intersection" across several different arrow
    geometries they tried, "the error of position seems to be the
    same" - a systematic offset, not a one-off, correctly diagnosed as
    the earlier midpoint-of-Point-2-and-Point-3 expression being only
    an APPROXIMATION of the ribbon's own real crossing point, which is
    actually a function of `width` (itself scaling with the line's own
    total length) and `attach_ratio`. Fixed by factoring the ribbon's
    own shared point math out of mct_axis_of_advance_ribbon() into a
    new `_axis_of_advance_ribbon_geometry()` helper (used by both, so
    they can't drift out of sync), and adding a new
    `mct_axis_of_advance_crossing_point()` expression function that
    computes the TRUE line-line intersection of the ribbon's own two
    edges via a new `_line_intersection()` helper - not another
    approximation. Also fixed a genuine mistake caught before it
    shipped: the `@qgsfunction` decorator for `mct_axis_of_advance_
    ribbon` ended up decorating the wrong function (`_line_intersection`,
    the next `def` after it) when the new functions were inserted above
    it - moved each decorator back onto its own actual function.
    726 tests passing on both QGIS versions (1 new: a direct geometric
    check that the crossing-point function's own result lies exactly ON
    both of the ribbon's own edges, for more than one geometry - strong
    enough that a regression back to the midpoint approximation would
    fail it even though that still "returns a point somewhere in the
    middle").
  - **Same-day eleventh follow-up, Main Attack's own turn - shape only,
    per the maintainer's own "render the arrow for now" scoping.** Main
    Attack (also listed among Table H-X's "real" ribbon-construction
    entries in this module's own docstring) moved off the old doubled-
    parallel-line approximation onto the real ribbon too, but with a
    genuinely different shape: "similar except the lines do not
    crossover, further the width of the shaft is constant" (the
    maintainer's own words). Added a `crossed` parameter to
    mct_axis_of_advance_ribbon() (default true, preserving Airborne/
    Aviation/Attack Helicopter's existing crossed behaviour unchanged) -
    when false, each edge runs straight to its own SAME-SIDE arrowhead
    corner instead of the opposite side's inset attachment point,
    skipping the attach_ratio math entirely (the shaft was already
    constant-width in the existing construction - width is a single
    shared value for both the Point-1 and Point-2 offsets already, so
    only the crossing behaviour needed to change). `_axis_of_advance_
    ribbon_symbol()` gained a `variant="main_attack"` branch, handled as
    an early return since it shares almost nothing with the icon-
    focused branches: no unit-context icon, Field T/Field W-W1 left at
    their ORIGINAL tip placement (LastVertex) rather than moved to
    Point 1 - explicitly scoped to shape only this round, per the
    maintainer's own "for now" framing, consistent with how Airborne's
    own first round also built the arrow alone before icon/label work
    followed in later rounds. Cleaned up the now-dead `doubled`
    parameter/branch on `_axis_of_advance_symbol()` (Main Attack was
    its only `doubled=True` caller) - that builder is now only
    Supporting Attack/Feint/Enemy, all identical. Caught and fixed one
    test regression along the way: `test_line_colours_follow_
    affiliation_per_ms_std_2525d_h_5_1_1_1` used Main Attack as its own
    representative Axis of Advance measure type, checking colour
    directly on `symbol.symbolLayer(0)` - which is now the geometry
    generator layer itself (colour lives on its own sub-symbol instead,
    same structure the airborne/aviation/attack-helicopter trio already
    use), swapped to Supporting Attack instead, unaffected by this
    round. 727 tests passing on both QGIS versions (2 new: the ribbon
    construction's own layer structure at Main Attack's own tip
    placement, and direct coverage of `crossed=false`'s own edge-
    termination geometry - each edge's own last point lands exactly on
    the arrowhead's SAME-SIDE corner, not the opposite one). Rendered
    for the maintainer's own review before any icon/label work - the
    arrowhead reads as a subtle taper rather than a pronounced barb
    without the crossing, flagged directly rather than assumed
    acceptable.
  - **Same-day twelfth follow-up, Field T's own placement.** The
    maintainer accepted the arrow shape and asked to "move the unique
    designation to the shaft, about 1/3 distance from the edge, text
    orientation should be horizontal, remove the DTG." Factored the
    shared font-marker-symbol setup out of `_designation_end_marker_
    layer()` into a new `_designation_font_marker()` helper (identical
    font/colour/Character wiring, only the wrapping symbol layer
    differs), then added `_shaft_fraction_label_layer()` - a
    QgsGeometryGeneratorSymbolLayer producing a Marker from QGIS's own
    `line_interpolate_point($geometry, length($geometry) * fraction)`
    expression (no new Python function needed, unlike the ribbon's own
    construction) at Point 1 read as "the edge." Reused the same
    "geometry-generator marker has no placement-driven rotation" fact
    Attack Helicopter's own crossing glyph already established -
    exactly what "text orientation should be horizontal" needed, no
    extra fixed-angle workaround. Dropped Field W-W1 (DTG) entirely for
    Main Attack too, the same "not worth the effort" call already made
    for Airborne/Aviation/Attack Helicopter, this time at the
    maintainer's own explicit request rather than inferred. 727 tests
    passing on both QGIS versions (the shape test rewritten for the new
    2-layer structure - ribbon + horizontal-label generator, zero
    QgsMarkerLineSymbolLayers now that Field T no longer rotates with
    the line and DTG is gone).
  - **Same-day thirteenth follow-up, the arrowhead's own width.** The
    maintainer flagged the arrowhead as "the same width as the shaft,
    increase the arrowhead width by 20%, and join the edge of the shaft
    tip and the arrowhead tips with a straight line - something similar
    to the arrowhead shape of the axis of advance of attack helicopter
    or friendly airborne." Added an `arrow_width_ratio` parameter to
    mct_axis_of_advance_ribbon() (default 1.0, so Airborne/Aviation/
    Attack Helicopter's own crossed construction is completely
    unaffected) and to `_axis_of_advance_ribbon_geometry()` - the
    arrowhead's own corners (`corner_left`/`corner_right`) now use
    `width * arrow_width_ratio` instead of the shaft's own plain
    `width`, with a new `shaft_corner_left`/`shaft_corner_right` pair
    (the shaft's own un-widened width, projected onto the same back-
    edge point) added specifically for the non-crossed construction's
    own edges to terminate at BEFORE one more straight segment out to
    the (now wider) arrowhead corner - the same "close the visible gap
    between a narrower run and a wider destination point" technique the
    CROSSED construction's own inset attachment points already needed,
    for a different underlying reason. Main Attack's own call site
    passes `arrow_width_ratio=1.2`. 728 tests passing on both QGIS
    versions (1 new: the arrowhead's own base width is exactly 1.2x the
    shaft's own width, computed directly from the returned geometry,
    not eyeballed off a render).
  - **Same-day fourteenth follow-up, the final piece of what the
    maintainer named the "master arrow"** (see this same date's own
    entry documenting that naming, and the standing project memory it
    was saved to for future cross-referencing). The maintainer asked to
    "add another line connecting the two edges of the shaft near the
    triangle following the shape of the triangle keeping the same
    distance - in effect the arrow tip is double lined," with a
    reference image showing two nested, parallel chevron lines. Added
    `_offset_arrowhead_chevron()` - a TRUE constant-perpendicular-
    distance parallel offset of the arrowhead's own two front edges
    (not a scaled-down copy, which would touch the real tip with a zero
    gap instead of keeping the same gap the whole way, per the
    maintainer's own explicit "keeping the same distance"), each offset
    edge extended back to where it crosses the real shaft edge nearest
    it. First attempt intersected the offset edge with the SHORT gap-
    closing segment's own line (`shaft_corner_left`-to-`corner_left`) -
    a real, test-caught bug: that segment is nearly perpendicular to
    the shaft, so the intersection point often lands nowhere near the
    actual drawn edge. Fixed by intersecting with the shaft edge's own
    SUBSTANTIAL straight run instead (`p2_left`-to-`shaft_corner_left`,
    the line the edge polyline actually follows just before that
    corner). Added a new `double_lined_arrowhead` parameter to
    mct_axis_of_advance_ribbon() (default false, so every other variant
    is unaffected), wired to `true` only for Main Attack's own call
    site. 729 tests passing on both QGIS versions (1 new: the inner
    chevron's own two base points land exactly ON the real shaft edges,
    not merely near them, and its own tip sits measurably back from the
    real tip rather than coincident with it - this test is what caught
    the gap-closing-segment bug above before it reached the maintainer).
  - **2026-08-11 correction, the inner chevron's own base points.** The
    maintainer flagged the fix above as still wrong: "no the inner
    chevron should be touching the tip of the arrow shaft, where the
    small line joining the triangle begins" - i.e. the base points
    should be EXACTLY `shaft_corner_left`/`shaft_corner_right`
    themselves (the point where the shaft's own constant width ends and
    the short gap-closing segment to the wider arrowhead corner
    begins), not a computed intersection with the shaft's own long
    straight run further back. Simplified `_offset_arrowhead_chevron()`
    accordingly - it now only computes the inner TIP (the true
    intersection of the two inward-offset edge lines); the two base
    points are passed straight through unchanged. Strengthened the
    existing test to check exact equality against each edge's own
    second-to-last vertex, not just "somewhere on the edge geometry" -
    the earlier, looser version of that assertion is exactly why this
    wrong placement wasn't caught the first time. 729 tests passing on
    both QGIS versions (no new test - the existing one now checks the
    right thing).
  - **2026-08-11 second correction, the inner chevron's own edges must
    be truly PARALLEL.** The maintainer caught a follow-on problem from
    the fix above: "the distance between the inner and outer chevron
    should be same throughout, so that the sides of the triangles are
    parallel lines, presently the inner chevron is slanting slightly
    with respect to the main triangle." Root cause: anchoring the base
    point exactly at `shaft_corner_left`/`shaft_corner_right` while
    still computing the inner edge's own DIRECTION from an
    independently-chosen perpendicular offset distance (from the
    PREVIOUS attempt) over-determined the line - the direction implied
    by "offset the real edge inward by a fixed distance" and the
    direction implied by "pass through this specific fixed point" only
    agree by coincidence. Fixed by dropping the `offset_distance`
    parameter entirely: each inner edge now runs from its own fixed
    base point along the SAME AZIMUTH as the corresponding real edge
    (`corner_left`-to-tip's own azimuth for the left side, mirrored for
    the right) - anchoring a point and a direction together, rather
    than a point and an independently-chosen distance, is what actually
    guarantees parallel sides; the inner tip is just where those two
    fixed-point/fixed-azimuth lines cross. 729 tests passing on both
    QGIS versions (1 new: the inner edges' own azimuth matches the real
    edges' azimuth exactly, computed directly rather than eyeballed -
    this is the check that would have caught the slant before it
    reached the maintainer). Main Attack's own arrow is now frozen -
    the maintainer confirmed "perfect, this can be frozen for main
    attack."
  - **2026-08-11, Supporting Attack's own turn - a verbatim reuse, not
    a new construction.** "just replicate the master arrow for the
    supporting attack, no other changes to it" - the maintainer's own
    words. Added a `_MASTER_ARROW_VARIANTS` module-level constant
    (`("main_attack", "supporting_attack")`) and generalised
    `_axis_of_advance_ribbon_symbol()`'s own master-arrow branch to key
    off membership in that tuple instead of the literal string
    `"main_attack"` - adding a future variant that's "just the master
    arrow too" is now a one-line addition to that tuple, not a new
    branch. Supporting Attack's own call site
    (`_LINE_SYMBOL_BUILDERS["axis_of_advance_supporting_attack"]`) now
    points at `_axis_of_advance_ribbon_symbol(variant="supporting_
    attack")` instead of the old shared `_axis_of_advance_symbol()`
    approximation, which is now down to just Feint/Enemy. Test fallout
    handled the same way Main Attack's own move required: Supporting
    Attack removed from the approximated-family loop test, and swapped
    out as `test_line_colours_follow_affiliation_per_ms_std_2525d_h_
    5_1_1_1`'s own representative measure type (its colour now lives on
    the geometry generator's own sub-symbol, not `symbolLayer(0)`
    directly) in favour of Feint. 729 tests passing on both QGIS
    versions (the Main-Attack-specific shape test generalised to cover
    both master-arrow variants in one parametrised test, rather than a
    second near-duplicate test). Rendered and confirmed structurally
    and visually identical to Main Attack's own frozen shape.
  - **2026-08-11, a scope-creep mistake caught and corrected in the same
    round: the double-lined arrowhead is Main Attack's own only, NOT
    part of what Supporting Attack replicates.** Right after Supporting
    Attack's own replication, the maintainer said "remove the inner
    chevron from this, keep only the outer triangle and the connectors
    from the shaft to the outer triangle" - read (wrongly) as applying
    to the shared master-arrow construction, so the double-lined
    arrowhead feature (`_offset_arrowhead_chevron()`, the
    `double_lined_arrowhead` parameter, its own test) was deleted
    outright, removing it from BOTH Main Attack and Supporting Attack.
    The maintainer caught this immediately: "we are doing one symbol at
    a time, once i confirm something works, don't touch it again - the
    main attack was not supposed to be touched, main attack requires
    the inner chevron, supporting attack does not require it!" - Main
    Attack's own arrowhead had already been explicitly frozen
    ("perfect, this can be frozen for main attack") earlier the same
    session; the instruction to drop the chevron was actually scoped to
    Supporting Attack alone, the symbol actually being worked on.
    Restored `_offset_arrowhead_chevron()`, the `double_lined_
    arrowhead` parameter/branch in mct_axis_of_advance_ribbon(), and
    its own dedicated test, all verbatim. Added a new
    `_DOUBLE_LINED_ARROWHEAD_VARIANTS = ("main_attack",)` constant and
    a small `_axis_of_advance_master_arrow_expression(variant)` helper
    in offensive_control_measures.py, so the master arrow's own shared
    branch can differ on this ONE point per variant (Main Attack's own
    call passes `double_lined_arrowhead=true`, Supporting Attack's own
    doesn't) without duplicating the rest of the construction. 729
    tests passing on both QGIS versions (back to the pre-mistake count -
    the double-line test restored, plus the shared shape test updated
    to expect the two variants' own now-genuinely-different ribbon
    expressions rather than assuming they're identical). This is now a
    standing reminder for the rest of H5/H-XI: once the maintainer
    confirms a specific symbol's own construction, treat it as frozen
    even when a nearby instruction about a DIFFERENT symbol could be
    read as applying more broadly - when in doubt about scope, the
    symbol actually in focus is the default target, not the shared code
    path underneath it.
  - **2026-08-11, Axis of Advance for a Feint's own turn.** Main Attack
    and Supporting Attack both confirmed fine and explicitly frozen
    ("please don't touch them anymore"). Feint's own instruction: "use
    the arrow and unique identification of supporting attack as the
    base, now add an outer chevron, outside the arrowhead, made of
    dashed line with adequate gap between the arrowhead and the new
    outer chevron." Added Feint to `_MASTER_ARROW_VARIANTS` (reusing
    the shared base, no double-lined arrowhead - `_DOUBLE_LINED_
    ARROWHEAD_VARIANTS` stays Main-Attack-only) and built a genuinely
    new construction on top: a new `mct_axis_of_advance_outer_chevron()`
    expression function - the mirror image of `_offset_arrowhead_
    chevron()`'s own inner chevron (same "parallel line through a fixed
    point" technique), offset OUTWARD from each arrowhead corner by a
    `gap` distance instead of anchored to the shaft. Rendered via its
    own SEPARATE `QgsGeometryGeneratorSymbolLayer` (not folded into
    mct_axis_of_advance_ribbon()'s own MultiLineString the way the
    inner chevron is) with a fixed dashed pen (`Qt.PenStyle.DashLine`)
    - this mark is dashed regardless of the feature's own status, not
    status-driven like the shaft/arrowhead's shared stroke style, so it
    needed its own independent line style. Tuned over three rounds of
    direct maintainer feedback against real renders: `gap_ratio=1.0`
    (first render) -> `0.8` ("the gap is too much, reduce it by 1/5th,
    adjust the chevron size accordingly") -> `0.2` ("gap is still too
    high, reduce the gap by 75%", i.e. `0.8 * 0.25`) -> `0.32`
    ("increase gap by 60%", i.e. `0.2 * 1.6`) - no separate "size"
    parameter was ever needed, since the chevron's own shape is a pure
    function of the gap, so it stays proportionate at any value. Test
    fallout from Feint leaving the old approximated family (down to
    Enemy's own only now): removed Feint from the approximated-family
    loop test, and swapped `test_line_colours_follow_affiliation_per_
    ms_std_2525d_h_5_1_1_1`'s own representative measure type from
    Feint to Final Coordination Line (Table H-XI's own simple end-
    labelled line) - Enemy alone remained in the approximated family
    but its own hardcoded red-regardless-of-affiliation colour can't
    stand in for testing the general affiliation-colour mapping either.
    731 tests passing on both QGIS versions (2 new: Feint's own 3-layer
    structure - master arrow base + dashed outer chevron - and direct
    geometric coverage confirming the outer chevron's own two base
    points sit strictly outside the real arrowhead's own corners, not
    overlapping or inside).
  - **2026-08-11, Axis of Advance - Enemy Confirmed/Templated - the
    LAST Table H-X "real" entry, closing out this appendix's own
    master-arrow rollout.** "just use the master arrow and default
    colour to red" - already true by construction: the shared
    `_OFFENSIVE_LINE_COLOR_EXPRESSION`/`_ENEMY_MEASURE_TYPES` mechanism
    (built long before the master arrow existed) applies uniformly via
    `_apply_offensive_line_color()` regardless of which construction a
    measure type uses, so switching Enemy's own construction needed no
    new colour code at all. Added `"enemy"` to `_MASTER_ARROW_VARIANTS`
    and pointed its own `_LINE_SYMBOL_BUILDERS` entry at
    `_axis_of_advance_ribbon_symbol(variant="enemy")`. This left
    `_axis_of_advance_symbol()` (the old single-thick-line-plus-
    arrowhead approximation) with ZERO remaining callers in Table H-X -
    deleted it outright rather than leaving dead code behind, per this
    project's own standing convention (Table H-XI's own Direction of
    Attack family has its own separate, still-used approximation,
    `_direction_of_attack_symbol()`, untouched). Test fallout: the
    approximated-family loop test (`test_axis_of_advance_variants_are_
    a_thick_line_with_a_filled_arrowhead`) had nothing left to test
    once Enemy left, so it was deleted rather than kept as an empty
    loop; `test_enemy_variants_render_red_regardless_of_affiliation`
    updated for Axis of Advance - Enemy's own colour now living on the
    geometry generator's own sub-symbol (the same relocation every
    other master-arrow variant already needed), Direction of Attack -
    Enemy unaffected. Rewrote the module's own top-of-file narrative to
    reflect that all seven of Table H-X's own real ribbon-construction
    entries are now complete. 730 tests passing on both QGIS versions
    (one fewer than before - the deleted empty-loop test, not a
    coverage gap).
  - **2026-08-11, Table H-XI, Direction of Attack - Friendly Aviation
    (140601), two real construction defects fixed.** The project
    maintainer's own instruction: "the aviation symbol should be
    before the line origin, and should be bounded in a rectangle; the
    unique designation should be just behind the arrow head with
    suitable masking, in line with the arrow shaft."
    1. **Unit icon before the line's own origin.** Re-reading the
       template picture directly (page 432) showed the first pass had
       missed a real element: the standard's own construction shows the
       bowtie/hourglass glyph TWICE - once ON the line at its own
       origin (Point 2, already built), and again, separately, BOXED,
       BEFORE that origin - both in solid black line-art, not this
       appendix's usual grey "illustrative only" annotation colour, so
       both are real drawn geometry. First attempt hand-built a custom
       inline-SVG rectangle outline to frame a shifted copy of the
       bowtie (QGIS's own `QgsSimpleMarkerSymbolLayerBase.Shape` enum
       has no non-square "Rectangle", confirmed directly against the
       enum) - the maintainer redirected mid-build: "we can use the
       aviation - fixed wing symbol from the milsymbol.js" instead, an
       already-catalogued `ENTITIES["ground_unit"]["aviation_fixed_
       wing"]` (120800) entity. Reused `_unit_context_icon_layer()`
       (the same real-SIDC-render technique Axis of Advance's own
       Airborne/Aviation/Attack Helicopter icons already use) rather
       than the hand-built SVG - simpler AND more standard-compliant,
       since the real SIDC render already comes rectangle-framed with
       no extra frame needed. Extended that function with a new
       optional `offset` parameter (None by default, every existing
       caller unchanged) so this one caller could shift the icon off
       its usual at-the-vertex position. One genuine surprise, found by
       render-and-compare rather than assumed: `QgsSvgMarkerSymbolLayer.
       setOffset()` is applied BEFORE that same layer's own `setAngle
       (90)` (the existing rotation this icon frame already needed, to
       put its broad dimension along the shaft), not after - so a
       desired final along-shaft offset of (-8, 0) actually needed to
       be requested as local (0, +8), confirmed by first trying the
       "obvious" (-8, 0) value, observing the icon jump vertically
       instead of horizontally in the render, then solving the implied
       90-degree rotation and re-testing.
    2. **Field T real masking.** Every other Direction of Attack/Axis
       of Advance variant's own Field T is a `QgsFontMarkerSymbolLayer`
       glyph, which has no masking capability of its own (confirmed by
       re-reading c2_measures.py's own `_boundary_symbol()` history -
       real Selective Masking, `QgsTextMaskSettings`, only ever attaches
       to a genuine PAL label). Moved Friendly Aviation's own Field T,
       and ONLY that one measure type's, onto a real PAL label: gave
       its own line symbol layer a stable `.setId()` (
       `_DIRECTION_OF_ATTACK_AVIATION_LINE_SYMBOL_LAYER_ID`) and wired
       the Lines layer's previously-placeholder empty-string labelling
       call to a real CASE-guarded expression (every other measure type
       on the layer still resolves to `''`, unaffected) with
       `masked_symbol_layer_ids` pointing at that one id. "Just behind
       the arrow head... in line with the arrow shaft" needed the label
       pinned to a FIXED point along the line rather than QGIS's own
       default best-position search - extended `_build_pal_layer_
       settings()`/`_configure_designation_labeling()` in
       `_control_measure_shared.py` with two new optional parameters,
       `line_anchor_percent`/`anchor_text_point` (both None by default,
       every existing caller - Boundary, Light Line, Areas - unchanged),
       using `QgsLabelLineSettings.AnchorType.Strict` plus a 0.9 anchor
       percent and `AnchorTextPoint.EndOfText` so the label's own
       trailing edge sits just short of the line's end, extending
       backward along the shaft rather than past it into the arrowhead.
       Confirmed by render: a real gap cut into the shaft exactly the
       shape of the rendered text, sitting just short of the chevron.
    One test segfaulted the whole interpreter during this round, not
    merely failed - `settings.format().mask()` chained in one
    expression: `QgsPalLayerSettings.format()` returns a `QgsTextFormat`
    BY VALUE, and calling `.mask()` straight off that temporary let its
    own C++ object get garbage-collected before the returned
    `QgsTextMaskSettings` was read, a sharper case of the same "wrapped
    C/C++ object has been deleted" class of bug this project's test
    suite hit once before (a loop-variable shadowing a symbol layer,
    same appendix, 2026-08-11 earlier). Fixed by holding the
    intermediate `QgsTextFormat` in its own named variable. 733 tests
    passing on both QGIS versions (3 new: the unit icon's own
    placement/exclusivity, the masked PAL label's own configuration,
    and the line layer's own stable id).

    **2026-08-12 follow-up, Axis of Advance only** (a minor correction
    the project maintainer caught after the Direction of Attack round
    above): the shaft's own base unit-context icon (Friendly Airborne's
    Infantry+Airborne-modifier, Friendly Aviation's and Attack
    Helicopter's shared Aviation Rotary Wing) was rotating to match the
    arrow's own direction, the same rotate-with-line behaviour every
    other marker on these ribbons uses - "the symbol at the base of the
    shaft... should not be rotated but be straight", then "same is the
    case for... attack helicopter" once asked directly. `_unit_context_
    icon_layer()` gained a new `rotate=True` parameter (default True,
    every pre-existing caller unchanged) controlling the wrapping
    `QgsMarkerLineSymbolLayer`'s own `rotateSymbols` flag; the one call
    site inside `_axis_of_advance_ribbon_symbol()`'s icon branch (shared
    by all three variants) now passes `rotate=False`. Direction of
    Attack - Friendly Aviation's own icon (added the round before,
    different call site, different placement logic - "before the line
    origin") is untouched, still rotates - not part of this correction.
    Confirmed by rendering all three variants on a deliberately diagonal
    shaft: the icon frame now stays upright/level regardless of the
    arrow's own direction, while Attack Helicopter's own separate
    crossing-point glyph (already fixed-orientation by construction) is
    unaffected. 733 tests passing on both QGIS versions (no new tests
    needed new coverage beyond 3 added assertions - `rotateSymbols()` is
    now explicitly checked False on each of the three icon layers in
    their own existing tests).

    **Immediate correction the same day**: "all three icons are 90 deg
    off, rotate them counter clockwise by 90 deg" - the maintainer's own
    words, right after seeing the render above. Root cause: the fixed
    `svg_angle=90` on `_unit_context_icon_layer()`'s own frame/hump
    layers was tuned specifically for the rotate-WITH-line case (it
    compensates for the SVG's own native orientation vs. the outer
    line-rotation's own reference axis - see that function's own
    docstring) - once `rotate=False` removed that outer reference
    entirely, the same fixed value rendered 90 degrees off. Both
    `frame_layer.setAngle()` and the airborne modifier's own `hump_
    layer.setAngle()` now branch on `rotate` (`90 if rotate else 0`,
    counter-clockwise per QGIS's own clockwise-increasing angle
    convention). Direction of Attack - Friendly Aviation's own icon
    (still `rotate=True`, added the round before) is unaffected - kept
    its original 90. Confirmed by render: all three Axis of Advance
    icon frames are now landscape (matching the real SIDC's own 158x108
    viewBox) and level, Friendly Airborne's own Infantry-cross-plus-
    Airborne-modifier-humps glyph and Aviation/Attack Helicopter's
    shared Aviation Rotary Wing glyph both read correctly inside their
    own boxes. 733 tests passing on both QGIS versions (angle
    assertions added to the same three existing tests, plus a
    regression check on Direction of Attack - Friendly Aviation's own
    icon confirming it kept `rotate=True`/angle 90, unaffected).

    **Same-day follow-up round, Direction of Attack - Friendly Aviation
    only**, after the project maintainer pasted the standard's own
    EXAMPLE picture directly for comparison against a live plugin
    render:
    1. **Bowtie fill + position.** "it is filled instead of being an
       outline only and is left and above the line" - both triangles in
       `_direction_of_attack_bowtie_layer()` now render unfilled
       (transparent fill, affiliation-coloured stroke only). Getting it
       correctly "at the beginning of the shaft moved inward slightly"
       took three real attempts, each render-verified, not assumed:
       (a) adding the same local X delta to both triangles' own
       `setOffset()` broke the tip-to-tip meeting entirely (two
       disconnected triangles); (b) `QgsMarkerLineSymbolLayer.
       setOffsetAlongLine()` looked like the right tool (a genuine
       "shift the anchor N mm along the line" primitive) but combined
       badly with the triangles' own per-layer offsets, shifting the
       whole glyph off the line vertically; (c) a dedicated standalone
       probe script (rendering single markers at known angle/offset
       combinations and measuring rendered centroids in pixels) revealed
       the real rule: a marker's own `setOffset()` is applied in its
       OWN pre-rotation local frame, then rotated by that marker's own
       `angle` - for angle=90, local (x,y) rotates to final (-y,x); for
       angle=270, local (x,y) rotates to final (y,-x). Solving both for
       a shared final target gave each triangle its own DIFFERENT local
       offset (right: (0,-3), left: (0,3)) - this also fixed a small
       pre-existing vertical bias (-triangle_size/2) baked into the
       ORIGINAL, never-corrected baseline offsets, very likely part of
       what "above the line" was describing even before this round.
    2. **Icon "should be straight".** "like axis of advance, the symbol
       for aviation should be straight" - `_unit_context_icon_layer()`'s
       own call for this icon now passes `rotate=False` too (same
       correction Axis of Advance's own base icons got earlier the same
       day), plus a matching offset fix (the old QPointF(0,8) value was
       specifically solved for the OLD rotate=True/angle=90 case; the
       non-rotating case needs a plain QPointF(-8,0), no rotation
       compensation).
    3. **DTG two-line + repositioned.** "the DTG in the plugin is going
       ahead of the arrow, if possible split it into two lines and
       place it below the arrow." Confirmed by a dedicated probe that
       `QgsFontMarkerSymbolLayer`'s own Character property has no
       multi-line text layout of its own (silently drops an embedded
       `\n`, unlike a real PAL label) - already documented elsewhere in
       this module from an earlier round (Main Attack/Supporting
       Attack/Feint's own DTG, dropped entirely rather than pay this
       cost) but not yet applied here. Split into two separate
       expressions/marker layers (`_DTG_START_LINE_EXPRESSION`/
       `_DTG_END_LINE_EXPRESSION`), also dropping a redundant trailing
       "Z" the old single-expression version appended (each raw DTG
       value already carries its own embedded Zulu-time designator).
       Repositioning needed -17.0mm of backward X offset to clear the
       chevron arrowhead's own painted stroke outline entirely - -10/
       -11/-13 all still clipped the first line's own trailing "-"
       under that outline, confirmed by a dedicated probe render (the
       dash was never truly "missing", just hidden under the chevron's
       own opaque stroke - a plain single-character isolated probe of
       the same string rendered it fine, which is what pointed at
       overlap rather than a text-rendering bug).
    This round applies to Direction of Attack - Friendly Aviation only
    for the bowtie/icon; Field W-W1's own fix (item 3) is shared, generic
    code and applies to every Direction of Attack variant. 733 tests
    passing on both QGIS versions (layer/font-marker counts updated for
    the extra DTG marker layer, plus a new bowtie-fill assertion).

    **Immediate same-day follow-up round**, three more corrections from
    a live plugin screenshot compared directly against the standard's
    own EXAMPLE picture:
    1. **Arrowhead width.** "reduce the arrowhead width to match the
       shaft width" - the chevron's own stroke width dropped from 1.3mm
       (the 2026-08-10 "bold enough to read" widening, see this
       function's own docstring) to 0.5mm, matching the shaft's own
       line width exactly. Shared code, applies to every Direction of
       Attack variant.
    2. **Bowtie tips overlapping.** "only the tips should touch each
       other - shape like a bowtie, right now they are overlapping."
       The PRECEDING round's own fix (moving the glyph "inward slightly"
       - see that entry's own math) solved both triangles converging on
       the exact SAME shared point, which turned out to be each
       triangle's own CENTRE, not its tip - concentric, heavily
       overlapping shapes, not a bowtie. Re-solved the same rotation
       equations for each triangle's own centre landing
       `triangle_size / 2` on its own AWAY side of the shared meeting
       point instead of directly on it - confirmed by a dedicated probe
       measuring the two rendered triangles' own pixel bounds: zero
       overlapping pixels, one triangle's own rightmost column exactly
       equal to the other's own leftmost column.
    3. **Line visible below the bowtie.** "the line should not be
       visible below the bowtie." First attempt: a SECOND masked PAL
       label (the exact same real-masking technique Field T's own
       label already uses), positioned near the bowtie instead of the
       arrowhead, via `QgsRuleBasedLabeling` (two rules sharing one
       feature, the same tool `_configure_area_designation_labeling()`
       already uses in c2_measures.py for a different-placement
       situation). This did NOT work, confirmed by render - the second
       rule's own `QgsTextMaskSettings` evaluated correctly in
       isolation (`enabled() == True`, the right symbol layer id
       referenced) but never actually cut a visible gap, regardless of
       which rule came first; QGIS's Selective Masking appears not to
       compose across two independent rules/providers both masking the
       same symbol layer on one `QgsRuleBasedLabeling` layer. Rather
       than depend on that undocumented limitation, switched to real
       geometry instead: for Friendly Aviation only, the base line
       layer is now wrapped in a `QgsGeometryGeneratorSymbolLayer`
       using `line_substring()` to drop the line's own first ~11% of
       length (tuned by render against a single test line to clear the
       bowtie's own footprint plus a small margin - a percentage of
       total line length, not a fixed mm distance, the same "not exact,
       an approximation" trade-off Field T's own anchor percent already
       accepts, since `line_substring()` takes CRS-unit distances, not
       render units) - real geometry, not compositing, so nothing is
       left underneath to show through regardless of any masking-engine
       quirk. `line_layer`'s own stable id (used by Field T's own mask)
       is unchanged, just nested one level deeper inside the new
       generator's own sub-symbol.
    733 tests passing on both QGIS versions (one test rewritten for the
    new nested-generator structure, one obsolete masking test removed
    after the approach changed, `_control_measure_shared.py`'s own
    speculative `text_color` parameter added and then removed again in
    the same round once the masking approach was abandoned).

    **Immediate next-day-equivalent follow-up round** (same session),
    three more requests plus a real design pivot on the trim/mask
    saga above:
    1. **Field T colour.** "change the colour of the unique designation
       also into blue (friend)" - Field T's own PAL label had no colour
       override before (plain black, the shared text format's own
       default); now carries a DATA-DEFINED `QgsPalLayerSettings.
       Property.Color` using the same `_OFFENSIVE_LINE_COLOR_EXPRESSION`
       every other piece of this construction already uses (fetched
       back off `layer.labeling().settings()` after `_configure_
       designation_labeling()` runs, mutated, and reapplied via a fresh
       `QgsVectorLayerSimpleLabeling` - no new parameter added to the
       shared `_build_pal_layer_settings()` helper for a single-caller
       need).
    2. **The `@map_scale` trim didn't generalise either.** The previous
       round's fix (see its own entry above) replaced a fixed-fraction
       line trim with one derived from `@map_scale / 1000`, reasoning
       that this would give a genuine physical mm distance regardless
       of the digitized line's own length. Confirmed by a direct,
       careful comparison of `QgsMapSettings.scale()` computed BEFORE
       rendering against the SAME expression evaluated with the SAME
       map settings that render_dtg_check.py's own script actually
       uses: consistent scale (~62000), and evaluating the trim
       expression in that exact context returned the ENTIRE untrimmed
       line - `line_substring()`'s own start/end distances, computed
       from that scale, came out far larger than the line's own total
       length in its own CRS units for this test geometry, and the
       real render's own gap pattern didn't match either the "fully
       untrimmed" or the "correctly trimmed" prediction cleanly. Rather
       than keep chasing exactly how `@map_scale` resolves inside a
       geometry-generator expression at real paint time, the maintainer
       proposed a genuinely simpler design instead of another patch:
       **don't overlap the bowtie with the real line at all.** The
       bowtie's own shared centre moved from a small positive offset
       (sitting ON the drawn line, needing something to hide the line
       underneath) to `-triangle_size` (fully BEFORE the line's own
       start, its own right edge touching Point 2 exactly) - the real
       shaft now draws completely plain and untouched, for every
       Direction of Attack variant including Friendly Aviation, no
       trim/mask/generator wrapping of any kind. "The arrow shaft
       should protrude slightly beyond the bowtie" (the same request)
       is a new, separate, purely decorative fixed-length `Shape.Line`
       marker (`_direction_of_attack_bowtie_stub_layer()`) positioned
       at the bowtie's own left edge - not real line geometry at all,
       just another small mm-sized glyph positioned the same "fixed
       offset, solved through the marker's own angle rotation" way
       every other glyph in this module already is. This retires the
       ENTIRE `@map_scale`/`line_substring()` construction from the
       previous round - simpler, and immune to whatever `@map_scale`
       actually does inside that specific rendering context, since it's
       no longer used at all.
    3. **Icon spacing.** Once the stub (item 2) landed almost exactly
       where the unit icon already sat (their two positions were only
       0.1mm apart, coincidence of the two independently-chosen
       numbers), "shift the aviation symbol left of the stub with some
       gap" moved the icon's own offset to a new constant derived from
       the stub's own left edge plus a 3mm gap, rather than the
       original hand-picked -8.0mm - so icon, stub, and bowtie now read
       as three visually distinct pieces left to right.
    733 tests passing on both QGIS versions (layer count/order tests
    updated for the new stub layer and the reverted-to-plain line
    layer).

    **Moving on to Direction of Attack - Main Attack (140602, page
    433)**, same session: "using with the DOA - Friendly aviation
    symbol, drop the aviation symbol, bowtie and line segment stub. now
    move the unique designation Field T to center of shaft, add a
    chevron outside the arrowhead and connect the two arrowheads."
    Confirmed against the standard's own template/example pictures
    directly (zoomed well past print resolution): Main Attack shares
    the plain status-driven shaft every Direction of Attack variant
    has, no unit icon/bowtie/stub (those are Friendly Aviation's own),
    and its own DOUBLE chevron arrowhead - two nested V shapes, back
    (open) ends joined by a short strut on each side, not two
    independent V's. `_direction_of_attack_symbol()` gained a `main_
    attack` parameter, scoped to `direction_of_attack_main` only via
    the `_LINE_SYMBOL_BUILDERS` lambda - every other variant (Supporting
    Attack/Ground Axis/Feint/Enemy) is untouched.

    The double chevron itself needed real geometry, not QGIS's own
    built-in `Shape.ArrowHead` (no way to express "two nested copies
    plus struts", and its own corner coordinates for a given size
    aren't exposed to build struts against) - a hand-authored inline
    SVG instead (`_DIRECTION_OF_ATTACK_MAIN_ATTACK_CHEVRON_SVG`, the
    same `base64:`/`param(fill)`/`param(outline)` technique
    `_attack_helicopter_direction_glyph_layer()` already uses). Getting
    the actual shape right took four real rounds of maintainer feedback
    against live renders, each one a genuine geometry correction, not
    just re-guessing numbers:
    1. **First cut**: two independently hand-picked V's. Feedback:
       "the chevron should be made of parallel lines for the side of
       the triangle, and you added an inner chevron instead of outer,
       anyway make the lines of both chevron lines parallel." Computing
       both arms' own slopes directly (not eyeballing) confirmed the
       two V's genuinely weren't parallel - the inner one was
       independently steeper, which is very likely also what read as
       "inner instead of outer" (a wider-angled inner V visually
       competes with the outer one instead of sitting cleanly inside
       it).
    2. **Second cut**: picked the OUTER chevron's own corners first
       (back corners at the SVG's own declared-viewBox centre, i.e. the
       marker's own default anchor point), derived the INNER chevron as
       a true parallel offset toward the centreline (same principle
       `expressions/military_symbology_functions.py`'s own
       `_offset_arrowhead_chevron()` already uses for Axis of Advance's
       own double-lined arrowhead, worked out by hand since this glyph
       is a fixed-size marker, not real ribbon geometry). This also
       answered "the shaft should touch the arrowhead" (anchoring the
       OUTER chevron's own back corners at the anchor put the shaft's
       own end exactly there) and added "Field T - unique designator
       should have a mask so that line is not seen below it" (see
       below).
    3. **Third correction**: "make the arrow shaft touch the arrow
       head - inner chevron." Anchoring the OUTER chevron at the
       marker's own anchor point meant the shaft touched the OUTER
       shape, leaving the smaller INNER one set back with a visible
       gap - backwards from what real double-chevron arrowheads (and
       every other Direction of Attack variant's own single arrowhead)
       actually do: the shaft flows into the "real"/inner arrowhead,
       with the outer one added around/past it. Swapped which shape is
       built first: INNER chevron's own corners now sit at the anchor,
       OUTER is a genuine parallel expansion OUTWARD from it (the same
       principle `mct_axis_of_advance_outer_chevron()` already
       established for Axis of Advance's own Feint - a chevron
       expanded from a real one, not built independently).
    4. **Fourth correction**: "the angle of the triangle is slightly
       less, check the angle of the triangle of the arrow head of DOA -
       friendly aviation, make this also same." Measured the real,
       already-confirmed single-chevron marker directly with a
       dedicated probe render (found its own half-angle from the
       centreline is ~43.7 degrees, a near-90-degree full V) rather
       than eyeballing a match, then recomputed the inner chevron's own
       back-corner-Y/tip-reach ratio to match that measured angle
       exactly, rebuilding the outer chevron the same "parallel
       expansion" way once more.

    Field T's own move to the shaft centre started as a plain
    `CentralPoint`-placed font marker (rotate-with-line, same technique
    every other variant's own Field T uses, just relocated) - then
    "Field T - unique designator should have a mask so that line is not
    seen below it" (the shaft now runs directly under the centred text)
    moved it onto a genuine masked PAL label instead, the exact same
    technique Friendly Aviation's own Field T already uses, just
    anchored at the shaft's own centre (0.5) instead of near the
    arrowhead (0.9) and masking Main Attack's own line id instead of
    aviation's. This meant reintroducing `QgsRuleBasedLabeling` on this
    layer (abandoned earlier in the Friendly Aviation bowtie-masking
    dead end) - but this time each rule matches a DIFFERENT feature
    (aviation's own Field T vs. Main Attack's own), not two rules
    competing to mask the SAME feature's line, which is what actually
    failed before. That distinction still weren't quite enough on its
    own: giving each rule its OWN single masked-symbol-layer-id list
    logged "Different sets of symbol layers are masked by different
    sources! Only one (arbitrary) set will be retained!" and silently
    dropped one variant's own masking - QGIS's own Selective Masking
    configuration is apparently LAYER-wide, not per-rule/per-provider.
    Fixed by giving BOTH rules the SAME combined list (both variants'
    own line ids together) - masking an id a given feature doesn't even
    have is harmless, since the cut only happens where that rule's own
    label text actually renders. Main Attack's own Field T also kept
    its existing affiliation colouring (the font-marker technique
    already had this via `_designation_font_marker()`) by setting the
    same data-defined `QgsPalLayerSettings.Property.Color` on both
    rules' own settings, not just aviation's.

    737 tests passing on both QGIS versions (four new: Main Attack's
    own masked PAL label, stable line id, absence of a font-marker
    Field T, and the double-chevron glyph's own presence/absence across
    variants; existing layer/font-marker-count tests updated for one
    fewer symbol layer now that Field T is a label, not a marker).

- **2026-08-12, Table H-XI's own remaining Direction of Attack variants,
  a full cross-check against the standard, and the start of Table
  H-XII.** Worked strictly to the maintainer's own dictated
  instructions this round, with the manual explicitly set aside until
  they asked for it ("just follow my instructions please, don't refer
  the manual for now, i will tell you when to refer the manual").

  - **Supporting Attack / Enemy / Friendly Ground Axis** each built
    from the previous one's own confirmed construction, exactly as
    dictated: Supporting Attack = Friendly Aviation minus the unit
    icon, bowtie and stub; Enemy = Supporting Attack with the colour
    forced red (which needed no new code at all -
    `direction_of_attack_enemy` was already in `_ENEMY_MEASURE_TYPES`,
    so every `_apply_offensive_line_color()` call this construction
    already goes through renders red automatically - verified by
    rendering with `affiliation="friend"` and confirming it still came
    out red); Ground Axis = Supporting Attack verbatim with ordinary
    affiliation colouring. Each got its own stable line-symbol-layer id
    and its own masked-PAL Field T rule, all sharing one combined
    `masked_symbol_layer_ids` list per the H5 finding above.

  - **Direction of Attack for a Feint** - "add a dashed chevron outside
    the main arrowhead, at a gap 1/6 of the length of arrowhead side,
    the new chevron being parallel to the existing arrowhead". The real
    arrowhead is the built-in `Shape.ArrowHead` marker, whose exact
    corner coordinates aren't exposed, so it was **measured** with a
    dedicated probe render (single marker, rendered alone, true tip
    located via a column-wise min-y-spread scan so stroke bleed
    couldn't skew it): half-angle ~43.727 degrees, arm length
    ~4.8505mm, and the marker's own anchor confirmed to BE the tip
    (within 0.05mm), not the bounding-box centre. The outer chevron is
    then a genuine perpendicular offset of each arm by gap =
    side/6 ≈ 0.8084mm with the two offset lines re-intersected for the
    new tip - not a scaled copy, which is what produced non-parallel
    arms the first time this technique was tried for Main Attack.

  - **Main Attack rebuilt** on that same measured geometry - "start
    with the symbol for feint; change the outer chevron to solid line,
    add line segments to join ends of both the stubs". Main Attack no
    longer has a special-cased chevron branch at all: it now uses the
    same real single-chevron marker every other variant does, plus one
    extra SVG layer carrying the solid outer chevron and the two struts
    joining each side's back corners. The original fully hand-authored
    double-chevron SVG (four rounds of correction) was retired.

  - **Cross-check against the standard**, at the maintainer's own
    request once the family was complete ("that clears all chapter
    X/XI - cross check please"). Read Tables H-X and H-XI directly
    (printed pages 428-433). Reported five discrepancies; the
    maintainer ruled on each, and **three were explicitly dismissed as
    non-issues**, which is itself worth recording: Main Attack's own
    double-lined arrowhead IS correct as built (my reading of the
    printed glyph as a single thick stroke was wrong); Enemy's Field N
    / "ENY" literal / absent DTG are monochrome-print conventions that
    don't apply once the symbol is rendered red, and an unfilled DTG
    field simply renders nothing, so neither needs changing. Of the
    two real findings, **Field T and Field W-W1 (DTG) were in the wrong
    place on all six variants** - the standard clusters both just past
    PT2, near the line's own START, where this build had put them near
    the tip (and, for Main Attack, at the shaft's centre). Both moved:
    one shared `_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT` (0.12,
    `StartOfText`) replaced the old per-variant 0.9/0.5 anchors, and
    the DTG's own two font markers moved from `LastVertex` with a large
    negative pull-back to `FirstVertex` with a small positive push.
    Friendly Aviation's own icon box was checked and confirmed already
    correct.

  - **Point of Departure (160400) rebuilt.** Reported as "missing"; it
    turned out to exist but to be positioning its unique designation
    with a hand-computed `QgsPalLayerSettings` offset (local-SVG-
    coordinate probe plus an mm-per-unit scale factor), on the strength
    of a comment claiming both of milsymbol.js's own text slots were
    wrong for this SIDC. A direct probe render disproved that: the
    plain `uniqueDesignation` slot places the text at (150, -30) - same
    y as the "PD" glyph, just past the box's right edge - exactly the
    standard's own top-right placement. Rebuilt on the same
    `mct_sidc_svg(...)` technique Fly-To-Point already uses, deleting
    the custom-offset machinery (~50 lines: two constants, an offset
    helper, and the whole `_configure_points_labeling()` function).

  - **Table H-XII started - Encirclement.** Perimeter decoration
    changed from repeated tick strokes to real triangles, base on the
    perimeter, gap 60% of base (interval = 1.6 x base); then hollow,
    +20% size, rotated 180 degrees with the base - not the tip - flush
    on the line, which needed the marker offset by half its own
    measured height so the perimeter stopped cutting through the
    shape's bounding-box centre. **A third round then caught a real
    bug the earlier renders had hidden**: the maintainer reported the
    triangles pointing inward in live QGIS. Reproduced with a probe
    rendering the same polygon in both ring windings - apex direction
    depends on whether the polygon was digitized clockwise or
    counterclockwise, and QGIS does not normalise that for hand-drawn
    shapes. Every render up to that point had happened to use a
    counterclockwise test ring, so the correct-looking result was a
    coincidence, not a guarantee. Fixed by normalising the winding
    before the markers are placed - a `QgsGeometryGeneratorSymbolLayer`
    feeding `boundary(force_polygon_ccw($geometry))` to the marker line
    - and re-verified on an irregular polygon.

  - **Bridgehead Line's end labels** - "the label on both ends should
    be straight, in our case one of the labels is inverted". Confirmed
    by render that with the marker line's own `rotateSymbols` flag on,
    a right-to-left line renders BOTH labels upside-down (and below the
    line, since the perpendicular offset rotates with the same frame),
    and an angled end segment tilts its own label. `_end_label_layer()`
    gained a `rotate_with_line=True` parameter (default preserves every
    existing caller unchanged) and Bridgehead Line passes False.
    Holding Line and Release Line share the identical bug; they were
    flagged rather than silently swept in, per the standing "one symbol
    at a time" convention, and the maintainer then confirmed the same
    treatment for both ("fix holding line and release line as well").
    With all three callers upright, the per-caller flag on
    `_simple_end_label_line_symbol()` was dropped again as redundant -
    the shared `_end_label_layer()` keeps its `rotate_with_line`
    parameter, since Light Line/FEBA and the other modules still use
    the rotating default.

  - **Housekeeping, same day**: removed genuinely dead code found by an
    AST sweep (three orphaned module-level constants -
    `_END_LABEL_CHARACTERS`, `_AIRBORNE_AVIATION_MEASURE_TYPES`,
    `_SIMPLE_LINE_END_LABELS` - and ~25 unused imports across the
    symbology and test modules); migrated 13 call sites off the
    deprecated `QgsTemplatedLineSymbolLayerBase.placement()` getter to
    `placements()`, which was already the established pattern in the
    other test modules; and gitignored `symbology-style.db`, an empty
    QGIS-generated local style database that had been sitting untracked
    in the repo root. One lesson worth recording from that sweep: a
    per-file "imported but not referenced here" check is NOT safe on
    its own - it flagged `LAND_RAMP`/`SEA_RAMP` in
    `terrain/tanaka_contours.py`, which are deliberate re-exports that
    `tests/test_tanaka_contours.py` imports from there. That removal
    broke the module's own test import and was caught by the full suite
    and restored; every other removal was then re-checked for the same
    re-export pattern before committing.

  - **Airhead Line's own label** - "the text is overlapping the line,
    it should be above the line". The shared `_build_pal_layer_
    settings()` had been forcing `OnLine` placement flags for every
    Line-placement label, which centres the text block vertically on
    the line. That IS the requirement for Boundary's own near/far
    designation pair and for every masked Field T label (which cuts its
    own gap in the line it sits on), but Airhead Line has no mask, so
    the line rendered straight through the glyphs. Added a
    `line_placement_flags` parameter (None by default, preserving
    `OnLine` for every existing caller) and passed `AboveLine |
    MapOrientation` for this one layer - MapOrientation included so the
    text still flips to stay readable on a right-to-left line rather
    than running upside-down. Same round, once the black-text-beside-a-
    blue-line mismatch was flagged: "change the colour as per
    affiliation for the airhead line also" - `_build_pal_layer_
    settings()` now data-defines every label's own Colour from
    `_AFFILIATION_COLOR_EXPRESSION`. Added first as an opt-in flag for
    Airhead Line alone; when the same black-label mismatch was flagged
    as affecting every other simple-labelling caller in this appendix,
    the maintainer's own instruction was "do it for all", so the flag
    was dropped again and the colouring made unconditional. Verified
    across all five affiliations and across every labelled layer
    (C2/Maneuver II/Airspace/Maritime/FSCM/Target/Target Acquisition).
    Direction of Attack's own per-rule colour still runs after this and
    overwrites the same property key, so Enemy's forced red keeps
    winning - confirmed by probe with `affiliation="friend"`.

    Same round, extending the long-standing enemy-red rule to its
    mirror image: "all friendly symbols must be blue and all enemy red,
    rest should depend on affiliation selection". A new
    `_FRIENDLY_MEASURE_TYPES` tuple forces blue for exactly the four
    measure types whose own NAME already commits them to a side (Axis
    of Advance - Friendly Airborne/Aviation, Direction of Attack -
    Friendly Aviation/Ground Axis), so a contradicting affiliation value
    can no longer override the name. Scope was deliberately checked
    with the maintainer rather than inferred, because three groups
    behave differently and a wrong guess silently miscolours real
    symbology: **Encirclement** (H-XII) and **Area** (H-VII) each FOLD
    the standard's own separate Friendly/Enemy codes into one measure
    type and use the affiliation field itself as the discriminator -
    forcing either colour would break that fold outright; and
    **Critical Friendly Zone**, **Enemy Prisoner of War Collection
    Point** and **Suppression of Enemy Air Defence** merely contain the
    words (a CFZ is a zone to protect, an EPW point is a friendly-run
    facility, SEAD is a friendly mission against enemy air defence) -
    none is an enemy symbol. All of those keep the dropdown. Verified
    by probe across all 6 forced types x 5 affiliations, plus a
    regression test that Main Attack (no side in its name) still
    follows the field.

- **2026-08-12, Table H-XII resumed - Attack By Fire Position (152000)
  built.** Deferred through all of Mini-Phase H6 for needing a shaft
  anchored to a COMPUTED midpoint rather than a digitized vertex; built
  now from the maintainer's own dictated Anchor Points/Size/Shape/
  Orientation rules. Three anchor points (PT1 = arrowhead tip, PT2/PT3 =
  the back line's own endpoints), with BOTH drawn pieces produced by
  geometry generators over that one 3-point line, since the rendered
  shape resembles the digitized path not at all:
  `mct_attack_by_fire_back()` for the back line plus a swept-back wing
  at each end, and `mct_attack_by_fire_shaft()` for the arrow, whose own
  last vertex the filled arrowhead rides so it inherits rotation for
  free.

  Both halves share one `_attack_by_fire_frame()` helper that derives
  its own normal direction from PT1 via a cross product, so the wings
  sweep away from PT1 and the arrow points towards it regardless of
  which side PT1 sits on or which order PT2/PT3 were digitized in -
  written that way deliberately after Encirclement's own winding bug
  the same day. Collinear input returns the digitized geometry
  untouched rather than inventing a direction.

  **The wings are not in the standard's own DRAW RULES text at all** -
  that text covers only the straight line and the midpoint connection -
  but both the TEMPLATE and EXAMPLE pictures clearly show them, so they
  were measured off the EXAMPLE by pixel analysis (length ~0.37x the
  PT2-PT3 distance, swept ~53 degrees back) and made proportional so
  they scale with whatever PT2/PT3 the user places. Flagged to the
  maintainer as measured-not-specified.

  **Same-round correction**: "the arrow is not perpendicular to the
  base, especially when PT2 and PT3 are not equidistant from PT1, make
  the arrow always perpendicular halfway between PT2 and PT3". The
  first version drew midpoint -> PT1 directly, which is only
  perpendicular when PT1 happens to sit over the midpoint. The arrow
  now always leaves the midpoint along the true normal, with PT1
  contributing only its own PERPENDICULAR DISTANCE (how far out, and
  which side) - the equidistant case is unchanged, so nothing already
  correct moved.

  744 tests passing on both QGIS versions.

- **2026-08-12, Support by Fire Position (152100) rebuilt as a two-click
  symbol.** The maintainer's own simplification of the standard's own
  four-anchor-point construction: "the user will click two points PT1
  and PT2 - they are equivalent to PT2 and PT3 of the attack by fire...
  now at the two vertex where the wings touch the horizontal line, make
  two arrows of same length as the wings... tilted slightly outward from
  perpendicular, say about 15deg". The standard places the two arrowhead
  tips as PT3/PT4; deriving them instead means they can never be placed
  inconsistently with the back line they spring from.

  Shares Attack By Fire Position's own back side via a new
  `_swept_back_line_geometry()` helper - the two symbols differ only in
  how they decide which way the wings sweep, so that decision is passed
  in rather than recomputed. Both arrows come back as one two-part
  MultiLineString with each part ordered base -> tip, so a single
  LastVertex marker line heads both and each picks up its own part's
  rotation.

  **One genuine ambiguity, flagged rather than guessed at**: with only
  two anchor points there is nothing in the geometry to say which side
  the firing position faces. Fixed by convention - arrows to the LEFT of
  PT1 -> PT2, wings sweeping right - which matches the standard's own
  EXAMPLE picture read left-to-right and lets the user orient the symbol
  simply by choosing which end to click first. Verified by render and by
  test that digitizing the other way flips the whole symbol.

  746 tests passing on both QGIS versions.

- **2026-08-12, Ambush (141700) built - Table H-XII complete.** The last
  outstanding entry, deferred through Mini-Phase H6 alongside Attack By
  Fire Position for the same computed-midpoint reason. Same three anchor
  points and the same "which side is PT1 on" frame, but the standard
  draws this one's back side as a CURVE ("Points 2 and 3 define the
  endpoints of the curved line on the back side of the symbol") - a
  circular arc bulging towards PT1, with comb teeth.

  **Corrected mid-build by the maintainer**: "the teeth behind the curve
  are all of equal length, also the distance between the arrow shaft end
  and the teeth is also equal". The first pass ran each tooth from the
  arc all the way down to the chord, making them longest in the middle
  and vanishing at PT2/PT3 - wrong. Every tooth is the SAME length, set
  back from the arc, so their tails trace a curve congruent to it, and
  the arrow's own tail sits on that same curve.

  Re-measured properly to settle it: a least-squares circle fit through
  the standard's own EXAMPLE picture (printed page 447) gives sagitta
  0.333 x chord and tooth 0.273 x chord, which predicts the arrow's tail
  at x=67.4 in that picture's own pixels against 67 measured. The first
  reading had put the apex ~20px too far out because the arrow overlaps
  the arc at exactly that row and contaminated the per-row maximum - a
  reminder that "rightmost ink in the row" is not the same as "the
  curve" wherever another element crosses it.

  Worth recording: this places the arrow's tail slightly SHORT of the
  chord midpoint (0.27 back from the apex where the chord is 0.33), so
  the standard's own drawing and its own prose ("the rear of the arrow
  should connect to the midpoint of the line between points 2 and 3")
  disagree here by ~6% of the chord. The maintainer chose the drawing.

  748 tests passing on both QGIS versions.

- **2026-08-12, Search Area/Reconnaissance Area (152200) rebuilt.** The
  last unreviewed entry in this table. It had been drawing the
  digitized path as-is - two plain straight arrows - with the module's
  own docstring openly recording that "the standard's own
  double-notched arrow shaft decoration is not reproduced". It is now.

  Three anchor points in the order this measure type already expected
  and the maintainer re-confirmed: **PT2 first, PT1 second, PT3 third**,
  PT1 being the middle vertex both arms spring from. Each arm runs
  PT1 -> outer barb corner -> back in towards the axis -> tip, which
  gives the standard's own barbed/fletched look. The shape constants
  were measured by projecting the template's own vertices onto each
  arm's axis (outer corner 0.554 along / 0.131 out; step back 0.481
  along / 0.035 inside), rounded to 0.55/0.13/0.48/0.035.

  They are fractions of EACH ARM's own length, computed independently -
  which is what the standard requires ("the length and orientation of
  the arrows can vary independently", and the maintainer's own
  reminder), so a short arm and a long one are each correctly
  proportioned rather than sharing one absolute offset. Covered by a
  test using arms differing 5x in length.

  Returned as a two-part MultiLineString each ordered PT1 -> tip, so a
  single LastVertex marker heads both arms OUTWARD; drawn as one
  PT2 -> PT1 -> PT3 path instead, the head at FirstVertex would point
  back inwards.

  **The placeholder "A" at the vertex was removed** rather than kept or
  improved. The standard wants "the tactical symbol indicator...
  centered over point 1" - a real unit symbol, as its own EXAMPLE shows
  - and the bare letter was standing in for one. The maintainer's own
  call: "remove the text 'A', it is supposed to be a military symbol,
  user can add separately". A wrong glyph is worse than none, and this
  plugin's own point layers can already place a real unit symbol over
  the vertex.

  One process note: the first attempt at this edit spliced from the
  target function all the way to the next module-level constant, which
  silently deleted `_simple_end_label_line_symbol()` and
  `_airhead_line_symbol()` along with it. Caught immediately by an
  ImportError on the very next render, restored from HEAD, and verified
  by diffing the file's own function list against HEAD before
  continuing - a reminder to bound a splice by the next `def`, not by
  the next thing that happens to look like a boundary.

  749 tests passing on both QGIS versions. **Table H-XII is now
  complete** - all ten entries built and reviewed.

- **2026-08-12, Table H-XIII (Airspace control means) reviewed
  end-to-end.** The maintainer's own live testing produced a list of
  six defects across the whole table; all six are fixed. Recorded here
  in one entry rather than six because the first two commits
  (`93b4f77`, `dc4f49c`) went in without a roadmap entry at all - a
  lapse against this project's own per-round convention, caught and
  filled in when the third landed.

  - **Air Corridor and the whole corridor/route family (AC, LLTR, MRR,
    SL, SAAFR, TC, UA Route) rebuilt as two parallel lines** with the
    designation label riding BETWEEN them, instead of the single thick
    line they had been. The maintainer's own words: "it is two parallel
    lines with the unique designation within the parallel lines, in
    case of multiple line segments the AC+unique_designator should be
    in all segments if it fits". Two `QgsSimpleLineSymbolLayer` at
    `setOffset(±2.0)` mm, and the label given a 45 mm repeat distance
    so a multi-segment route carries its own name wherever it fits
    rather than only once at the centre.

  - **Zone labels (HIDACZ, ROZ, AARROZ, UA-ROZ, WEZ/FEZ/JEZ/MEZ/LOMEZ/
    HIMEZ/SHORADEZ, WFZ) moved to the polygon's own top-left corner,
    inside it.** The label CONTENT was already correct - the
    maintainer's own correction mid-round ("the zones names and unique
    identifier are rendered correctly, they just need to be on to top
    left corner of polygon, within it") narrowed this from a
    content bug to a placement one. Needed a new expression function,
    `mct_area_label_anchor()`, because a bounding-box corner can fall
    outside a concave polygon entirely: it clips to the top band, then
    to the left of that band, and returns `pointOnSurface()`, falling
    back a step at a time if either clip comes up empty. `AboveRight`
    was tried first and straddled the top edge; `BelowRight` hangs the
    text down-and-right INTO the shape, which is what was wanted.

  - **IFF Off/On Line labels no longer render upside-down** depending
    on which direction the line was digitized - the same
    `rotate_with_line=False` fix already applied to the boundary-line
    family.

  - **Weapons Free Zone**: hatch spacing tightened 30% (2.5 -> 1.75 mm)
    and the label given a `QgsTextMaskSettings` mask so it stays
    readable over the fill.

  - **Base Defense Zone (170800) built**, having been skipped when this
    mini-phase was first written because its own template is a
    fixed-size ("Static") circle around ONE anchor point - fitting
    neither milsymbol's vocabulary nor the Areas layer's freeform-
    polygon model. Built as a TWO-point circle instead (centre, then
    radius) on the maintainer's own explicit instruction: "make it a
    two point circle, one for the center and other for radius". **This
    deliberately departs from the standard's own one-anchor/Static
    rule** in exchange for a sizable zone; the departure is recorded in
    the module docstring, the function docstring, the test, and the
    commit message, not just here. It lives on the LINES layer because
    its own geometry is a 2-point line.

  - **All 26 point entries (180000-182500) moved to their own
    "Airspace Control Measures (Points)" layer**, out of the shared
    `control_measure_points.py` one - "all symbols related to points, I
    think they are in control measure points, need to be relocated".
    Same per-table convention Table H-VI, Table H-IX and Table H-XI's
    Point of Departure already follow. sidc.py's own entities are
    untouched by the move, so anything already digitized keeps
    rendering. Three findings, all from probe renders rather than
    assumption:

    - **180000, the table's own generic "Airspace Control Points"
      parent entry, was missing from `sidc.py` entirely** - a gap in
      the original H7 pass, not something the move introduced. Present
      in milsymbol as `TP.AIR CONTROL POINT`, confusingly close to
      180100's own `TP.AIR CONTROL POINT (ACP)` but a genuinely
      different icon (bars + centre dot vs. circle + "ACP"). Added, and
      the vocabulary is now pinned by a test that checks the codes form
      the unbroken 180000-182500 sequence the table itself lists,
      rather than checking the dict against itself.
    - **Only 3 of the 26 take a unique designation at all** - ACP
      (180100) and CCP (180200) place it inside the circle under their
      own text, TACAN (180600) outside at top right. All three use
      milsymbol's plain `uniqueDesignation`, so this layer needs no
      per-entity slot lookup of the kind `c2_measures.py` had to build.
      The other 23 define no text slot whatsoever - which matches the
      standard, whose templates show a Field T box on exactly those
      same three.
    - **Downed Aircrew Pick-Up Point (180300) anchors at its own
      bottom**, not its centre ("The point defines the tip of the
      inverted cone"); its rendered viewBox is identical to Point of
      Departure's, already anchored `bottom` for the same reason.
      Every other entry is a "Center Point".

  **Two further defects found, reported, and adjudicated** - both are
  the same underlying QGIS/milsymbol interaction (QGIS reads an SVG
  marker's size as its WIDTH, so a wider viewBox at a fixed mm size
  draws a smaller symbol), and fixing either means choosing a size
  multiplier, which on this project is the maintainer's call. Both were
  reported with measurements rather than fixed unilaterally:

  - **Pop-Up Point (180400) rendered at roughly half its siblings'
    scale.** Its "PUP" text sits OUTSIDE the circle, so milsymbol's
    viewBox is 198x108 where the bars family's is 88x148. Static, so a
    fixed multiplier fixes it. Matching PUP's own circle to Air Control
    Point's exactly would have wanted 1.83x; the maintainer's own call
    was "pop up point can be doubled in size", so it uses 2.0.

    **The other half of the same finding - the click landing beside
    the circle rather than on it - was then fixed too**, on the
    maintainer's follow-up ("can you fix the pop up point so that the
    point of click is the center of the circle?"). Because that "PUP"
    text hangs off to the RIGHT, milsymbol draws the circle at x=100
    inside a 46..244 viewBox whose own midpoint is x=145, and QGIS
    centres a marker on its VIEWBOX - so the click sat in the white
    space between circle and text. The standard anchors the circle
    ("The center point defines the center of the symbol"), and QGIS's
    own horizontal-anchor options are left/center/right only, none of
    which lands on x=100, so this takes an explicit offset instead:
    shift right by those same 45 units, expressed as a FRACTION of the
    icon's own width so it tracks the size multiplier rather than going
    stale if that ever changes. Measured before and after by probe
    render at 300 DPI - the circle sat 43.5 px left of the anchor
    before (3.68 mm, against the 3.64 mm the fraction predicts, agreeing
    within the ~1 px uncertainty of locating the circle's crown row),
    and 0.5 px after, that half being the pixel-centre convention.
  - **TACAN (180600) shrinks whenever a designation is typed** - bare
    it is 88x148, with "629" it is 164.5x148, i.e. 53% scale. Because
    the width depends on how many characters the user types, no static
    multiplier can fix this one; it would need a length-driven size
    expression. Maintainer's own call: "tacan is fine". Left as-is
    deliberately, not overlooked.

  A related latent bug was found and fixed in passing: **the Weapons
  Free Zone hatch was rendering black** while its outline was correctly
  affiliation-coloured. `_apply_affiliation_color()` was being called
  on the fill layer, but a `QgsLinePatternFillSymbolLayer` paints
  through its own SUB-SYMBOL, so a data-defined colour set on the fill
  layer itself is silently ignored. The intent was always there; it
  just never reached the layer that paints. Verified across all four
  affiliations.

  One process note: the first version of the WFZ mask test chained
  `layer.labeling().settings().format().mask()` and segfaulted the
  interpreter outright. `format()` and `settings()` return by VALUE, so
  chaining lets the temporary's C++ object be collected mid-expression
  - a trap `test_offensive_control_measures.py` already documents, and
  which this walked straight back into. Each intermediate is now held
  in its own variable, with a comment saying so.

  768 tests passing on both QGIS versions. **Table H-XIII is now
  complete** - lines, areas and points all built and reviewed.

- **2026-08-12, Table H-XIV (Maritime control measures) reviewed.** The
  maintainer's own live testing: "all the lines are rendered fine, just
  three issues" - all three on the Bearing Line family's own labelling,
  none on its geometry. Fixing them meant this module stops calling the
  shared _configure_designation_labeling() and builds its own
  QgsRuleBasedLabeling tree instead, because there are now two
  separately-placed labels per feature rather than one.

  - **The abbreviation (B/E/EW/A/T/O/J/RDF) is upright at all times**,
    not rotated to follow the line. Qgis.LabelPlacement.Line rotates
    its label with the feature, so a bearing digitized right-to-left or
    steeply descending rendered its own letter upside-down;
    .Horizontal is QGIS's own "place along the line, keep the text
    level" mode. Confirmed by rendering deliberately awkward bearings
    (right-to-left, steep descent, pure horizontal) rather than only
    the tidy up-and-right case the template happens to draw.

    This also extended _build_pal_layer_settings()'s own line-settings
    block to fire for .Horizontal as well as .Line - additive, since
    Horizontal honours exactly the same lineSettings() (anchor,
    placement flags) and no existing caller uses it.

  - **It masks the line**, so the line no longer draws through the
    glyph. Both symbol builders needed a stable `.setId()` for this -
    masking is configured layer-wide against a LIST of ids, so the
    always-dashed Acoustic (Ambiguous) variant would otherwise have
    kept drawing through its own "A".

  - **A "unique_designation" free-text field was added**, labelled at
    the line's own END, below-right, also upright (OverPoint placement
    against `end_point($geometry)` with the BelowRight quadrant). This
    is the identifier the template shows in a box near the PT2 end -
    "MSL"/"MCU"/"TENT" for Electronic Warfare, "L3-ACT" for Acoustic,
    "PAT-1" for Jammer. It had been dropped when this mini-phase was
    first built, under the same "extra descriptive field box" tolerance
    as H7's own WIDTH/altitude/DTG fields, on the reasoning that it
    would need a different fixed vocabulary per sub-type; one shared
    free-text field sidesteps that entirely. **Note this deliberately
    departs from the template, which puts the box just ABOVE the end
    point** - below-right is the maintainer's own explicit call.

    The rule is filtered to non-empty designations. Without that filter
    the rule still runs for blank features and QGIS reserves the empty
    label's own space, which collides with the abbreviation's own
    placement search on short lines.

  Both rules are given the SAME masked-id list even though only the
  abbreviation sits on a line, because masking is per QGIS layer rather
  than per rule - rules declaring different lists make QGIS log
  "Different sets of symbol layers are masked by different sources!
  Only one (arbitrary) set will be retained!" and silently keep one.
  That was already learned on H-XIII's own zone labels; applying it
  here up front rather than rediscovering it.

  771 tests passing on both QGIS versions.

- **2026-08-12, Table H-XIV's point vocabulary moved and expanded to
  the full 105 entries.** Two decisions here were the maintainer's, not
  this pass's, and both reversed earlier calls - so they were put to
  them explicitly, with the tradeoffs stated, rather than assumed.

  **Scope: the sonar/sonobuoy curation was reversed.** This table's
  points started as an 18-entry curated subset on the shared
  control_measure_points.py layer, with the Sonobuoy (17 entries) and
  anti-submarine-warfare fix/contact (17) families deliberately left
  out as "more Navy/ASW-specific" - a standing decision this project's
  own docstrings recorded in three places. The maintainer went through
  printed pages 474-501 directly and asked for the lot; that is now
  built. sidc.py's own entities are untouched by the move, so anything
  already digitized keeps rendering.

  **Grouping: a label prefix plus a derived field, NOT a cascading
  dropdown.** 105 entries in one flat list is unusable - "can we make
  them into sub menu, otherwise the list is too long". QGIS's attribute
  form has no nested dropdown, and the only mechanism that genuinely
  filters one field by another is the ValueRelation cascade **this
  project already retired from unit_layer.py after a confirmed
  native-crash risk** - the same cascade sidc.py's own
  ENTITIES["subsurface"] comment names as the likely root cause of the
  Subsurface bug that prompted splitting per-appendix layers in the
  first place. Rather than quietly re-adding a known hazard for a nicer
  menu, both options were put to the maintainer with that tradeoff
  stated; they chose the prefix. So each label reads "Routes - General
  Route", which clusters the dropdown by group and answers to
  type-ahead, and a real "group" FIELD is auto-derived from the chosen
  entity (applyOnUpdate, so it re-derives on change) for filtering and
  styling. The group is never typed - it is a property OF the entity,
  and an editable copy could only ever disagree with the symbol drawn.

  Groups are the table's OWN sub-headings, in its own order: General,
  Sub-Surface Warfare, Search, Sonobuoys, Reference Points, Subsurface
  Stations, Surface Stations, Routes, Emergency, Hazard, Sea Subsurface
  Returns. "General" is this module's name for the table's first,
  unheaded block (210100-211100). **"Hazard" was nearly missed** - the
  PDF's own text layer renders that heading as "Har.ard", so the
  heading scan skipped it and its three entries would have been filed
  under Emergency; caught by rendering the page as an image instead of
  trusting the extracted text, which is exactly the failure mode this
  project's own methodology already warns about.

  **Five codes in the 474-501 range are deliberately not built**, each
  for a different reason, all recorded in the module docstring, sidc.py
  and a test rather than left as silent gaps:

  - **210000** is the table's own parent row - template column reads
    "N/A". Nothing to draw; milsymbol has no icon for it either.
  - **211000/211200/211300** are each marked "(AEGIS only)" in their
    own CONTROL MEASURE cell. The maintainer's instruction on this pass
    was to ignore AEGIS.
  - **217300 (PIM Route)** is broken in milsymbol itself: its source
    maps the code to `icn["TP.ROUTE POINT R"]` - the SAME icon as
    217500, Point R Route - under a literal `##### FIX TODO #######`
    comment. Shipping it would silently draw the wrong symbol, which
    this project treats as worse than drawing none (the same call
    already made for Search Area's placeholder glyph).
  - **218400 (Navigational)** is not a point at all - its own draw
    rules say "requires two anchor points... define the corner points
    of the symbol", a two-vertex hooked line, which is why milsymbol
    has no point icon for it. It belongs on the Lines layer as a
    hand-built construction. **Still outstanding.**

  Names were taken from milsymbol's own per-code source comments rather
  than the PDF's text layer, which is badly mangled here ("Mal'itime
  Contl'OI Points", "Beal'ing Line"). Cross-checked against the page
  images for the entries where the two disagreed. Every one of the 105
  was then rendered through the real pipeline and confirmed to produce
  a symbol, with the codes checked unique - worth doing exhaustively
  rather than by sample, since most of these had never been rendered
  before this expansion.

  780 tests passing on both QGIS versions.

- **2026-08-12, Table H-XVI (Fire Support Coordination Measures) lines
  reviewed.** Four points from the maintainer's own live testing, all
  on labelling. Every one is confirmed against the table's own template
  pictures (printed pages 521-523) as well as the report.

  - **Every line label now carries the feature's unique designation**,
    and WHERE it goes is per-type, read off each template rather than
    assumed uniform: FSCL draws "[T] FSCL" with the designation FIRST
    (its own example, "MND(S) FSCL"), while NFL/BCL/RFL/CFL all draw
    "NFL [T]" with it LAST ("NFL II CORPS", "BCL III MEF", "CFL 52ID
    (M)"). MFP has no Field T box at all. Getting prefix and suffix
    backwards is invisible until someone reads the map, so each is
    pinned by its own test.

    A blank designation collapses to the bare abbreviation via trim() -
    without it "NFL " keeps a trailing space and the mask cuts a hole in
    the line for it.

  - **FSCL/NFL/BCL/RFL label BOTH ENDS, above the line and inboard.**
    This is what forced the rework: they had been a pair of fixed-
    character font markers via _end_label_layer(), and **a marker's
    character is set when the symbol is built and cannot read the
    feature's own fields** - so there was nowhere for a per-feature
    designation to come from. They are two real PAL rules now, anchored
    on `start_point($geometry)` and `end_point($geometry)`.

    AboveRight at the start and AboveLeft at the end, not a plain Above
    at both: Above centres the text ON the end vertex, which left half
    of "MND(S) FSCL" hanging off past the end of the line entirely
    (caught by render, not by reading the code).

  - **CFL labels once above the centre** - its own draw rules say "the
    line information will be posted once at the center of the line", and
    the maintainer asked for above specifically. Line placement with the
    AboveLine flag.

  - **MFP was already placed correctly and only needed the mask**, so it
    keeps the OnLine default its own template draws.

  All four rules mask the line, and all four declare the SAME masked-id
  list - masking is per QGIS layer, not per rule, so differing lists
  make QGIS keep one arbitrarily and log a warning. All three line
  symbol builders needed a stable setId() for this.

  The layer moved from QgsVectorLayerSimpleLabeling to
  QgsRuleBasedLabeling, since the six types no longer share one
  placement.

  784 tests passing on both QGIS versions.

- **2026-08-12, Table H-XVI areas.** Two changes, both from the
  maintainer's own live testing, plus one latent bug found on the way.

  - **No Fire Area's label masks its hatch**, so the text stays
    readable against the diagonal fill. The same treatment H7's own
    Weapons Free Zone already had - NFA is the only other area in this
    whole appendix pass with a real fill.
  - **Position Area For Artillery labels all FOUR sides of its own
    perimeter** - "the text PAA should be in all four directions - top,
    bottom, right and left along the perimeter of the area made" -
    rather than once in the middle like every other area in the table.
    Straight off its own template (page 521, the Circular variant),
    which draws each "PAA" sitting ON the outline with the line broken
    around it; so the labels use the Over quadrant and the PAA outline
    is masked too.

    Each anchor is a bounding-box edge midpoint. That is EXACT for both
    shapes the standard actually allows here - PAA is Rectangle or
    Circular only, with no Irregular variant in its own table - so none
    of the boundary-clipping machinery mct_area_label_anchor() needs for
    H7's freeform zones applies. Bounding box rather than centroid(),
    which would wander off the two axes on a rotated rectangle.

    The centred rule needed an explicit non-PAA filter rather than
    setIsElse(True): an else-flagged rule's own sub-provider still
    places its label for rows the other rules matched, which would have
    given every PAA a fifth label in the middle. Already established in
    c2_measures.py's own area labelling and reused here rather than
    rediscovered.

  Both changes needed the areas layer to move from
  QgsVectorLayerSimpleLabeling to QgsRuleBasedLabeling, since the five
  types no longer share one placement, and all five rules declare the
  same masked-id list (masking is per QGIS layer, not per rule).

  **Latent bug fixed on sight**: No Fire Area's hatch was rendering
  black beside its own correctly affiliation-coloured outline, because
  a QgsLinePatternFillSymbolLayer paints through a SUB-SYMBOL and a
  data-defined StrokeColor set on the fill layer itself is silently
  ignored. This is the identical bug found in H7's Weapons Free Zone
  earlier the same day - the same wrong pattern had been copied into
  both. Fixed here without waiting for it to be reported a second time,
  and pinned by a test across all four affiliations.

  787 tests passing on both QGIS versions.

- **2026-08-12, Table H-XVII (Targets).** Points relocated, plus three
  line-label fixes and one area-label fix from the maintainer's own
  live testing. All confirmed against the table's own templates
  (printed pages 525-536), not just the report.

  - **The nine point entries moved to their own POINTS layer**, the
    same per-table convention every other H.5.x group now follows.
    sidc.py's entities are untouched.

    **"Fire support station symbol is missing, 240900" turned out not
    to be missing.** The entity, its code and its rendering were all
    already correct - verified by probe before changing anything. Two
    things made it easy to overlook, and both are now fixed: it was one
    line in a flat ~44-entry shared dropdown, and its own "FSS" text
    sits OUTSIDE the X glyph, widening milsymbol's viewBox to 158
    against its siblings' 108. QGIS reads a marker's size as its WIDTH,
    so the X drew at about two-thirds their scale, and the X's own
    centre (x=100, measured off the rendered path) sat 25 viewBox units
    left of the point QGIS anchors on. Both corrected - the identical
    asymmetry as H7's Pop-Up Point, measured the same way rather than
    assumed from the earlier case.

  - **Linear Target's designation moved ABOVE the line.** Its label is
    a single line, and the shared OnLine default centres a single line
    ON the line, striking it through.

  - **A blank designation now stays a blank LINE** on Linear Smoke
    Target and Final Protective Fire. Both draw a two-line label that
    straddles the line - designation above, "SMOKE"/"FPF" below - which
    is exactly what OnLine gives on a two-line label. Drop the empty
    first line and the label collapses to ONE line, which OnLine then
    centres on the line and strikes through: the maintainer's own
    report, and their own suggested fix ("maybe default to a ' ' fixed
    blank space?"), which is what this does via
    nullif(...,'')/coalesce.

  - **Final Protective Fire gained a unique designation**, which it had
    never had - it was a bare fixed "FPF". Same terms as Smoke, per the
    maintainer, and confirmed by its own example ("QC1968" above the
    line, "FPF" below).

  - **Series or Group of Targets labels ON its own boundary**, at the
    top, with the outline masked - "the unique designator should be on
    the perimeter with suitable mask so that line does not overlap the
    text", and what all four of its own examples draw. It is the only
    area in this table whose label isn't centred inside the shape.

    **The default mask buffer was not enough.** QGIS's text mask is
    GLYPH-shaped, not a box, so at the 1.2mm default the boundary line
    still showed through the enclosed counter of a round letter - an
    "OWL" label had the line visible inside its own "O". Caught by
    render (the mask looked correct everywhere else); widened to 2.4mm,
    which closes those counters. Worth remembering for any future label
    masked against a line it sits directly on.

  Both layers moved from QgsVectorLayerSimpleLabeling to
  QgsRuleBasedLabeling, since their measure types no longer share one
  placement.

  797 tests passing on both QGIS versions.

- **2026-08-12, Table H-XVIII (Target acquisition).** One missing
  measure type built, one pair explicitly deferred.

  - **Terminally Guided Munition Footprint (242000, "TGMF") was missed
    entirely** when this mini-phase was first built - not curated out
    and recorded the way the two Weapon/Sensor Range Fans were, just
    absent, with nothing in the module docstring acknowledging it.
    Added on the maintainer's own report. Its construction is the same
    freeform outline + centred prefix as every other entry here, so it
    needed no new technique - which is what makes the omission worth
    noting rather than shrugging at.

    **Why it slipped, and what stops the next one.** Every other entry
    in this table is an Irregular/Rectangle/Circular code TRIPLE folded
    into one measure type; TGMF is a lone code. A pass reading the
    table in triples had nothing to catch on. The test guarding this
    was a bare `len(AREA_MEASURE_TYPE_LABELS) == 11`, which agreed with
    itself and stayed green - a count can only ever confirm what was
    already built. Replaced with an explicit set assertion against the
    standard's own code list, so an absent measure type now fails by
    name. Worth applying the same reading to other tables' guards.

    Its own template shows no Field T box, unlike its siblings; the
    optional name is still offered for uniformity with the rest of the
    layer, and simply stays unused if left blank.

  - **Weapon/Sensor Range Fan - Circular (242100) and Sector (242200)
    remain unbuilt, now tracked as work rather than as a curation
    decision** (task #38). Both need genuinely computed geometry from a
    single anchor point - concentric range rings, or a pie sector with
    an azimuth centreline and left/right limits - not a boundary the
    user digitizes. The likely approach is a geometry generator in the
    style of H7's own Base Defense Zone (centre + radius click into
    make_circle), extended to arcs and sectors; the open design
    question, to settle with the maintainer before building, is whether
    ranges and azimuths come from attribute fields or from extra
    clicked points. Pinned by an assertNotIn so the deferral stays
    visible rather than reading as an oversight.

  798 tests passing on both QGIS versions.

- **2026-08-12, Table H-XIX (Obstacles) batch B0 - audit only.** The
  largest table in this appendix pass (75 code rows, printed pages
  573-603), so it is being built in batches (tasks #39-#46). B0 builds
  no symbols: it produces the inventory every later batch reads from,
  as checkable data in obstacle_control_measures.py's own
  TABLE_H_XIX_INVENTORY rather than as prose.

  **Starting assumptions that turned out wrong**, all caught by reading
  template pictures rather than the PDF's text layer (which is badly
  OCR-mangled here - "Obstacle Fl'ee Zone", "Une Cluste1·"):

  - **Obstacles are not in c2_measures.py at all.** Six point entries
    sit on the shared control_measure_points.py layer; every line and
    area in the table is unbuilt, and there was no obstacle module.
  - **The table ends at printed 603, not 602.** An early boundary scan
    said 602 because the regex matched "H-XIX" as "H-XX"; the
    maintainer's own 573-603 was right, and 603 carries Raft Site
    (290800), the last row.
  - **Most of the minefield family are POINTS, not areas** - 270701-
    270705 each say "requires one anchor point... Size/Shape: Static".
    Only 270706/270707 are freeform areas. B3 was rescoped.
  - **The obstacle zones are not a plain outline** - Obstacle Belt/
    Zone/Free Zone/Restricted Zone all draw a SERRATED boundary, and
    Restricted adds a hatch on top. Mined Area and its decoy variants
    repeat "M" glyphs around the perimeter rather than carrying a
    centred label. B2 was rescoped; neither can reuse
    _status_driven_area_outline_symbol() unchanged.
  - **Overhead Wire (282003) is a LINE despite its 28xxxx code**, the
    single exception to the table's own Points/Lines prefix split.
    Moved from B1 to B7.
  - **The PDF text layer misnames 271500.** It renders as "~~ry",
    reading as Ferry; it is Ford Easy. Ferry is 290700, a different
    symbol on a different page. Pinned by a test.

  **Two rules that govern every later batch:**

  - **The code prefix does not identify the table.** 28xxxx/29xxxx are
    shared with H-XX (shelters, fort) and H-XXI (CBRN events).
    Anything scoped by prefix rather than page range silently pulls two
    other tables in - pinned by a test naming each intruder.
  - **Obstacles draw GREEN, not in the affiliation hue** - the
    maintainer's own note, and directly visible in the table's EXAMPLE
    column. A documented departure from H.5.3 and from every other
    H.5.x group here, so it gets its own _apply_obstacle_color() rather
    than quietly reusing _apply_affiliation_color(). The green is a
    default the caller can override, because the maintainer has flagged
    exceptions to be named per batch. B1 is where this first collides
    with the rendering pipeline: its points come through milsymbol,
    which owns their colour.

  The inventory is verified against the standard both ways - the test's
  expected code list is written out literally rather than derived from
  the inventory under test, so it checks the inventory AGAINST the
  table rather than against itself. That is the failure mode that let
  H-XVIII's Terminally Guided Munition Footprint hide behind a
  self-agreeing `len(...) == 11` the day before.

  No layers and no plugin menu entry yet - deliberately, rather than
  shipping three empty layers into the UI. They arrive with B1, the
  first batch with symbols to place.

  804 tests passing on both QGIS versions.

- **2026-08-12, Table H-XIX B0 reconciled against the maintainer's own
  independent audit.** They audited the table in parallel; the two
  passes were compared entry by entry.

  **Both arrived at the same 65 buildable entries from 75 code rows** -
  no additions, no omissions either way. That agreement, reached
  independently, is the strongest evidence either inventory is
  complete.

  **Two corrections went against B0**, both confirmed against the
  templates before accepting:

  - **Abatis (280100) is a LINE, not a point.** Its own draw rules say
    "requires at least two anchor points... to define the line", and it
    draws as a toothed line. B0 classified it from the "Protection
    Points" heading above it - which is precisely the trap B0's own
    docstring warns about, walked into on the same page it was written.
    Moved from B1 to B4.
  - **290400 is "Mine Cluster", not "Line Cluster".** B0 took the name
    from the PDF's mangled "Une Cluste1" and resolved it to "Line". A
    name read from OCR rather than from a picture - the same class of
    error as 271500/"Ford Easy", which B0 did catch.

  **The audit also supplied per-entry colour and Field T requirements**,
  now carried in the inventory and pinned by tests. Eight entries draw
  black rather than green (the three Obstacle Bypass variants, Bridge
  or Gap, UXO Area, Antitank Ditch Reinforced, Antitank Wall, Lane);
  five draw a green outline with black text (the four obstacle zones
  and Obstacle Line); everything else defaults to green. Nine entries
  require Field T.

  **A new architectural requirement**: the user must be able to switch
  any obstacle to black. That makes colour a per-FEATURE choice, not a
  per-measure-type constant, so the layers need a colour field
  defaulting to each type's own value - settled before B1 builds the
  first layer.

  **The minefield family is specified beyond the standard.** The audit
  calls for a mine-type choice per minefield (antipersonnel/antitank/
  unspecified/combination, alternating when combined), Completed
  Minefield accepting either a symbol or a digitized line closed into a
  filled rectangle, Planned folding in as a dashed variant, Known Enemy
  adding masked "ENY" at its edges, and the two dynamic entries merging
  into one area with randomly scattered mines. None of that is in
  MIL-STD-2525D - it is a deliberate extension, recorded as such, and
  B3 owns it.

  **Three open questions recorded rather than guessed**, in the module
  docstring: whether Mine Cluster (290400) and Trip Wire (290500) are
  meant as single-click symbols despite their templates requiring two
  and three anchor points; four code typos in the audit read as
  intended rather than literally (270501, 280300, 271000, 270704); and
  the reading of "OT" as outline-green/text-black.

  806 tests passing on both QGIS versions.

- **2026-08-12, AEGIS-only sweep across the whole of Appendix H.** The
  project's standing rule is that it ships no AEGIS-only symbols -
  naval combat-system display constructs rather than general-purpose
  military symbology. That rule had been applied per-table as each
  mini-phase was built, and applying it table by table is exactly how
  two got through.

  Prompted by the maintainer spotting "Target - Recorded (AEGIS Only)"
  in the H-XVII points dropdown. Swept every "(AEGIS only)" marking in
  the appendix rather than removing just the one reported.

  **Seventeen AEGIS-only codes exist in Appendix H. Two were shipped:**

  - **Airfield (131900, Table H-VI)** - its own CONTROL MEASURE cell
    reads "Airfield (AEGIS Only)". Shipped since H2, and it even
    carried a +20% size multiplier from the maintainer's own live
    testing, so it had been looked at more than once without the
    marking being noticed. **Not to be confused with Airfield Zone**
    (Table H-V), a different, non-AEGIS AREA that stays.
  - **Target-Recorded (240603, Table H-XVII)** - kept deliberately on
    its first pass, with the recorded reasoning that it "renders a
    real, correct icon from its own template rather than an AEGIS
    display construct this project has no model for". That reasoning
    was a per-symbol judgement standing against a per-project rule; the
    rule wins.

  **One near-miss worth recording.** The first pass of this sweep
  grepped sidc.py for the AEGIS code list and reported SIX hits -
  including cbrn_equipment, computer_system, command_launch_equipment
  and generator_set at 200400-200700. All four were false positives:
  **SIDC codes are only unique WITHIN a symbol set**, and those four
  are Land Equipment, not control measures. Re-scoped to
  ENTITIES["control_measure"] the real count is two. Deleting on the
  first result would have removed four correct entries.

  The rule now lives in one test (test_military_symbology_sidc.py's own
  TestNoAegisOnlySymbols) carrying all seventeen codes, rather than
  being re-argued per table. Both removals are also pinned by their own
  modules' tests.

  806 tests passing on both QGIS versions.

- **2026-08-12, Table H-XIX batch B1 - protection points.** The first
  obstacle symbols, and the first layer in the module B0 scaffolded.
  13 point entries: the mine family and its variants, Booby Trap,
  Engineer Regulating Point, Tetrahedrons/Dragons Teeth, and the two
  Towers. Eight codes were new to sidc.py.

  **The colour question B0 flagged as blocking answered itself.**
  Obstacles draw green, but the points come through milsymbol, which
  owns their colour and applies H.5.3's affiliation rule - so the
  points looked set to be the one part of this table stuck on the wrong
  colouring. milsymbol's own `monoColor` option turns out to recolour
  the whole icon, stroke and fill, confirmed by probe. So
  mct_sidc_svg() gained an optional FOURTH argument (additive, default
  off, no existing caller affected) and the points follow exactly the
  same per-feature green/black choice as the hand-built lines and areas
  will. No decision needed after all.

  **Colour is a per-FEATURE field**, per the maintainer: "user should
  have the ability to change colour to black if he wants to". The
  layer's own Colour dropdown defaults to green and drives both the
  icon and its label.

  **A real gap between the audit and milsymbol**: both Towers REQUIRE a
  unique designation, and milsymbol has no text slot for either icon -
  probed all six of its text options against both codes, none accepted,
  and neither rendered SVG has a <text> element to hang one on. Unlike
  every other Points layer in this pass, the designation needs a real
  PAL label beside the icon. Engineer Regulating Point also requires
  one but DOES accept `uniqueDesignation`, so it keeps the in-icon
  route and is excluded from that label - otherwise it would show its
  designation twice.

  Two render-caught mistakes on that label, neither visible in code:
  it came out BLUE, because _build_pal_layer_settings() colours every
  label by affiliation (made unconditional in H-XII when the
  instruction was "do it for all") - obstacles are the first group
  where that is wrong, overridden after the fact rather than by adding
  another flag to the shared helper. And it sat on top of the glyph:
  `dist` is the radius for AroundPoint placement and is ignored by
  OverPoint, so pushing the text clear needs `xOffset`.

  **Abatis stays on the shared Control Measure Points layer for now**,
  deliberately. It is a line, not a point, so it belongs to B4 - but
  removing it here before B4 builds it would make it vanish from every
  dropdown in between.

  816 tests passing on both QGIS versions.

- **2026-08-12, H-XIX open question 1 settled: Mine Cluster (290400)
  and Trip Wire (290500) are LINES.** The maintainer's audit had listed
  both as "symbol/point"; their own templates require two and three
  anchor points respectively, and the maintainer confirmed lines. Both
  were already held that way in the inventory, so this changes no code
  - it moves the entry from "open question, do not guess" to settled,
  and pins it by test so B4 cannot drift back.

  **Trip Wire is flagged as the awkward one.** Its three anchor points
  give a vertical straight portion (PT1-PT2), a horizontal extent
  (PT3), AND a 90 degree arc at the bottom whose radius is the distance
  from the PT1-PT2 line to PT3. The maintainer's own note: "slightly
  complex, we will figure it out when it comes to that". B4 should
  budget for it separately rather than assuming it drops into that
  batch's shared marker-line helper.

  Two of the three open questions from the audit reconciliation remain
  (the four code typos read as intended, and the reading of "OT"), both
  low-risk and recorded in the module docstring.

    739 tests passing on both QGIS versions.

- **H-XIX B1 follow-up: every obstacle point rendered as "unknown"**
  (2026-08-12) - caught by the maintainer's own live smoke test
  immediately after B1 landed, and NOT caught by a green 821-test
  suite. Worth recording in full, because the way it hid is more
  reusable than the one-line fix.

  **The bug.** The new Points layer configured its `affiliation` field
  with `_control_measure_shared.py`'s own `_configure_affiliation_field()`,
  reusing what every LINES and AREAS layer in this appendix uses. For
  those layers that is right: `affiliation` there only ever picks a Qt
  colour, so the shared vocabulary carries a deliberate fifth value,
  "Unspecified (black)", and `DEFAULT_AFFILIATION` is exactly that. But
  a POINTS layer feeds the same field into `build_sidc()`, and SIDC
  digit 4 has only the four real standard identities. So every point
  digitized without touching that dropdown - which is every point in a
  smoke test - produced an invalid SIDC.

  **Why it looked like a symbol bug rather than a field bug.**
  `mct_build_sidc()` catches KeyError and returns the error MESSAGE as
  its result. That string flows on to `mct_sidc_svg()` as if it were a
  SIDC, milsymbol fails to resolve it, and falls back to its own
  unknown icon (an inverted "?"). Every one of the 13 entities drew the
  identical glyph, in the correct green - because `monoColor` is
  applied whether or not the icon resolved. The result reads as "the
  icons are broken", and points investigation at milsymbol, the
  vendored build, the SIDC codes and the QGIS version - all of which
  were fine. Probing the codes directly (all 13 valid, both QGIS
  versions, all 104 affiliation x status combinations) is what ruled
  the symbol pipeline out and turned attention to the layer's own
  defaults.

  **Why the tests passed.** The B1 render test asserted that the
  data-defined path `startswith("base64:")`, and set `affiliation` to
  "friend" by hand. Both halves were wrong: hardcoding the value meant
  the layer's own default was never exercised by anything, and a
  base64 path is exactly what the unknown-icon fallback also produces.
  The assertion could not distinguish "rendered the right symbol" from
  "rendered milsymbol's placeholder".

  **The fix**, matching what `c2_measures.py`,
  `defensive_control_measures.py` and `offensive_control_measures.py`
  already do: the Points layer gets its own four-value
  `_POINT_AFFILIATION_LABELS` and its own 'friend' default, instead of
  the lines/areas helper.

  **The tests that would have caught it**, now added: they build a
  feature from the layer's OWN configured defaults rather than
  restating them, decode the base64 payload and assert milsymbol's
  unknown-icon path is absent - across the layer's defaults, every
  entity, and the full sweep of what the attribute form actually
  offers (affiliation x status x entity x colour). Verified by
  reverting the fix: 15 of them fail, and pass again with it restored.

  Also found, NOT changed: `airspace_control_measures.py`,
  `maritime_control_measures.py` and `target_control_measures.py` build
  their own point affiliation dropdown as `dict(AFFILIATION_LABELS)`,
  so all three still OFFER "Unspecified (black)" on a milsymbol-
  rendered layer. Their defaults are 'friend', so they work as shipped
  and nothing regressed - but choosing that one menu entry produces the
  same unknown icon. Left alone rather than folded into this fix: all
  three are maintainer-confirmed tables, and the standing rule is one
  symbol at a time. Raised for a decision.

    821 tests passing on both QGIS versions.

- **The same defect class, swept across every Points layer**
  (2026-08-12, on the maintainer's instruction after the H-XIX fix
  above: "fix the other three layers too").

  **Root cause addressed, not just the three sites.**
  `_control_measure_shared.py` now carries `POINT_AFFILIATION_LABELS`
  and `DEFAULT_POINT_AFFILIATION`, plus a
  `_configure_point_affiliation_field()` to match the lines/areas
  helper that already existed. That absence was the actual cause: the
  module's own comment had already worked out that points and control
  measures need different affiliation vocabularies - it says so
  explicitly, "Point symbols don't have this problem" - but only ever
  provided the control-measure one, so a new Points layer reaching for
  a shared helper could only find the wrong one. All seven Points
  layers now take the shared points vocabulary; airspace, maritime and
  target stop offering "Unspecified (black)", and c2, defensive,
  offensive and obstacle stop each restating the same four-value dict.

  `POINT_AFFILIATION_LABELS` is written out longhand rather than
  derived from AFFILIATIONS, so adopting it does not reshuffle any
  existing dropdown's order; a test pins its keys to AFFILIATIONS'
  instead, which also catches a standard identity added to sidc.py and
  missed here.

  **A separate, older bug found by the new sweep**: Abatis (280100) is
  a LINE, so milsymbol has no point icon for it at all - and it was the
  shared Control Measure Points layer's own DEFAULT entity. Every
  freshly digitized point on that layer drew the unknown icon until an
  entity was chosen: the same user-visible symptom as the H-XIX bug,
  from an unrelated cause, and present since Abatis was left there. The
  default is now Shelter. Abatis stays in the dropdown as intended (it
  should not vanish between batches) and B4 still removes it when it
  builds the line version. Its unrenderability is now asserted rather
  than skipped, so the exemption fails and must be deleted when B4
  removes the entry.

  **tests/test_point_layer_affiliations.py** is new and deliberately
  cross-layer: the defect is not about any one table, so pinning it
  inside each table's own tests would not have caught the next layer to
  get this wrong. It enumerates every Points layer and asserts each
  one's affiliation default is a real standard identity, that no
  dropdown offers a value build_sidc() rejects, and that both the
  layer's own defaults and every offered affiliation decode to a real
  icon rather than milsymbol's unknown fallback. Verified by
  reintroducing `dict(AFFILIATION_LABELS)` on the target layer: caught.

  Two test-construction notes worth keeping. The sweep must FIND the
  data-defined symbol layer rather than assume `symbolLayer(0)` -
  Defensive draws a simple marker beneath its icon and C2 draws one
  above, so the index differs per layer. And it must drive each layer's
  OWN configured defaults rather than restating them, which is exactly
  what the original B1 test failed to do.

    829 tests passing on both QGIS versions.

- **H-XIX batch B2 - obstacle zones and the mined-area family**
  (2026-08-12). EIGHT area measure types, not the ten the batch title
  guessed: 270500 (Obstacle Effects) and 270700 (Minefields) are
  PARENT rows whose own template cell reads "N/A". B0's rescope was
  right and the title was stale.

  New `Obstacle Control Measures (Areas)` layer: Obstacle Belt/Zone/
  Free Zone/Restricted Zone, Mined Area, Decoy Mined Area, Decoy Mined
  Area Fenced, and UXO Area.

  **Two new expression functions**, both real geometry rather than
  styling tricks, following the precedent mct_crenellate_outline() set
  for Fortified Area (two QgsMarkerLineSymbolLayer attempts there
  produced a "beaded chain of floating shapes" before a geometry
  construction fixed it):

  - `mct_serrate_outline($geometry, teeth, outward)` - the zones'
    sawtooth boundary. Same walk-the-ring cycle as crenellation, and so
    inherits its hard-won detail: outward direction resolved once per
    ring from winding order, because the centroid-distance test flips
    the wrong way in concave stretches.
  - `mct_decoy_chevron($geometry)` - the dashed inverted-V that is the
    ONLY thing distinguishing a decoy from a real Mined Area. Map-unit
    geometry so it scales with the polygon, as the standard's own draw
    rules require of that block.

  **The maintainer caught a real error mid-build**: the teeth on
  Obstacle Free Zone and Obstacle Restricted Zone point INWARD, cut as
  notches out of the shape, where Belt and Zone spike outward. The
  first pass drew all four outward. Verified against the enlarged
  template pictures and now pinned by a test that reads the real
  geometry expressions, so a future edit cannot flip one silently.

  **Four render-caught mistakes**, none visible in code review:

  - The "M" glyphs around the mined-area perimeter were first built as
    a repeating label with Line placement. Wrong twice over: the labels
    ROTATE with the boundary where the template draws every M upright,
    and the count drifts with polygon size where the template shows
    exactly four. Now four fixed anchors, each snapped onto the real
    boundary with closest_point() rather than used as a raw bounding-box
    corner (which sits off the shape for anything non-rectangular).
  - Mined Area's Fields H and W landed on top of each other and PAL
    silently dropped one - both expressions evaluated correctly, so
    only the render showed it. Fixed with yOffset, since `dist` is the
    AroundPoint radius and is ignored by OverPoint (the same trap B1
    hit). The sign convention was then confirmed by render too: a
    POSITIVE yOffset moves the label DOWN here, so Field H, which the
    template puts above centre, takes a negative one.
  - Obstacle Restricted Zone's Field T sat unreadably on its own hatch
    until the hatch layer joined the outline in the mask id list.
  - The hatch had to fill the SERRATED shape, not the user's polygon,
    or the teeth sit outside the fill - make_polygon() closes the
    serrated ring back into an area.

  **A standing test earned its keep.** B2's first pass put its eight
  area codes into sidc.py's own ENTITIES; test_control_measure_points'
  own "every entity is offered by SOME dropdown" invariant failed
  immediately. It was right: ENTITIES is the milsymbol-rendered POINT
  vocabulary, and every hand-drawn line/area measure type in this
  appendix carries its code in module-level data instead. The codes
  moved to AREA_MEASURE_TYPE_CODES.

  **Colour** is the first batch with MIXED defaults - UXO Area black,
  the rest green - so the `colour` field's default is now the CASE B1's
  own comment predicted, DERIVED from TABLE_H_XIX_INVENTORY rather than
  restated. The audit's "OT" (outline green, text black) is implemented
  as exactly that: the four zones' labels are black while their outline
  follows the colour field.

  **Deliberately not built, and why:**

  - **Mined Area's Field A.** The standard calls it "graphics ...
    filled with the type of mine(s)", and mine-type selection is
    precisely the beyond-the-standard extension the maintainer's audit
    assigns to batch B3. A placeholder here would only be torn out.
    Fields H ("S"/"+S") and W (self-destruct time) ARE built - the
    standard's own Note makes those plain text.
  - **The "N" field boxes** on Decoy Mined Area, Fenced. Boxed glyphs
    in the TEMPLATE column are field placeholders, not drawn geometry -
    confirmed by that entry's own EXAMPLE column, which omits them.

  **One discrepancy raised rather than resolved**: the standard draws
  Decoy Mined Area, Fenced in BLACK (measured by pixel analysis of the
  rendered page, not judged by eye - green_px=1 against black_px=4706),
  while the maintainer's audit leaves it unlisted and so green by their
  own stated default rule. Built green per the audit, since colour is a
  per-feature field the user can switch anyway.

    839 tests passing on both QGIS versions.

- **H-XIX batch B3 - mine types and the minefield family**
  (2026-08-12). The maintainer opened this one by pointing out that B2
  had shipped Mined Area without its Field A: "the user needs to be
  given a choice of which types of mines are in the area". They then
  asked whether to fix it immediately or fold it into B3, and how to
  model it.

  **Modelled as a FIELD, not as extra measure types.** The alternative
  the maintainer offered was one measure type per combination ("mined
  area - anti-personnel", "mined area - anti-tank", ...). Rejected for
  three reasons: it does not remove the hard part (the combined variant
  still has to alternate glyphs on a line either way); measure_type
  maps 1:1 onto the standard's own code and a test pins it, so four
  Mined Area variants would all claim 270800; and minefield STATE is a
  separate axis, so splitting by type as well gives ~15-20 entries for
  one family - the "otherwise the list is too long" problem the
  maintainer already raised on Table H-XIV.

  **The glyphs are batch B1's own icons.** Antipersonnel Mine (280200),
  Antitank Mine (280300) and Unspecified Mine (280600) are exactly the
  three the standard's own examples draw inside the A field, so nothing
  new was drawn - the fill renders the same milsymbol SVGs through
  mct_sidc_svg. Pinned by a test, so losing one from B1's vocabulary
  fails loudly instead of silently rendering the unknown icon.

  **Two glyph rules, per the maintainer**: an AREA shows just one
  symbol of each selected type, while anything drawing more than one
  ALTERNATES. So Mined Area's A field draws one glyph (two side by side
  when combined), and the minefield box draws three, alternating
  antipersonnel/antitank when combined.

  **New Minefields layer** - five codes over four measure types.
  Completed (270701) and Planned (270702) are ONE type split by
  `status`, since their templates differ only by a solid versus dashed
  box, which is what H.5.1.1.3's own present/planned rule already
  drives everywhere else; the audit asked for exactly that fold. Known
  Enemy and Suspected stay separate - "suspected" is not the same claim
  as "planned".

  Its own layer rather than more entries on B1's Points layer: those
  are single milsymbol icons behind one SVG marker, while these are
  hand-built composites needing a rule-based renderer and their own
  fields.

  **QgsEllipseSymbolLayer for the box**, not QgsSimpleMarkerSymbolLayer:
  the box is wider than it is tall (~2.3:1 off the template) and a
  simple marker has only one `size`. The ellipse layer takes an
  independent width and height in millimetres, which is also what
  "Size/Shape: Static" needs - a fixed screen size, not one derived
  from anchor points. Verified to behave identically on 3.44 and 4.2
  before being relied on.

  **Render caught the chevron.** Dummy Minefield's decoy mark was first
  built with Qgis.MarkerShape.ArrowHead, which draws a diagonal arrow
  rather than a symmetric open V; a Triangle would have closed the
  bottom edge the template leaves open. QGIS has no open-V marker
  shape, so mct_decoy_chevron_svg() now returns the two strokes as an
  inline "base64:" SVG - the same path format the milsymbol pipeline
  already feeds to QgsSvgMarkerSymbolLayer. Note this is the FIXED-SIZE
  case; mct_decoy_chevron() still serves the polygon case, where the
  mark has to scale with the shape.

  **A deliberate departure from the audit, raised rather than taken
  silently**: it asked for Dummy Minefield Dynamic (270706) and Dynamic
  Depiction (270707) to merge into one area. They are built as TWO,
  because the dashed chevron is the only thing that says "this is a
  decoy" - a claim about the ground, not a styling detail, and merging
  would conflate a fake minefield with a real one. **CONFIRMED by the
  maintainer 2026-08-12** after smoke-testing B3: "the dummy minefield
  and dynamic are fine, no problem". The audit document still reads
  "merge", so the departure is recorded in the module itself too.

  Both dynamic areas scatter their mines with
  QgsRandomMarkerFillSymbolLayer at a FIXED count and a fixed seed, so
  the symbol reads the same at any zoom and does not reshuffle on every
  repaint.

  A standing test again did its job: the B2 areas test failed the
  moment the two dynamic minefield areas joined that layer, and was
  tightened to assert the real union (B2 plus those two) rather than
  loosened to a subset.

    848 tests passing on both QGIS versions.

- **B1/B2 smoke-test follow-ups** (2026-08-12) - five items from the
  maintainer's own live QGIS pass.

  **"What is the mine indicator field supposed to be filled with?"** -
  Field H, and the answer is that it should never have been a free-text
  box. The standard's own Note gives it exactly two values: "S" when
  only scatterable mines are present, "+S" for a mix (with the
  self-destruct time then going in Field W). It is now a ValueMap
  offering those two and nothing else, on both the Areas and Minefields
  layers, and all three mine fields carry aliases naming the standard's
  own field letter ("Mine type (Field A)", "Scatterable mines (Field
  H)", "Self-destruct time (Field W)") so the form explains itself
  rather than needing the table open alongside.

  **Towers +30%, designation pulled in and raised.** The label offset
  was 0.62 of the marker width; the maintainer asked for 60% closer, so
  it is 40% of that. They then followed up that it should sit level
  with the TOP of the glyph rather than its middle - both Tower icons
  have a 108x98 viewBox, so the raise is derived from the drawn height
  (width * 98/108) rather than typed as a millimetre constant, and
  tracks the size multiplier instead of drifting off it. Note a
  NEGATIVE yOffset is what raises a label, confirmed by render; the
  sign reads backwards.

  **Antipersonnel Mine with Directional Effects** - "the circle has
  become too small". Measured rather than eyeballed: its viewBox is 148
  wide against its plain sibling's 108, because the directional arrow
  hangs outside the circle, and QGIS sizes an SVG marker by WIDTH. So
  the artwork drew at 73% scale. 148/108 restores it. Third time this
  exact trap has appeared (Pop-Up Point, Fire Support Station), and the
  test asserts the ratio against the REAL rendered viewBoxes rather
  than the constant, so it survives milsymbol changing its artwork.

  **Stroke thickness +80%** on the five outline icons the maintainer
  named. Worth recording how NOT to do this: milsymbol has its own
  `strokeWidth` option, and it does not do what it looks like. Probed
  directly - it only widens the generated viewBox (108 -> 110.8) while
  every path keeps stroke-width="3", so passing it would render the
  icon SMALLER at a fixed marker size and no thicker. The scaling is
  therefore done on the rendered SVG in symbol_engine, and mct_sidc_svg
  gained an optional fifth argument (additive, default off, no existing
  caller affected) exactly as it did for monoColor.

  Fixed and Prefabricated Obstacle is included because the maintainer
  listed it, but it is a FILLED triangle rather than an outline, so the
  change is barely visible there by construction - noted rather than
  silently dropped.

    856 tests passing on both QGIS versions.

- **B3 correction and a second faintness report** (2026-08-12).

  **"ENY" belongs ON the box's vertical sides, not clear of them** -
  the maintainer's correction after smoke-testing B3, and what the
  template draws: the box's own side is interrupted where the field
  sits. So the offset is exactly half the box width with no clearance
  gap, the quadrant is Over, and the box carries an id the labels mask
  against so its line breaks through the text. One shared mask list on
  every rule, including the H and W labels that do not need it, because
  masking is configured per LAYER and rules declaring different lists
  make QGIS keep one arbitrarily.

  Moving it there immediately showed why the box had to grow: at 15mm
  the ENY text reached inward over the outer mine glyphs. The two enemy
  variants now draw a 21mm box through a data-defined width, which is
  also what the standard's own picture shows - its enemy box is wider
  than the plain one, for exactly this reason.

  **The mine glyphs needed B1's stroke thickening too.** The maintainer
  found the Antipersonnel Mine's "ears" and the Unspecified Mine's
  circle faint again, this time as the glyphs drawn inside areas and
  minefield boxes - which the B1 change had not touched, because those
  go through their own SIDC expressions. They also draw at 5mm against
  a B1 marker's 8mm, so the same thin stroke reads fainter still. Both
  glyph expressions now pass the same 1.8 factor.

  **The by-value segfault caught its author.** The first version of the
  new ENY test chained `settings.format().mask().maskedSymbolLayers()`
  and killed the interpreter mid-run - the exact trap this project has
  documented for months, in a test written to guard against regressions.
  Each accessor now lands in its own variable.

    859 tests passing on both QGIS versions.

- **The unknown-glyph bug, third occurrence** (2026-08-12). The
  maintainer's B2 smoke test: "when inserting the mined area with the
  mines, the glyphs are broken", and the same on Dynamic Depiction.

  Same defect class as B1's, in a new place. Both symbols live on the
  AREAS layer, whose `affiliation` correctly defaults to "unspecified"
  - that is the lines/areas vocabulary, and right for a hand-drawn
  outline, where the fifth value means "draw it black". But B3 then
  fed that same field into the mine glyphs' SIDC, build_sidc() raised,
  mct_build_sidc() returned the KeyError message as if it were a SIDC,
  and milsymbol drew its unknown-icon fallback for every mine.

  **Fixed by removing the dependency, not by changing the vocabulary.**
  That layer genuinely needs the fifth value for its outline. The
  glyphs simply stop reading `affiliation` and use a fixed standard
  identity instead - nothing is lost, because monoColor repaints these
  icons from the `colour` field regardless and an unframed
  control-measure icon takes no other cue from its standard identity.
  The affiliation was never visible on them in the first place.

  **The test that should have caught it made the identical mistake the
  B1 test did**: it built its feature with affiliation="friend"
  hardcoded, so the layer's own default was never exercised. Rewritten
  to drive the layer's defaults.

  **A new cross-layer guard** now renders every milsymbol-bearing
  symbol on the Areas and Minefields layers FROM THEIR OWN DEFAULTS,
  walks into sub-symbols (the glyphs hide inside a centroid fill and a
  random-marker fill), decodes each base64 payload and asserts the
  unknown-icon path is absent - across every measure type, every mine
  type, and every affiliation the form offers. Verified by reverting
  the fix: 17 failures.

  The generalisable lesson, now recorded in that test's own docstring:
  the risk is not "affiliation" specifically, it is any field that is
  legitimate for a layer's hand-built symbology while being invalid as
  SIDC input - and the only way to see it is to render from the
  layer's own defaults, because a broken SIDC still yields a perfectly
  well-formed base64 path.

    862 tests passing on both QGIS versions.

- **Presentable mine scatter** (2026-08-12) - "these scattered mines,
  they don't look good, should not touch the perimeter, should not
  touch each other".

  QgsRandomMarkerFillSymbolLayer cannot do either. It clips the POINTS
  to the polygon, so a glyph centred near the edge still hangs over the
  boundary, and it has no notion of minimum separation at all. Replaced
  with mct_scatter_points(): seeded dart-throwing that holds each point
  clear of an inset boundary and of every point already placed, giving
  up after a bounded number of attempts so a long thin sliver takes
  fewer mines rather than being crammed or left empty.

  Both distances are fractions of the shape's own size (sqrt of area)
  rather than absolute map units, so one setting reads the same on a
  small minefield and a large one. The seed comes from the geometry's
  own centroid, so each feature gets its own arrangement while any one
  feature stays stable - QGIS re-evaluates this on every pan and zoom,
  and an unseeded scatter would visibly crawl.

  **A bug found while fixing it**: a combined anti-personnel/anti-tank
  dynamic minefield was drawing only the primary glyph, which breaks
  the maintainer's own rule that anything drawing more than one glyph
  alternates. The scatter now runs twice over the SAME placement,
  taking alternate points via new modulus/remainder arguments - so the
  two halves are disjoint by construction, which two independent
  scatters could not guarantee. _minefield_glyph_sidc_expression()
  already had the right semantics for both passes: alternating for a
  combined type, repeating for a single one.

  **The mines vanished entirely on the first attempt** and the render
  showed it: random.Random accepts only None/int/float/str/bytes, and
  the tuple seed raised a TypeError that QgsExpression swallowed into a
  null result - a silent empty geometry rather than a visible error.
  Seeded with a formatted string now.

  Note the new tests evaluate the function through QgsExpression rather
  than calling it: @qgsfunction replaces the Python function with a
  QgsPyExpressionFunction, which is not callable.

    868 tests passing on both QGIS versions.

- **Dummy Dynamic's chevron spans the area** (2026-08-12) - the one
  observation from the maintainer's B3 smoke test: "the chevron above
  should ideally extend to the horizontal extent of the area, height is
  fine".

  mct_decoy_chevron() gained a half-span argument rather than being
  widened outright, because ONE function serves two different
  placements: Decoy Mined Area and Decoy Mined Area, Fenced draw their
  chevron INSIDE the shape, where the template keeps it well short of
  the sides, while Dummy Minefield, Dynamic draws it ABOVE. Only that
  caller passes 0.5 (corner to corner); the other two keep the measured
  0.24. Both spans are pinned by test, and the two Decoy variants were
  re-rendered to confirm they did not move.

  Height untouched, as asked.

    871 tests passing on both QGIS versions.

- **H-XIX batch B4, first pass - the wire family** (2026-08-12). Nine
  of B4's seventeen entries: 290301-290309, printed pages 586-587.

  New `Obstacle Control Measures (Lines)` layer. All nine are ONE
  construction - a line carrying a repeating glyph - so they share a
  single symbol with the glyph, its offset and the line's style all
  chosen by expression, rather than nine near-identical builders that
  would drift apart. Same reasoning as B3's mine-type field.

  **290300 ("Wire Obstacles") is excluded**: its template cell reads
  "N/A", making it a heading row rather than a symbol - the third
  parent row this table has hidden in a code range, after 270500 and
  270700.

  The glyphs are inline SVG (mct_wire_glyph_svg) rather than font
  markers. An X, a six-pointed asterisk and a wire loop would otherwise
  depend on whatever glyphs the host machine's fonts happen to carry,
  which is not good enough on a standard this project renders against
  template pictures.

  **The render caught two pairs shipping identical.** Double Apron
  Fence was drawing Single Fence's plain barb, and High Wire Fence was
  drawing Single Concertina's loop. The apron now has its own glyph
  (a barb with a stay to each side, which is what the apron is), and
  the concertina raises its loops ABOVE the line where High Wire Fence
  centres them on it - which is the only thing separating those two in
  the standard's own templates.

  The regression guard for that then found a THIRD pair, correctly:
  Unspecified Wire Obstacle and Low Wire Fence both repeat a cross. But
  there the test was wrong, not the symbol - the standard separates
  those two by Unspecified drawing no line at all, so the line style is
  now part of what the test treats as the symbol's signature.

  **Still to come in B4** (8 entries): Abatis (280100), Obstacle Line
  (290100), the four antitank ditches (290201-290204), Mine Cluster
  (290400) and Trip Wire (290500) - the last still expected to need its
  own construction rather than the shared marker line.

    875 tests passing on both QGIS versions.

- **The wire family, rebuilt from the maintainer's own description**
  (2026-08-12). The first pass read the nine shapes off the template
  pictures and got several wrong. The maintainer then wrote out the
  construction directly, and it is far simpler than that pass assumed:
  every one of the nine is "a series of Xs" (or of 0s - an OVAL, they
  were explicit, not a circle), varying only in three things.

  So the module now carries a `_WIRE_SPECS` table with exactly those
  three axes - glyph, gap between glyphs in glyph-widths, and which
  straight lines run through the series - transcribed from that
  description, which is the single source of truth for all nine. Two
  shapes replace the six the first pass invented.

  A symbol per measure type replaces the earlier one-shared-symbol
  design, because the NUMBER of straight lines genuinely varies (none,
  one, or two) and that is a different set of symbol layers rather than
  a different expression.

  Double Fence's pair is one marker holding two crosses: a marker line
  has a single interval, and that measure type spaces the pair (0.5 of
  a width) differently from the gap between pairs (3 widths). Its
  viewBox is 250 wide against the others' 100, so it is drawn 2.5x -
  QGIS sizes an SVG marker by WIDTH, the same trap as Pop-Up Point,
  Fire Support Station and the directional mine.

  **"The line should always be longer or extend beyond the Xs or 0s."**
  offsetAlongLine was the first attempt and is not enough - it insets
  the FIRST glyph only, and a render showed Single Fence still ending
  flush, because markers land at fixed intervals from the start and the
  last can fall on the final vertex. The glyphs now run along a TRIMMED
  copy of the line (line_substring) while the straight lines are drawn
  on the full geometry, which bounds both ends by construction. The
  trim is a fraction of the line's own length, since line_substring
  works in layer units.

    879 tests passing on both QGIS versions.

- **Wire glyph spacing tightened 40%** (2026-08-12), on the
  maintainer's word after the rebuilt render: "reduce the gap between
  the Xs and 0s across the board by 40%".

  Applied as a single `_WIRE_GAP_SCALE` factor rather than by editing
  the nine numbers in `_WIRE_SPECS`. Those numbers are a transcription
  of the maintainer's own description of the manual, and a test asserts
  they still match it - so tuning how the symbols LOOK must not quietly
  rewrite what the table SAYS. The two concerns now have separate
  knobs.

  The 0.5 spacing inside a Double Fence pair is deliberately not
  scaled: it was given as an explicit figure and is baked into the
  paired glyph's own geometry. Flagged rather than assumed.

    880 tests passing on both QGIS versions.

- **Double Fence pair spacing to 0.25**, and a duplication removed with
  it (2026-08-12).

  The pair gap had been written down TWICE - as a 250-wide viewBox in
  the glyph function and as a 2.5 size multiplier in the module - which
  are the same fact, since QGIS sizes an SVG marker by width. Changing
  the spacing to 0.25 would have made them disagree and rendered the
  paired crosses at the wrong size against every other glyph.

  Both are now derived from one `_WIRE_PAIR_GAP` constant, passed into
  the glyph function as an argument, and the test asserts the
  multiplier as `2 + _WIRE_PAIR_GAP` rather than as a literal. The
  duplication was latent from the first build and only surfaced because
  the maintainer changed the number.

  Note this gap is deliberately NOT scaled by `_WIRE_GAP_SCALE`: that
  factor tunes the space BETWEEN pairs, and the within-pair figure was
  given explicitly.

    880 tests passing on both QGIS versions.

- **B4 continued - the toothed obstacles** (2026-08-12). Four more:
  Abatis (280100), both antitank ditches (290201/290202) and the
  Antitank Wall (290204). Thirteen of B4's seventeen are now built.

  They reuse the wire family's own construction rather than a parallel
  one, because they ARE the same thing - a line carrying a repeating
  glyph. Only the glyph and its spacing differ, so they are four more
  rows in `_WIRE_SPECS` and four more shapes in the glyph function,
  which grew a `filled` flag for the one real difference between the
  two ditches: Under Construction is hollow, Completed is solid, and
  that is the whole of it in the standard's own templates.

  "The teeth point toward enemy forces" needs no code: a marker line
  rotates its glyph to follow the line, so the side they fall on
  follows the order the anchor points were digitized in - which is
  exactly what the standard's own Orientation rule says.

  Three existing tests then failed, correctly: they asserted
  `_WIRE_SPECS` held exactly the nine wire types. Two were widened to
  cover every line obstacle (the no-two-alike invariant is the same
  invariant for all thirteen), and the third - which pins the
  maintainer's own transcription of the manual - was scoped to the nine
  it actually describes, since the toothed four came from the templates
  instead.

  **Four remain in B4**, listed in the module and deliberately NOT
  offered by the layer until they can be drawn correctly: Obstacle Line
  and Antitank Ditch Reinforced with Antitank Mines (templates not yet
  read), and Mine Cluster and Trip Wire, whose constructions are now
  known and recorded but which need their own geometry functions rather
  than a marker line.

    882 tests passing on both QGIS versions.

- **All four toothed obstacles corrected** (2026-08-12), from the
  maintainer's smoke test. Every one of the four was wrong, and in the
  same way: the first build assumed each was "a line with teeth on it"
  when three of them ARE their own line, and the fourth is not
  repeating at all.

  - **Abatis** is a SINGLE hump just after the first anchor point and
    then straight line - "_^____", with the hump's legs meeting the
    horizontal. Not a repeating glyph, so it now has its own builder
    rather than a `_WireSpec`, using FirstVertex placement so there is
    exactly one hump however long the line is.
  - **Both antitank ditches** are a line BUILT OF triangles, bases
    touching end to end, with no separate straight line drawn. So the
    gap is 0 (the glyphs tile) and there are no line layers.
  - **The antitank wall** tiles a serrated profile into one continuous
    sawtooth - the maintainer's own comparison to the obstacle zones'
    serrated boundary - rather than dropping separate notches below a
    line.

  All four also needed their glyph raised half its height, so the edge
  that IS the line (the triangles' bases, the sawtooth's flats, the
  hump's legs) sits on the digitized geometry instead of running
  through the glyph's middle.

  Three tests needed correcting with them, and one is worth noting: it
  asserted "only Unspecified Wire Obstacle draws no line", which was
  true and is now wrong for a second reason - the ditches and wall draw
  no separate line either, because they are their line. The test now
  names both reasons rather than just widening the set.

    882 tests passing on both QGIS versions.

- **Abatis and the antitank wall, corrected again** (2026-08-12). Both
  needed further passes, for the same underlying reason: a symbol drawn
  ON a line is not the same as a symbol that IS the line.

  **Abatis** is a KINK, not a marker: "the base of triangle touching
  the line should be clear... not a full triangle". A marker riding the
  line leaves the straight line running underneath it, which closes the
  triangle - exactly what the previous attempt did. It is now real
  geometry (mct_abatis_line), inserting a triangular detour into the
  line near its start, so the base is genuinely open.

  **The antitank wall** went through three readings before landing:
  separate notches below a line, then Vs hanging off a line, then
  finally "--v--v--v--", one continuous path that runs flat, dips into
  a V and comes back up, the line joining the EDGES of the Vs. Built as
  a tile whose flats sit at its own vertical centre, so consecutive
  tiles leave one V side length of flat between dips - the spacing the
  maintainer specified.

  **Two rendering artifacts the maintainer caught**, both invisible in
  code and neither reachable by reading the standard:

  - Glyphs painted OVER the straight line nibble a hairline out of it
    at each glyph's own box edge. The glyph series is now drawn
    beneath the lines; everything here is one colour, so the order is
    otherwise invisible.
  - Tiling glyphs butted at exactly one glyph width still leave a
    hairline at every join. They now overlap by a sliver.

    883 tests passing on both QGIS versions.

- **Maritime Control Measures (Points): the Group now genuinely filters
  the Entity list** (2026-08-12). The maintainer's own report, and it
  had two halves - one usability, one correctness. "From a UI point of
  view, it is not friendly", 105 entities in one flat dropdown; and
  "user may select group as general and entity as reference point -
  ultimately reference point is displayed which is incorrect."

  When this layer was built earlier the same day, the group was carried
  as a PREFIX on every label plus a "group" field auto-derived from the
  chosen entity, on the stated grounds that the only QGIS mechanism
  that truly filters one field by another - a ValueRelation cascade -
  had been retired from the old shared `unit_layer.py` after a native
  crash. **That reasoning was wrong, and this roadmap already said so.**
  The maintainer remembered it correctly: "initially when we had
  land/air/space etc under one layer, in the menu selection, if we
  selected land in group, only land related entities came up, and it
  worked perfectly fine". The crash was only ever reproduced by driving
  `QgsValueRelationFieldFormatter.createCache()` DIRECTLY from the
  headless harness, and Phase 10's own entry records the resolution in
  as many words - "**Confirmed safe 2026-08-07**: user smoke-tested the
  real interactive attribute form live - the cascading dropdown works
  correctly, no crash". What `unit_layer.py` was retired for was its
  one-layer-for-four-domains design, not this widget. The lesson is
  narrower than "avoid the cascade": a caveat that has since been
  settled has to be re-read before being cited, not carried forward as
  received wisdom.

  So the dependency now runs group -> entity, the way the form reads:
  a hidden `NoGeometry` lookup layer (one row per (group, entity, label)
  pair, registered with `addToLegend=False`, reused rather than rebuilt
  so a second Points layer cannot orphan the first one's widget config)
  backs a ValueRelation on "entity", filtered by `"group" =
  current_value('group')`. Entity labels dropped their group prefix -
  the group is on the line directly above in the form, so repeating it
  in all 105 options was the workaround, not the goal.

  **The correctness half needed its own answer.** Filtering the
  dropdown only stops a mismatched pair being PICKED; changing the
  group AFTER the entity still leaves the old value stored, because
  QGIS re-filters the list but does not clear the field. "entity" now
  carries a HARD constraint expression pinning it to its own group's
  rows - an ordinary per-feature expression with no `current_value()`
  in it, which is also the documented fallback the original crash note
  itself named. The two defaults are derived from each other so a
  freshly digitized point can never arrive already invalid.

  **Verified in a real QgsAttributeForm, offscreen, deliberately
  outside the test suite** (instantiating a ValueRelation widget is
  exactly the call that once segfaulted this harness, so it ran in its
  own process where a crash would cost nothing). It did not crash, and
  the filter works: group=General offers its own 10 entries,
  group=Hazard 3, group=Sonobuoys 16. That probe also corrected a wrong
  assumption in the first cut - `OrderByValue: False` does NOT preserve
  the lookup layer's own row order (the standard's printed order); QGIS
  sorts a ValueRelation either way, so it is now True, sorting by the
  label the user actually reads rather than by the internal entity slug.

  887 tests passing on both QGIS versions.

- **Mine Cluster (290400) built** (2026-08-12), the first of B4's last
  two. The maintainer's own construction: "user clicks two points,
  connect it with a dashed line, make a semi-circle over it, radius
  1/3 and not 1/2 of the line connecting the two points."

  **That last clause is a deliberate departure from the standard's own
  text**, flagged here rather than silently followed either way. Table
  H-XIX's own draw rule for 290400 (printed page 597, rendered and
  read directly) states: "The radius of the semicircle is 1/2 the
  length of the straight line." The maintainer's instruction was 1/3,
  given as an explicit correction ("and not 1/2") rather than as a
  vague description this project might have misread - so it is built
  exactly as instructed, as `_MINE_CLUSTER_ARC_RADIUS_FRACTION = 1.0 /
  3.0`, with the standard's own 1/2 recorded here for the record and
  raised back to the maintainer to confirm is an intentional
  house departure, not a misremembering.

  Two symbol layers: the straight PT1-PT2 line is drawn as-is (a
  QgsSimpleLineSymbolLayer over the feature's own digitized geometry),
  and the arc is real generated geometry
  (`mct_mine_cluster_arc($geometry, 1/3)`) rather than a fixed-size
  marker, so it scales with however far apart the two clicks are - the
  same reasoning already applied to Abatis's kink and the Decoy
  chevrons. Both layers are dashed OUTRIGHT, not driven by "status":
  the standard's own note reads "the dashed lines in this symbol shall
  be displayed in present and anticipated status", i.e. always dashed,
  the same fixed-iconography treatment as Maritime's own Bearing Line,
  Acoustic (Ambiguous).

  The semicircle's diameter sits ON the line, centred at its own
  midpoint - not spanning the full line, since the radius is a
  fraction of the line's length, leaving a straight run bare at each
  end. Built generically for any line angle (bulges perpendicular to
  the PT1->PT2 direction, not to a map axis), verified against a
  diagonal line, not just an axis-aligned one.

  Only Trip Wire (290500) remains in B4 - the one already flagged as
  needing its own working-out at build time.

  895 tests passing on both QGIS versions.

- **Mine Cluster, corrected same day** (2026-08-12): "the line should
  not extend beyond the semicircle or the semicircle should touch the
  end points of the line, make the dashes slightly longer say by 40%
  and increase the space between them by 50%." This also settles the
  open question the previous entry raised: the maintainer confirmed
  1/3 by correcting the RELATIONSHIP between the line and the arc
  rather than the radius itself, so 1/2 (the standard's own printed
  figure) is not the intended reading here.

  The straight line is now a geometry generator too, not the raw
  digitized geometry: `line_substring($geometry, length($geometry) *
  (0.5 - 1/3), length($geometry) * (0.5 + 1/3))` trims it to exactly
  the arc's own diameter span, derived from the SAME radius fraction
  the arc uses rather than a second hard-coded number, so the two
  cannot drift apart.

  The dash pattern is a custom `QgsSimpleLineSymbolLayer` dash vector
  now, not a bare `Qt.PenStyle.DashLine`. Probed Qt's own default
  first rather than assuming it (`QPen().dashPattern()` with
  `Qt.PenStyle.DashLine` set) - `[4, 2]` in units of the pen's own
  width - and applied the maintainer's +40%/+50% to THAT baseline, so
  `_MINE_CLUSTER_DASH_MM`/`_MINE_CLUSTER_GAP_MM` stay traceable to a
  real starting point rather than round numbers invented to look
  about right.

  898 tests passing on both QGIS versions.

- **Trip Wire (290500) built** (2026-08-13), closing out B4 at 17 of
  17 - all of H-XIX's line obstacles now built. The one the maintainer
  flagged in advance as needing to be worked out at build time.

  Read directly off the standard's own template/draw-rules text
  (printed page 598, rendered and read rather than trusted from an
  earlier paraphrase - the two disagreed on exactly which lines are
  part of the symbol). Three clicked anchor points, reinterpreted
  (like Abatis and Mine Cluster before it) rather than drawn as the
  raw PT1-PT2-PT3 polyline a digitizing tool connects them into:
  PT1-PT2 is a plain straight segment; PT3 "defines an end of the
  horizontal line", the other end being PT1 itself (the only anchor
  left once PT2 is spent on the arc); the template's own longer,
  unlabelled line running further down and past the vertical one is
  the same convention already caught once in this appendix (Light
  Line, H2) - an EXAMPLE-column explanatory addition (linking to a
  mine glyph to show the trip wire's purpose), not part of the control
  measure's own geometry, and not drawn.

  The arc: "the distance between the line connecting points 1 and 2
  and point 3 is the radius of the 90 degree arc at the bottom" - built
  as the PERPENDICULAR distance from PT3 to the infinite line through
  PT1-PT2 (not just the axis-aligned offset), so an off-axis PT3 still
  resolves sensibly; verified with a non-perpendicular PT3 specifically,
  not just the template's own axis-aligned example. The arc starts at
  PT2 tangent to the PT1->PT2 direction and curves 90 degrees to end
  tangent away from PT3's own side, matching the template's hook.

  Follows the ordinary H.5.1.1.3 present/planned rule (solid/dashed by
  status), unlike Mine Cluster - the standard's own draw rules carry no
  "always dashed" note here.

  Render-compared side by side against the standard's own template
  picture; matches.

  908 tests passing on both QGIS versions.

- **Mine Cluster's arc rebuilt as a half-ellipse touching both clicked
  points** (2026-08-13), superseding the previous day's "trim the line"
  fix. The maintainer's own correction: "you are trimming the line
  instead of extending the semi-circle, the user when he clicks pt1
  and pt2 expects the mine cluster to span that much, not reduce."

  A true semicircle at radius 1/3 of the line cannot span the full
  line without leaving its own ends bare - that gap was what motivated
  trimming the line down to match in the first place, which is exactly
  the "reduce" the maintainer rejected. Reconciled as a half-ELLIPSE
  instead: horizontal semi-axis locked to exactly half the PT1-PT2
  span (so it touches both points, full length, nothing trimmed),
  vertical semi-axis (the dome's own height) kept at the maintainer's
  own 1/3. `mct_mine_cluster_arc`'s `radius_fraction` argument is
  renamed `height_fraction` to match what it now actually controls.
  The straight line is back to a plain, undecorated
  `QgsSimpleLineSymbolLayer` over the feature's raw geometry - the
  `line_substring` trimming and the geometry-generator wrapper it
  needed are both gone.

  908 tests passing on both QGIS versions - the Mine Cluster suite was
  rewritten in place for the new construction rather than grown, so the
  total is unchanged from Trip Wire's own entry above.

- **Trip Wire rebuilt from the maintainer's own dictated construction**
  (2026-08-13), replacing the template-picture reading entirely.
  Reviewing that render, the maintainer gave the construction directly
  instead of correcting the reading: "user clicks PT1 and PT2 - draw a
  line connecting PT1 and 2, now at 1/7 pt from PT1, draw a line 90 deg
  to the line between PT1 and PT2, length 0.5 of the distance between
  PT1 and PT2, now at midway point, draw another line 90 deg or
  perpendicular to the line between PT1 and PT2, length 1.2 times the
  distance between PT1 and PT2, finally at PT2, draw an arc of 90 deg
  anticlockwise, radius 1/5 of the distance between PT1 and PT2."

  Two anchor points now, not three - PT3 is gone entirely. Built as a
  MultiLineString: the main PT1-PT2 line fused with the arc (they share
  PT2), plus the two perpendicular crossbars as their own separate
  parts. The arc's centre is derived, not guessed: for a start tangent
  u (continuing PT1->PT2's own direction) and an ANTICLOCKWISE sweep,
  the centre is PT2 offset by one radius along n = u rotated 90 degrees
  CCW - verified by a hand-worked example (PT1=(0,0), PT2=(10,0) ->
  centre=(10,2), end=(12,2)) before it went in the docstring, and
  cross-checked again by direct expression evaluation.

  Neither crossbar's own side nor which screen direction
  "anticlockwise" reads as was pinned down beyond the dictated wording
  - built consistently on one side (the main line's own left, standard
  CCW convention) so the whole symbol reads as one coherent shape. That
  is the one thing flagged for the maintainer's own review, per their
  own "will give further instructions if required."

  910 tests passing on both QGIS versions.

- **Trip Wire's crossbars made symmetric** (2026-08-13). The maintainer
  reviewed the render and corrected the one thing flagged for their own
  review, though not the side of the arc: "both the horizontal lines
  are on one side of the line connecting pt1 and 2, they should be on
  both sides." Each crossbar now extends the dictated length to BOTH
  perpendicular directions from its own base point on the main line,
  rather than one - the crossbar's own total span is now twice the
  stated multiplier (e.g. the midpoint crossbar reaches 1.2x the
  PT1-PT2 distance on each side, 2.4x total). The arc is untouched -
  the correction named "both the horizontal lines" specifically.

  910 tests passing on both QGIS versions (rewritten in place, not
  grown).

- **B5 started: Block and Turn built** (2026-08-13), the two of Table
  H-XIX's own four obstacle effects (270501-270504) whose draw rules
  are fully specified in the standard's own text rather than only
  shown in a picture - so they were built directly rather than run past
  the maintainer first, the same triage this appendix has used since
  H0 (build what the text settles, ask about what only the picture
  shows).

  **Block (270501)**: a "T" - crossbar PT1-PT2, stem from the
  crossbar's own midpoint out to a length set by PT3's perpendicular
  distance to the PT1-PT2 line (`mct_block_geometry`), the same
  projection technique already used for Trip Wire and Mine Cluster.

  **Turn (270504)**: PT1 (rear) to PT2 (arrowhead tip) connected by a
  TRUE 90 degree circular arc, PT3 picking which side it bulges toward
  (`mct_turn_arc`) - radius = chord/sqrt(2), centre set back chord/2
  from the midpoint, both derived from the standard circular-segment
  relations for a 90 degree included angle and checked against a
  hand-worked example before being trusted. The arrowhead reuses the
  plain-unfilled-chevron-at-LastVertex technique Direction of Attack
  already established (offensive_control_measures.py).

  **A real bug, caught by the render, not the tests**: the first cut
  appended the chevron's own marker-line layer as a sibling of the
  arc's geometry-generator layer, so it evaluated LastVertex against
  the feature's own RAW 3-vertex geometry (PT1, PT2, PT3) instead of
  the generated arc - the arrowhead landed at PT3, the side-selector
  point, nowhere near the arc at all. Every symbol layer evaluates
  against the feature's own geometry independently unless it is
  itself wrapped in a generator; the fix wraps the chevron in its own
  `mct_turn_arc($geometry)` generator too, so it follows the same arc
  the line layer draws. The unit tests as originally written could not
  have caught this - they checked the marker line's own placement
  setting, not what geometry it actually saw - so a render-and-compare
  step is still load-bearing even with a green suite.

  Also checked, and clean: nothing in this codebase already uses
  "disrupt"/"fix"/"block"/"turn" as a measure_type - the old stage-
  based pass's Disrupt/Fix mission-task conflation bug (see this
  batch's own comment in the source) has nothing left to collide with
  here.

  **Disrupt (270502) and Fix (270503) are deliberately NOT built yet.**
  Both templates show a fixed-proportion shape (Disrupt: a vertical
  spine with three perpendicular arrows, the top one longest, tip = PT3;
  Fix: a zigzag lightning-bolt from PT2 to an arrowhead at PT1) but
  neither draw-rules TEXT gives a numeric ratio for it - only one
  picture each. Measured off the template by pixel anyway (Disrupt's
  three arrow lengths came out roughly 257:145:77 px, an inexact ratio
  that reads as measurement noise off a scanned page rather than a
  clean intended fraction; Fix's zigzag os roughly flat-22%/zigzag-50%/
  flat+arrow-28% of its own total length) - but given this appendix's
  own repeated lesson that the maintainer's own description beats
  inferring a fiddly shape from a picture, these numbers are being
  held for confirmation rather than built silently.

  926 tests passing on both QGIS versions.

- **B5 complete: Turn rebuilt, Disrupt and Fix built** (2026-08-13),
  the maintainer's own read of all three after seeing Block/Turn's own
  first render.

  **Turn corrected first**: "turn is rendering in the opposite
  direction of the points, and the line is getting trimmed instead of
  being from PT1 to PT3." The true-90-degree-arc-with-a-side-selector
  reading was replaced entirely, in favour of their own dictated
  construction: "User clicks three points PT1, PT2 and PT3 - just
  connect the three with a curved line, something like a bezier curve
  from PT1 to PT3." Built as a quadratic Bezier, PT1 start, PT2
  CONTROL point (not a second endpoint), PT3 end - reusing
  `_quadratic_bezier_points()`, already in this codebase for Main
  Attack's own ribbon curve, rather than writing new curve math. The
  arrowhead moved from PT2 to PT3 to match, and its own generator
  wrapper (the bug fixed earlier the same day) carried over unchanged.

  **Disrupt**, in full: "user clicks three points PT1, PT2 and PT3;
  Connect PT1 and PT2, call it base. Draw an arrow from PT2 to PT3 -
  this arrow should be perpendicular to the base so Shift PT3
  accordingly to get a perpendicular. Draw another arrow from PT1
  parallel to the arrow PT2 to PT3, half of the length of PT2-PT3
  arrow. Now at the midpoint of base, draw another arrow parallel to
  the other two arrows, length adjusted such that the tip of the arrow
  is halfway as compared to the tips of the other two arrows from the
  base, extend the shaft below the base, length same as base to the
  tip of the arrow." Every number in that resolves cleanly: PT2's own
  arrow = the full perpendicular distance L; PT1's = L/2; the midpoint
  arrow's own tip = the average of the two, 0.75L, with a matching
  0.75L tail on the opposite side (confirms a pixel-measurement from
  the standard's own template that never made it into the build: the
  middle arrow's own line really does extend past the base, not a scan
  artifact). Two geometry generators - one for the whole thing (base +
  3 arrows, no arrowhead on the base), one scoped to just the 3 arrows
  (so the arrowhead marker's LastVertex placement can't also land one
  on the base's own final point, which sits exactly at Arrow A's own
  start).

  **Fix**, at the maintainer's own explicit request to deviate from
  the standard ("I know it is slightly different from what manual
  suggests, go with it"): "Draw a line segment followed by upright
  open triangle, inverted triangle - continue alternate triangles, end
  with a line segment, the length of line segment and the sides of the
  open triangle is the perpendicular distance between a line joining
  PT1-PT2 and PT3." One length, L, drives both the flat end-runs and
  each tooth's own two sides; the apex angle itself isn't dictated, so
  it borrows the 60 degree/equilateral proportions this project's own
  antitank wall/obstacle line "vee" tiles already settled on for the
  same shape - flagged as the one placement call in an otherwise fully
  numeric construction. Complete teeth are packed between two flat
  runs of at least L, any remainder split evenly so the pattern sits
  centred rather than jammed against one end. No arrowhead, unlike the
  standard's own template - the maintainer's own construction doesn't
  have one.

  946 tests passing on both QGIS versions. **B5 is now complete, all 4
  of Table H-XIX's own obstacle effects built** - this closes out
  H-XIX's line obstacles entirely (B4 + B5). B6 (bypasses, roadblocks,
  craters, gaps) and B7 (crossing sites) remain.

- **Fix gets a filled arrowhead at PT2** (2026-08-13, same day). The
  maintainer's own construction had deliberately dropped the standard's
  own arrowhead entirely; reviewing the render, they asked for it back
  in a different form: "just in case of Fix, end the line segment at
  PT2 with an arrowhead" and, immediately after, "filled arrowhead" -
  `QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHeadFilled`, unlike
  Block/Disrupt/Turn's own unfilled chevron. Same generator-wrapper
  pattern as every other B5 arrowhead, reading `mct_fix_geometry`'s own
  last point (PT2) rather than the feature's raw geometry.

  946 tests passing on both QGIS versions.

- **B6 built: Obstacle Bypass and the Roadblock family** (2026-08-13),
  all 8 of Table H-XIX's own bypasses/roadblocks (pages 578-581,
  identified by the maintainer directly from the printed page numbers
  after B4/B5 closed out). Unlike B5, every one of these has a fully
  numeric draw rule, so all eight were read straight off the standard
  rather than waiting for a dictated construction, at the maintainer's
  own direction ("build from the standard now").

  **Obstacle Bypass Easy/Difficult/Impossible (270601-270603)**: PT1/
  PT2 are the two arrow tips, PT3's own perpendicular distance from
  the PT1-PT2 line sets both the rear line's offset and the arrows'
  own length - the same `_perpendicular_projection` helper B5's Block/
  Disrupt/Fix already established. The three variants differ only in
  the rear line's own decoration: Easy is plain, Difficult is a
  "spring" zigzag bulging toward PT3, Impossible replaces the rear
  line entirely with two independent hook stubs (no line spanning the
  opening - the standard's own template shows it fully closed off at
  each end, not bridged). BLACK, not green, per the module's own
  audit - the one line-obstacle family that overrides the default
  outright. The zigzag's amplitude and the hooks' own stub/tick
  lengths have no numbered draw rule (same situation as Fix's own
  teeth in B5) - built to a reasonable, documented proportion and
  flagged for the maintainer's own render review, same as every
  ASSUMED entry in this batch.

  **Bridge or Gap (271100)**: the first four-anchor-point line this
  project has built - "points 1 and 2 define one side of the gap and
  points 3 and 4 define the opposite side," drawn as two independent
  plain lines. The standard's own template also shows small flared
  hook end-caps on all four endpoints, whose proportions the draw
  rules never number - skipped here, the same call already made for
  Overhead Wire's own tower icons, addable later if wanted. BLACK,
  with Field T (a freeform "W - W1"-style designation, same mechanism
  Obstacle Line already uses).

  **The Roadblock family (271201-271204)**, GREEN: three "state"
  variants share one construction - "points 1 and 2 determine the
  centerline... point 3 determines its width" - a main line on PT1-PT2
  with an arrowhead at PT1, and a second line parallel to it, offset
  toward PT3 by PT3's own perpendicular distance. Planned (271201)
  dashes both lines; Explosives State of Readiness 1/Safe (271202)
  keeps the main line solid and dashes only the parallel one;
  Explosives State of Readiness 2/Passable (271203) is fully solid -
  fixed per variant, not status-driven, since the variant itself
  already encodes a real-world readiness state rather than present/
  planned. **Roadblock Complete/Executed (271204)** breaks from the
  other three: its own template shows an "X" rather than two parallel
  lines, read as one line from the parallel position's own PT2-side
  end up to PT1 (arrowhead) crossing one from the parallel position's
  own PT1-side end down to PT2 (arrowhead) - marked ASSUMED, not
  CONFIRMED, since this was read off the picture rather than a
  numbered rule, and the standard's own scan is ambiguous about
  whether the real symbol doubles this X (flagged for the maintainer's
  own review).

  966 tests passing on both QGIS versions. **B6 is now complete, 8 of
  8.** Only B7 (water crossing sites and the remaining lines) is left
  before H-XIX's line obstacles close out entirely.

- **B6 corrected across all three families** (2026-08-13, same day),
  from the maintainer's own review of the first render. Seven changes,
  and the pattern in them is worth recording: **every single one was a
  place the standard's own draw rules were silent and the first build
  guessed**, which is the same lesson B4 and B5 each produced
  independently. Where the rules were numeric, the first build was
  right; where they weren't, it was wrong every time.

  **Obstacle Bypass Difficult**: "from the arrows, initially start
  with a small line segment, the zig-zag, then another line segment to
  connect with the next arrow base" - the zigzag had spanned the whole
  rear line, and now sits between two flat runs that reach the arrow
  bases. Plus "make the teeth closer ie the angle of the teeth should
  be more acute (reduce by 50%)" - amplitude halved (0.4 to 0.2 of
  PT3's own perpendicular distance), which sharpens each tooth's own
  apex at a fixed pitch.

  **Obstacle Bypass Impossible**, two corrections, the second of which
  exposed a real bug: "reduce the distance between the stubs by 30%"
  (stub ratio 0.25 to 0.325, so the gap between the two hooks' own
  ends drops from 0.5 to 0.35 of the symbol's height) and "the center
  or middle of the stub should touch the perpendicular, presently the
  end is touching." The first attempt at that second one centred the
  tick by shifting the ELBOW sideways - which silently turned each
  stub into a diagonal, since the stub and tick were one 3-vertex
  polyline. **Caught by the render, not the test** (the numeric test
  written alongside it asserted the same wrong model). The tick meets
  the stub in a T, which no single polyline can trace, so the function
  now returns FOUR parts - two stubs, two ticks - and carries a test
  pinning the stubs straight.

  **The Roadblock family**: "roadblock planned - there is no arrow,
  and it is a set of two parallel lines, dashed" - the first build had
  given all three state variants an arrowhead; Planned now has none,
  Readiness 1 and 2 keep theirs. Readiness 1 and 2's own dash
  patterns were already right and confirmed unchanged.

  **Roadblock Complete** was the substantive mis-read: "add another
  set of parallel lines of same dimensions at 50 deg angle to the
  first set." The first build had read the standard's own template as
  a single X built from the main/parallel pair's own DIAGONALS - the
  maintainer's wording makes clear the first "set" is the same
  main-plus-parallel pair every other roadblock variant draws, and
  the second is a rotated copy of it, so the symbol reads as two
  parallel PAIRS crossing. That is what the template actually shows;
  rendering the diagonal reading made it obvious (it came out as a
  four-armed star). Arrowheads are now scoped to a separate
  `mct_roadblock_complete_mains` so only the two main lines carry one.

  **Bridge or Gap** was rebuilt outright: "user will click only two
  points PT1 and PT2, make two parallel lines and require unique
  designation Field T, so the gap between the lines will be slightly
  more than the text, wings or flares at both ends, outwards at
  30deg." PT1-PT2 is now the CENTRELINE, not one side of a four-point
  gap, and the two drawn lines straddle it - so the symbol went from
  four clicked anchor points to two. The flares the first build had
  deliberately skipped as unnumbered are now in, at the maintainer's
  own 30 degrees. Field T became a HARD field constraint
  (`ConstraintStrengthHard`, the same mechanism the Maritime Points
  layer's own group/entity pair uses) - the first line obstacle where
  a designation is mandatory rather than optional. One honest
  limitation recorded in the code: "slightly more than the text"
  cannot be measured from geometry alone (no text metrics available in
  a geometry generator), so the channel is a fixed fraction of the
  centreline's own length - scale-invariant like Mine Cluster's 1/3
  and Trip Wire's 1/5, but not literally text-fitted.

  978 tests passing on both QGIS versions.

- **B6's second correction round** (2026-08-13, same day), and the one
  that finally settled the arrowhead question. Six more items, two of
  which turned out to be real bugs hiding behind green tests.

  **The roadblock arrowheads were never in the standard at all.** The
  maintainer reported them still drawing on Readiness 1, Readiness 2
  and Complete after the previous round had removed only Planned's.
  Re-reading the table's own TEMPLATE column settles it: the "PT 1 ->"
  / "PT 2 ->" / "PT 3 ->" arrows there are ANNOTATION POINTERS naming
  anchor points, used that way throughout Appendix H, and the EXAMPLE
  column - which renders the real symbol - shows plain lines with no
  arrowhead anywhere. **This is the third time this exact misreading
  has shipped in this project** (Light Line's invented perpendicular
  tick in H2, then Boundary's, now all four roadblocks), and the
  maintainer has caught it every time. All four variants now draw no
  arrowhead; `mct_roadblock_complete_mains`, which existed only to
  scope them, is deleted.

  **Obstacle Bypass Difficult's teeth** are now derived rather than
  drawn to a fixed count: "the teeth angles are too wide, reduce the
  angle to 30 deg, making the teeth closer and more in number." The
  apex angle is the specified quantity, so it became the INPUT - a
  tooth alternates between the rear axis and a peak `amplitude` out,
  giving an apex of 2*atan(step/amplitude), so pinning that at 30
  degrees fixes step = amplitude * tan(15 degrees) and the count falls
  out of however much rear line there is to fill (rounded even, so the
  zigzag lands back on the axis). The first build had it backwards -
  it fixed the count at 6 and let an ~83-degree apex fall out, which
  is exactly why it read as "too wide".

  **Obstacle Bypass Impossible's stub gap** was reduced 30% again,
  compounding on the previous round's 30%: 0.5 -> 0.35 -> 0.245 of the
  symbol's height.

  **The arrowhead now scales with the drawn obstacle**: "the arrow
  head dimension remains same whether i draw a small obstacle or big
  ... arrowhead should also become small if the lines are small, upto
  the current size which will be the max." The marker is now sized in
  MAP UNITS as a fraction of its own arrow's length, capped at the
  previous fixed 6mm through `QgsMapUnitScale.maxSizeMM` - so it
  tracks the symbol and tops out where it used to sit. **The first cut
  of this silently did nothing**, and is worth recording: the size
  expression called a helper that used `asPolyline()`, but this
  property is evaluated on a marker nested inside a geometry
  generator, where `$geometry` is the GENERATED geometry (the two
  arrows, a MultiLineString) rather than the feature's raw points -
  and `asPolyline()` RAISES on a MultiLineString rather than returning
  empty, so the property errored, QGIS fell back to the static size,
  and every arrowhead rendered identically. The helper now accepts
  either form (each generated arrow part runs rear -> tip, so its own
  length is the same number), and carries a test that evaluates it
  against the generated geometry specifically. This is the same
  generator-context trap as Turn's arrowhead in B5, in a third guise.

  **Bridge or Gap's designation** moved from below the symbol into the
  channel between its two parallel lines ("the text is below the line
  - it should be within the parallel lines") - the clicked geometry
  the label follows IS that centreline, so it only needed an on-line
  placement, data-defined so Obstacle Line keeps its below-line one.
  **This shipped broken once too**, for a reason worth knowing: the
  `LinePlacementOptions` data-defined property takes QGIS's own
  two-letter codes (`OL`/`AL`/`BL`/`LO`), and a readable spelling like
  `on_line` is silently accepted and simply drops the label. The
  string-comparison test written alongside it passed while Bridge or
  Gap rendered with no designation at all; it now asserts the tokens
  against the list QGIS itself publishes in the property's own help
  text.

  984 tests passing on both QGIS versions. **B6 remains complete at 8
  of 8**; B7 (water crossing sites and the remaining lines) is all
  that is left of H-XIX's line obstacles.

- **B6's last two Bridge or Gap adjustments** (2026-08-13, same day) -
  "all others are fixed", closing the batch out.

  **Field T went from mandatory to required**: "you have made field T
  mandatory, not required." The previous round had used
  `ConstraintStrengthHard`, which BLOCKS the save outright - the right
  strength for the Maritime Points layer's own group/entity pair,
  where a mismatched pair renders the wrong symbol, but too strong
  here, where a missing designation only means an unlabelled bridge.
  Now `ConstraintStrengthSoft`: the form flags the field, the feature
  still saves. Verified as BEHAVIOUR rather than as an enum value -
  a probe confirmed `validateAttribute()` reports the failure while
  `addFeature()` still succeeds, and the test asserts both, since the
  enum alone says only what was asked for, not what it does.

  **The channel widened 50%**: "the channel width needs to be adjusted
  to a minimum, present default width is too less, increase by 50%" -
  half-width ratio 0.12 to 0.18, so the gap between the two lines is
  now 0.36 of the centreline's own length.

  986 tests passing on both QGIS versions.

- **Bridge or Gap's cross-section moved off geometry entirely and into
  millimetres** (2026-08-13, same day), which retires the open
  channel-width question above rather than answering it. The
  maintainer, after both the 0.12 and the widened 0.18 versions: "keep
  the gap at a fixed unit rather than making it length of line
  dependent, as such it is a linear feature, so the width increasing
  with the length is not practical." Followed by the number: "make the
  bridge width 4.56mm, 6mm is too much."

  That is a design correction, not a parameter tweak, and it is right
  twice over. A linear feature's cross-section shouldn't scale with
  its length - and a millimetre channel also settles the text-fitting
  problem the previous entry had left open, because the label is
  millimetre-sized too, so the channel holds it at any zoom and any
  bridge length, which no ratio-of-length ever could.

  The structural consequence: **a geometry generator works in layer
  units and cannot see page units**, so none of the cross-section can
  be built there any more. `mct_bridge_or_gap_geometry` now returns
  the bare PT1-PT2 centreline (still trimming extra clicked vertices,
  which would otherwise bend the symbol), two line layers draw the
  parallel lines by offsetting it +/- 2.28mm via
  `setOffsetUnit(Millimeters)`, and each end cap's pair of 30-degree
  wings is a millimetre-sized rotating SVG marker on the first/last
  vertex. The two caps are mirror images because QGIS rotates a marker
  to the LINE's direction at both ends rather than reversing it at the
  start.

  One bug found by render on the way, worth recording as a class:
  **the flare glyph rendered as nothing at all** because it was handed
  `_AREA_OUTLINE_COLOR_EXPRESSION`, which is built from `color_rgb()`
  and evaluates to a bare `"0,0,0"` - correct for a QGIS colour
  property, silently invalid inside SVG markup, which wants
  `"rgb(0,0,0)"`. This module already had `_POINT_MONO_COLOR_EXPRESSION`
  for exactly this reason; the two are now not interchangeable by
  accident. A second, non-bug worth noting: at ordinary render DPI the
  flares looked inverted, and only a 400-DPI render showed they were
  correct all along - millimetre-sized detail needs the DPI raised to
  be judged at all.

  988 tests passing on both QGIS versions.

- **B7 built - water crossing sites, and Table H-XIX closes out**
  (2026-08-13). Seven measure types covering eight code rows: Bridge/
  Assault Crossing (271400 + 271300), Ford Easy (271500), Ford
  Difficult (271600), Lane (290600), Ferry (290700), Raft Site
  (290800) and Overhead Wire (282003).

  Following the lesson B6 taught the hard way, the unnumbered parts
  were put to the maintainer BEFORE building rather than guessed at,
  and all three answers changed the work:

  **Bridge and the Fords lost their third anchor point.** The standard
  gives all three a PT3 for channel width; the maintainer chose "fixed
  mm, 2 clicks" so they match Bridge or Gap. All four parallel-line
  symbols now share `_parallel_channel_symbol()` at a fixed
  `_BRIDGE_CHANNEL_MM`, differing only in dash, end wings and Ford
  Difficult's own midpoint zigzag (a millimetre-sized rotating SVG, for
  the same page-units reason as the bridge flares).

  **Assault Crossing is merged into Bridge**, not built separately -
  "assault crossing, merge it with the bridge i.e. just add the heading
  since it is same as bridge". Its template really is identical, and
  once Bridge lost PT3 so is its construction. `_B7_MERGED_CODES`
  records 271300 explicitly so a coverage check can tell a deliberate
  merge from a quiet drop, and a new whole-table test asserts every
  buildable LINE code is either built or recorded as merged.

  **Lane and Raft Site are deliberately identical.** Their templates
  AND their draw rules are word for word the same; the only difference
  in the entire table is that Lane carries the W/W1 amplifiers. Kept as
  two entries sharing one builder, with the decision pinned by a test
  so it does not later read as the duplication bug `TestWireObstacles`
  guards against.

  **Overhead Wire's pylons are the table's own Tower High (282002)**,
  not an invented glyph - which came directly from the maintainer
  asking "is there any sidc for tower?" rather than accepting a
  hand-drawn one. There are four tower SIDCs in the vocabulary; two
  (Tower Low 282001, Tower High 282002) are in this very table and
  already rendered by milsymbol from B1. Overhead Wire now builds its
  marker through the same `mct_build_sidc()`/`mct_sidc_svg()` pair the
  Points layer uses, at the same size, so the two drawings of the same
  real-world object cannot drift apart. A test asserts the entity
  resolves to a real glyph rather than the unknown icon - the defect
  class this module has already hit three times.

  Also useful, and the reason the arrowheads here are fixed-size:
  Lane, Ferry and Raft Site all say the symbol "varies only in length",
  which is the standard's own way of stating exactly the principle the
  maintainer applied to the bridge channel.

  **The whole B7 family defaults to BLACK, not the table's usual
  green** - "b7 all default colour black not green", the maintainer's
  call on reviewing the batch. It is a sensible distinction: the green
  marks obstacles, and a crossing site is the opposite of one. Lane was
  already black in the original B0 audit; the other seven now match it.
  Pinned twice over - by code in the audit test, and as a rule about
  the BATCH, so a later addition to B7 cannot quietly come back green.

  1002 tests passing on both QGIS versions. **Table H-XIX is now
  COMPLETE - all seven batches, B1 through B7**, across four layers
  (Points, Areas, Minefields, Lines). Mini-Phase H15/H16 is done;
  H17 (Table H-XX, Field Fortification) is next.

- **B7's smoke-test corrections** (2026-08-13, same day) - five items,
  one of them a symbol that had been rendering as garbage.

  **Overhead Wire's towers were not drawing at all.** The marker built
  its SIDC from `"affiliation"` and `"status"` READ OFF THE LINES
  LAYER - but that layer's affiliation vocabulary includes, and
  defaults to, `"unspecified"`, which `mct_build_sidc()` rejects: it
  returns an error STRING rather than a SIDC, so every tower rendered
  as nonsense. Structural glyphs have no business reading an
  affiliation (their colour comes from the obstacle colour expression),
  and the mine glyphs already had this right with a fixed
  `_MINE_GLYPH_AFFILIATION` literal - this now follows them. **The unit
  test could not have caught it**: it asserted the expression STRING
  contained the entity name, which it did. Only the render showed the
  output was an error message.

  **The pylon is now Land Installation's Telecommunications Tower
  (121203)**, the maintainer's own pick over this table's Tower High
  (282002). Note the symbol set has to travel with the entity - 121203
  is a `land_installation` code, and building it against
  `control_measure` yields a valid-looking SIDC for the wrong symbol.
  It also renders FRAMED, so `mct_sidc_svg()` gained an optional 6th
  argument to draw the icon without milsymbol's frame (defaulting to
  framed, so no existing caller changes); a framed installation box at
  every vertex is not the bare pylon the template draws.

  **And a tower now sits on EVERY vertex**, not just the two ends -
  "it should not be restricted to 2 points - a multi-segment line will
  have a tower at every point/vertex". The standard's own draw rules
  say the same ("additional points can be defined to extend the line")
  and its example picture shows a three-tower run with a bend. This is
  the one crossing symbol that draws the feature's OWN geometry rather
  than the shared first-two-points centreline, which would have thrown
  away every vertex past the second.

  **Lane and Raft Site became one entry.** They had shipped as two
  entries sharing a builder; the maintainer folded them together like
  Bridge/Assault Crossing - "since same construction, put them in one
  option itself". `_B7_MERGED_CODES` records 290800 alongside 271300.

  **The open ends were pointing the wrong way.** Lane/Raft Site's ends
  are not arrowheads: they OPEN outward, vertex on the line's own end
  and both arms splaying away, which the maintainer drew as
  `>-----<`. The first build had an arrow pointing outward instead.
  Since QGIS's ArrowHead glyph points ALONG the rotation direction,
  getting this right means spinning the LAST vertex 180 degrees rather
  than the first - the exact opposite of Ferry, whose filled heads are
  real arrows and do point outward.

  **The Fords' dashes doubled** - "increase length of dashes by 2
  time" - off Qt's own [4, 2]-pen-width default, the same traceable
  baseline Mine Cluster's custom pattern uses. Only the dash was
  doubled; nothing was said about the gap.

  One process note: a new test segfaulted the interpreter by chaining
  `_ferry_symbol().symbolLayer(...)` - the temporary's C++ object is
  collected mid-expression. That trap is already recorded in this
  project's own gotchas from three earlier hits, and it applies to
  symbols exactly as it does to `QgsPalLayerSettings`.

  1005 tests passing on both QGIS versions.

- **Overhead Wire's pylon replaced with the maintainer's own drawing**
  (2026-08-13, same day). They supplied it as SVG - mast, crossbar with
  downturned ends, two splayed legs, an internal brace, a lower V brace
  and a diagonal support - and it is used verbatim, with only the
  stroke colour parameterised so the pylon follows the obstacle colour
  field like every other glyph in this table.

  This retires the borrowed SIDC glyph entirely, and with it a whole
  class of problem: Land Installation's Telecommunications Tower
  (121203) rendered correctly once its affiliation bug was fixed, but
  it is an INSTALLATION symbol, so it arrived with a frame that had to
  be stripped and an installation indicator bar that could not be. A
  drawn glyph has no SIDC, so no symbol set to keep straight and no
  affiliation to get wrong.

  Two sizing details worth keeping: the tower is **6mm TALL**, the
  maintainer's own figure, but **QGIS sizes an SVG marker by its
  WIDTH** - and the glyph's viewBox is 100x160, so the marker is
  3.75mm. That is DERIVED from the viewBox rather than written down
  separately, because a viewBox and a hand-copied multiplier drifting
  apart is a mistake this module has already made once (the
  double_cross wire glyph). And the pylon is **centred on the clicked
  vertex** - "the tower center should be the vertex point clicked by
  user i.e. pt1 pt2 etc". A first cut offset it downward so the wire
  met the crossbar, which looked right but silently moved the anchor to
  the top of the tower; an SVG marker centres on its own point, so the
  correct answer was no offset at all.

  1005 tests passing on both QGIS versions.

- **Mini-Phase H17 - Table H-XX (Field fortification) built**
  (2026-08-13). Six entries over printed pages 603-605, in two new
  layers, and the first table since H-XIX opened that needed no
  correction round on its own construction.

  **Points (4)** - Shelter (280900), Above Ground Shelter (281000),
  Below Ground Shelter (281100), Fort (281200). All four already
  existed in `sidc.py` and are RELOCATED here out of the shared
  `control_measure_points.py` layer, the same move Tables H-VI, H-IX,
  H-XIII and H-XIX's own points already made. Each was verified to
  render a real glyph through milsymbol BEFORE the module was written,
  rather than after - the "present in sidc.py but renders as the
  unknown icon" defect has cost this project three debugging rounds.

  **Lines (2)** - Fortified Line (290900), a crenellated rampart tiled
  along however many anchor points the user clicks, and Fortified
  Position (291000), whose two points are its front corners with a leg
  trailing back from each.

  **Colour is affiliation, not green.** The green is H.5.21.1's own
  explicit exception for obstacles; H.5.22 claims nothing like it, so
  this table takes ordinary H.5.3 colouring.

  Both lines say their symbol "varies only in length" - the standard's
  own way of saying the CROSS-SECTION is fixed, which is exactly the
  principle the maintainer applied to Bridge or Gap. So both
  cross-sections are fixed MILLIMETRES and neither is generated
  geometry: Fortified Line is a tiled glyph, and Fortified Position is
  a two-point front bar plus a millimetre leg glyph on each corner.

  **Three things the standard does not number**, built as this pass's
  own call and flagged for smoke test rather than presented as read off
  the page: the rampart tile's size and merlon proportions; Fortified
  Position's leg depth; and **which side the front faces**. That last
  one matters most - both entries carry only a "typically faces/points
  toward enemy forces" note, which two anchor points cannot express.
  Both templates draw the front on the LEFT of PT1->PT2 travel, so
  that is the convention used for both, consistently.

  **A stale leftover from B4 fixed in passing**: Abatis was still
  offered as a POINT on the shared Control Measure Points layer, though
  B4 built it as a line and its own code comment said "B4 removes it
  from here". It never did. Abatis is now offered only as a line, and
  the shared layer's coverage test grew an explicit
  `_NOT_POINT_ENTITIES` exclusion so a line entity can no longer hide
  in a points dropdown unnoticed.

  1019 tests passing on both QGIS versions.

- **Mini-Phase H18 - Table H-XXI (CBRN defense), POINTS built**
  (2026-08-13). 18 of the table's 27 rows; the other nine are areas
  and lines and are audited but deliberately not built - see below.

  **The split is a real seam, not an arbitrary stopping place.** Every
  one of the 18 point codes (281300-281809) is backed by a real
  milsymbol icon, checked entry by entry against milsymbol's own
  `src/numbersidc/sidc/control-measure.js` rather than inferred from
  the code prefix. NONE of the nine area/line codes (271700-272200)
  is, which is exactly what you would expect - milsymbol has no line or
  polygon support, so every line and area in this appendix has always
  been hand-built. So the points are mechanical and the areas are new
  drawing work, and the table divides precisely there.

  Four of the 18 (Chemical/Biological/Nuclear/Radiological Event) were
  already in `sidc.py` and are RELOCATED off the shared Control Measure
  Points layer with the rest of their table; the other **14 are new
  vocabulary**. All 18 were then rendered and checked to be real,
  distinct glyphs - a batch that adds 14 entities at once gives the
  "present in sidc.py but renders as the unknown icon" defect fourteen
  chances to slip in.

  **One quirk pinned rather than left to be reported as a bug**:
  Nuclear Event (281500) and Nuclear Fallout Producing Event (281600)
  are two codes the standard names and numbers separately but that
  milsymbol draws with the SAME icon. A test asserts that this is the
  ONLY glyph collision among the 18, so the known case is recorded and
  any accidental one still fails loudly.

  **The nine unbuilt rows, and what each needs.** The seven
  contaminated areas share one construction - freeform outline of 3+
  points, yellow hatched fill, and a centred inverted-triangle glyph
  carrying a letter (B/C/N/R) with an optional "T" beneath for the
  Toxic Industrial Material variants. Outline, fill and anchor rules
  are all fully specified; **the triangle glyph's own proportions are
  not, and it does not exist in milsymbol**, so it has to be drawn.
  That is the single open question, and on this appendix's own track
  record it is worth asking about rather than guessing at. Minimum Safe
  Distance Zone (272100) is the one of the nine that IS fully numbered
  - a centre point plus a radius point - and could be built without
  asking anything. Radiation Dose Rate Contour Line (272200) is a
  plain line with a dose-rate label at each end, the same shape as
  Boundary's own labelling from H0. All nine are recorded in
  `cbrn_defense.py`'s own TABLE_H_XXI_REMAINING, and a test asserts
  18 + 9 = 27 so the gap cannot quietly become a loss.

  1026 tests passing on both QGIS versions.

- **H17 and H18's own menu items were dead on arrival** (2026-08-13,
  same day), found by the maintainer's first restart of QGIS for the
  smoke test - both `add_field_fortification_points_layer()` and
  `add_cbrn_defense_points_layer()` called
  `add_single_domain_point_layer(iface, name, create_fn)`, but that
  helper's own signature is `(iface, name, symbol_set, entity_labels,
  default_entity, ...)`. A plain `TypeError: missing 2 required
  positional arguments`, raised the moment either menu item was
  clicked. Both now call `add_layer_if_absent(iface, name, create_fn)`
  instead - the same guard-and-insert, but it takes the FACTORY, which
  is what these two modules wanted all along and what
  `field_fortification.py`'s own Lines layer was already doing three
  functions further down. Every other caller of
  `add_single_domain_point_layer()` was checked and passes the right
  arity.

  **Why 1026 green tests missed it.** Both modules' tests built their
  layers through `create_*()` exclusively; neither ever called the
  function the menu item is actually wired to, so an arity error in
  the one line between them was invisible. Fixed at the root, not just
  patched: `TestFieldFortificationLayerInsertion` and
  `TestCbrnLayerInsertion` now call each `add_*_layer(iface)` for real
  through the shared `FakeIface`, asserting one layer lands and a
  second click warns instead of replacing - the same pair of tests
  every older layer module has had all along, and precisely why none
  of them shipped this bug. 1031 tests passing on both QGIS versions.

- **Table H-XIV reopened: four maritime defects from the maintainer's
  own review** (2026-08-13, same day). Two turned out to be general
  rendering bugs living in `symbol_engine.py`, not maritime bugs at
  all, and both are fixed at the root so every appendix benefits.

  **1. Qt's SVG renderer silently ignores `dominant-baseline`.** Probed
  directly through QSvgRenderer: the same `<text>` rasterises
  pixel-for-pixel identically with and without the attribute. Every
  label milsymbol means to CENTRE on its own `y` was therefore sitting
  with its BASELINE there, about 0.26 em too high. On most icons that
  reads as slightly-off; on any icon that puts a letter just under a
  centre dot it is a collision, which is how it surfaced - Reference
  Points' Corridor Tab "C", Data Link "D", Marshall "M", Enemy "ENY"
  and the rest all printed ON the dot ("touching the dot in center
  making it unreadable"). `_apply_dominant_baseline()` now bakes the
  shift into `y` before the SVG ever reaches Qt, using half the font's
  own x-height as SVG defines that baseline - measured from Qt's own
  metrics rather than hardcoded, since macOS substitutes Helvetica for
  Arial. The attribute is left in the markup so it still says what it
  means to a renderer that honours it. Re-rendered the obstacle points
  and the airspace points as well: letters that were high in their
  boxes are now centred, nothing regressed.

  **2. milsymbol's declared bbox is wrong for six of the sixteen
  sonobuoys.** 213510-213515 (Expired, Kingpin, LOFAR, Pattern Center,
  Range Only, VLAD) declare `x1:40 x2:160`, a 128-wide box, for content
  that is the same circle r=40 at (100,100) every other sonobuoy draws
  - genuinely 80 wide, and correctly declared as such for
  213500-213509. QGIS sizes an SVG marker by its WIDTH, so those six
  rendered ~31% smaller than the ten beside them: the maintainer's
  "these symbols are smaller than others significantly", and their list
  matched the six exactly. `_VIEWBOX_CORRECTIONS` now swaps in the
  family's own box. The correction has to widen back out over any
  amplifier text, and that is not optional - Table H-XIV's own sonobuoy
  examples hang the T and H fields OUTSIDE the circle ("99", "HOT",
  upper right), and a first cut that swapped the bare icon box in
  clipped a unique designation clean off, caught in a render. The text
  extent is measured with the same Qt font machinery that will draw it.

  **3. The six harbour entries moved to Surface Stations.** A
  deliberate departure from the printed table, at the maintainer's
  request. The standard really does print Harbor (212800) and the five
  Harbor Entrance Points under its own "Sub-Surface Warfare" rule -
  checked on the page image, there is no intervening heading - but a
  harbour and its entrance points are surface features and the group
  here is a menu, not a citation. Codes and glyphs untouched.

  **4. The two station groups are NOT duplicates - the names were.**
  Reported as "a lot of underwater symbols repeated or are populated
  here ... remove duplicates". They are not duplicates: Subsurface
  Stations (214900-215500) and Surface Stations (215600-217000) are
  separate codes and milsymbol draws them differently - dashed line
  above and solid below for subsurface, both solid for surface -
  verified entity by entity in a render and now pinned by a test that
  asserts on the GLYPH, not the name. What was wrong was our own
  labelling: every station name carried an invented "Sea" ("General
  Sea Surface Station" for the table's own "General Surface Station"),
  and two were wrong outright - 216800 is "Remote Multi-Mission
  Vehicle Unmanned Underwater Vehicle Surface Station", not "...Mine
  Warfare Unmanned Underwater Sea Surface Station", and 216900 has no
  "Mine Warfare" in it at all. That padding is exactly what made the
  two groups read as each other's duplicates. All 22 station names are
  now the table's own CONTROL MEASURE column verbatim, entity keys
  included; the one name the table really does spell with "Sea" is
  Replenishment at Sea Surface Station, and a test says so. Nothing was
  deleted - deleting five real codes on the strength of a misleading
  label would have been the actual defect.

  1041 tests passing on both QGIS versions.

- **H-XX and H-XXI smoke-tested; five defects fixed, two of them in the
  shared point-layer builder** (2026-08-13, same day).

  **Fortified Line started at PT1 with a merlon.** The rampart tile put
  its whole gap AFTER the merlon, so the very first tile rose straight
  out of PT1 while the last one trailed a level run into PT2 - and
  Table H-XX's own template starts with that level run too. It is not
  decoration: "that line segment actually determines which way the
  ramparts are pointing." The gap is now split across the tile's two
  ends (`M 0,50 L 25,50 L 25,12 L 75,12 L 75,50 L 100,50`), so the
  merlon is still 50 wide with 50 of gap between merlons - the same
  rhythm already signed off, moved by a quarter tile in phase.

  **Fortified Position's legs did not draw at all** on a real map,
  though they rendered fine in the offscreen harness - the front bar
  plus two legs held at a fixed millimetre depth by a rotated SVG
  marker. Rather than chase it, the maintainer called for the
  construction Table H-XIX's Obstacle Bypass Easy already uses and this
  codebase already trusts: three anchor points, PT3's own perpendicular
  distance setting the depth, plain ends where Bypass draws arrowheads.
  That swaps the standard's own anchor roles - it calls PT1/PT2 the
  front corners, i.e. the ends of the bar - and the maintainer took
  that knowingly ("the user can figure out how to make it correctly").
  The bracket that comes out is the same either way; only which point
  is clicked first changes. `mct_fortified_position_front` and
  `mct_fortified_position_leg_svg` are gone with the old construction.

  **The Lines layer offered a null measure_type** no other menu in the
  appendix shows, because it was the one lines/areas layer that never
  set a default value on that field, so a new feature started NULL and
  QGIS added its own null entry.

  **Table H-XXI's events render at barely half their siblings' scale**
  - milsymbol's box for each event is a wide, low 158x118 where each
  decontamination point is a narrow, tall 88x168, and QGIS sizes an SVG
  marker by its WIDTH. Scaled up 30%, the maintainer's own number;
  matching the decon points' drawn scale exactly would be about 80%, so
  this is a legibility call rather than a normalisation and is theirs
  to revisit. Needed a new opt-in `entity_marker_size_scales` on the
  shared point-layer builder, which had only ever had one size per
  layer.

  **Field T never reached the symbol on ANY layer built through the
  shared builder.** Its renderer called `mct_sidc_svg(mct_build_sidc(
  ...))` with no text argument, so `unique_designation` was collected
  in the attribute table and drawn nowhere - the exact defect the
  maintainer found on 2026-08-10 in `c2_measures.py`,
  `defensive_control_measures.py` and `control_measure_points.py`, each
  of which carries its OWN SIDC expression and was fixed there while
  this shared one was missed. Fixed at the root, so every appendix
  layer gains it. milsymbol's `uniqueDesignation` is the right slot
  here, probed rather than assumed: it places the text to the RIGHT of
  the box, where Table H-XXI's template puts T, while
  `uniqueDesignation1` places it INSIDE, which is the template's own
  T1. One icon, Biological - Toxic Industrial Material (281401),
  defines no designation slot at all despite the table drawing a T on
  it; passing one is a harmless no-op.

  **Found while fixing the above, not reported**: the shared Control
  Measure Points layer still defaulted its entity to `'shelter'` after
  H17 moved Shelter out to `field_fortification.py`, so a freshly
  digitized point landed on an entity its own dropdown no longer
  offered. `tests/test_point_layer_affiliations.py` exists precisely to
  sweep that class of bug and missed this one twice over: it checked
  only that each default RENDERS, and `'shelter'` is still perfectly
  real vocabulary in `sidc.py`; and its layer list had never been
  extended to the H-XX and H-XXI Points layers at all. Both gaps
  closed - the sweep now asserts every default is an option that layer
  actually offers, and covers all ten Points layers. Verified by
  reintroducing the bug and watching the new test fail on it.

  1049 tests passing on both QGIS versions.

- **Second H-XX/H-XXI review round** (2026-08-13, same day).

  **Fortified Line's corners.** A marker line lays each tile down
  straight and rotated to the local bearing, so a tile spanning a bend
  is drawn across it - a notch outside the corner, an overlap inside.
  Two tempting fixes are both wrong and were ruled out before building:
  a plain line under the whole profile would close every merlon into a
  box (the standard's template is a bare square wave, no baseline under
  a merlon), and generating the profile as real geometry needs page
  units inside a geometry generator, where `@map_scale` is confirmed
  not to behave - re-probed here rather than taken on trust, since
  `offensive_control_measures.py` had already paid for that lesson
  once. So the connector goes only where it is needed:
  `mct_rampart_connector_svg()` at InnerVertices, half a tile long.
  A full tile was tried first and reached far enough to close the
  merlon sitting on the corner; half bridges the joint and stops.

  **The end runs are doubled**, as asked. A quarter of that comes from
  the tile's own ends and cannot grow without changing the merlon
  rhythm already signed off, so the tiling is pushed a quarter tile
  inward (`setOffsetAlongLine`) and the same connector glyph fills what
  it vacates, at FirstVertex and LastVertex.

  **An icon no longer shrinks when Field T is typed into it.** The new
  `unique_designation` wiring exposed the other half of the bounding-box
  problem: milsymbol widens an icon's own box to take in its amplifier
  text, and QGIS sizes an SVG marker by WIDTH, so adding a designation
  visibly shrank the symbol it belonged to - "inconsistent from a UI
  point of view", and it was. New `mct_sidc_svg_width()` reports the
  width of exactly the SVG `mct_sidc_svg()` returns for the same
  arguments, and the shared point-layer renderer now scales the marker
  by amplified-width / plain-width. That cancels the shrink exactly:
  the icon holds its size and the text hangs outside it, which is how
  the standard draws amplifiers anyway. Applies to every layer built
  through the shared builder, not just H-XXI, and composes with the
  per-entity 30% event bump. Pinned by a test that measures millimetres
  of page per icon unit across five designation lengths.

  1053 tests passing on both QGIS versions.

---

### Mini-Phases H19, H20, H21 and H22 — Tables H-XXII to H-XXVII (2026-08-14)

Built at the maintainer's own instruction and to their own scope:
"complete the remaining tables H-XXII to H-XXVII - all the point
symbols derived from milsymbol.js". **37 point symbols across three
new layers**, and the boundary of that scope turned out to be the
standard's own, not a convenience - the audit that opened this pass
checked every code in all four tables against milsymbol's own
`src/numbersidc/sidc/control-measure.js` entry by entry, and the split
falls exactly where point symbols end:

| Table | Rows | Points with a milsymbol icon | Built |
|---|---|---|---|
| H-XXII (Sustainment) | 17 | 16 | **16** |
| H-XXIII (Supply points) | 37 | 18 | **18** |
| H-XXIV (Mission Tasks) | 29 | 3 | **3** |
| H-XXV (Intelligence) | 2 | 0 | 0 |

The rows with no icon are areas and lines - milsymbol has no line or
polygon support at all, so every one of those in this appendix has
always been hand-built here. Each module records its own unbuilt rows
by CODE (`TABLE_H_XXIII_REMAINING`, `TABLE_H_XXIV_REMAINING`), with a
test asserting built + unbuilt equals the printed table's own count so
the gap cannot quietly become a loss. Tables H-XXVI and H-XXVII are
abbreviation lists, not symbol tables, and Table H-XXV's two rows are
both lines.

**New vocabulary: the sixteen supply classes.** Table H-XXIII splits
them by standard, not just by number - 321701-321706 are the NATO
classes, each row citing its own STANAG 2961 definition, and
321707-321716 are the US classes I through X. They share roman numerals
and mean different things, so keys and labels both say which is which.
NATO Multiple Supply Class Point (321706) draws the same plain box as
General Supply Point, and that is the standard's own doing: its box
carries no icon, only a user-typed A field ("I/III/V", or "ALL"). Pinned
by a test as the only glyph collision among the 18, the same way Table
H-XXI's own 281500/281600 pair is.

**The shared Control Measure Points layer is retired.** It was always a
holding pen for point entities whose own table module did not exist
yet, and these three mini-phases took its last 21 entries - 16 to
Sustainment, 2 to Supply, 3 to Mission Tasks. Leaving an empty layer
behind would leave a dropdown nothing can populate, so the module, its
menu entry and its test file are gone.

**That retirement took two invariants with it, and both moved rather
than disappearing.** Eleven separate per-table tests each asserted "my
family left the shared points layer" - near-copies that could only ever
see two layers at a time - and one test asserted that every
control-measure entity was offered by SOME dropdown. Both are now one
file, `tests/test_control_measure_point_vocabulary.py`: a pairwise
sweep over all twelve point vocabularies, plus the union check.

**It found a shipped bug on its first run.** `special_point` and
`waypoint` were each defined TWICE in `sidc.py`'s control-measure
vocabulary - once for Table H-VI (131700/131800) and again for Table
H-XIV (213700/214800). A dict keeps the last one, so the two H-VI codes
were silently overwritten and **the C2 Measures layer had been drawing
MARITIME icons for its own Special Point and Waypoint**. The maritime
keys now carry that module's own `_reference` group suffix, the way its
Navigational Reference Point already did for exactly this reason. Five
further maritime entries (Distressed Vessel, Downed Aircraft, Iceberg,
Oil Rig, Sea Mine-Like Contact) were duplicated with the SAME code -
harmless, and removed.

1064 tests passing on both QGIS versions.

- **Mission Task Points bumped 30%** (2026-08-14, same day), on the
  maintainer's own instruction: "mission task points - increase size by
  30% like cbrn events". Same cause as Table H-XXI's own events, at the
  extreme end of it - all three icons are a wide, low pair of crossed
  lines whose milsymbol box is 208x128, the WIDEST in the entire
  control-measure set, so at one marker size they drew at 8/208 mm per
  icon unit against a supply point's 8/88: about 42% of the scale.
  Reused `entity_marker_size_scales`, added for the CBRN events, with no
  new mechanism. As there, worth being plain that 30% is a legibility
  call rather than a normalisation - closing the gap to the supply
  points outright would be about 136% - and the module says so. A test
  measures millimetres of page per icon unit and confirms the bump
  composes with the amplifier compensation, so a designation still does
  not resize the glyph.

  1067 tests passing on both QGIS versions.

---

### Table H-VIII: Contain and Retain built (2026-08-14)

The first two of the appendix's own 59 remaining symbols, and the first
of the "deferred because it needs computed geometry" family to actually
land. H4 put them off in 2026-08-09 as "procedural circle/arc
constructions [that don't] fit this module's one-polygon-one-symbol
pattern" - which was right, and is why they are built as **lines**, not
areas, on a new Defensive Control Measures (Lines) layer. Base Defense
Zone had already made that call for the same reason.

**Why they are buildable now when Weapon/Sensor Range Fan still is
not.** Every dimension the maintainer dictated is a FRACTION OF THE
RADIUS - tick length 1/3 (Contain) or 1/5 (Retain), spacing 18 and 15
degrees. Fractions are scale-free, so a geometry generator can produce
them in layer units; the standard's own rule instead ties tick length
to the echelon field's text height, a page unit that a geometry
generator cannot see (`@map_scale` does not resolve there - re-probed
again this session).

**Four corrections came out of the first render, all from the
maintainer.**

- **Contain's ticks point INWARD**, Retain's outward. Read off the
  template at 480 dpi to confirm.
- **Neither arrowhead is filled.** The only solid black triangles on
  either page are the annotation pointers to the "PT. 1"/"PT. 2"/
  "PT. 3" labels. That is the FOURTH time this appendix has confused an
  annotation pointer for geometry (Light Line, Boundary, B6's
  roadblocks, and now here), which is worth stating as a rule: a filled
  triangle in a TEMPLATE column is almost always a pointer.
- **Ticks are inclusive of both ends** - the first and last land
  exactly on PT1 and PT2. A half-step inset was tried first on the
  reading that the templates leave their ends bare; they do not.
- **"C" and "R" sit ON the perimeter and mask it**, rather than
  floating outside. That forced both letters to become LABELS: only
  the label engine can cut a real hole in the line it sits on, since a
  marker glyph has no QgsTextMaskSettings (established in
  offensive_control_measures.py). All three labels here - those two
  plus Contain's red "ENY" on its arrow shaft - therefore take a
  DATA-DEFINED position, because every one of them belongs on
  generated geometry rather than on the feature's own clicked points.

**One number where the standard contradicts itself.** Its DRAW RULES
say Retain's "opening will be a 30-degree arc", making the drawn arc
330 - but its own template and example both draw an opening nearer 60,
and the maintainer asked for 300. Two of the three agree, so 300 it is,
in a single constant with the disagreement recorded beside it.

The by-value-temporary segfault trap bit again on the way, in a test
chaining `layer.labeling().settings().dataDefinedProperties()`. Every
such accessor is now held in its own variable, and the test that hit it
says why.

**A second review round, same day**, took four more corrections:

- **Retain's last tick is dropped** - it sat under the arrowhead and
  read as part of it.
- **All three labels sat above their own point.** A data-defined label
  position anchors by the text's BOTTOM-LEFT corner, not its centre;
  Hali/Vali are the documented pair that fixes it, and QGIS only
  honours them when a fixed position is set. Worth knowing generally -
  every future data-defined label in this project needs both.
- **The mask has to bridge inter-letter spacing.** It follows each
  glyph's own outline, so at 0.6 mm the arrow shaft showed through the
  gap between "N" and "Y". Widened to 1.1.
- **The tick where each letter sits is left out rather than masked.**
  Both letters land exactly on a tick (180 degrees is a whole number
  of steps for both spacings). Masking the ticks was tried first and
  did not take, where masking the ARC does - so the tick is simply
  omitted, which is deterministic, needs no mask, and is what Retain's
  own template draws anyway.

**A third round settled the masking properly, and turned up a real
QGIS limit worth recording.**

**Selective Masking does not reach symbol layers inside a
QgsGeometryGeneratorSymbolLayer.** Probed both ways - referencing the
nested line layer's own id, and the generator's - and neither takes.
What had looked like a working mask on the arc turned out to be the
letter glyph simply covering it, same colour; the giveaway was that
masking ONLY the ticks still produced the same "gap". Every part of
Contain and Retain is generated, so masking could never have worked
here. `c2_measures.py`'s Boundary masks fine because its line is a
plain top-level symbol layer.

So the gap is cut into the GEOMETRY instead: the arc returns two parts
with a 14-degree gap at the letter, and the tick at that same angle
keeps its length but starts clear of the letter rather than at the
perimeter. **The tick is not dropped** - the manual does not drop it,
it hides the part the letter covers, which is what shortening
reproduces. That is also more faithful than a mask would be: it breaks
the line by a fixed amount of ARC rather than by whatever the glyph
happens to cover. "ENY" keeps its painted mask, which does work, since
the arrow is a single unbroken line.

One consequence caught in the render: a marker on the last vertex of
the now-two-part arc lands on the end of EACH part, putting a second
arrowhead beside the "R". The arrowhead rides on its own short
ungapped tail (`mct_retain_arc_end`) instead.

1089 tests passing on both QGIS versions.

### Table H-XXV: the Intelligence Coordination Line (2026-08-14)

The first of the six remaining line/area units, and the one that
closes an entire Appendix H section. **H.5.27 is two rows**: 300000
names the group and draws nothing (TEMPLATE and EXAMPLE both "N/A"),
and 300100 is the Intelligence Coordination Line. One symbol, printed
page 656, the whole section.

**Built to the maintainer's own instruction: "it is same as
battlefield coordination line or restrictive fire line in fire support
coordination measures, except for BCL or RFL, it will be ICL".** The
template picture confirms it exactly - a plain line carrying its
abbreviation plus Field T at both ends, above the line, with the
standard's own example reading "ICL EUSTIS": abbreviation first,
designation last, which is the NFL/BCL/RFL order and the opposite of
FSCL's own designation-first one.

So this is deliberately not a fresh construction. `intelligence_
control_measures.py` reuses the exact pattern
`fire_support_coordination_measures.py` already carries for that
family, down to the details that were only learned by rendering it:

- **AboveRight at the start vertex, AboveLeft at the end**, not a
  plain Above at both. Above centres the text ON the end vertex, so
  half of a long designation hangs off past the end of the line.
- **The label masks the line.** "Above" and "clear of the line" are
  not the same thing on a near-vertical run, which the render check
  here included on purpose - the mask is what keeps the text readable
  there.
- `trim()` on the label, so a blank designation gives "ICL" rather
  than "ICL " with a trailing space for the mask to cut a hole for.

**What is not drawn**: the two W-W1 boxes below the line (effective
times, Field W/W1) - this appendix's own standing tolerance of keeping
the abbreviation and dropping the extra descriptive info boxes, the
same call made for the whole Fire Support family. And the up-arrows at
PT1/PT2 in the TEMPLATE column are annotation pointers, not geometry -
the convention first confirmed for Light Line and since then for
Boundary, H-XIX's roadblocks and H-VIII's Contain/Retain arrowheads.

New layer and new menu entry, "Intelligence Control Measures", per the
one-layer-per-table convention. 1101 tests passing on both QGIS
versions; render-verified across designated/undesignated, all three
line colours, present and planned, a multi-vertex bend and a steep
diagonal.

**Five units, 54 symbols left in Appendix H.**

### Table H-XXIII: the designation moves to Field T1 (2026-08-14)

Smoke-test finding, and a real misreading of the table rather than a
placement nicety: **every template in Table H-XXIII puts the unique
designation INSIDE the supply box**, in the box labelled T1, and fills
it in its own examples - "1AD" on General Supply Point, "3SUST" on
NATO Class I, "55ORD" on NATO Class V. Field T on those templates is a
separate box outside the symbol to its upper right. This built them
all in T.

milsymbol exposes the T1 position as `uniqueDesignation1`, at (100,
20) against Field T's (150, -30) - established by probing all 18 icons
for which text options they actually define and where each one lands,
rather than by reading milsymbol's source, since its option NAMING
does not line up with the standard's own field naming or even with
itself across icons.

**Only 7 of the 18 move.** The probe's other finding is that not one
of the ten US class icons (321707-321716) defines `uniqueDesignation1`
at all - Field T is the only text position they have, which is exactly
why they read as correct in the smoke test. They keep it. A slot
passed to an icon that does not define it is a silent no-op, so
"fixing" those would have deleted their designation rather than moved
it; both directions are now pinned by tests.

The mechanism is a new opt-in `entity_designation_slots` on the shared
point-layer builder, mirroring `entity_marker_size_scales` next to it:
a per-entity CASE feeding both the symbol expression and the
size-compensation one. Every other layer is untouched.

**Still open on this table**: NATO Multiple Supply Class Point (321706)
defines NO text option whatsoever - not Field T, not T1 - so its box
draws bare. Its own template asks for A/A1/A2 (up to three supply class
numbers, or ALL) plus T1, and the maintainer has asked for that class
input. Being built next.

### Contain's "ENY" gap, and Table H-XXII moves to Field T1 (2026-08-14)

Two smoke-test findings, both corrections to work signed off earlier
the same day.

**"ENY" was still trying to use a mask that cannot work.** The
maintainer's report: "the ENY text on the shaft is not masked, so the
shaft is running through the text". When the "C" and "R" gaps were cut
into geometry on 2026-08-14, the conclusion recorded was that
Selective Masking "works on the arrow, and does not on the arc" - and
that was simply wrong. The arrow is a geometry generator like every
other line in both symbols, and QGIS cannot reach a symbol layer
nested inside one. There was never a case where the mask took; the
arrow's own render happened to look plausible.

So the arrow is now cut the same way the arcs are: two parts with a
gap at the shaft's midpoint, sized as a fraction of the RADIUS
(`_CONTAIN_ENY_GAP_RATIO`, 0.62) and clamped to half the arrow's own
length so a short arrow on a wide semicircle is not cut away
completely. **The arrowhead moved to its own ungapped tip segment**
(`mct_contain_arrow_head`) - a marker at LastVertex fires on the last
vertex of EVERY part, so on the split shaft it would have dropped a
second arrowhead at the gap. Exactly the bug Retain hit when its arc
was split, caught here before it shipped rather than after.

Every mask is now gone from this layer, along with the placeholder-id
machinery that re-stamped them - the module is honest that nothing
here can be masked.

**Table H-XXII's designations move to Field T1**, the same fix and the
same reason as Table H-XXIII's earlier today: every template draws the
designation inside the box, and the standard's own examples fill it -
"4077" under "AXP", "MNSE" under "ASP". 15 of the 16 move.

**Ambulance Exchange Point (320100) cannot be fixed here.** Its
template has a T1 box and its example fills it, but milsymbol defines
no text option for that icon at all - neither T nor T1 - so no slot
reaches it and its designation cannot be drawn. The same gap Table
H-XXIII's NATO Multiple Supply Class Point has. Both are pinned by
tests that will fail the day milsymbol grows one.

1108 tests passing on both QGIS versions.

### Two icons milsymbol draws no text on at all (2026-08-14)

The T1 work above turned up a harder case behind it. **NATO Multiple
Supply Class Point (321706) and Ambulance Exchange Point (320100)
define NO milsymbol text option whatsoever** - not Field T, not T1, not
anything. Both have amplifier boxes in their own templates that the
standard fills in its own EXAMPLE column ("I/III/V" over "ISAF";
"4077"), and both drew a bare box no matter what was typed.

So this plugin now draws that text itself, into the returned SVG,
under slot names of its own (`mctFieldA`, `mctFieldT1`) that
`render_symbol_svg()` intercepts rather than passing to milsymbol.
**Every coordinate is lifted from a sibling icon milsymbol does
define** rather than invented - 321706's two from 321701-321705 and
321700, 320100's from 320200 - which is what makes the result line up
with the icons beside it. Three details that had to come across with
them:

- **The baseline flag is per-slot.** milsymbol draws the class numeral
  with `dominant-baseline="middle"` and the T1 designation without it.
  Injection happens BEFORE `_apply_dominant_baseline()` runs, so each
  slot carries its sibling's own flag and gets the same treatment.
- **Colour is read off the rendered markup**, not resolved from the
  affiliation a second time - so injected text follows whatever the
  icon actually did, monoColor included.
- **Long text is shrunk to fit the box**, measured with the same Qt
  font machinery that will draw it. "I/III/V" at the sibling's own 45
  would overrun the frame.

**The class field itself stops at three classes, and that is the
template's own limit**: its A field reads A/A1/A2, three sub-fields, so
the dropdown offers every combination of one, two or three of the five
NATO classes in ascending order plus ALL - 26 options, and no
four-class one, because the symbol has nowhere to put a fourth.

The shared point-layer builder gained one opt-in `extra_text_field`
parameter for this. **One QGIS trap on the way**: the second amplifier
needs mct_sidc_svg's arguments 4 and 5 skipped, and skipping them with
NULL blanked the icon entirely - QGIS short-circuits a whole function
call to NULL the moment any argument is NULL. Empty strings, which the
function already reads as "not given".

1113 tests passing on both QGIS versions.

### Table H-XXI's decontamination points move to Field T1 too (2026-08-14)

The third and last table with this defect, and the one that had
already been signed off. Raised while fixing H-XXII and H-XXIII -
their supply/sustainment boxes are the same shape with the same T1
box - reported to the maintainer rather than changed unilaterally, and
applied on their instruction.

All ten decontamination points (281800-281809) put their designation
in Field T, outside and above-right of the box. Every one of their
templates draws it INSIDE, in T1, and the standard's own examples fill
it: "1/2COY" under Forward Troop Decontamination Point/Site's own "DCN
(F) T", "4CBRN" under Wounded Personnel Decontamination Site's "DCN W".

**The eight events are untouched, and that is a finding rather than a
skip**: they are a different icon family - a wide inverted triangle,
not the box - and milsymbol gives them exactly one text position, at
(40, 90) beside the triangle. There is nothing to move.

Worth recording that this table's own test asserted the WRONG
behaviour, explicitly: it checked the designation landed to the right
of the box, with a comment noting that uniqueDesignation1 "would have
put it inside the box, which is the template's T1". The test was
written to pin a choice that had never been checked against the
template. It now pins the template's own answer, plus the events'
single position.

Three tables, one defect, one shared mechanism
(`entity_designation_slots`). 1114 tests passing on both QGIS versions.

### Icon-size stability, for real this time; Retain settles at 330 (2026-08-14)

**The size fix shipped broken, and the reason is worth recording.** On
2026-08-13 the maintainer reported that a symbol SHRANK the moment a
unique designation was typed into it - QGIS sizes an SVG marker by its
width, and milsymbol widens an icon's declared box to take in its
amplifier text. That was fixed the same day, inside
`_point_symbol_layer.py`, as a private expression.

It was never engine-wide. **Seven modules in this appendix build their
own point renderer** rather than going through that shared builder -
c2_measures, airspace, maritime, obstacle, target, defensive and
offensive - and not one of them had the compensation. Reported again
2026-08-14 against Table H-VI's own Checkpoint and Contact Point:
"icon size changes in case of C2 measures points... icon remained same
in case of land units and land eqpt".

The compensation now lives in
`_control_measure_shared.stabilised_point_size_expression()` and every
point renderer in the project shares it, the builder included. Two
things it does that the private copy did not:

- **Derives BOTH widths from the module's own `mct_sidc_svg(...)`
  call** rather than taking them as separate arguments, so the
  amplified and plain widths cannot drift apart. The plain one is that
  call's `mct_build_sidc(...)` argument, extracted by counting
  parentheses - a regex stops at the first `)` inside a nested call,
  and every one of these expressions has several.
- **Guards the ratio** with `coalesce`/`nullif`. QGIS nulls a whole
  function call on any NULL argument, so one unset attribute would
  otherwise null the size expression and silently drop a per-entity
  multiplier back to the base size.

`tests/test_point_icon_size_stability.py` is the new guard: it sweeps
every point layer in the plugin, drives each one's OWN configured
defaults, and compares millimetres-per-icon-unit with and without a
designation. It imports its layer list from
`test_point_layer_affiliations` rather than restating it, so a new
Points layer cannot be added to one sweep and missed by the other. A
second test guards the guard - if no layer's box actually widened,
the first would pass for the wrong reason.

**Retain is now 330 degrees**, a 30-degree opening. Built at 300 on
the maintainer's own dictated geometry, then settled at 330 by them
after seeing it rendered: the standard's DRAW RULES text says the
opening is 30 degrees while its own picture draws nearer 60, and the
written rule wins. One constant.

1118 tests passing on both QGIS versions.

### Smoke test signed off: every built Appendix H symbol (2026-08-14)

The maintainer's own hands-on QGIS pass over everything built on
2026-08-13/14 is complete and clear. Tables H-VIII (Contain/Retain),
H-XIV, H-XX, H-XXI, H-XXII, H-XXIII, H-XXIV and H-XXV, plus the three
engine-wide changes that touch every milsymbol-rendered layer in the
plugin.

**Eight real defects came out of it, and the split is worth keeping in
mind for the units still to build.** Three were engine-wide rather
than table-local, and all three had shipped looking fine:

- Qt's SVG renderer silently ignores `dominant-baseline`, so every
  milsymbol label sat ~0.26 em too high.
- The unique designation was collected on every layer built through
  the shared point-layer builder and never passed to the symbol at all.
- The icon-size compensation reached only that same builder, leaving
  the seven modules with their own point renderer still shrinking.

The other five were readings of a table: the designation belonged in
Field T1 on three separate tables, two icons needed text milsymbol
draws no slot for, Contain's "ENY" mask could never have worked,
Retain's sweep was 330 rather than 300, and six sonobuoys rendered
small because milsymbol over-declared their box.

**The pattern across all eight**: not one was found by the test suite,
and several had tests that passed while asserting the wrong thing -
Table H-XXI's own designation test pinned Field T explicitly, with a
comment explaining why T1 was rejected. String-level assertions on
expressions are what let that happen. The tests written in response
render and measure instead, and three of them are cross-module sweeps
that a new layer joins automatically.

What remains in Appendix H is construction, not correction: 54
symbols in five units, all lines and areas - recounted from each
module's own audit the same day, the ledger's summary line having
drifted from its own rows.

### Maritime Navigational (218400) built; Table H-XIV closed (2026-08-14)

The first of the 54 remaining line/area symbols, and the smallest unit:
one row, and it closes Table H-XIV outright.

Built to the maintainer's own dictated construction - "user clicks pt1
and pt2, draw a line joining them, at pt 1 draw a line segment of 6mm
at 40 deg angle relative to the pt1-pt2 line, at pt2 draw a line at
220deg angle relative to the pt1-pt2 line, 6mm" - and checked against
the template, which draws exactly that Z. 220 is 40 + 180, so the pair
is anti-parallel and the symbol reads the same whichever way round the
two points were clicked.

**The flanks are marker GLYPHS, not generated geometry, because 6 mm is
a page unit.** The standard's own Size/Shape rule agrees that only the
middle run varies ("The symbol varies only in length"), and nothing
inside a geometry generator can express millimetres - `@map_scale` does
not resolve there, probed twice. Same reasoning as Fortified Line's own
rampart tile. `setRotateSymbols(True)` on each marker line is what makes
the angle relative to the direction of travel rather than to north.

Two details carried over from earlier rounds rather than rediscovered:
the glyph's viewBox is symmetric about the origin so it centres on the
vertex, which means the marker size is TWICE the flank length (QGIS
sizes an SVG marker by its width); and the colour reaches the SVG as a
STRING, since the shared `_AFFILIATION_COLOR_EXPRESSION` is built from
`color_rgb()`, which evaluates to a bare "0,0,255" - valid for a colour
property, silently invalid inside an SVG, and it draws the glyph as
nothing at all. That one cost a debugging round on H-XIX's towers.

**Verified by measuring the render, not by eye**: the drawn flanks come
out at 40.0 and 219 degrees relative to the line for east, west and
north-east headings alike. QGIS's marker-rotation convention is exactly
the kind of thing that looks plausible and is 90 degrees out.

53 symbols left, in 4 units. 1120 tests passing on both QGIS versions.

### Table H-XXIII's eight supply routes (2026-08-14)

Eight codes, **one construction** - which is the whole reason this unit
was worth doing before the bigger ones. The MSR and ASR halves differ
only in the abbreviation they label with; the three traffic variants
differ only in which arrows ride above the line. One symbol function,
one label expression, one glyph function.

**The unnumbered choices went to the maintainer BEFORE building**, not
after - the lesson from Table H-XIX, where every guess at a dimension
the standard omits needed correcting and every question asked first did
not. Arrow 12 mm, 3 mm above the line, 3 mm between the pair, label
2 mm clear of the topmost arrow, and everything drawn **once per
feature, centred**.

That last one is a deliberate departure from the text. The draw rules
say "the line segment between each pair of anchor points will repeat
all information associated with the line segment" - but a route
digitized along a real road has dozens of short segments, and an arrow
and a label on each is unreadable. Same call already made for Boundary
and the FSCL family; made explicitly here rather than by drift.

**Two things the first render caught**, both against the standard's own
examples rather than by eye:

- **Two Way had its arrows the wrong way up.** "MSR SUMMER" draws the
  arrow WITH the direction of travel ABOVE the one against it; the
  build had them swapped. The arrow tuple is now ordered outward from
  the line, which makes that ordering explicit rather than incidental.
- **Alternating's "ALT" ate its own shafts.** The text size was derived
  from the glyph's length, so lengthening the assembly enlarged the
  word too and the two heads stayed pressed against it. The size is an
  explicit argument now, and lengthening buys shaft.

The arrows are marker glyphs in millimetres, the same page-unit
technique as Navigational's flanks and Fortified Line's rampart. The
glyph colour reaches the SVG as a STRING for the same reason as ever -
`color_rgb()` yields a bare "0,0,255" that an SVG silently ignores.

45 symbols left, in 3 units. 1127 tests passing on both QGIS versions.

### Table H-XXIII's seven sustainment areas (2026-08-14)

The construction was the easy part - "at least three anchor points to
define the boundary", the same freeform-area build Table H-V already
uses here. **What needed reading was the lettering, and the obvious
derivation was wrong twice.**

- The three SUPPORT areas letter with an abbreviation - RSA, BSA, DSA -
  and **carry no Field T at all**, drawn bare in both the TEMPLATE and
  EXAMPLE columns.
- The other four spell their name out IN FULL, on two lines exactly as
  drawn ("DETAINEE" / "HOLDING AREA"), and do take Field T beneath it
  ("GB", "15MP", "2AVN", "8MEB" in the standard's own examples).

Had these been derived from the measure names, three of them would
have been captioned "DHA", "EPWHA" and "RHA" - forms that appear
nowhere in MIL-STD-2525D. That is the same class of mistake as
inventing a "Sea" prefix on Table H-XIV's station names, caught there
by the maintainer's own smoke test; caught here by rendering the
templates before writing anything.

Table H-XXIII is now 33 of its 37 rows: 18 points, 8 supply routes,
7 areas. What remains is the two convoy lines and two parent rows that
draw nothing.

38 symbols left, in 2 units plus the range fans. 1133 tests passing on
both QGIS versions.

### Weapon/Sensor Range Fans built; the last blocked unit clears (2026-08-14)

Deferred when the rest of Table H-XVIII was built, on the grounds that
they "need genuinely computed geometry rather than a boundary you
digitize" - which was right, and stayed blocked until the maintainer
dictated the construction.

**Two codes, one symbol.** Circular (242100) is Sector (242200) with
the default angles, so nothing in the build distinguishes them but the
numbers typed. One clicked centre, then up to five rings of left angle,
right angle, range and altitude.

**The range is a real ground distance, which makes this the only symbol
in the appendix that is not page units.** Everything else built here -
rampart tiles, traffic arrows, Navigational's flanks - is millimetres
on the page and deliberately does not scale. A range ring must, so the
arc is projected GEODESICALLY via
`QgsDistanceArea.computeSpheroidProject()`, the same machinery the
bearing/range tool uses. A constant-coordinate circle would draw an
ellipse anywhere off the equator, and worse the further from it.

Decisions worth recording:

- **Angles are compass bearings** - clockwise from north - because the
  construction says "the centerline is always north". A sector may
  cross north; 300 to 60 is the 120-degree sector straddling it, not
  the 240-degree one going the other way. Pinned by a test, since the
  maths convention (anticlockwise from east) is the natural thing to
  write by accident.
- **Metres is an assumption**, named as such in the module. The
  construction gives the range as a distance but never its unit;
  metres is conventional for weapon and sensor ranges and for the
  Minimum Safe Distance Zone beside it. One constant if not.
- **Five rings is a hard cap**, not a paging problem - the maintainer's
  own instruction is that a sixth means a second symbol at the same
  point.
- **One label rule per ring.** QGIS places a single label per rule, so
  five rings need five rules, each with its own data-defined position
  and filtered to features where that ring has a range. Same pattern
  as Contain/Retain.

A ring with a range of 0 or less returns an empty geometry; a ring left
UNFILLED never runs the function at all, because QGIS short-circuits a
call to NULL on any NULL argument. Both draw nothing, but for different
reasons, and both are pinned.

36 symbols left, in 2 units. 1143 tests passing on both QGIS versions.

### Range fans: three smoke-test corrections (2026-08-14)

All three from the maintainer's own side-by-side against the standard's
picture, which is the comparison that keeps catching what a render
alone does not.

- **The altitude was not upper-cased.** A typed "gl" stayed "gl"
  against H.5.4's own all-caps rule. The range is numeric and needed
  nothing; only the altitude is free text.
- **Outer rings drew straight through the inner ones.** Every ring's
  straight sides ran to the centre. They span only their OWN band now -
  from the previous ring's range out to their own - so the fan reads as
  nested annulus segments, which is what the standard draws. Only ring
  1 reaches the vertex, and only because its inner range is 0. Worth
  recording that the first reading of this was more elaborate than the
  rule turned out to be: whether a side reached the vertex looked like
  it should depend on whether an inner ring covered that BEARING, and
  the maintainer corrected it to the simple version before any of that
  was built.
- **The north axis was missing entirely.** It runs from the centre
  through every ring to the outermost range plus 250 m, with a FILLED
  arrowhead - filled, unlike Contain and Retain's open heads, because
  those are open only where the solid triangles turned out to be
  annotation pointers. This one is drawn solid on a picture with no
  anchor-point callouts at all.

**A second round the same day, from the maintainer's own map rather
than a bare render**:

- **The axis overshoot is now a floor AND a proportion** - 400 m or ten
  per cent of the outermost range, whichever is larger. A fixed ground
  overshoot cannot work alone, because the thing it has to clear is a
  4 mm arrowhead: 250 m showed shaft on a 5 km fan and none at all on a
  larger one. The proportion holds the look constant at any size.
- **The arrowhead was sitting off the end of its own shaft.** QGIS
  centres a marker on the vertex it is placed at, so an arrowhead at
  LastVertex hangs half its length past the line. Backing it off by
  half a head with setOffsetAlongLine puts the TIP on the line's end.
- **Rings with an inner range are CLOSED now.** Where consecutive rings
  share their angles the inner arc lands invisibly on the ring inside
  it; where the angles differ it is the only thing closing the band,
  and without it the corners hung open.

1148 tests passing on both QGIS versions.

---

### Table H-XXI's seven contaminated areas; the last blocker was imaginary (2026-08-15)

The seven contaminated areas (271700-272001) - Biological, Chemical,
Nuclear and Radiological, each with a Toxic Industrial Material variant
except Nuclear - built as a new **CBRN Contaminated Areas** polygon
layer on `cbrn_defense.py`. Table H-XXI now has 25 of its 27 rows; only
the Minimum Safe Distance Zone and the dose-rate contour line remain,
and neither is blocked on anything.

**The blocker was a framing error, not a real gap.** These seven had
been held since 2026-08-13 on this project's own recorded audit: the
centred triangle carrying B/C/N/R "does not exist in milsymbol", and
its proportions "are not" given by the standard, so it would have to be
drawn - and, by the hard-won rule that where the standard is silent you
ask rather than guess, it was put to the maintainer and left. Their
answer was one sentence: the appropriate milsymbol inside, masked.

They were right, and the audit was wrong twice over. The triangle in
every one of the seven template pictures is - path for path - the icon
milsymbol already draws for the matching EVENT point in this same
table: 271800 Chemical Contaminated Area carries 281300 Chemical
Event's own glyph, 271801 carries 281301's (which is where the "T"
under the letter comes from, for free), and so on for all seven.
Probed and confirmed before building: all seven event icons render
into an identical viewBox with an identical triangle path. There were
no proportions to invent, because there was nothing to draw.

The lesson worth keeping is not "the audit was wrong" but WHERE it went
wrong: it asked whether the standard specified the glyph before asking
whether the glyph already existed. Checking milsymbol for the AREA's
own codes had been done (all seven render nothing at all, which is
still true and is why the glyph is addressed by the event's entity),
but not for the icon the picture actually showed.

**The construction.** A yellow hatched fill, an affiliation-coloured
status-driven outline, and one glyph centred inside, sized to fill the
area with at least 3 mm of clearance from the outline - the
maintainer's own specification. Each part had something to learn:

- **The glyph is sized from the polygon's own inscribed circle**, via
  two new expression functions - `mct_inscribed_centre()` for where the
  circle sits (the pole of inaccessibility) and
  `mct_inscribed_radius_mm()` for how big it is. A glyph whose furthest
  corner sits at (radius - 3 mm) from that circle's centre is, by the
  definition of the circle, at least 3 mm from every edge, whatever
  shape the user digitizes. Conservative for a long thin area, where
  only the two top corners ever reach that far - see the note at the
  end.
- **NOT point_on_surface().** Built first on a centroid fill, whose
  only choice is the true centroid or a point-on-surface, the glyph's
  corners crossed the outline: the size was right for a circle centred
  where the glyph wasn't. It draws in a geometry generator at the pole
  instead, so placement and sizing agree by construction.
- **The radius is in PAGE millimetres, deliberately not ground
  metres**, and getting that wrong cost the most time here. Measured
  geodesically - the way `mct_area_km2()` and every other measurement
  in this plugin is measured, and a perfectly defensible measurement of
  the Earth - the glyph rendered 29% oversized, corners well outside
  the area. A map drawn in a geographic CRS gives a degree of longitude
  and a degree of latitude the same width on the page while they are
  not the same distance on the ground. The page is what the 3 mm is
  measured on, so the radius is measured plainly in map units and only
  the units-to-millimetres factor is derived on the ellipsoid.
- **And that factor is asked of QGIS, not recomputed.** The obvious
  derivation - geodesic width of the extent, divided by its width in
  map units - is also wrong: for a view 0.2 degrees wide at 28 degrees
  north it gives 98,344 m per degree, while the number QGIS itself used
  to arrive at `@map_scale` is 76,402. Since the whole point is to
  agree with `@map_scale`, `_map_millimetres_per_unit()` recovers it
  from `QgsScaleCalculator` instead, at an arbitrary reference DPI and
  pixel width that both cancel exactly.
- **The hatch is masked behind the triangle**, which is what the
  maintainer meant by "(masked)" and what the template draws - the
  hatch stops at the triangle's outline and its interior is clean.
  A `QgsMaskMarkerSymbolLayer` carrying a filled-triangle SVG in
  milsymbol's own coordinate system, at the same data-defined size as
  the glyph, so the cut lands exactly on the drawn triangle.

**Two QGIS findings worth carrying forward**, both established by
render rather than by reading:

- **A mask nested inside a geometry generator DOES reach a sibling fill
  layer of the same symbol.** Worth stating because the reverse is not
  true and this project has hit the reverse twice: a MASKED layer
  nested inside a geometry generator cannot be reached at all.
- **Inside a geometry generator's (or a centroid fill's) sub-symbol,
  `$geometry` is the POINT being drawn, not the feature's polygon** -
  and so is `geometry(@feature)`'s geometry... except that it isn't:
  `geometry(@feature)` DOES return the polygon, while `$geometry` does
  not. The size expression uses the former. `get_feature_by_id(@layer,
  $id)` also returns it but deadlocked the renderer, and is not used.

**Yellow is the standard's own colour, not an affiliation.** All seven
templates fill with the same yellow hatch whatever the symbol's
identity, exactly as Table H-XIX's obstacles are green whatever theirs.
The outline still follows affiliation per H.5.3, which nothing in
H.5.23 overrides.

No `unique_designation` field: alone among the areas in this appendix,
not one of the seven templates carries a text amplifier at all. The
glyph is the whole symbol.

**One thing for the maintainer to call.** The inscribed-circle rule is
shape-proof but conservative: in a long thin plume or a crescent - both
realistic for a downwind hazard area, though neither is what the
template draws - the largest circle that fits is small, so the glyph
comes out small with it. Filling those tightly would mean fitting the
triangle itself rather than its circumcircle, which is a real search
rather than a formula. Shown in the render alongside the template
shape. **Answered the same day** - see the capping entry below, which
largely retires this.

1161 tests passing on both QGIS versions.

---

### The unknown-glyph bug, fourth occurrence (2026-08-15)

Reported the same day the contaminated areas landed: "glyphs are again
breaking in qgis, old problem" - milsymbol's inverted "?" drawn in
place of every area's triangle, and the hatch running straight through
it.

**Same defect, same root cause as 2026-08-12's.** An areas layer's
affiliation vocabulary carries a fifth value, "unspecified", meaning
"draw it black" - correct for a hand-drawn outline, and the field's own
DEFAULT. It is not a SIDC standard identity, so `build_sidc()` raised,
`mct_build_sidc()` returned the KeyError message as though it were a
SIDC, and milsymbol fell back to its unknown icon. The second symptom
followed from the first: the fallback icon's box is 108x108 against the
event icon's 158x118, so the mask - correctly cutting a triangle where
the real glyph would be - cut somewhere the wrong glyph wasn't.

**And the test that shipped alongside it made exactly the mistake the
roadmap already records the previous two tests making**: every check,
including the offscreen render used to sign the work off, built its
feature with `affiliation="friend"` hardcoded. The layer's own default
was never once exercised. That is now written into the new test class's
own docstring, where the next person to add a milsymbol-bearing layer
will read it.

**Fixed by mapping, not by removing the fifth value** - this layer
genuinely needs it for the outline. The glyph's standard identity is
the affiliation when it is one of the four real ones and "friend"
otherwise, with `monoColor` set to #000000 for the fifth so it really
is black rather than relying on friend happening to render black.
Nothing is lost: probed, milsymbol draws only HOSTILE differently
(red); friend, neutral and unknown all render black already.

**A new guard** drives `QgsVectorLayerUtils.createFeature()` - what
QGIS itself calls when the user digitizes - across every measure type
and every affiliation the form offers, and asserts the unknown-icon
path is absent. Verified by reverting the fix: 15 failures.

**Swept the rest of the plugin for the same pairing**, since this is
the fourth time: every `create_*_layer()` in `military_symbology/`
built, populated from its own defaults, and every data-defined SVG
path in every symbol layer and sub-symbol evaluated and decoded - 42
milsymbol-bearing symbol layers. **No other layer produces the
fallback.** The one flagged row is Mined Area's second mine-glyph slot
returning an empty string by design, which its caller turns into a
zero-size marker.

1167 tests passing on both QGIS versions.

---

### The contaminated-area glyph is capped, not fitted (2026-08-15)

The maintainer, on the same day's smoke test: "in smaller areas, the
3 mm is making the glyph too small; can we put a limit - say 1 mm gap
subject to a max size of glyph to say 12 mm."

Two numbers, and together they change what the construction IS. It was
built to FILL the area - the original specification - so the triangle
came out nearly as wide as the polygon at every zoom, and a 3 mm
clearance was a small tax on a large area but most of the room in a
small one. Now:

- **12 mm cap.** This, not the clearance, is what governs at ordinary
  zoom: any area whose inscribed radius exceeds about 7.3 mm on the
  page draws its glyph at exactly 12 mm, so every area big enough to
  hold one shows the same symbol at the same weight. It sits close to
  the point layers' own marker sizes - 8 mm generally, 10.4 mm for
  these same event icons on the CBRN Points layer - so an area's glyph
  and a point's now read at comparable weight, which they did not
  before.
- **1 mm clearance.** Only binds below that threshold, where it decides
  how much the glyph shrinks rather than whether it is capped.
- The 3 mm floor is unchanged: past the point where even 1 mm cannot be
  honoured the glyph deliberately overflows its own area rather than
  disappearing.

Measured across the range: an inscribed radius of 43.5 mm, 19.6 mm and
9.6 mm all draw at 12.00 mm; 4.8 mm draws at 7.21 mm with the gap tight
against 1 mm.

**The tests measure both regimes now**, at two different zooms against
the same feature, rather than one arbitrary one - the previous single
test would have passed unchanged on the capped build without ever
exercising the cap. A third pins the floor.

This also mostly retires the caveat recorded with the original build.
A long thin plume or a crescent was under-served by sizing to the
inscribed circle, because that circle is small for such a shape; with a
12 mm cap and a 1 mm gap it only shrinks when it genuinely cannot hold
a normal glyph, and then only as far as the fit allows.

1169 tests passing on both QGIS versions.

---

### Table H-XXI closes: Minimum Safe Distance Zone and the dose-rate contour (2026-08-15)

The maintainer's own constructions for the table's last two rows, and
with them **Table H-XXI is complete - all 27 codes, across four
layers**.

**Minimum Safe Distance Zone (272100)** - "same construction as weapon
sensor range fan; only that only range is required to be input - in
meters, and range is inscribed on the perimeter circle... straight, on
the right, masked". A new point layer with one clicked centre and up to
five ranges: no angles (the zone is always a full circle), no altitude.

Their one change to the standard is what the labels SAY. Its own draw
rules number the rings 1, 2, 3; the maintainer writes the range itself,
so 500/1500/2500 label as "500m", "1500m", "2500m". **Everything else
they described turns out to be the standard's own picture exactly** -
the numbers level with the centre, to its right, horizontal, with each
circle broken either side of its own number. Worth checking the example
before building rather than after: it confirmed the whole placement in
one look.

The break is cut into the ring's own geometry rather than masked, and
that part is not a choice - QGIS's Selective Masking cannot reach a
symbol layer nested inside a geometry generator, and a generated ring
has nowhere else to live. Its width is the label's own rendered width
plus padding, measured with Qt's font metrics rather than estimated
from the character count, so "500m" and "12500m" each get the gap they
actually need.

**Radiation Dose Rate Contour Line (272200)** - "just a polygon with
the unique designation Field T place at the top; nothing special,
contours will be hand drawn by user so multiple contours = multiple
lines/polygons". Built as exactly that: an unfilled status-driven
outline with Field T at the top of the shape, masking the outline it
sits on. A POLYGON layer despite the row being called a "Contour Line",
because its own draw rules ask for "at least three anchor points to
define the boundary of the area" - the area vocabulary word for word.

Two details the first render caught:

- **The dose rate is NOT upper-cased**, alone among the Field T labels
  in this appendix. H.5.4's "all text labeling in upper case" is
  applied everywhere else here, but this row's own example writes
  "30cGy", "100cGy", "300cGy", and cGy is the SI symbol for the
  centigray, where case carries meaning. Upper-casing it would
  contradict the standard's own picture of this very row to satisfy its
  general rule.
- **displayAll**, because nested contours are the normal case: three
  contours around one release sit close together near the top, which is
  where their labels go, and PAL's default collision handling silently
  dropped the middle one. A missing dose rate is worse than two labels
  close together.

**A long-standing note in this project is wrong, and it is corrected
rather than quietly dropped.** Three places recorded that `@map_scale`
does not resolve inside a geometry generator - field_fortification.py,
offensive_control_measures.py and a Maritime test. **It does.** Probed
directly on 2026-08-15 with a properly populated map-settings scope: a
geometry-generator expression reads exactly the scale
`QgsMapSettings.scale()` reports.

Where the belief came from is worth knowing, because both sources are
now understood:

- The offensive_control_measures case saw a trim come out "far larger
  than intended" - not a NULL variable but a map-unit conversion. A
  scale relates ground metres to page millimetres, and the geometry
  there is in DEGREES.
- The offscreen harness this project renders with never called
  `settings.setExpressionContext(...)`, so EVERY map variable read NULL
  in it - not just this one. That flaw was found earlier the same day
  while sizing the contaminated areas' glyph.

**No existing construction was changed on the strength of this.** The
rampart profile, the bowtie and Navigational's flanks all work, are
signed off, and their marker-glyph approaches were never the worse
answer. Only the comments were corrected, so the claim is not carried
forward as fact - the CBRN triangle blocker earlier the same day is
what a stale claim in a comment costs.

1183 tests passing on both QGIS versions.

---

### Penetrate (341800), on Block's own construction (2026-08-15)

The maintainer's instruction: "same construction as the block, replace
'B' with 'P' the perpendicular line joining pt3 to p1-pt2 line segment
- arrowhead at the point of contact between the perpendicular and the
base".

So the crossbar, the stem, the three anchor points and the letter gap
are Block's calls again. The one new piece is where the head goes:
`mct_block_stem_foot()` returns a short segment run from the tip TOWARDS
the stem's meeting point with the crossbar, so a marker on its last
vertex sits at the join and points INTO the base.

**A note in the first version of this entry was wrong** and is
corrected here: it claimed the standard draws Penetrate's arrow
projecting OUTWARD and that the maintainer's placement diverged. It
does not. Rendered and looked at on the maintainer's own prompting
("recheck the manual"), Table H-XXIV's template draws the arrowhead
exactly where they said - at the junction, pointing INTO the vertical
line. The draw-rules text says the arrow "projects perpendicularly
from the midpoint", which is about the stem, not the head.

Its own short geometry rather than the symbol's, for the reason every
one of these heads needs one: the stem is multi-part once the letter
gap is cut into it, and a LastVertex marker fires on the last vertex of
every part.

1191 tests passing on both QGIS versions.

---

### Seize (342300), Turn's curve with a circle at its start (2026-08-16)

The maintainer's own construction: "same as turn, only that at p1
instead of beginning the line (bezier curve), insert a circle - keep
the radius 1.5 times that of a standard milsymbol... and the line
pt1-pt2-pt3 does not go through the circle at pt1 but starts from the
perimeter of the circle".

So the curve is `mct_turn_arc()` untouched - Table H-XIX's own Turn,
same three anchor points, same arrowhead at PT3. Everything Seize adds
is symbol layers over it:

- The circle at PT1, drawn on the CURVE's own first vertex rather than
  the feature's, so it stays put whichever way the curve bends. Its
  radius is one and a half times a point marker's own - a page unit,
  deliberately, since the maintainer pinned it to another page-sized
  symbol.
- The clearance, as `setTrimDistanceStart()` in millimetres. The gap is
  the circle's own page-unit radius, and QGIS applies a trim after
  projecting, so the curve leaves the perimeter at every zoom. The same
  tool the convoy bar uses to meet its head.

**Seize was briefly built with NO letter**, since the maintainer's
construction did not mention one - and that exposed a real assumption:
the letter machinery took every line task to have one, and raised a
KeyError the moment Seize was added. `LINE_LETTERS` is now the source
of truth for which tasks label at all, rather than the measure-type
list. The "S" was added straight after, on their word.

**The "S" sits ON the curve, in a gap cut for it** - like every other
letter on this layer.

That took a correction. Reading the template, the S looks as though it
sits clear of the line, and the first build placed it there. The
maintainer's answer: "no that is incorrect, S is on the line with
masking, like every other line you mentioned". The lesson is not about
this symbol - it is that a template picture is evidence about SHAPE and
weak evidence about a convention the maintainer has already set six
times on the same layer. The pattern was the better guide here, and I
had reached past it.

Broken with QGIS's own `line_substring()` in the module rather than
inside `mct_turn_arc()`, so Table H-XIX's Turn is untouched - which
needed `mct_mm_in_map_units()`, the inverse of `mct_radius_mm()`, to
express a page-sized gap in the map units the curve is measured in.

One thing the template did settle: **the circle holds a boxed Field A**,
not the letter. Field A is not offered on this build.

1191 tests passing on both QGIS versions.

---

### Counterattack by Fire (340700), and Appendix H closes (2026-08-16)

The last symbol in Appendix H, plus two corrections to Counterattack
itself from the maintainer's own render review.

**"the arrowhead being solid is not acceptable, so change it to dashed
- figure it out".** It could not be dashed as built: the head was the
convoy's own SVG glyph, and an SVG has no pen style. So the head and
the rear bar are GEOMETRY now - `mct_counterattack_head()` and
`mct_counterattack_rear()` - redrawn point for point from that glyph's
own path, which lets the whole outline take the same dashed stroke the
rails do. The flare ratio is written out rather than derived from
`_CONVOY_SVG_HEAD_FLARE / _CONVOY_SVG_BODY`, which would be a forward
reference at import time; a test asserts the two agree, so the link is
checked rather than merely claimed.

That also simplified the symbol: only the RAILS still need
`reverse($geometry)`, because only they rely on the convoy's own
end-trim. The head and the bar read PT1 and the last vertex directly
and are drawn the right way round either way.

**"align CATK text with the arrowhead".** So
`mct_counterattack_text_angle()` takes the arrowhead's own direction
and folds it into the half turn that reads left to right on the page.
The maintainer restated what "upright" had to mean after a first build
missed it, and their restatement is the clearest test of it: "left to
right K is near the arrowhead, right to left C is near the arrowhead".
Both follow from the fold, and both are pinned.

**That first build had the sign backwards.** QGIS's own label rotation
is CLOCKWISE from east; the angle was computed counter-clockwise, so
every label drew mirrored about the horizontal - which reads as
plausibly-rotated-but-wrong rather than as an obvious error, and only a
render caught it. Established by render, not by documentation, and the
test now asserts a north-east head gives a NEGATIVE rotation.

It is the only rotated label on this layer; every other one is upright,
which was the convoy's own convention and is what this replaces here.

**And it stands just behind the arrowhead, not at the middle of the
arrow** - the maintainer's own correction once the rotation was right:
"the text at mid point is not fine, put it slightly behind the arrow
head as is shown in the manual". Centring it had a second fault the
page also shows: on a three-point arrow the middle IS the bend, so the
word sat across both rails.

`mct_counterattack_text_point()` walks BACK from PT1 by the head's own
length, the word's own half width and a millimetre of clearance - so it
ends just short of the head at any size, and on a bent arrow it stays
on the leg the head is on. It needs the font size to know how wide the
word will be, so the size calculation is now a shared helper rather
than living inside the size function. A very short arrow falls back to
its own middle: better a cramped label than one hanging off the back of
the symbol.

**Counterattack by Fire is that arrow plus one detached piece, and the
first attempt at it was wrong.** It was built as a bar across the axis
with a filled triangle sitting on it, from a proposal made without
looking closely enough at the page - and a triangle against a bar reads
as a pennant. The maintainer's response was the right question: "why is
there a flag after the arrow head".

What the standard actually draws, measured off the example at 600 dpi:
an open bracket that WRAPS the arrowhead - an arm sweeping in from
beyond it, a straight run past its flare, an arm sweeping back out -
and then, after a clear gap, a small solid arrow WITH A STEM. The stem
is what makes it an arrow rather than a flag, and the bracket's
straight run is set from the head's own flare so the two are the same
size by construction.

The small arrow is the one FILLED part, and the one part the symbol's
own "dashed lines" note does not cover - both of the standard's
pictures draw it solid.

**The lesson is the same one this appendix keeps teaching**: the
template picture is the specification, and a proposal written from a
glance at it is a guess. Crop the page and measure it first.

**Appendix H is complete.** 1284 tests passing on both QGIS versions.

---

### Counterattack (340600), the Moving Convoy's arrow dashed (2026-08-16)

"let's start with moving convoy 330100 as template; user click three
points - pt1,2,3; draw an arrow of same dimensions as moving convoy,
but with dashed line; starting at pt3 with arrow head tip at pt1; put
text CATK - same rules for text as RIP" - the maintainer's own
instruction, and a deliberate simplification: the standard's own
Counterattack is a broad hollow arrow taking between 3 and 50 anchor
points.

**The head is at PT1, the FIRST click - the opposite end from the
convoy, whose head sits on its last vertex** (probed rather than
assumed; the convoy's own docstring numbers its points the standard's
way, not the click order's). So the whole symbol rides one geometry
generator over `reverse($geometry)`. Reversed, the feature is exactly
the shape a convoy expects - rear first, tip last - and every one of
its offsets, trims and placements carries over untouched instead of
being re-derived with the signs flipped. That is the point of doing it
this way rather than moving the head to the first vertex.

**"Same dimensions" is now enforced by a shared name.**
`_CONVOY_BODY_HEIGHT_MM`, `_CONVOY_HEAD_LENGTH_MM` and
`_CONVOY_REAR_BAR_WIDTH_MM` lost their underscores and are imported
from `supply_points`, so a change to the convoy moves this too rather
than the two drifting apart. The head is drawn by
`mct_convoy_end_svg('moving', ...)` - the convoy's own glyph, not a
copy of it.

**The dashes are the symbol, not its status**, per its own note - the
same clause Follow and Assume carries, and the same `always_dashed`
flag.

Two things worth flagging rather than burying:

- **The head cannot be dashed.** It is an SVG glyph and an SVG has no
  pen style, so it draws solid where the standard's picture dashes it.
- **The 24 pt cap on "CATK" never binds.** Sized "same rules as RIP" -
  both dimensions, smallest winning - but this arrow's height is the
  convoy's own bar, a FIXED page size, so the height constraint settles
  it at about 10.5 pt on anything but a very short arrow. Pinned by a
  test so a later change to the bar cannot silently move the text.

CATK sits at the path's midpoint, upright rather than following the
line - the convoy's own placement, and for its own stated reason: a
symbol drawn right to left would otherwise read upside down. On a
sharply bent arrow that midpoint IS the bend, which is where the text
lands.

1274 tests passing on both QGIS versions.

---

### Follow and Assume (341200) and Follow and Support (341300) (2026-08-16)

Built from the standard alone - "follow the manual, i will give
corrections after the smoke test if required" - so everything here is a
reading rather than a dictated construction, and worth recording as
such.

Two anchor points, PT1 the tip and PT2 the rear, which is the
standard's own order and the one Delay already uses on this layer.

**"Points 1 and 2 determine the length of the symbol, WHICH VARIES
ONLY IN LENGTH."** That clause is the whole design: the tag at the rear
and the head at the tip are FIXED PAGE SIZES and only the line between
them stretches. Building them as fractions of the line would have been
the easy reading and the wrong one - a long Follow would have drawn a
huge tag. Every figure is millimetres, converted to map units at draw
time, and a test pins that the tag's height does not move when the
symbol is made forty times longer.

The two differ in exactly three ways, all off the standard's own
examples on printed pages 644 and 645:

- the rear tag is NOTCHED on Support, straight on Assume;
- the line between tag and head is DASHED on Assume, solid on Support;
- the head is an OUTLINED double chevron on Assume, twice the tag's
  height, against a SOLID triangle on Support about as tall as it.

**Assume's dashes are not a status style**, and that distinction
matters here. Its own note says "The dashed lines in this graphic shall
be displayed in present AND anticipated status" - so that line is
dashed because of what the symbol IS. `_task_line_layer()` gained an
`always_dashed` flag which pins the pen and leaves the status property
off entirely, rather than trying to express it through the usual
status expression. Both halves are pinned by tests.

Support's head is the first FILLED part on this layer, so
`_task_fill_generator_layer()` is new - a line symbol layer cannot
fill, and that head is solid in the standard's example.

The millimetre figures come off both examples measured at 800 dpi and
scaled so the taller head is 8 mm, a marker's own width here. Ratios
held from the page: the tag is half the assume head's height, its nose
is a third of its own length, and the support head is as tall as the
tag.

**Field T is not drawn.** Both templates put a boxed T inside the rear
tag - that is what the tag is for - and the layer already carries a
`unique_designation` field that nothing on it draws. Left alone under
the standing partial-amplifier decision rather than added speculatively;
raised here because this is the one symbol where the amplifier has a
container built for it.

1268 tests passing on both QGIS versions.

---

### Security: Cover, Guard and Screen (342201-342203) (2026-08-16)

One construction with three letters, the way the Delay family is.
**342200, the Security row they sit under, draws nothing at all** - its
own TEMPLATE and EXAMPLE both read "N/A" - so there are three symbols
here rather than four. Confirmed directly: "in security 342200 there is
nothing to be built drop it". It stays in the remaining record, marked
undrawable, so the arithmetic still runs; the same standing the table's
own section parent has.

The maintainer's construction, from the centre outwards: a gap for a
unit symbol at the centre click, the letter either side of it, a small
gap, then a lightning bolt out to each end point finishing in an
arrowhead, the two bolts mirror images of each other.

**The MIDDLE click is the centre**, which is not what the standard
does - its PT1 is the centre and PT2/PT3 the ends. The maintainer's
order makes the feature a plain three-vertex line drawn end, centre,
end, which is how a screen frontage is actually digitized, and it is
the order the layer already uses for every other three-point task.

**The unit symbol is reserved space, not a built field** - "make a gap
for a milsymbol say infantry batallion". A user who wants one places it
themselves, exactly as with every other Field A in this appendix. The
width left is DEFAULT_MARKER_SIZE_MM, a standard point marker on this
plugin's own layers.

**The bolt's shape is measured off the standard**, printed page 651,
read back at 1400 dpi from both the template and the example. As
fractions of the bolt's own length the first rail ends at 0.687, the
diagonal lands back at 0.576, and the drop is 0.098. Rounded to 0.70 /
0.60 / 0.10, which makes the diagonal exactly 45 degrees - the distance
it travels back equals the distance it drops. The diagonal running
BACK toward the centre as it falls is what makes it a lightning bolt
rather than a step.

**The clicked line is the spine.** PT1 and PT3 sit on the upper rail in
the template - their leaders point level with it, not at the arrowheads
- so the letters, the reserved space and the inner rails all lie on the
line the user drew and only the outer rail and the head drop off it.
Worth having checked: the obvious reading, that the arrowheads land on
the clicked points, is the wrong one.

**Each bolt drops to its own arm's own side**, PT1's to the left and
PT3's to the right walking outward. On a straight line those are the
same physical side, which is what makes the pair read as a mirror; on a
bent one each still follows its own arm rather than a side of the
world. The same reasoning Breach's ticks needed, and the same reason
both are geometry rather than rotated markers.

**These write the same letter twice**, the only symbols on the layer
that do, so `_label_specifications()` returns a LIST of labels per
measure type rather than one. That list was introduced for "RIP" an
hour earlier and paid for itself immediately.

1254 tests passing on both QGIS versions.

---

### Relief in Place (341900), Retire without its letter (2026-08-16)

"same construction as retire, remove the letter R and let the line be
continuous, just add another arrow parallel to pt1-pt2 line segment
with the arrowhead touching pt3" - the maintainer's own instruction.

The continuous line came free: `_letter_gap_expression()` returns 0 for
a task that carries no letter, so `mct_delay_geometry()` takes its own
no-gap path and the labelling loop, which iterates `LINE_LETTERS`,
builds no rule for it either. Seize's KeyError of 2026-08-16 is what
made `LINE_LETTERS` the source of truth for that rather than the
measure-type list, and this is the first symbol to benefit.

**Relief in Place draws the Delay shape but is deliberately NOT in
`DELAY_CONSTRUCTION_MEASURE_TYPES`.** That tuple carries a promise -
only the letter differs between its members - and this breaks it twice
over, with no letter and an extra arrow. It is in a wider
`_DELAY_SHAPE_MEASURE_TYPES` instead, so the four-way guarantee and its
test stay true of the family they describe.

**The second arrow ends where the ARC ends, not at PT3 as clicked.**
Those are the same point whenever PT3 is square to the shaft, which is
how these are drawn now that the arc is forced perpendicular - but on a
skewed click the raw PT3 would leave the arrowhead floating off the end
of the curve. Pinned by a test on a deliberately skewed PT3.

**The standard draws "RIP" centred inside the shape**, in both its
template and its example. That was raised rather than assumed - the
instruction was about removing the letter from the shaft, not about
adding different text - and the maintainer took it the same day:
"correct about RIP text - add it".

It goes in the middle of the enclosed shape:
`mct_relief_in_place_text_point()` is the shaft's midpoint carried half
way out along the perpendicular. Unlike every letter on this layer it
sits in OPEN PAPER rather than on a line, so it cuts no gap - which is
exactly what lets the shaft stay continuous. That is why Relief in
Place stays out of `LINE_LETTERS` and a wider
`LABELLED_MEASURE_TYPES` drives the labelling loop instead: the two
lists mean different things now, and conflating them would put a gap
back in the shaft.

**And it is the only text on this layer that is not a fixed size** -
"make it variable so as to fit the area reasonably well subject to a
maximum of 24pt - see the manual", the same day again. Every letter
here sits in a gap cut to its own width, so a fixed size is what keeps
the two agreeing; "RIP" sits in open paper inside a shape whose size
the user sets, so it grows with the shape and stops at the cap.

Both of the shape's dimensions bind, smallest winning, and that is not
belt-and-braces: the shaft is set by PT1/PT2 and the gap between the
arrows by PT3, so a tall narrow one sized on height alone would run
the text out through its own arrows. The fractions - 0.40 of the gap
as a font size, 0.60 of the shaft as a width - are measured off the
standard's own template, where they happen to land on the same answer.

`mct_relief_in_place_text_size()` returns POINTS and is wired as a
data-defined Size on the label, set BEFORE the rule takes ownership of
the settings rather than reached back into afterwards.

Three anchor points rather than the standard's four: its PT3/PT4 set
the second arrow's length independently, and here it takes the first
arrow's. The maintainer's construction, and it keeps the whole Delay
family clicking the same way.

1239 tests passing on both QGIS versions.

---

### Clear (340500), Penetrate with two more arrows (2026-08-16)

"start with penetrate of mission task, same construction, just add
another two arrows of same lengths, distance from the middle arrow -
3/4 of the length between the midpoint of base shaft to the end; on
both sides" - the maintainer's own instruction. So the base line, the
middle arrow, its "C" gap and its head are all Block's own calls a
third time, and `mct_clear_side_stems()` is the only new geometry.

**The maintainer's 3/4 is the standard's own proportion, arrived at
independently.** Its draw rules only say "the spacing between the
symbol's arrows will stay proportional to the symbol's height", but
its template puts the outer arrows about 0.73 of the way from the
midpoint to each end of the vertical line. Two readings agreeing is
worth more than either, and it is why this one needed no measurement
argument.

The outer pair runs TIP TO FOOT, so a last-vertex marker lands each
head on the base line pointing into it - the arrangement Penetrate's
own head already uses, and the reason two parts give exactly two heads.

The standard's other rule here came free: "the arrows will stay
perpendicular to the vertical line, regardless of the rotational
orientation of the symbol as a whole" is just the projection Block
already does, so a rotated Clear needed nothing extra. Pinned by a test
on a diagonal base line all the same.

1232 tests passing on both QGIS versions.

---

### Breach (340200) and Canalize (340400), Bypass with its heads replaced (2026-08-16)

"same as bypass, replace the arrowheads with slanting lines at the
edges, converging out" for Breach; "same as breach, replace B with C,
and reverse the orientation slanting lines, converging in" for
Canalize. So all three share `mct_obstacle_bypass_arrows()` and the
joining line, and `BYPASS_CONSTRUCTION_MEASURE_TYPES` holds the set the
way `DELAY_CONSTRUCTION_MEASURE_TYPES` does.

**The ticks are real geometry, not rotated markers, and that is the
one decision here worth keeping.** A marker line places ONE angle on
every part it fires on, and the two ticks are mirror images of each
other - so the angle would have to be keyed to which ARM each tick sat
on. It would have worked until a user clicked PT1 and PT2 the other way
round, at which point Breach would have drawn Canalize's picture and
nothing would have errored. `mct_bypass_ticks()` takes each tick's
outward direction from its own tip's side of the opening instead, so
click order cannot change the symbol. Pinned by a test that swaps the
two points and asserts the drawing is unchanged.

**Two numbers, both measured off the standard's own pages 645-646.**
The tilt is 30 degrees off the perpendicular, 60 degrees to the arm:
four ticks fitted by principal axis came out at 66, 62, 59 and 53
degrees, a hand-drawn spread with 60 through the middle. The length is
a quarter of the arm capped at 6 mm - not measured but INHERITED, since
that is exactly the arrowhead each tick replaces, and the instruction
was to swap one for the other rather than to resize anything.

The cap is applied inside the geometry rather than by a marker's
QgsMapUnitScale, which needed `_page_gap_in_map_units()` to express 6
page millimetres in the map units the ticks are drawn in - the same
conversion every letter gap on this layer uses.

1225 tests passing on both QGIS versions.

---

### Bypass (340300), on Obstacle Bypass Easy's own construction (2026-08-16)

"same as obstacle bypass easy 270601, except add B (masked) on line
segment joining the two arrows, in the middle of the line" - the
maintainer's own instruction, and a reminder that the cheap reuse was
not quite as spent as the previous entry claimed.

So the two arrows are `mct_obstacle_bypass_arrows()` untouched and the
line joining them is `mct_obstacle_bypass_rear_easy()`, which gains the
same OPTIONAL gap arguments every other reused construction here has -
Table H-XIX's own 270601 passes neither and draws one unbroken part, a
test pins that.

**The arrowheads scale, because 270601's do.** They are sized in MAP
UNITS as a quarter of the arrow they sit on and capped at this layer's
own 6 mm, which is the behaviour the maintainer asked for on the
obstacle version in 2026-08-13: "arrowhead should also become small if
the lines are small, upto the current size which will be the max".
Every other head on the Mission Task Lines layer is a fixed 6 mm, so
`_arrowhead_layer()` gained a `map_unit_size_expression` rather than
Bypass getting a chevron generator of its own copied out of
`obstacle_control_measures.py`.

Worth recording why the size expression can read `$geometry` here at
all, given how often the opposite has bitten this project:
`mct_obstacle_bypass_arrow_length()` was written to accept EITHER the
feature's three clicked points or the generated arrows, precisely
because inside a generator's sub-symbol `$geometry` is the generated
one. Each generated arrow part is [rear, tip], so its own length is the
same distance either way.

**Bypass is the ninth name that appears twice in Appendix H** under
different codes and different drawn forms - except that this pair
really is the same drawing, which none of the earlier eight were. The
records stay keyed by code regardless.

1216 tests passing on both QGIS versions.

---

### The Delay arc is forced perpendicular (2026-08-16)

Raised when Delay shipped, answered the same day: "yes, force the arc
perpendicular for all four". So the standard's own draw rule now holds
- "The 180 degree circular arc is always perpendicular to the line" -
across Delay, Retire, Withdraw and Withdraw Under Pressure at once,
which is what building them as one construction bought.

**PT3 now sets the diameter's LENGTH and its SIDE, not its
direction.** The diameter is PT3's perpendicular distance from the
infinite line through PT1-PT2; the shaft sets which way it points.
Click PT3 square to the shaft and nothing changes at all, which is why
this could be taken without invalidating anything already drawn.

Worth recording that this makes a third anchor point behave the SAME
WAY everywhere in the module. `mct_block_geometry`, `mct_contain_arc`
and `mct_trip_wire_geometry` already projected their own PT3 onto a
perpendicular; Delay was the odd one out, and the standard and the
codebase turned out to want the same thing.

The degenerate case moved with it: it used to be "PT2 and PT3
coincide", and it is now "PT3 sits on the shaft's own line" - there is
no side to be on, so no arc is drawn rather than one being guessed.
The shaft, its letter and its arrowhead all still appear.

1212 tests passing on both QGIS versions.

---

### Retire, Withdraw and Withdraw Under Pressure: Delay four times over (2026-08-16)

"Retire, Withdraw, withdraw under pressure - all same as delay; only
change being use letter R for retire, W for withdraw and WP for
withdraw under pressure" - the maintainer's own instruction, and the
standard agrees: the four rows' draw rules are word for word each
other's.

So the three of them cost a vocabulary entry apiece.
`DELAY_CONSTRUCTION_MEASURE_TYPES` holds all four, and every branch
that used to name "delay" now tests membership of that tuple - kept as
one name rather than four branches so a change to the shape cannot
reach one of them and miss the others. A test pins that the four
renderer rules build the same layers over the same geometry, and that
only the letter differs.

**WP is two glyphs, and the letter gap is measured rather than
assumed.** `mct_text_width_mm()` takes Qt's own font metrics, so the
wider letter cuts the wider gap with nothing per-letter written down.
Pinned by a test, because a per-letter constant is exactly the kind of
thing a later change would add without noticing.

**This is the last of the cheap reuse.** Twelve line tasks have shipped
in two days and eleven of them were an existing construction - Retain
three times, Block twice, Turn, H-XIX's own Fix and Disrupt, and now
Delay three times. The 13 rows left share a shape with nothing built,
and the module's own audit note says so rather than still promising a
quick win.

1210 tests passing on both QGIS versions.

---

### Delay (340800), the first mission task that borrows nothing (2026-08-16)

The maintainer's own construction: "user clicks pt1, pt2 and pt3.
arrowhead at pt1, shaft from pt1 to pt2, then join pt2 and pt3 with a
semicircle, pt2 to pt3 being the diameter; letter D masked, on the
shaft between pt1 and pt2".

Every line task before this one was an existing construction reused -
Retain three times over, Block twice, Turn, and H-XIX's own Fix and
Disrupt. Delay is the first with no relative anywhere in the plugin, so
`mct_delay_geometry()`, `mct_delay_shaft()` and
`mct_delay_letter_point()` are all new.

**PT2-PT3 was taken as the diameter exactly as clicked** in this first
build, which is what the instruction said. The standard says something
slightly stronger - "The 180 degree circular arc is always
perpendicular to the line" - so it was raised with the maintainer
rather than decided here, and they took it: see the entry above, which
supersedes this paragraph.

**The one thing PT3 cannot settle on its own is which way the
semicircle bulges** - a diameter admits two. It bulges AWAY FROM PT1,
which is what the template draws and the only reading that keeps the
arc off the shaft. Implemented by taking whichever of the two crowns
lands further from PT1, so it follows PT3 to either side rather than
being pinned to one side of the world.

Two small things worth recording:

- The arc carries on from PT2 with no break, so it belongs to the same
  PART as the shaft's second half. One continuous run, not a shaft
  plus a separate arc.
- The arrowhead rides `mct_delay_shaft()`, which is the shaft run
  BACKWARDS - PT2 to PT1 - so a marker on its last vertex sits at PT1
  and points out of the symbol. It cannot ride the main geometry: that
  is two parts once the "D" gap is cut, and a LastVertex marker would
  drop a second arrowhead at PT3. The same trap Retain and Contain
  both hit.

1206 tests passing on both QGIS versions.

---

### Isolate (341500), Secure with triangles on it (2026-08-16)

The maintainer's own construction: "start with same construction rules
as secure including the arrowhead, replace 'S' with 'I'; now draw
triangles facing inwards, based on the perimeter, base is not drawn the
perimeter arc acts like the base, triangles start 30 deg from pt2, and
end 30 deg before the arrow head, size of triangles (base to tip) 1/3
of radius".

So the arc is `mct_retain_arc()` for the third time - Retain, Secure,
Occupy and now Isolate are one construction - and the arrowhead is
`mct_retain_arc_end()` unchanged. The only new geometry is
`mct_isolate_teeth()`, and it is genuinely new: Retain's own teeth are
radial TICKS a fifth of the radius long, not triangles standing on the
perimeter.

Each triangle is an OPEN three-point run - corner, apex, corner. The
base is not drawn because the arc it stands on already is the base, so
closing the ring would draw the one line the instruction rules out.

**Two figures the instruction leaves open, both measured off the
standard's own template** (page 646, rendered at 900 dpi and read
back as a radial profile rather than eyeballed):

- The SPACING. The template's apexes measure out at 0, 42, 93 and 142
  degrees round the half of the drawing its captions do not cross -
  45 degrees apart. 45 also divides the 270 degrees the instruction
  leaves for them exactly six times, so seven triangles land on 30, 75,
  120, 165, 210, 255 and 300 degrees of sweep, first and last exactly
  where they were asked for. Both readings agree, which is why this is
  a measurement worth trusting rather than a guess.
- The BASE WIDTH, which the instruction does not give at all. Set equal
  to the height - a third of the radius - which sits inside the 18 to
  25 degrees of arc the template's own bases subtend. Because base and
  radius scale together the half-angle is a CONSTANT, `asin(1/6)`, so
  the triangles hold their shape at every radius. Pinned by a test.

**One thing the template settles the other way, and the maintainer's
word wins.** Table H-XXIV's Isolate draws no arrowhead - what looks
like one is the leader line pointing at the "PT. 2 (START POINT)"
caption. The instruction says "including the arrowhead", so it carries
Secure's. Worth recording because the same leader line could easily be
read as part of a future symbol on this page.

Small refactor alongside: the stroke every mission-task line draws with
- black, affiliation-driven, dashed when planned - is now
`_task_line_layer()`, shared by the symbol's own run and by Isolate's
triangles, so the two cannot drift apart.

1198 tests passing on both QGIS versions.

---

### Penetrate's head scales, and the manual is re-read (2026-08-15)

Two from the maintainer: "recheck the manual, the way we have drawn
penetrate is correct" - it is, see the correction in the entry below -
and make the head dynamic, "cap it to a max of 7mm".

**The fraction is measured off the template**, which they asked for
directly ("get a measurement from the manual - for dimension check").
On Table H-XXIV's own picture the chevron spans about a fifth of the
stem it sits on. That is the same ratio Occupy's cross uses, which is
a coincidence worth naming rather than a shared rule.

This is a pixel measurement of a printed drawing, which this project
normally distrusts - the draw rules give no number for it. It is
defensible here because it only sets a proportion and the 7 mm cap
does the real work at any usable zoom.

`mct_block_stem_mm()` gives the stem in page millimetres, through the
same units-to-millimetres factor everything else here uses, and reads
`geometry(@feature)` rather than `$geometry` - the marker is nested in
a geometry generator, where `$geometry` is the short foot segment.

1191 tests passing on both QGIS versions.

---

### Occupy's cross scales with its circle (2026-08-15)

The maintainer's smoke test: "the cross is correct - but the size is
fixed irrespective of the circle's radius - let's make the cross 1/5 of
the radius subject to max size which is the current size". Done: a
fifth of the radius, capped at the plain arrowhead's own 6 mm.

The radius is a GROUND distance and the cross a PAGE size, so
`mct_radius_mm()` converts through the same units-to-millimetres
factor the contaminated-area glyph uses.

**And it shipped wrong once, in the same place that has caught this
project twice before.** The first build read `$geometry` - but the size
is evaluated inside a geometry generator's own sub-symbol, where
`$geometry` is the short arc-end segment being drawn, not the feature's
own two clicked points. The cross came out at a fraction of a
millimetre. `geometry(@feature)` is the fix, exactly as on Table
H-XXI's contaminated areas.

1191 tests passing on both QGIS versions.

---

### Occupy (341700), Secure with a different end mark (2026-08-15)

The maintainer's own words: "everything same as secure, except,
replace 'S' with 'O', and have a X - drawn in the same size as the
arrowhead twice like this >< in place of the secure's arrowhead".

So the arc, the letter anchor and the gap are Secure's calls again -
which are Retain's. The only new thing is the end mark: the SAME
arrowhead marker twice on the same point, the second turned through
180 degrees, so ">" and "<" meet tip to tip. Co-located they read as
an X, which is what the instruction names first.

`_arrowhead_layer()` already took an angle - added for Fix's own
flipped head - so Occupy needed no new geometry at all.

1191 tests passing on both QGIS versions.

---

### Secure (342100), on Retain's own arc (2026-08-15)

First of the one-at-a-time run through Table H-XXIV, and the cheapest
symbol in it: **Secure is Retain's construction, reused whole.**

The maintainer's dictation - PT1 the centre, PT1-PT2 the radius, a 330
degree arc "like we did retain earlier", an arrowhead at the 330 degree
point, the letter on the perimeter at the 180 degree mark - describes
`mct_retain_arc()` exactly, gap and all. So Secure calls it, and calls
`mct_retain_arc_end()` for the head, rather than restating either.

**One line of new geometry**: `mct_secure_letter_point()`. Retain's own
"R" sits just OUTSIDE its perimeter; this "S" was asked for ON it, so
the anchor takes the radius itself instead of Retain's outward ratio.
Nothing else differs.

Also generalised `_arrowhead_layer()` out of Disrupt's own, since three
line tasks now carry heads on their own separate short geometry - each
of these shapes is multi-part once a letter gap is cut into it, and a
LastVertex marker fires on the last vertex of EVERY part.

1191 tests passing on both QGIS versions.

---

### Fix gains its arrowhead; the menu entry is renamed (2026-08-15)

Two from the maintainer's smoke test, Block and Disrupt cleared.

**"The menu item reads as mission task points, since there are lines
also, change it to mission tasks."** Renamed to "Mission Tasks", with a
tooltip that names both layers. The action's own attribute keeps its
old name - renaming that would touch nothing a user sees and every
caller that does.

**"Fix - pt1 there should be an arrow head."** Added at the first
vertex, turned through 180 degrees: a marker rotated onto a line's
FIRST vertex faces along the direction of travel, towards PT2 and back
into the symbol, so an arrowhead at the start has to be flipped to
point out of it.

Worth noting against Table H-XIX, whose own Fix deliberately has NO
arrowhead - the maintainer dropped the standard's when they dictated
that construction. The two now differ on purpose, and the obstacle
version is untouched.

1191 tests passing on both QGIS versions.

---

### Disrupt lands, without the mirror (2026-08-15)

The maintainer settled the orientation question by removing it: "just
follow the original instructions, ignore the call for mirror, we draw
it same as 270502 with the letter D on the middle arrow. simple. if the
user wants the longest arrow upwards, he clicks pt1 and 2 accordingly...
let's not complicate a simple situation."

So Disrupt (341000) is Table H-XIX's 270502 exactly - same geometry
function, same three anchor points, same three arrowheads - in black,
with "D" set into a gap cut in the MIDDLE arrow's shaft, halfway from
the base line to that arrow's tip.

**The mirror is gone from the code, not just unused.** `_disrupt_arrows`
had grown an optional `mirrored` flag and a `_disrupt_mirrored()`
helper; both are removed rather than left as dead options that would
read as a supported feature to whoever comes next.

Worth recording why the question arose at all: "vertically mirrored" is
a statement about how the symbol looks on the page, and this
construction is defined relative to the user's own PT1 and PT2. There
was no fixed answer to implement - which is exactly what the maintainer
said back, and the right call. **Table H-XXIV's three held rows are
now all built.**

1191 tests passing on both QGIS versions.

---

### Mission Task Lines: Fix; Disrupt held back again (2026-08-15)

Fix (341100) built to the maintainer's own instruction - Table H-XIX's
270503 geometry, black, with "F" masked into the lead run at the PT2
end, that run lengthened to hold it. The mask is a gap cut into the
geometry, as on Block, and at the maintainer's explicit confirmation
("mask F the same way").

Both reach the obstacle function as OPTIONAL arguments defaulting to
the old behaviour, so Table H-XIX's own Fix is untouched - its 192
tests pass unchanged.

**Disrupt is held a second time, and the reason is better than the
first.** Its mirror and its letter are built and its geometry
evaluates, but two things would ship wrong:

- **Which end the mirror is measured against.** "Longest arrow at the
  bottom" is relative to how the STANDARD draws 270502, not to the
  order the user happens to click PT1 and PT2. This project's own
  obstacle Disrupt puts its longest arrow at PT2, whichever end of the
  screen that lands on - so "mirrored" needs the maintainer's own
  reference, or it is a coin toss that renders convincingly either way.
- **Disrupt has three arrowheads.** The obstacle version draws them
  from a separate marker layer over `mct_disrupt_arrow_tips()`; the
  mission-task symbol draws only the shafts so far.

The first render showed exactly this: a correctly mirrored, headless
Disrupt that looked finished.

1191 tests passing on both QGIS versions.

---

### Mission Task Lines begin: Block (2026-08-15)

The maintainer released the three held rows with explicit
constructions, and instructed that **everything in Table H-XXIV lives
on a Mission Tasks layer** - point, line or area. New Mission Task
Lines layer; Block (340100) is the first on it.

Their instruction: "same as defensive control measures 270501, but
default colour is black not green and the letter B (masked) on the
horizontal shaft... Construction mechanism for user for all three
remains same as 270501/2/3." So it reuses Table H-XIX's own
`mct_block_geometry()` outright rather than reimplementing a "T", with
the same three anchor points.

**The obstacle version is untouched.** The gap the letter needs reaches
it as OPTIONAL arguments defaulting to no gap - the additive pattern
this project uses whenever a signed-off helper gains a second caller.

The gap is CUT INTO THE GEOMETRY rather than masked, because Selective
Masking cannot reach a symbol layer inside a geometry generator. Its
width is the letter's own rendered width plus padding, converted from
page millimetres through @map_scale - which resolves inside a geometry
generator, as established earlier the same day.

**Two bugs the render caught, neither visible to a test:**

- **A gap in map units is not a gap in metres.** The first conversion
  stopped at ground metres and would have cut a gap five orders of
  magnitude too wide on a layer in degrees. Metres-per-unit is now
  measured on the ellipsoid at the feature's own latitude.
- **The "B" simply never drew.** `mct_block_letter_point()` called
  `mct_block_geometry` through its own decorator, and QGIS invokes a
  @qgsfunction's `.func` with an extra context argument - so the call
  raised, the expression went NULL, and the label vanished silently
  while the "T" looked perfect. The point is computed inline now.

**Disrupt and Fix are NOT in this commit.** Both need a change to the
H-XIX geometry they borrow that Block did not - Disrupt is vertically
mirrored against the obstacle version (longest arrow at the bottom),
and Fix needs its lead segment lengthened to hold the letter. Shipping
them now would have drawn the unmirrored shape. Recorded in
`TABLE_H_XXIV_LINES_NEXT` with the maintainer's own wording for each.

1191 tests passing on both QGIS versions.

---

### The two convoys; Table H-XXIII closes (2026-08-15)

Moving Convoy (330100) and Halted Convoy (330200), on the existing
Supply Routes (Lines) layer - the same table, the same geometry, and a
rule-based renderer that already keys off `measure_type`. **Table
H-XXIII is complete**, all 37 rows.

Both are a BAR of fixed page height between the anchor points with an
end piece at PT1: a forward-pointing open arrowhead for Moving, and the
same triangle REVERSED - apex back into the bar - for Halted. That
reversal is the entire difference between the two symbols. Moving's
"varies only in length" is what makes the height a page unit.

**Field A is deliberately absent** - the vehicle icon both examples draw
in the middle box, an M1A2 and an M915. The maintainer's own call:
"drop the Field A, if required, user will insert additionally; lot of
symbols where we have not included multiple fields". Fields V, H and the
W/W1 pair are all built.

The bar is two offset line layers rather than generated geometry, with
`setTrimDistanceEnd()` stopping them short of the head - a page distance
matching the page-sized head, so the two meet at every zoom without the
geometry needing to know the scale.

**Three defects the first two renders caught, all of them page-unit
sign or ratio errors:**

- **The heads sat a full head-length past PT1.** QGIS measures
  `offsetAlongLine` BACKWARD from the end at a LastVertex placement, so
  the negative offset that looked right pushed the glyph forward. The
  same marker-is-centred-on-its-vertex correction the range fans' axis
  needed, with the opposite sign.
- **Both heads drew mirrored.** A marker rotated onto a line's last
  vertex has its own +x running back along the line, not forward - so
  the SVGs are authored with the tip at x=0 and the join at x=length.
  Established by render.
- **The rear bar drew at a ninth of the body's height.** QGIS sizes an
  SVG marker by its WIDTH and that glyph is a thin, tall stroke; sized
  as the height directly it came out at the stroke-to-body ratio.

**Two numbers here are mine, not the standard's**: the bar's height
(6 mm) and the head's length (6 mm). The table draws both to no stated
proportion. Sized so one line of the shared 9 pt label sits inside the
bar with room to spare, and kept as single constants precisely because
they are the kind of thing a smoke test moves.

1191 tests passing on both QGIS versions.

---

### The remaining 27: plan and decisions taken (2026-08-15)

Agreed with the maintainer before starting, so nothing here is
guesswork later.

**The two convoys (H-XXIII, 330100/330200).** Both are fully numbered:
Moving Convoy is two anchor points, PT1 the arrowhead's tip, PT2 the
rear, "varies only in length"; Halted Convoy is the same body with an
OPEN triangle instead of a filled head, at least two points, repeating
per segment - the repeat the supply routes on this layer already do.

**Field A is deliberately not built.** Both examples draw a vehicle
ICON in the middle box (an M1A2, an M915). The maintainer's own call:
"drop the Field A, if required, user will insert additionally; lot of
symbols where we have not included multiple fields". Consistent with
the rest of this appendix, where partial amplifier sets are the norm.

**Mission Tasks (H-XXIV, 25).** Better specified than the earlier audit
implied: every row derives its whole shape from numbered anchor points,
so the only page-unit choices are the arrowhead length, the bracket
ticks and the letter glyph - all reusing sizes already signed off here.
Three batches, in this order: **arrows (9), brackets (9 of 12),
security (4)**.

**Three rows are held back to the very end**, not to be built without
the maintainer's explicit word: **Block (340100), Disrupt (341000) and
Fix (341100)**. They are the only three whose names match a symbol
ALREADY BUILT in this plugin - all three are obstacle effects in
`obstacle_control_measures.py`, under different codes and different
drawn forms.

**That number is three, not nine, and the correction matters.** An
earlier audit recorded nine rows as sharing a name with something
elsewhere in Appendix H, and this session repeated the figure without
checking it. Verified against the built vocabularies directly: Breach,
Bypass, Canalize, Clear, Delay, Isolate, Penetrate, Seize and Withdraw
have no counterpart built here at all. The near-misses that made the
old count look right are different names, not the same one - "Obstacle
Bypass Easy/Difficult/Impossible" and "Penetration Box". Six rows were
about to be deferred for no reason.

**Destroy (340900), Interdict (341400) and Neutralize (341600) are
already built** - one-anchor-point X glyphs on the Mission Task Points
layer, milsymbol-rendered, sized +30%. Which is why the remaining count
is 25 and not 28. They are back on the tracker at the maintainer's
request for a second look.

---

## Usability (U-series)

**U-1 (NATO symbol menu in the print layout) CLOSED, 2026-08-18 - "a
small win."** Raised 2026-08-17 alongside U-2/U-3/U-4 (still open,
tracked only in the build tracker artifact, not here - see the "Your
call on order" note there). A layout page is not a map canvas - no
attribute table, no ValueMap field, no feature to hold an entity or
affiliation - so this is a layout item type, not a reused canvas
path, exactly as the item's own note anticipated.

Built as a new "Insert Symbol" action on the per-Layout-Designer
toolbar `on_layout_designer_opened()` already builds (alongside the
existing Add/Remove Grid Frame), opening a small
`InsertSymbolDialog` (`military_symbology/layout_symbol_dialog.py`):
Affiliation, Symbol Set, Entity - Entity a real cascading dropdown,
repopulated from `entities_for_edition(current_edition())` whenever
Symbol Set changes, so the offered vocabulary always matches whatever
a newly-added canvas layer would use right now. Accepting it builds a
SIDC via the same `build_sidc()` every canvas layer uses, renders it
through `render_symbol_base64_path()` (the same "base64:..." inline-
SVG path format `QgsSvgMarkerSymbolLayer` already relies on), and
hands that straight to a `QgsLayoutItemPicture` - confirmed live
against the bundled QGIS Python that `setPicturePath()` accepts the
same "base64:" convention as the marker layer, so the symbol never
touches disk as a temp file. `ResizeMode.ZoomResizeFrame` keeps the
picture's own aspect ratio correct without extra code. Placed at a
fixed 20mm frame near the page's top-left corner and named after its
own entity in the Items panel (`QgsLayoutItem.setId()`); like any
other layout item it can be dragged and resized afterwards - no
custom click-to-place mouse tool was built for this pass (a genuine,
separate scope, considered and set aside rather than assumed
unnecessary).

Deliberately minimal - Affiliation/Symbol Set/Entity only, no
echelon/status/headquarters/sector modifiers - matching this
project's standing decision to leave the manual's amplifier fields
partial rather than build them out everywhere they could apply: the
picture is static, there is nothing to edit after insertion, so the
fuller amplifier set is better reached by building the symbol as a
real feature on a map layer instead. Entity labels are a plain
`key.replace("_", " ").title()` humanisation rather than the
hand-curated per-layer `ENTITY_LABELS` dicts (e.g. land_layer.py's
own `_UNIT_ENTITY_LABELS`) - those are private to their own modules
by this codebase's own convention, and importing a dozen of them into
one dialog was not worth the coupling for a small, standalone
feature. `SYMBOL_SET_LABELS` (19 entries, one per `sidc.SYMBOL_SETS`
key) is hand-written and checked by test against `SYMBOL_SETS`
itself, so a future symbol set cannot go silently missing from the
dropdown.

11 new tests (`tests/test_layout_symbol_dialog.py` plus one on the
toolbar wiring itself in `tests/test_plugin.py`), 1403 -> 1414 on
both QGIS versions; Bandit and detect-secrets both clean.

---

## Smoke testing — the unreleased 1.0.4 (closed 2026-08-18)

Every defect found across three live smoke-testing rounds this session
(see the dated entries throughout Phase 10/12 above) was fixed and
re-confirmed in QGIS. **S-3, the last item on the tracker, closed
2026-08-18: an OLD project - built and saved under the published
1.0.3 plugin, before the edition switch existed at all - still opens
and renders correctly against the current dev checkout.** Verified by
the maintainer directly: installed 1.0.3 from plugins.qgis.org into a
real QGIS 4.2.1 profile, built and saved a project with several
symbology layers and points, then swapped that profile's plugin
directory back to a symlink onto the dev checkout (matching how the
3.44.12 profile was already set up) and reopened the same project -
no errors, every layer still rendered. This was the one genuine
backward-compatibility question the edition-switch work raised (a
layer created before editions existed has no edition recorded on it
anywhere) and it holds: `edition.py`'s `current_edition()` default and
`layer_name_for()`'s un-suffixed-name fallback mean an old layer is
read as 2525D, which is what it always was, with nothing retroactive
about switching the toolbar setting afterwards.

Every S-series smoke-test item is now cleared; the build tracker's
own SMOKE unit has been removed as a result, per the maintainer's own
"remove cleared items" instruction.

---

## Menu polish (2026-08-18)

Three small, related UI fixes raised directly by the maintainer, not
tracked on the build tracker - not urgent enough to hold up 1.1.0, but
folded into it since they were quick.

**NATO Symbols and Control Measures menus alphabetised.** Both had
been ordered by the standard's own layout (appendix order for NATO
Symbols; H.5.x section order for Control Measures) rather than by
label - reasonable for a table that mirrors a printed manual, but this
is a plain "pick one of many" dropdown with no standards-table reason
to keep that order. `plugin.py`'s `_setup_toolbar_groups()` NATO
Symbols item list reordered in place; `_setup_control_measures_menu()`
kept every action's own construction (and its tooltip, sourced from
the standard) exactly where it was, but decoupled insertion from
construction - the 18 interleaved `addAction()` calls became one
batched, alphabetically-ordered loop at the end of the function, so
the order lives in one place rather than being implied by construction
order. Two existing tests had pinned the old order and needed
updating, not just extending.

**"Supply Points" renamed "Supply Control Measures" in the Control
Measures menu.** Raised by the maintainer noticing that clicking
"Supply Points" adds three layers (Points/Lines/Areas), while the
separate "Sustainment Points" entry genuinely adds only one - asked
whether Sustainment Areas belonged under Sustainment Points instead,
and whether both labels should read "...Measures". Checked against
the module docstrings rather than assumed: `supply_points.py` and
`sustainment_control_measures.py` build from two genuinely different
standard tables (H-XXIII "Supply point control measure symbols" and
H-XXII "Sustainment point control measure symbols" respectively) -
Sustainment Areas is Table H-XXIII's own area geometry, not H-XXII's,
so the DATA grouping is correct as built and moving it would
misrepresent which table it belongs to. The LABEL was the real
problem: "Supply Points" promised only points while building three
geometry types, unlike every other multi-type entry in the same menu,
which all use "...Control Measures" - renamed to match that
convention rather than the maintainer's own suggested "...Measures"
(without "Control"), to stay consistent with its 15 siblings.
Along the way, found `create_supply_points()`'s own docstring flatly
contradicted its function body - it claimed the seven sustainment
areas "are not built", three lines above a call to
`add_sustainment_areas_layer()` that builds them. Fixed to describe
all three layers; the action's tooltip was similarly incomplete
(named only two of the three) and is now complete too.
`docs/user-guide.md`'s own Control Measures overview updated to
match.

**Newly-added symbology layers now insert collapsed, not expanded.**
Raised by the maintainer building a real map: several layers added at
once (one domain click on Land adds four; one Control Measures click
routinely adds two or three) previously all landed expanded in the
Layers panel, and control-measure layers in particular render via
`QgsRuleBasedRenderer` - one rule per placement - so an expanded node
can show many legend rows each. Both of the module's own
`default_insert_position()` implementations
(`military_symbology/_point_symbol_layer.py`,
`military_symbology/_control_measure_shared.py` - the two functions
every symbology layer's insertion routes through, confirmed by
grepping for any other definition) now call `.setExpanded(False)` on
the `QgsLayerTreeLayer` node `QgsLayerTreeGroup.insertLayer()`
returns, rather than leaving the newly-created node's default
(expanded) state untouched.

3 new tests, 1414 -> 1417 on both QGIS versions; Bandit and
detect-secrets both clean.

---

## IDX smoke-testing round: L09/L12-15, A09-14, P01, M01-04 (2026-08-18)

Every row the maintainer checked in this pass came back clear except
four findings, three acted on and one investigated and reported back
rather than guessed at.

**Dummy Minefield, Dynamic's decoy chevron moved closer to the
shape.** "The chevron - as close as possible to the area without
touching or overlapping, say 1mm gap." The chevron is real map-unit
geometry (a `QgsGeometryGeneratorSymbolLayer`, not a fixed-size
marker), so a literal print-scale millimetre isn't directly
expressible - tightened to a small, fixed FRACTION of the shape's own
height instead (0.02, was 0.12 - a `translate()` multiplier of 0.72,
was 0.82, in `_dynamic_minefield_symbol()`), which reads as close on a
small minefield and a large one alike, unlike a fixed map-unit gap
would. The chevron's own internal proportions (apex height, arm
spread, inside `mct_decoy_chevron()`) are untouched - only the whole
chevron's distance from the polygon moved. 3 new tests
(`TestDummyMinefieldChevronGap`) confirm the gap is present (not
touching), small, and proportional to the shape's own size.

**Trip Wire's known problem has a sibling: Abatis.** "Change to
symbol - already flagged earlier" (Trip Wire, U-4) and "Abatis -
change to symbol" (new). Checked Abatis's own construction rather
than assuming it shares Trip Wire's exact defect: it does not - Trip
Wire is a repeating marker riding an arbitrary-length line with no
size of its own, where Abatis's single triangular kink
(`mct_abatis_line()`) is deliberately sized as a fixed 6% of the
line's own length, "so the symbol scales with the feature" per its
own docstring. Different mechanism, same maintainer ask: a point
symbol with a real page size, not one that scales with however long a
line gets digitized. U-4 (build tracker) widened to cover both,
un-fixed here - this is the same category of work as Trip Wire's own
entry (a layer move, a migration story for existing features, and
overlap with U-2's rotation work), not a quick tweak, so it stays
tracked rather than rushed.

**Obstacle Control Measures (Lines)'s own tooltip was stale.** It
described only the wire-obstacle family (9 codes) and said "the
table's lines are being built in later batches" - true when written,
false since batches B5-B7 landed (obstacle effects, bypasses/
roadblocks, and crossings), which is most of the layer's own 35
entries. Rewritten to name all four sub-layers (Points/Areas/
Minefields/Lines) and describe the Lines layer's actual current
scope.

**"The menu count is 33 while your count is 35" - investigated, not
found.** Checked directly rather than assumed: `LINE_MEASURE_TYPE_
LABELS` (`obstacle_control_measures.py`) has exactly 35 keys, all 35
labels are distinct (no collision that would silently collapse two
entries into one dropdown row), and building the real layer and
reading its `measure_type` field's own `ValueMap` editor config back
confirms 35 selectable entries, matching the IDX tracker's own count
exactly. No discrepancy found in the data or the widget config this
session's tools can inspect - reported back to the maintainer rather
than "fixed" against a guess, since chasing a phantom bug with no
reproduction is worse than asking where the 33 came from (a hand
count while scrolling a long dropdown is an easy place for this kind
of small miscount, but that is a guess, not a finding). **Confirmed
the same day**: a hand-count miscount, no bug.

3 new tests (`TestDummyMinefieldChevronGap`), 1417 -> 1420 on both
QGIS versions; Bandit and detect-secrets both clean.

---

## IDX smoke-testing round: A01-08, L01-15 (2026-08-18)

A01-03 and L01-08 all clear. Four real findings among A04-08, each
investigated against the actual construction rather than patched on
the label alone.

**A08, Limited Access Area (`maneuver_control_measures.py`): its
designation label was never masked.** "The text is not masked; for
all other areas the unique designator [is]." Every other area on this
layer has a plain or no fill, so an unmasked label just sits on open
map background and reads fine; Limited Access Area is the only one
with an actual hatch PATTERN, and the layer's own
`_configure_designation_labeling()` call had no `masked_symbol_layer_ids`
at all - not a Limited-Access-specific bug, but the one area type it
was ever going to be visible on. Gave the hatch layer a stable id
(`laa_hatch`) and wired it into the mask. Found and fixed the same
latent bug alongside it while in the code: the hatch's own affiliation
colour was set on the fill layer itself rather than its sub-symbol -
`QgsLinePatternFillSymbolLayer` paints through a sub-symbol, so a
data-defined colour on the fill layer is silently ignored, the
identical latent bug already found and fixed in Weapons Free Zone and
No Fire Area's own hatches. 3 new tests.

**A07, Position Area For Artillery (`fire_support_coordination_
measures.py`): its four perimeter labels could land outside the
shape.** "The text is not always on the perimeter line, sometimes it
goes out of the area also especially in irregular polygons." Each
anchor was a raw bounding-box edge midpoint - exact for the standard's
own two prescribed shapes (Rectangle, Circular), but nothing stops a
user digitizing a third, and a bounding-box point can fall outside a
concave boundary entirely. Each anchor now wraps that same target
point in `closest_point(boundary($geometry), ...)`, snapping it onto
the actual boundary - a no-op for the two prescribed shapes (confirmed
by test: anchors land at the exact same coordinates on a true
rectangle) and correct for whatever a user actually draws (confirmed
on a concave polygon: every anchor lies exactly on its boundary). 2
new tests, one existing test's pinned expression updated.

**A05, Radiation Dose Rate Contours (`cbrn_defense.py`): the "cGy"
unit is now suffixed automatically.** "Can we suffix cGy to the
unique designation rather than expecting the user to type it in,
usually the user will enter only the number." The field itself still
stores whatever is typed (typing the full "300cGy" still works,
unchanged), but the LABEL expression now appends "cGy" unless it is
already there, so typing "300" alone is enough. 3 new tests.

**A04, Minimum Safe Distance Zones (`cbrn_defense.py`): the ring
breaks were too wide, and close-together ranges could drop a label
entirely.** "The mask is too much, and due to the overlapping labels -
some of the labels are hidden." Two distinct causes, both fixed:
(1) `_SAFE_DISTANCE_LABEL_PADDING_MM` (breathing room either side of
the label inside its own ring's break) was 1.4mm - nearly half the
~3.2mm label height per side - tightened to 0.7mm, roughly this
codebase's own established "just enough" buffer size (`mask_size_mm`'s
1.2mm default elsewhere). (2) Each ring's own label rule had no
`displayAll`, so PAL's default collision handling could silently drop
a label when two rings' ranges sit close together (all five labels sit
due east of the same centre, at different radii) - the identical
symptom the maintainer had already found and fixed for Radiation Dose
Rate Contours' own nested-contour case, never applied here even though
this feature is explicitly built as "the same construction as the
Weapon/Sensor Range Fan." 2 new tests.

9 new tests, 1420 -> 1429 on both QGIS versions; Bandit and
detect-secrets both clean.

---

## IDX smoke-testing round: L10, L11 (2026-08-18)

Both investigated empirically - rendered the actual symbol and
inspected the pixels, rather than reasoning about GEOS/font behaviour
in the abstract, since both turned out to be exactly the kind of
thing that abstract reasoning gets wrong.

**L10, Electro-Optical Intercept's "O" had a dot leaking through it
(`maritime_control_measures.py`).** "The O label has a dot in it -
maybe the line leaking through." Confirmed by rendering the actual
symbol: the abbreviation's own Selective Masking uses the shared
1.2mm `mask_size_mm` default, and for the one bearing-line
abbreviation with a genuine enclosed counter ("O"), that default
doesn't reliably close it, leaving the underlying line visible as a
small dot in the middle of the letter. The fix was found by rendering,
not derived: GEOS buffer size vs. a glyph's own outline is not simply
"bigger is better" - 1.2/1.4mm leaked, 1.6-1.8mm rendered a clean "O",
2.0mm leaked again, checked across three render resolutions (150/300/
600 DPI) to rule out a DPI-specific fluke. `mask_size_mm=1.7` (the
middle of the confirmed-clean band) applied to both of this layer's
label rules; also confirmed clean on every other abbreviation here,
including the other two with their own enclosed counters (B, RDF). 1
new test.

**L11, Mission Task Lines' Fix lost both its zigzag and its own
letter on a short PT1-PT2 (`expressions/military_symbology_
functions.py`).** "If the line is short, the kinks dont form and even
the letter F goes missing." Confirmed by direct expression evaluation
(not just reading the code): `mct_fix_geometry()`/`mct_fix_letter_
point()` shared a single all-or-nothing threshold - two full-size flat
runs, one full-size tooth, AND the letter's own reservation all had to
fit before either function drew anything, so a PT1-PT2 under that
threshold showed a bare straight line with no letter. Presented to the
maintainer as a design question, not a one-line bug fix, since several
genuinely different ways to degrade were all defensible (drop teeth
first, shrink teeth to fit, or just report the real minimum length) -
**"shrink the teeth to fit" was the maintainer's own call.** New
shared helper `_fix_effective_tooth_length()` shrinks the tooth size
(never beyond its own PT3-derived nominal size) down to whatever fits
exactly one tooth alongside the letter, called identically from both
functions so the letter's own position always matches whatever gap
the teeth actually cut; the letter drops - never the tooth - only as a
true last resort, when PT1-PT2 is too short even for the letter's own
reservation alone. One real bug caught verifying this empirically
rather than trusting the algebra: solving for the exact "one tooth
fits" boundary left the later `usable // tooth_length` floor division
sitting on a floating-point knife edge, occasionally rounding down to
zero teeth right at that boundary - fixed with a 0.1% margin, found by
testing across a range of lengths, not assumed safe. 5 new tests.

6 new tests, 1429 -> 1435 on both QGIS versions; Bandit and
detect-secrets both clean.

---

## Symbol index (IDX) — complete (closed 2026-08-18)

**Every hand-built row checked against the standard: all 15 line
layers (L01-L15), all 14 area layers (A01-A14), the one point layer
(P01), and all three modified-milsymbol-icon entries (M01-M03) - 33
rows in total.** The maintainer's own systematic pass, table by table,
across several rounds this session.

Most rows came back clean outright. Where they didn't, each finding
was investigated against the actual construction (not patched on the
symptom alone) and is recorded in its own dated entry above:
Position Area For Artillery's perimeter anchors leaving the boundary
on irregular polygons (A07), Limited Access Area's unmasked label and
a second latent hatch-colour bug found alongside it (A08), Radiation
Dose Rate Contours' now-automatic "cGy" suffix (A05), Minimum Safe
Distance Zone's tightened gap and fixed label-collision handling
(A04), the Dummy Minefield decoy chevron's gap (P01), Electro-Optical
Intercept's mask leak (L10), and Mission Task Fix's shrink-to-fit
degradation on short lines (L11) - the last of these a real design
question put to the maintainer rather than guessed at. One reported
count discrepancy (Obstacle Control Measures Lines, L12) was
investigated and confirmed to be a hand-count, not a bug. Two
follow-on items (Abatis, alongside the already-tracked Trip Wire)
were found to need the same kind of construction change and folded
into the build tracker's own U-4 rather than rushed.

The build tracker's own IDX unit has been removed as a result, per
the maintainer's standing "remove cleared items" instruction - this
entry is the permanent record of the pass.

---

## U-2, first landing: rotation and scale on the shared point-layer builder (2026-08-19)

**Scope, by the maintainer's own choice**: land the mechanism in
`military_symbology/_point_symbol_layer.py` - the shared builder behind
Land, Air, Sea Surface, Subsurface, Space, Cyberspace, SIGINT and
Activities - rather than touching the ~15 other modules that build
their own point renderer (`c2_measures.py`, `obstacle_control_
measures.py`, `maritime_control_measures.py`, and the rest). Those stay
tracked as their own follow-up pass rather than folded in here.

**Two fields, added unconditionally** (not opt-in like echelon/
headquarters/sector1/sector2 above them): `rotation` (degrees,
clockwise from north - the same convention QGIS's own marker "Rotation"
data-defined property already uses, so a heading typed here matches a
compass or GPS-track bearing) and `scale` (percent of the layer's own
base marker size, 100 = unchanged). Both use QGIS's "Range" spin-box
editor widget (0-360°, 10-400%) rather than a free-text field, with a
field alias naming the unit since the Range widget itself has no
suffix option.

**Wiring**: `rotation` drives the marker's `QgsSymbolLayer.Property.
Angle` directly (`coalesce("rotation", 0)` - an unset field draws
unrotated rather than nulling the icon out, same guard pattern as every
other per-feature read in this expression). `scale` multiplies the base
size BEFORE `stabilised_point_size_expression()`'s own designation-
text compensation is applied, so the two compose correctly - a scaled-
up icon still holds its own size when a unique designation is typed
into it, rather than the compensation ratio being thrown off by
computing it against the un-scaled size.

**"Rotate as one unit" was raised mid-build** - the maintainer's own
words: "keep in mind any addition eg modifiers, field t etc - all of
them should be rotated as one unit of the symbol." Checked rather than
assumed: this module builds exactly ONE `QgsSvgMarkerSymbolLayer` per
feature (`QgsMarkerSymbol()`'s default single layer, never added to),
and `mct_sidc_svg()` bakes the icon, every amplifier (echelon ticks,
headquarters underline, Field T/T1 designation) into ONE rendered SVG
picture, which is what that one layer's Angle property rotates as a
whole - there is no second, separately-positioned renderer for the
text. Confirmed by rendering a friend Infantry Battalion ("1AD",
echelon ticks "II") at rotation=0 and rotation=90: the box, its
echelon ticks and its designation text all turned together, staying in
the same relative position to the box at both angles. Separately
confirmed scale=200 renders visibly larger than scale=100 at the same
rotation. (The other ~15 modules deferred to the follow-up pass will
each need this same check individually - several may draw a
designation via QGIS's own PAL labelling instead of baking it into the
SVG, which would NOT rotate with the icon the same way.)

7 new tests (`TestRotationAndScaleFields` in `tests/test_point_symbol_
layer.py`): field presence, Range widget config, default values
("0"/"100"), rotation driving Angle (including the unset-field-draws-
unrotated case), and scale multiplying size 2x-for-2x (including the
unset-field-draws-at-100%-case). 7 existing layer-module tests (air,
sea surface, subsurface x2, space, sigint, cyberspace, activities) that
pinned the exact field list needed the two new fields appended - not a
regression, just an assertion that had to catch up to a real schema
change. 1435 -> 1442 tests on both QGIS versions; Bandit and
detect-secrets both clean.

Follow-up, not yet started: the same mechanism in the ~15 modules that
build their own point renderer - each needs the same "is the text baked
into the same SVG, or drawn separately" check before Angle can be
wired in safely.

---

## U-4: Trip Wire and Abatis become point symbols (2026-08-19)

**Both moved from the Obstacle Control Measures (Lines) layer to the
Points layer**, drawn as fixed page-size glyphs oriented by a
"rotation" field, replacing constructions whose every dimension had
derived from however long a line the user happened to digitize -
Trip Wire (290500) without limit (a dictated construction built
2026-08-13 from two anchor points), Abatis (280100) by a smaller but
real fraction (`mct_abatis_line()`'s own `size=0.06`, calibrated for an
arbitrarily long obstacle line). Design decisions confirmed with the
maintainer before building (layer placement, rotation workflow, old-
line migration) - see the three-question exchange this session; all
three "recommended" options were chosen: land on the EXISTING Points
layer rather than a new one, set facing by typing into the rotation
field rather than a two-click bearing tool, and accept the break for
any line feature already digitized under the old (buggy) construction
rather than keep both offered.

**Two real implementation passes, same day - the first one retired
after being confirmed broken by an actual render, not by reasoning
about the code.** First pass: `mct_trip_wire_point_geometry()`/
`mct_abatis_point_geometry()`, real map-unit geometry via a
`QgsGeometryGeneratorSymbolLayer`, converting a page-mm size to ground
units through `@map_scale` (the same `_page_gap_in_map_units()`
pattern every other fixed-size element in this module uses), rotated
by wrapping the result in QGIS's own `rotate(...)`. Evaluated correctly
against a direct `QgsExpression` check with a real `QgsMapSettings`
scope - but rendered NOTHING through QGIS's actual render pipeline,
confirmed by three independent render attempts (`QgsMapRendererParallelJob`
and `QgsMapRendererCustomPainterJob` both, ruling out a Parallel-job-
specific quirk). Narrowed, not just noticed: reproduced with a minimal
two-layer marker symbol built entirely outside this module, and traced
to QGIS computing the whole marker's own render/clip bounds from
symbol layer 0's reported size BEFORE per-feature data-defined
properties are evaluated - an SVG marker layer with a data-defined
Size that resolves to 0 (needed to hide it for these two entities, so
the geometry generator layer could draw instead) zeroed the bounds for
every layer after it too, not just itself. Reordering the two layers
(geometry generator first) fixed the render in isolation - confirmed
live - but that fix would have required every existing test asserting
`symbolLayer(0)` is the SVG layer on this Points layer to be rewritten
around a fragile index instead of a stable "which layer has an active
Name property" search.

**Second pass, while implementing that reorder fix, landed on a better
design instead of shipping the workaround**: `mct_trip_wire_svg()`/
`mct_abatis_svg()`, fixed inline "base64:<...>" SVG markers - the exact
pattern `mct_decoy_chevron_svg()` already established for a hand-drawn
glyph that must not scale with the map. This sidesteps `@map_scale`
inside a geometry generator entirely (confirmed unreliable there in a
live render, contradicting this project's own 2026-08-15 note that it
"DOES resolve inside a geometry generator" - that earlier probe
evidently covered a different case; not chased to a root cause once
the working alternative was confirmed) and reuses the SAME Angle/Size
data-defined properties every other point icon in this project already
has (U-2's own mechanism) - no `rotate()`, no second symbol layer, no
layer-ordering fragility. Both new SVG functions take `colour` and
`dashed` arguments the same way `mct_decoy_chevron_svg()` does; Trip
Wire keeps the maintainer's own dictated proportions exactly (0.5x/1.2x
crossbars, 0.2x arc radius, now against a fixed 60-unit "line" instead
of a digitized PT1-PT2 span); Abatis drops the retired construction's
long lead-in/trail-off run (meaningful only when interrupting a real,
arbitrarily long digitized line, a concept a point icon does not
carry) and keeps just the kink itself, sized up from the old 6% (which
would have drawn sub-millimetre against a small fixed icon) to read
next to this layer's own milsymbol siblings - a first render-verified
guess, screenshot sent to the maintainer for their own visual call, the
same way every other page-size constant in this project has been
tuned.

**Where the two custom entities live**: `_CUSTOM_SHAPE_POINT_LABELS`,
deliberately separate from `POINT_ENTITY_LABELS` (the real milsymbol/
2525D vocabulary every existing test walks expecting a real SIDC
entity) and merged into the layer's own entity dropdown only at the
attribute-form level. Rotation only affects these two entities on this
layer - deliberately not extended to the other 13 real milsymbol
entities here, which is the deferred U-2 rollout's own job, not U-4's.

`TABLE_H_XIX_INVENTORY`'s own "geometry" tag for both rows flipped from
LINE to POINT (a second reversal for Abatis specifically - it was moved
points-to-lines once already, 2026-08-12/H17, for a template-reading
reason; this one is a deliberate trade, not a correction) - this field
records how the symbol is actually drawn in this plugin, not a frozen
record of the standard's own template, so it follows the real
construction the same way the minefield family's own geometry
corrections did earlier in this appendix.

7 new tests for the two SVG functions, 9 for the Points-layer wiring
(entity dropdown, colour/dashing/rotation/scale each verified via the
actual data-defined properties, not assumed from the expression text),
plus fixes to every pre-existing test that depended on Trip Wire/Abatis
being on the Lines layer, on Abatis being excluded from every points
dropdown (the 2026-08-12/H17 guard in `tests/test_point_layer_
affiliations.py`, narrowed to name this layer as the one deliberate
exception rather than deleted), and on `symbolLayer(0)` being the SVG
layer specifically. 1442 -> 1444 tests on both QGIS versions (heavy
churn along the way from two full construction rewrites in one day,
not just net-new coverage); Bandit and detect-secrets both clean.

**Abatis's own kink corrected the same day, after the maintainer saw
the render**: "reduce the kink by 40% and shift it closer to the
beginning - the line segments should be in a ratio of about 1:4." The
first render-verified guess had it centred near the icon's own
midpoint; `mct_abatis_svg()`'s path numbers now put the kink's apex
offset at 8 (was 14) and its span at 6-16 of the 40-unit icon (was
12-28), solved so the straight run before the kink (6) to the run
after it (24) comes out to exactly 1:4. Confirmed by render, not just
by the numbers - see that function's own docstring for the full before/
after.

**Trip Wire widened and Abatis rebuilt a second time, same day, after
the maintainer's own smoke test of both fixes above**: "Tripwire line
width is too less, increase by 50%, increase overall size by 10%.
Abatis basic size is too big and by default it is rotated 90 degrees.
Rotate it 90 degrees clockwise and reduce size to match that of
tripwire. match abatis line width to the tripwire line width." Two
separate root causes, found by actually comparing the two icons side
by side (rendered together for the first time this pass, not
separately as before):

- Trip Wire's own stroke width (4 SVG units, on a 144-wide declared
  canvas) rendered under a quarter of a millimetre at this layer's
  default marker size - far thinner than any milsymbol icon sharing
  the layer. Raised to 6 in all three of `mct_trip_wire_svg()`'s paths.
- Abatis's declared canvas (12 wide, 44 tall - a vertical build, kink
  deviating in X) was over 7x taller than wide, next to Trip Wire's own
  144-wide/72-tall (2x wider than tall) canvas - almost certainly what
  read as "rotated 90 degrees, too big" once the two were compared.
  Rebuilt to adopt Trip Wire's own canvas and stroke width EXACTLY
  (144x72, stroke 6), with the same kink proportions from the fix
  above rotated 90 degrees clockwise into it (main run now horizontal,
  deviating in Y) and rescaled proportionally to the new canvas - still
  exactly a 1:4 stub-in:stub-out ratio.
- The "overall size +10%" is a new `_CUSTOM_SHAPE_SIZE_MULTIPLIER`
  (1.10) in `obstacle_control_measures.py`, applied to both entities'
  shared marker-size expression rather than to either SVG's own path
  numbers - QGIS scales an SVG marker uniformly from its declared width
  to a target millimetre size, so one multiplier grows path and stroke
  together for both icons at once, keeping them in lockstep now that
  they share a canvas.

Confirmed by rendering both icons side by side, unrotated and at 90
degrees: Abatis now reads as comparably sized to Trip Wire, both
strokes visually match, and the 90-degree rotation behaves consistently
across both. 1444 tests on both QGIS versions (no test pinned exact
path coordinates, only structure - colour, dash, path count); Bandit
and detect-secrets both clean.

---

## U-3: milsymbol stroke width, applied globally (2026-08-19)

**Scope check first.** Asked to fix "too thin" lines, the maintainer's
own audit of the icon set found roughly 40 entities across a dozen-plus
modules - the basic Checkpoint/Contact Point/Decision Point/reference-
point family, every Observation Post variant, Target Reference Point,
CBRN event triangles, Sonobuoys, and similar - all sharing the same
thin, unfilled milsymbol frame. Asked directly: "instead of doing this
one by one, can we just increase the line width by 50% across all
milsymbols for lines? is that easier?"

**A working global mechanism already existed, unused.** `mct_sidc_svg()`
has had an optional fifth argument, `stroke_scale`, wired all the way
through `render_symbol_base64_path()`/`scale_svg_stroke_width()` since
earlier this session - but no caller (~26 call sites across the plugin)
had ever passed it. It multiplies every `stroke-width="X"` in the
RENDERED svg markup directly - deliberately NOT milsymbol's own native
`strokeWidth` option, which `scale_svg_stroke_width()`'s own docstring
records as broken: probed directly, that option only widens the
generated viewBox (108 -> 110.8), leaving every path's own stroke-width
unchanged - it makes the icon draw SMALLER at a fixed marker size, not
thicker.

**Two rounds of render comparison before deciding anything**, both
requested directly rather than assumed:

1. A thin unfilled Checkpoint against a filled Infantry unit box, each
   at 1.0x and 1.5x. Confirmed live: `stroke_scale` has no way to tell
   "thin frame-only icon" from "filled unit box" apart - it thickens
   the outline and internal glyph lines on BOTH. Global was going to
   mean literally global, not "every thin icon", and the maintainer
   needed to see that plainly before choosing.
2. Five of the plugin's own busiest icons - Radiological Event,
   Decontamination Point, SIGINT Communications, Miniaturized
   Satellite, Drifter - each at 1.0x and 1.5x, to check nothing goes to
   mud at a higher stroke weight on fine internal linework. None did;
   Communications' own delicate antenna glyph (the busiest of the
   five) held up legibly even at 1.5x, just visibly fuller at its
   joints.

**Landed at 1.3x** - the maintainer's own choice after both
comparisons, between the 1.5x first tried and milsymbol's own
unscaled 1.0x. `DEFAULT_STROKE_SCALE = 1.3` in
`expressions/military_symbology_functions.py`, applied as the
FALLBACK for `mct_sidc_svg()`'s/`mct_sidc_svg_width()`'s own
`stroke_scale` argument rather than a new call anywhere - since every
existing caller omits that argument, changing its own default in one
place reaches all ~26 of them without touching any caller's own
expression text. A caller that ever needs a different value (or
milsymbol's own true 1.0x) still can, by passing its own fifth
argument.

**Deliberately not touching Trip Wire/Abatis** - those are hand-built
inline SVGs (`mct_trip_wire_svg()`/`mct_abatis_svg()`), never routed
through `mct_sidc_svg()` or milsymbol at all, and were already widened
directly in the entry above, the same day.

One existing test (`test_cbrn_defense.py`'s
`test_an_empty_designation_leaves_the_icon_alone`) compared a layer's
own rendered icon against a hand-computed "reference" that called
`render_symbol_svg()` directly, bypassing `mct_sidc_svg()` entirely -
correct before this change, since both sides were equally unscaled;
updated to wrap that reference in `scale_svg_stroke_width(...,
DEFAULT_STROKE_SCALE)` too, matching what the layer itself now
actually draws. 2 new tests confirm the default applies when the fifth
argument is omitted and that an explicit value still overrides it.
1444 -> 1446 tests on both QGIS versions.

---

## U-4 — closed (2026-08-19)

Smoke-tested by the maintainer and confirmed clear, covering rotation,
scale, colour, dashed/planned status, and a side-by-side size check
against the layer's own milsymbol siblings on both Trip Wire and
Abatis - including the corrected kink (this same day) and the widened
canvas/stroke match to Trip Wire (this same day). The build tracker's
own U-4 item has been removed as a result, per the maintainer's
standing "remove cleared items" instruction; this entry is the
permanent record of the pass. U-2's own rollout to the ~15 modules
that build their own point renderer, and U-3's smoke test, remain open
on the tracker.

---

## U-3 — closed (2026-08-19)

Smoke-tested by the maintainer and confirmed clear. Build tracker's
own U-3 item removed per the standing "remove cleared items"
instruction; the U-3 entry above (global 1.3x stroke scale) is the
permanent record.

---

## U-2 rollout — the remaining ~15 modules (2026-08-19)

Extends rotation and scale to every module that builds its own point
renderer instead of going through `_point_symbol_layer.py`'s shared
builder - the follow-up explicitly deferred when U-2 first landed. An
investigation pass first cut the "~15" figure down to the real count:
of every `military_symbology/*.py` file constructing a
`QgsSvgMarkerSymbolLayer`/`QgsMarkerSymbol`, only **six** build a
genuine standalone point-icon layer that didn't already have this
wiring - `airspace_control_measures.py`, `c2_measures.py`,
`defensive_control_measures.py`, `maritime_control_measures.py`,
`offensive_control_measures.py`, `target_control_measures.py`. The
rest either already delegate to the shared builder
(`cbrn_defense.py`, `field_fortification.py`,
`mission_task_control_measures.py`, `supply_points.py` - no work
needed) or construct markers for something other than a point icon
(line/area decorations in `maneuver_control_measures.py` and its `_2`
sibling; `target_acquisition_control_measures.py`'s Range Fans layer,
which has no icon glyph at all to rotate - flagged, not folded in
here, a separate design question if it's ever wanted).

Each of the six got the same treatment `obstacle_control_measures.py`
already established for U-4: two new fields (`rotation`, `scale`) via
`configure_rotation_and_scale_fields()` - the shared widget/default/
alias helper in `_control_measure_shared.py`, exercised directly for
the first time this pass in its own new test file
(`test_control_measure_shared.py`) rather than only indirectly through
each caller - `"scale"` folded into the base size expression BEFORE
`stabilised_point_size_expression()`'s own designation-compensation
ratio (same ordering as U-2's first landing, so a scaled icon still
holds its size when a designation is typed into it), and `"rotation"`
wired to the marker's own `Angle` property.

**Two modules needed more care.** `c2_measures.py` (Distress Call) and
`defensive_control_measures.py` (Forward Observer) each draw a SECOND
symbol layer on top of the SVG icon - a small diagonal anchor line
milsymbol.js's own icon has no slot for, built via
`QgsSimpleMarkerSymbolLayer` at a fixed base angle. Setting Angle only
on the icon would have left these lines standing still while the icon
turned, breaking the maintainer's own explicit requirement from
earlier this session ("any addition eg modifiers, field t etc - all of
them should be rotated as one unit of the symbol"). Fixed by ADDING
`"rotation"` to each line's own fixed base angle (data-defined,
`f'{base_angle:g} + coalesce("rotation", 0)'`) rather than replacing
it - `QgsSimpleMarkerSymbolLayer`'s own `angle` property already
rotates both the drawn line AND its own pre-computed `offset` together
around the feature's point (documented and confirmed by render in this
project already, see `_distress_call_anchor_line_offset()`'s own
comment), so no separate offset recalculation was needed - just the
same rotation value added to what was already there. Confirmed by
rendering Distress Call and Forward Observer at 0/90/180/270 degrees:
both anchor lines stay attached to their icon at every angle. `"scale"`
was also applied to each line's own length, though its static `offset`
is not re-derived for scale - a minor, accepted cosmetic gap on these
two entities' own decorative lines at extreme scale values, not the
icon itself.

6 new/extended test files (one per module, plus the new shared-helper
test file), 1446 -> 1463 tests on both QGIS versions.

---

## 1.1.0 — moderator approved, live on plugins.qgis.org (2026-08-19)

Confirmed by the maintainer. Uploaded and security-checked earlier this
session (see this file's own 1.1.0 housekeeping/packaging entry above),
now live for every user - the same milestone 1.0.3 reached 2026-08-17.
Everything since that upload - the menu polish, the full IDX symbol-
index pass, U-1 through U-4, and U-2's own rollout - was built AFTER
1.1.0 was already packaged and uploaded, so none of it shipped in this
release; it accumulates for the next one, per this project's standing
"fixes accumulate for the next version" policy.

---

## U-2 rollout: fix the anchor lines' own offset at non-100% scale (2026-08-19)

Found by the maintainer's own smoke test of the six-module rollout
above: "when we scale the distress call the line shifts - if we
increase the scale, the line shifts slightly right of the point, if we
decrease it moves left and appears detached" (c2_measures.py) and "when
we scale up i.e. increase, the line is going out of the triangle's
sides; even when we reduce the scale, the line is not correct"
(defensive_control_measures.py). Rotation was fine on both - only
scale broke.

Root cause: both anchor lines' `offset` (a `QgsSimpleMarkerSymbolLayer`
property that shifts the drawn line so it starts AT the feature's own
point rather than being centred on it) was left as the FIXED vector
computed for the line's own 100%-scale length, while `Size` (the
line's own drawn length) was correctly scaled. At any scale other than
100%, the line's own drawn length no longer matched the fixed offset
that positions it - too little offset at scale > 100% (the line
reaching back past its own intended start, reading as "shifted right/
into the icon"), too much offset at scale < 100% (the line's own
nearest point pulled away from the icon entirely, reading as
"detached"). The U-2 rollout entry above called this "a minor cosmetic
gap" - the maintainer's own report shows it was worse than that call
allowed for.

Fixed by making `offset` data-defined too, in both
`_distress_call_anchor_line_layer()` (c2_measures.py) and
`_forward_observer_anchor_line_layer()` (defensive_control_measures.py):
the same fixed (x, y) vector, both components multiplied by the
identical `coalesce("scale", 100) / 100.0` factor already used for
`Size`, so the offset's own magnitude always matches the line's own
current length. Confirmed by rendering both at scale 50/100/200/300 -
the line now stays attached at the icon's own edge, proportionally, at
every size. 2 new tests (one per module) pin the offset's own value at
three scale factors against the base vector; 1463 -> 1465 tests on
both QGIS versions.

---

## U-2 rollout: Obstacle Control Points' remaining 13 entities (2026-08-19)

Raised as a question by the maintainer after smoke-testing the six-
module rollout: "I think you've missed obstacle control points, field
fortification, cbrn, supply points, sustainment points, mission
tasks?" Checked all six directly rather than assumed - five of them
(`field_fortification.py`, `cbrn_defense.py`, `supply_points.py`,
`sustainment_control_measures.py`, `mission_task_control_measures.py`)
already delegate their own Points layer to
`build_single_domain_point_layer()`, which has had working rotation
and scale since U-2's very first landing - confirmed by evaluating a
real feature's own Angle/Size properties on each, not just reading the
code. **Obstacle Control Measures Points was the real gap**: U-4's own
first landing had deliberately scoped rotation/scale to Trip Wire/
Abatis only, leaving this layer's other 13 milsymbol entities
(Antipersonnel Mine, both Towers, and the rest) unable to rotate or
scale at all - a genuine, intentional-at-the-time deferral, not an
oversight, but one the maintainer now wants closed.

`_CUSTOM_SHAPE_ANGLE_EXPRESSION` simplified from a CASE scoped to Trip
Wire/Abatis to a plain `coalesce("rotation", 0)` applying to every
entity; `_CUSTOM_SHAPE_SIZE_EXPRESSION`'s own ELSE branch (the 13
milsymbol entities) now folds `"scale"` into the base size expression
before `stabilised_point_size_expression()`'s designation-compensation
ratio, the same ordering every other module in this rollout uses.
Confirmed by rendering Antipersonnel Mine and Tower Low at several
rotation/scale combinations. One existing test
(`test_an_ordinary_entity_is_unaffected`) pinned the OLD deferred
behaviour and was replaced with two: one confirming an ordinary entity
still renders its real icon, one confirming it now rotates and scales
like every other entity on the layer. 1465 -> 1466 tests on both QGIS
versions.

**Caveat found the same day, while the maintainer smoke-tested this
fix**: an Obstacle Control Measures Points layer already sitting in a
saved project (added before this fix landed) does not pick up
rotation/scale after just updating the plugin and reopening that
project - rotation and scale stay inert, exactly as before, on that
one already-saved layer. Confirmed as expected behaviour, not a bug:
QGIS serializes a layer's own renderer (the symbol, its data-defined
properties, everything) into the project file at save time, and
reopening a project reconstructs the layer from what was saved rather
than re-running this plugin's `_build_points_renderer()` - the same
category of "old layer keeps its old style" behaviour already accepted
for S-3 (an old 1.0.3 layer stays on its own recorded edition after
the plugin is updated). Deleting and re-adding the layer rebuilds it
with the current code and picks up the new wiring immediately, which
is exactly what the maintainer found by hand. Nothing to fix - a
brand-new layer in any project, old or new, gets rotation/scale
automatically; only a layer added by an OLDER plugin version, before
this fix, needs that one manual re-add.

---

## Suggested near-term order

1. ✅ ~~Phase 1 leftovers (`mct_mgrs_zone/square/easting/northing`)~~ — done 2026-07-27.
2. ✅ ~~Phase 3 leftovers (magnetic declination)~~ — done 2026-07-27.
3. ✅ ~~Phase 4 — "New Military Layout" suite (heading, north arrow, scale bar, metadata block, centre coordinate, neatline, classification, geographic graticule)~~ — done 2026-07-27.
4. ✅ ~~Phase 6's Grid Settings dialog~~ — decided not needed 2026-07-27; QGIS's own layer styling panel already covers this, closing out Phase 6 entirely.
5. ✅ ~~Phase 5's remaining items~~ (military coordinate reference box, standard legend layouts, grid reference diagrams, coordinate conversion tables) — all decided not needed 2026-07-27, closing out Phase 5 entirely.
6. ✅ ~~Phase 7's codebase cleanup~~ — done 2026-07-28.
7. ✅ ~~Phase 7's test-harness formalization and gotcha documentation~~ — done 2026-07-28 (`tests/` suite, `docs/developer-guide.md`).
8. ✅ ~~Phase 7's user documentation~~ — done 2026-07-28 (`docs/user-guide.md`, rewritten `README.md`, `LICENSE`).
9. ✅ ~~Phase 7's Plugin Repository packaging~~ — published 2026-07-28, moderator approved, plugin ID 5843. Phase 7 is now fully complete, including both known-issue items, genuinely fixed and re-verified (see Phase 7 above).
10. ✅ ~~Phase 8 — terrain analysis~~ — complete 2026-08-06 (see Phase 8 above).
11. ✅ ~~Phase 9 — navigation & production utilities~~ — complete 2026-08-06. Bearing/range tool, GPX/KML import/export, and map sheet series all done, reusing existing infrastructure with no new subsystem required.
12. ✅ ~~Phase 10 — tactical graphics (MIL-STD-2525/APP-6 symbology)~~ — **complete 2026-08-17**; the appendix work itself finished 2026-08-16 when Appendix H closed, and shipped in 1.0.0. Every appendix built or explicitly triaged out (I/METOC decided not needed). What is left inside this phase is expansion, not completion - the Land entity vocabularies and the Land sector 1/2 modifiers - tracked separately rather than holding the phase open. The history below is kept because the reasoning still matters. All four original sub-phases (rendering foundation, unit/formation point symbols, control measures, area/perimeter reporting) built, tested, and documented; manual smoke test completed 2026-08-07, three issues found and fixed same-day. Reopened 2026-08-07 at the user's request to verify against the official MIL-STD-2525D standard directly: found and fixed control-measure colouring (H.5.3), added sub-phase 10.5 (Air/Sea Surface/Subsurface unit symbol sets), and made Entity a real cascading dropdown filtered by Symbol Set (confirmed safe in live testing after a native-crash risk was flagged and accepted). A broader scope review the same day (cross-referencing the standard's own table of contents against milsymbol.js's real source) confirmed substantially more of the standard remains uncovered - Land Civilian/Equipment/Installation, Mine Warfare, Activities, SIGINT, Cyberspace (all already rendered by milsymbol.js, a vocabulary gap only), Appendix H's line/area control measures beyond the 5 built so far (no rendering library to lean on - this is where Mission Task graphics like BLOCK/DISRUPT actually live), and METOC (no library support at all, unscoped). Sub-phase 10.6 (control-measure point symbols, Appendix H symbol set "25") and sub-phase 10.7 (Maneuver/Defensive/Offensive control measures and Mission Task symbols, H.5.11-H.5.14/H.5.26) are both done and merged, tested headlessly on both QGIS versions; sub-phase 10.6 has also been live-smoke-tested, sub-phase 10.7 has not yet (see Phase 10's own entry above for all of the above in detail). **Update 2026-08-08/09**: the stage-based plan above was superseded by a strict appendix-by-appendix completion plan - Appendices A-G, J, and L are now DONE (each its own verified layer + icon), Appendix I (METOC) was triaged and explicitly SKIPPED (no felt need, no library support), and Appendix H (Control Measures) is being rebuilt sub-phase by sub-phase (H0-H22) in the standard's own section order, starting with H0 (general rules + Boundaries, done 2026-08-09) - see Phase 10's own entry above for full detail on every appendix. **Update 2026-08-09/10**: H0-H14 built and tested headlessly; live hands-on QGIS smoke-testing by the project maintainer (started 2026-08-09, table-by-table henceforth via a dedicated tracker artifact) found and fixed real construction defects in H3 (FLOT/Line of Contact/Phase Line/FEBA/Principal Direction of Fire/Fortified Area, plus building the previously-skipped Limited Access Area) and H4 (echelon placement, Strong Point tick direction/masking, Battle Position's "prepared" line style) - see both dated entries above for the full list. Also, at the maintainer's own request, Table H-VI and Table H-IX's point-type entries moved out of the shared `control_measure_points.py` layer into their own dedicated Points layers (C2 Measures/Defensive Control Measures respectively), matching every other H.5.x group's own "own layer(s)" convention - the remaining groups' own points (Airspace/Maritime control points; everything under the not-yet-built H15-H22) are scoped to move the same way once each group's own mini-phase is built, not preemptively. H15-H22 remain pending. 696 tests passing on both QGIS versions as of 2026-08-10. **Update 2026-08-16: APPENDIX H IS COMPLETE.** H15-H22 are all built, smoke-tested and cleared - the last of them Table H-XXIV's own 24 mission-task lines, finished 2026-08-16. Every drawable row of every Appendix H table now has a symbol; the only rows still recorded as unbuilt anywhere are two group parents the standard gives no template for, kept so each module's row arithmetic still reconciles. See the "Appendix H — complete" section at the end of this file for the authoritative ledger. 1289 tests passing on both QGIS versions.
13. ✅ ~~Phase 12 — MIL-STD-2525E / APP-6E symbology~~ — **complete
    2026-08-18**: 978 entities and 226 sector modifiers across every
    symbol set, an edition setting on the toolbar, every Land layer's
    own modifiers covering both editions, and E-8 (the 93 common
    sector 1/2 modifiers, SIDC digits 21/22) wired into every layer
    that already has a per-set 2525E modifier dropdown - see those
    entries under Phase 10 above, including the genuine milsymbol
    rendering bug D-4b caught and fixed (8 codes drawing the wrong icon
    under MIL-STD-2525D, including the vendored-file patch). E-6/E-7
    (APP-6E's own modifier tables and NATO spelling) are CLOSED, not
    built - no source for the official MIL-STD-2525E or APP-6E
    documents was obtainable, and no third-party repo carries APP-6E's
    own modifier tables either, so there is nothing to build them from
    without misrepresenting the standard - see that entry under Phase
    10 above for the full evidence (the two editions were confirmed
    genuinely divergent, not a safe substitute for each other).
    "Complete" here means every item is resolved, built or explicitly
    closed for lack of a source - not that APP-6E has full coverage;
    revisit E-6/E-7 only if a user asks and can point to a source.
    1403 tests passing on both QGIS versions.

---

## Appendix H — complete (closed 2026-08-16)

**APPENDIX H IS COMPLETE**, 2026-08-16. Every table is built or
explicitly closed, and **nothing is left to construct**.

Two rows remain on the record and never will be built: 340000, Table
H-XXIV's own section parent, and 342200, its Security group parent.
Both read "N/A" for TEMPLATE and EXAMPLE. They stay listed so each
module's built-plus-unbuilt arithmetic still adds to its table's own
printed row count.

It was 1 in 1 unit that morning, 36 in 2 before Table H-XXI closed on
2026-08-15, and 54 in 5 before Maritime's Navigational, H-XXIII's eight
supply routes and its seven sustainment areas were all built on
2026-08-14. Every one of those last 54 was a LINE or an AREA - not a
coincidence, since milsymbol renders points and nothing else, so the
whole remainder was hand-built QGIS symbology.

**Nothing was ever really blocked.** The one standing blocker, the CBRN
contaminated areas' centred triangle, turned out not to be a blocker at
all (see below).

**The total was wrong until 2026-08-14** - written as 53, then 52, by
arithmetic on the summary line rather than on the table's own rows,
which have always added to 54 (25 + 17 + 9 + 2 + 1). Re-derived from
each module's own recorded audit and corrected. Trust the rows.

Unit 5, H-XXV's own Intelligence Coordination Line, was built
2026-08-14 and its table is closed - see that entry above.

| Unit | Table | Left | What |
|---|---|---|---|
| ~~1~~ | ~~H-XXIV Mission Tasks~~ | ~~25~~ | **Built 2026-08-15/16** - 3 points and 24 lines: Block, Disrupt, Fix, Secure, Occupy, Penetrate, Seize, Isolate, Delay, Retire, Withdraw, Withdraw Under Pressure, Bypass, Breach, Canalize, Clear, Relief in Place, Cover, Guard, Screen, Follow and Assume, Follow and Support, Counterattack, Counterattack by Fire. Table H-XXIV closed, and with it Appendix H. |
| ~~2~~ | ~~H-XXIII Supply~~ | ~~17~~ | **Built 2026-08-14/15** - 8 supply routes, 7 sustainment areas, 2 convoys. Table H-XXIII closed. |
| ~~2~~ | ~~H-XXI CBRN~~ | ~~9~~ | **Built 2026-08-15** - the 7 contaminated areas, the Minimum Safe Distance Zone and the dose-rate contour. Table H-XXI closed, and with the areas the last blocker in Appendix H. |
| ~~4~~ | ~~H-XVIII Target Acquisition~~ | ~~2~~ | **Built 2026-08-14** - both codes, one symbol. |
| ~~5~~ | ~~H-XIV Maritime~~ | ~~1~~ | **Built 2026-08-14** - Navigational (218400). Table H-XIV closed. |

Each module records its own unbuilt rows by CODE, with a test asserting
built + unbuilt equals the printed table's own count:
`TABLE_H_XXI_REMAINING` (now empty, and deliberately kept so the
arithmetic still runs), `TABLE_H_XXIII_REMAINING`,
`TABLE_H_XXIV_REMAINING`.

**Nothing is blocked.** Both of the sub-groups that were have since
been built, and both for the same reason: the maintainer answered a
question this project had framed too hard.

The seven CBRN contaminated areas were held from 2026-08-13 to
2026-08-15 on the belief that their centred triangle (B/C/N/R, optional
"T" beneath) "does not exist in milsymbol" and had proportions the
standard never gives. Both halves of that were wrong. The triangle in
every one of the seven template pictures is the icon milsymbol already
draws for the matching EVENT point in the same table - so there were no
proportions to invent and nothing to draw. Recording that here rather
than only in the module, because the failure was one of framing: the
audit reached "the standard is silent, so ask" without first checking
whether the thing being asked about already existed. Ask sooner.

Unit 4 was deferred for the same reason Contain/Retain were until
2026-08-14 - it needed genuinely computed geometry rather than a
digitized polygon - and was built on 2026-08-14 once the maintainer
dictated the construction.

**Amplifier fields are deliberately PARTIAL, and that is a standing
decision** (2026-08-16), not an unfinished job.

Most tables offer more amplifier fields than this plugin exposes -
Supply Points' own US Class I (321707) carries T, H, W and W1 and only
T is built; Seize's circle holds a Field A this plugin draws empty; the
convoys' Field A was dropped outright. The question came up as "could
we make a shared piece for it", and the maintainer's answer was to stop
and leave them:

> "we will end up making too many such helpers for catering for all the
> variables in the manual... Incorporating all these also increases the
> plugin's complexity manifold - for a user base which as of now at
> version 0.3.0 is at about 160, and experimental status of the plugin,
> I think we best leave it. we can always revisit when the number of
> users increase and we start getting PRs or Issues being flagged."

The cost is real and this project has already paid a version of it:
Field T1 alone needed a fix across three tables plus the shared point
builder, because milsymbol's own slot naming does not line up with the
standard's field naming or with itself between icons. Every further
field is that same problem again, per icon.

**So: a user who needs an amplifier adds a field to the layer
themselves.** Do NOT add amplifier fields speculatively, and do not
treat a missing one as a defect. Revisit when real users ask -
issues or PRs, not anticipation.

**Closed, not pending** (so they never come back as apparent gaps):

- **H-VII** Occupied Assembly Area with Offset Unit/Units (150301/
  150302) - out of scope at the maintainer's own instruction,
  2026-08-14.
- **AEGIS-only symbols** throughout: maritime 211000/211200/211300 and
  the whole 200xxx overlay family (printed 467-473), target 240603 and
  240804. A standing curation rule.
- **217300** (PIM Route) - broken in milsymbol itself, which maps it to
  the wrong icon under its own `##### FIX TODO #######` comment.
- **Every table's parent row** whose TEMPLATE and EXAMPLE both read
  "N/A" - they name a group, they do not draw.
- **Tables H-XXVI and H-XXVII** - abbreviation and acronym lists, not
  symbol tables. They feed Boundary's own Field T labelling, built in
  H0.

