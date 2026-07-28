# -*- coding: utf-8 -*-

"""
Add a bottom-left metadata block to a print layout: geodetic
datum, projection, coordinate units, map scale, project file, and
page size - mirrors the reference layout's own bottom-left
marginalia block. The map centre coordinate is its own separate,
independently-positioned label (see layout/center_coordinate.py).

Placed in the same shared bottom margin band as the scale bar and
the centre-coordinate label (see layout/scale_bar.py,
layout/center_coordinate.py, and new_layout.py's create_layout()),
bottom-aligned to the same bottom_y so all three line up.

Military Cartography Tools
"""

from qgis.core import QgsLayoutItemLabel

from qgis.PyQt.QtCore import QRectF, Qt

from ..core.text_format import build_text_format
from .scale_bar import scale_text_expression


FONT_SIZE = 8

# Per-line height - generous enough for FONT_SIZE at typical line
# spacing without needing an exact font-metrics measurement.
LINE_HEIGHT = 3.6

NUM_LINES = 6

# Left inset from the page edge - matches the map item's own side
# margin (new_layout.py's MAP_SIDE_MARGIN) for visual alignment,
# but defined independently here to avoid a circular import
# between the two modules.
LEFT_MARGIN = 10.0

BLOCK_WIDTH = 120.0

# Fixed item id so a later call can find and replace this label
# in place instead of stacking duplicates.
ITEM_ID = "mct_metadata_block"


def remove_metadata_block(layout):

    """
    Remove this layout's metadata block, if present.
    """

    item = layout.itemById(ITEM_ID)

    if item is not None:
        layout.removeLayoutItem(item)


def required_height():

    """
    Total vertical space this block needs - used by
    new_layout.py to size the shared bottom margin band before
    anything is placed.
    """

    return LINE_HEIGHT * NUM_LINES


def _metadata_text(width_mm, height_mm):

    """
    The block's text, one line per fact. Everything derivable
    live is an embedded [% %] expression (so it stays correct if
    the map is later panned/rescaled/reprojected in the Designer)
    - only the page size is baked in as static text, since it's
    known for certain at creation time and there's no reliable
    layout-level expression variable for a page's own dimensions.
    """

    lines = [
        "Geodetic datum: WGS-84",
        (
            "Projection: UTM zone GZD [% mct_mgrs_zone("
            "mct_map_center_lat(@layout_name), "
            "mct_map_center_lon(@layout_name)"
            ") %]"
        ),
        "Coordinate Units: Meters",
        f"Map Scale: [% {scale_text_expression()} %]",
        "Project File: [% @project_basename %]",
        f"Page Size: {width_mm:.0f} x {height_mm:.0f} mm",
    ]

    return "\n".join(lines)


def add_metadata_block(layout, width_mm, height_mm, bottom_y):

    """
    Add the metadata block, bottom-left, with its last line's
    bottom edge at bottom_y (shared with the scale bar group).
    Replaces any metadata block already on the layout.
    """

    remove_metadata_block(
        layout
    )

    label = QgsLayoutItemLabel(layout)

    label.setId(
        ITEM_ID
    )

    label.setText(
        _metadata_text(width_mm, height_mm)
    )

    label.setTextFormat(
        build_text_format(FONT_SIZE)
    )

    label.setHAlign(
        Qt.AlignmentFlag.AlignLeft
    )

    label.setVAlign(
        Qt.AlignmentFlag.AlignBottom
    )

    layout.addLayoutItem(
        label
    )

    block_height = required_height()

    label.attemptSetSceneRect(
        QRectF(
            LEFT_MARGIN,
            bottom_y - block_height,
            BLOCK_WIDTH,
            block_height
        )
    )

    return label
