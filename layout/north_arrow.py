# -*- coding: utf-8 -*-

"""
Add a north arrow to a print layout, positioned inside the map
item's own rectangle (top-right corner) and linked to that map
item so its rotation stays in sync with true north (relative to
grid north - i.e. the grid convergence angle) as the map's
extent, rotation, or CRS changes.

Military Cartography Tools
"""

from pathlib import Path

from qgis.core import QgsLayoutItemPicture

from qgis.PyQt.QtCore import QRectF


# This plugin's own north arrow design (shaft + arrowhead, bold
# "N" to the right, bottom-aligned) - confirmed with the user
# over several rounds of adjustment, rather than QGIS's built-in
# north arrow SVG.
DEFAULT_ARROW_SVG = str(
    Path(__file__).parent.parent / "icons" / "north_arrow.svg"
)

# Size of the arrow on the page, in millimetres.
ARROW_SIZE = 12.0

# How far the arrow sits inside the map item's own top-right
# corner, in millimetres - keeps it clear of the map frame/border
# rather than flush against it.
ARROW_MARGIN = 5.0

# Fixed item id so a later call can find and replace this picture
# in place (e.g. after the map item's rect changes size) instead
# of stacking duplicates.
ITEM_ID = "mct_north_arrow"


def remove_north_arrow(layout):

    """
    Remove this layout's north arrow, if present.
    """

    item = layout.itemById(ITEM_ID)

    if item is not None:
        layout.removeLayoutItem(item)


def add_north_arrow(layout, map_item):

    """
    Add a north arrow picture item to the layout, positioned
    inside map_item's own rectangle near its top-right corner,
    and linked to it via QgsLayoutItemPicture's native
    NorthMode.TrueNorth so the arrow's rotation automatically
    tracks true north (map rotation + grid convergence, computed
    by QGIS itself) rather than needing our own convergence math
    wired up by hand. Replaces any north arrow already on the
    layout (e.g. to reposition it after the map item is resized).
    """

    remove_north_arrow(
        layout
    )

    arrow = QgsLayoutItemPicture(layout)

    arrow.setId(
        ITEM_ID
    )

    arrow.setPicturePath(
        DEFAULT_ARROW_SVG
    )

    position = map_item.positionWithUnits()

    size = map_item.sizeWithUnits()

    arrow_x = (
        position.x()
        + size.width()
        - ARROW_MARGIN
        - ARROW_SIZE
    )

    arrow_y = position.y() + ARROW_MARGIN

    arrow.attemptSetSceneRect(
        QRectF(
            arrow_x,
            arrow_y,
            ARROW_SIZE,
            ARROW_SIZE
        )
    )

    layout.addLayoutItem(
        arrow
    )

    arrow.setLinkedMap(
        map_item
    )

    arrow.setNorthMode(
        QgsLayoutItemPicture.NorthMode.TrueNorth
    )

    arrow.refreshItemRotation()

    return arrow
