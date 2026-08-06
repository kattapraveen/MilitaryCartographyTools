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
docs/roadmap.md's Phase 10 entry). The styling below is a hand-authored,
practically-recognisable approximation of the standard conventions
(dashed/dotted boundary lines, an arrowhead for axis of advance, dashed
outlines for NAIs) rather than a verified-correct rendition of the
written specification - flagged here plainly rather than implied to be
as exact as the point-symbol side of Phase 10.

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
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ..core._layer_utils import add_layer_at_default_position
from ..core.text_format import build_text_format


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


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _phase_line_symbol():

    return QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.4",
        }
    )


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

    arrow_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "arrowhead",
            "color": "0,0,0",
            "size": "4",
        }
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

    return QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,0,0",
            "outline_width": "0.5",
        }
    )


def _nai_symbol():

    return QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "dash",
            "outline_color": "0,0,0",
            "outline_width": "0.4",
        }
    )


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
            QgsField("unique_designation", QMetaType.Type.QString),
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
            QgsField("unique_designation", QMetaType.Type.QString),
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
