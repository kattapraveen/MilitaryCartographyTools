# -*- coding: utf-8 -*-

"""
Add an independent "Center of Map: <MGRS>" label to a print
layout, bottom-right - kept separate from the metadata block
(layout/metadata_block.py) at the user's request, rather than
being one of its stacked lines.

Placed in the same shared bottom margin band as the scale bar and
metadata block (see new_layout.py's create_layout()), bottom-
aligned to the same bottom_y so all three line up.

Military Cartography Tools
"""

from qgis.core import QgsLayoutItemLabel

from qgis.PyQt.QtCore import QRectF, Qt

from ..core.text_format import build_text_format


FONT_SIZE = 9

LINE_HEIGHT = 4.0

# Right inset from the page edge - matches the metadata block's
# own LEFT_MARGIN convention for a symmetric look, but defined
# independently to avoid a circular import between the two
# modules.
RIGHT_MARGIN = 10.0

BLOCK_WIDTH = 120.0

# Fixed item id so a later call can find and replace this label
# in place instead of stacking duplicates.
ITEM_ID = "mct_center_coordinate"


def remove_center_coordinate_label(layout):

    """
    Remove this layout's centre-coordinate label, if present.
    """

    item = layout.itemById(ITEM_ID)

    if item is not None:
        layout.removeLayoutItem(item)


def required_height():

    """
    Vertical space this label needs - used by new_layout.py to
    size the shared bottom margin band before anything is placed.
    """

    return LINE_HEIGHT


def add_center_coordinate_label(layout, page_width, bottom_y):

    """
    Add the "Center of Map: <MGRS>" label, bottom-right, with its
    bottom edge at bottom_y (shared with the scale bar and
    metadata block). Replaces any centre-coordinate label already
    on the layout.
    """

    remove_center_coordinate_label(
        layout
    )

    label = QgsLayoutItemLabel(layout)

    label.setId(
        ITEM_ID
    )

    label.setText(
        "Center of Map: [% mct_map_center_mgrs(@layout_name) %]"
    )

    label.setTextFormat(
        build_text_format(FONT_SIZE)
    )

    label.setHAlign(
        Qt.AlignmentFlag.AlignRight
    )

    label.setVAlign(
        Qt.AlignmentFlag.AlignBottom
    )

    layout.addLayoutItem(
        label
    )

    label.attemptSetSceneRect(
        QRectF(
            page_width - RIGHT_MARGIN - BLOCK_WIDTH,
            bottom_y - LINE_HEIGHT,
            BLOCK_WIDTH,
            LINE_HEIGHT
        )
    )

    return label
