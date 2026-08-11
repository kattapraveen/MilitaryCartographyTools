# -*- coding: utf-8 -*-

"""
Builds a ready-to-use layer for MIL-STD-2525D Appendix H.5.16 (Table
H-XIV, "Maritime control measures") - Mini-Phase H8/H9, the eighth
H.5.x logical group in this appendix-by-appendix pass.

**Lines only - Table H-XIV has no Areas section at all.** Its own text
reads "maritime control measures can be broken down into the following
groups: points, lines and areas", but the actual table content ends
(H.5.17/Table H-XV, Deception, begins immediately after the last line
entry) without ever reaching an "Areas" heading the way every other
H.5.x section so far has had one.

**Only the Bearing Line family (9 types, codes 220100-220108) is built
here** - a simple 2-point line with a fixed abbreviation centred along
it (via the general designation-label system, the same technique
Airhead Line and this appendix's own corridor/route family already
use): Bearing Line ("B"), Electronic ("E"), Electronic Warfare ("EW"),
Acoustic ("A"), Acoustic (Ambiguous) ("A", always dashed - a genuinely
separate SIDC code from plain Acoustic, not a status variant, the same
"fixed dash regardless of status" construction already used for
offensive_control_measures.py's own Probable Line of Deployment),
Torpedo ("T"), Electro-Optical Intercept ("O"), Jammer ("J"), and Radio
Detention Finder ("RDF"). Every variant's own template also shows an
optional "H" identifier box near one end (e.g. "MSL"/"MCU"/"TENT" for
Electronic Warfare, "L3-ACT"/"L3-pHELO"/etc. for Acoustic, "PAT-1" for
Jammer) - dropped here, the same "extra descriptive field box" tolerance
already applied to this appendix's WIDTH/altitude/DTG fields (H7's
corridor family) rather than modelling a different fixed vocabulary per
sub-type for one small label.

**Everything else in Table H-XIV is deliberately out of scope** - this
table turned out to be overwhelmingly Navy-AEGIS-combat-system-specific
or anti-submarine-warfare/sonar-specific, not general-purpose maritime
control measures:

- **The whole "(AEGIS only)" family of fixed-graphic overlay
  constructs** - Launch Area (200101/200102, Ellipse/Rectangle), Defended
  Area (200201/200202), No Attack (NOTACK) Zone (200300), Ship Area of
  Interest (200400 grid-heatmap/200401 Ellipse/200402 Rectangle), Active
  Maneuver Area (200500), Cued Acquisition Doctrine (200600), Radar
  Search Doctrine (200700). Confirmed by reading every one of their own
  template pictures: these are AEGIS naval combat system display
  overlays with specific fixed colours/fills/orientations (not this
  project's usual freeform-polygon or simple-line model), a genuinely
  different, narrow display category this project doesn't otherwise
  build toward.
- **The entire anti-submarine-warfare/sonar-contact-point family**
  (roughly codes 211000-213399: Launched Torpedo, Acoustic Countermeasure
  (Decoy), Electronic Countermeasures (ECM) Decoy, BT Buoy Drop, Reported
  Bottomed Sub, Moving Haven, Acoustic/Electromagnetic/MAD Fix, and
  similar) and **the entire Sonobuoys sub-section** (codes 213500+:
  Sonobuoy, Ambient Noise Sonobuoy, ATAC, Barra, and further sonobuoy
  sub-types) - the same "more Navy/anti-submarine-warfare-specific ones
  (sonobuoy types and similar)" category this project's own
  control_measure_points.py docstring already documents as curated out
  of the base ENTITIES["control_measure"] vocabulary; this mini-phase
  applies that same standing curation decision rather than reversing it.
- A curated subset of the remaining, genuinely general-purpose maritime
  points (Plan Ship, Aim Point, Defended Asset, Drop Point, Entry Point,
  Air Detonation, Ground Zero, Impact Point, Predicted Impact Point,
  Missile Detection Point, Brief Contact, Datum Lost Contact,
  Navigational Reference Point) WAS added, directly to sidc.py's
  ENTITIES["control_measure"] and control_measure_points.py's own
  _ENTITY_LABELS - the same "point control measures belong to the
  shared, milsymbol-rendered Control Measure Points layer" precedent as
  every other H-subphase's own point vocabulary.

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
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, Qt
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Maritime Control Measures (Lines)"

__all__ = [
    "LINES_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_maritime_control_measures_lines_layer",
    "add_maritime_control_measures_lines_layer",
]

# Table H-XIV, codes 220100-220108 - see module docstring for the much
# larger AEGIS/ASW-sonar/Sonobuoy family deliberately left out.
LINE_MEASURE_TYPE_LABELS = {
    "bearing_line": "Bearing Line (B)",
    "bearing_line_electronic": "Bearing Line, Electronic (E)",
    "bearing_line_electronic_warfare": "Bearing Line, Electronic Warfare (EW)",
    "bearing_line_acoustic": "Bearing Line, Acoustic (A)",
    "bearing_line_acoustic_ambiguous": "Bearing Line, Acoustic (Ambiguous)",
    "bearing_line_torpedo": "Bearing Line, Torpedo (T)",
    "bearing_line_electro_optical_intercept": "Bearing Line, Electro-Optical Intercept (O)",
    "bearing_line_jammer": "Bearing Line, Jammer (J)",
    "bearing_line_rdf": "Bearing Line, Radio Detention Finder (RDF)",
}

_LINE_LABEL_CHARACTERS = {
    "bearing_line": "B",
    "bearing_line_electronic": "E",
    "bearing_line_electronic_warfare": "EW",
    "bearing_line_acoustic": "A",
    "bearing_line_acoustic_ambiguous": "A",
    "bearing_line_torpedo": "T",
    "bearing_line_electro_optical_intercept": "O",
    "bearing_line_jammer": "J",
    "bearing_line_rdf": "RDF",
}

_LINE_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN '{character}'"
    for measure_type, character in _LINE_LABEL_CHARACTERS.items()
) + " ELSE '' END"


def _bearing_line_symbol():

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


def _bearing_line_acoustic_ambiguous_symbol():

    """
    Table H-XIV, code 220104, page 503. A genuinely separate SIDC code
    from plain Acoustic (220103), always drawn dashed regardless of
    "status" - the same fixed-dash construction already used for
    offensive_control_measures.py's own Probable Line of Deployment.
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
    "bearing_line": _bearing_line_symbol,
    "bearing_line_electronic": _bearing_line_symbol,
    "bearing_line_electronic_warfare": _bearing_line_symbol,
    "bearing_line_acoustic": _bearing_line_symbol,
    "bearing_line_acoustic_ambiguous": _bearing_line_acoustic_ambiguous_symbol,
    "bearing_line_torpedo": _bearing_line_symbol,
    "bearing_line_electro_optical_intercept": _bearing_line_symbol,
    "bearing_line_jammer": _bearing_line_symbol,
    "bearing_line_rdf": _bearing_line_symbol,
}


def create_maritime_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XIV's own Bearing Line family
    - see this module's own docstring for the full list and for
    everything scoped out of this mini-phase.
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
        QgsDefaultValue("'bearing_line'")
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


def add_maritime_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_maritime_control_measures_lines_layer
    )
