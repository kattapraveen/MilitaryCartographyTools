# -*- coding: utf-8 -*-

"""
Builds a ready-to-use layer for MIL-STD-2525D Appendix H.5.27 (Table
H-XXV, "Intelligence control measure symbols") - Mini-Phase H22, and
the last H.5.x section of this appendix-by-appendix pass to be reached.

**The whole table is two rows and one drawable symbol**: 300000
("Intelligence Lines") is the section's own parent entry with TEMPLATE
and EXAMPLE both reading "N/A", and 300100 is the Intelligence
Coordination Line (ICL). Printed page 656, the entire section.

**ICL is constructed exactly like Battlefield Coordination Line and
Restrictive Fire Line** - the project maintainer's own instruction, and
confirmed against the template picture on both pages: a plain line
through PT1..PTn carrying its abbreviation plus the feature's own
unique designation (Field T) at BOTH ends, above the line. The
standard's own example spells it out - "ICL EUSTIS", designation
LAST, the same order NFL/BCL/RFL use and the opposite of FSCL's own
"MND(S) FSCL". So this module is deliberately the same construction
fire_support_coordination_measures.py's own _end_labelled_line_symbol()
and its start/end label pair already carry, with "ICL" as the
abbreviation; anything learned about that family (the mask, the
AboveRight/AboveLeft quadrants that stop a long designation hanging off
past the end vertex) applies here unchanged.

**The two W-W1 boxes below the line are not drawn.** They are the
effective-times fields (Field W/W1, "from" and "to" date-time groups),
and this appendix's own established tolerance throughout this project
is to keep the abbreviation - the SIDC-relevant part - and drop the
extra descriptive info boxes; see fire_support_coordination_measures.py
for where that was first reasoned out for this same both-ends label
convention, and H7's corridor family before it.

**The up-arrows at PT1 and PT2 in the TEMPLATE column are annotation
pointers, not geometry** - the standing convention in this appendix,
first confirmed for c2_measures.py's own Light Line and since then for
Boundary, H-XIX's roadblocks and H-VIII's Contain/Retain arrowheads.
Nothing is drawn at the ends but the label.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLineSymbol,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Intelligence Control Measures (Lines)"

__all__ = [
    "LINES_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "LINE_MEASURE_TYPE_CODES",
    "TABLE_H_XXV_NOT_A_SYMBOL",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_intelligence_control_measures_lines_layer",
    "add_intelligence_control_measures_lines_layer",
]

LINE_MEASURE_TYPE_LABELS = {
    "icl": "Intelligence Coordination Line (ICL)",
}

LINE_MEASURE_TYPE_CODES = {
    "icl": "300100",
}

# The table's other row. Recorded rather than dropped, so the
# arithmetic can be checked against the printed table without
# re-reading it - the same convention every other module in this
# appendix uses for its own unbuilt rows.
TABLE_H_XXV_NOT_A_SYMBOL = {
    "300000": "Intelligence Lines (section parent; TEMPLATE and "
              "EXAMPLE both N/A)",
}

_ICL_ABBREVIATION = "ICL"

# "ICL EUSTIS" - abbreviation first, designation last, per the
# standard's own example. trim() collapses the separating space away
# when the field is blank, rather than leaving "ICL " with a trailing
# gap the mask would then cut a hole for.
_LINE_LABEL_EXPRESSION = (
    f"trim('{_ICL_ABBREVIATION} ' || "
    "upper(coalesce(\"unique_designation\",'')))"
)

# Stable id so the label can cut a real gap in the line it sits on.
_ICL_SYMBOL_LAYER_ID = "icl_line"

_MASKED_LINE_SYMBOL_LAYER_IDS = [_ICL_SYMBOL_LAYER_ID]


def _icl_symbol():

    """
    Table H-XXV, code 300100. A plain line, solid when present and
    dashed when planned - status-driven like every other line in this
    appendix, not fixed, since the template shows the solid variant and
    nothing in the row makes the dash a property of the code itself.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setId(
        _ICL_SYMBOL_LAYER_ID
    )

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


_LINE_SYMBOL_BUILDERS = {
    "icl": _icl_symbol,
}


def _configure_lines_labeling(layer):

    """
    "ICL <designation>" at both ends, above the line and pushed INWARD
    from each end vertex - the same pair of rules the BCL/RFL family
    already uses, and for the same reasons: a plain Above quadrant
    centres the text ON the end vertex and hangs half of a long
    designation off past the end of the line, and the mask is what
    keeps the text readable on geometry where "above" and "clear of the
    line" are not the same thing (a near-vertical line, say).

    Both rules declare the SAME masked-id list. Masking is configured
    per QGIS layer rather than per rule, and rules declaring different
    lists make QGIS keep just one of them, arbitrarily.
    """

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for anchor, quadrant in (
        ("start_point($geometry)", Qgis.LabelQuadrantPosition.AboveRight),
        ("end_point($geometry)", Qgis.LabelQuadrantPosition.AboveLeft),
    ):

        root_rule.appendChild(
            QgsRuleBasedLabeling.Rule(
                _build_pal_layer_settings(
                    layer,
                    Qgis.LabelPlacement.OverPoint,
                    _LINE_LABEL_EXPRESSION,
                    masked_symbol_layer_ids=_MASKED_LINE_SYMBOL_LAYER_IDS,
                    label_geometry_expression=anchor,
                    quadrant=quadrant
                )
            )
        )

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


def create_intelligence_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XXV's own single drawable
    entry, the Intelligence Coordination Line.
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
        QgsDefaultValue("'icl'")
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

    _configure_lines_labeling(layer)

    return layer


def add_intelligence_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_intelligence_control_measures_lines_layer
    )
