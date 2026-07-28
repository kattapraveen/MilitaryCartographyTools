# -*- coding: utf-8 -*-

"""
Add a security classification banner (e.g. "RESTRICTED") at both
the top and bottom of a print layout's page, bold and all caps -
mirrors the reference layout's own classification markings.

Military Cartography Tools
"""

from qgis.core import QgsLayoutItemLabel

from qgis.PyQt.QtCore import QRectF, Qt

from ..core.text_format import build_text_format


# Offered in the New Military Layout dialog's classification
# combo - "None" means no banner at all.
LEVELS = [
    "None",
    "UNCLASSIFIED",
    "RESTRICTED",
    "CONFIDENTIAL",
    "SECRET",
    "TOP SECRET",
]

FONT_SIZE = 12

LINE_HEIGHT = 5.0

# Fixed item ids (one per banner position) so a later call can
# find and replace these labels in place instead of stacking
# duplicates - see remove_classification_banners().
TOP_ITEM_ID = "mct_classification_top"
BOTTOM_ITEM_ID = "mct_classification_bottom"


def required_height(level):

    """
    Vertical space the banner needs - 0 if there's no
    classification selected (level is None or "None"). Used by
    new_layout.py to size the top/bottom margins before anything
    is placed.
    """

    if not level or level == "None":
        return 0

    return LINE_HEIGHT


def remove_classification_banners(layout):

    """
    Remove both classification banners from layout, if present.
    """

    for item_id in (TOP_ITEM_ID, BOTTOM_ITEM_ID):

        item = layout.itemById(item_id)

        if item is not None:
            layout.removeLayoutItem(item)


def existing_classification(layout):

    """
    The classification level currently shown on layout - "None"
    if there isn't one. Used to pre-fill the Layout Settings panel
    from a layout that's already open.
    """

    item = layout.itemById(TOP_ITEM_ID)

    if item is None:
        return "None"

    return item.text()


def add_classification_banner(layout, page_width, level, top_y, item_id):

    """
    Add a classification banner, centred horizontally, starting
    at top_y, tagged with item_id (TOP_ITEM_ID or BOTTOM_ITEM_ID)
    so it can be found and replaced later. No-op (returns None) if
    level is None or "None".
    """

    if not level or level == "None":
        return None

    label = QgsLayoutItemLabel(layout)

    label.setId(
        item_id
    )

    label.setText(
        level.upper()
    )

    label.setTextFormat(
        build_text_format(FONT_SIZE, bold=True)
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
            LINE_HEIGHT
        )
    )

    return label
