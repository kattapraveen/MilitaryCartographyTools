# -*- coding: utf-8 -*-

"""
Draw the "where am I in the grid" inset diagram every print layout
gets - a small mosaic of the plugin's own existing grid cells (GZD
or MGRS 100km squares - see grid_position.py for which tier applies
and why), inset in the map item's own bottom-left corner (opposite
north_arrow.py's own top-right placement), with the map's actual
footprint outlined on top of the mosaic so it's clear exactly where
the printed sheet sits relative to the standard grid, not just which
cell it's nearest to.

Military Cartography Tools
"""

from qgis.core import QgsFillSymbol, QgsLayoutItem, QgsLayoutItemLabel, QgsLayoutItemShape

from qgis.PyQt.QtCore import QRectF, Qt

from ..core.text_format import build_text_format
from .grid_position import compute_grid_position


CELL_SIZE = 8.0

# How far inside the map item's own bottom-left corner the diagram
# sits - matches north_arrow.py's own ARROW_MARGIN convention for
# the opposite corner.
DIAGRAM_MARGIN = 5.0

FONT_SIZE = 6

CELL_BORDER_COLOR = "31,58,95"  # matches the plugin's own #1f3a5f
CELL_FILL = "255,255,255,230"

# A red distinct from the blue cell grid, so the footprint outline
# reads as "your map is here" at a glance rather than blending into
# the grid itself. Thin (matches the cell grid's own outline weight)
# so it reads as a crisp rectangle at any normal footprint size -
# confirmed live that the original 0.6mm width visually collapsed
# into a solid red blob rather than a legible outline once the
# footprint itself was small relative to the diagram.
FOOTPRINT_COLOR = "215,48,39"
FOOTPRINT_OUTLINE_WIDTH = "0.3"

ITEM_ID_PREFIX = "mct_grid_position"


def _cell_symbol():

    return QgsFillSymbol.createSimple(
        {
            "color": CELL_FILL,
            "outline_color": CELL_BORDER_COLOR,
            "outline_width": "0.3",
        }
    )


def _footprint_symbol():

    return QgsFillSymbol.createSimple(
        {
            "color": "0,0,0,0",
            "outline_color": FOOTPRINT_COLOR,
            "outline_width": FOOTPRINT_OUTLINE_WIDTH,
        }
    )


def remove_grid_position_diagram(layout):

    """
    Remove this layout's grid position diagram, if present.
    """

    for item in list(layout.items()):

        # layout.items() returns every graphics item in the layout's
        # scene, including plain QGraphicsRectItem page-background
        # items with no id() at all - confirmed live (AttributeError)
        # rather than assumed, so only QgsLayoutItem instances (which
        # this plugin's own items always are) are considered here.
        if not isinstance(item, QgsLayoutItem):
            continue

        item_id = item.id()

        if item_id and item_id.startswith(ITEM_ID_PREFIX):
            layout.removeLayoutItem(item)


def add_grid_position_diagram(layout, map_item):

    """
    Add the grid position diagram, inset in map_item's own bottom-
    left corner, sized to whatever grid computed by
    grid_position.compute_grid_position() for map_item's own current
    extent/CRS - a single cell for tier 3, a small mosaic for tiers
    1-2. Replaces any diagram already on the layout.
    """

    remove_grid_position_diagram(
        layout
    )

    position_info = compute_grid_position(
        map_item.extent(),
        map_item.crs()
    )

    cells = position_info["cells"]

    rows = len(cells)
    cols = len(cells[0])

    total_width = cols * CELL_SIZE
    total_height = rows * CELL_SIZE

    map_position = map_item.positionWithUnits()
    map_size = map_item.sizeWithUnits()

    origin_x = map_position.x() + DIAGRAM_MARGIN

    origin_y = (
        map_position.y()
        + map_size.height()
        - DIAGRAM_MARGIN
        - total_height
    )

    for row in range(rows):

        for col in range(cols):

            cell_rect = QRectF(
                origin_x + (col * CELL_SIZE),
                origin_y + (row * CELL_SIZE),
                CELL_SIZE,
                CELL_SIZE
            )

            background = QgsLayoutItemShape(layout)

            background.setId(
                f"{ITEM_ID_PREFIX}_cell_bg_{row}_{col}"
            )

            background.setShapeType(
                QgsLayoutItemShape.Shape.Rectangle
            )

            background.setSymbol(
                _cell_symbol()
            )

            layout.addLayoutItem(
                background
            )

            background.attemptSetSceneRect(
                cell_rect
            )

            label = QgsLayoutItemLabel(layout)

            label.setId(
                f"{ITEM_ID_PREFIX}_cell_label_{row}_{col}"
            )

            label.setText(
                cells[row][col]["label"]
            )

            label.setTextFormat(
                build_text_format(FONT_SIZE)
            )

            label.setHAlign(
                Qt.AlignmentFlag.AlignHCenter
            )

            label.setVAlign(
                Qt.AlignmentFlag.AlignVCenter
            )

            layout.addLayoutItem(
                label
            )

            label.attemptSetSceneRect(
                cell_rect
            )

    left, top, right, bottom = position_info["footprint_fraction"]

    footprint = QgsLayoutItemShape(layout)

    footprint.setId(
        f"{ITEM_ID_PREFIX}_footprint"
    )

    footprint.setShapeType(
        QgsLayoutItemShape.Shape.Rectangle
    )

    footprint.setSymbol(
        _footprint_symbol()
    )

    layout.addLayoutItem(
        footprint
    )

    footprint.attemptSetSceneRect(
        QRectF(
            origin_x + (left * total_width),
            origin_y + (top * total_height),
            (right - left) * total_width,
            (bottom - top) * total_height
        )
    )

    return footprint
