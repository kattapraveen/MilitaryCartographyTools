# Military Cartography Tools — User Guide

A QGIS plugin for military mapping and MGRS work: coordinate conversion,
military grid generation, and automated print-layout production.

---

## Contents

- [Installation](#installation)
- [The toolbar, at a glance](#the-toolbar-at-a-glance)
- [Coordinate Probe](#coordinate-probe)
- [Military grids](#military-grids)
- [New Military Layout](#new-military-layout)
- [Military Layout Settings panel](#military-layout-settings-panel)
- [Print-layout grid frame](#print-layout-grid-frame)
- [Tanaka Contours](#tanaka-contours)
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

Left to right:

| Icon | Action |
|---|---|
| Grid with a highlighted square + crosshair | About / plugin info |
| Coarse 3×2 grid | Toggle the UTM Grid Zone Designator grid |
| Fine grid with a highlighted square | Toggle the MGRS 100km square grid |
| Fine grid + crosshair, with a dropdown | Sub Grid spacing (Off / 10km / 5km / 1km) |
| Grid with a red X | Clear Grid — remove every grid layer |
| Crosshair reticle | Coordinate Probe |
| Page with a heading bar and a small map | New Military Layout |
| Illuminated concentric rings | Tanaka Contours |

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
lines whose width and color vary by local terrain illumination, giving a
sense of relief without needing a hillshade raster underneath. Requires a
DEM (elevation raster) layer already loaded in your project; this plugin
doesn't fetch or download one for you (see "Getting a DEM" below).

The dialog asks for:

| Field | Notes |
|---|---|
| DEM layer | Any loaded raster layer |
| Contour interval | Vertical spacing between contour lines, in metres |
| Segment length | How finely each contour is subdivided for illumination to vary smoothly along it, in metres — smaller values give a smoother gradient at the cost of more features |
| Light azimuth | Direction the virtual light comes from, in degrees (0 = north). Defaults to 315° (north-west), matching QGIS's own hillshade default |
| Min/max line width | Line width at fully-lit and fully-shadowed, in mm |
| Lit color / Shadow color | Colors blended between based on each segment's illumination |

Contours are generated for the **current map canvas extent** only (not the
whole DEM), clipped and reprojected to the appropriate local UTM zone
automatically — pan/zoom to the area you want first. On a large DEM, keep
the extent reasonably small (a few kilometres across) for fast generation.

### Getting a DEM

This plugin doesn't include a DEM downloader — that's a generic GIS task
already well covered elsewhere. If you don't already have elevation data
for your area, options include QGIS's own **Data Source Manager** (WCS
connections), or a dedicated plugin such as **SRTM Downloader** (via
**Plugins → Manage and Install Plugins**).

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

Every function returns a short error string (e.g. `"Layout not found"`,
`"Need latitude, longitude"`) instead of failing silently if its arguments
don't resolve.
