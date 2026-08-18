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
their abbreviation at BOTH ends; Coordinated Fire Line ("CFL", 260200)
and Munition Flight Path ("MFP", 260600) both show a single label
CENTRED along the line instead.

**Every one of those labels carries the feature's own unique
designation, and every one is masked** - reworked 2026-08-12 from the
maintainer's own live testing of the whole family. The designation's
POSITION relative to the abbreviation is per-type, read off each
template: FSCL puts it FIRST ("MND(S) FSCL" in the standard's own
example), NFL/BCL/RFL/CFL put it LAST ("NFL II CORPS", "BCL III MEF",
"CFL 52ID (M)"), and MFP has no designation box at all. CFL sits above
the centre of its line; MFP stays on the line where its own template
draws it, and only needed the mask. See _configure_lines_labeling(),
which replaced the shared single-label call with a rule tree - and note
that the both-ends pair could not stay as _end_label_layer() font
markers, because a marker's character is fixed when the symbol is built
and cannot read a feature's own fields. **CFL is
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
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
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

# Where each measure type's own unique designation (Field T) sits
# relative to its abbreviation, read straight off each template picture
# (page 521-523) and confirmed by the maintainer's own live testing:
# FSCL puts the designation FIRST ("MND(S) FSCL" in the standard's own
# example), every other labelled type puts it LAST ("NFL II CORPS",
# "BCL III MEF", "CFL 52ID (M)"). Munition Flight Path has no Field T
# box in its own template at all - just the fixed "MFP".
_LINE_LABEL_ABBREVIATIONS = {
    "fscl": "FSCL",
    "cfl": "CFL",
    "nfl": "NFL",
    "bcl": "BCL",
    "rfl": "RFL",
    "mfp": "MFP",
}

_DESIGNATION_PREFIXED_TYPES = ("fscl",)

_UNDESIGNATED_TYPES = ("mfp",)


def _line_label_expression(measure_type):

    """
    "<designation> FSCL" for FSCL, "NFL <designation>" for the rest,
    and the bare abbreviation for whichever types take no designation
    or whose own field was left blank. trim() collapses the separating
    space away in that blank case rather than leaving "NFL " with a
    trailing gap the mask would then cut a hole for.
    """

    abbreviation = _LINE_LABEL_ABBREVIATIONS[measure_type]

    if measure_type in _UNDESIGNATED_TYPES:
        return f"'{abbreviation}'"

    designation = "upper(coalesce(\"unique_designation\",''))"

    if measure_type in _DESIGNATION_PREFIXED_TYPES:
        return f"trim({designation} || ' {abbreviation}')"

    return f"trim('{abbreviation} ' || {designation})"


_LINE_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN "
    + _line_label_expression(measure_type)
    for measure_type in _LINE_LABEL_ABBREVIATIONS
) + " ELSE '' END"

# Which types put that label at BOTH ENDS rather than once in the
# middle - the template pictures again: FSCL/NFL/BCL/RFL all draw it
# twice, once near each of PT1 and PT2, while CFL and MFP each draw it
# once at the centre (MFP's own Note 1 says so in as many words:
# "'MFP' shall be displayed once at the approximate center").
_END_LABELLED_TYPES = ("fscl", "nfl", "bcl", "rfl")

_CENTRE_LABELLED_TYPES = ("cfl", "mfp")


def _measure_type_filter(measure_types):

    return " OR ".join(
        f"\"measure_type\" = '{measure_type}'"
        for measure_type in measure_types
    )


# Stable ids so every one of these lines can have its own label cut a
# real gap in it. Masking is configured layer-wide against a LIST, so a
# type whose id is missing here would keep drawing through its own text.
_FSCL_FAMILY_SYMBOL_LAYER_ID = "fscl_family_line"
_CFL_SYMBOL_LAYER_ID = "cfl_line"
_MFP_SYMBOL_LAYER_ID = "mfp_line"

_MASKED_LINE_SYMBOL_LAYER_IDS = [
    _FSCL_FAMILY_SYMBOL_LAYER_ID,
    _CFL_SYMBOL_LAYER_ID,
    _MFP_SYMBOL_LAYER_ID,
]


def _end_labelled_line_symbol():

    """
    FSCL/NFL/BCL/RFL. Until 2026-08-12 this appended a fixed-character
    font marker at each end via _end_label_layer() - which could only
    ever draw the bare abbreviation, since a marker's character is
    fixed at build time and cannot read the feature's own fields. The
    text now comes from a pair of real PAL labels instead (see
    _configure_lines_labeling()), so the designation can ride along
    with it; this builds the plain line only.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setId(
        _FSCL_FAMILY_SYMBOL_LAYER_ID
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


def _mfp_symbol():

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setId(
        _MFP_SYMBOL_LAYER_ID
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


def _cfl_symbol():

    """
    Table H-XVI, code 260200, page 522. Always dashed, as a fixed
    property of the code itself - see module docstring.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setId(
        _CFL_SYMBOL_LAYER_ID
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
    "fscl": _end_labelled_line_symbol,
    "cfl": _cfl_symbol,
    "nfl": _end_labelled_line_symbol,
    "bcl": _end_labelled_line_symbol,
    "rfl": _end_labelled_line_symbol,
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


# Stable ids so these areas' own labels can cut real gaps via QGIS
# Selective Masking. Only two of the five need one: No Fire Area is the
# only type here with a FILL for a label to disappear into, and
# Position Area For Artillery is the only one whose labels sit ON the
# outline rather than inside the shape.
_NFA_HATCH_SYMBOL_LAYER_ID = "nfa_hatch"
_PAA_OUTLINE_SYMBOL_LAYER_ID = "paa_outline"

_MASKED_AREA_SYMBOL_LAYER_IDS = [
    _NFA_HATCH_SYMBOL_LAYER_ID,
    _PAA_OUTLINE_SYMBOL_LAYER_ID,
]

# Position Area For Artillery draws "PAA" at FOUR points around its own
# perimeter - top, bottom, left and right - not once in the middle like
# every other area in this table. Straight off its own template
# (page 521, the Circular variant), and the maintainer's own words:
# "the text PAA should be in all four directions - top, bottom, right
# and left along the perimeter of the area made".
#
# Each anchor targets the midpoint of one bounding-box edge, then
# snaps to the CLOSEST point on the polygon's own boundary to it -
# exact for both shapes the standard actually allows here (PAA is
# Rectangle or Circular only, with no Irregular variant in its own
# table: for either, the bounding-box edge midpoint already sits
# exactly on the boundary, so the snap is a no-op) and still correct
# for whatever a real user actually digitizes. 2026-08-18, the
# maintainer's own smoke test: "the text is not always on the
# perimeter line, sometimes it goes out of the area also especially
# in irregular polygons" - the standard's own restriction to two
# shapes does not stop QGIS's own digitizing tools from drawing a
# third, and a raw bounding-box point (the original version here) can
# fall outside a concave or otherwise irregular boundary entirely.
# closest_point(boundary($geometry), ...) is exactly
# mct_area_label_anchor()'s own reason for existing (H7's freeform
# zones), applied here as a targeted point snap instead of that
# function's own top-left-corner clip, since PAA's four anchors need
# to land ON the perimeter, not inside the shape. The bounding box is
# used for the TARGET rather than centroid(), which would wander off
# the two axes on a rotated rectangle.
_PAA_MID_X = "(x_min($geometry) + x_max($geometry)) / 2"
_PAA_MID_Y = "(y_min($geometry) + y_max($geometry)) / 2"


def _paa_anchor(target_point_expression):

    return (
        f"closest_point(boundary($geometry), {target_point_expression})"
    )


_PAA_PERIMETER_ANCHORS = (
    _paa_anchor(f"make_point({_PAA_MID_X}, y_max($geometry))"),
    _paa_anchor(f"make_point({_PAA_MID_X}, y_min($geometry))"),
    _paa_anchor(f"make_point(x_min($geometry), {_PAA_MID_Y})"),
    _paa_anchor(f"make_point(x_max($geometry), {_PAA_MID_Y})"),
)


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

    hatch_layer.setId(
        _NFA_HATCH_SYMBOL_LAYER_ID
    )

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

    # A QgsLinePatternFillSymbolLayer paints its hatch through a SUB-
    # SYMBOL (a QgsLineSymbol), so a data-defined StrokeColor set on the
    # fill layer itself is silently ignored - which is what this did
    # until 2026-08-12, leaving every No Fire Area hatched black beside
    # its own correctly affiliation-coloured outline. The identical
    # latent bug airspace_control_measures.py's own Weapons Free Zone
    # had, found there first and the same fix applied here on sight
    # rather than waiting for it to be reported twice.
    _apply_affiliation_color(
        hatch_layer.subSymbol().symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol.appendSymbolLayer(
        hatch_layer
    )

    return symbol


def _paa_symbol():

    """
    Position Area For Artillery. The same plain status-driven outline
    every other area here uses, but with a stable id on it - its own
    "PAA" labels sit ON that outline (see _PAA_PERIMETER_ANCHORS), so
    the outline has to be maskable for the text to stay readable.
    """

    symbol = _status_driven_area_outline_symbol()

    symbol.symbolLayer(0).setId(
        _PAA_OUTLINE_SYMBOL_LAYER_ID
    )

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "aca": _status_driven_area_outline_symbol,
    "ffa": _status_driven_area_outline_symbol,
    "nfa": _nfa_symbol,
    "rfa": _status_driven_area_outline_symbol,
    "paa": _paa_symbol,
}


def _configure_lines_labeling(layer):

    """
    Table H-XVI's own lines don't all label the same way, so this
    builds a QgsRuleBasedLabeling tree rather than one shared
    QgsPalLayerSettings. Reworked 2026-08-12 from the maintainer's own
    live testing of the whole family.

    - **FSCL/NFL/BCL/RFL carry their label at BOTH ENDS**, each one
      including the feature's own unique designation - "MND(S) FSCL",
      "NFL II CORPS", "BCL III MEF". Two rules, one anchored on
      `start_point($geometry)` and one on `end_point($geometry)`, both
      OverPoint with the Above quadrant so the text sits clear of the
      line exactly as the template draws it. They are ALSO masked, so
      the line still breaks around the glyphs on any geometry where
      "above" and "clear of the line" aren't the same thing (a
      near-vertical bearing, say) - "not overlapping line" is the
      requirement, and the quadrant alone doesn't guarantee it.

      This replaced a pair of fixed-character font markers. Those could
      only ever draw the bare abbreviation: a marker's character is set
      when the symbol is built and cannot read the feature's fields, so
      there was nowhere for a per-feature designation to come from.

    - **CFL labels once at the CENTRE, above the line** - its own draw
      rules say "the line information will be posted once at the center
      of the line". Line placement with the AboveLine flag.

    - **MFP labels once at the centre too**, but stays ON the line
      where it already was (its own template draws it interrupting the
      line) - the only change it needed was the mask, so the line stops
      striking through the text.

    Every rule declares the SAME masked-id list. Masking is configured
    per QGIS layer rather than per rule, and rules declaring different
    lists make QGIS log "Different sets of symbol layers are masked by
    different sources! Only one (arbitrary) set will be retained!" and
    silently keep just one of them.
    """

    rules = []

    # AboveRight at the start and AboveLeft at the end, rather than a
    # plain Above at both: Above centres the text ON the end vertex, so
    # half of a long designation like "MND(S) FSCL" hangs off past the
    # end of the line entirely (confirmed by render). These two push it
    # INWARD from each end instead, which is where the template draws
    # it.
    for anchor, quadrant in (
        ("start_point($geometry)", Qgis.LabelQuadrantPosition.AboveRight),
        ("end_point($geometry)", Qgis.LabelQuadrantPosition.AboveLeft),
    ):

        rule = QgsRuleBasedLabeling.Rule(
            _build_pal_layer_settings(
                layer,
                Qgis.LabelPlacement.OverPoint,
                _LINE_DESIGNATION_LABEL_EXPRESSION,
                masked_symbol_layer_ids=_MASKED_LINE_SYMBOL_LAYER_IDS,
                label_geometry_expression=anchor,
                quadrant=quadrant
            )
        )

        rule.setFilterExpression(
            _measure_type_filter(_END_LABELLED_TYPES)
        )

        rules.append(rule)

    cfl_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _LINE_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_LINE_SYMBOL_LAYER_IDS,
            line_placement_flags=Qgis.LabelLinePlacementFlag.AboveLine
        )
    )

    cfl_rule.setFilterExpression(
        _measure_type_filter(("cfl",))
    )

    rules.append(cfl_rule)

    mfp_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _LINE_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_LINE_SYMBOL_LAYER_IDS
        )
    )

    mfp_rule.setFilterExpression(
        _measure_type_filter(("mfp",))
    )

    rules.append(mfp_rule)

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for rule in rules:

        root_rule.appendChild(rule)

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


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

    _configure_lines_labeling(layer)

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

    _configure_areas_labeling(layer)

    return layer


def _configure_areas_labeling(layer):

    """
    Four of the five areas here label once, centred inside the shape.
    Position Area For Artillery labels FOUR times instead, once at each
    of the top, bottom, left and right of its own perimeter - see
    _PAA_PERIMETER_ANCHORS. That is a different PLACEMENT rather than
    different text, so one shared QgsPalLayerSettings cannot express it
    and this builds a QgsRuleBasedLabeling tree (2026-08-12).

    Every rule is masked. For No Fire Area that is the whole point -
    it is the one area here with a hatched fill, and the maintainer
    asked for the text to be readable against it. For PAA the labels sit
    ON the outline, exactly as its own template draws them (the circle's
    arc breaks where each "PAA" sits), so the outline is what gets cut.
    Airspace Coordination Area/Free Fire Area/Restricted Fire Area have
    no fill and their label sits well inside, so masking is a harmless
    no-op there - which is why one shared id list on every rule is fine,
    and necessary: masking is configured per QGIS layer, not per rule,
    and rules declaring different lists make QGIS keep one arbitrarily.
    """

    centred_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _AREA_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_MASKED_AREA_SYMBOL_LAYER_IDS
        )
    )

    # Explicit non-PAA filter rather than setIsElse(True): each rule in
    # a QgsRuleBasedLabeling gets its own independent sub-provider, and
    # an else-flagged rule's provider still places its own label for the
    # rows the other rules matched - giving PAA a fifth, centred label
    # on top of its four. Confirmed the same way in c2_measures.py's own
    # _configure_area_designation_labeling(); reused here rather than
    # rediscovered.
    centred_rule.setFilterExpression(
        "\"measure_type\" IS NULL OR \"measure_type\" != 'paa'"
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(centred_rule)

    for anchor in _PAA_PERIMETER_ANCHORS:

        paa_rule = QgsRuleBasedLabeling.Rule(
            _build_pal_layer_settings(
                layer,
                Qgis.LabelPlacement.OverPoint,
                _AREA_DESIGNATION_LABEL_EXPRESSION,
                masked_symbol_layer_ids=_MASKED_AREA_SYMBOL_LAYER_IDS,
                label_geometry_expression=anchor,
                quadrant=Qgis.LabelQuadrantPosition.Over
            )
        )

        paa_rule.setFilterExpression(
            "\"measure_type\" = 'paa'"
        )

        root_rule.appendChild(paa_rule)

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


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
