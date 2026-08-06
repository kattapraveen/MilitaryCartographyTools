# -*- coding: utf-8 -*-

"""
Create a new print layout with a chosen page size, orientation,
and initial map scale in one step, and let those same settings be
changed later on a layout that's already open in the Designer.

QGIS's own "New Layout" dialog only asks for a name and opens a
blank layout - page size, orientation and an initial map scale all
have to be configured afterwards, item by item. This wraps that
into a single up-front dialog and creates a ready-to-use layout
(with its map item already sized, positioned, and scaled) directly.

A layout's page size/orientation/scale/heading/classification can
also be revisited afterwards via the "Military Layout Settings"
dock panel added to every Layout Designer window (see plugin.py's
on_layout_designer_opened and layout_dialogs.py's
LayoutOptionsPanel), instead of having to throw the layout away
and create a new one for every iteration.

This module holds the layout-building/geometry logic
(create_layout/update_layout/_compute_geometry/_apply_marginalia);
the Qt dialog/panel that drive it live in layout_dialogs.py.

Military Cartography Tools
"""

import re

from qgis.core import (
    QgsPrintLayout,
    QgsLayoutItemMap,
    QgsLayoutSize,
    QgsUnitTypes,
    QgsProject,
    QgsRectangle
)

from .grid_position_diagram import add_grid_position_diagram
from .north_arrow import add_north_arrow
from .scale_bar import add_scale_bar
from .scale_bar import required_height as scale_bar_required_height
from .metadata_block import add_metadata_block
from .metadata_block import required_height as metadata_required_height
from .center_coordinate import add_center_coordinate_label
from .center_coordinate import required_height as center_coordinate_required_height
from .neatline import add_neatline
from .heading import add_heading
from .heading import required_height as heading_required_height
from .heading import remove_heading, existing_heading_lines
from .geographic_graticule import add_geographic_graticule
from .classification import add_classification_banner
from .classification import required_height as classification_required_height
from .classification import (
    remove_classification_banners,
    existing_classification,
    TOP_ITEM_ID as CLASSIFICATION_TOP_ITEM_ID,
    BOTTOM_ITEM_ID as CLASSIFICATION_BOTTOM_ITEM_ID,
)

from qgis.PyQt.QtCore import QRectF


# Page sizes in millimetres - each listed as (larger, smaller)
# dimension, since the dialog's own orientation toggle is what
# decides which one ends up as width vs height.
PAGE_SIZES = {
    "A0": (1189.0, 841.0),
    "A3": (420.0, 297.0),
    "A4": (297.0, 210.0),
    "Arch E": (1219.2, 914.4),  # 48 x 36 in
}

# Common map scales offered in the (still editable) scale combo -
# denominators only; the combo displays them as "1:N".
COMMON_SCALES = [
    10000,
    25000,
    50000,
    100000,
    250000,
    500000,
    1000000,
]

# Map item's own left/right margin from the page edges, in
# millimetres - reduced from an earlier, more conservative 15mm
# per request. The print-layout grid frame's worst-case label (a
# superscript hundreds-digit prefix at 18pt plus two normal digits
# at 12pt - see grid/layout_grid_frame.py's
# SUPERSCRIPT_SIZE/ANNOTATION_SIZE) measures ~11mm wide plus QGIS's
# own default 1mm annotation-to-frame distance, so at 10mm the very
# worst case can sit slightly into this margin rather than fully
# clear of the page edge - accepted trade-off for more map area.
MAP_SIDE_MARGIN = 10.0

# Clearance between the map item's own top edge and whatever's
# directly above it (a heading or classification banner) - or from
# the page edge directly if neither is present. Squeezed back down
# to the minimum per request, matching a hand-tuned reference
# layout - accepting that the grid frame's own worst-case label (a
# superscript hundreds-digit prefix, which only appears at the
# map's starting edge or a 100km boundary, not on every tick - see
# grid/layout_grid_frame.py) may occasionally sit close to, or
# slightly touch, the heading/scale bar text rather than always
# being fully clear of it (that would need ~10.5mm, measured via
# QFontMetricsF - deliberately not used here, in favour of map
# area).
MAP_TOP_CLEARANCE = 2.0

# Clearance between the map item's own bottom edge and the shared
# bottom band (scale bar/metadata block/centre coordinate) below
# it - same reasoning as MAP_TOP_CLEARANCE.
MAP_BOTTOM_CLEARANCE = 2.0

# Classification banner's own margin from the page's top/bottom
# edge, in millimetres - squeezed to the minimum that still reads
# as a clear gap from the page edge.
CLASSIFICATION_MARGIN = 2.0

# Gap between the classification banner and the heading, at the
# top of the page.
CLASSIFICATION_GAP_TOP = 1.5

# Gap between the shared bottom band (scale bar/metadata block/
# centre coordinate)'s own bottom edge and the classification
# banner, at the bottom of the page.
CLASSIFICATION_GAP_BOTTOM = 1.0

# Tolerance (mm) used to match a layout's actual page dimensions
# back to one of PAGE_SIZES when pre-filling the Layout Settings
# panel - a few hundredths of a mm of float drift shouldn't read
# as "Custom".
PRESET_MATCH_TOLERANCE_MM = 0.5


def _format_scale(denominator):

    return f"1:{denominator:,}"


def _parse_scale(text):

    """
    Parse a scale string like "1:50,000", "1:50000", or a bare
    "50000" into its denominator as a float.
    """

    digits = re.sub(
        r"[^0-9.]",
        "",
        text.split(":")[-1]
    )

    value = float(digits)

    if value <= 0:
        raise ValueError("Scale must be a positive number")

    return value


def _detect_preset(width_mm, height_mm):

    """
    Match (width_mm, height_mm) against PAGE_SIZES, in either
    orientation - returns (size_name, orientation), or ("Custom",
    an orientation guessed from the aspect ratio) if nothing
    matches closely enough. Used to pre-select the right preset in
    the Layout Settings panel from a layout that's already open.
    """

    for name, (larger, smaller) in PAGE_SIZES.items():

        if (
            abs(width_mm - larger) <= PRESET_MATCH_TOLERANCE_MM
            and abs(height_mm - smaller) <= PRESET_MATCH_TOLERANCE_MM
        ):
            return name, "Landscape"

        if (
            abs(width_mm - smaller) <= PRESET_MATCH_TOLERANCE_MM
            and abs(height_mm - larger) <= PRESET_MATCH_TOLERANCE_MM
        ):
            return name, "Portrait"

    return "Custom", ("Landscape" if width_mm >= height_mm else "Portrait")


def _unique_layout_name(project, name):

    manager = project.layoutManager()

    if manager.layoutByName(name) is None:
        return name

    suffix = 2

    while manager.layoutByName(f"{name} ({suffix})") is not None:

        suffix += 1

    return f"{name} ({suffix})"


def _find_map_item(layout):

    """
    The (single) map item on layout, or None. Every layout this
    plugin builds has exactly one.
    """

    for item in layout.items():

        if isinstance(item, QgsLayoutItemMap):
            return item

    return None


def _compute_geometry(width_mm, height_mm, heading_lines, classification):

    """
    Every y-coordinate needed to place the map item and its
    marginalia on a width_mm x height_mm page - shared by
    create_layout() (building a layout from scratch) and
    update_layout() (resizing one that's already open), so both
    always agree on where everything goes. All reserved space
    (classification/heading above, scale bar/metadata/centre
    coordinate band and classification below) is computed upfront
    so the map item's rect is already its final size before
    anything is placed - no post-hoc resize-and-reseed-extent step
    needed.
    """

    classification_height = classification_required_height(
        classification
    )

    has_classification = classification_height > 0

    heading_height = heading_required_height(
        len(heading_lines)
    )

    band_height = max(
        scale_bar_required_height(),
        metadata_required_height(),
        center_coordinate_required_height()
    )

    # Top: classification (if shown) is anchored CLASSIFICATION_MARGIN
    # from the page edge; the heading (if shown) sits CLASSIFICATION_GAP
    # below it, or takes that same anchor if there's no classification.
    # The map's own top edge is then always MAP_EDGE_GRID_CLEARANCE
    # below whichever of those is last - or that same clearance
    # straight from the page edge if neither is present.
    top_cursor = CLASSIFICATION_MARGIN

    classification_top_y = top_cursor

    if has_classification:

        top_cursor += classification_height + CLASSIFICATION_GAP_TOP

    heading_top_y = top_cursor

    if heading_lines:

        top_cursor += heading_height

    if has_classification or heading_lines:

        map_top = top_cursor + MAP_TOP_CLEARANCE

    else:

        map_top = MAP_TOP_CLEARANCE

    # Bottom mirrors the top: classification anchored
    # CLASSIFICATION_MARGIN from the bottom edge, the shared band
    # (scale bar/metadata block/centre coordinate) CLASSIFICATION_GAP
    # above it, and the map's own bottom edge always
    # MAP_EDGE_GRID_CLEARANCE above the band.
    bottom_cursor = height_mm - CLASSIFICATION_MARGIN

    if has_classification:

        bottom_cursor -= classification_height

    classification_bottom_y = bottom_cursor

    if has_classification:

        bottom_cursor -= CLASSIFICATION_GAP_BOTTOM

    band_bottom_y = bottom_cursor

    map_bottom = (
        band_bottom_y
        - band_height
        - MAP_BOTTOM_CLEARANCE
    )

    return {
        "has_classification": has_classification,
        "classification_top_y": classification_top_y,
        "classification_bottom_y": classification_bottom_y,
        "heading_top_y": heading_top_y,
        "map_top": map_top,
        "band_bottom_y": band_bottom_y,
        "map_bottom": map_bottom,
    }


def _apply_marginalia(
    layout,
    map_item,
    width_mm,
    height_mm,
    heading_lines,
    classification,
    geometry
):

    """
    Add (or replace, if already present) every marginalia item -
    used by both create_layout() and update_layout() so a layout
    ends up in exactly the same state either way. The always-on
    items (north arrow, neatline, graticule, scale bar, metadata
    block, centre coordinate) are idempotent in their own add_*
    functions; the optional ones (heading, classification) are
    removed explicitly first since there's no add_* call to fall
    back on when they're toggled off.
    """

    add_north_arrow(
        layout,
        map_item
    )

    add_grid_position_diagram(
        layout,
        map_item
    )

    add_neatline(
        map_item
    )

    add_geographic_graticule(
        map_item
    )

    remove_heading(
        layout
    )

    if heading_lines:

        add_heading(
            layout,
            width_mm,
            heading_lines,
            geometry["heading_top_y"]
        )

    remove_classification_banners(
        layout
    )

    if geometry["has_classification"]:

        add_classification_banner(
            layout,
            width_mm,
            classification,
            geometry["classification_top_y"],
            CLASSIFICATION_TOP_ITEM_ID
        )

        add_classification_banner(
            layout,
            width_mm,
            classification,
            geometry["classification_bottom_y"],
            CLASSIFICATION_BOTTOM_ITEM_ID
        )

    add_scale_bar(
        layout,
        map_item,
        geometry["band_bottom_y"]
    )

    add_metadata_block(
        layout,
        width_mm,
        height_mm,
        geometry["band_bottom_y"]
    )

    add_center_coordinate_label(
        layout,
        width_mm,
        geometry["band_bottom_y"]
    )


def create_layout(
    iface,
    name,
    width_mm,
    height_mm,
    scale,
    heading_lines=None,
    classification=None,
    center=None,
    open_designer=True
):

    """
    Create, register, and open a new print layout with the given
    page size (mm) and initial map scale, centred on the current
    canvas extent.

    heading_lines:
        0-2 strings for an optional heading at the top of the
        page. Omit (or pass an empty list) for no heading.

    classification:
        One of classification.LEVELS (e.g. "RESTRICTED"), shown
        bold/all-caps at both the top and bottom of the page.
        Omit (or "None") for no classification banners.

    center:
        A QgsPointXY, in the same CRS as the map canvas's own
        destination CRS, to centre the map on instead of the
        current canvas extent's centre - used by
        layout/map_sheet_series.py to place each sheet in a
        batch-generated series at its own computed centre rather
        than wherever the canvas happens to be pointed. Omit for
        the normal single-layout behaviour.

    open_designer:
        Whether to open this layout in the Layout Designer once
        built - True for the normal single-layout case; a batch
        generator creating many layouts at once passes False to
        avoid flooding the user with that many open windows.
    """

    heading_lines = heading_lines or []

    project = QgsProject.instance()

    layout = QgsPrintLayout(project)

    layout.initializeDefaults()

    layout.setName(
        _unique_layout_name(project, name)
    )

    layout.pageCollection().page(0).setPageSize(
        QgsLayoutSize(
            width_mm,
            height_mm,
            QgsUnitTypes.LayoutUnit.LayoutMillimeters
        )
    )

    geometry = _compute_geometry(
        width_mm,
        height_mm,
        heading_lines,
        classification
    )

    map_item = QgsLayoutItemMap(layout)

    map_item.attemptSetSceneRect(
        QRectF(
            MAP_SIDE_MARGIN,
            geometry["map_top"],
            width_mm - (2 * MAP_SIDE_MARGIN),
            geometry["map_bottom"] - geometry["map_top"]
        )
    )

    canvas = iface.mapCanvas()

    map_item.setCrs(
        canvas.mapSettings().destinationCrs()
    )

    # setExtent() resizes the ITEM's own rect to match whatever
    # aspect ratio the given extent has - confirmed live: passing
    # the canvas's own extent directly (whatever shape it happens
    # to be) silently overwrote the precise page-derived rect set
    # above. Seeding an extent that already matches the rect's own
    # aspect ratio (centred on the canvas's current centre) avoids
    # that resize entirely, so the rect set above sticks.
    canvas_extent = canvas.extent()

    rect_width = width_mm - (2 * MAP_SIDE_MARGIN)
    rect_height = geometry["map_bottom"] - geometry["map_top"]

    seed_width = canvas_extent.width()
    seed_height = seed_width * (rect_height / rect_width)

    # seed_width/seed_height only need to match the rect's own
    # aspect ratio, per the comment above - their absolute size is
    # irrelevant, since setScale() below rescales the extent around
    # this same centre point to the exact requested denominator
    # regardless of what size it started at. That's what makes it
    # safe to seed from the canvas's own (otherwise arbitrary, for
    # a batch-generated sheet) extent width even when center is
    # given explicitly.
    map_center = center if center is not None else canvas_extent.center()

    map_item.setExtent(
        QgsRectangle(
            map_center.x() - (seed_width / 2),
            map_center.y() - (seed_height / 2),
            map_center.x() + (seed_width / 2),
            map_center.y() + (seed_height / 2)
        )
    )

    project.layoutManager().addLayout(
        layout
    )

    layout.addLayoutItem(
        map_item
    )

    # Rescales the item's extent around its current centre to hit
    # this exact denominator - the seed extent above already
    # matches the rect's aspect ratio, so this doesn't touch the
    # rect either.
    map_item.setScale(
        scale
    )

    _apply_marginalia(
        layout,
        map_item,
        width_mm,
        height_mm,
        heading_lines,
        classification,
        geometry
    )

    if open_designer:

        iface.openLayoutDesigner(
            layout
        )

    return layout


def update_layout(
    layout,
    width_mm,
    height_mm,
    scale,
    heading_lines=None,
    classification=None
):

    """
    Re-apply page size/orientation/scale/heading/classification to
    a layout that's already open in the Designer, in place of
    creating a new one every time an option changes. Resizes the
    page and the map item (preserving the map's current centre)
    and replaces every marginalia item via the same
    _apply_marginalia() create_layout() uses, so the two paths can
    never drift apart. Does nothing if layout has no map item.
    """

    heading_lines = heading_lines or []

    map_item = _find_map_item(
        layout
    )

    if map_item is None:
        return

    layout.pageCollection().page(0).setPageSize(
        QgsLayoutSize(
            width_mm,
            height_mm,
            QgsUnitTypes.LayoutUnit.LayoutMillimeters
        )
    )

    geometry = _compute_geometry(
        width_mm,
        height_mm,
        heading_lines,
        classification
    )

    rect_width = width_mm - (2 * MAP_SIDE_MARGIN)
    rect_height = geometry["map_bottom"] - geometry["map_top"]

    map_item.attemptSetSceneRect(
        QRectF(
            MAP_SIDE_MARGIN,
            geometry["map_top"],
            rect_width,
            rect_height
        )
    )

    # Same aspect-seeding trick as create_layout(), centred on the
    # map's own current centre this time (preserving whatever pan
    # position it already had) rather than the canvas's, since
    # we're editing a layout that already has its own independent
    # view rather than seeding a brand new one.
    current_extent = map_item.extent()

    center = current_extent.center()

    seed_width = current_extent.width()
    seed_height = seed_width * (rect_height / rect_width)

    map_item.setExtent(
        QgsRectangle(
            center.x() - (seed_width / 2),
            center.y() - (seed_height / 2),
            center.x() + (seed_width / 2),
            center.y() + (seed_height / 2)
        )
    )

    map_item.setScale(
        scale
    )

    _apply_marginalia(
        layout,
        map_item,
        width_mm,
        height_mm,
        heading_lines,
        classification,
        geometry
    )

    layout.refresh()


def get_layout_values(layout):

    """
    layout's own current page size/scale/heading/classification -
    used to pre-fill the Layout Settings panel when a Layout
    Designer window opens on a layout this plugin already built.
    """

    page_size = layout.pageCollection().page(0).pageSize()

    map_item = _find_map_item(
        layout
    )

    scale = (
        map_item.scale()
        if map_item is not None
        # No map item to read a real scale from (a layout with
        # none shouldn't normally happen, but the panel still
        # needs something to show) - COMMON_SCALES[2] is 50000,
        # matching NewLayoutDialog's own default scale.
        else COMMON_SCALES[2]
    )

    return {
        "width": page_size.width(),
        "height": page_size.height(),
        "scale": scale,
        "heading_lines": existing_heading_lines(layout),
        "classification": existing_classification(layout),
    }
