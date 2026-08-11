# -*- coding: utf-8 -*-

"""
Builds ready-to-use layers for MIL-STD-2525D Appendix H.5.15 (Table
H-XIII, "Airspace control means") - Mini-Phase H7, the seventh H.5.x
logical group in this appendix-by-appendix pass.

Table H-XIII's own text splits airspace control means into four groups:
points, lines, corridors/routes (nominally "Areas" in the standard's own
SIDC prefix, code range 170000, but their own construction - PT1/PT2
anchor points plus every segment defined the same way a line is - is a
band-shaped LINE, not a closed boundary; see below) and areas/zones
(code range 170000-172000, genuine freeform polygons).

**Points (25 entries, codes 180000-182500) are NOT built here at all -
every one of them (Air Control Point, Communications Checkpoint, Downed
Aircrew Pick-Up Point, Pop-Up Point, Air Control Rendezvous, TACAN, CAP/
AEW/ASW/SUCAP/MIW Stations, Strike Initial Point, Replenishment Station,
Tanking, Tomcat, Rescue, Unmanned Aerial System, VTUA, Orbit + its 3
variants) is confirmed present in milsymbol.js's own vendored source
under this exact numeric code, so they were added directly to sidc.py's
ENTITIES["control_measure"] and control_measure_points.py's own
_ENTITY_LABELS instead, the same "point control measures belong to the
shared, milsymbol-rendered Control Measure Points layer" precedent
already established for H4's Observation Post family and H5's Point of
Departure - unlike those two mini-phases, this appendix's own point
vocabulary genuinely was NOT already present and had to be added.
milsymbol's own display name for 180400 is "TP.PULL-UP POINT", not
"Pop-Up Point (PUP)" as the standard calls it - confirmed by inspecting
its actual drawn geometry (circle + "PUP" text + bowtie path), which
matches the standard's own template exactly; a milsymbol naming quirk,
not a missing/wrong symbol.

**Base Defense Zone (170800, BDZ)** was skipped when this module was
first built - its own template is a fixed-size ("Static") circle
labelled "BDZ" around ONE anchor point, fitting neither milsymbol's
vocabulary nor the Areas layer's freeform-polygon model. Added
2026-08-12 on the maintainer's own instruction, as a TWO-point circle
instead: "make it a two point circle, one for the center and other for
radius". That deliberately departs from the standard's own one-anchor,
Static rule in exchange for a sizable zone - see
_base_defense_zone_symbol(). It lives on the LINES layer because its
own geometry is a 2-point line.

**Corridors/Routes (7 types, all under the standard's own "17" Area SIDC
prefix) are built on the LINES layer instead**, because their actual
construction (2-99 sequential PT anchor points defining a centerline,
same as any other digitized line) is a path, not a closed boundary a
polygon layer could hold - the same "organise by actual QGIS geometry
type, not the standard's own SIDC field-code grouping" principle already
applied to H6's Support by Fire Position/Search Area. Every one of them
(Air Corridor 170100, Low-Level Transit Route 170200, Minimum-Risk Route
170300, Safe Lane 170400, SAAFR 170500, Transit Corridor 170600,
Unmanned Aircraft Route 170700) is, per its own template picture, really
a variable-width RIBBON/BAND with rounded ACP/CCP circle endpoints and up
to 5 extra descriptive fields (WIDTH/MIN ALT/MAX ALT/DTG START/DTG END) -
drawn as TWO PARALLEL LINES either side of the digitized centreline
with the "PREFIX NAME" label centred BETWEEN them (rebuilt 2026-08-12 -
until then this was a single thick line, which the maintainer
corrected: "it is two parallel lines with the unique designation within
the parallel lines"), the label repeating along the route so multi-
segment corridors carry it wherever it fits. Still approximated in the
same whole-table-approximation tolerance already used for
offensive_control_measures.py's own Axis of Advance family: the taper,
the ACP/CCP endpoint circles (themselves just
separate, already-covered point symbols the standard's own draw rules
say anchor each end - not part of the corridor's own drawn geometry) and
the WIDTH/altitude/DTG fields are all dropped, keeping only what's
SIDC-relevant (measure_type, correct colour, the name). "Air Corridor
with Multiple Segments" is the same code (170100) as plain Air Corridor,
just with more than 2 anchor points - not a separate measure_type.

**Two simple end-labelled lines**: Identification, Friend-or-Foe (IFF)
Off Line (190100, "IFF OFF" at both ends) and IFF On Line (190200,
"IFF ON") - the same _end_label_layer() fixed-character-marker technique
already used throughout this appendix (FCL/LOA/LD/BL/HL/RL, etc.).

**Areas/Zones (12 types, code range 170900-172000)** all share the
identical "freeform outline + PREFIX + optional name" construction
already proven extensively elsewhere in this appendix (AO/NAI/TAI/AA/DZ/
EZ/LZ/PZ/etc.) via a shared prefix dict: High-Density Airspace Control
Zone (170900, HIDACZ), Restricted Operations Zone (171000, ROZ),
Air-to-Air ROZ (171100, AARROZ), Unmanned Aircraft ROZ (171200, UA-ROZ),
Weapon Engagement Zone (171300, WEZ - the standard's own note says WEZ
"includes" FEZ/JEZ/MEZ(LOMEZ/HIMEZ)/SHORADEZ as its own sub-types, but
the table then goes on to list each of those as its OWN separate code
too, so all 6 are built as distinct measure types, matching the
table's own literal code list rather than collapsing them under WEZ),
Fighter Engagement Zone (171400, FEZ), Joint Engagement Zone (171500,
JEZ), Missile Engagement Zone (171600, MEZ), Low/High (Altitude) Missile
Engagement Zone (171700/171800, LOMEZ/HIMEZ), Short Range Air Defense
Engagement Zone (171900, SHORADEZ). **Weapons Free Zone (172000, WFZ) is
the first area in this entire appendix-by-appendix pass whose own
template requires a genuine HATCHED FILL** ("Note: Upward diagonal lines
are part of the fill", not a plain "no fill" outline like every other
area built so far) - built with a QgsLinePatternFillSymbolLayer, a new
technique for this project.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFontMarkerSymbolLayer,
    QgsGeometryGeneratorSymbolLayer,
    QgsLinePatternFillSymbolLayer,
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
    _end_label_layer,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Airspace Control Measures (Lines)"
AREAS_LAYER_NAME = "Airspace Control Measures (Areas)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_airspace_control_measures_lines_layer",
    "create_airspace_control_measures_areas_layer",
    "add_airspace_control_measures_lines_layer",
    "add_airspace_control_measures_areas_layer",
]

# Table H-XIII - see module docstring for why the "Corridors (Areas)"
# section's own 7 entries live here instead, and for what's skipped
# (Base Defense Zone).
LINE_MEASURE_TYPE_LABELS = {
    "air_corridor": "Air Corridor (AC)",
    "low_level_transit_route": "Low-Level Transit Route (LLTR)",
    "minimum_risk_route": "Minimum-Risk Route (MRR)",
    "safe_lane": "Safe Lane (SL)",
    "saafr": "Standard Use Army Aircraft Flight Route (SAAFR)",
    "transit_corridor": "Transit Corridor (TC)",
    "unmanned_aircraft_route": "Unmanned Aircraft (UA) Route",
    "base_defense_zone": "Base Defense Zone (BDZ)",
    "iff_off_line": "Identification, Friend-or-Foe (IFF) Off Line",
    "iff_on_line": "Identification, Friend-or-Foe (IFF) On Line",
}

AREA_MEASURE_TYPE_LABELS = {
    "hidacz": "High-Density Airspace Control Zone (HIDACZ)",
    "roz": "Restricted Operations Zone (ROZ)",
    "aarroz": "Air-to-Air Restricted Operations Zone (AARROZ)",
    "ua_roz": "Unmanned Aircraft Restricted Operations Zone (UA-ROZ)",
    "wez": "Weapon Engagement Zone (WEZ)",
    "fez": "Fighter Engagement Zone (FEZ)",
    "jez": "Joint Engagement Zone (JEZ)",
    "mez": "Missile Engagement Zone (MEZ)",
    "lomez": "Low (Altitude) Missile Engagement Zone (LOMEZ)",
    "himez": "High (Altitude) Missile Engagement Zone (HIMEZ)",
    "shoradez": "Short Range Air Defense Engagement Zone (SHORADEZ)",
    "weapons_free_zone": "Weapons Free Zone (WFZ)",
}

# Table H-XIII's own examples: "AC GOLD", "LLTR COBRA", "MRR RED",
# "SL LION", "SAAFR BLUE", "TC KING", "UA DRAGON" - identical
# "prefix + optional name" pattern to c2_measures.py's own AO/NAI/TAI
# and maneuver_control_measures.py's own AA/DZ/EZ/LZ/PZ.
_CORRIDOR_LABEL_PREFIXES = {
    "air_corridor": "AC",
    "low_level_transit_route": "LLTR",
    "minimum_risk_route": "MRR",
    "safe_lane": "SL",
    "saafr": "SAAFR",
    "transit_corridor": "TC",
    "unmanned_aircraft_route": "UA",
}

_LINE_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    + " ".join(
        f"WHEN \"measure_type\" = '{measure_type}' THEN "
        f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
        " AND \"unique_designation\" != '' THEN"
        f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
        for measure_type, prefix in _CORRIDOR_LABEL_PREFIXES.items()
    )
    + " ELSE '' END"
)


# Half the corridor's own drawn width - each of the two parallel lines
# sits this far off the digitized centreline, so the gap between them is
# twice this. 2.0mm leaves room for the label to sit BETWEEN the lines
# at this appendix's own 9pt label size without touching either, the
# same offset offensive_control_measures.py's own Infiltration Lane
# already uses for its own parallel pair.
_CORRIDOR_HALF_WIDTH_MM = 2.0

# How often the corridor's own "AC GOLD"-style label repeats along the
# route. The maintainer's own requirement (2026-08-12) is that "in case
# of multiple line segments the AC+unique_designator should be in all
# segments if it fits" - QGIS has no "once per digitized segment" mode,
# so this is a repeat DISTANCE, which PAL then honours only where the
# text actually fits. Short segments simply go unlabelled rather than
# overprinting, which is the "if it fits" behaviour asked for.
_CORRIDOR_LABEL_REPEAT_MM = 45.0


def _corridor_symbol():

    """
    Table H-XIII (printed page 448) - the corridor/route family is drawn
    as TWO PARALLEL LINES with the label centred between them, NOT the
    single thick line this rendered as until 2026-08-12 ("it is two
    parallel lines with the unique designation within the parallel
    lines" - the project maintainer's own words).

    The user digitizes the corridor's own CENTRELINE, exactly as the
    standard's own template shows (PT1/PT2 "define the endpoint of a
    segment's centerline"); the two drawn lines are plain symbol-layer
    offsets either side of it, so no geometry generator is needed and
    the feature's own geometry stays the centreline for labelling.

    Shared by all 7 corridor/route measure types - only the label prefix
    differs between them (see _CORRIDOR_LABEL_PREFIXES).
    """

    symbol = QgsLineSymbol()

    for index, offset in enumerate(
        (_CORRIDOR_HALF_WIDTH_MM, -_CORRIDOR_HALF_WIDTH_MM)
    ):

        line_layer = QgsSimpleLineSymbolLayer()

        line_layer.setColor(
            QColor(0, 0, 0)
        )

        line_layer.setWidth(
            0.5
        )

        line_layer.setOffset(
            offset
        )

        _apply_affiliation_color(
            line_layer,
            [QgsSymbolLayer.Property.StrokeColor]
        )

        line_layer.setDataDefinedProperty(
            QgsSymbolLayer.Property.StrokeStyle,
            QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
        )

        if index == 0:

            symbol.changeSymbolLayer(
                0,
                line_layer
            )

        else:

            symbol.appendSymbolLayer(
                line_layer
            )

    return symbol


# Base Defense Zone's own circle, from the TWO points the user clicks:
# vertex 1 is the centre, vertex 2 sets the radius. QGIS's own
# make_circle() takes exactly that, so no custom Python function is
# needed; boundary() then reduces the polygon it returns to the ring,
# since this lives on the LINES layer.
_BASE_DEFENSE_ZONE_LABEL_EXPRESSION = (
    "'BDZ' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != ''"
    " THEN ' ' || " + _PLAIN_DESIGNATION_LABEL_EXPRESSION + " ELSE '' END"
)

_BASE_DEFENSE_ZONE_CIRCLE_EXPRESSION = (
    "boundary(make_circle("
    "point_n($geometry, 1),"
    " distance(point_n($geometry, 1), point_n($geometry, 2)),"
    " 64"
    "))"
)


def _base_defense_zone_symbol():

    """
    Table H-XIII, code 170800, page 452 - added 2026-08-12, having been
    skipped when this module was first built (see module docstring's own
    former "one point is skipped outright" note).

    **This deliberately departs from the standard**, on the project
    maintainer's own instruction: "make it a two point circle, one for
    the center and other for radius". The standard's own draw rules say
    the symbol "requires one anchor point" and is "Static" - a
    FIXED-size circle centred on it - which is exactly why it was
    skipped: a fixed circle around a single point fits neither the
    freeform-polygon Areas layer nor any line construction here. Taking
    a second point for the radius makes it sizable, which is far more
    useful on a real map, at the cost of no longer matching the
    standard's own "Static" size rule.

    It lives on the LINES layer because its own geometry IS a 2-point
    line - the same "organise by actual QGIS geometry type, not the
    standard's own SIDC grouping" principle already applied to the
    corridor family above.
    """

    symbol = QgsLineSymbol()

    circle_generator = QgsGeometryGeneratorSymbolLayer.create({})

    circle_generator.setGeometryExpression(
        _BASE_DEFENSE_ZONE_CIRCLE_EXPRESSION
    )

    circle_generator.setSymbolType(
        Qgis.SymbolType.Line
    )

    circle_symbol = QgsLineSymbol()

    circle_line_layer = circle_symbol.symbolLayer(0)

    circle_line_layer.setWidth(
        0.4
    )

    _apply_affiliation_color(
        circle_line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    circle_line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    circle_generator.setSubSymbol(
        circle_symbol
    )

    symbol.changeSymbolLayer(
        0,
        circle_generator
    )

    # "BDZ" at the circle's own centre - which is vertex 1, a point the
    # user actually clicked, so a marker on the ORIGINAL geometry does
    # it without touching this layer's own shared labelling (that is
    # set up for the corridor family's along-the-line, repeating
    # labels, which would be wrong here). Data-defined so the unique
    # designation rides along, the way every other zone in this table
    # labels; the standard's own template shows only the bare "BDZ",
    # but a nameable zone is more use on a real map and the prefix is
    # unchanged either way.
    label_layer = QgsFontMarkerSymbolLayer()

    label_layer.setFontFamily(
        "Arial"
    )

    label_layer.setSize(
        3.5
    )

    label_layer.setColor(
        QColor(0, 0, 0)
    )

    label_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Character,
        QgsProperty.fromExpression(_BASE_DEFENSE_ZONE_LABEL_EXPRESSION)
    )

    _apply_affiliation_color(
        label_layer,
        [QgsSymbolLayer.Property.FillColor]
    )

    label_marker = QgsMarkerSymbol()

    label_marker.changeSymbolLayer(
        0,
        label_layer
    )

    centre_label_layer = QgsMarkerLineSymbolLayer(False)

    centre_label_layer.setSubSymbol(
        label_marker
    )

    centre_label_layer.setPlacements(
        Qgis.MarkerLinePlacement.FirstVertex
    )

    symbol.appendSymbolLayer(
        centre_label_layer
    )

    return symbol


def _iff_line_symbol(character):

    """
    Table H-XIII, codes 190100/190200, page 465. A plain status-driven
    line with a fixed "IFF OFF"/"IFF ON" label at each end - the same
    _end_label_layer() technique as FCL/LOA/LD elsewhere in this
    appendix.

    The end labels do NOT rotate with the line. 2026-08-12: "the text
    is inverted depending on how the line is made, it should be right
    way up" - the maintainer's own words, the same defect already fixed
    for Bridgehead/Holding/Release Line. With rotation on, a line
    digitized right-to-left renders BOTH its labels upside-down and
    below the line, and an angled end segment tilts them.
    """

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
            _end_label_layer(placement, character, rotate_with_line=False)
        )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "air_corridor": _corridor_symbol,
    "low_level_transit_route": _corridor_symbol,
    "minimum_risk_route": _corridor_symbol,
    "safe_lane": _corridor_symbol,
    "saafr": _corridor_symbol,
    "transit_corridor": _corridor_symbol,
    "unmanned_aircraft_route": _corridor_symbol,
    "base_defense_zone": _base_defense_zone_symbol,
    "iff_off_line": lambda: _iff_line_symbol("IFF OFF"),
    "iff_on_line": lambda: _iff_line_symbol("IFF ON"),
}


# Table H-XIII's own examples: "HIDACZ\n32AADC", "ROZ\n11 ADA BDE",
# "AARROZ\n2ID", "WFZ\nATF" - same "prefix + optional name" pattern as
# the corridor family above and every other prefixed area in this
# appendix, just on the Areas layer.
_AREA_LABEL_PREFIXES = {
    "hidacz": "HIDACZ",
    "roz": "ROZ",
    "aarroz": "AARROZ",
    "ua_roz": "UA-ROZ",
    "wez": "WEZ",
    "fez": "FEZ",
    "jez": "JEZ",
    "mez": "MEZ",
    "lomez": "LOMEZ",
    "himez": "HIMEZ",
    "shoradez": "SHORADEZ",
    "weapons_free_zone": "WFZ",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = (
    "CASE "
    + " ".join(
        f"WHEN \"measure_type\" = '{measure_type}' THEN "
        f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
        " AND \"unique_designation\" != '' THEN"
        f" '\\n' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
        for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
    )
    + " ELSE '' END"
)


# Weapons Free Zone's own hatch spacing. Was 2.5mm; reduced 30% on
# 2026-08-12 at the project maintainer's own request ("the hashing can
# be a bit closer say by 30%").
_WEAPONS_FREE_ZONE_HATCH_SPACING_MM = 2.5 * 0.7

# A stable id so this layer's own "WFZ ..." label can mask the hatch it
# sits on. Masking is configured once per QGIS layer, on the one shared
# text format (see _build_pal_layer_settings()), and this Areas layer
# uses a single simple labelling - so one id in one list is all that is
# needed here, unlike offensive_control_measures.py's own rule-based
# tree which had to pass every variant's id to every rule.
_WEAPONS_FREE_ZONE_HATCH_SYMBOL_LAYER_ID = "weapons_free_zone_hatch"


def _weapons_free_zone_symbol():

    """
    Table H-XIII, code 172000, page 459. The one area in this whole
    appendix-by-appendix pass with a real fill - "Note: Upward diagonal
    lines are part of the fill." A QgsLinePatternFillSymbolLayer at 45
    degrees on top of the same status-driven outline every other area
    here uses.

    2026-08-12, per the project maintainer: "the hashing can be a bit
    closer say by 30%, and the text inside needs to have a mask so that
    it is readable" - the spacing below is that 30% reduction, and the
    hatch layer carries a stable id so this layer's own label can cut a
    real gap in it via QGIS Selective Masking (see
    _WEAPONS_FREE_ZONE_HATCH_SYMBOL_LAYER_ID).
    """

    symbol = _status_driven_area_outline_symbol()

    hatch_layer = QgsLinePatternFillSymbolLayer()

    hatch_layer.setId(
        _WEAPONS_FREE_ZONE_HATCH_SYMBOL_LAYER_ID
    )

    hatch_layer.setLineAngle(
        45
    )

    hatch_layer.setDistance(
        _WEAPONS_FREE_ZONE_HATCH_SPACING_MM
    )

    hatch_layer.setLineWidth(
        0.2
    )

    hatch_layer.setColor(
        QColor(0, 0, 0)
    )

    # A QgsLinePatternFillSymbolLayer draws its own hatch through a SUB-
    # SYMBOL (a QgsLineSymbol), so a data-defined StrokeColor set on the
    # fill layer itself is silently ignored - which is what this code
    # did until 2026-08-12, leaving every WFZ hatched black while its
    # own outline was correctly affiliation-coloured. Found by render
    # while masking the label; the intent was always here, it just
    # never reached the layer that actually paints.
    _apply_affiliation_color(
        hatch_layer.subSymbol().symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol.appendSymbolLayer(
        hatch_layer
    )

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "hidacz": _status_driven_area_outline_symbol,
    "roz": _status_driven_area_outline_symbol,
    "aarroz": _status_driven_area_outline_symbol,
    "ua_roz": _status_driven_area_outline_symbol,
    "wez": _status_driven_area_outline_symbol,
    "fez": _status_driven_area_outline_symbol,
    "jez": _status_driven_area_outline_symbol,
    "mez": _status_driven_area_outline_symbol,
    "lomez": _status_driven_area_outline_symbol,
    "himez": _status_driven_area_outline_symbol,
    "shoradez": _status_driven_area_outline_symbol,
    "weapons_free_zone": _weapons_free_zone_symbol,
}


def create_airspace_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XIII's own line-geometry
    measure types (the corridor/route family plus IFF Off/On Line) - see
    this module's own docstring for the full list and what's scoped out.
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
        QgsDefaultValue("'air_corridor'")
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

    # OnLine placement (the shared helper's own default) centres the
    # label vertically ON the digitized centreline - which, now that the
    # two drawn lines are offset either side of it, puts the text
    # exactly BETWEEN them, as the standard's own "AC GOLD" example
    # shows. The repeat distance is what gives the maintainer's own "in
    # all segments if it fits" - see _CORRIDOR_LABEL_REPEAT_MM.
    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.Line,
        _LINE_DESIGNATION_LABEL_EXPRESSION,
        repeat_distance_mm=_CORRIDOR_LABEL_REPEAT_MM
    )

    return layer


def create_airspace_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XIII's own 12 zone/area
    measure types.
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
        QgsDefaultValue("'roz'")
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

    # 2026-08-12: "the zones names and unique identifier ... just need
    # to be on to top left corner of polygon, within it" - the project
    # maintainer's own words. The label CONTENT was already right; only
    # its position was, defaulting to the polygon's own centre. PAL
    # labels the point mct_area_label_anchor() returns instead - see
    # that function for why a bounding-box corner cannot be used
    # directly - and AboveRight hangs the text down-and-right off that
    # anchor so it hangs DOWN-and-right into the shape rather than
    # straddling its own top edge (AboveRight was tried first and put
    # the text half outside - confirmed by render).
    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.OverPoint,
        _AREA_DESIGNATION_LABEL_EXPRESSION,
        label_geometry_expression="mct_area_label_anchor($geometry)",
        quadrant=Qgis.LabelQuadrantPosition.BelowRight,
        # Only Weapons Free Zone has a fill for a label to disappear
        # into, so its hatch is the only id here - masking a layer a
        # given feature doesn't have is harmless, the cut only happens
        # where the label's own text actually renders.
        masked_symbol_layer_ids=[_WEAPONS_FREE_ZONE_HATCH_SYMBOL_LAYER_ID]
    )

    return layer


def add_airspace_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_airspace_control_measures_lines_layer
    )


def add_airspace_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_airspace_control_measures_areas_layer
    )
