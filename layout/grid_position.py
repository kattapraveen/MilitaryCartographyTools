# -*- coding: utf-8 -*-

"""
Where a print layout's map sits in the plugin's own existing grid
hierarchy - UTM Grid Zone Designator (GZD, 6deg x 8deg) down to MGRS
100km squares - rather than any separate, invented numbering scheme.
Used by grid_position_diagram.py to draw the inset "where am I"
diagram every layout gets, and by map_sheet_series.py to name each
generated sheet after the real grid square it falls in.

Three tiers, chosen automatically from how much of the hierarchy the
map's own extent actually spans - a small-scale map covering several
GZDs needs a GZD-level picture; a large-scale map that fits inside
one 100km square only needs to show where it sits within that one
square:

1. The extent touches more than one GZD cell - show a mosaic of GZD
   cells (real Grid Zone Designators, e.g. "37M") with the map's own
   footprint outlined across them.
2. The extent fits within a single GZD but touches more than one
   100km square - show a mosaic of 100km square IDs (e.g. "BA")
   within that GZD instead, footprint outlined the same way.
3. The extent fits within a single 100km square - show just that one
   square, with the map's own footprint outlined at its actual
   position inside it.

Military Cartography Tools
"""

import math

from qgis.core import QgsCoordinateTransform, QgsProject, QgsRectangle

from qgis.core import QgsPointXY

from ..core import mgrs_square_id, MGRSConverter
from ..core.coordinate_utils import (
    WGS84,
    get_utm_crs_from_zone_band,
    utm_candidate_zones,
    utm_zone_bounds,
)


# Same latitude-band letter sequence grid/utm_grid.py's
# UTMGridGenerator uses for GZD bands (C-X, skipping I/O, X doubled
# to reach 84N) - duplicated rather than imported to avoid this
# module depending on a grid-layer-generation class for two small
# helper computations.
BAND_LETTERS = "CDEFGHJKLMNPQRSTUVWXX"

ONE_HUNDRED_KM = 100000.0

# How many extra cells of context to show around whatever the map's
# own extent actually touches, in a mosaic tier - so a map touching
# just one or two cells still shows its immediate neighbours, not a
# tight crop with no surrounding context.
CONTEXT_MARGIN_CELLS = 1


def _required_zones(wgs84_extent, band):

    """
    The zone numbers actually covering wgs84_extent in `band`.

    Takes the band because the UTM grid is not a plain 6-degree
    lattice in bands V and X - see core/coordinate_utils.py. Without
    it, a map over south-west Norway at 4E reports zone 31 when it is
    really in the widened 32V, and a map over Svalbard can report a
    zone (32X, 34X, 36X) that does not exist at all.
    """

    covering = []

    for zone in utm_candidate_zones(
        wgs84_extent.xMinimum(),
        wgs84_extent.xMaximum()
    ):

        bounds = utm_zone_bounds(zone, band)

        if bounds is None:
            continue

        west, east = bounds

        if east <= wgs84_extent.xMinimum() or west >= wgs84_extent.xMaximum():
            continue

        covering.append(zone)

    return covering


def _required_band_indices(wgs84_extent):

    ymin = max(-80, wgs84_extent.yMinimum())
    ymax = min(84, wgs84_extent.yMaximum())

    start = int((ymin + 80) / 8)
    end = int((ymax + 80) / 8)

    return list(
        range(
            max(0, start),
            min(len(BAND_LETTERS) - 1, end) + 1
        )
    )


def _zone_lon_bounds(zone, band=None):

    """
    A zone's longitude bounds. With a band, this is the real cell -
    including the V and X exceptions; without one it is the nominal
    6-degree column, which is what the mosaic's own outer extent
    wants since that spans several bands at once.
    """

    if band is not None:

        bounds = utm_zone_bounds(zone, band)

        if bounds is not None:
            return bounds

    west = -180 + ((zone - 1) * 6)

    return west, west + 6


def _band_lat_bounds(band_index):

    south = -80 + (band_index * 8)

    north = 84 if BAND_LETTERS[band_index] == "X" else south + 8

    return south, north


def grid_label_for_point(lat, lon):

    """
    (gzd, hundred_km_id) for a single point - used to name a Map
    Sheet Series sheet after the real grid square its own centre
    falls in, regardless of which tier its own footprint would need
    for the position diagram.
    """

    converter = MGRSConverter()

    mgrs_string = converter.convert(lat, lon)

    gzd = converter.gzd(mgrs_string)

    zone = int(gzd[:-1])
    band = gzd[-1]

    utm_crs = get_utm_crs_from_zone_band(zone, band)

    transform = QgsCoordinateTransform(
        WGS84,
        utm_crs,
        QgsProject.instance()
    )

    point_utm = transform.transform(
        QgsPointXY(lon, lat)
    )

    x_100k = math.floor(point_utm.x() / ONE_HUNDRED_KM) * ONE_HUNDRED_KM
    y_100k = math.floor(point_utm.y() / ONE_HUNDRED_KM) * ONE_HUNDRED_KM

    hundred_km_id = mgrs_square_id(zone, x_100k, y_100k, band) or ""

    return gzd, hundred_km_id


def _footprint_fraction(inner_extent, outer_extent):

    """
    (left, top, right, bottom) fractions describing where
    inner_extent sits within outer_extent, both in the same CRS -
    0 at outer_extent's west/north edge, 1 at its east/south edge.
    Used directly as a 0-1 proportion of the diagram's own drawn
    rectangle, regardless of how many grid cells that rectangle
    happens to represent.
    """

    width = outer_extent.width()
    height = outer_extent.height()

    left = (inner_extent.xMinimum() - outer_extent.xMinimum()) / width
    right = (inner_extent.xMaximum() - outer_extent.xMinimum()) / width

    top = (outer_extent.yMaximum() - inner_extent.yMaximum()) / height
    bottom = (outer_extent.yMaximum() - inner_extent.yMinimum()) / height

    return left, top, right, bottom


def _tier1_gzd_mosaic(wgs84_extent, zones, band_indices):

    zone_span = list(
        range(
            max(1, min(zones) - CONTEXT_MARGIN_CELLS),
            min(60, max(zones) + CONTEXT_MARGIN_CELLS) + 1
        )
    )

    band_span = list(
        range(
            max(0, min(band_indices) - CONTEXT_MARGIN_CELLS),
            min(len(BAND_LETTERS) - 1, max(band_indices) + CONTEXT_MARGIN_CELLS) + 1
        )
    )

    cells = []

    for band_index in band_span:

        row = []

        for zone in zone_span:

            band = BAND_LETTERS[band_index]

            # 32X, 34X and 36X do not exist. Drawing the box but
            # leaving it unlabelled is the honest rendering: that
            # ground is real, it just belongs to the widened zones
            # either side rather than to a cell of its own.
            exists = utm_zone_bounds(zone, band) is not None

            row.append(
                {
                    "label": f"{zone}{band}" if exists else "",
                }
            )

        cells.append(
            row
        )

    # Reversed so row 0 is the northernmost band, matching every
    # other grid-row convention in this plugin.
    cells.reverse()

    mosaic_west, _ = _zone_lon_bounds(zone_span[0])
    mosaic_east, _ = _zone_lon_bounds(zone_span[-1] + 1)

    mosaic_south, _ = _band_lat_bounds(band_span[0])
    _, mosaic_north = _band_lat_bounds(band_span[-1])

    mosaic_extent = QgsRectangle(
        mosaic_west, mosaic_south, mosaic_east, mosaic_north
    )

    return {
        "tier": 1,
        "cells": cells,
        "footprint_fraction": _footprint_fraction(wgs84_extent, mosaic_extent),
    }


def _tier2_hundred_km_mosaic(utm_extent, zone, band, x_indices, y_indices):

    x_span = list(
        range(
            min(x_indices) - CONTEXT_MARGIN_CELLS,
            max(x_indices) + CONTEXT_MARGIN_CELLS + 1
        )
    )

    y_span = list(
        range(
            min(y_indices) - CONTEXT_MARGIN_CELLS,
            max(y_indices) + CONTEXT_MARGIN_CELLS + 1
        )
    )

    cells = []

    for y_index in reversed(y_span):

        row = []

        for x_index in x_span:

            square_id = mgrs_square_id(
                zone,
                x_index * ONE_HUNDRED_KM,
                y_index * ONE_HUNDRED_KM,
                band
            ) or "?"

            row.append(
                {
                    "label": square_id,
                }
            )

        cells.append(
            row
        )

    mosaic_extent = QgsRectangle(
        x_span[0] * ONE_HUNDRED_KM,
        y_span[0] * ONE_HUNDRED_KM,
        (x_span[-1] + 1) * ONE_HUNDRED_KM,
        (y_span[-1] + 1) * ONE_HUNDRED_KM,
    )

    return {
        "tier": 2,
        "cells": cells,
        "footprint_fraction": _footprint_fraction(utm_extent, mosaic_extent),
    }


def _tier3_single_square(utm_extent, zone, band, x_index, y_index):

    square_id = mgrs_square_id(
        zone,
        x_index * ONE_HUNDRED_KM,
        y_index * ONE_HUNDRED_KM,
        band
    ) or "?"

    square_extent = QgsRectangle(
        x_index * ONE_HUNDRED_KM,
        y_index * ONE_HUNDRED_KM,
        (x_index + 1) * ONE_HUNDRED_KM,
        (y_index + 1) * ONE_HUNDRED_KM,
    )

    return {
        "tier": 3,
        "cells": [[{"label": square_id}]],
        "footprint_fraction": _footprint_fraction(utm_extent, square_extent),
    }


def compute_grid_position(map_extent, map_crs):

    """
    Which tier applies to map_extent (given in map_crs), and the
    cell labels/footprint position needed to draw it - see this
    module's own docstring for the three tiers. "cells" is a list of
    rows (row 0 = north) of {"label": str} dicts; "footprint_fraction"
    is (left, top, right, bottom), each 0-1, describing where
    map_extent itself sits within the full drawn mosaic (a single
    cell, for tier 3).
    """

    transform_to_wgs84 = QgsCoordinateTransform(
        map_crs,
        WGS84,
        QgsProject.instance()
    )

    wgs84_extent = transform_to_wgs84.transformBoundingBox(
        map_extent
    )

    # Bands first: which zones cover the extent depends on the band,
    # since 31V/32V and the X-band zones are not 6 degrees wide.
    band_indices = _required_band_indices(wgs84_extent)

    zones = sorted({
        zone
        for band_index in band_indices
        for zone in _required_zones(
            wgs84_extent,
            BAND_LETTERS[band_index]
        )
    })

    if len(zones) * len(band_indices) > 1:

        return _tier1_gzd_mosaic(
            wgs84_extent,
            zones,
            band_indices
        )

    zone = zones[0]
    band = BAND_LETTERS[band_indices[0]]

    utm_crs = get_utm_crs_from_zone_band(
        zone,
        band
    )

    transform_to_utm = QgsCoordinateTransform(
        map_crs,
        utm_crs,
        QgsProject.instance()
    )

    utm_extent = transform_to_utm.transformBoundingBox(
        map_extent
    )

    # Cells are treated as half-open [start, start+100km) - an
    # extent's own max edge landing exactly on a cell boundary
    # belongs to the cell below it, not the next one up. Confirmed
    # live: a plain floor() on the max edge over-counted an
    # exactly-100km-aligned extent as touching one extra column/row
    # it doesn't actually reach into.
    x_indices = list(
        range(
            math.floor(utm_extent.xMinimum() / ONE_HUNDRED_KM),
            math.ceil(utm_extent.xMaximum() / ONE_HUNDRED_KM)
        )
    )

    y_indices = list(
        range(
            math.floor(utm_extent.yMinimum() / ONE_HUNDRED_KM),
            math.ceil(utm_extent.yMaximum() / ONE_HUNDRED_KM)
        )
    )

    if len(x_indices) * len(y_indices) > 1:

        return _tier2_hundred_km_mosaic(
            utm_extent,
            zone,
            band,
            x_indices,
            y_indices
        )

    return _tier3_single_square(
        utm_extent,
        zone,
        band,
        x_indices[0],
        y_indices[0]
    )
