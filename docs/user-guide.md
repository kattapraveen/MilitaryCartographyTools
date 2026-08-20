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
- [Print-layout toolbar](#print-layout-toolbar)
- [Tanaka Contours](#tanaka-contours)
- [Hypsometric Tint](#hypsometric-tint)
- [Line of Sight](#line-of-sight)
- [Hillshade Combinations](#hillshade-combinations)
- [Viewshed](#viewshed)
- [Sensor Coverage](#sensor-coverage)
- [Waypoint Import/Export (GPX/KML)](#waypoint-importexport-gpxkml)
- [Map Sheet Series](#map-sheet-series)
- [Tactical Graphics - point symbol layers](#tactical-graphics---point-symbol-layers)
- [Tactical Graphics - Control Measures](#tactical-graphics---control-measures)
- [Expression functions](#expression-functions)

---

## Installation

Requires QGIS 3.44 or later. Install from the [official QGIS Plugin
Repository](https://plugins.qgis.org) via **Plugins → Manage and Install
Plugins**, search for "Military Cartography Tools" — or manually:

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
| Toggle switch | *(standalone)* | **Symbology Edition** — MIL-STD-2525D/APP-6D or MIL-STD-2525E/APP-6E; picks which standard newly added symbology layers use, see [below](#tactical-graphics---point-symbol-layers) |
| 3×3 grid | **Grid** | UTM Grid, MGRS 100km Grid, Sub Grid (10km/5km/1km spacing, itself a nested flyout), Clear Grid |
| Compass rose | **Navigation** | Coordinate Probe, Bearing / Range |
| Layered peaks with a contour line | **Terrain Analysis** | Tanaka Contours, Hypsometric Tint, Hillshade Combinations, Line of Sight, Viewshed, Sensor Coverage |
| Location pin | **Waypoints** | Import Waypoints, Export Waypoints |
| Printed sheet with a folded corner | **Print Production** | New Military Layout, Map Sheet Series |
| Hexagonal frame with a centre dot | **NATO Symbols** | Every MIL-STD-2525D/E and APP-6D/E point symbol layer (Space, Air, Land, Sea Surface, Subsurface, Activities, SIGINT, Cyberspace) plus Control Measures |

Each individual tool keeps its own icon and behaviour exactly as
described in its own section below (checkable tools still show as
checked/unchecked inside the dropdown, same as they did as standalone
toolbar buttons) — grouping only changes *where* you click to reach it.

Each Layout Designer window (opened from a print layout) additionally gets
its own small toolbar with **Add/Remove Grid Frame**, **Insert Symbol**, and
a **Military Layout Settings** toggle — see their own sections below.

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
  extent (e.g. `37M`). Cells are 6° × 8° everywhere except the two places
  the standard itself makes an exception, both of which are drawn correctly:
  over south-west Norway (band V, 56–64°N) `31V` narrows to 3° and `32V`
  widens to 9°, and over Svalbard (band X, 72–84°N) `32X`, `34X` and `36X`
  do not exist at all, with `31X`, `33X`, `35X` and `37X` widened to cover
  that ground.
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

## Print-layout toolbar

Each Layout Designer window's own small toolbar has:

- **Add Grid Frame** — adds border tick marks and coordinate annotations
  around the map, spaced automatically for the layout's current print
  scale, and hides the sub-grid layer's own on-map tick labels for that
  layout specifically (the interactive canvas keeps showing them normally).
- **Remove Grid Frame** — removes it and restores the normal on-map labels
  for that layout.
- **Insert Symbol** — places a MIL-STD-2525/APP-6 symbol directly onto the
  layout page (for a legend key, a callout, or a cover sheet, rather than a
  georeferenced feature on the map). Pick an **Affiliation**, **Symbol
  Set** and **Entity** and click **Insert**; the symbol appears near the
  top-left corner of the page as a normal, draggable/resizable picture
  item, using whichever standard the toolbar's own Symbology Edition
  setting is currently on. Deliberately minimal: no echelon, status,
  headquarters or sector modifiers — it is a static picture, not a live
  feature, so there is nothing to edit afterwards; build the symbol on a
  map layer instead if you need the fuller set of amplifiers.

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
you've since panned or zoomed.

The dialog carries a standing **caution** about generation time, and it's
a real one: a large DEM and a fine contour interval multiply together into
a lot of work, and QGIS will simply look busy until it finishes rather
than showing progress. The two settings that cost the most are **contour
interval** (smaller means far more lines) and **segment length** (smaller
means every line is cut into more pieces, each needing its own elevation
sample). If a run is taking longer than you want to wait, crop the DEM
itself first, or start with a coarser interval and refine from there.

### Getting a DEM

This plugin doesn't include a DEM downloader — that's a generic GIS task
already well covered elsewhere. If you don't already have elevation data
for your area, options include QGIS's own **Data Source Manager** (WCS
connections), or a dedicated plugin such as **SRTM Downloader** (via
**Plugins → Manage and Install Plugins**).

**For bathymetry — depth below sea level — SRTM won't help**, since it
carries land elevation only and leaves water flat. The usual free source
is **GMRT** (the Global Multi-Resolution Topography synthesis), which
serves grids over your own bounding box from its **GridServer** web
service at `https://www.gmrt.org/services/gridserverinfo.php`. There is
no dedicated QGIS downloader plugin for it, so the practical routes are
GMRT's own **GMRT MapTool** website (draw an area, download a GeoTIFF,
then add it as a raster layer), or QGIS's built-in **Download file**
Processing algorithm with a GridServer URL built by hand.

Two things worth knowing once you have bathymetry loaded. Depths arrive
as **negative** elevations, and both Line of Sight and Viewshed
deliberately clamp anything below zero up to sea level — an observer on
water sits on the surface, not the seabed. And the Hypsometric Tint's
colour ramp already has its own below-sea-level band, so a bathymetric
DEM tints correctly without any extra setup.

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
sweeps every direction out to a chosen range and draws a polygon covering
just the area actually visible from the observer — green by default, in
whatever colour you pick. Ground that's out of range, or hidden behind
terrain, is left blank rather than filled in — a full coloured circle
covering the whole swept area reads as "the whole circle matters," which
was more confusing than useful in practice. Like Line of Sight, this
accounts for both real terrain and earth curvature/atmospheric
refraction, and treats any elevation below sea
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
| Opacity | How solid the visible area appears, so terrain underneath still shows through (default 65%) |
| Colour | The colour the visible area is drawn in (default green, the same green Line of Sight uses for a visible line). Useful for telling several observers' coverage apart, or for staying legible over a base map the default green disappears into |
| Outline only (no fill) | Off by default. Check it to draw just the boundary of the visible area instead of filling it, leaving whatever's underneath fully readable — worth knowing that a real viewshed breaks into many small fragments, so an outline-only result shows scatter that a solid fill visually merges together |
| Add as new layer | Off by default — clicking again corrects the existing "Viewshed" layer in place. Check this to keep the previous result and add a new one alongside it instead |

Adjust a field — including colour and outline-only — and press
**Generate** to re-run without re-clicking, or just click a different
point on the map — every click is a complete,
standalone analysis on its own, so there's no observer/target pair to keep
track of. Like Line of Sight, the DEM is clipped to a box around wherever
the observer actually is (sized from the max distance you've set), not
tied to the current map canvas extent, and the tool stays active across
repeated clicks until you select a different tool.

---

## Sensor Coverage

Where Viewshed answers "what can this one observer see", Sensor Coverage
answers "what does this whole sensor laydown cover" — several sensors
plotted together, with their coverage merged into one picture.

Click the two-overlapping-circles icon to open the setup dialog. Pick
your **DEM layer** and tick which of the three levels you need, and the
plugin creates a **Sensor Points** layer for each one. That's all the
dialog does — everything after this happens on the layers themselves.

### The three levels

Sensors are split by how high above themselves they can detect, each
level with its own points layer and its own coverage layer:

| Level | Detection height above the sensor |
|---|---|
| **Low Level** | Up to 3,300 m (10,000 ft) |
| **Medium Level** | 3,300 m to 7,000 m (10,000–25,000 ft) |
| **High Level** | Above 7,000 m (above 25,000 ft) |

**These bands are measured from the antenna, not from sea level**, and
that distinction matters as soon as you site anything on high ground.
A radar with a 5 m mast on a boat sits at 5 m AMSL, so a 3,300 m
capability reaches up to 3,305 m — an aircraft at 3,500 m is above it
and out of reach. Put the identical radar on a 2,000 m plateau and it
sits at 2,005 m, so the same capability now reaches 5,305 m and that
same aircraft is comfortably inside the low-level picture. Siting a
sensor higher lifts its whole band with it.

Each level draws in its own colour — green, amber and blue respectively —
so all three can be read together over the same ground. A whole band can
be shown or hidden with its own checkbox in the Layers panel. Each band
is drawn at its own **top**, so for identically sited sensors the three
nest: whatever the low-level layer covers, the medium and high layers
cover too.

### Plotting sensors

Select the **Sensor Points** layer for the level you want, toggle
editing on, and place sensors with QGIS's ordinary **Add Point** tool.
Each sensor carries its own characteristics:

| Field | Notes |
|---|---|
| Sensor height | Height of the antenna above the ground it stands on, in metres (default 5). The DEM supplies the ground elevation underneath it |
| Max detection height above sensor | How far above itself this sensor can detect, in metres — limited to that layer's own band, so a point on the Low Level layer can't be given a high-level capability by accident. Defaults to the band's ceiling |
| Maximum range | That individual sensor's own detection range, in metres (default 30,000) |

Range and sensor height are deliberately **not** tied to the level.
Sensors in the same band routinely differ by an order of magnitude — a
man-portable set at 5–6 m and 30 km, a vehicle-mounted one at 10–12 m
and 150 km, and a ground-based one at 10–15 m and 180 km can all be
low-level sensors — so each point carries its own figures. Only the DEM
is shared across the whole laydown.

### The coverage layer

Save your edits and a **Sensor Coverage** layer appears for that level,
covering everything visible from any sensor on it. Where two sensors'
coverage overlaps, the two are **merged into a single perimeter** rather
than drawn on top of each other; sensors too far apart to overlap simply
keep their own separate outlines.

Each sensor's own footprint accounts for terrain, earth curvature and
atmospheric refraction, and treats water as sea level rather than seabed
depth. Unlike Viewshed, the target is modelled as **flying level at a
fixed altitude** rather than at a fixed height above whatever ground is
underneath it — so a mountain taller than the target's altitude hides
what is behind it, and the mountain itself isn't covered either. An
aircraft at 3,305 m cannot be over a 4,000 m peak.

Refraction uses the **4/3-earth model** standard for radar (k = 0.25),
rather than the optical coefficient Line of Sight and Viewshed use. That
pushes the horizon out roughly 15% further than an optical sightline —
on a long-range set, tens of kilometres.

Coverage updates itself: move a sensor with the vertex tool, correct a
range in the attribute form, add or delete a point, and that level's
coverage redraws when you **save your edits**. Only the level you edited
is recomputed — the other two bands are left alone. Regeneration is
deliberately tied to saving rather than to every intermediate drag
position, because each sensor on the layer means a full viewshed
computation and re-running that continuously through a drag would make
the drag itself unusable.

Deleting the last sensor on a level removes that level's coverage layer,
rather than leaving a shape behind claiming ground nothing covers any
more.

### On maximum ranges

The maximum range field is that sensor's own detection range — the
plugin doesn't compute one for you, because the real limit is the
sensor's own capability far more often than it is the horizon. For
reference, though, curvature alone puts a hard ceiling on any sightline.
Using the radar 4/3-earth model, the horizon distance for something at
height *h* metres is roughly `4.12 × √h` km, and the maximum range
between sensor and target is the sum of both horizons. For a 5 m mast at
sea level:

| Detection height above the sensor | Curvature ceiling |
|---|---|
| Ground level (0 m) | ~9 km |
| 3,300 m (10,000 ft) | ~246 km |
| 7,000 m (25,000 ft) | ~354 km |
| 30,000 m | ~723 km |

Those are unobstructed-atmosphere ceilings, not suggested values —
terrain cuts real coverage well below them anywhere that isn't open flat
ground, and at medium and high level a sensor's own range binds long
before curvature does. Note that these grow when the sensor is sited
higher, since both the sensor's own horizon and the target's altitude
rise together.

### What is deliberately not modelled

Antenna tilt limits, beam width, and RF path loss are all left out. Path
loss in particular (Longley-Rice, ITU-R P.1812 and similar) needs
frequency, transmit power, antenna gain, receiver sensitivity and ground
constants — supply guesses for those and you get a confident-looking
signal contour built on invented numbers. This tool models geometry
only: terrain, curvature, and the range you state. It claims what it
knows and nothing more.

Requires a DEM layer already loaded in your project (see "Getting a DEM"
above). Reopen the dialog at any time to add a level you skipped, or to
point an existing laydown at a different DEM.

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
correct military symbol under whichever edition the layer was built
against (MIL-STD-2525D/APP-6D by default, or MIL-STD-2525E/APP-6E - see
[Symbology edition](#tactical-graphics---point-symbol-layers) below),
drawn from its own attributes. There's no dialog and no separate symbol
picker: each layer is created empty and ready to use immediately.

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
| Rotation | Degrees, clockwise from north — default 0. Turns the whole symbol, amplifiers included (echelon ticks, unique designation text), as one picture rather than just the base icon. |
| Scale | Percent of the symbol's own default size — default 100. |

Some layers add further fields, since MIL-STD-2525D's own amplifier
tables don't apply the same fields to every domain (a battalion has an
Echelon; a single ship or aircraft doesn't):

| Layer(s) | Echelon | Headquarters | Sector 1 / 2 Modifier | Dimension |
|---|---|---|---|---|
| Land Unit | ✅ | ✅ | ✅ / ✅ | — |
| Land Civilian / Installation | — | ✅ | ✅ / ✅ | — |
| Land Equipment | — | ✅ | ✅ / — (no sector 2 in this appendix) | — |
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
| Land | "Land Unit", "Land Civilian", "Land Equipment", "Land Installation" (four layers, one click) | Appendix D (symbol sets 10, 11, 15, 20) | Land Civilian: full vocabulary. Land Equipment and Land Installation: essentially the full standard, including complete law-enforcement families. Land Unit: still a curated common-vocabulary subset organised by functional area (maneuver, fires, air defense, combat support, intelligence, combat service support) — every other layer above it was widened first. Not the full spec on Land Unit yet — the rendering engine already supports the complete standard, so widening it further is a vocabulary-only change |
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

**Symbology edition (MIL-STD-2525D/E, APP-6D/E)**: a **Symbology
Edition** menu on the toolbar picks which standard NEWLY ADDED point
symbol layers (and Control Measures layers, below) are built against —
either "MIL-STD-2525D / APP-6D" (the default) or "MIL-STD-2525E /
APP-6E". It's a plugin-wide setting, remembered between sessions, not a
per-feature choice — an individual symbol can't mix editions, because
the standard itself defines the Entity and Sector 1/2 Modifier
vocabularies differently per edition.

Switching the setting **never changes a layer already in your
project** — each layer's own symbol rendering is fixed at the moment
it's created, and a layer added before this setting existed keeps
working exactly as it always has (read as MIL-STD-2525D). Both editions
of the same layer type can exist side by side in one project: adding
"Air" once under each edition gives you two distinct layers, named "Air
(2525D/6D)" and "Air (2525E/6E)" so they're never confused with each
other in the Layers panel — adding the identical layer a third time
under an edition you've already used is still refused, same
data-safety guard as every other layer here.

MIL-STD-2525E's own vocabulary is substantially larger than 2525D's for
some domains (Land Unit in particular) and drops a handful of 2525D
codes it retired outright. APP-6E is not built as a fully separate
vocabulary — it shares MIL-STD-2525E's symbology closely enough that
the "2525E/6E" edition serves both; if you specifically need APP-6E's
own wording or modifier tables and hit a gap, open an issue.

---

## Tactical Graphics - Control Measures

Click the icon for a dropdown with one entry per Appendix H logical
group (2026-08-09 - previously a single click that added every control
measure layer at once, split up at the project maintainer's own request
so this doesn't keep growing into one unwieldy pile as more of Appendix
H gets built):

- **C2 Measures** — adds a "Lines" layer, an "Areas" layer, and a
  "Points" layer (H.5.5/H.5.9/H.5.10, described below).
- **Sustainment Points**, **Supply Control Measures**, **Mission
  Tasks** — one menu entry per table (H.5.24/H.5.25/H.5.26, described
  further down this section). Sustainment Points adds only its own
  point layer; Supply Control Measures adds a "Supply Points" layer
  plus a lines layer and an areas layer (named for what it adds, not
  "Supply Points", since that name would promise only the one); Mission
  Tasks also adds a lines layer alongside its own points.

Each layer is created empty and ready to use immediately; there's no
dialog, and clicking an entry again never replaces a layer that already
exists (each is checked independently, so it only adds back whichever
ones are still missing).

**Every Points layer under Control Measures also has a Rotation
field** (degrees, clockwise from north — default 0) **and a Scale
field** (percent of the symbol's own default size — default 100),
alongside its own Affiliation/Entity/Status/Unique designation fields
— the same two fields every point-symbol layer described in
[Tactical Graphics - point symbol layers](#tactical-graphics---point-symbol-layers)
has. Rotating or scaling a symbol carries its own amplifiers along
with it as one picture. Lines and Areas layers don't have these
fields — only Points.

**Appendix H is complete** — every one of its logical groups was rebuilt
and verified one section at a time, finishing 2026-08-16. C2
Measures' Lines layer offers **Boundary** and **Light Line**;
its Areas layer offers **Area of Operations**, **Named Area of
Interest**, **Target Area of Interest**, and **Airfield Zone** (H.5.5/
Table H-IV and H.5.9/Table H-V, verified against the real MIL-STD-2525D
template pictures 2026-08-09); its Points layer offers all 22 of Table H-VI's own
command-and-control point types (Checkpoint, Contact/Coordination/
Decision Point, Fly-To Point, Rally Point, and similar - added
2026-08-10, moved out of the shared Control Measure Points layer that
used to sit alongside these and has since been retired; two entries this layer briefly
carried, Target Handover and Key Terrain, were removed again the same
day once cross-checked against the real standard text and found not to
exist in Table H-VI, or anywhere in MIL-STD-2525D at all) - every other
line/area measure type from an earlier,
less rigorous build pass was removed rather than left half-verified
alongside these, so what's in each dropdown is always exactly what's
actually been checked. Every other Appendix H logical group (Maneuver,
Defensive, Offensive, Airspace, Maritime, Obstacles, CBRN, Sustainment,
Supply, Mission Tasks, Intelligence, and the rest) has its own dropdown
entry and its own layer(s), built and verified the same way - see
docs/roadmap.md's own "Appendix H — complete" section for the ledger.
Every H.5.x group now has its own point layer: the shared
Control Measure Points layer that used to hold whatever hadn't been
split out yet was emptied and retired on 2026-08-14, when
Sustainment/Supply/Mission Task Points took its last 21 entries. It
had previously handed off Table
H-VI (now on C2 Measures), Table H-IX (now on Defensive Control
Measures), Table H-XI's Point of Departure (now on Offensive Control
Measures), Table H-XIII (now on Airspace Control Measures), Table
H-XIV (now on Maritime Control Measures) and Table H-XVII (now on
Target Control Measures).

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

**C2 Measures' own Points layer** (Table H-VI, H.5.10) works the same
way as every other point layer in this section - pick an **Entity**
from the dropdown (Unspecified Control Point,
Amnesty Point, Checkpoint, Center of Main Effort, Contact/Coordination/
Decision Point, Distress Call, Entry Control Point, Fly-To Point
(Sonobuoy/Weapon/Normal), Linkup/Passage Point, Point of Interest (and
its own Launch Event variant), Rally/Release/Start/Special Point,
Waypoint), then set **Affiliation** and **Status**; the symbol
is rendered through the same milsymbol library as the unit layers above,
not hand-built QGIS symbology like the Lines/Areas layers on this same
page. Give it a **Unique designation** too and it appears wherever that
specific icon's own layout puts it - below the main text for most of
these, but centred in the box for some (Contact Point) and to the right
of the icon's own line for others (Waypoint) - milsymbol
handles the placement per icon, not a fixed rule this plugin applies
uniformly.

### Maneuver Control Measures

The **Maneuver Control Measures** entry in the same Control Measures
dropdown adds its own "Lines" and "Areas" layers (MIL-STD-2525D Appendix
H.5.11, Table H-VII) - a separate pair from C2 Measures' own, since each
Appendix H logical group gets its own layers (see the intro to this
section).

**Lines** offers **Forward Line of Troops (FLOT)** (one continuous
touching chain of open semicircular arcs, colour driven by Affiliation
like every other measure here - solid when Present, dotted when Planned/
Suspected), **Line of Contact (LOC)** (two offset arc chains with a
4.5mm gap between them, bulging toward the opposite side - friendly
convex toward the enemy, enemy convex toward friendly, a ")(" shape -
one chain always black, the other always red, since both sides are shown
at once and affiliation doesn't apply), **Phase Line** (a plain line with
"PL" + your own name at each end, no tick), **FEBA** ("FEBA" at each
end, no tick), and **Principal Direction of Fire** (draw it as a 3-point
line - the far point, the vertex, then the other far point - for a
two-armed arrow with both arrowheads pointing away from the vertex).

**Areas** offers a plain **Area** (no label), **Assembly Area (AA)**,
**Joint/Submarine/Submarine-Generated Action Area** (JTAA/SAA/SGSA -
labelled "JTAA-02" style, with optional start/end date-time-group
fields shown as a second line, e.g. "051030-051600Z"), **Drop/
Extraction/Landing/Pickup Zone** (DZ/EZ/LZ/PZ), **Fortified Area** (a
genuinely castellated/toothed outline, computed geometry rather than a
styling approximation - see docs/roadmap.md's own Mini-Phase H3
correction-pass entry for how), and **Limited Access Area (LAA)** (a
hatched-fill freeform area, the same technique Airspace Control
Measures' own Weapons Free Zone uses).

Only **Occupied Assembly Area with Offset Unit(s)** is deliberately not
built here - it needs a second, separately-connected point/leader-line
this plugin's control-measure layers don't support yet.

### Defensive Control Measures

The **Defensive Control Measures** entry adds an "Areas" layer and a
"Lines" layer (both MIL-STD-2525D Appendix H.5.12.1, Table H-VIII) and
a "Points" layer (H.5.12.2, Table H-IX).

**Battle Position** and **Strong Point** both carry an optional
**Echelon** field (the same Table D-III amplifier Boundary uses under
C2 Measures - Ø, •, ••, •••, I, II, III, X, XX, ...) - drawn IN the
perimeter line itself, at the point where you started digitizing the
polygon, with a real gap cut in the line around it (the same masked-gap
technique Boundary uses), not as a floating label. Battle Position also
has a **Prepared** field - set it to add a "(P) " prefix to the name for
a battle position that's dug in and ready but not yet occupied (e.g.
"(P) MARS"); setting Prepared always draws the outline dashed, even if
Status is still left at Present, since "Prepared but not occupied" is
its own dashed variant in the standard regardless of the separate Status
field. Strong Point additionally draws a spiked/toothed border around
the whole outline, pointing outward only regardless of which direction
you digitized the polygon. **Engagement Area (EA)** is a plain outline
with an "EA" + optional name label, the same pattern as C2 Measures' own
AO/NAI/TAI.

**Contain** and **Retain** are on the **Lines** layer, not Areas -
neither is a boundary you digitize, so neither fits the
polygon-per-symbol model every area here uses.

- **Contain** takes **three** clicks. Points 1 and 2 are the two ends
  of the semicircle's opening (so the line between them is its
  diameter), and point 3 sets how long the arrow is and which side the
  opening faces. The arc always bulges away from point 3, ticks point
  inward, and a red arrow runs down the perpendicular through the
  arc's centre with a red "ENY" set into its shaft.
- **Retain** takes **two**. Point 1 is the centre; point 2 is both the
  radius and where the arc starts. It sweeps 300° clockwise from
  there, leaving a 60° opening, with an arrowhead at the far end,
  ticks pointing outward, and an "R" half way round.

Both scale entirely with the radius - tick length is a third of it for
Contain and a fifth for Retain - so the symbol keeps its proportions
whatever size you draw it. The "C" and "R" sit in a real gap in the
perimeter, and the tick behind each is shortened rather than removed,
matching the standard's own templates.

**Defensive Control Measures' own Points layer** (Table H-IX) offers
**Observation Post/Outpost** and its own Reconnaissance/Forward
Observer/CBRN/Sensor-Listening/Combat Outpost variants, plus **Target
Reference Point** - pick an **Entity** from the dropdown, then set
**Affiliation** and **Status**, the same way as C2 Measures' own Points
layer above. Moved here from the shared Control Measure Points layer on
2026-08-10 (that layer has since been retired), since a flat ~90-entry
dropdown made these 7 hard to find.

### Offensive Control Measures

The **Offensive Control Measures** entry adds its own "Lines" and
"Areas" layers (MIL-STD-2525D Appendix H.5.13, Tables H-X/H-XI).

**Lines** offers two visually different arrow families, plus a handful
of simple end-labelled lines:

- **Axis of Advance** (Friendly Airborne/Aviation, Attack Helicopter,
  Main Attack, Supporting Attack, for a Feint, Enemy) - drawn as a
  thick line with a solid arrowhead at the end. The standard's own
  construction is a variable-width tapered ribbon computed from up to
  50 anchor points; this plugin approximates it as a single-width line
  along whatever path you digitize, so the exact taper and the small
  per-type decorations (a crossed "X" for Attack Helicopter, a doubled
  outline for Main Attack, ...) aren't reproduced - only the arrow
  shape and colour are.
- **Direction of Attack** (the same six sub-types) - drawn for real,
  not approximated: a thin line with a small open (unfilled) chevron
  arrowhead at the end.
- **Final Coordination Line (FCL)**, **Limit of Advance (LOA)**, **Line
  of Departure (LD)**, **Line of Departure/Line of Contact (LD/LC)** -
  a plain line with the fixed abbreviation at each end, the same
  pattern as C2 Measures' own Light Line.
- **Probable Line of Deployment (PLD)** - same "PLD" end-label
  construction, but always dashed regardless of the Status field - the
  standard's own note says this one is dashed in both Present and
  Planned status.

**Areas** offers **Assault Position (ASLT)**, **Attack Position
(ATK)**, and **Objective Area (OBJ)** - all the familiar "prefix +
optional name" pattern.

**Infiltration Lane** is here too — two parallel lines with a plain
designation centred between them, approximated the same way Main
Attack's doubled outline is rather than with genuine variable-width
geometry. **Point of Departure** is a point symbol, so it lives on this
group's own Points layer.

### Maneuver Control Measures II

The standard's own Appendix H.5.14 section is titled "Maneuver control
measure symbols" - the identical title H.5.11 already uses - so this
entry (Table H-XII) got a "II" suffix to tell it apart from the earlier
**Maneuver Control Measures** entry, not because it's a lesser or
optional set.

**Lines** offers **Support by Fire Position** and **Search Area/
Reconnaissance Area** (both arrow-based, an arrowhead at each end or at
a shared vertex plus a boxed "A"), plus four simple end-labelled lines:
**Airhead Line** (a fixed, centred "AIRHEAD LINE" label rather than one
at each end), **Bridgehead Line (BL)**, **Holding Line (HL)**, and
**Release Line (RL)**.

**Areas** offers **Encirclement** (a spiked/toothed border, the same
technique as Defensive Control Measures' own Strong Point) and
**Penetration Box** (a plain outline, no label).

**Attack By Fire Position** is on the Maneuver Control Measures layer
rather than here. It needed a shaft whose tail meets not a point you
digitize but the *computed midpoint* between two others, so both halves
of the symbol are generated from the clicked path instead of the path
being drawn directly — the same technique Support by Fire Position was
rebuilt onto.

**Ambush** is on that same layer, for the same reason and built with
the same technique.

### Airspace Control Measures

MIL-STD-2525D Appendix H.5.15 (Table H-XIII) splits airspace control
means into points, corridors/routes, and zones. All three are here, on
their own **Lines**, **Areas** and **Points** layers.

**Lines** offers the corridor/route family — **Air Corridor (AC)**,
**Low-Level Transit Route (LLTR)**, **Minimum-Risk Route (MRR)**, **Safe
Lane (SL)**, **SAAFR**, **Transit Corridor (TC)**, **Unmanned Aircraft
(UA) Route** — each drawn as a moderately-thick status-driven line with
a centred "PREFIX NAME" label. The standard's own template draws these
as a variable-width ribbon with rounded Air Control Point/Communications
Checkpoint circles at each end and up to 5 extra fields (width, min/max
altitude, DTG start/end); this plugin keeps only what's SIDC-relevant
(the measure type, colour, and name) and drops the taper, endpoint
circles, and extra fields — place separate Air Control Point/
Communications Checkpoint features from the Points layer below at the
ends if you want them shown. Also on this layer: **Identification,
Friend-or-Foe (IFF) Off/On Line**, simple lines with a fixed "IFF OFF"/
"IFF ON" label at each end.

**Areas** offers 12 zone types, all a plain status-driven outline with a
centred "PREFIX\nNAME" label: **High-Density Airspace Control Zone
(HIDACZ)**, **Restricted Operations Zone (ROZ)**, **Air-to-Air ROZ
(AARROZ)**, **Unmanned Aircraft ROZ (UA-ROZ)**, and the Weapon Engagement
Zone family — **WEZ**, **FEZ**, **JEZ**, **MEZ**, **LOMEZ**, **HIMEZ**,
**SHORADEZ** (the standard's own note says WEZ "includes" the other five
as its own sub-types, but the table lists each as its own separate SIDC
code too, so all six are separate dropdown entries here). **Weapons Free
Zone (WFZ)** is the one exception — the standard's own template requires
a genuine hatched fill ("upward diagonal lines are part of the fill"),
the first area in this plugin's whole Appendix H pass with a real fill
rather than a plain outline.

**Base Defense Zone (BDZ)** is on the **Lines** layer, and is drawn by
clicking **two** points — the first is the zone's centre, the second sets
its radius. The standard itself specifies a single anchor point and a
fixed ("Static") size; this plugin deliberately departs from that so the
zone can be sized to the ground it actually covers. It sits on the Lines
layer rather than Areas because a centre-plus-radius pair is a 2-point
line, not a polygon.

**Points** offers all 26 of the table's own point symbols — **Airspace
Control Points** (the generic parent), **Air Control Point (ACP)**,
**Communications Checkpoint (CCP)**, **Downed Aircrew Pick-Up Point**,
**Pop-Up Point (PUP)**, **Air Control Rendezvous**, **TACAN**, **CAP**,
**AEW**, **ASW (Helo and F/W)**, **Strike Initial Point**,
**Replenishment Station**, **Tanking**, **Antisubmarine Warfare, Rotary
Wing**, **SUCAP** and **MIW** (each fixed- and rotary-wing),
**Tomcat**, **Rescue**, **Unmanned Aerial System (UAS/UA)**, **VTUA**,
and **Orbit** with its **Figure Eight**, **Race Track** and **Random
Closed** variants. These are drawn by milsymbol, the same way unit
symbols are, so they take the usual affiliation/status fields rather
than this appendix's hand-built line and area styling.

Only three of them show a **unique designation**: ACP and CCP print it
inside the circle beneath their own text, and TACAN prints it outside at
top right. The standard shows a designation box on exactly those three
and no others, so typing one against any other entry has no visible
effect. Note also that every one of these is centred on the point you
click except **Downed Aircrew Pick-Up Point**, whose point marks the
*tip of the inverted cone* — so it draws entirely above where you click.

### Maritime Control Measures

MIL-STD-2525D Appendix H.5.16 (Table H-XIV) turned out to be
overwhelmingly Navy-AEGIS-combat-system-specific or anti-submarine-
warfare/sonar-specific, not general-purpose maritime control measures —
this section is heavily curated as a result, and (unlike every other
Appendix H section built so far) has no Areas layer at all, since the
table's own content never reaches an "Areas" heading.

**Lines** offers **Navigational** plus the **Bearing Line** family.

**Navigational** is the hazard-marker Z: click the two corner points and
it draws the run between them, then a fixed **6 mm** flank at each
corner — 40° off the direction of travel at the first, 220° at the
second. Those two are 180° apart, so the symbol reads the same whichever
way round you click. The flanks stay 6 mm on the page at any zoom, which
is the standard's own rule that the symbol "varies only in length"; only
the middle run grows.

The **Bearing Line** family is a simple 2-point line
with a fixed abbreviation centred along it: **Bearing Line (B)**,
**Electronic (E)**, **Electronic Warfare (EW)**, **Acoustic (A)**,
**Acoustic (Ambiguous)** (a separate, always-dashed SIDC code, not a
status variant), **Torpedo (T)**, **Electro-Optical Intercept (O)**,
**Jammer (J)**, **Radio Detention Finder (RDF)**.

That abbreviation stays **upright whichever way you draw the line** —
draw a bearing right-to-left or steeply downhill and the letter still
reads level rather than upside-down — and it **masks the line**, so the
line breaks cleanly around it instead of striking through the glyph.

Each line also takes an optional **unique designation**, drawn at the
line's **end**, below and to the right of the last vertex, also upright.
This is the identifier the standard's own template shows in a small box
near the PT.2 end (its examples include "MSL"/"MCU"/"TENT" for Electronic
Warfare, "L3-ACT" for Acoustic, "PAT-1" for Jammer). It's free text
rather than a fixed per-type list, so type whatever your own unit uses;
leave it blank and nothing is drawn. Note the standard puts this box
just *above* the end point — below-right is a deliberate choice here.

**Points** carries the table's whole point vocabulary — all 105 usable
symbols from printed pages 474–501. That is far too many for one flat
list, so the form asks for them in two steps: **pick a Group first, and
the Entity dropdown offers only that group's own symbols.** The groups
are the standard's own sub-headings — **General**, **Sub-Surface
Warfare**, **Search**, **Sonobuoys**, **Reference Points**, **Subsurface
Stations**, **Surface Stations**, **Routes**, **Emergency**, **Hazard**,
and **Sea Subsurface Returns** — which brings the longest list you ever
face down to 17 entries, and most of them to under 10.

Change the Group after choosing an Entity and the Entity list re-filters,
but your old choice stays in the field. That combination is rejected on
save, with the message *"The entity must be one of the chosen group's own
entries"* — pick an entity from the new group's list and it clears.

The Group field is also a real attribute, so you can filter, select and
style by group in the attribute table.

**Five codes on pages 474–501 are deliberately not offered**: the
table's own "Maritime Control Points" parent row (its template column
reads "N/A" — there is no symbol); **Launched Torpedo**, **Acoustic
Countermeasure (Decoy)** and **ECM Decoy**, each marked "(AEGIS only)";
**Position and Intended Movement (PIM) Route**, because the underlying
symbol library maps it to the wrong picture (it draws Point R Route) and
a wrong symbol is worse than none; and **Navigational** (218400), which
is not a point at all but a two-click hooked line — it belongs on a
Lines layer and isn't built yet.

**Deliberately not built**: the whole "(AEGIS only)" family of fixed-
graphic overlay constructs on pages 467–473 (Launch Area, Defended Area,
No Attack Zone, Ship Area of Interest, Active Maneuver Area, Cued
Acquisition Doctrine, Radar Search Doctrine — AEGIS naval combat system
display overlays with specific fixed colours/fills, a genuinely different
display category this plugin doesn't otherwise build toward).

### Deception Control Measures

The smallest section in this whole Appendix H pass — MIL-STD-2525D
Appendix H.5.17 (Table H-XV) has exactly one symbol worth building.

**Lines** offers **Decoy/Dummy**: a 3-point line (drag out two arms from
a shared vertex) drawn as a dashed "tent"/chevron shape, always dashed
regardless of any present/planned distinction — a decoy is inherently a
simulated, not-actually-occupied construct.

Everything else in the table is either already covered elsewhere or
deferred: **Decoy/Dummy and Feint** modifies another, separately-drawn
control measure rather than standing alone, so it isn't built; **Axis
of Advance for a Feint** and **Direction of Attack for a Feint** are the
standard's own cross-references to symbols already on the **Offensive
Control Measures** layer (`axis_of_advance_feint`/
`direction_of_attack_feint`); **Decoy Mined Area** and **Dummy
Minefield** are the standard's own forward-references to the
**Obstacles** layer, where both are built.

### Fire Support Coordination Measures

MIL-STD-2525D Appendix H.5.18 (Table H-XVI) sets a general labelling
rule for every entry here: abbreviation + controlling headquarters +
effective times. This plugin keeps the abbreviation and drops the
controlling-headquarters/effective-times info boxes, the same tolerance
already used for other appendices' own WIDTH/altitude/DTG fields.

**Areas** offers 5 types, each folding the standard's own separate
Irregular/Rectangle/Circular SIDC codes into one dropdown entry (draw
whichever boundary shape you like — the standard's own 3 shape variants
render identically once only the boundary differs): **Airspace
Coordination Area (ACA)**, **Free Fire Area (FFA)**, **No Fire Area
(NFA)** — the one area here with a genuine hatched fill, matching
Airspace Control Measures' own Weapons Free Zone — **Restricted Fire
Area (RFA)**, **Position Area For Artillery (PAA)** (Rectangle/Circle
only, no Irregular variant in the standard's own table).

**No Fire Area's label masks the hatch**, so the text stays readable
against the diagonal fill instead of competing with it.

**Position Area For Artillery labels all four sides.** Rather than one
label in the middle, "PAA" is drawn at the top, bottom, left and right
of the area's perimeter, sitting on the outline with the line breaking
around it — exactly as the standard's own template draws it. This works
for both shapes the standard allows here (rectangle and circle); the
anchors are the midpoints of each side, so a rotated or stretched shape
still gets its four labels on the right axes.

**Lines** offers 6 types. Four repeat their label at both ends —
**Fire Support Coordination Line (FSCL)**, **No Fire Line (NFL)**,
**Battlefield Coordination Line (BCL)**, **Restrictive Fire Line
(RFL)**. Two show a single label instead — **Coordinated Fire Line
(CFL)**, above the centre of its line, and **Munition Flight Path
(MFP)**, on the line at its centre (its own note: "'MFP' shall be
displayed once at the approximate center").

Every one of those labels takes the feature's optional **unique
designation**, and where it goes relative to the abbreviation follows
the standard per type: FSCL puts it **first** ("MND(S) FSCL"), while
NFL, BCL, RFL and CFL put it **last** ("NFL II CORPS", "BCL III MEF",
"CFL 52ID (M)"). MFP has no designation box in the standard and ignores
the field. Leave the field blank and you get the bare abbreviation.

All of these labels **mask the line**, so it breaks cleanly around the
text rather than striking through it, and the both-ends labels sit
above the line and inboard from each end rather than overhanging it.

**CFL is also always drawn dashed**, a fixed property of the code
itself (not a present/planned distinction) — its own template and
example both show it dashed with no solid variant.

### Target Control Measures

MIL-STD-2525D Appendix H.5.19 (Table H-XVII).

**Points** offers this table's own nine entries — **Point/Single
Target**, **Nuclear Target**, **Fire Support Station (FSS)**, and the Fires Points family (**Firing**,
**Hide**, **Launch**, **Reload** and **Survey Control Point**). These
were previously on the shared Control Measure Points layer, since
retired.

Note that the five Fires Points draw *above* where you click — their
anchor is the tip of the cone at the bottom, not the centre.

**Lines** offers 3 types, each with a perpendicular tick at both ends:
**Linear Target**, **Linear Smoke Target** (a fixed "SMOKE" below the
line) and **Final Protective Fire (FPF)** (a fixed "FPF" below the
line). All three take an optional **unique designation**: Linear Target
draws it above the line, and the other two draw it above the line with
their fixed word below, so the pair straddles it. Leave the designation
blank and the fixed word still sits below the line rather than on it.

**Areas** offers 5 types: **Area Target** and **Series or Group of
Targets** (both a bare name with no fixed prefix — for Series or Group
of Targets, place the individual target features it groups as their
own separate point/line/area features; only the boundary + name is
drawn here, and that name sits **on the top of the boundary** with the
line masked around it, as the standard draws it), **Smoke** (a fixed
"SMOKE" label plus an optional name —
present/planned folds onto the usual Status field here, unlike this
appendix's other fixed-dash constructions), **Bomb Area** (a fixed
"BOMB" label, no name), **Fire Support Area (FSA)** (prefix + optional
name).

**Rectangular Target - Single Target (AEGIS Only)** is not built — a
fixed compound diamond+cross icon anchored to one point with a
permanently-upright orientation, the same AEGIS-combat-system-specific
category already excluded throughout Maritime Control Measures.

**No AEGIS-only symbols anywhere.** Throughout Appendix H the standard
marks a handful of entries "(AEGIS only)" — naval combat-system display
constructs rather than general-purpose military symbology. None of them
are offered by this plugin. Two had slipped in and were removed
2026-08-12: **Airfield** (Table H-VI's point, not the Airfield *Zone*
area, which stays) and **Target-Recorded** (Table H-XVII). If you had
already placed either, the feature keeps its attribute value but no
longer appears in the dropdown.

### Obstacle Control Measures

MIL-STD-2525D Appendix H.5.21 (Table H-XIX) — the largest table in the
standard's control-measure appendix, and now complete. It spans **four
layers**: Points, Areas, Minefields and Lines.

**Obstacles draw green**, not in the affiliation colour every other
control measure uses. Each feature has its own **Colour** field so you
can switch any single obstacle to black — a few types are black by
convention in the standard, and the field lets you follow that or your
own unit's practice. The green marks an obstacle specifically, so the
**water crossing sites default to black**: a crossing is the opposite
of an obstacle.

**Points** offers 15 entries: **Antipersonnel Mine** and its
**Directional Effects** variant, **Antitank Mine** and its
**Anti-handling Device** variant, **Wide Area Antitank Mine**,
**Unspecified Mine**, **Booby Trap**, **Engineer Regulating Point**,
the Tetrahedrons/Dragons Teeth family (**Fixed and Prefabricated**,
**Movable**, **Movable and Prefabricated**), **Tower, Low** /
**Tower, High**, and **Trip Wire** / **Abatis** (moved here from
**Lines**, 2026-08-19 — both draw as a fixed page size regardless of
zoom, oriented by the feature's own **Rotation** field, rather than
growing with however long a line got digitized).

Both Towers take a **unique designation** drawn beside the icon.
Engineer Regulating Point takes one too, drawn inside its own symbol.

Every feature on this layer has a **Rotation** (degrees, clockwise from
north) and a **Scale** (%) field, and every one of the 15 entries uses
them — set a heading and size after placing one, same as typing into
any other field on the form.

**Areas** covers the four serrated obstacle zones (**Belt**, **Zone**,
**Free Zone**, **Restricted Zone**), the mined-area family (**Mined
Area**, **Decoy Mined Area** and its **Fenced** variant), **UXO Area**,
and the two freeform dynamic minefields.

**Minefields** holds the box-and-mine-glyph family — **Completed /
Planned**, **Known Enemy**, **Suspected or Templated Enemy** and
**Dummy** — each offering a mine type (antipersonnel, antitank,
unknown, or a combined field that alternates both).

**Lines** is the largest of the four and carries everything else: the
nine wire obstacles, both antitank ditches, the antitank wall, Obstacle
Line and Mine Cluster; the four obstacle effects
(**Block**, **Disrupt**, **Fix**, **Turn**); the three **Obstacle
Bypass** variants, **Bridge or Gap** and the four **Roadblock** states;
and the water crossing sites — **Bridge / Assault Crossing**, **Ford
Easy**, **Ford Difficult**, **Lane / Raft Site**, **Ferry** and
**Overhead Wire**.

Two entries in that list are deliberately one dropdown item covering
two SIDCs, because the standard draws them identically: **Bridge /
Assault Crossing** and **Lane / Raft Site**.

**Overhead Wire** is the one line here that accepts more than two
clicks — it draws a pylon at *every* vertex, so a multi-segment run
gets a tower at each bend.

### Field Fortification Control Measures

MIL-STD-2525D Appendix H.5.22 (Table H-XX) — six entries in two
layers. Affiliation-coloured like most control measures; the green used
for obstacles is that table's own exception and does not apply here.

**Points** offers the four static icons, each centred on a single
click: **Shelter**, **Shelter, Above Ground**, **Shelter, Below
Ground** and **Fort**. These moved here out of the general Control
Measure Points layer, so they are no longer in that dropdown.

**Lines** offers two:

- **Fortified Line** — a crenellated rampart profile. Click as many
  points as you like; the ramparts follow every bend.
- **Fortified Position** — your two clicks are the two *front corners*,
  and a leg of fixed depth trails back from each. Only the distance
  between your two points changes the symbol; its depth never does.

Both lines put their **front on the left of the direction you
digitize** — so click left-to-right along the front with the enemy
above the line. The standard only says the front "typically faces
enemy forces", which two points cannot express on their own, so this
plugin fixes a consistent convention instead.

### CBRN Defense Control Measures

MIL-STD-2525D Appendix H.5.23 (Table H-XXI) — four layers, all 27 rows.

**Points** offers 18: the **Chemical**, **Biological**, **Nuclear** and
**Radiological** event markers, a **Toxic Industrial Material** variant
of the chemical, biological and radiological ones, a **Nuclear Fallout
Producing Event**, and ten decontamination point/site types (general,
alternate, equipment, troops, equipment and troops, operational,
thorough, main equipment, forward troop, and wounded personnel).

On the ten decontamination points the **unique designation** draws in
**Field T1**, inside the lower part of the box, which is where their
templates put it ("1/2COY", "4CBRN" in the standard's own examples).
The eight event markers are a different shape and have only one text
position, beside the triangle.

The four CBRN event markers moved here out of the general Control
Measure Points layer, so they are no longer in that dropdown.

Note that **Nuclear Event** and **Nuclear Fallout Producing Event**
draw the same icon. That is the standard's own doing — it gives them
separate names and codes but no separate symbol.

**Contaminated Areas** offers seven, one for each of **Biological**,
**Chemical**, **Nuclear** and **Radiological**, plus a **Toxic
Industrial Material** variant of all but Nuclear. Digitize the area
with at least three points; QGIS's own polygon tools do the rest.

Each one draws with a **yellow hatched fill** — the standard's own
colour for contamination, not an affiliation colour — an outline in the
usual affiliation colour, solid for present and dashed for planned, and
the matching **B / C / N / R triangle centred inside it**, with a **T**
beneath the letter on the Toxic Industrial Material variants. The
hatching is cut away behind the triangle so the glyph stays readable.

**The triangle sizes itself to the area.** In any area with room for
it, it draws at a steady 12 mm — about the size of a point symbol, so
an area and a point read at the same weight. Only an area too small to
hold that shrinks it, and then only as far as needed to keep 1 mm of
clear space between the glyph and the outline at any zoom.

A long thin or crescent-shaped area will shrink its glyph sooner than
its size suggests: the fit is measured against the largest circle that
fits inside the shape, which is what lets the clearance hold for any
shape you draw.

**Minimum Safe Distance Zones** takes one click for the centre and up
to five **ranges in metres** — nothing else. Each range draws a circle
around the centre at that true ground distance, and writes the range
itself into a break in the circle, level with the centre and to its
right, exactly where the standard puts its own ring numbers. The break
is sized to the text, so "500m" and "12500m" each get the gap they
need. A sixth ring means a second zone placed at the same point.

**Radiation Dose Rate Contours** is a plain polygon per contour. Draw
each contour separately — three dose rates are three features — and put
the number in **Unique designation** (just "300", not "300cGy" — the
"cGy" unit is added automatically); it draws at the top of the shape,
breaking the outline it sits on. This is the one field in the whole
appendix that is *not* forced to upper case, because the standard's own
example writes "30cGy" and the case of "cGy" carries meaning.

### Target Acquisition Control Measures

MIL-STD-2525D Appendix H.5.20 (Table H-XVIII) — 12 area types, all the
same "freeform outline + prefix + optional name" construction: **Artillery
Target Intelligence Zone (ATI)**, **Call For Fire Zone (CFF ZONE)**,
**Censor Zone**, **Critical Friendly Zone (CF ZONE)**, **Dead Space Area
(DA)**, **Sensor Zone**, **Target Build-up Area (TBA)**, **Target Value
Area (TVAR)**, **Zone of Responsibility (ZOR)**, **Terminally Guided
Munition Footprint (TGMF)**, **Blue Kill Box (BKB)**, **Purple Kill Box
(PKB)**. The prefix text matches each one's own
template exactly — the standard itself isn't consistent about spelling
"ZONE" out, so this plugin doesn't force one either.

**Weapon/Sensor Range Fans** comes with the same menu entry, and covers
both of the table's range-fan codes with one symbol — Circular (242100)
is simply Sector (242200) left at its default angles.

Click **one point** for the centre, then fill in up to **five rings**.
Each ring takes a **max left angle**, a **max right angle**, a **range**
and an **Alt**:

- Angles are **compass bearings** — degrees clockwise from north — and
  a ring left at the **0/360** default draws a **full circle**.
- Any other pair draws a **sector** from left to right, with straight
  sides back to the centre. A sector may cross north (300 → 60 is a
  120° sector straddling it).
- **Range is in metres of real ground distance**, so the fan grows and
  shrinks with the map rather than staying a fixed size on the page.
- Each ring's **straight sides span only its own band** — from the
  previous ring's range out to its own — so an outer ring never draws
  through the inner ones. Only the first ring's sides reach the centre.
- A **north axis with a filled arrowhead** runs from the centre through
  every ring and 250 m past the outermost one.
- Each ring is labelled `RG <range>` over `ALT <alt>` on its own
  centreline, between its radius and the ring inside it. Leave Alt blank
  and only the range line is drawn.

Rings you leave blank draw nothing. **Five is the limit** — if you need
more, place a second range fan at the same point.

### Sustainment, Supply and Mission Task Points

Three separate layers, one per table, added 2026-08-14 — the last of
Appendix H's own point vocabularies to get their own homes. They
replace the old flat "Control Measure Points" layer, which was a
holding pen for whichever point types had no table module yet and was
emptied by these three.

- **Sustainment Points** — Table H-XXII's own sixteen: Ambulance
  Exchange Point, Ammunition Supply Point, Ammunition Transfer and
  Holding Point, Cannibalization Point, Casualty Collection Point,
  Civilian Collection Point, Detainee Collection Point, Enemy Prisoner
  of War Collection Point, Logistics Release Point, Maintenance
  Collection Point, MEDEVAC Pick-Up Point, Rearm/Refuel/Resupply Point,
  Refuel on the Move Point, Traffic Control Post, Trailer Transfer
  Point, Unit Maintenance Collection Point.
- **Supply Points** — Table H-XXIII's own eighteen: General Supply
  Point, Medical Supply Point, and the supply classes. Note that the
  classes are **two separate vocabularies** — NATO Class I to V plus
  Multiple Supply Class (each defined by STANAG 2961), and US Class I
  to X. They share roman numerals and mean different things, so every
  entry says which standard it belongs to.
- **Mission Task Points** — Destroy, Interdict and Neutralize. These
  are the only three of Table H-XXIV's 29 rows drawn as a single
  centred glyph on one anchor point. Twenty-four more are arrows,
  brackets and outlined regions built from two to fifty anchor points,
  all of them on the **Mission Task Lines** layer described below. The
  last two rows are group headings the standard draws nothing for.

All three render through the same verified milsymbol library as the
Units layer, not hand-built QGIS symbology, so they are spec-exact
rather than an approximation.

Place points with QGIS's own native **Add Point Feature** tool, then
fill in the attribute form:

- **Affiliation** — Friend/Hostile/Neutral/Unknown. Colour follows
  MIL-STD-2525D's own H.5.3 rule for control measures specifically:
  friendly/neutral/unknown draw in black, hostile draws in red.
- **Entity** — which point control measure this is.
- **Status** — Present or Planned.
- **Unique designation** — drawn in **Field T1**, inside the lower part
  of the box, which is where every template in these two tables puts it
  ("1AD", "3SUST", "MNSE" in the standard's own examples). The ten US
  supply classes are the exception: their icons have no T1 position at
  all, so theirs draws in Field T, outside the box to its upper right.
- **Supply class** — Supply Points only, and drawn only on **NATO
  Multiple Supply Class Point**, whose box otherwise carries no icon of
  its own. Pick one to three classes, or ALL. The list stops at three
  because the template's own A field is three sub-fields wide (A/A1/A2)
  and there is nowhere to put a fourth; a long combination is shrunk to
  fit the box.

There's no "Symbol Set" field on any of them the way the Units layer
has one — these only ever draw from Appendix H's control-measure set,
so there's nothing to choose between.

**Supply Routes (Lines)** comes with the same menu entry — Table
H-XXIII's eight route codes, which are really one construction: **Main**
or **Alternate** Supply Route, each plain or carrying **one-way**,
**two-way** or **alternating** traffic arrows. Digitize along the road
with as many points as you like; the label (`MSR CAMEL`, `ASR 3`) and
the arrows are drawn **once, centred**, and stay upright whichever way
you draw the line.

The standard's own draw rules say that information repeats on *every*
segment between anchor points. That's deliberately not done here — a
route traced along a real road has dozens of short segments, and an
arrow and label on each is unreadable. Same simplification already made
for Boundary and the Fire Support lines.

**Sustainment Areas** comes with the same menu entry — the table's seven
holding and support areas, drawn as a freeform outline with at least
three points and captioned inside.

How each is lettered is the standard's own, and it isn't uniform: the
three support areas use an abbreviation (**RSA**, **BSA**, **DSA**) and
carry no designation at all, while **Detainee Holding Area**, **EPW
Holding Area**, **Refugee Holding Area** and **FARP** spell their name
out and take a **unique designation** on a line beneath it. There is no
"DHA" or "RHA" — those forms appear nowhere in the standard.

**Two things to know.** NATO Multiple Supply Class Point draws the same
plain box as General Supply Point, with no icon of its own — that is the
standard's doing, and the Supply class field above is what tells the two
apart on the map. And **Convoy** — moving or halted — is on the Supply
Routes layer rather than a layer of its own: it is a route with a head
at PT1 and a bar at the far end, so it belongs where the routes are.

**Mission Task Lines** comes with the Mission Tasks menu entry — all
twenty-four of Table H-XXIV's multi-anchor tasks, drawn with QGIS's own **Add Line
Feature** tool. Each carries its own letter, set into a real gap cut in
the shaft or arc it sits on rather than painted over it.

Three of them are clicked exactly like the obstacle effects of the same
name on the Obstacles layer, because they *are* the same construction —
three points, PT1 and PT2 setting the base line and PT3 the depth:

- **Block** — the "T", letter **B** on the crossbar.
- **Disrupt** — three arrows, letter **D** on the middle one. Click PT1
  and PT2 the way round you want the long arrow to fall.
- **Fix** — the wavy shaft, letter **F** on its first straight segment,
  arrowhead at PT1.
- **Penetrate** — Block's shape again, letter **P**, and the arrowhead
  where the stem meets the base rather than at its tip.
- **Clear** — Penetrate with two more arrows, one either side of the
  middle one and the same length, letter **C**. All three heads sit on
  the base line pointing into it, and all three stay square to that
  line however you rotate the symbol.
- **Bypass** — the Obstacles layer's own **Obstacle Bypass Easy**: PT1
  and PT2 are the two arrow *tips*, PT3 sets how deep the symbol runs,
  and letter **B** sits in the middle of the line joining the two
  arrows. Its arrowheads shrink with a small symbol, as that one's do.
- **Breach** and **Canalize** — Bypass with the arrowheads replaced by
  a slanting line across each tip, and letters **B** and **C**.
  Breach's pair closes as it runs outward; Canalize's opens. Which way
  they lean comes from the geometry, so clicking PT1 and PT2 in either
  order draws the same symbol.

**These are not the obstacle effects.** Block, Disrupt and Fix each
appear twice in the standard under different codes and different
drawn forms; the Obstacles layer's versions draw green per H.5.21.1,
these draw black.

Three more are built on a circle — **PT1 the centre, PT2 both the start
point and the radius**, sweeping 330 degrees clockwise and leaving the
standard's own 30-degree opening. They are the same construction as
**Retain** on the Defensive Control Measures layer:

- **Secure** — plain arc, arrowhead where it ends, letter **S** on the
  perimeter half way round.
- **Occupy** — the same, letter **O**, and `><` in place of the
  arrowhead. The cross is a fifth of the radius, capped so it never
  swamps a small symbol.
- **Isolate** — the same again, letter **I**, plus seven triangles
  facing inward off the perimeter. Their base is not drawn — the arc
  itself is the base. They stand 45 degrees apart, starting 30 degrees
  from PT2 and stopping 30 degrees short of the arrowhead, each a third
  of the radius deep.
**Delay**, **Retire**, **Withdraw** and **Withdraw Under Pressure**
are one shape with four letters — **D**, **R**, **W** and **WP** — and
the standard's draw rules for the four are word for word each other's.
Three points: arrowhead at PT1, a straight shaft from PT1 to PT2 with
the letter set into it, then a semicircle carrying on from PT2 round to
PT3.

**The arc always leaves PT2 square to the shaft**, which is the
standard's own rule. So PT3 sets how big the arc is and which side of
the shaft it falls on, but not which way it points — click PT3 at an
angle and only its distance across the shaft counts. The semicircle
always bulges away from PT1. Click PT3 on the shaft's own line and no
arc is drawn at all, since there is no side for it to be on.

**Relief in Place** is that same shape with no letter, so its line
runs unbroken, plus a second arrow parallel to the first and pointing
back the other way — two units passing each other. Its head meets the
far end of the curve, and **RIP** is written in the middle of the
shape. That text grows with the symbol so it fills the shape at any
size, stopping at 24pt.

**Cover**, **Guard** and **Screen** are one shape with three letters —
**C**, **G** and **S**. Click three points: one end, then the **centre**,
then the other end. The centre keeps a gap wide enough for a unit
symbol, which you place yourself if you want one; the letter sits
either side of that gap; and from there a lightning bolt runs out to
each end point, finishing in an arrowhead. The two bolts mirror each
other.

**Security** itself (342200) draws nothing — the standard gives it no
template — so there is no entry for it.

**Follow and Assume** and **Follow and Support** are one shape with
three differences. Two clicks: **PT1 is the tip**, PT2 the rear. Both
draw a tag at the rear, a line, and a head at the tip — Assume's tag is
plain, its line dashed and its head an outlined double chevron;
Support's tag is notched, its line solid and its head a filled
triangle.

Their tag and head are a **fixed size on the page** and only the line
between them stretches, which is the standard's own rule for these two.
Assume's line stays dashed whether the feature is present or planned —
also the standard's rule, and the one place on this layer where a dash
does not mean "planned".

**Counterattack** and **Counterattack by Fire** are the Supply Routes
layer's own **Moving Convoy** arrow, dashed throughout: click three
points, and the arrow runs from PT3 back to an arrowhead at **PT1**,
with **CATK** written along it. By Fire adds a bracket just beyond the
tip with a small solid arrow through it. The dashes stay dashed whether
the feature is present or planned — the standard's own rule, as with
Follow and Assume — and CATK sits just behind the arrowhead, following
the arrow's own direction while staying the right way up however you
draw it.

**Seize** is the odd one out — three points, PT1 carrying a circle, a
curve running PT1-PT2-PT3 that starts on that circle's perimeter rather
than at its centre, an arrowhead at PT3 and letter **S** on the curve.
It is **Turn**'s own curve from the Obstacles layer with the circle
added.

**Table H-XXIV is complete**, and with it the whole of Appendix H. The
two rows the module still lists are the table's own section parent and
its Security group parent, neither of which the standard gives a
template for.

### Intelligence Control Measures

One layer, one symbol: the **Intelligence Coordination Line (ICL)**,
Table H-XXV, the whole of Appendix H.5.27. The table's only other row
names the group and draws nothing.

Draw it with QGIS's own **Add Line Feature** tool — two clicks for a
straight line, or as many as you like to bend it. The line carries
`ICL` plus its own unique designation at **both ends**, above the line
and pushed inward from each end vertex, and the label cuts a real gap
in the line so the text stays readable wherever it lands. The
standard's own example reads "ICL EUSTIS": abbreviation first,
designation last.

It is deliberately the same construction as the **Battlefield
Coordination Line** and **Restrictive Fire Line** on the Fire Support
Coordination Measures layer — same both-ends label, same mask, same
status-driven solid/dashed line, same affiliation colouring. Only the
abbreviation differs.

The effective-times boxes the template draws below the line (Field
W/W1) are not modelled, the same as everywhere else in this appendix.


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
