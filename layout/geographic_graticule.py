# -*- coding: utf-8 -*-

"""
Add a lightweight geographic (latitude/longitude) graticule
overlay to a print layout's map item - light brown lines with
small italic degree-minute labels, auto-spaced (15'/30'/1 degree
based on the map's own extent), distinct from the plugin's own
bold black UTM/MGRS grid.

Uses a second QgsLayoutItemMapGrid (CRS EPSG:4326) added to the
same map item's grid stack - QGIS's own built-in DegreeMinute
annotation format handles the degree-minute-suffix text natively,
unlike the UTM grid frame's custom expression (which was only
needed there for the MGRS-specific 100km prefix convention).

Military Cartography Tools
"""

from qgis.core import (
    QgsLayoutItemMapGrid,
    QgsCoordinateTransform,
    QgsProject
)

from qgis.PyQt.QtGui import QColor

from ..core.coordinate_utils import WGS84
from ..core.text_format import build_text_format


NAME = "Geographic Graticule"

GRID_LINE_COLOR = QColor(181, 136, 66)

GRID_LINE_WIDTH_MM = 0.15

FONT_SIZE = 8

# 15', 30', 1 degree, smallest first.
INTERVALS_DEGREES = [0.25, 0.5, 1.0]

TARGET_TICKS_PER_SIDE = 6


def _extent_in_wgs84(map_item):

    transform = QgsCoordinateTransform(
        map_item.crs(),
        WGS84,
        QgsProject.instance()
    )

    return transform.transformBoundingBox(
        map_item.extent()
    )


def _auto_interval(extent_deg):

    """
    Smallest of 15'/30'/1 degree that keeps roughly
    TARGET_TICKS_PER_SIDE or fewer ticks along the map's longer
    side, based on the map's actual geographic extent.
    """

    span = max(
        extent_deg.width(),
        extent_deg.height()
    )

    for interval in INTERVALS_DEGREES:

        if span / interval <= TARGET_TICKS_PER_SIDE:

            return interval

    return INTERVALS_DEGREES[-1]


def _text_format():

    return build_text_format(
        FONT_SIZE,
        italic=True,
        color=GRID_LINE_COLOR
    )


def remove_geographic_graticule(map_item):

    """
    Remove this plugin's geographic graticule from a map item, if
    present.
    """

    stack = map_item.grids()

    for existing in stack.asList():

        if existing.name() == NAME:

            stack.removeGrid(
                existing.id()
            )

    map_item.invalidateCache()


def add_geographic_graticule(map_item):

    """
    Add (replacing any existing one) a light brown lat/lon
    graticule to map_item, spaced automatically from its current
    extent, with small italic degree-minute labels just inside
    the map's own frame.
    """

    extent_deg = _extent_in_wgs84(
        map_item
    )

    interval = _auto_interval(
        extent_deg
    )

    remove_geographic_graticule(
        map_item
    )

    grid = QgsLayoutItemMapGrid(
        NAME,
        map_item
    )

    grid.setCrs(
        WGS84
    )

    grid.setIntervalX(
        interval
    )

    grid.setIntervalY(
        interval
    )

    grid.setStyle(
        QgsLayoutItemMapGrid.GridStyle.Solid
    )

    grid.setGridLineColor(
        GRID_LINE_COLOR
    )

    grid.setGridLineWidth(
        GRID_LINE_WIDTH_MM
    )

    grid.setFrameStyle(
        QgsLayoutItemMapGrid.FrameStyle.NoFrame
    )

    grid.setAnnotationEnabled(
        True
    )

    grid.setAnnotationFormat(
        QgsLayoutItemMapGrid.AnnotationFormat.DegreeMinute
    )

    # Whole minutes only - confirmed live that the default
    # precision showed 3 decimal places on the minutes value
    # (e.g. "38°30,000'E"), and with a comma as this build's
    # locale decimal separator rather than a period, which read
    # as an entirely different (and wrong) number.
    grid.setAnnotationPrecision(
        0
    )

    grid.setAnnotationTextFormat(
        _text_format()
    )

    for side in (
        QgsLayoutItemMapGrid.BorderSide.Left,
        QgsLayoutItemMapGrid.BorderSide.Right,
        QgsLayoutItemMapGrid.BorderSide.Top,
        QgsLayoutItemMapGrid.BorderSide.Bottom,
    ):

        grid.setAnnotationPosition(
            QgsLayoutItemMapGrid.AnnotationPosition.InsideMapFrame,
            side
        )

        grid.setAnnotationDirection(
            QgsLayoutItemMapGrid.AnnotationDirection.Horizontal,
            side
        )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.DisplayMode.LongitudeOnly,
        QgsLayoutItemMapGrid.BorderSide.Top
    )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.DisplayMode.LongitudeOnly,
        QgsLayoutItemMapGrid.BorderSide.Bottom
    )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.DisplayMode.LatitudeOnly,
        QgsLayoutItemMapGrid.BorderSide.Left
    )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.DisplayMode.LatitudeOnly,
        QgsLayoutItemMapGrid.BorderSide.Right
    )

    map_item.grids().addGrid(
        grid
    )

    map_item.invalidateCache()

    return grid
