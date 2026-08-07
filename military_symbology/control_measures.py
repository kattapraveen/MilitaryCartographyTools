# -*- coding: utf-8 -*-

"""
Builds ready-to-use control-measure layers - one for line-type measures
(phase lines, boundaries, axis of advance), one for area-type measures
(objectives, named areas of interest) - each styled via a
QgsRuleBasedRenderer keyed on a "measure_type" field, mirroring
grid/mgrs_sub_grid.py's own rule-based renderer pattern.

Unlike military_symbology/sidc.py's point symbols (verified exactly
against milsymbol.js's own parsing source - see that module's docstring),
there is no equivalent programmatic renderer for MIL-STD-2525/APP-6
tactical graphics lines and areas to verify against: milsymbol.js's own
source has no multipoint/polygon/linestring code at all, and the one
library that attempted this (milgraphics) is archived/incomplete (see
docs/roadmap.md's Phase 10 entry). The line/area SHAPES below (dashed
boundary pattern, arrowhead placement, NAI's dashed-outline-on-any-polygon)
remain a hand-authored, practically-recognisable approximation rather
than a verified-correct rendition of MIL-STD-2525D Appendix H's own
templates (which specify, e.g., an actual hexagon for NAI and
echelon-symbol line ends for boundaries) - a further pass to match those
templates precisely is tracked as a future sub-phase in docs/roadmap.md,
deliberately deferred since it needs custom QGIS symbol construction with
no rendering library to lean on, unlike the point-symbol side.

The COLOURING, however, is verified directly against the standard's own
H.5.3 Coloring rule (read from the actual MIL-STD-2525D PDF, not a
paraphrase): friendly control measures in black or blue, hostile in red.
This module uses the same "affiliation" vocabulary as sidc.py's own
AFFILIATIONS (friend/hostile/neutral/unknown) and colours friend=blue,
hostile=red, neutral/unknown=black (black is also the default affiliation,
matching "black as standard" for a control measure with no stated
affiliation) - a data-defined colour expression applied on top of each
measure type's own shape, not a rule-tree branch per affiliation.

Two separate layers, not one, because a QgsVectorLayer is always a single
geometry type - there's no "LineString or Polygon" layer in QGIS.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ..core._layer_utils import add_layer_at_default_position
from ..core.text_format import build_text_format
from .sidc import AFFILIATIONS


LINES_LAYER_NAME = "Tactical Graphics - Control Measures (Lines)"
AREAS_LAYER_NAME = "Tactical Graphics - Control Measures (Areas)"

LABEL_FONT_SIZE = 9

LINE_MEASURE_TYPE_LABELS = {
    "phase_line": "Phase Line",
    "boundary": "Boundary",
    "axis_of_advance": "Axis of Advance",
}

AREA_MEASURE_TYPE_LABELS = {
    "objective": "Objective",
    "nai": "Named Area of Interest (NAI)",
}

# Keys match sidc.py's own AFFILIATIONS (the same "standard identity"
# concept MIL-STD-2525D uses for units) - labels are this module's own
# presentation layer, same separation-of-concerns convention as
# unit_layer.py's _AFFILIATION_LABELS.
AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

DEFAULT_AFFILIATION = "unknown"

# Per MIL-STD-2525D H.5.3 Coloring, as scoped by the user: friendly control
# measures in blue, hostile in red, everything else (neutral/unknown/the
# default) in black - "black as standard". A single shared expression
# applied to every measure type's own stroke/fill colour, rather than
# threading affiliation through each symbol builder's own parameters.
_AFFILIATION_COLOR_EXPRESSION = (
    "CASE "
    "WHEN \"affiliation\" = 'friend' THEN color_rgb(0, 0, 255) "
    "WHEN \"affiliation\" = 'hostile' THEN color_rgb(255, 0, 0) "
    "ELSE color_rgb(0, 0, 0) "
    "END"
)


def _apply_affiliation_color(symbol_layer, properties):

    """
    Makes the given symbol_layer's colour properties (e.g. StrokeColor,
    FillColor) data-defined by _AFFILIATION_COLOR_EXPRESSION, so every
    control measure's own "affiliation" attribute drives its colour
    automatically - the same data-defined-property pattern
    unit_layer.py's own SIDC rendering already uses, rather than
    QgsRuleBasedRenderer rules per affiliation (which would multiply
    the existing measure_type rule tree by every affiliation value for
    no benefit, since only colour - not shape - varies by affiliation).
    """

    color_property = QgsProperty.fromExpression(_AFFILIATION_COLOR_EXPRESSION)

    for property_key in properties:

        symbol_layer.setDataDefinedProperty(
            property_key,
            color_property
        )


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _phase_line_symbol():

    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


def _boundary_symbol():

    # A distinctive dash-dash-dot pattern to read as "boundary" at a
    # glance rather than an ordinary line - not claimed to match the
    # spec's own exact dash ratios (see this module's own docstring).
    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.4
    )

    line_layer.setUseCustomDashPattern(
        True
    )

    line_layer.setCustomDashVector(
        [8, 2, 1, 2, 1, 2]
    )

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    return symbol


def _axis_of_advance_symbol():

    # A solid line with a filled arrowhead at its last vertex, pointing
    # in the drawn direction of advance.
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.5",
        }
    )

    # "arrowhead" is a stroke-only shape (no fillable interior), so its
    # boldness comes entirely from outline_width - the createSimple()
    # default is outline_width=0, which Qt draws as a 1-device-pixel
    # cosmetic hairline regardless of zoom, reading as too faint next to
    # the 0.5mm line it caps. Set explicitly, heavier than the line
    # itself so the arrowhead reads clearly.
    arrow_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "arrowhead",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.8",
            "size": "4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    _apply_affiliation_color(
        arrow_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    marker_line = QgsMarkerLineSymbolLayer()

    marker_line.setSubSymbol(
        arrow_marker
    )

    marker_line.setPlacements(
        QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
    )

    symbol.appendSymbolLayer(
        marker_line
    )

    return symbol


def _objective_symbol():

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,0,0",
            "outline_width": "0.5",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


def _nai_symbol():

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "dash",
            "outline_color": "0,0,0",
            "outline_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "phase_line": _phase_line_symbol,
    "boundary": _boundary_symbol,
    "axis_of_advance": _axis_of_advance_symbol,
}

_AREA_SYMBOL_BUILDERS = {
    "objective": _objective_symbol,
    "nai": _nai_symbol,
}


def _build_rule_based_renderer(root_symbol, symbol_builders):

    root_rule = QgsRuleBasedRenderer.Rule(None)

    for measure_type, build_symbol in symbol_builders.items():

        rule = QgsRuleBasedRenderer.Rule(
            build_symbol()
        )

        rule.setFilterExpression(
            f'"measure_type" = \'{measure_type}\''
        )

        rule.setLabel(
            measure_type
        )

        root_rule.appendChild(
            rule
        )

    return QgsRuleBasedRenderer(root_rule)


def _configure_affiliation_field(layer):

    """
    Shared by both layers - a "Friend"/"Hostile"/"Neutral"/"Unknown"
    ValueMap dropdown driving _AFFILIATION_COLOR_EXPRESSION, defaulting
    to DEFAULT_AFFILIATION ("unknown", which renders black - "black as
    standard" per the user's own scoping of this feature).
    """

    affiliation_idx = layer.fields().indexOf("affiliation")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AFFILIATION_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        affiliation_idx,
        QgsDefaultValue(f"'{DEFAULT_AFFILIATION}'")
    )


def _configure_designation_labeling(layer, placement):

    settings = QgsPalLayerSettings()

    settings.fieldName = "unique_designation"

    settings.placement = placement

    settings.setFormat(
        build_text_format(LABEL_FONT_SIZE)
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(settings)
    )

    layer.setLabelsEnabled(
        True
    )


def create_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for phase lines/boundaries/axis of
    advance - a "measure_type" ValueMap dropdown plus a
    "unique_designation" text field, labelled along each line. Digitized
    with QGIS's own native "Add Line Feature" tool - see this module's
    own docstring and unit_layer.py's for why no custom drawing tool
    exists.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"LineString?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("length_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(LINE_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'phase_line'")
    )

    _configure_affiliation_field(layer)

    # applyOnUpdate=True ("Recalculate value on update") keeps this in
    # sync as the line is reshaped, not just at initial digitizing -
    # confirmed live via QgsVectorLayerUtils.createFeature() (what the
    # GUI's own "Add Line Feature" tool calls) and via a geometry-only
    # edit through updateFeature()/commitChanges().
    layer.setDefaultValueDefinition(
        layer.fields().indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.Line
    )

    return layer


def create_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for objectives/NAIs - same shape as
    create_control_measures_lines_layer(), for area-type measures.
    Digitized with QGIS's own native "Add Polygon Feature" tool.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("area_km2", QMetaType.Type.Double),
            QgsField("perimeter_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AREA_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'objective'")
    )

    _configure_affiliation_field(layer)

    # applyOnUpdate=True - see create_control_measures_lines_layer()'s
    # own comment on length_km for why, and
    # expressions/military_symbology_functions.py's _distance_area()
    # docstring for why these expressions take only $geometry, not
    # $geometry + @layer.
    layer.setDefaultValueDefinition(
        layer.fields().indexOf("area_km2"),
        QgsDefaultValue("mct_area_km2($geometry)", True)
    )

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("perimeter_km"),
        QgsDefaultValue("mct_perimeter_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _AREA_SYMBOL_BUILDERS)
    )

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.OverPoint
    )

    return layer


def default_insert_position(project, layer):

    """
    Top of the layer tree - matches unit_layer.py's own convention for
    an operational overlay meant to sit above whatever base terrain
    rendering is underneath.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


def _add_layer_if_absent(iface, name, create_layer):

    """
    Shared guard for both add_control_measures_lines_layer()/
    add_control_measures_areas_layer() - see unit_layer.py's own
    add_unit_layer() for why a control-measures layer must never be
    silently replaced the way a generate_*() layer would be: its
    content is hand-drawn operational data, not derived from a DEM/AO,
    so a second click must warn rather than risk destroying it.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(name):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'A "{name}" layer already exists - use the Layers panel '
            "to work with it, or rename it first if you want a second "
            "one."
        )

        return None

    layer = create_layer()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )


def add_control_measures_lines_layer(iface):

    return _add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_control_measures_lines_layer
    )


def add_control_measures_areas_layer(iface):

    return _add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_control_measures_areas_layer
    )
