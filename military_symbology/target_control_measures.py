# -*- coding: utf-8 -*-

"""
Builds ready-to-use layers for MIL-STD-2525D Appendix H.5.19 (Table
H-XVII, "Target control measure symbols") - Mini-Phase H12, the twelfth
H.5.x logical group in this appendix-by-appendix pass.

**Most of this table's own point vocabulary was already present** in
sidc.py's ENTITIES["control_measure"] from an earlier pass, confirmed
by name and code rather than assumed: Point/Single Target (240601),
Nuclear Target (240602), Target-Recorded (AEGIS Only) (240603 -
confirmed against milsymbol.js's own "TP.TARGETRECORDED (AEGIS ONLY)"
entry, which really does draw the standard's own rectangle+diamond
icon - not a curation gap, just an unusually-shaped AEGIS point icon),
Fire Support Station (240900), and the whole "Field Artillery" points
sub-section (Firing Point 250100, Hide Point 250200, Launch Point
250300, Reload Point 250400, Survey Control Point 250500). Nothing new
needed there.

**Lines: 3 new measure types**, all sharing the same perpendicular
end-tick construction confirmed against each one's own EXAMPLE column
(genuine black ticks touching each end, not grey illustrative
annotation - the same per-measure-type check this appendix has used
since Phase Line's own H3 precedent): Linear Target (240701, plain,
optional name - no fixed abbreviation), Linear Smoke Target (240702,
fixed "SMOKE" second line under an optional name), Final Protective
Fire (240703, fixed centred "FPF" - its own optional weapon-type/unit
info box, Fields T1/V, dropped per this appendix's usual "extra
descriptive field box" tolerance).

**Areas: 5 new measure types**, each folding an Irregular/Rectangle/
Circular SIDC code triple into one (the same reasoning used throughout
this appendix): Area Target (240801/240802/240803, a bare name with NO
fixed prefix - unlike most other prefixed areas in this appendix,
confirmed by its own EXAMPLE column showing only a raw designation like
"PC9008"), Series or Group of Targets (240805, also a bare name -
its own template shows individual target-designator crosses inside the
boundary, each one a SEPARATE already-covered point/line/area target
feature the user places on this module's own other layers, not part of
this boundary's own drawn geometry, so only the boundary + name is
built), Smoke (240806 present/240807 planned - folds cleanly onto this
project's own existing status field, since the standard's own two codes
ARE exactly a present/planned pair, unlike this appendix's other
"genuinely separate code, not status-driven" fixed-dash constructions;
fixed "SMOKE" label plus an optional name), Bomb Area (240808, fixed
"BOMB" label, no name field in the standard's own template), Fire
Support Area (241001/241002/241003, "FSA" prefix + optional name).

**Two entries skipped outright**: **Rectangular Target - Single Target
(240804, AEGIS Only)** needs a fixed compound icon (a diamond outline
with a permanently-upright cross-target glyph centred inside) anchored
to one point with a fixed orientation regardless of the area's own
rotation - a genuinely different, AEGIS-combat-system-specific
construction from this project's usual freeform-polygon model, the
same "(AEGIS only)" curation already applied throughout H8/H9's own
Maritime Control Measures mini-phase.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Target Control Measures (Lines)"
AREAS_LAYER_NAME = "Target Control Measures (Areas)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_target_control_measures_lines_layer",
    "create_target_control_measures_areas_layer",
    "add_target_control_measures_lines_layer",
    "add_target_control_measures_areas_layer",
]

LINE_MEASURE_TYPE_LABELS = {
    "linear_target": "Linear Target",
    "linear_smoke_target": "Linear Smoke Target",
    "final_protective_fire": "Final Protective Fire (FPF)",
}

_LINE_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    "WHEN \"measure_type\" = 'linear_target' THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " WHEN \"measure_type\" = 'linear_smoke_target' THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} || '\\n' ELSE '' END"
    " || 'SMOKE'"
    " WHEN \"measure_type\" = 'final_protective_fire' THEN 'FPF'"
    " ELSE '' END"
)


def _end_tick_layer(placement):

    """
    A small perpendicular tick at each line end - the same
    QgsMarkerLineSymbolLayer "line"-shape-at-angle-0 technique already
    confirmed for maneuver_control_measures.py's own Phase Line -
    reused here since Linear Target/Linear Smoke Target/Final
    Protective Fire's own EXAMPLE columns all show the same genuine
    black end tick.
    """

    tick_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "line",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.6",
            "size": "3",
            "angle": "0",
        }
    )

    _apply_affiliation_color(
        tick_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    tick_layer = QgsMarkerLineSymbolLayer(True)

    tick_layer.setSubSymbol(
        tick_marker
    )

    tick_layer.setPlacements(
        placement
    )

    return tick_layer


def _ticked_line_symbol():

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.4
    )

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    for placement in (
        Qgis.MarkerLinePlacement.FirstVertex,
        Qgis.MarkerLinePlacement.LastVertex,
    ):

        symbol.appendSymbolLayer(
            _end_tick_layer(placement)
        )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "linear_target": _ticked_line_symbol,
    "linear_smoke_target": _ticked_line_symbol,
    "final_protective_fire": _ticked_line_symbol,
}


AREA_MEASURE_TYPE_LABELS = {
    "area_target": "Area Target",
    "series_or_group_of_targets": "Series or Group of Targets",
    "smoke": "Smoke",
    "bomb_area": "Bomb Area",
    "fire_support_area": "Fire Support Area (FSA)",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    "WHEN \"measure_type\" IN ('area_target', 'series_or_group_of_targets') THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " WHEN \"measure_type\" = 'smoke' THEN "
    "CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" {_PLAIN_DESIGNATION_LABEL_EXPRESSION} || '\\n' ELSE '' END"
    " || 'SMOKE'"
    " WHEN \"measure_type\" = 'bomb_area' THEN 'BOMB'"
    " WHEN \"measure_type\" = 'fire_support_area' THEN "
    "'FSA' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    " ELSE '' END"
)


_AREA_SYMBOL_BUILDERS = {
    "area_target": _status_driven_area_outline_symbol,
    "series_or_group_of_targets": _status_driven_area_outline_symbol,
    "smoke": _status_driven_area_outline_symbol,
    "bomb_area": _status_driven_area_outline_symbol,
    "fire_support_area": _status_driven_area_outline_symbol,
}


def create_target_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XVII's own 3 line measure
    types - see this module's own docstring for the full list.
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
            QgsField("status", QMetaType.Type.QString),
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
        QgsDefaultValue("'linear_target'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.Line,
        _LINE_DESIGNATION_LABEL_EXPRESSION
    )

    return layer


def create_target_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XVII's own 5 area measure
    types - see this module's own docstring for the full list and for
    which Irregular/Rectangle/Circular code triples were folded into
    each one.
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
            QgsField("status", QMetaType.Type.QString),
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
        QgsDefaultValue("'area_target'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

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
        Qgis.LabelPlacement.OverPoint,
        _AREA_DESIGNATION_LABEL_EXPRESSION
    )

    return layer


def add_target_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_target_control_measures_lines_layer
    )


def add_target_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_target_control_measures_areas_layer
    )
