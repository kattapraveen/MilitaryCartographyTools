# Military Cartography Tools — User Guide

A QGIS plugin for military mapping and MGRS work: coordinate conversion,
military grid generation, and automated print-layout production.

---

## Contents

- [Installation](#installation)
- [The toolbar, at a glance](#the-toolbar-at-a-glance)
- [Coordinate Probe](#coordinate-probe)
- [Bearing / Range](#bearing--range)
- [Military grids](#military-grids)
- [New Military Layout](#new-military-layout)
- [Military Layout Settings panel](#military-layout-settings-panel)
- [Print-layout grid frame](#print-layout-grid-frame)
- [Tanaka Contours](#tanaka-contours)
- [Hypsometric Tint](#hypsometric-tint)
- [Line of Sight](#line-of-sight)
- [Hillshade Combinations](#hillshade-combinations)
- [Viewshed](#viewshed)
- [Waypoint Import/Export (GPX/KML)](#waypoint-importexport-gpxkml)
- [Map Sheet Series](#map-sheet-series)
- [Tactical Graphics - point symbol layers](#tactical-graphics---point-symbol-layers)
- [Tactical Graphics - Control Measures](#tactical-graphics---control-measures)
- [Expression functions](#expression-functions)

---

## Installation

Requires QGIS 3.44 or later. Install from the [official QGIS Plugin
Repository](https://plugins.qgis.org) — the plugin is currently listed as
experimental, so tick **"Show also experimental plugins"** under **Plugins
→ Manage and Install Plugins → Settings** first — or manually:

1. Copy the `MilitaryCartographyTools` folder into your QGIS plugins
   directory (`Settings → User Profiles → Open Active Profile Folder →
   python/plugins`).
2. In QGIS, open **Plugins → Manage and Install Plugins → Installed**, and
   tick **Military Cartography Tools**.
3. A new toolbar appears with the plugin's tools.

---

## The toolbar, at a glance

The toolbar has one standalone icon (About / plugin info) plus six
grouped dropdown buttons — click a button to open its menu, then pick
the specific tool. The same six groups are mirrored as submenus under
**Plugins → Military Cartography Tools**, so every tool is reachable
from either place.

Left to right:

| Icon | Button | Opens |
|---|---|---|
| Grid with a highlighted square + crosshair | *(standalone)* | About / plugin info |
| 3×3 grid | **Grid** | UTM Grid, MGRS 100km Grid, Sub Grid (10km/5km/1km spacing, itself a nested flyout), Clear Grid |
| Compass rose | **Navigation** | Coordinate Probe, Bearing / Range |
| Layered peaks with a contour line | **Terrain Analysis** | Tanaka Contours, Hypsometric Tint, Hillshade Combinations, Line of Sight, Viewshed |
| Location pin | **Waypoints** | Import Waypoints, Export Waypoints |
| Printed sheet with a folded corner | **Print Production** | New Military Layout, Map Sheet Series |
| Hexagonal frame with a centre dot | **NATO Symbols** | Every MIL-STD-2525D/APP-6 point symbol layer (Space, Air, Land, Sea Surface, Subsurface, Activities, SIGINT, Cyberspace) plus Control Measures |

Each individual tool keeps its own icon and behaviour exactly as
described in its own section below (checkable tools still show as
checked/unchecked inside the dropdown, same as they did as standalone
toolbar buttons) — grouping only changes *where* you click to reach it.

Each Layout Designer window (opened from a print layout) additionally gets
its own small toolbar with **Add/Remove Grid Frame** and a **Military Layout
Settings** toggle — see their own sections below.

---

## Coordinate Probe

Click the crosshair icon to activate, then click anywhere on the map
canvas. Each click:

- Opens (or reuses) a **Coordinate Probe** window listing every click,
  newest at the top, with latitude/longitude and full-precision (1m) MGRS.
- Copies that click's MGRS coordinate to the clipboard.

The window stays open and keeps accumulating across clicks — closing it just
hides it; the next click reopens it with its history intact. **Double-click
any row** to re-copy that row's MGRS to the clipboard (handy if a later
click already overwrote it).

The tool stays active across repeated clicks, like QGIS's own
Identify/Measure tools, until you select a different tool.

---

## Bearing / Range

Click the icon to activate, then click two points on the map canvas: the
first sets the **from** point (blue cross marker), the second sets the
**to** point (red X marker) and immediately logs a reading. A third click
starts a fresh pair rather than adding to the previous one. Once both points
are set, a line with an arrowhead is drawn from the from-point to the
to-point, so the direction is visible on the map itself, not just as a
number in the log.

Each logged reading shows:

| Column | Notes |
|---|---|
| From / To | Latitude/longitude and full-precision (1m) MGRS for each point, on separate lines |
| True Az | True (geographic) azimuth from the from-point to the to-point |
| Grid Az | Azimuth relative to UTM grid north at the from-point |
| Mag Az | Azimuth relative to magnetic north at the from-point (WMM2025, current date) |
| Distance | Geodesic distance between the two points, in metres |

Grid and magnetic azimuth are both computed at the **from** point, the same
convention a paper grid-magnetic-angle diagram uses. All three azimuths and
the distance are geodesic (ellipsoid-surface) values, not flat-plane
approximations.

The **Bearing / Range** window stays open and keeps accumulating readings,
newest at the top, the same persistent-log pattern Coordinate Probe uses —
handy for logging several readings in one session rather than only ever
seeing the most recent one. Use **Clear** to empty the log. The tool stays
active across repeated pairs, like Coordinate Probe and Line of Sight, until
you select a different tool.

---

## Military grids

- **UTM Grid** — Grid Zone Designator (GZD) polygons for the current map
  extent (e.g. `37M`).
- **MGRS 100km Grid** — the 100km square grid, built from the UTM grid
  (turning this on brings the UTM grid up automatically if it isn't already
  visible).
- **Sub Grid** — 10km / 5km / 1km tactical grid lines, with on-map tick
  labels. Picking a spacing brings the UTM grid up too, since sub-grid lines
  are generated per Grid Zone Designator.
- **Clear Grid** — removes every grid layer (all sub-grid spacings
  included) and resets every toggle — a clean slate before regenerating for
  a new area.

Each grid is generated once per area and then just shown/hidden by its
toggle; panning to a new area and re-toggling regenerates it there.

---

## New Military Layout

Click the page icon to open the **New Military Layout** dialog, which
creates a fully-configured print layout in one step — QGIS's own "New
Layout" only asks for a name and starts blank.

| Field | Notes |
|---|---|
| Name | Duplicates get auto-suffixed (`My Layout (2)`, etc.) |
| Page size | `Custom`, `A0`, `A3`, `A4`, `Arch E` |
| Orientation | Landscape / Portrait |
| Width / Height | Only editable when Page size is `Custom` |
| Scale | Common scales offered, or type your own (`1:50000`, `50000`, etc.) |
| Heading line 1 / 2 | Optional. Always rendered in upper case regardless of how you type it. Leave both blank for no heading. |
| Classification | `None`, `UNCLASSIFIED`, `RESTRICTED`, `CONFIDENTIAL`, `SECRET`, `TOP SECRET` — shown as a bold banner top and bottom |

The layout it creates automatically includes:

- **North arrow** — rotates to true north automatically as the map's
  rotation/CRS/grid convergence change; no manual adjustment needed.
- **Scale bar** — "Line Ticks Up" style, auto-sized to a sensible width for
  the map's current scale.
- **Metadata block** (bottom-left) — geodetic datum, projection/GZD,
  coordinate units, map scale, project file name, page size.
- **Center of Map** label (bottom-right) — the map's centre coordinate in
  MGRS.
- **Neatline** — a thin border tracking the map frame exactly.
- **Geographic graticule** — a light-brown lat/lon overlay, auto-spaced
  15′/30′/1° depending on the map's extent, distinct from the plugin's own
  UTM/MGRS grid.
- **Grid position diagram** (bottom-left) — a small inset showing where
  this map sits in the plugin's own grid hierarchy (UTM Grid Zone
  Designator down to MGRS 100km squares), with the map's own footprint
  outlined on it — see [Map Sheet Series](#map-sheet-series) below for the
  full explanation, since every layout gets one, not just a generated
  series.
- **Classification banners**, if selected.

Every element auto-sizes the map's margins to fit whatever combination of
heading/classification you chose, so the map always fills the remaining
space rather than leaving dead margin.

---

## Military Layout Settings panel

Every Layout Designer window gets a **Military Layout Settings** dock panel
(and a matching toggle button on its toolbar, in case you close the panel
and want it back) with the same fields as the creation dialog. Change any of
them and click **Apply** to update the *existing* layout in place — page
size, scale, heading, and classification — instead of creating a new layout
for every iteration. The map's current pan position is preserved across a
resize.

---

## Print-layout grid frame

Each Layout Designer window's own small toolbar has:

- **Add Grid Frame** — adds border tick marks and coordinate annotations
  around the map, spaced automatically for the layout's current print
  scale, and hides the sub-grid layer's own on-map tick labels for that
  layout specifically (the interactive canvas keeps showing them normally).
- **Remove Grid Frame** — removes it and restores the normal on-map labels
  for that layout.

This is the standard topographic/military-map convention: ticks and numbers
on the neatline rather than labels drawn over the map content.

---

## Tanaka Contours

Click the illuminated-rings icon to generate **Tanaka contours** — contour
lines whose *width* always varies by local terrain illumination: thick where
a segment faces directly toward or directly away from the light (extreme
illumination or extreme shadow), thin only where it's perpendicular/grazing
to it. This gives a sense of relief without needing a hillshade raster
underneath. *Style* (color) is one of three modes:

- **Elevation colour** (default) — the standard hypsometric ("layer tint")
  convention topographic/military maps use: shades of blue below sea level,
  then green → yellow → brown → red → white with increasing elevation above
  it. The colour range is stretched across whichever elevations are actually
  present in the area you generate — so the lowest point on screen is always
  green and the highest is always white, regardless of whether that area
  sits at 50m or 5,000m — rather than a fixed global scale, which would
  leave a single small-extent generation looking almost one flat colour.
- **Monochrome** — the classic grayscale Tanaka look, where color (dark
  where shadowed, light where lit) comes from the same illumination value
  as the line width, instead of elevation.
- **Illuminated overlay** — the conventional technique for combining
  illumination with elevation colour: the line itself is pure black/white by
  illumination, and the layer's blend mode is set to **Soft Light**, so its
  displayed colour comes from compositing against whatever's underneath at
  render time. Soft Light rather than Overlay — Overlay's stronger swing
  darkened shadowed contour rings on steep terrain into a muddy dark red
  instead of clean highlights; Soft Light gives a gentler version of the
  same effect that keeps the tint's own hue recognisable. **Use this
  together with a Hypsometric Tint layer** — without
  one, lit segments will look nearly invisible against a blank canvas (the
  dialog warns if no Hypsometric Tint layer exists in the project when you
  pick this mode, but still generates the layer either way).

Requires a DEM (elevation raster) layer already loaded in your project;
this plugin doesn't fetch or download one for you (see "Getting a DEM"
below).

The dialog asks for:

| Field | Notes |
|---|---|
| DEM layer | Any loaded raster layer |
| Contour interval | Vertical spacing between contour lines, in metres |
| Segment length | How finely each contour is subdivided for illumination to vary smoothly along it, in metres — smaller values give a smoother gradient at the cost of more features |
| Light azimuth | Direction the virtual light comes from, in degrees (0 = north). Defaults to 315° (north-west), matching QGIS's own hillshade default |
| Min line width (perpendicular to light) / Max line width (facing toward/away from light) | Line width at the grazing case and at either illumination extreme, in mm |
| Style | Elevation colour (default) / Monochrome / Illuminated overlay — see above |
| Add as new layer | Off by default — re-running the dialog corrects the existing "Tanaka Contours" layer in place. Check this to keep the previous layer and add a new one alongside it instead, e.g. to compare two parameter sets |

Contours are generated for the **DEM layer's own full extent**, clipped and
reprojected to the appropriate local UTM zone automatically — the current
map canvas view has no effect on the result, so regenerating (e.g. after
tweaking a parameter) always produces the same output regardless of where
you've since panned or zoomed. On a large DEM, generation may take longer;
crop the DEM itself first if you only need a smaller area.

### Getting a DEM

This plugin doesn't include a DEM downloader — that's a generic GIS task
already well covered elsewhere. If you don't already have elevation data
for your area, options include QGIS's own **Data Source Manager** (WCS
connections), or a dedicated plugin such as **SRTM Downloader** (via
**Plugins → Manage and Install Plugins**).

---

## Hypsometric Tint

Tanaka Contours colors *lines*, but the space between them is left blank.
Click the filled-colour-bands icon to generate a **Hypsometric Tint**
layer instead — a filled, full-coverage raster using the same elevation
color convention (blue below sea level, green → yellow → brown → red →
white with increasing elevation above it, stretched across whichever
elevations are actually present in the area you generate). It's a
separate layer from Tanaka Contours, meant to sit underneath it: generate
both over the same area, and the tint fills the gaps between the
contour lines rather than leaving them blank.

Requires a DEM layer already loaded in your project (see "Getting a DEM"
above). The dialog asks for:

| Field | Notes |
|---|---|
| DEM layer | Any loaded raster layer |
| Opacity | 0–100%, default 100 |
| Stepped colour ramp | Off by default (a smooth gradient). Check this for hard-edged discrete colour bands instead, matching the classic banded "layer tint" look used by most published hypsometric references, rather than a continuous blend |
| Add as new layer | Off by default — re-running the dialog corrects the existing "Hypsometric Tint" layer in place. Check this to keep the previous layer and add a new one alongside it instead |

Like Tanaka Contours, it's generated for the **DEM layer's own full
extent**, clipped and reprojected automatically — the current map canvas
view has no effect on the result. New layers are always placed at the
**bottom** of the layer panel, so it won't cover any grid or contour
layers already in your project.

**Tip:** for a fuller, textured relief look (closer to a shaded physical
relief map), generate a **Hillshade Combinations** layer (see below) over
the same area — it automatically sits above this one with an Overlay
blend already applied.

---

## Line of Sight

Click the two-dots-and-a-line icon to activate, then click two points on the
map canvas: the first sets the **observer**, the second sets the **target**.
Each click drops a marker on the map so it's obvious it registered — a blue
cross for the observer, a red X for the target. A small **Line of Sight**
window opens on the first click, showing each point's coordinates (both
latitude/longitude and full-precision MGRS) as you set them, and the check
runs automatically as soon as both are set.

The result is drawn as a line between the two points — **green** where the
target is visible from the observer, **red** where it's blocked — with the
total observer-to-target distance, and (if blocked) roughly how far along
the path the first obstruction is, shown in the window's own **Result**
line. Visibility accounts for both real terrain (sampled from your DEM
along the path) and earth curvature/atmospheric refraction, so even a low
target far enough away over open ground can be correctly reported as not
visible. Any elevation below sea level (open water on a bathymetric DEM)
is treated as sea level (0m) rather than the seabed's own depth — an
observer or target over water sits on the surface, not the seafloor.

Requires a DEM layer already loaded in your project (see "Getting a DEM"
above). The window also lets you set:

| Field | Notes |
|---|---|
| DEM layer | Any loaded raster layer |
| Observer height | Height above ground at the observer point, in metres (default 1.7 — average eye height) |
| Target height | Height above ground at the target point, in metres (default 0 — ground level) |
| Add as new layer | Off by default — re-running the check corrects the existing "Line of Sight" layer in place. Check this to keep the previous result and add a new one alongside it instead |
| Result | Read-only — total distance, and visible/blocked (with the blocking distance, if any) |

Adjust a height and press **Generate** to re-run the check without
re-clicking either point. Clicking a third point starts a fresh
observer/target pair rather than adding to the previous one — the observer
marker jumps to the new point and the old target marker disappears.

Unlike Tanaka Contours and Hypsometric Tint, this isn't tied to the current
map canvas extent — the DEM is clipped to a box around wherever the observer
and target actually are, so you can freely pan or zoom between clicking the
first point and the second without losing it. The tool stays active across
repeated pairs, like Coordinate Probe, until you select a different tool.

---

## Hillshade Combinations

QGIS/GDAL's own hillshade tools (**Raster → Analysis → Hillshade**, or the
`gdal:hillshade` Processing algorithm) only light the terrain from a single
direction, which can hide relief that happens to run parallel to that
light. Click the hill-with-two-arrows icon to generate a **Combined
Hillshade** layer instead — it runs the hillshade calculation once per
light direction and averages the results into one blended relief layer.

Requires a DEM layer already loaded in your project (see "Getting a DEM"
above). The dialog asks for:

| Field | Notes |
|---|---|
| DEM layer | Any loaded raster layer |
| Light directions | Two-direction (NW + NE) or Three-direction (NW + NE + S) — default Three-direction |
| Opacity | How strongly the relief shading shows through (default 100%) |
| Add as new layer | Off by default — re-running the dialog corrects the existing "Combined Hillshade" layer in place. Check this to keep the previous layer and add a new one alongside it instead |

Like Tanaka Contours and Hypsometric Tint, it's generated for the **DEM
layer's own full extent**, clipped and reprojected automatically — the
current map canvas view has no effect on the result. The layer is
rendered in grayscale with an **Overlay** blending mode already applied
(darkens shadowed slopes and lightens sunlit ones, while keeping the
underlying colour's own hue — a plain Multiply blend was tried first but
dragged colours toward a muddy brown-purple instead), so if a Hypsometric
Tint layer already exists in your project, the new layer is placed
directly above it — the two combine automatically into a coloured,
textured relief look. If there's no Hypsometric Tint layer yet, it's
placed at the bottom of the layer panel instead, same as Hypsometric Tint
itself, so it won't cover any grid or contour layers.

---

## Viewshed

Click the radiating-arcs icon to activate, then click a point on the map:
that's the **observer**, marked with a blue cross. A small **Viewshed**
window opens showing the observer's coordinates (both latitude/longitude
and full-precision MGRS), and generates a coverage layer automatically.

Unlike Line of Sight, which checks visibility to one target point, Viewshed
sweeps every direction out to a chosen range and draws a single **green**
polygon covering just the area actually visible from the observer. Ground
that's out of range, or hidden behind terrain, is left blank rather than
filled in — a full coloured circle covering the whole swept area reads as
"the whole circle matters," which was more confusing than useful in
practice. Like Line of Sight, this accounts for both real terrain and
earth curvature/atmospheric refraction, and treats any elevation below sea
level (open water on a bathymetric DEM) as sea level (0m) rather than the
seabed's own depth — an observer or target over water sits on the surface,
not the seafloor.

Requires a DEM layer already loaded in your project (see "Getting a DEM"
above). The window also lets you set:

| Field | Notes |
|---|---|
| DEM layer | Any loaded raster layer |
| Observer height | Height above ground (or water surface) at the observer point, in metres (default 1.7 — average eye height) |
| Target height | Height above ground being checked for visibility, in metres (default 0 — ground level) |
| Max distance | How far out to sweep, in metres (default 5000) |
| Opacity | How solid the visible-area fill appears, so terrain underneath still shows through (default 65%) |
| Add as new layer | Off by default — clicking again corrects the existing "Viewshed" layer in place. Check this to keep the previous result and add a new one alongside it instead |

Adjust a field and press **Generate** to re-run without re-clicking, or
just click a different point on the map — every click is a complete,
standalone analysis on its own, so there's no observer/target pair to keep
track of. Like Line of Sight, the DEM is clipped to a box around wherever
the observer actually is (sized from the max distance you've set), not
tied to the current map canvas extent, and the tool stays active across
repeated clicks until you select a different tool.

---

## Waypoint Import/Export (GPX/KML)

Two separate actions — **Import Waypoints** reads waypoints from a GPX or
KML file; **Export Waypoints** writes a point layer out to one. Both attach
an MGRS grid reference, since neither format has any native concept of it.

**Import Waypoints:**

1. Click the icon, then **Browse...** to pick a `.gpx` or `.kml` file.
2. Click **Import**. A new point layer is added (named after the file),
   with every field the source file already had, plus a new **mgrs**
   field computed from each waypoint's own position — the original
   name/label field is left untouched alongside it.

**Export Waypoints:**

1. Click the icon, choose a point layer already in your project, and pick
   a format (**GPX** or **KML**).
2. **Browse...** to pick a destination file, then click **Export**.
3. Each waypoint's **name** (the field a GPS unit or ATAK actually
   displays) is set to its MGRS grid reference. If the source layer has
   its own name/label field, it's preserved as a separate description
   field alongside it.

Both `.gpx` and `.kml` are supported; `.kmz` (zipped KML) isn't. A GPX
file's **routes**/**tracks** aren't imported — only standalone waypoints.

---

## Map Sheet Series

Click the icon to batch-generate a numbered series of print sheets tiling
the **current map extent** — for producing a full set of standard-size
map sheets over a large area of operations, rather than one layout at a
time.

The dialog asks for the same page size/orientation/scale/heading/
classification fields as New Military Layout — every sheet in the series
shares them. Click **OK** and a grid of sheets is generated to cover the
current extent edge-to-edge (no gaps or overlap), each registered as its
own print layout (see **Project → Layouts Manager** to open one) — they
aren't opened individually, since a large series could mean dozens of
Designer windows at once.

**Sheet naming**: each sheet is named after the real MGRS grid square its
own centre falls in — `{GZD} {100km square} #{N}`, e.g. `37M EN #1`. No
invented numbering scheme: `37M` is the UTM Grid Zone Designator and `EN`
the MGRS 100km square, the same grids the UTM Grid and MGRS 100km Grid
tools already generate. The `#N` at the end disambiguates sheets that
share the same square — normal at any practical print scale, since one
100km square is much larger than a typical sheet — and restarts at 1 for
each distinct square rather than counting the whole series, so it never
implies an ordering across the series.

**Grid position diagram**: every layout this plugin creates — a single
New Military Layout as much as one sheet in a series — gets a small inset
in the map's bottom-left corner showing exactly where it sits in that same
grid hierarchy, picked automatically from how much of it the map's own
extent actually spans:

- A small-scale map spanning more than one UTM Grid Zone Designator shows
  a mosaic of the relevant GZDs (e.g. `37M`, `38M`).
- A map that fits within one GZD but spans more than one MGRS 100km
  square shows a mosaic of those squares instead (e.g. `EN`, `FN`).
- A large-scale map (1:50,000 or finer) that fits entirely inside a single
  100km square just shows that one square.

In every case, the map's own footprint is outlined on the diagram at its
actual position and proportions — not just "which cell is closest" — so a
sheet that doesn't align to a grid boundary still shows exactly where
within the shown square(s) it sits.

A page size/scale combination that would produce more than 200 sheets is
rejected with a warning instead of silently generating an impractically
large, slow-to-build series — zoom in to a smaller extent or choose a
larger scale denominator instead.

---

## Tactical Graphics - point symbol layers

Eight actions inside the toolbar's **NATO Symbols** dropdown (see [The
toolbar, at a glance](#the-toolbar-at-a-glance)), each adding one or
more point layers where every feature automatically renders as the
correct MIL-STD-2525D/APP-6 military symbol, drawn from its own
attributes. There's no dialog and no separate symbol picker: each layer
is created empty and ready to use immediately.

**Placing a symbol**: use QGIS's own native point editing tools (toggle
editing, **Add Point Feature**) to click a location — the same tools
you'd use for any other point layer, with full undo/snapping/
vertex-editing. Filling in the attribute form that appears (or opening
it later from the attribute table) sets the symbol. Every layer shares
the same core fields:

| Field | Notes |
|---|---|
| Affiliation | Friend / Hostile / Neutral / Unknown |
| Entity | The full entity vocabulary for that layer's own domain — open the dropdown to see every option; see the table below for scope/size per layer |
| Status | Present / Planned (planned symbols render with a dashed outline) |
| Unique designation | Free-text label (e.g. "1-501 IN") |

Some layers add further fields, since MIL-STD-2525D's own amplifier
tables don't apply the same fields to every domain (a battalion has an
Echelon; a single ship or aircraft doesn't):

| Layer(s) | Echelon | Headquarters | Sector 1 / 2 Modifier | Dimension |
|---|---|---|---|---|
| Land Unit | ✅ | ✅ | — | — |
| Land Civilian / Equipment / Installation | — | ✅ | — | — |
| Space, Air, Sea Surface, Subsurface | — | — | ✅ / ✅ | — |
| Activities | — | — | ✅ / — (no sector 2 in this appendix) | — |
| Mine Warfare | — | — | — | — |
| SIGINT | — | — | ✅ / — (no sector 2 in this appendix) | ✅ |
| Cyberspace | — | — | — (no modifiers at all in this appendix) | — |

**Echelon** (where present): Unspecified, Team/Crew, Squad, Section,
Platoon, Company, Battalion, Regiment, Brigade, Division, Corps, Army,
Army Group, Theater, or Command (Table D-III of the Land appendix — the
three highest levels were added 2026-08-09; every layer above with an
Echelon column already has them, nothing further to enable).
**Headquarters** (where present): a checkbox marking the symbol as
a headquarters element. **Sector 1/2 Modifier** (where present): a
second small icon shown beside the main one — e.g. a ship's warfare
role, a submarine's propulsion type, or (Activities/SIGINT) a crime/
IED/incident qualifier or a radar/jammer category — each with an
explicit **"(None)"** option. **Dimension** (SIGINT only): Space / Air /
Land / Sea Surface / Subsurface — SIGINT's four entities (Signal
Intercept, Communications, Jammer, Radar) mean the same thing in every
dimension, so this field picks which of the five underlying symbol sets
the point actually belongs to, instead of a separate layer per
dimension.

**The eight actions / nine layers**:

**Layer names dropped their "Tactical Graphics - " prefix 2026-08-09**
(at the maintainer's request) — the QGIS Layers panel sidebar is narrow,
and with nine of these layers active at once the prefix pushed the part
that actually distinguishes them off the visible edge. The toolbar
dropdown/menu action labels dropped the same prefix, for consistency.

| Toolbar action | Layer(s) added | MIL-STD-2525D | Coverage |
|---|---|---|---|
| Space | "Space" | Appendix B (symbol sets 05, 06 merged) | Full vocabulary — every space platform/equipment entity, plus Space Missile folded in |
| Air | "Air" | Appendix C (symbol sets 01, 02 merged) | Full vocabulary — every air platform entity, plus Air Missile folded in |
| Land | "Land Unit", "Land Civilian", "Land Equipment", "Land Installation" (four layers, one click) | Appendix D (symbol sets 10, 11, 15, 20) | Curated common-vocabulary subset for each — Land Unit organised by functional area (maneuver, fires, air defense, combat support, intelligence, combat service support); Equipment/Installation cover the common platform and facility types. Not the full spec — the rendering engine supports the complete standard, so growing any of these is a vocabulary-only change |
| Sea Surface | "Sea Surface" | Appendix E (symbol set 30) | Full vocabulary — every surface vessel entity, including "Own Ship" and "Fused Track" |
| Subsurface | "Subsurface", "Mine Warfare" (two layers, one click) | Appendix F (symbol sets 35, 36) | Full vocabulary for both, including Mine Warfare's confidence-level (1-5) sub-variants for each mine position |
| Activities | "Activities" | Appendix G (symbol set 40) | Full vocabulary — incidents, civil disturbance, operations, fire/hazmat events, transportation incidents, natural events, and personalities |
| SIGINT | "SIGINT" | Appendix J (symbol sets 50-54, one per Dimension) | Full vocabulary — 4 entities (Signal Intercept, Communications, Jammer, Radar) × the full 64-entry sector 1 modifier list (radar/jammer/comms categories) |
| Cyberspace | "Cyberspace" | Appendix L (symbol set 60) | Full vocabulary — 50 entities (botnets, infections, network health/status, device types and domains, cyber effects) |

The symbol updates immediately as soon as the attributes are saved — no
regenerate step. These are a genuinely different kind of layer from
every other tool in this plugin: their content is hand-placed
operational data, not something derived from a DEM or grid, so running
a toolbar action again never touches an existing layer of the same name
(it warns instead of risking any data loss) — rename an existing layer
first if you deliberately want a second one.

**Symbol rendering**: powered by the open-source
[milsymbol](https://github.com/spatialillusions/milsymbol) library
(MIT license, see `THIRD_PARTY_NOTICES.md`), running entirely offline
in-process — no network access, no external services. These are only
the point-symbol layers; control measures (phase lines, boundaries,
objectives, NAIs) are a separate feature — see below.

**Not covered**: MIL-STD-2525D Appendix I (Meteorological and
Oceanographic — METOC) symbology isn't built. Unlike every layer above,
milsymbol has no support for it at all, so its roughly 400 symbols
(pressure systems, fronts, sea ice, wave heights, and similar) would all
be custom hand-drawn graphics rather than a lookup into an existing
renderer — a scope decided not worth building without a concrete need.
If you need METOC symbology, open an issue or a pull request and we can
scope it together.

---

## Tactical Graphics - Control Measures

Click the icon for a dropdown with one entry per Appendix H logical
group (2026-08-09 - previously a single click that added every control
measure layer at once, split up at the project maintainer's own request
so this doesn't keep growing into one unwieldy pile as more of Appendix
H gets built):

- **C2 Measures** — adds a "Lines" layer and an "Areas" layer (H.5.5/
  H.5.9/H.5.10, described below).
- **Control Measure Points** — adds the "Control Measure Points" layer
  (checkpoints, decision points, supply points, and similar - described
  further down this section).

Each layer is created empty and ready to use immediately; there's no
dialog, and clicking an entry again never replaces a layer that already
exists (each is checked independently, so it only adds back whichever
ones are still missing).

**Work in progress, being rebuilt one Appendix H section at a time.** C2
Measures' Lines layer currently offers **Boundary** and **Light Line**;
its Areas layer offers **Area of Operations**, **Named Area of
Interest**, **Target Area of Interest**, and **Airfield Zone** (H.5.5/
Table H-IV and H.5.9/Table H-V, verified against the real MIL-STD-2525D
template pictures 2026-08-09) - every other line/area measure type from
an earlier, less rigorous build pass was removed rather than left
half-verified alongside these, so what's in the dropdown is always
exactly what's actually been checked. Further Appendix H logical groups
(Maneuver, Defensive, Offensive, Airspace, Maritime, and the rest) get
their own new dropdown entry and their own layer(s), freshly verified,
as each group's own mini-phase gets its turn - see docs/roadmap.md's
Phase 10 entry for progress. The Control Measure Points layer (below) is
unaffected by this reorganisation - its ~80 point-type control measures
are unchanged, and it hasn't been split by logical group yet.

**Drawing a Boundary**: use QGIS's own native line editing tools (toggle
editing, **Add Line Feature**) to digitize the line between two units,
then fill in its attribute form. A Boundary is the two-unit shape
MIL-STD-2525D Table H-III describes:

- **Unique designation** / **Far designation** — the near and far unit's
  own designation (e.g. "2ID (USA)" / "52ID (GBR)"), shown stacked above
  and below the echelon amplifier. Always rendered in upper case
  regardless of what you type, per MIL-STD-2525D's own Labeling rule
  (Appendix H, H.5.4: "All text labeling shall be in upper case
  letters").
- **Status** — Present (solid line) or Planned / Anticipated / On Order
  (dashed line), per Table H-I.
- **Echelon** — Team/Crew through Theater, plus Command (Table D-III of
  the Land appendix) - draws the matching amplifier (Ø, •, ••, •••, I,
  II, III, X, XX, XXX, XXXX, XXXXX, XXXXXX, or ++) between the near/far
  designation lines, with the line itself genuinely cut away behind all
  three (QGIS's own label masking, not a painted box) so the background
  underneath always shows through cleanly.

This whole label - near designation, echelon amplifier, far designation -
repeats periodically along a long or multi-vertex boundary (roughly every
80mm on screen), approximating Table H-III's own "each segment repeats
the same information" rule.

Status and Echelon exist on the Lines layer's schema for every line
measure type, not just Boundary; a Status field exists on the Areas layer
too (H.5.1.1.3's own present/planned rule explicitly covers area control
measures as well as linear ones) - they're reused as later Appendix H
sections add their own measure types back in.

**Drawing a Light Line**: a plain status-driven solid/dashed line marked
"LL" above each end (Table H-IV) - optionally give it its own name (e.g.
"CRAB") in **Unique designation**, which repeats along the line the same
masked, gap-cutting way Boundary's own label does.

**Drawing an Area of Operations / Named Area of Interest / Target Area
of Interest**: use **Add Polygon Feature** to digitize the area (at
least 3 points), then set **Unique designation** for an optional name.
The label always shows the type's own fixed abbreviation - "AO", "NAI",
or "TAI" - followed by the name if you gave one (e.g. "AO BUFFALO",
matching MIL-STD-2525D's own examples). The standard's own template
pictures draw NAI/TAI as a hexagon, but the draw rules underneath say the
shape is "determined by the anchor points" the same as every other area
here - so these render whatever shape you actually digitize, not a forced
hexagon.

**Drawing an Airfield Zone**: same polygon digitizing, but with a
crossed-runway-style icon (two lines crossing at an uneven angle, a
stand-in for the standard's own specific glyph - not a plain symmetric
"X") at the area's centre instead of a type-abbreviation label -
Airfield Zone's own template has no Field A abbreviation. **Unique
designation** here represents the runway length (Field H, e.g. "750M",
matching the standard's own example) and renders just outside the
boundary rather than inside it, since that's where the standard's own
picture places it.

**Auto-populated measurements**: the Lines layer has a **Length (km)**
field, and the Areas layer has **Area (km²)** and **Perimeter (km)**
fields — all computed automatically the moment you finish digitizing
(via `mct_length_km`/`mct_area_km2`/`mct_perimeter_km`, below), and kept
up to date if you later reshape the feature. Nothing to fill in by hand.

**Affiliation and colour**: both layers also have an **Affiliation**
field (Friend / Hostile / Neutral / Unknown / Unspecified (black),
defaulting to Unspecified) that drives the control measure's colour —
friendly in blue, hostile in red, neutral in green, unknown in yellow,
unspecified in black — per MIL-STD-2525D's own Standard identity (color
rules) (Appendix H, section H.5.1.1.1: "black, blue (friendly), red
(hostile), green (neutral or obstacles), or yellow (unknown ...)").
"Unspecified" is control measures' own 5th colour choice, alongside the
four affiliations point symbols elsewhere in this plugin already use —
there's no equivalent "unspecified, draws black" option for a unit/
equipment/installation symbol, only for a control measure. The shape
itself is unaffected by affiliation; only colour changes.

**A note on accuracy**: unlike the unit symbols above (verified exactly
against the MIL-STD-2525/APP-6 SIDC specification via the milsymbol
library), there's no equivalent verified rendering engine for tactical
graphics lines and areas — Boundary's own construction is checked
directly against the standard's real template pictures (not just its
text), but it's still a hand-built QGIS rendition, not a spec-exact one -
see this section's own notes above for what's approximated and why.

### Control Measure Points

The "Control Measure Points" layer covers MIL-STD-2525D Appendix H's own
point-type control measures — command/control points (checkpoint, contact
point, decision point, rally point, ...), observation posts, target and
fire-support points, obstacle/mine/shelter/CBRN-event points, and
sustainment/supply points (ammunition supply point, casualty collection
point, MEDEVAC pick-up point, ...). Unlike the Lines/Areas layers above,
these ARE rendered through the same verified milsymbol library as the
Units layer, not hand-built QGIS symbology — so they're spec-exact, not an
approximation.

Place points with QGIS's own native **Add Point Feature** tool, then fill
in the attribute form:

- **Affiliation** — Friend/Hostile/Neutral/Unknown. Colour follows
  MIL-STD-2525D's own H.5.3 rule for control measures specifically
  (confirmed by rendering real examples through the library and reading
  the actual SVG output): friendly/neutral/unknown draw in black, hostile
  draws in red.
- **Entity** — which point control measure this is (e.g. "Checkpoint",
  "Decision Point", "Ammunition Supply Point"). About 80 of the
  standard's ~260 point control measures are available; the more
  Navy/anti-submarine-warfare-specific ones (sonobuoy types and similar)
  and the granular per-nation supply-class variants aren't currently
  included.
- **Status** — Present or Planned.

There's no "Symbol Set" field here the way the Units layer has one — this
layer only ever draws from Appendix H's control-measure set, so there's
nothing to choose between.

---

## Expression functions

All registered under the **Military Cartography Tools** group in the
expression editor (`fx` button on any field, or the Expression Builder).
`[optional]` arguments can be omitted.

### From latitude/longitude

| Function | Returns |
|---|---|
| `mct_mgrs(lat, lon)` | Full MGRS string, e.g. `37M DQ 75135 15087` |
| `mct_mgrs_zone(lat, lon)` | Grid Zone Designator, e.g. `37M` |
| `mct_mgrs_square(lat, lon)` | 100km square id, e.g. `DQ` |
| `mct_mgrs_easting(lat, lon)` | Full-precision easting digits, e.g. `75135` |
| `mct_mgrs_northing(lat, lon)` | Full-precision northing digits, e.g. `15087` |
| `mct_grid_convergence(lat, lon)` | UTM grid convergence, decimal degrees |
| `mct_magnetic_declination(lat, lon, [date])` | Magnetic declination (WMM2025), decimal degrees. `date` is an ISO string (`'2026-07-27'`) or date value; defaults to today |

### From an MGRS string (reverse conversion)

| Function | Returns |
|---|---|
| `mct_mgrs_to_point(mgrs_string)` | Point geometry (WGS84) |
| `mct_mgrs_lat(mgrs_string)` | WGS84 latitude |
| `mct_mgrs_lon(mgrs_string)` | WGS84 longitude |

### From a print layout's map item

All take a layout name as the first argument (and most accept an optional
map item id as the last argument, for layouts with more than one map item —
omit it to use the layout's first/only map item).

| Function | Returns |
|---|---|
| `mct_map_center_mgrs(layout_name, [precision], [map_id])` | Map centre in MGRS. `precision` 2–5 (1km down to 1m); defaults to 5 |
| `mct_map_scale(layout_name, [map_id])` | Map scale as `"1:N"` |
| `mct_map_rotation(layout_name, [map_id])` | Map rotation, degrees |
| `mct_map_width(layout_name, [map_id])` | Map extent width, in the map's CRS units |
| `mct_map_height(layout_name, [map_id])` | Map extent height, in the map's CRS units |
| `mct_map_center_lat(layout_name, [map_id])` | Map centre latitude (WGS84) |
| `mct_map_center_lon(layout_name, [map_id])` | Map centre longitude (WGS84) |
| `mct_map_convergence(layout_name, [map_id])` | Grid convergence at the map's centre |
| `mct_map_magnetic_declination(layout_name, [date], [map_id])` | Magnetic declination at the map's centre. Note `date` comes *before* `map_id` here, matching `mct_map_center_mgrs`'s argument order |

These are live: reference them in a layout label's expression (e.g.
`[% mct_map_scale(@layout_name) %]`) and they update automatically as you
pan, zoom, or rescale the map in the Designer — this is what drives the
metadata block and center-of-map label in every New Military Layout.

### Military symbology

| Function | Returns |
|---|---|
| `mct_build_sidc(affiliation, entity, symbol_set, echelon, status, headquarters, [sector1_modifier], [sector2_modifier])` | A 20-character SIDC from named components — see [Tactical Graphics - point symbol layers](#tactical-graphics---point-symbol-layers) |
| `mct_sidc_svg(sidc)` | A rendered symbol as a `"base64:<...>"` path, usable directly as a `QgsSvgMarkerSymbolLayer` path |
| `mct_area_km2($geometry)` | A polygon's geodesic area in km² — for AO/NAI reporting on any polygon feature, not just the Areas control-measures layer |
| `mct_perimeter_km($geometry)` | A polygon's geodesic perimeter in km |
| `mct_length_km($geometry)` | A line's geodesic length in km — for phase lines/boundaries/axis of advance |

These three take only `$geometry` — a bare geometry carries no CRS of its
own, so they measure against the current **project's** CRS (via
`QgsProject.instance().crs()`) rather than needing a layer passed in
explicitly. An earlier version took `$geometry, @layer`, but `@layer`
turned out not to be reliably populated by every QGIS expression entry
point — notably the attribute table's own in-place field calculator
toolbar, which silently evaluated it as NULL (shown as `nan`) even though
`$geometry` itself resolved correctly. Correct for any layer this plugin
creates itself (they're always built in the project's own CRS); if you
reuse these functions on a layer whose CRS was later changed independently
of the project, reproject the layer to match first.

Every function returns a short error string (e.g. `"Layout not found"`,
`"Need latitude, longitude"`) instead of failing silently if its arguments
don't resolve.
