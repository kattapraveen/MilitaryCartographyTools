# Military Cartography Tools

A QGIS plugin for military mapping: MIL-STD-2525D/E and APP-6D/E tactical graphics,
MGRS coordinate conversion, military grid generation, terrain analysis, and
automated print-layout production. Runs fully offline — no external services,
no data leaves your machine.

Requires QGIS 3.44 or later.

> **Fully offline.** Every tool runs entirely against local data - GDAL/QGIS
> Processing, a bundled World Magnetic Model, and your own DEM - with no
> external services, API calls, or telemetry of any kind. Nothing you map
> ever leaves your machine, which makes this plugin suitable for sensitive
> or classified work.

> **Status: stable, and feature-complete for now.** Active development
> is largely finished — the plugin does what it set out to do, and from
> here it's maintained rather than extended. Fixes and improvements will
> be driven by what users actually report, so bug reports, suggestions
> and feedback are very welcome: please
> [open an issue](https://github.com/kattapraveen/MilitaryCartographyTools/issues).

## Features

- **MGRS conversion** — lat/lon ↔ MGRS, both directions, plus expression
  functions for grabbing individual components (zone, 100km square,
  easting, northing) or a print layout's own map centre live.
- **Coordinate Probe** — click the map canvas to read off lat/lon and
  full-precision MGRS for any point, logged in a running window, with the
  MGRS coordinate copied to the clipboard automatically.
- **Military grids** — UTM Grid Zone Designators, MGRS 100km squares, and
  10km/5km/1km tactical sub-grids, generated for the current map extent.
- **New Military Layout** — a single dialog creates a fully-configured
  print layout: north arrow (auto-rotating to true north), scale bar,
  metadata block, center-of-map coordinate, neatline, geographic
  graticule, optional heading and security classification banners — then
  lets you revisit any of those settings later on the same layout instead
  of starting over.
- **Print-layout grid frame** — border tick marks and coordinate
  annotations around a layout's map, the standard topographic-map
  convention.
- **Insert Symbol** — place a MIL-STD-2525/APP-6 symbol directly onto a
  print layout page, for a legend key or callout rather than a
  georeferenced map feature.
- **Grid convergence and magnetic declination** (WMM2025) as expression
  functions, usable anywhere in QGIS or wired into a layout's own
  marginalia.
- **Terrain analysis** — Tanaka (illuminated) contours, Hypsometric Tint,
  Combined (multi-directional) Hillshade, Line of Sight, and Viewshed
  (dead-ground analysis), all generated locally from your own DEM.
- **Sensor Coverage** — plot several sensors at low, medium or high
  level, each with its own height, detection ceiling, range, MIL-STD-2525
  affiliation and designation. Each level's combined coverage is drawn as
  a single perimeter, merging overlapping footprints on the same side
  only, with every sensor labelled along its own stretch of the outline.
  Updates itself as sensors are moved, added or removed.

See the **[User Guide](docs/user-guide.md)** for full usage details,
including every expression function's exact signature.

## Installation

1. Copy the `MilitaryCartographyTools` folder into your QGIS plugins
   directory (`Settings → User Profiles → Open Active Profile Folder →
   python/plugins`).
2. In QGIS, open **Plugins → Manage and Install Plugins → Installed**, and
   tick **Military Cartography Tools**.

## Documentation

- [User Guide](docs/user-guide.md) — how to use every tool and expression
  function.
- [Developer Guide](docs/developer-guide.md) — running the test suite, and
  PyQGIS/QGIS 4.x API gotchas found while building this plugin.
- [Roadmap](docs/roadmap.md) — phase-by-phase project status.

## License

GNU General Public License v2 or later — see [LICENSE](LICENSE).

---

## Acknowledgements

### MGRS Conversion Engine

Military Cartography Tools incorporates the MGRS conversion engine
originally developed by Alex Bruy for Boundless and later maintained
by Planet Federal / Planet Inc.

The MGRS engine is distributed under the GNU General Public License
(GPL v2 or later).

The remaining plugin code—including the QGIS integration, expression
functions, layout tools, user interface, grid management system, and
additional functionality—is original work developed for Military
Cartography Tools.


### MGRS Grid Generation Workflow

The MGRS grid generation workflow was inspired by QGIS Processing
models originally developed by:

Klas Karlsson

Published through the QGIS Model Repository:
https://hub.qgis.org/models/4/

License:
Creative Commons Zero (CC0)

The workflow was used as a reference for:
- Global MGRS GZD generation
- 100 km MGRS grid construction
- Handling of special UTM zones

The implementation within Military Cartography Tools has been
re-designed and integrated as a native QGIS plugin workflow.

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for full attribution,
including the vendored World Magnetic Model code (pyGeoMag, MIT license).
