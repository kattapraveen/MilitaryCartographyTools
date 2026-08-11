# -*- coding: utf-8 -*-

"""
Builds a ready-to-use layer for MIL-STD-2525D Appendix H.5.20 (Table
H-XVIII, "Target acquisition control measure symbols") - Mini-Phase
H13/H14, the thirteenth H.5.x logical group in this appendix-by-
appendix pass.

**Areas only - 11 measure types, every one of them the identical
"freeform outline + prefix + optional name" construction already
proven throughout this appendix**, each folding a separate Irregular/
Rectangle/Circular SIDC code triple into one measure type (the same
reasoning used throughout - these render pixel-identically once only
the boundary shape differs): Artillery Target Intelligence Zone
(241101/102/103, "ATI"), Call For Fire Zone (241201/202/203, "CFF
ZONE" - the standard's own template text, not "CFFZ"), Censor Zone
(241301/302/303, "CENSOR ZONE"), Critical Friendly Zone (241401/402/
403, "CF ZONE"), Dead Space Area (241501/502/503, "DA"), Sensor Zone
(241601/602/603, "SENSOR ZONE"), Target Build-up Area (241701/702/703,
"TBA"), Target Value Area (241801/802/803, "TVAR"), Zone of
Responsibility (241901/902/903, "ZOR"), Blue Kill Box (242301/302/303,
"BKB"), Purple Kill Box (242304/305/306, "PKB"). The prefix text is
kept exactly as each measure type's own template/example shows it,
rather than forced onto one uniform abbreviation scheme - the standard
itself is inconsistent here (some spell the word "ZONE" out, others
don't).

**Two entries skipped outright**: **Weapon/Sensor Range Fan - Circular
(242100)** and **Weapon/Sensor Range Fan - Sector (242200)** both need
genuinely parametric/computed geometry from a single anchor point - one
or more concentric range RINGS (Circular) or a pie-shaped SECTOR with
an azimuth-defined centreline plus left/right limits and multiple range
arcs (Sector) - not a freeform polygon a user directly digitizes. The
same "doesn't fit this project's own techniques" reasoning already
applied to H4's Contain/Retain (also a computed-circle construct).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsProject,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _build_rule_based_renderer,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


AREAS_LAYER_NAME = "Target Acquisition Control Measures (Areas)"

__all__ = [
    "AREAS_LAYER_NAME",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_target_acquisition_control_measures_areas_layer",
    "add_target_acquisition_control_measures_areas_layer",
]

AREA_MEASURE_TYPE_LABELS = {
    "ati": "Artillery Target Intelligence Zone (ATI)",
    "cffz": "Call For Fire Zone (CFFZ)",
    "censor_zone": "Censor Zone",
    "cfz": "Critical Friendly Zone (CFZ)",
    "dead_space_area": "Dead Space Area (DA)",
    "sensor_zone": "Sensor Zone",
    "tba": "Target Build-up Area (TBA)",
    "tvar": "Target Value Area (TVAR)",
    "zor": "Zone of Responsibility (ZOR)",
    "blue_kill_box": "Blue Kill Box (BKB)",
    "purple_kill_box": "Purple Kill Box (PKB)",
}

_AREA_LABEL_PREFIXES = {
    "ati": "ATI",
    "cffz": "CFF ZONE",
    "censor_zone": "CENSOR ZONE",
    "cfz": "CF ZONE",
    "dead_space_area": "DA",
    "sensor_zone": "SENSOR ZONE",
    "tba": "TBA",
    "tvar": "TVAR",
    "zor": "ZOR",
    "blue_kill_box": "BKB",
    "purple_kill_box": "PKB",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN "
    f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" '\\n' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
) + " ELSE '' END"

_AREA_SYMBOL_BUILDERS = {
    measure_type: _status_driven_area_outline_symbol
    for measure_type in AREA_MEASURE_TYPE_LABELS
}


def create_target_acquisition_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XVIII's own 11 zone/box
    measure types - see this module's own docstring for the full list
    and for the two entries skipped (both Weapon/Sensor Range Fan
    variants).
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
        QgsDefaultValue("'ati'")
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


def add_target_acquisition_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_target_acquisition_control_measures_areas_layer
    )
