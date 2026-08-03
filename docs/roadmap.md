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

A reference layout PDF ("EX PANGANI" sketch) was reviewed against this suite earlier in the 2026-07-27 session; three more elements it showed were considered and explicitly not built: a unit badge/crest logo (out of scope entirely), corner coordinate readouts at the four page corners, and 100km-square letter labels at grid corners (decided not needed) — plus an annex reference block (e.g. "ANNEX P TO INDEX 3 / REFERS TO PARA 2", top-right), deliberately deferred rather than ruled out, since it's specific to this one reference document and building it now would over-fit the plugin to one user's exact use case rather than staying broadly usable.

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
- ✅ Package for the official QGIS Plugin Repository — **published 2026-07-28**, moderator approved. Live at plugins.qgis.org, plugin ID 5843, listed as experimental (visible to users with "show experimental plugins" enabled in their Plugin Manager settings). `package_plugin.sh` builds `dist/MilitaryCartographyTools-<version>.zip` in the structure the repository requires (verified by extracting it and running the full test suite against the packaged code directly, not the dev checkout — 45/45 pass); `changelog=` added to `metadata.txt`; manual smoke test passed in a real QGIS 3.44 install (toolbar, all grids, coordinate probe, New Military Layout + Layout Settings panel + grid frame — no crashes, no Log Messages panel errors); two cosmetic bugs found, see below. First upload attempt (0.1.0) was automatically reviewed and flagged 40 findings: 1 Flake8 (`E731`, a lambda assignment in `core/layout_refresh.py`) and 39 "Qt6 compatibility" enum-scoping warnings (QGIS enums accessed via their old flat form rather than fully scoped through the enum class, e.g. `QgsLayoutItemMapGrid.GridStyle.FrameAnnotationsOnly` instead of `QgsLayoutItemMapGrid.FrameAnnotationsOnly`) — all fixed and re-verified (45/45 on both 3.44.12 and 4.0.3). The repository rejects re-uploading an already-used version string, so the fixed build went out as **0.1.1** — that's the version actually submitted, not 0.1.0. Uploaded, security scan cleared, **plugin ID 5843** assigned. Version stays `experimental=True` until there's been some real usage/feedback (a deliberate decision, unrelated to the version-number bump forced by re-submission).

**Known issues found during the manual smoke test (2026-07-28):**
- ✅ **MGRS 100km grid labels land in the wrong square at some zoom levels** (`grid/grid_labels.py`) — actually fixed and re-verified 2026-08-02 (previously only administratively checked off 2026-07-31; see git history for that note). Root cause: `GridLabelManager._centered_settings()` applied a fixed `-20mm` screen-space `yOffset` to every 100km square's centred label at *every* zoom level. That offset was sized for when a square fills much of the screen; once zoomed out enough that a square's own on-screen footprint shrinks below ~20mm, the fixed offset overshot the square entirely and landed the label inside the square immediately to the south — most visible for squares near the top of the view, matching the reported "northern labels drift down into the lower box." A second, related symptom (labels "so big they are all over" when zoomed out) had a separate cause: the centred rule had no scale-based cutoff at all, unlike the corner labels and the sub-grid tick labels (`MGRSSubGridGenerator.LABEL_MAX_SCALE`) — with `displayAll=True` forcing every label to render regardless of collisions, zooming out far enough to see many squares piled a full-size label onto each one. Fix: `apply_square_label()` now splits the single centred rule into two scale-gated rules — a "near" rule (`@map_scale < corner_scale_threshold`) that keeps the offset (safe there, matching the regime the corner labels are already known to work in), and a "far" rule (`@map_scale` between `corner_scale_threshold` and a new `center_max_scale`, default 3,000,000) with **no offset** and a smaller font (`CENTER_LABEL_FAR_SIZE`, default 14pt vs 24pt). Beyond `center_max_scale` no per-square label renders at all, falling back to the UTM GZD label for context. Covered by `tests/test_grid_labels.py` (new).
- ✅ **Print-layout scale bar renders too large in some cases** (`layout/scale_bar.py`) — actually fixed and re-verified 2026-08-03 (previously only administratively checked off 2026-07-31; see git history for that note). Root cause, confirmed with real rendered crops at 1:1,000 and 1:2,000: `_pick_units_per_segment()`'s "nice" segment-size list (`NICE_SEGMENT_KM`) bottomed out at 0.1 km/segment, too coarse for close-in scales — at 1:1,000 on an A4-landscape (297mm-wide) page, the picked bar came out **400mm wide** (5x the 80mm target), and since the bar is horizontally centered via `(page_width - bar_width) / 2`, that went negative and visibly pushed the bar into the metadata block (its line rendered directly through the "Projection: UTM zone GZD 36M" text). Fix: extended `NICE_SEGMENT_KM` one more decade down (`0.01, 0.02, 0.025, 0.05`), following the exact same 1x/2x/2.5x/5x pattern the list already used — 1:1,000 now lands exactly on the 80mm target, 1:2,000 comes in at 100mm (1.25x, well within any real page). Scales at 1:10,000 and above are unaffected (confirmed no regression). Covered by three new tests in `tests/test_layout.py`'s `TestPickUnitsPerSegment`. This doesn't add a hard page-width ceiling — an even tighter scale or a very narrow custom page could theoretically still overshoot — but covers every case actually observed.

The 100km label and scale bar items have both now been genuinely root-caused, fixed, and re-verified with real rendered output (not just administratively marked) — Phase 7's two known-issue items are fully closed.

**Status: Complete.** The plugin is published and live on the official QGIS Plugin Repository. Both known-issue items (100km grid label placement, fixed 2026-08-02; scale bar oversizing, fixed 2026-08-03) are now genuinely fixed and re-verified, not just administratively marked.

---

## Phase 8 — Terrain analysis

- ⬜ Tanaka contours, hillshade combinations, slope/aspect maps, observation points, line-of-sight, elevation profiles, terrain masks

Large and mostly orthogonal to the cartography/grid focus of Phases 1–7. Positioned here, after all completed work, as the biggest deferred effort remaining before the newer navigation/tactical-graphics phases below — revisit when there's appetite for a separate large effort.

**Status: Not started.**

---

## Phase 9 — Navigation & production utilities

Planned 2026-07-31, from a review of what a working military cartography
workflow still lacks beyond base-map/grid production. Chosen as the
"cheap wins" set: each item reuses existing plugin infrastructure
(`core/geomag`, the Coordinate Probe tool's `QgsMapTool` pattern,
`grid/utm_grid.py`, the New Military Layout suite) rather than opening a
new subsystem, so effort/risk is low relative to Phase 10.

- ⬜ **Bearing/range (polar coordinate) tool** — click two points on the
  canvas, report true azimuth, grid azimuth, magnetic azimuth (reusing
  the WMM2025 declination code already in `core/geomag/`), and distance.
  Sibling to the existing Coordinate Probe tool, same `QgsMapTool` +
  persistent-dialog pattern.
- ⬜ **Map sheet series / index generation** — batch-generate a numbered
  series of standard print sheets covering a large AO extent: sheet
  boundaries on a regular grid, a naming/numbering convention, and an
  adjoining-sheet diagram on each printed sheet showing its neighbors.
  Mostly a batch wrapper around `grid/utm_grid.py` and the "New Military
  Layout" suite (Phase 4) rather than new geometry work.
- ⬜ **GPX/KML waypoint import/export with MGRS labels** — round-trip
  waypoints with GPS units, ATAK, or similar, labeled with MGRS via the
  existing conversion functions. Self-contained I/O, no new UI paradigm.

**Considered and deferred:** datum transformation support (converting
coordinates under pre-WGS84 datums, for registering legacy paper maps).
QGIS/PROJ already handles the underlying transform; the work would be
exposing it as a clean expression function and confirming the MGRS
engine doesn't silently assume WGS84 where a transform is needed. Real
value depends on actually working with pre-WGS84 source material —
revisit if that need shows up, rather than building speculatively.

**Status: Not started.**

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

- ⬜ Unit/formation symbols (affiliation, echelon, status modifiers per
  APP-6 / MIL-STD-2525)
- ⬜ Control measures — phase lines, boundaries, axis of advance,
  objectives, named areas of interest (NAIs)
- ⬜ AO/NAI area & perimeter reporting in military units — folded in
  here rather than Phase 9, since it only earns its keep once there are
  polygons (from the above) to report on

**Status: Not started.** Largest remaining item on the roadmap after
Phase 8.

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
10. Phase 8 — terrain analysis, whenever there's appetite for a separate large effort.
11. Phase 9 — navigation & production utilities (bearing/range tool, map sheet series, GPX/KML import/export) — cheap wins, reuse existing infrastructure, no new subsystem required.
12. Phase 10 — tactical graphics (MIL-STD-2525/APP-6 symbology) — largest remaining item, a new symbol-library subsystem; sequence after Phase 8 and Phase 9.
