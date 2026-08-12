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
Detention Finder ("RDF").

**All three of this table's own labelling requirements were reworked
2026-08-12** after the maintainer's own live testing ("all the lines are
rendered fine, just three issues"), and they are why this module builds
its own _configure_lines_labeling() instead of calling the shared
_configure_designation_labeling() the way it used to:

- The abbreviation is **upright at all times** rather than rotated to
  follow the line - Qgis.LabelPlacement.Horizontal, not .Line. On a
  right-to-left or steeply descending bearing the old rotated label
  came out upside-down.
- It is **masked**, so the line no longer draws straight through the
  glyph.
- Every variant's own template also shows an optional "H" identifier
  box near one end (e.g. "MSL"/"MCU"/"TENT" for Electronic Warfare,
  "L3-ACT"/"L3-pHELO"/etc. for Acoustic, "PAT-1" for Jammer). That was
  dropped when this mini-phase was first built - the same "extra
  descriptive field box" tolerance applied to H7's own WIDTH/altitude/
  DTG fields - and is now **a "unique_designation" free-text field**,
  labelled at the line's own end, below-right, also upright. Free text
  rather than nine fixed per-sub-type vocabularies, which is what made
  it look not worth modelling the first time round.

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
    QgsRuleBasedLabeling,
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
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
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

# The optional identifier the template shows in a box near the PT2 end
# ("MSL"/"MCU"/"TENT" for Electronic Warfare, "PAT-1" for Jammer, and
# similar). Dropped when this mini-phase was first built - see the
# module docstring's own "extra descriptive field box" note - and added
# 2026-08-12 on the maintainer's own instruction: "there should be an
# option for unique designator which will be place at the end - bottom
# right of the line, also oriented straight". Free text rather than the
# fixed per-sub-type vocabulary the template's own examples come from,
# which is why it is one shared field and not nine.
#
# upper(...) per H.5.4's "all text labeling shall be in upper case".
_LINE_UNIQUE_DESIGNATION_LABEL_EXPRESSION = (
    "upper(coalesce(\"unique_designation\",''))"
)

# Stable ids so the abbreviation's own label can cut a real gap in the
# line it sits on, via QGIS's own Selective Masking - the maintainer's
# own second point on this table, "should be masked so that the line is
# not cutting through the letter". Both builders need one: masking is
# configured layer-wide against a LIST of symbol layer ids, so a type
# whose id is missing would simply keep drawing through its own label.
_BEARING_LINE_SYMBOL_LAYER_ID = "bearing_line"
_BEARING_LINE_AMBIGUOUS_SYMBOL_LAYER_ID = "bearing_line_acoustic_ambiguous"

_MASKED_LINE_SYMBOL_LAYER_IDS = [
    _BEARING_LINE_SYMBOL_LAYER_ID,
    _BEARING_LINE_AMBIGUOUS_SYMBOL_LAYER_ID,
]


def _bearing_line_symbol():

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setId(
        _BEARING_LINE_SYMBOL_LAYER_ID
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


def _bearing_line_acoustic_ambiguous_symbol():

    """
    Table H-XIV, code 220104, page 503. A genuinely separate SIDC code
    from plain Acoustic (220103), always drawn dashed regardless of
    "status" - the same fixed-dash construction already used for
    offensive_control_measures.py's own Probable Line of Deployment.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setId(
        _BEARING_LINE_AMBIGUOUS_SYMBOL_LAYER_ID
    )

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


def _configure_lines_labeling(layer):

    """
    Two labels per feature, so two QgsRuleBasedLabeling rules - the
    abbreviation ("B"/"E"/"EW"/...) centred along the line, and the
    optional unique designation at the line's own end. All three of the
    maintainer's own 2026-08-12 points on this table land here:

    - **Upright at all times.** Both rules avoid
      Qgis.LabelPlacement.Line, which rotates its label to follow the
      feature - the abbreviation uses Horizontal (QGIS's own "along the
      line, but text stays level" mode) and the designation uses
      OverPoint against the line's own end vertex.
    - **Masked**, so the line no longer draws straight through the
      glyphs. The abbreviation sits ON the line (OnLine flag, the
      shared default), which is exactly the case Selective Masking
      exists for.
    - **Unique designation at the end, bottom right.** OverPoint
      placement against a label geometry of `end_point($geometry)`,
      with the BelowRight quadrant hanging the text down-and-right off
      that vertex. The standard's own template puts its "H" box just
      ABOVE the PT2 end instead; below-right is the maintainer's own
      explicit call ("place at the end - bottom right of the line").

    Both rules are given the SAME masked-id list even though only the
    abbreviation actually sits on a line. Masking is configured per
    QGIS layer, not per rule, and rules declaring DIFFERENT lists make
    QGIS log "Different sets of symbol layers are masked by different
    sources! Only one (arbitrary) set will be retained!" and silently
    keep just one of them - so they have to agree.
    """

    abbreviation_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Horizontal,
            _LINE_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_LINE_SYMBOL_LAYER_IDS
        )
    )

    designation_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _LINE_UNIQUE_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_LINE_SYMBOL_LAYER_IDS,
            label_geometry_expression="end_point($geometry)",
            quadrant=Qgis.LabelQuadrantPosition.BelowRight
        )
    )

    # Without this the rule still runs for features that left the field
    # blank, and QGIS reserves the empty label's own space - which
    # collides with the abbreviation's placement search on short lines.
    designation_rule.setFilterExpression(
        "coalesce(\"unique_designation\",'') != ''"
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(
        abbreviation_rule
    )

    root_rule.appendChild(
        designation_rule
    )

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


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

    _configure_lines_labeling(layer)

    return layer


def add_maritime_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_maritime_control_measures_lines_layer
    )
