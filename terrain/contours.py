# -*- coding: utf-8 -*-

"""
Plain contour lines, styled the way a topographic sheet draws them:
index contours every fifth line at a heavier weight and labelled with
their height, intermediate contours as hairlines, both in the usual
brown.

Deliberately NOT Tanaka Contours. That tool varies line width by
terrain illumination, which means splitting every contour into short
segments and sampling the DEM twice per segment - the expense that
makes it a map-sheet technique and nothing larger (see
docs/roadmap.md's 2026-10-20 entry, where a country-sized extent made
QGIS hang). This module does neither: gdal:contour emits one feature
per contour line and the styling is a renderer, so a whole country at
a sensible interval is one ordinary run with no DEM-sampling cost at
all. It is the right tool for a small-scale sheet; Tanaka is the right
tool for a large-scale one.

Military Cartography Tools
"""

import math

import processing

from qgis.core import (
    Qgis,
    QgsLineSymbol,
    QgsPalLayerSettings,
    QgsProcessing,
    QgsRuleBasedLabeling,
    QgsRuleBasedRenderer,
    QgsSymbolLayerReference,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsTextMaskSettings,
    QgsVectorLayer,
)

from qgis.PyQt.QtGui import QColor, QFont

from ._dem_utils import clip_and_reproject_dem
from .tanaka_contours import MAX_DEM_PIXELS


OUTPUT_LAYER_NAME = "Contours"

ELEVATION_FIELD = "ELEV"

# Brown, the topographic and military convention for contours on land.
# Exposed in the dialog as a colour picker rather than fixed, so a
# sheet can be matched or printed monochrome.
DEFAULT_COLOUR = "#8a5a2b"

# Every fifth line is an index contour. Universal enough on printed
# sheets to be the default, but a parameter because 4 and 10 both
# appear in the wild.
DEFAULT_INDEX_EVERY = 5

DEFAULT_INTERVAL = 20.0

INDEX_WIDTH_MM = 0.35
INTERMEDIATE_WIDTH_MM = 0.15

LABEL_FONT_SIZE = 7.0

# The gap cut in the line so a label sits IN it rather than on top of
# it. Same Selective Masking technique military_symbology/
# _control_measure_shared.py uses for Boundary's own echelon label -
# see that module if this ever needs to do something cleverer.
LABEL_MASK_MM = 1.1

# Stable ids so the label mask can name the symbol layer it cuts
# through. A mask references a symbol layer by id, so these have to be
# set explicitly rather than left to QGIS's generated ones.
INDEX_SYMBOL_LAYER_ID = "contour_index"
INTERMEDIATE_SYMBOL_LAYER_ID = "contour_intermediate"

# Contour interval by map scale, following what published sheets
# actually use rather than a formula. There is no single formula that
# fits: 1:50,000 uses 20 m (1/2,500 of the scale) while 1:250,000 and
# 1:1,000,000 use 50 m and 200 m (1/5,000), because a large-scale
# sheet carries proportionally more detail.
#
# These are comfortably coarser than bare legibility requires. The
# usual 0.4 mm-apart rule puts the FLOOR at about 1 m for 1:50,000 on
# moderate ground and 20 m for 1:1,000,000 - but a sheet drawn at its
# legibility floor is an unreadable thicket, and SRTM's own vertical
# error (around +/-10 m) makes anything finer than ~20 m contour the
# noise rather than the ground. Practice, not the floor, is the useful
# suggestion.
#
# (max_scale_denominator, interval_m) - the first band whose scale is
# at least the map's own wins.
_INTERVAL_BY_SCALE = (
    (10_000, 5.0),
    (25_000, 10.0),
    (50_000, 20.0),
    (100_000, 25.0),
    (250_000, 50.0),
    (500_000, 100.0),
    (1_000_000, 200.0),
)

# Beyond the last band, keep the 1/5,000 ratio the small-scale bands
# settle on rather than inventing a new rule.
_INTERVAL_RATIO_BEYOND_TABLE = 5_000.0


def round_up_nicely(value):

    """
    The next 1, 2 or 5 times a power of ten at or above `value`, so a
    suggested interval reads as a number someone would actually type
    (20, 50, 200) rather than 183.47.
    """

    if value <= 0:
        return 0

    power = math.floor(math.log10(value))

    for step in (1, 2, 5, 10):

        candidate = step * (10 ** power)

        if candidate >= value:
            return candidate

    return 10 ** (power + 1)


def suggested_interval(map_scale):

    """
    The contour interval a sheet at `map_scale` would normally use -
    the denominator, so 50000 for 1:50,000.

    Read off _INTERVAL_BY_SCALE, which follows published practice: 20 m
    at 1:50,000, 50 m at 1:250,000, 200 m at 1:1,000,000. See that
    table's own comment for why this is not derived from the 0.4 mm
    legibility rule - that rule gives a floor far finer than anything
    anyone draws, and finer than SRTM's own vertical error can
    support.

    A suggestion, not a limit. The dialog opens with it and the user
    may type anything; it exists so that asking for 20 m contours on a
    1:1,000,000 sheet is a deliberate choice rather than an accident.
    """

    if map_scale <= 0:
        return DEFAULT_INTERVAL

    for max_scale, interval in _INTERVAL_BY_SCALE:

        if map_scale <= max_scale:
            return interval

    return round_up_nicely(map_scale / _INTERVAL_RATIO_BEYOND_TABLE)


def _line_symbol(colour, width_mm, symbol_layer_id):

    symbol = QgsLineSymbol.createSimple(
        {
            "color": colour.name(),
            "width": str(width_mm),
            "capstyle": "round",
            "joinstyle": "round",
        }
    )

    symbol.symbolLayer(0).setId(
        symbol_layer_id
    )

    return symbol


def _index_filter(interval, index_every):

    """
    True for an index contour.

    Compared against a tolerance rather than with `% == 0`: ELEV is a
    double written by gdal:contour, and an exact modulo on a float is
    a coin toss - 1500.0 % 500 can land on 499.99999999 as easily as
    on 0. The tolerance is a thousandth of the interval, far tighter
    than any real contour spacing and far looser than the error.
    """

    index_interval = interval * index_every

    tolerance = interval / 1000.0

    return (
        f'abs("{ELEVATION_FIELD}" - '
        f'(round("{ELEVATION_FIELD}" / {index_interval}) '
        f'* {index_interval})) < {tolerance}'
    )


def _build_renderer(colour, interval, index_every):

    """
    Two rules: index contours heavier, everything else a hairline.
    Rule-based rather than two layers, so the result is one layer the
    user can move, toggle and style as a unit.
    """

    root = QgsRuleBasedRenderer.Rule(None)

    index_rule = QgsRuleBasedRenderer.Rule(
        _line_symbol(colour, INDEX_WIDTH_MM, INDEX_SYMBOL_LAYER_ID)
    )

    index_rule.setLabel("Index contour")

    index_rule.setFilterExpression(
        _index_filter(interval, index_every)
    )

    intermediate_rule = QgsRuleBasedRenderer.Rule(
        _line_symbol(
            colour,
            INTERMEDIATE_WIDTH_MM,
            INTERMEDIATE_SYMBOL_LAYER_ID
        )
    )

    intermediate_rule.setLabel("Intermediate contour")

    intermediate_rule.setIsElse(True)

    root.appendChild(index_rule)
    root.appendChild(intermediate_rule)

    return QgsRuleBasedRenderer(root)


def _build_labeling(layer, colour, interval, index_every):

    """
    Height labels on the index contours only, set INTO a gap cut in
    the line rather than drawn over it.

    Intermediate contours are deliberately unlabelled: on a real sheet
    only the index lines carry their height, and labelling every line
    at a 20 m interval would bury the map in numbers.
    """

    settings = QgsPalLayerSettings()

    # to_string(to_int(...)) rather than format_number(), which adds a
    # thousands separator - a contour labelled "1,000" is not how any
    # sheet draws it.
    settings.fieldName = (
        f'to_string(to_int(round("{ELEVATION_FIELD}")))'
    )
    settings.isExpression = True

    settings.placement = Qgis.LabelPlacement.Line

    settings.lineSettings().setPlacementFlags(
        Qgis.LabelLinePlacementFlags(
            Qgis.LabelLinePlacementFlag.OnLine
        )
    )

    text_format = QgsTextFormat()

    font = QFont()
    font.setItalic(True)

    text_format.setFont(font)
    text_format.setSize(LABEL_FONT_SIZE)
    text_format.setSizeUnit(Qgis.RenderUnit.Points)
    text_format.setColor(colour)

    # A small white buffer as well as the mask: the mask clears the
    # contour itself, the buffer keeps the number legible over
    # whatever raster is underneath.
    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(0.6)
    buffer_settings.setSizeUnit(Qgis.RenderUnit.Millimeters)
    buffer_settings.setColor(QColor("#ffffff"))

    text_format.setBuffer(buffer_settings)

    mask_settings = QgsTextMaskSettings()
    mask_settings.setEnabled(True)
    mask_settings.setSize(LABEL_MASK_MM)
    mask_settings.setSizeUnit(Qgis.RenderUnit.Millimeters)

    # Both ids are passed even though only the index line is ever
    # labelled: QGIS simply finds no matching symbol layer for the
    # other, which is a harmless no-op, and this keeps working if the
    # rules are ever reorganised.
    mask_settings.setMaskedSymbolLayers(
        [
            QgsSymbolLayerReference(layer.id(), INDEX_SYMBOL_LAYER_ID),
            QgsSymbolLayerReference(
                layer.id(), INTERMEDIATE_SYMBOL_LAYER_ID
            ),
        ]
    )

    text_format.setMask(mask_settings)

    settings.setFormat(text_format)

    # Label only what the index rule draws.
    rule_root = QgsRuleBasedLabeling.Rule(None)

    index_label_rule = QgsRuleBasedLabeling.Rule(settings)

    index_label_rule.setFilterExpression(
        _index_filter(interval, index_every)
    )

    rule_root.appendChild(index_label_rule)

    return QgsRuleBasedLabeling(rule_root)


def default_insert_position(project, layer):

    """
    Bottom of the tree, like Hypsometric Tint's own - contours are a
    base on which other things are drawn, so a brand new layer should
    not cover the symbology already in the project.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        len(root.children()),
        layer
    )


def generate_contours(
    dem_layer,
    extent,
    extent_crs,
    interval=DEFAULT_INTERVAL,
    index_every=DEFAULT_INDEX_EVERY,
    colour=None,
):

    """
    Build a styled contour layer from dem_layer, clipped to extent.
    Deliberately does NOT add the layer to the project - see
    core/_layer_utils.py's module docstring for why. Returns the
    layer.
    """

    if interval <= 0:
        raise ValueError(
            f"Contour interval must be positive, got {interval}"
        )

    if index_every < 1:
        raise ValueError(
            f"Index contours must be every 1 or more, got {index_every}"
        )

    colour = QColor(colour) if colour is not None else QColor(DEFAULT_COLOUR)

    clipped_dem = clip_and_reproject_dem(
        dem_layer,
        extent,
        extent_crs
    )

    pixels = clipped_dem.width() * clipped_dem.height()

    if pixels > MAX_DEM_PIXELS:

        raise ValueError(
            f"This DEM is too large to contour: {pixels:,} pixels "
            f"({clipped_dem.width():,} x {clipped_dem.height():,}) "
            f"against a limit of {MAX_DEM_PIXELS:,}. Clip the DEM, or "
            "narrow the extent."
        )

    result = processing.run(
        "gdal:contour",
        {
            "INPUT": clipped_dem,
            "BAND": 1,
            "INTERVAL": interval,
            "FIELD_NAME": ELEVATION_FIELD,
            "CREATE_3D": False,
            "IGNORE_NODATA": False,
            "NODATA": None,
            "OFFSET": 0.0,
            "EXTRA": None,
            "OPTIONS": "",
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT,
        }
    )

    layer = QgsVectorLayer(
        result["OUTPUT"],
        OUTPUT_LAYER_NAME,
        "ogr"
    )

    if not layer.isValid():

        raise ValueError(
            "Could not read the contours gdal:contour produced at "
            f"{result['OUTPUT']} (interval {interval:g}). The contour "
            "step ran but left nothing openable."
        )

    layer.setRenderer(
        _build_renderer(colour, interval, index_every)
    )

    layer.setLabeling(
        _build_labeling(layer, colour, interval, index_every)
    )

    layer.setLabelsEnabled(True)

    return layer
