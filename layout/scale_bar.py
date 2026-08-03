# -*- coding: utf-8 -*-

"""
Add a scale bar to a print layout, with its own "kilometers" unit
label (italic) and a "Scale 1:N" text beneath it, stacked and
centred horizontally on the page.

The whole group is bottom-aligned to a shared bottom_y the caller
provides (new_layout.py's create_layout(), which reserves a bottom
margin band shared with the metadata block placed alongside it -
see layout/metadata_block.py) rather than computed from the map
item's own edge, so both pieces line up on the same baseline.

Military Cartography Tools
"""

from qgis.core import (
    QgsLayoutItemScaleBar,
    QgsLayoutItemLabel,
    QgsUnitTypes,
    Qgis
)

from qgis.PyQt.QtCore import QRectF, Qt

from ..core.text_format import build_text_format


# QGIS's own built-in scale bar renderer names (see
# QgsApplication.scaleBarRendererRegistry()) - ticks only above
# the line (not crossing through both sides), per request.
SCALE_BAR_STYLE = "Line Ticks Up"

# Reduced 60% from the original 4.0mm per request - also shrinks
# required_height(), freeing up more room for the map above it.
BAR_HEIGHT = 1.6

NUM_SEGMENTS = 4

# "Nice" round km-per-segment values to choose from - see
# _pick_units_per_segment(). QGIS's own FitWidth segment-size
# mode was tried first (the same auto-sizing its GUI "Add Scale
# Bar" action uses) but its rounding was confirmed live to
# overshoot the requested maximum bar width rather than respect
# it, whenever the next-smaller nice value would have undershot
# the minimum - so this picks the segment size directly instead.
#
# The 0.01-0.05 decade was added after a real bug report: at very
# close-in scales (confirmed live at 1:1,000 and 1:2,000), the
# previous smallest value (0.1) was already too coarse, so the
# picked bar came out wider than the page itself (400mm on a
# 297mm-wide page at 1:1,000) - centering math then went negative
# and the bar visibly overlapped the metadata block. This still
# doesn't guarantee the bar can never exceed a given page (an even
# tighter scale or a narrow custom page could still do it), but
# covers every case actually observed.
NICE_SEGMENT_KM = [
    0.01, 0.02, 0.025, 0.05,
    0.1, 0.2, 0.25, 0.5,
    1, 2, 2.5, 5,
    10, 20, 25, 50,
    100, 200, 250, 500,
    1000, 2000, 2500, 5000,
]

# Target on-page width for the bar - kept well clear of typical
# page widths so it reads as a normal map marginalia element
# rather than spanning most of the page.
TARGET_BAR_WIDTH_MM = 80.0

# The bar's own native unit label is left empty (see
# add_scale_bar()) - "kilometers" is drawn as our own separate,
# independently-styleable (italic) label instead, along with the
# "Scale 1:N" text under it, matching the reference layout of
# three stacked, differently-styled lines rather than the bar's
# usual single-line "0  1  2  3  4 km" layout.
UNIT_LABEL_HEIGHT = 4.0
UNIT_LABEL_FONT_SIZE = 9

# Measured via QFontMetricsF: 9pt Arial's own ascent+descent is
# ~4.72mm - this leaves only a hair of slack over that real
# minimum, rather than the more generous round number used before.
SCALE_TEXT_HEIGHT = 4.8

# Matches center_coordinate.py's FONT_SIZE - was 11, confirmed
# too big relative to the rest of the marginalia text. Also
# applied to the bar's own tick numbers (TICK_NUMBER_FONT_SIZE
# below), the other "scale" text this request referred to.
SCALE_TEXT_FONT_SIZE = 9

TICK_NUMBER_FONT_SIZE = 9

# Gap between each of the three stacked lines (bar-to-unit-label,
# unit-label-to-scale-text) - squeezed to the minimum that still
# reads as separate lines rather than touching, per request.
GAP = 0.5

# Approximate space the bar's own "above segment" numbers need,
# on top of the bar's own drawn height - used only to size the
# shared bottom band from new_layout.py (required_height()); the
# actual bar is positioned by its own real sizeWithUnits() in
# add_scale_bar() itself.
NUMBER_LABEL_HEIGHT = 5.0

# Fixed item ids so a later call can find and replace these three
# items in place instead of stacking duplicates - see
# remove_scale_bar().
BAR_ITEM_ID = "mct_scale_bar"
UNIT_LABEL_ITEM_ID = "mct_scale_bar_unit_label"
SCALE_LABEL_ITEM_ID = "mct_scale_bar_scale_label"


def remove_scale_bar(layout):

    """
    Remove this layout's scale bar and its two accompanying
    labels, if present.
    """

    for item_id in (
        BAR_ITEM_ID,
        UNIT_LABEL_ITEM_ID,
        SCALE_LABEL_ITEM_ID,
    ):

        item = layout.itemById(item_id)

        if item is not None:
            layout.removeLayoutItem(item)


def required_height():

    """
    Total vertical space this group needs (numbers + bar + gap +
    unit label + gap + scale text) - used by new_layout.py to
    size the shared bottom margin band before anything is placed.
    """

    return (
        NUMBER_LABEL_HEIGHT
        + BAR_HEIGHT
        + GAP
        + UNIT_LABEL_HEIGHT
        + GAP
        + SCALE_TEXT_HEIGHT
    )


def _pick_units_per_segment(scale, num_segments):

    """
    Smallest "nice" km-per-segment value whose total bar width
    (num_segments segments, converted to page mm at the map's
    current scale) reaches at least TARGET_BAR_WIDTH_MM.
    """

    for candidate in NICE_SEGMENT_KM:

        total_km = candidate * num_segments

        total_mm = (total_km * 1_000_000) / scale

        if total_mm >= TARGET_BAR_WIDTH_MM:

            return candidate

    return NICE_SEGMENT_KM[-1]


def scale_text_expression():

    """
    "Scale 1:N" with a thousands-separated denominator, evaluated
    live so it always matches whatever scale the map item ends up
    at (including later manual changes in the Designer). Reused
    by metadata_block.py for its own "Map Scale:" line.

    @map_scale doesn't resolve to anything in a plain label's own
    expression context (confirmed live: it evaluates to NULL here,
    silently blanking the whole label) - it's only meaningful for
    items that are themselves linked to a map, like the scale bar
    below. mct_map_scale(@layout_name) is this plugin's own,
    already-proven way to look up "the" map for a given layout
    (see expressions/mgrs_functions.py) and works from any
    context; its output ("1:50000") is reformatted here to match
    the requested "1:50,000" comma-separated style.
    """

    return (
        "'1:' || format_number("
        "to_int(replace(mct_map_scale(@layout_name), '1:', '')), 0"
        ")"
    )


def add_scale_bar(layout, map_item, bottom_y):

    """
    Add a scale bar plus its unit and "Scale 1:N" labels, stacked
    bottom-up so the scale text's own bottom edge sits at bottom_y
    (a page-space y-coordinate, shared with the metadata block
    placed alongside it), centred on the page horizontally.
    Replaces any scale bar already on the layout.
    """

    remove_scale_bar(
        layout
    )

    page_width = layout.pageCollection().page(0).pageSize().width()

    scale_bar = QgsLayoutItemScaleBar(layout)

    scale_bar.setId(
        BAR_ITEM_ID
    )

    scale_bar.setLinkedMap(
        map_item
    )

    # Cosmetic baseline (colours, line/font style) - the scale-
    # relevant properties it also sets (units, segment sizing)
    # are all explicitly overridden below instead, since its
    # defaults left unitsPerSegment at 0.0 (a degenerate,
    # practically-invisible bar) when kilometres were requested,
    # and its FitWidth auto-sizing mode - the same one QGIS's own
    # "Add Scale Bar" GUI action uses - was confirmed live to
    # overshoot a requested maximum bar width rather than respect
    # it, whenever the next-smaller "nice" segment value would
    # have undershot the minimum. Computing the segment size
    # ourselves (_pick_units_per_segment) avoids depending on
    # that auto-sizing behaviour at all.
    scale_bar.applyDefaultSettings()

    scale_bar.setUnits(
        QgsUnitTypes.DistanceUnit.DistanceKilometers
    )

    # No explicit setMapUnitsPerScaleBarUnit() call here -
    # confirmed live that setting it to 1000.0 (reasoning: "1km =
    # 1000 map metres") double-applied the conversion, since
    # setUnits(DistanceKilometers) already handles the metres->km
    # conversion from the map's own CRS on its own; the labelled
    # values came out 1000x too small (e.g. "0.001" instead of
    # "1"). Left at its default (1.0 - no extra custom factor).
    scale_bar.setSegmentSizeMode(
        Qgis.ScaleBarSegmentSizeMode.Fixed
    )

    scale_bar.setNumberOfSegments(
        NUM_SEGMENTS
    )

    scale_bar.setUnitsPerSegment(
        _pick_units_per_segment(
            map_item.scale(),
            NUM_SEGMENTS
        )
    )

    scale_bar.setStyle(
        SCALE_BAR_STYLE
    )

    scale_bar.setUnitLabel(
        ""
    )

    scale_bar.setHeight(
        BAR_HEIGHT
    )

    scale_bar.setLabelVerticalPlacement(
        Qgis.ScaleBarDistanceLabelVerticalPlacement.AboveSegment
    )

    # applyDefaultSettings() leaves the tick-number font at
    # whatever the layout's own generic default is - explicit here
    # to match the rest of the marginalia text.
    scale_bar.setTextFormat(
        build_text_format(TICK_NUMBER_FONT_SIZE)
    )

    layout.addLayoutItem(
        scale_bar
    )

    bar_size = scale_bar.sizeWithUnits()

    scale_text_y = bottom_y - SCALE_TEXT_HEIGHT

    unit_label_y = (
        scale_text_y
        - GAP
        - UNIT_LABEL_HEIGHT
    )

    bar_y = (
        unit_label_y
        - GAP
        - bar_size.height()
    )

    scale_bar.attemptSetSceneRect(
        QRectF(
            (page_width - bar_size.width()) / 2,
            bar_y,
            bar_size.width(),
            bar_size.height()
        )
    )

    unit_label = QgsLayoutItemLabel(layout)

    unit_label.setId(
        UNIT_LABEL_ITEM_ID
    )

    unit_label.setText(
        "kilometers"
    )

    unit_label.setTextFormat(
        build_text_format(UNIT_LABEL_FONT_SIZE, italic=True)
    )

    unit_label.setHAlign(
        Qt.AlignmentFlag.AlignHCenter
    )

    layout.addLayoutItem(
        unit_label
    )

    unit_label.attemptSetSceneRect(
        QRectF(
            0,
            unit_label_y,
            page_width,
            UNIT_LABEL_HEIGHT
        )
    )

    scale_label = QgsLayoutItemLabel(layout)

    scale_label.setId(
        SCALE_LABEL_ITEM_ID
    )

    scale_label.setText(
        f"[% 'Scale ' || {scale_text_expression()} %]"
    )

    scale_label.setTextFormat(
        build_text_format(SCALE_TEXT_FONT_SIZE)
    )

    scale_label.setHAlign(
        Qt.AlignmentFlag.AlignHCenter
    )

    layout.addLayoutItem(
        scale_label
    )

    scale_label.attemptSetSceneRect(
        QRectF(
            0,
            scale_text_y,
            page_width,
            SCALE_TEXT_HEIGHT
        )
    )

    return scale_bar, unit_label, scale_label
