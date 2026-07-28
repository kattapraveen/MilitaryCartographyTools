# -*- coding: utf-8 -*-

"""
Add a one- or two-line heading, centred at the top of a print
layout's page - the text itself comes from the user (entered in
the New Military Layout dialog), not derived live like the other
marginalia elements.

Military Cartography Tools
"""

from qgis.core import QgsLayoutItemLabel

from qgis.PyQt.QtCore import QRectF, Qt

from ..core.text_format import build_text_format


FONT_SIZE = 22

LINE_HEIGHT = 10.0

# Fixed item id so a later call can find and replace this label
# in place (e.g. from the in-designer Layout Settings panel)
# instead of stacking duplicates on top of each other.
ITEM_ID = "mct_heading"


def required_height(num_lines):

    """
    Vertical space a heading of num_lines lines needs (0 if
    there's no heading at all) - used by new_layout.py to size
    the map's own top margin before anything is placed.
    """

    return LINE_HEIGHT * num_lines


def remove_heading(layout):

    """
    Remove this layout's heading label, if present.
    """

    item = layout.itemById(ITEM_ID)

    if item is not None:
        layout.removeLayoutItem(item)


def existing_heading_lines(layout):

    """
    The heading text currently on layout, as a list of lines - []
    if there's no heading. Used to pre-fill the Layout Settings
    panel from a layout that's already open.
    """

    item = layout.itemById(ITEM_ID)

    if item is None:
        return []

    return item.text().split("\n")


def add_heading(layout, page_width, heading_lines, top_y):

    """
    Add the heading label, centred horizontally, starting at
    top_y. heading_lines is a list of 1-2 strings. Replaces any
    heading already on the layout.
    """

    remove_heading(
        layout
    )

    label = QgsLayoutItemLabel(layout)

    label.setId(
        ITEM_ID
    )

    # Always shown upper-case, regardless of the case the user
    # actually typed it in as (matches classification.py's own
    # banners, which do the same).
    label.setText(
        "\n".join(line.upper() for line in heading_lines)
    )

    label.setTextFormat(
        build_text_format(FONT_SIZE, bold=True, underline=True)
    )

    label.setHAlign(
        Qt.AlignmentFlag.AlignHCenter
    )

    label.setVAlign(
        Qt.AlignmentFlag.AlignTop
    )

    layout.addLayoutItem(
        label
    )

    label.attemptSetSceneRect(
        QRectF(
            0,
            top_y,
            page_width,
            required_height(len(heading_lines))
        )
    )

    return label
