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
- ✅ Package for the official QGIS Plugin Repository — **published 2026-07-28**, moderator approved. Live at plugins.qgis.org, plugin ID 5843, listed as experimental (visible to users with "show experimental plugins" enabled in their Plugin Manager settings). `package_plugin.sh` builds `dist/MilitaryCartographyTools-<version>.zip` in the structure the repository requires (verified by extracting it and running the full test suite against the packaged code directly, not the dev checkout — 45/45 pass); `changelog=` added to `metadata.txt`; manual smoke test passed in a real QGIS 3.44 install (toolbar, all grids, coordinate probe, New Military Layout + Layout Settings panel + grid frame — no crashes, no Log Messages panel errors); two cosmetic bugs found, see below. First upload attempt (0.1.0) was automatically reviewed and flagged 40 findings: 1 Flake8 (`E731`, a lambda assignment in `core/layout_refresh.py`) and 39 "Qt6 compatibility" enum-scoping warnings (QGIS enums accessed via their old flat form rather than fully scoped through the enum class, e.g. `QgsLayoutItemMapGrid.GridStyle.FrameAnnotationsOnly` instead of `QgsLayoutItemMapGrid.FrameAnnotationsOnly`) — all fixed and re-verified (45/45 on both 3.44.12 and 4.0.3). The repository rejects re-uploading an already-used version string, so the fixed build went out as **0.1.1** — that's the version actually submitted, not 0.1.0. Uploaded, security scan cleared, **plugin ID 5843** assigned. Version stays `experimental=True` until there's been some real usage/feedback (a deliberate decision, unrelated to the version-number bump forced by re-submission). **0.1.2 uploaded 2026-08-03** with both bug fixes below (100km grid label, scale bar oversizing) — security scans passed. **0.2.0 built 2026-08-05**, bumping the version for Phase 8's whole terrain analysis toolset (Tanaka Contours, Hypsometric Tint, Line of Sight, Combined Hillshade, Viewshed) and rewording `metadata.txt`'s `description=`/`about=` to foreground the plugin's fully-offline, no-external-services design. Caught and fixed a real packaging bug in the process: `package_plugin.sh`'s `INCLUDE` array had never been updated when `terrain/` was added, so every zip built since Phase 8 started (including what would have been the 0.2.0 upload) silently shipped without the `terrain` package at all — `plugin.py` imports from it unconditionally, so the plugin would have failed to load entirely. Fixed by adding `terrain` to `INCLUDE`; verified by extracting the rebuilt `dist/MilitaryCartographyTools-0.2.0.zip` and confirming `terrain/` is present with all 16 files, plus 203/203 tests passing on both QGIS 3.44.12 and 4.2.0 before the rebuild. **Uploaded and pushed 2026-08-05** — plugin ID 5843, still `experimental=True`. **0.2.0's automated review flagged 2 real issues**, fixed as **0.2.1** the same day (the repository rejects re-uploading 0.2.0 itself, same constraint as the 0.1.0→0.1.1 re-submission above): (1) 3 Qt6 enum-scoping errors — `QgsVertexMarker.ICON_CROSS`/`ICON_X` needed to be `QgsVertexMarker.IconType.ICON_CROSS`/`ICON_X`, in `terrain/line_of_sight_tool.py` (both markers) and `terrain/viewshed_tool.py` (observer marker); (2) a **blocking security finding** — `tempfile.mktemp()` (insecure/deprecated: creates a filename with no atomic reservation, a TOCTOU race) used at 9 call sites across `terrain/_dem_utils.py`, `hillshade_combination.py`, `tanaka_contours.py`, and `viewshed.py` to generate `processing.run()` OUTPUT paths. Fixed by switching every one to `QgsProcessing.TEMPORARY_OUTPUT`, the idiomatic QGIS Processing sentinel that lets QGIS itself generate the temp file safely — the correct fix, not just a safer Python temp-file call, since it removes the plugin from temp-path generation entirely. One follow-up bug surfaced by the switch: `native:` algorithms (`native:splitlinesbylength` in `tanaka_contours.py`, `native:extractbyattribute` in `viewshed.py`) resolve `TEMPORARY_OUTPUT` to an already-loaded `QgsVectorLayer` object directly in `result["OUTPUT"]`, unlike GDAL-wrapped algorithms which still return a file path to re-wrap — confirmed live via a `TypeError` when re-wrapping the object in another `QgsVectorLayer()` call; fixed by returning `result["OUTPUT"]` directly for those two call sites. Re-verified 203/203 on both QGIS 3.44.12 and 4.2.0, plus an extracted-zip sweep confirming no remaining `mktemp`/unscoped-enum references, before rebuilding `dist/MilitaryCartographyTools-0.2.1.zip`. **Uploaded 2026-08-05, security checks cleared** — Phase 8's terrain analysis toolset is now live on the official Plugin Repository. **0.3.0 built 2026-08-06**, bundling everything shipped since 0.2.1: Phase 9 in full (Bearing/Range tool, GPX/KML waypoint import/export, Map Sheet Series with its automatic grid-position diagram now standard on every layout), MGRS shown alongside lat/lon in Line of Sight/Viewshed, and the Hypsometric Tint/Tanaka Contours colour fixes (discrete ramp toggle, `LAND_RAMP` hue warm-up, Illuminated Overlay's Soft Light blend). Unlike the 0.2.0 packaging bug, no new top-level package needed adding to `package_plugin.sh`'s `INCLUDE` array this time — every Phase 9 feature lives inside packages already listed (`core/`, `waypoints/`, `layout/`). `metadata.txt`'s `changelog=`/`about=`/`tags=` updated; verified by extracting `dist/MilitaryCartographyTools-0.3.0.zip` and running the full suite against the packaged code directly (not the dev checkout) — 291/291 on both QGIS 3.44.12 and 4.2.0. **Deliberately stays `experimental=True`** — considered flipping it given 83 downloads with no reported issues on 0.2.1, but that signal reflects the *older* core (MGRS/grid/terrain), not this release's own newest, least-battle-tested batch (Map Sheet Series, Bearing/Range, GPX/KML) — decided to wait for this batch to collect its own field exposure before reconsidering the flag on a later release. **Built and packaged, not yet uploaded** — the actual Plugin Repository submission needs the maintainer's own OSGeo login, outside what this session can do.

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

- 🔧 **Deferred cosmetic tuning, not a bug**: `GZD_OFFSET_MAX_SCALE = 3000000` (the scale at which the UTM/GZD label switches from its up-left nudge to sitting dead-centre) is a loose derivation, not yet confirmed against a real render at the actual boundary scale. User-confirmed 2026-08-06 that the underlying centroid-anchoring bug is fixed and this is fine to leave as-is for now - revisit only if the offset ever visibly looks off right around that threshold in practice, and just nudge the constant if so.
- 🔧 **Flagged for a future cleanup pass, not urgent**: `core/mgrs_engine.py:462` has a leftover `# FIXME: do we really need this?` above a block of already-commented-out dead code (a special-case zone-31V rounding check from the original vendored MGRS conversion library) - predates this project's own work, inert either way since it's already commented out. Worth a look next time there's a general codebase-cleanup pass (decide whether to delete the dead block entirely or restore/document the special case), not on its own worth a dedicated session.

**Status: Complete.** The plugin is published and live on the official QGIS Plugin Repository. All three known-issue items (100km grid label placement, fixed 2026-08-02; scale bar oversizing, fixed 2026-08-03; UTM/GZD label overflow, fixed 2026-08-06) are genuinely fixed and re-verified, not just administratively marked. Two minor items deferred, neither tracked as a bug: GZD_OFFSET_MAX_SCALE's exact threshold value, and the mgrs_engine.py FIXME cleanup above.

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
  - ⬜ **Requested 2026-08-06, not started: a caution about long generation times.** Tanaka Contours can take noticeably long to generate against a large DEM and/or a small contour interval - more of the DEM to clip/contour, and/or a finer interval producing far more contour lines (each further subdivided into `segment_length`-sized pieces, each needing its own two-sided DEM sample for illumination), multiply directly into a much bigger `native:splitlinesbylength` + per-segment sampling workload. No warning today - the dialog just appears to hang until it's done. Likely needs a `tanaka_dialog.py` message-bar caution (e.g. `pushInfo` before calling `generate_tanaka_contours()`) when the DEM's pixel count and/or `dem_extent_area / interval` implies a heavy run - exact thresholds would need picking against real timing data rather than guessed, so this needs its own scoping pass before implementation.
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
  - ⬜ **Requested 2026-08-06, not started - two related Viewshed enhancements**, both explicitly deferred (user: "add them as to do works, not right now"):
    1. **Multi-sensor coverage in one layer.** Today, every observer click either replaces the existing "Viewshed" layer in place or (with "Add as new layer" checked) starts an entirely separate layer - there's no way to add a second, third, etc. observer point whose visible areas *accumulate* (union) into the same layer. Real use case: modeling several sensors/observers in one area and seeing their combined coverage as a single picture, rather than one polygon per sensor or manually unioning layers afterward. A new layer should still be available on request, for comparing a distinct set of sensors against the current one. Touches `generate_viewshed()`'s single-observer signature and `viewshed_dialog.py`'s current "replace the whole named layer" `replace_named_layer()` usage - likely needs its own accumulation path (union new polygon into existing layer's geometry, or add a new feature per sensor to one multi-feature layer) rather than reusing that helper unchanged.
    2. **Movable, persistent sensor points.** The observer marker (`QgsVertexMarker`) is purely a transient, click-driven UI cue - it doesn't correspond to any real feature in the output layer, so once the coverage polygon exists there's no way to grab the "sensor" and drag it to reposition, the way you can with an ordinary point feature in edit mode. User's stated preference: keep the sensor's own point visible and repositionable, with its coverage recomputing/updating as it's moved - closer to a live, editable sensor-siting layer than the current one-shot "click, get a static result" model. Acknowledged by the user as a real, non-trivial change to the underlying architecture (observer points would need to become actual stored/editable features, with some way to detect a moved point and regenerate that sensor's own polygon), not a small tweak.
    3. **Sensor polygon colour picker.** *(added 2026-08-06)* Today the coverage polygon is always styled with `VISIBLE_COLOR` (green, reused from Line of Sight). Real use case: distinguishing multiple sensors/forces by colour (e.g. red/blue/yellow/green for different sides), especially once item 1 (multi-sensor) lands and several sensors' coverage might need to sit in view together, or be compared side by side. Would need a colour picker in `viewshed_dialog.py` and a `color` parameter threaded through `generate_viewshed()`'s styling step, defaulting to the current green so existing behaviour is unchanged.
    4. **Outline-only vs. filled polygon toggle.** *(added 2026-08-06)* Today `_apply_polygon_style()` always renders a filled `QgsFillSymbol`. Real use case: an outline-only rendering lets underlying terrain/imagery stay fully visible while still showing the coverage boundary - useful when overlaying several sensors' coverage areas at once, where stacked filled polygons (even at reduced opacity) obscure both each other and the map underneath. Would need a checkbox/toggle in the dialog and a style branch in `generate_viewshed()`'s styling step (an outline-only `QgsFillSymbol` with `"style": "no"`/`"outline_style": "solid"`, rather than a different symbol type).
    All four items reshape Viewshed from "one-shot analysis per click" toward "a small persistent sensor-coverage layer you build up, style, and edit over time" - worth designing together rather than separately, given how much they overlap (items 1-2 both need observer points to be real, addressable features rather than ephemeral clicks; items 3-4 are smaller, independent styling additions that could land first without needing the others).
- ✅ ~~Radar/sensor-siting coverage polygon~~ — retired as redundant 2026-08-06. Originally scoped as "the same swept curvature/refraction calculation with a user-supplied max-range parameter, producing a coverage polygon rather than a shaded raster" - once Viewshed itself was redesigned to output a visible-area polygon with a user-set max distance (see the 2026-08-06 entry above), that description no longer distinguishes the two features at all. Considered whether a real difference was worth building anyway - a radio/radar-specific refraction coefficient (optical line-of-sight conventionally uses k≈0.13, `line_of_sight.py`'s own value, vs. a different standard for radio propagation, e.g. the "4/3 earth radius" model) and a sector/azimuth-limited sweep (a directional sensor doesn't always scan the full 360° Viewshed does) - user decided neither is worth a separate feature; Viewshed already covers this use case.
- ✅ ~~Slope/aspect convenience wrapper~~ — dropped 2026-08-06. Originally scoped as batch-generating slope + aspect (+ hillshade) with plugin-provided military-style symbology presets, on the theory that a one-click preset would save re-styling QGIS's native Slope/Aspect renderer by hand each time. Dropped because that reasoning didn't hold up: QGIS's own raster properties panel already offers "Slope"/"Aspect" rendering with one dropdown and no processing run needed, so the *only* value this would have added was the military-style presets themselves - a cosmetic convenience layered on a feature QGIS already ships natively, not new capability, and not worth the maintenance surface of a whole extra dialog/toolbar action for that alone.
- ✅ ~~Elevation profiles~~ — decided not needed 2026-08-03; QGIS 3.28+ (covers both this plugin's 3.44 and 4.x targets) already has a native Elevation Profile panel built in, so building a duplicate wouldn't add value.
- ✅ ~~DEM acquisition/download tool~~ — considered and explicitly decided not needed 2026-08-03. Getting a DEM is a generic GIS task already covered by QGIS's own Data Source Manager (WCS connections) and dedicated existing plugins (e.g. SRTM Downloader), not something specific to military cartography. It would also fit this plugin's actual audience poorly - military cartography users are exactly the kind who may be working disconnected or in restricted-network environments, where a feature that silently depends on live internet access is a liability rather than a convenience (contrast with `core/geomag/`'s WMM2025 data, vendored locally specifically to avoid any runtime network dependency). Every item above assumes a DEM is already loaded, same precondition QGIS's own Slope/Aspect/Hillshade/Elevation Profile/viewshed tools already have. **Follow-up reminder fulfilled 2026-08-03**: `docs/user-guide.md`'s new Tanaka Contours section includes a "Getting a DEM" pointer (Data Source Manager / SRTM Downloader), now that there's a real feature to attach it to. **Revisited and reaffirmed 2026-08-05**, after the user hit a real GMRT (bathymetry) download snag in practice: unlike SRTM, GMRT has no dedicated QGIS downloader plugin, and QGIS's own built-in "Download file" Processing tool needs the GridServer URL built by hand. Even a thin, scoped-down version (just an extent-to-URL convenience button, not a full downloader dialog) was considered and declined - the offline/restricted-network reasoning above still applies, and it would only ever help the narrow slice of usage generating terrain layers over open water. `docs/user-guide.md`'s Tanaka Contours section could eventually mention GMRT's GridServer as a bathymetry-specific pointer alongside the existing SRTM one, but that's a docs change, not a feature.

Large and mostly orthogonal to the cartography/grid focus of Phases 1–7. Positioned here, after all completed work, as the biggest deferred effort remaining before the newer navigation/tactical-graphics phases below — revisit when there's appetite for a separate large effort.

**Status: Complete**, aside from the four requested-but-deferred Viewshed enhancements (multi-sensor coverage, movable/persistent sensor points, sensor polygon colour picker, outline-only/filled toggle - all 2026-08-06, not started) and a requested Tanaka Contours long-generation-time caution (2026-08-06, not started, needs its own scoping pass). Tanaka contours, hypsometric tint, line-of-sight/visibility, hillshade combinations, and viewshed/dead-ground done and user-confirmed; the Discrete colour-ramp toggle, `LAND_RAMP` hue warm-up, and Illuminated overlay's Soft Light blend fix (all 2026-08-06) close out the reference research; radar/sensor-siting retired as redundant once Viewshed itself became a polygon-with-max-range tool; elevation profiles, DEM acquisition, and the slope/aspect convenience wrapper closed out as not needed.

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

**Phase 10 NOT yet complete** - reopened 2026-08-07. All four
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
        (less-than-lethal), sensor (emplaced). **One real inconsistency,
        not a deliberate boundary**: the law-enforcement family here is
        only half-included - `law_enforcement`/`border_patrol`/
        `customs_service`/`drug_enforcement_agency` (170000-400) are
        present but DOJ/FBI/Secret Service/TSA/law-enforcement-vessel/US
        Marshals (170500-171100) aren't, even though the identical full
        family WAS added for Land Installation in this same session -
        should be fixed for consistency when this is revisited.
      - **Land Installation - 29 of 126 real `landinstallation.js`
        entities excluded** (we have 97, after this session's fix
        above). Main groups: intelligence-marking installations
        (black-list/gray-list/white-list location, mass grave location);
        radioactive material; tent+evacuee/training-camp compounds;
        industrial site+warehouse; Class III/V supply-facility compounds;
        electric-power-generation-station duplicate icon; base+armory
        compound; naval-yard/airport-of-debarkation transportation
        compounds.
      - Sector 1/2 modifiers remain entirely unbuilt for all four Land
        layers (already noted above) - Tables D-VI/D-VII (Land Unit
        alone) have 50+ codes per sector.
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
12. 🟡 Phase 10 — tactical graphics (MIL-STD-2525/APP-6 symbology) — NOT yet complete. All four original sub-phases (rendering foundation, unit/formation point symbols, control measures, area/perimeter reporting) built, tested, and documented; manual smoke test completed 2026-08-07, three issues found and fixed same-day. Reopened 2026-08-07 at the user's request to verify against the official MIL-STD-2525D standard directly: found and fixed control-measure colouring (H.5.3), added sub-phase 10.5 (Air/Sea Surface/Subsurface unit symbol sets), and made Entity a real cascading dropdown filtered by Symbol Set (confirmed safe in live testing after a native-crash risk was flagged and accepted). A broader scope review the same day (cross-referencing the standard's own table of contents against milsymbol.js's real source) confirmed substantially more of the standard remains uncovered - Land Civilian/Equipment/Installation, Mine Warfare, Activities, SIGINT, Cyberspace (all already rendered by milsymbol.js, a vocabulary gap only), Appendix H's line/area control measures beyond the 5 built so far (no rendering library to lean on - this is where Mission Task graphics like BLOCK/DISRUPT actually live), and METOC (no library support at all, unscoped). Sub-phase 10.6 (control-measure point symbols, Appendix H symbol set "25") and sub-phase 10.7 (Maneuver/Defensive/Offensive control measures and Mission Task symbols, H.5.11-H.5.14/H.5.26) are both done and merged, tested headlessly on both QGIS versions; sub-phase 10.6 has also been live-smoke-tested, sub-phase 10.7 has not yet (see Phase 10's own entry above for all of the above in detail). **Update 2026-08-08/09**: the stage-based plan above was superseded by a strict appendix-by-appendix completion plan - Appendices A-G, J, and L are now DONE (each its own verified layer + icon), Appendix I (METOC) was triaged and explicitly SKIPPED (no felt need, no library support), and Appendix H (Control Measures) is being rebuilt sub-phase by sub-phase (H0-H22) in the standard's own section order, starting with H0 (general rules + Boundaries, done 2026-08-09) - see Phase 10's own entry above for full detail on every appendix.
