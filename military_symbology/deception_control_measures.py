# -*- coding: utf-8 -*-

"""
Builds a ready-to-use layer for MIL-STD-2525D Appendix H.5.17 (Table
H-XV, "Deception control measure symbols") - Mini-Phase H10, the
smallest H.5.x logical group in this appendix-by-appendix pass: exactly
one drawable symbol.

**Decoy/Dummy (230100) is the only entry built here** - a 3-point line
(PT2 -> PT1 -> PT3, the vertex at PT1) drawn as two dashed segments
forming a "tent"/chevron shape, the same 3-point-line-from-a-shared-
vertex construction already used repeatedly elsewhere in this appendix
(maneuver_control_measures.py's own Principal Direction of Fire,
maneuver_control_measures_2.py's own Search Area/Reconnaissance Area) -
just without arrowheads. **Always drawn dashed**, not status-driven -
the standard's own template and example both show it dashed with no
solid variant anywhere, consistent with a decoy/dummy being inherently
a simulated, not-actually-occupied construct; the same fixed-dash
technique already used for offensive_control_measures.py's own Probable
Line of Deployment (H5) and maritime_control_measures.py's own Bearing
Line, Acoustic (Ambiguous) (H8/H9). **No label at all** - the standard's
own EXAMPLE column shows an information box with 3 grey circle icons
inside (representing whatever is being decoyed, e.g. a vehicle or
antenna type), entirely grey, matching this appendix's own established
"grey in the EXAMPLE column is illustrative-only, not drawn geometry"
convention (see c2_measures.py's own Light Line docstring for where
that convention was first confirmed) - so nothing in that box is
modelled here.

**Everything else in Table H-XV is either a cross-reference to a symbol
already built elsewhere, or a forward-reference to a symbol that
belongs in a later table - neither needs new code in this module**:

- **Decoy/Dummy and Feint (230200)** is explicitly a MODIFIER whose own
  "anchor points are determined by the relationship between the control
  measure symbol being modified and the decoy/dummy or feint control
  measure symbol modifying it" (the standard's own text) - it overlays
  another, separately-drawn control measure rather than standing alone,
  the same "doesn't fit this project's one-feature-one-symbol model"
  reasoning already applied to every other compound/cross-referencing
  construct skipped elsewhere in this appendix (H3's Occupied Assembly
  Area w/ Offset Unit, H4's Contain/Retain, H6's Attack By Fire
  Position/Ambush). Not built.
- **Axis of Advance for a Feint** and **Direction of Attack for a
  Feint** are the standard's own explicit cross-references ("See Axis
  of Advance under Maneuver Control Measures") to symbols this project
  already built in Mini-Phase H5 - offensive_control_measures.py's own
  `axis_of_advance_feint`/`direction_of_attack_feint` measure types.
  Nothing new needed here.
- **Decoy Mined Area** and **Dummy Minefield** are both the standard's
  own explicit forward-reference ("See Decoy Mined Area under
  Obstacles") to Table H-XIX (H.5.21, Mini-Phase H15/H16, not yet
  reached in this pass). Deferred to that mini-phase, not built here.

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsLineSymbol,
    QgsProject,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, Qt
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Deception Control Measures (Lines)"

__all__ = [
    "LINES_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "create_deception_control_measures_lines_layer",
    "add_deception_control_measures_lines_layer",
]

# Table H-XV, code 230100 - see module docstring for why this is the
# ONLY entry (everything else is a cross-reference or a modifier
# construct that doesn't fit this project's own techniques).
LINE_MEASURE_TYPE_LABELS = {
    "decoy_dummy": "Decoy/Dummy",
}


def _decoy_dummy_symbol():

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
    "decoy_dummy": _decoy_dummy_symbol,
}


def create_deception_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XV's own single drawable
    entry (Decoy/Dummy) - see this module's own docstring for why
    everything else in the table needs no new code.
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
        QgsDefaultValue("'decoy_dummy'")
    )

    _configure_affiliation_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    return layer


def add_deception_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_deception_control_measures_lines_layer
    )
