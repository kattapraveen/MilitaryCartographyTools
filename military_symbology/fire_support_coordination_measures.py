# -*- coding: utf-8 -*-

"""
Builds ready-to-use layers for MIL-STD-2525D Appendix H.5.18 (Table
H-XVI, "Fire Support Coordination Measures") - Mini-Phase H11, the
eleventh H.5.x logical group in this appendix-by-appendix pass.

The table's own intro text sets a general rule applying to every entry
here: "Fire support control measures should be labeled with the
abbreviation of the control measure, the controlling headquarters
(Field T) and the effective times (Field W/W1). For lines this
labeling should be on both ends of the line and repeated as often as
necessary for clarity along any line that passes through many
boundaries." This module keeps the abbreviation (the SIDC-relevant
part) and drops the controlling-headquarters/effective-times info
boxes, the same "extra descriptive field box" tolerance already used
throughout this appendix (H7's corridor family, H8/H9's Bearing Line
family) - and keeps the abbreviation ONCE (centred, or once per end)
rather than literally repeating along a line crossing many boundaries,
the same simplification already used for c2_measures.py's own Boundary.

**Areas: 5 measure types, each folding an Irregular/Rectangle/Circular
triple of separate SIDC codes into ONE measure type** (the same "these
render pixel-identically once only the boundary shape differs, and this
project already lets the user draw whatever boundary shape they want"
reasoning applied throughout this appendix - see maneuver_control_
measures.py's own AA/DZ/EZ/LZ/PZ precedent): Airspace Coordination Area
(240101/240102/240103, "ACA"), Free Fire Area (240201/240202/240203,
"FFA"), No Fire Area (240301/240302/240303, "NFA" - the only one with a
genuine HATCHED FILL, per its own template, the second area in this
whole appendix-by-appendix pass needing one after H7's Weapons Free
Zone), Restricted Fire Area (240401/240402/240403, "RFA"), Position Area
For Artillery (240501/240502, "PAA" - only Rectangular/Circular, no
Irregular variant in the standard's own table).

**Lines: 6 measure types**, split into two label conventions confirmed
by reading each one's own template picture (not assumed from the
family's shared "abbreviation" framing): Fire Support Coordination Line
("FSCL", 260100), No Fire Line ("NFL", 260300), Battlefield Coordination
Line ("BCL", 260400), and Restrictive Fire Line ("RFL", 260500) all show
their abbreviation at BOTH ends (the `_end_label_layer()` fixed-marker
technique used throughout this appendix); Coordinated Fire Line ("CFL",
260200) and Munition Flight Path ("MFP", 260600) both show a single
label CENTRED along the line instead (the same `Qgis.LabelPlacement.
Line` technique already used for maneuver_control_measures_2.py's own
Airhead Line and this appendix's own corridor/route family). **CFL is
also the one line in this whole family drawn DASHED as a fixed property
of the code itself, not status-driven** - confirmed by its own template
and example both showing a dashed line with no solid variant, the same
fixed-dash construction already used for offensive_control_measures.py's
own Probable Line of Deployment, maritime_control_measures.py's own
Bearing Line Acoustic (Ambiguous), and deception_control_measures.py's
own Decoy/Dummy.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLinePatternFillSymbolLayer,
    QgsLineSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, Qt
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
    _end_label_layer,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Fire Support Coordination Measures (Lines)"
AREAS_LAYER_NAME = "Fire Support Coordination Measures (Areas)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_fire_support_coordination_measures_lines_layer",
    "create_fire_support_coordination_measures_areas_layer",
    "add_fire_support_coordination_measures_lines_layer",
    "add_fire_support_coordination_measures_areas_layer",
]

LINE_MEASURE_TYPE_LABELS = {
    "fscl": "Fire Support Coordination Line (FSCL)",
    "cfl": "Coordinated Fire Line (CFL)",
    "nfl": "No Fire Line (NFL)",
    "bcl": "Battlefield Coordination Line (BCL)",
    "rfl": "Restrictive Fire Line (RFL)",
    "mfp": "Munition Flight Path (MFP)",
}

_CENTRED_LABEL_CHARACTERS = {
    "cfl": "CFL",
    "mfp": "MFP",
}

_LINE_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN '{character}'"
    for measure_type, character in _CENTRED_LABEL_CHARACTERS.items()
) + " ELSE '' END"


def _end_labelled_line_symbol(character):

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
            _end_label_layer(placement, character)
        )

    return symbol


def _mfp_symbol():

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

    return symbol


def _cfl_symbol():

    """
    Table H-XVI, code 260200, page 522. Always dashed, as a fixed
    property of the code itself - see module docstring.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.4
    )

    line_layer.setPenStyle(
        Qt.PenStyle.DashLine
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


_LINE_SYMBOL_BUILDERS = {
    "fscl": lambda: _end_labelled_line_symbol("FSCL"),
    "cfl": _cfl_symbol,
    "nfl": lambda: _end_labelled_line_symbol("NFL"),
    "bcl": lambda: _end_labelled_line_symbol("BCL"),
    "rfl": lambda: _end_labelled_line_symbol("RFL"),
    "mfp": _mfp_symbol,
}


AREA_MEASURE_TYPE_LABELS = {
    "aca": "Airspace Coordination Area (ACA)",
    "ffa": "Free Fire Area (FFA)",
    "nfa": "No Fire Area (NFA)",
    "rfa": "Restricted Fire Area (RFA)",
    "paa": "Position Area For Artillery (PAA)",
}

_AREA_LABEL_PREFIXES = {
    "aca": "ACA",
    "ffa": "FFA",
    "nfa": "NFA",
    "rfa": "RFA",
    "paa": "PAA",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN "
    f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" '\\n' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
) + " ELSE '' END"


def _nfa_symbol():

    """
    Table H-XVI, code 240301/240302/240303, pages 514-516. The one
    hatched-fill area in this mini-phase - "Note: Upward diagonal lines
    are part of the fill" (matching H7's own Weapons Free Zone note
    exactly) - built the same way, a QgsLinePatternFillSymbolLayer on
    top of the usual status-driven outline.
    """

    symbol = _status_driven_area_outline_symbol()

    hatch_layer = QgsLinePatternFillSymbolLayer()

    hatch_layer.setLineAngle(
        45
    )

    hatch_layer.setDistance(
        2.5
    )

    hatch_layer.setLineWidth(
        0.2
    )

    hatch_layer.setColor(
        QColor(0, 0, 0)
    )

    _apply_affiliation_color(
        hatch_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol.appendSymbolLayer(
        hatch_layer
    )

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "aca": _status_driven_area_outline_symbol,
    "ffa": _status_driven_area_outline_symbol,
    "nfa": _nfa_symbol,
    "rfa": _status_driven_area_outline_symbol,
    "paa": _status_driven_area_outline_symbol,
}


def create_fire_support_coordination_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XVI's own 6 line measure
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
        QgsDefaultValue("'fscl'")
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


def create_fire_support_coordination_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XVI's own 5 area measure
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
        QgsDefaultValue("'ffa'")
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


def add_fire_support_coordination_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_fire_support_coordination_measures_lines_layer
    )


def add_fire_support_coordination_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_fire_support_coordination_measures_areas_layer
    )
