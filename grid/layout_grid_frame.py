# -*- coding: utf-8 -*-

"""
Layout Grid Frame

Adds a native QGIS layout map-grid frame - tick marks plus
coordinate annotations positioned just outside the map's border -
to a print layout's map item.

This is the standard topographic/military map convention for
printed grid coordinates (ticks on the neatline, not labels drawn
over the map content), and it uses QGIS's own built-in
QgsLayoutItemMapGrid feature rather than PAL line-anchor
labeling, which mgrs_sub_grid.py's own investigation found to be
unreliable for near-vertical lines during a layout's static
render.

The grid LINES across the map still come from the plugin's own
generated sub-grid layer (unchanged, already correct in both
canvas and layout) - this frame only adds the border ticks and
numbers, and hides that layer's own on-map tick labels within
this one layout by swapping in a label-disabled clone of the
layer for this map item specifically (a QgsMapLayerStyleOverride
was tried first but had no visible effect on labeling, even
though the override was confirmed correctly attached) - the
canvas keeps showing the original layer, labels and all.

Military Cartography Tools
"""

import math

from qgis.core import (
    QgsLayoutItemMapGrid,
    QgsProject,
    QgsCoordinateTransform
)

from ..core.coordinate_utils import project_to_wgs84, get_utm_crs
from ..core.text_format import build_text_format
from .mgrs_sub_grid import MGRSSubGridGenerator


NAME = "Military Grid Frame"

# Matches mgrs_sub_grid.py's own on-map LABEL_SIZE, so the
# layout frame's numbers read the same size as the main canvas's
# grid labels rather than looking undersized by comparison.
ANNOTATION_SIZE = 12

# Point size of the superscript prefix digit specifically - the
# Unicode superscript glyphs below are already raised/shaped
# correctly on their own, but ride at whatever size the run's
# HTML span requests, so this is independent of ANNOTATION_SIZE.
# Kept at the same ratio to ANNOTATION_SIZE (~1.5x) that was
# confirmed headlessly to stay inline without wrapping.
SUPERSCRIPT_SIZE = 18

# Real Unicode superscript digits, indexed by value - these
# render genuinely raised and small in any font, unlike HTML
# markup: both a bare <sup> tag and an explicit inline
# vertical-align:super style were tried and neither actually
# raised the digit in this QGIS build's label rendering (only
# shrank the font). HTML is still used for SIZE (font-size did
# work in that earlier test, just not the vertical raise), so
# the two techniques are combined: Unicode glyph for the raise,
# HTML span for the size.
SUPERSCRIPT_DIGITS = "⁰¹²³⁴⁵⁶⁷⁸⁹"


def _annotation_expression(spacing, edge_values):

    """
    Build the tick annotation expression for a given spacing.

    Every tick shows the plain 2-digit "tens+units of km" value
    (e.g. "51"). A frame annotation doesn't sit right next to its
    own 100km square's label the way an on-map tick does, so that
    alone can be ambiguous between adjacent squares whose last
    two km digits happen to match (e.g. "51" for both 451xxx and
    551xxx) - disambiguated with a small superscript hundreds-of-
    km digit prefix, standard topographic-map convention, but
    only at the map's own starting edge (so the reader has
    context immediately) and at each 100km boundary ("00") - not
    on every single tick, which would be noisy, and not on the
    opposite edge either.

    edge_values:
        The exact coordinate values (in the grid's own CRS,
        computed once in Python from the map's current extent -
        see _edge_ticks()) of the starting-edge tick for each
        axis. Matched against the FULL coordinate, not just its
        last 2 digits, so this never accidentally fires on an
        unrelated tick elsewhere that happens to share the same
        tens+units.
    """

    tens_units = (
        "lpad(to_string(to_int((@grid_number % 100000) / 1000)), 2, '0')"
    )

    # Wrapped in its own explicit-size span, rather than left as
    # plain text relying on the annotation's base text format -
    # with allowHtmlFormatting on, plain (unwrapped) runs were
    # rendering noticeably larger than ANNOTATION_SIZE, so every
    # run now carries its own explicit font-size span.
    main_digits = (
        f"'<span style=\"font-size:{ANNOTATION_SIZE}pt;\">' || "
        f"{tens_units} || '</span>'"
    )

    hundreds_digit = (
        "to_int((@grid_number % 1000000) / 100000)"
    )

    superscript_digit = "CASE " + " ".join(
        f"WHEN {hundreds_digit} = {digit} THEN '{char}'"
        for digit, char in enumerate(SUPERSCRIPT_DIGITS)
    ) + " END"

    superscript = (
        f"'<span style=\"font-size:{SUPERSCRIPT_SIZE}pt;\">' || "
        f"{superscript_digit} || '</span>'"
    )

    prefixed = f"{superscript} || {main_digits}"

    edge_list = ", ".join(
        str(int(value))
        for value in sorted(edge_values)
    )

    return (
        f"CASE WHEN {hundreds_digit} = 0 "
        f"THEN {main_digits} "
        f"WHEN {tens_units} = '00' OR @grid_number IN ({edge_list}) "
        f"THEN {prefixed} "
        f"ELSE {main_digits} "
        f"END"
    )

# Custom property marking a layer as one of this module's own
# label-disabled clones, so it can be told apart from the real
# sub-grid layer during cleanup.
CLONE_MARKER = "mct_grid_frame_label_clone"

# Every layer name the canvas's sub-grid generator can produce -
# whichever of these actually exist have their on-map tick labels
# hidden for this layout while the frame is active.
SUB_GRID_LAYER_NAMES = [
    f"MGRS {spacing // 1000}km Grid"
    for spacing in (
        MGRSSubGridGenerator.ORDER_MAJOR,
        MGRSSubGridGenerator.ORDER_MEDIUM,
        MGRSSubGridGenerator.ORDER_MINOR,
    )
]


def _grid_crs(map_item):

    """
    UTM CRS for the map item's own centre - matches the
    convention used elsewhere in this plugin (one UTM zone per
    area of interest) rather than the project's own CRS, which
    may be geographic and unsuitable for a metre-based interval.
    """

    center = map_item.extent().center()

    wgs84_center = project_to_wgs84(
        center
    )

    return get_utm_crs(
        wgs84_center.y(),
        wgs84_center.x()
    )


# Aim for roughly this many ticks along the map's longer side -
# unlike on-map PAL labels (which thin themselves out via
# collision avoidance), every frame tick gets a number with no
# such filtering, so crowding has to be controlled directly by
# picking a coarse enough interval for the actual ground distance
# being printed, not by the map's scale denominator alone (the
# same scale can cover very different ground distances depending
# on page size).
TARGET_TICKS_PER_SIDE = 10


def _extent_in_grid_crs(map_item, grid_crs):

    """
    The layout map item's current extent, reprojected into the
    grid's own CRS (metres) - shared by _auto_spacing() and
    _edge_ticks() so both work from the same ground-distance
    figures.
    """

    transform = QgsCoordinateTransform(
        QgsProject.instance().crs(),
        grid_crs,
        QgsProject.instance()
    )

    return transform.transformBoundingBox(
        map_item.extent()
    )


def _auto_spacing(extent_m):

    """
    Pick the finest tick spacing that still keeps roughly
    TARGET_TICKS_PER_SIDE or fewer ticks along the map's longer
    side, based on the actual ground distance the layout's map
    item currently covers.
    """

    span = max(
        extent_m.width(),
        extent_m.height()
    )

    for order in (
        MGRSSubGridGenerator.ORDER_MINOR,
        MGRSSubGridGenerator.ORDER_MEDIUM,
        MGRSSubGridGenerator.ORDER_MAJOR,
    ):

        if span / order <= TARGET_TICKS_PER_SIDE:

            return order

    return MGRSSubGridGenerator.ORDER_MAJOR


# QgsLayoutItemMapGrid computes its own frame ticks from
# intervalX/Y against an implicit origin, independent of the
# actual sub-grid layer's drawn lines - whenever the map's own
# extent happens to land exactly on a multiple of the spacing
# (very common with round UTM extents, and GUARANTEED for the
# edge ticks computed below, by construction), a tick ends up
# sitting exactly on the frame's corner. Confirmed live (via a
# real exported PDF): QGIS then mis-assigns that corner tick to
# the perpendicular side - an easting's annotation appearing on
# the LEFT edge instead of the TOP, positioned wherever that
# side's own annotation rules happen to place it, rather than
# vanishing outright. Nudging every tick by a tiny, fixed offset
# keeps them off the exact boundary/corner without perceptibly
# moving them - since it's applied uniformly (grid.setOffsetX/Y
# in add_grid_frame(), plus here so edge_values still match the
# actual @grid_number values QGIS will generate), and since it's
# far smaller than the smallest tick spacing (1000m), it doesn't
# change any displayed digit (tens_units/hundreds_digit only look
# at thousands and above).
GRID_OFFSET = 1.0


def _edge_ticks(extent_m, spacing):

    """
    The exact coordinate (in the grid's own CRS) of the starting-
    edge tick for each axis, for the given spacing - both axes are
    read in the natural left-to-right / bottom-to-top map reading
    order, so the starting tick is the western (minimum-X) edge
    for eastings and the southern (minimum-Y) edge for northings.
    Only these, not the opposite edges too - the reader gets
    context once at the start of each axis, plus at every 100km
    boundary.
    """

    return [
        math.ceil(extent_m.xMinimum() / spacing) * spacing + GRID_OFFSET,
        math.ceil(extent_m.yMinimum() / spacing) * spacing + GRID_OFFSET,
    ]


def _text_format():

    # allow_html needed for the <span style="font-size:..."> markup
    # around the superscript digit in _annotation_expression() to
    # actually change that digit's size rather than showing up as
    # literal tag text - confirmed working for size (unlike
    # vertical-align, which this build's label rendering seems
    # not to support at all).
    return build_text_format(
        ANNOTATION_SIZE,
        allow_html=True
    )


def _sub_grid_layers():

    """
    The real (non-clone) sub-grid layers currently in the
    project, by name.
    """

    project = QgsProject.instance()

    layers = []

    for name in SUB_GRID_LAYER_NAMES:

        for layer in project.mapLayersByName(name):

            if not layer.customProperty(CLONE_MARKER):

                layers.append(
                    layer
                )

    return layers


def _visible_project_layers():

    """
    Every layer currently checked visible in the project's layer
    tree, in tree order - the baseline set to fall back on when
    the map item isn't already using its own locked layer list.
    """

    root = QgsProject.instance().layerTreeRoot()

    return [
        node.layer()
        for node in root.findLayers()
        if node.itemVisibilityChecked() and node.layer() is not None
    ]


def _hide_sub_grid_labels(map_item):

    """
    Swap in a label-disabled clone of each sub-grid layer for
    this map item specifically, in place of the real layer - a
    QgsMapLayerStyleOverride was tried first (confirmed correctly
    attached, with labelsEnabled="0" in the serialized style) but
    had no visible effect on rendered labels, so this uses the
    layer-set mechanism instead, which is already proven to work
    for controlling what a specific layout map item renders.
    """

    grid_layers = _sub_grid_layers()

    if not grid_layers:
        return

    grid_ids = {
        layer.id()
        for layer in grid_layers
    }

    if map_item.keepLayerSet():

        base = [
            layer for layer in map_item.layers()
            if layer.id() not in grid_ids
            and not layer.customProperty(CLONE_MARKER)
        ]

    else:

        base = [
            layer for layer in _visible_project_layers()
            if layer.id() not in grid_ids
        ]

    clones = []

    for layer in grid_layers:

        clone = layer.clone()

        # clone() copies the memory layer's schema/symbology, but
        # its provider's feature data is runtime state that isn't
        # guaranteed to come along for a "memory" provider - if
        # it didn't, the clone would silently render as an empty
        # (line-less) layer. Confirmed live: without this, the
        # grid lines themselves vanished from the layout, not
        # just the labels.
        if clone.dataProvider().featureCount() == 0:

            clone.dataProvider().addFeatures(
                list(
                    layer.getFeatures()
                )
            )

            clone.updateExtents()

        clone.setLabelsEnabled(False)

        # clone() also preserves the original's exact name - left
        # unchanged, this clone (registered in the project so it
        # can be referenced by the map item, but never added to
        # the Layers panel) would satisfy any OTHER code's
        # mapLayersByName("MGRS 1km Grid") lookup too. Confirmed
        # live: this silently broke the canvas's own "does this
        # layer already exist?" check in GridManager.show_sub_grid
        # after a leftover clone from earlier layout testing stuck
        # around - it matched the clone (which has no tree node,
        # so nothing visibly happened) and skipped regenerating.
        clone.setName(
            layer.name() + " (grid frame, no labels)"
        )

        clone.setCustomProperty(
            CLONE_MARKER,
            True
        )

        QgsProject.instance().addMapLayer(
            clone,
            False
        )

        clones.append(
            clone
        )

    map_item.setLayers(
        clones + base
    )

    map_item.setKeepLayerSet(True)


def _restore_sub_grid_labels(map_item):

    """
    Undo _hide_sub_grid_labels(): drop this module's label-
    disabled clones and, if the map item's locked layer set only
    ever existed to support this, unlock it again so the item
    goes back to mirroring the project's layer tree dynamically.
    """

    if not map_item.keepLayerSet():
        return

    current = list(
        map_item.layers()
    )

    clones = [
        layer for layer in current
        if layer.customProperty(CLONE_MARKER)
    ]

    if not clones:
        return

    # Clear the explicit list entirely rather than repopulating it
    # with the non-grid "base" layers captured at add-time - that
    # base list was deliberately built EXCLUDING the real sub-grid
    # layers (they were swapped for clones), so setting it back
    # would leave the map item's layer list permanently missing
    # the grid, even after setKeepLayerSet(False) - confirmed live:
    # the grid stopped reappearing in the layout at all, across
    # repeated reopens, until the explicit list itself was cleared.
    map_item.setLayers(
        []
    )

    map_item.setKeepLayerSet(False)

    for clone in clones:

        QgsProject.instance().removeMapLayer(
            clone.id()
        )


def remove_grid_frame(map_item):

    """
    Remove this plugin's grid frame from a map item, if present,
    and restore that layout's sub-grid layers to their normal
    (on-map labels enabled) style.
    """

    stack = map_item.grids()

    for existing in stack.asList():

        if existing.name() == NAME:

            stack.removeGrid(
                existing.id()
            )

    _restore_sub_grid_labels(
        map_item
    )

    # .refresh() alone doesn't force a redraw - QgsLayoutItemMap
    # caches its rendered image, and only invalidateCache()
    # actually marks that cache dirty (same lesson learned
    # earlier this session with the since-abandoned locked-
    # layer-set approach).
    map_item.invalidateCache()


def add_grid_frame(map_item, spacing=None):

    """
    Add (replacing any existing one) a tick-and-annotation grid
    frame on a layout map item, and hide the sub-grid layer's own
    on-map tick labels for this layout only (the frame replaces
    them) - the canvas keeps showing those labels as normal.

    spacing:
        Tick interval in metres (10000/5000/1000). Auto-picked
        from the layout's own current print scale when omitted -
        see _auto_spacing().
    """

    grid_crs = _grid_crs(
        map_item
    )

    extent_m = _extent_in_grid_crs(
        map_item,
        grid_crs
    )

    if spacing is None:

        spacing = _auto_spacing(
            extent_m
        )

    edge_values = _edge_ticks(
        extent_m,
        spacing
    )

    remove_grid_frame(
        map_item
    )

    grid = QgsLayoutItemMapGrid(
        NAME,
        map_item
    )

    grid.setCrs(
        grid_crs
    )

    grid.setIntervalX(
        spacing
    )

    grid.setIntervalY(
        spacing
    )

    # See GRID_OFFSET's comment on _edge_ticks() - keeps every
    # tick this grid computes off the exact map boundary/corner,
    # avoiding a QGIS mis-assignment of corner-coincident ticks to
    # the wrong (perpendicular) side.
    grid.setOffsetX(
        GRID_OFFSET
    )

    grid.setOffsetY(
        GRID_OFFSET
    )

    # Grid LINES already come from the plugin's own generated
    # layer - this frame is only for the border ticks/numbers.
    grid.setStyle(
        QgsLayoutItemMapGrid.FrameAnnotationsOnly
    )

    grid.setFrameStyle(
        QgsLayoutItemMapGrid.InteriorTicks
    )

    grid.setAnnotationEnabled(
        True
    )

    grid.setAnnotationFormat(
        QgsLayoutItemMapGrid.CustomFormat
    )

    grid.setAnnotationExpression(
        _annotation_expression(spacing, edge_values)
    )

    grid.setAnnotationTextFormat(
        _text_format()
    )

    for side in (
        QgsLayoutItemMapGrid.Left,
        QgsLayoutItemMapGrid.Right,
        QgsLayoutItemMapGrid.Top,
        QgsLayoutItemMapGrid.Bottom,
    ):

        grid.setAnnotationPosition(
            QgsLayoutItemMapGrid.OutsideMapFrame,
            side
        )

        # Keep annotation text upright/horizontal on every side -
        # this controls the TEXT'S OWN rotation, not which axis
        # it represents (that's annotationDisplay, below); using
        # Vertical here for the left/right sides was a mistake
        # that rotated the northing numbers 90 degrees.
        grid.setAnnotationDirection(
            QgsLayoutItemMapGrid.Horizontal,
            side
        )

    # Eastings (values that vary left-to-right) run along the
    # top/bottom edges; northings (values that vary top-to-
    # bottom) run along the left/right edges - same convention
    # as the plugin's own on-map tick labels.
    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.LongitudeOnly,
        QgsLayoutItemMapGrid.Top
    )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.LongitudeOnly,
        QgsLayoutItemMapGrid.Bottom
    )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.LatitudeOnly,
        QgsLayoutItemMapGrid.Left
    )

    grid.setAnnotationDisplay(
        QgsLayoutItemMapGrid.LatitudeOnly,
        QgsLayoutItemMapGrid.Right
    )

    map_item.grids().addGrid(
        grid
    )

    _hide_sub_grid_labels(
        map_item
    )

    # .refresh() alone doesn't force a redraw - QgsLayoutItemMap
    # caches its rendered image, and only invalidateCache()
    # actually marks that cache dirty (same lesson learned
    # earlier this session with the since-abandoned locked-
    # layer-set approach).
    map_item.invalidateCache()

    return grid
