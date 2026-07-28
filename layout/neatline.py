# -*- coding: utf-8 -*-

"""
Add a neatline (a thin border) directly around a print layout's
map item - hugs the map canvas itself, not the page. Anything
placed outside the map item (e.g. a grid frame's own ticks and
annotations, if the user separately enables it) is expected to
sit outside this line, in the page margin.

Uses the map item's own built-in frame rather than a separate
overlaid rectangle item, so it always exactly matches the map
item's current rectangle even if that's resized later.

Military Cartography Tools
"""

from qgis.core import QgsLayoutMeasurement, QgsUnitTypes
from qgis.PyQt.QtGui import QColor


NEATLINE_WIDTH_MM = 0.3
NEATLINE_COLOR = QColor(0, 0, 0)


def add_neatline(map_item):

    """
    Enable a thin black border on map_item's own frame.
    """

    map_item.setFrameEnabled(
        True
    )

    map_item.setFrameStrokeColor(
        NEATLINE_COLOR
    )

    map_item.setFrameStrokeWidth(
        QgsLayoutMeasurement(
            NEATLINE_WIDTH_MM,
            QgsUnitTypes.LayoutMillimeters
        )
    )
