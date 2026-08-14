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

**Points: the FULL vocabulary of printed pages 474-501 (105 entries),
on this module's own POINTS layer.** They started as an 18-entry curated
subset on the shared control_measure_points.py layer, with the sonobuoy
and anti-submarine-warfare fix/contact families deliberately left out as
"more Navy/ASW-specific". The maintainer reversed that 2026-08-12,
having read the table's own pages directly, and moved the whole family
here at the same time - so Sonobuoys (17) and Sub-Surface Warfare (17)
are now built in full. sidc.py's own entities are untouched by the move,
so anything already digitized keeps rendering.

They are grouped by **the table's own sub-headings** - General,
Sub-Surface Warfare, Search, Sonobuoys, Reference Points, Subsurface
Stations, Surface Stations, Routes, Emergency, Hazard, Sea Subsurface
Returns - carried as a real "group" field that **filters the "Entity"
dropdown to just that group's own entries**, so 105 options are never
shown at once. That cascade replaced a flat list with group-prefixed
labels on 2026-08-12; see POINT_ENTITY_LABELS for why the flat list was
there first, and why the ValueRelation crash risk it was avoiding
turned out to have already been settled by the maintainer's own live
smoke test.

**Five codes in the 474-501 range are deliberately NOT built**, each for
its own reason:

- **210000** is the table's own parent row - its template column reads
  "N/A". There is no symbol to draw, and milsymbol has no icon for it.
- **211000 (Launched Torpedo), 211200 (Acoustic Countermeasure
  (Decoy)) and 211300 (Electronic Countermeasures (ECM) Decoy)** are
  each marked "(AEGIS only)" in their own CONTROL MEASURE cell, the
  same AEGIS category excluded wholesale below. The maintainer's own
  instruction on this pass was to ignore AEGIS.
- **217300 (Position and Intended Movement (PIM) Route)** is broken in
  milsymbol itself: its own source maps the code to
  `icn["TP.ROUTE POINT R"]` - the SAME icon as 217500, Point R Route -
  under a literal `##### FIX TODO #######` comment. Rendering it would
  silently draw the wrong symbol, which this project treats as worse
  than drawing none (the same call already made for Search Area's own
  placeholder glyph).
- **218400 (Navigational)** is not a point at all: its own draw rules
  say "This symbol requires two anchor points. Points 1 and 2 define
  the corner points of the symbol" - a two-vertex hooked line, which is
  why milsymbol has no point icon for it either. **Built 2026-08-14 on
  the LINES layer**, hand-constructed; see _navigational_symbol(). With
  it, Table H-XIV is closed.

**The whole "(AEGIS only)" family of fixed-graphic overlay constructs
remains out of scope** (printed pages 467-473, which the maintainer
confirmed can be skipped in full) - Launch Area (200101/200102, Ellipse/
Rectangle), Defended Area (200201/200202), No Attack (NOTACK) Zone
(200300), Ship Area of Interest (200400 grid-heatmap/200401 Ellipse/
200402 Rectangle), Active Maneuver Area (200500), Cued Acquisition
Doctrine (200600), Radar Search Doctrine (200700). Confirmed by reading
every one of their own template pictures: these are AEGIS naval combat
system display overlays with specific fixed colours/fills/orientations
(not this project's usual freeform-polygon or simple-line model), a
genuinely different, narrow display category this project doesn't
otherwise build toward.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsFeature,
    QgsField,
    QgsFieldConstraints,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsProject,
    QgsMarkerSymbol,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, Qt
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    stabilised_point_size_expression,
    AFFILIATION_LABELS,
    POINT_AFFILIATION_LABELS,
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
POINTS_LAYER_NAME = "Maritime Control Measures (Points)"

# Not a layer the user ever sees or edits - the hidden reference table
# behind the Points layer's own cascading "Entity" dropdown. See
# _point_entity_lookup_layer().
POINT_ENTITY_LOOKUP_LAYER_NAME = "Maritime Control Measure Point Entities"

__all__ = [
    "LINES_LAYER_NAME",
    "POINTS_LAYER_NAME",
    "POINT_ENTITY_LOOKUP_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "POINT_ENTITY_LABELS",
    "POINT_GROUP_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_maritime_control_measures_lines_layer",
    "create_maritime_control_measures_points_layer",
    "add_maritime_control_measures_lines_layer",
    "add_maritime_control_measures_points_layer",
]

# Table H-XIV, codes 220100-220108 - see module docstring for the much
# larger AEGIS/ASW-sonar/Sonobuoy family deliberately left out.
LINE_MEASURE_TYPE_LABELS = {
    "navigational": "Navigational",
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


# --- Navigational (218400) ---

# The two corner flanks, in MILLIMETRES on the page, and their angles
# counter-clockwise from the direction of travel (PT1 toward PT2) - the
# maintainer's own dictated construction: "at pt 1 draw a line segment
# of 6mm at 40 deg angle relative to the pt1-pt2 line, at pt2 draw a
# line at 220deg angle relative to the pt1-pt2 line, 6mm".
#
# 220 is 40 + 180, so the pair is anti-parallel - which is exactly the
# Z the template draws, and the reason the symbol reads the same either
# way round. The standard's own Size/Shape rule agrees that only the
# middle run varies: "The symbol varies only in length."
_NAVIGATIONAL_FLANK_MM = 6.0
_NAVIGATIONAL_FIRST_ANGLE_DEG = 40.0
_NAVIGATIONAL_LAST_ANGLE_DEG = 220.0

_NAVIGATIONAL_LINE_WIDTH_MM = 0.4

# A colour STRING for the SVG glyphs, not a QGIS colour. The shared
# _AFFILIATION_COLOR_EXPRESSION is built from color_rgb(), which
# evaluates to a bare "0,0,255" - right for a colour property and
# silently invalid inside an SVG, where it draws the glyph as nothing
# at all. Same reason field_fortification.py carries its own.
_NAVIGATIONAL_GLYPH_COLOR_EXPRESSION = (
    "CASE "
    "WHEN \"affiliation\" = 'friend' THEN 'rgb(0,0,255)' "
    "WHEN \"affiliation\" = 'hostile' THEN 'rgb(255,0,0)' "
    "WHEN \"affiliation\" = 'neutral' THEN 'rgb(0,255,0)' "
    "WHEN \"affiliation\" = 'unknown' THEN 'rgb(255,255,0)' "
    "ELSE 'rgb(0,0,0)' "
    "END"
)


def _navigational_flank_layer(placement, angle_deg):

    """
    One corner flank, as a glyph on a marker line.

    `setRotateSymbols(True)` is what makes the angle RELATIVE to the
    line: QGIS turns the marker with the segment it sits on, and the
    glyph itself is drawn at `angle_deg` from its own +x axis, so the
    two compose to "so many degrees off the direction of travel".

    The marker's size is TWICE the flank length, because the glyph's
    viewBox is symmetric about the origin so it can centre on the
    vertex - and QGIS sizes an SVG marker by its width.
    """

    glyph = QgsSvgMarkerSymbolLayer("")

    glyph.setSize(_NAVIGATIONAL_FLANK_MM * 2.0)

    glyph.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_navigational_flank_svg({colour}, {length}, {angle}, "
            "{stroke})".format(
                colour=_NAVIGATIONAL_GLYPH_COLOR_EXPRESSION,
                length=_NAVIGATIONAL_FLANK_MM,
                angle=angle_deg,
                stroke=_NAVIGATIONAL_LINE_WIDTH_MM,
            )
        )
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, glyph)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(placement)

    marker_line.setRotateSymbols(True)

    return marker_line


def _navigational_symbol():

    """
    Navigational (218400) - the last row of Table H-XIV, and the only
    one of its hazards that is a LINE rather than a point, which is why
    milsymbol has no icon for it: "This symbol requires two anchor
    points. Points 1 and 2 define the corner points of the symbol."

    The clicked points are the CORNERS, not the ends: the run between
    them is drawn as given, and each corner grows a fixed 6 mm flank.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(QColor(0, 0, 0))

    line_layer.setWidth(_NAVIGATIONAL_LINE_WIDTH_MM)

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, line_layer)

    symbol.appendSymbolLayer(
        _navigational_flank_layer(
            Qgis.MarkerLinePlacement.FirstVertex,
            _NAVIGATIONAL_FIRST_ANGLE_DEG,
        )
    )

    symbol.appendSymbolLayer(
        _navigational_flank_layer(
            Qgis.MarkerLinePlacement.LastVertex,
            _NAVIGATIONAL_LAST_ANGLE_DEG,
        )
    )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "navigational": _navigational_symbol,
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


# --------------------------------------------------------------------
# Points (Table H-XIV's own point vocabulary, printed pages 474-501) -
# milsymbol-rendered icons, not hand-built symbology. See this module's
# own docstring for the move out of control_measure_points.py, for the
# full-vocabulary decision, and for the five codes deliberately left
# out.
# --------------------------------------------------------------------

# The table's OWN sub-headings, in its own order. "General" is this
# module's name for the table's first, unheaded block (210100-211100,
# everything before the "Sub-Surface Warfare" rule) - the standard runs
# those rows straight on from the section's own parent entry without a
# heading of their own.
POINT_GROUP_LABELS = {
    "general": "General",
    "sub_surface_warfare": "Sub-Surface Warfare",
    "search": "Search",
    "sonobuoys": "Sonobuoys",
    "reference_points": "Reference Points",
    "subsurface_stations": "Subsurface Stations",
    "surface_stations": "Surface Stations",
    "routes": "Routes",
    "emergency": "Emergency",
    "hazard": "Hazard",
    "sea_subsurface_returns": "Sea Subsurface Returns",
}

# entity -> (group, name within that group). 105 entries, the full
# vocabulary of pages 474-501.
#
# **Two deliberate departures from the table's own printed layout, both
# from the maintainer's 2026-08-13 review.**
#
# 1. The six HARBOUR entries (212800-212904) sit under Surface Stations
#    here, not Sub-Surface Warfare. The standard really does print them
#    under its own "Sub-Surface Warfare" rule - checked on the page
#    image, there is no intervening heading - but a harbour and its
#    entrance points are surface features, and the group in this form
#    is a menu, not a citation. Their codes and glyphs are untouched;
#    only which submenu they appear under changes.
#
# 2. Every name in both station groups is now the standard's own
#    CONTROL MEASURE column verbatim. They previously carried an
#    invented "Sea" ("General Sea Surface Station" for the table's own
#    "General Surface Station"), and two were wrong outright - 216800
#    is "Remote Multi-Mission Vehicle Unmanned Underwater Vehicle
#    Surface Station", not "...Mine Warfare Unmanned Underwater Sea
#    Surface Station", and 216900 is "Surface Warfare Unmanned
#    Underwater Vehicle Surface Station" with no "Mine Warfare" in it
#    at all. That padding is what made the two groups read as
#    duplicates of each other, which is how this surfaced. They are
#    not duplicates: the Subsurface Stations (214900-215500) draw a
#    DASHED line above and a solid line below, the Surface Stations
#    (215600-217000) draw both lines solid, and the render bears that
#    out entity by entity.
_POINT_ENTITIES = {
    # General
    "plan_ship": ("general", "Plan Ship"),
    "aim_point": ("general", "Aim Point"),
    "defended_asset": ("general", "Defended Asset"),
    "drop_point": ("general", "Drop Point"),
    "entry_point": ("general", "Entry Point"),
    "air_detonation": ("general", "Air Detonation"),
    "ground_zero": ("general", "Ground Zero"),
    "impact_point": ("general", "Impact Point"),
    "predicted_impact_point": ("general", "Predicted Impact Point"),
    "missile_detection_point": ("general", "Missile Detection Point"),
    # Sub-Surface Warfare
    "brief_contact": ("sub_surface_warfare", "Brief Contact"),
    "datum_lost_contact": ("sub_surface_warfare", "Datum Lost Contact"),
    "bt_buoy_drop": ("sub_surface_warfare", "BT Buoy Drop"),
    "reported_bottomed_sub": ("sub_surface_warfare", "Reported Bottomed Sub"),
    "moving_haven": ("sub_surface_warfare", "Moving Haven"),
    "screen_center": ("sub_surface_warfare", "Screen Center"),
    "lost_contact": ("sub_surface_warfare", "Lost Contact"),
    "sinker": ("sub_surface_warfare", "Sinker"),
    "trial_track": ("sub_surface_warfare", "Trial Track"),
    "acoustic_fix": ("sub_surface_warfare", "Acoustic Fix"),
    "electromagnetic_fix": ("sub_surface_warfare", "Electromagnetic Fix"),
    "electromagnetic_magnetic_anomaly_detection": ("sub_surface_warfare", "Electromagnetic - Magnetic Anomaly Detection (MAD)"),
    "optical_fix": ("sub_surface_warfare", "Optical Fix"),
    "formation": ("sub_surface_warfare", "Formation"),
    # Search
    "dip_position": ("search", "Dip Position"),
    "search": ("search", "Search"),
    "search_area": ("search", "Search Area"),
    "search_center": ("search", "Search Center"),
    "navigational_reference_point": ("search", "Navigational Reference Point"),
    # Sonobuoys
    "sonobuoy": ("sonobuoys", "Sonobuoy"),
    "ambient_noise_sonobuoy": ("sonobuoys", "Ambient Noise Sonobuoy"),
    "air_transportable_communication_sonobuoy": ("sonobuoys", "Air Transportable Communication Sonobuoy"),
    "barra_sonobuoy": ("sonobuoys", "Barra Sonobuoy"),
    "bathythermograph_transmitting_sonobuoy": ("sonobuoys", "Bathythermograph Transmitting Sonobuoy"),
    "command_active_multi_beam_sonobuoy": ("sonobuoys", "Command Active Multi-Beam (CAMBS) Sonobuoy"),
    "command_active_sonobuoy_system": ("sonobuoys", "Command Active Sonobuoy System (CASS)"),
    "directional_frequency_analysis_and_recording_sonobuoy": ("sonobuoys", "Directional Frequency Analysis and Recording (DIFAR) Sonobuoy"),
    "directional_command_active_sonobuoy_system": ("sonobuoys", "Directional Command Active Sonobuoy System (DICASS)"),
    "expendable_reliable_acoustic_path_sonobuoy": ("sonobuoys", "Expendable Reliable Acoustic Path Sonobuoy (ERAPS)"),
    "expired_sonobuoy": ("sonobuoys", "Expired Sonobuoy"),
    "kingpin_sonobuoy": ("sonobuoys", "Kingpin Sonobuoy"),
    "low_frequency_analysis_and_recording_sonobuoy": ("sonobuoys", "Low Frequency Analysis and Recording (LOFAR) Sonobuoy"),
    "pattern_center_sonobuoy": ("sonobuoys", "Pattern Center Sonobuoy"),
    "range_only_sonobuoy": ("sonobuoys", "Range Only Sonobuoy"),
    "vertical_line_array_directional_frequency_analysis_and_recording_sonobuoy": ("sonobuoys", "Vertical Line Array Directional Frequency Analysis and Recording (DIFAR) Sonobuoy"),
    # Reference Points
    "reference_point": ("reference_points", "Reference Point"),
    "special_point_reference": ("reference_points", "Special Point"),
    "navigational_reference_point_reference": ("reference_points", "Navigational Reference Point"),
    "data_link_reference_point": ("reference_points", "Data Link Reference Point"),
    "vital_area_center": ("reference_points", "Vital Area Center"),
    "corridor_tab_point": ("reference_points", "Corridor Tab Point"),
    "enemy_point": ("reference_points", "Enemy Point"),
    "marshall_point": ("reference_points", "Marshall Point"),
    "position_and_intended_movement": ("reference_points", "Position and Intended Movement (PIM)"),
    "pre_landfall_waypoint": ("reference_points", "Pre-Landfall Waypoint"),
    "estimated_position": ("reference_points", "Estimated Position (EP)"),
    "waypoint_reference": ("reference_points", "Waypoint"),
    # Subsurface Stations
    "general_subsurface_station": ("subsurface_stations", "General Subsurface Station"),
    "submarine_subsurface_station": ("subsurface_stations", "Submarine Subsurface Station"),
    "submarine_antisubmarine_warfare_subsurface_station": ("subsurface_stations", "Submarine Antisubmarine Warfare Subsurface Station"),
    "unmanned_underwater_vehicle_subsurface_station": ("subsurface_stations", "Unmanned Underwater Vehicle Subsurface Station"),
    "antisubmarine_warfare_unmanned_underwater_vehicle_subsurface_station": ("subsurface_stations", "Antisubmarine Warfare (ASW) Unmanned Underwater Vehicle Subsurface Station"),
    "mine_warfare_unmanned_underwater_vehicle_subsurface_station": ("subsurface_stations", "Mine Warfare Unmanned Underwater Vehicle Subsurface Station"),
    "surface_warfare_unmanned_underwater_vehicle_subsurface_station": ("subsurface_stations", "Surface Warfare Unmanned Underwater Vehicle Subsurface Station"),
    # Surface Stations
    "harbor": ("surface_stations", "Harbor"),
    "harbor_entrance_point": ("surface_stations", "Harbor Entrance Point"),
    "harbor_entrance_point_a": ("surface_stations", "Harbor Entrance Point A"),
    "harbor_entrance_point_q": ("surface_stations", "Harbor Entrance Point Q"),
    "harbor_entrance_point_x": ("surface_stations", "Harbor Entrance Point X"),
    "harbor_entrance_point_y": ("surface_stations", "Harbor Entrance Point Y"),
    "general_surface_station": ("surface_stations", "General Surface Station"),
    "antisubmarine_warfare_surface_station": ("surface_stations", "Antisubmarine Warfare (ASW) Surface Station"),
    "mine_warfare_surface_station": ("surface_stations", "Mine Warfare Surface Station"),
    "non_combatant_surface_station": ("surface_stations", "Non-Combatant Surface Station"),
    "picket_surface_station": ("surface_stations", "Picket Surface Station"),
    "rendezvous_surface_station": ("surface_stations", "Rendezvous Surface Station"),
    "replenishment_at_sea_surface_station": ("surface_stations", "Replenishment at Sea Surface Station"),
    "rescue_surface_station": ("surface_stations", "Rescue Surface Station"),
    "surface_warfare_surface_station": ("surface_stations", "Surface Warfare Surface Station"),
    "unmanned_underwater_vehicle_surface_station": ("surface_stations", "Unmanned Underwater Vehicle Surface Station"),
    "antisubmarine_warfare_unmanned_underwater_vehicle_surface_station": ("surface_stations", "Antisubmarine Warfare (ASW) Unmanned Underwater Vehicle Surface Station"),
    "mine_warfare_unmanned_underwater_vehicle_surface_station": ("surface_stations", "Mine Warfare Unmanned Underwater Vehicle Surface Station"),
    "remote_multi_mission_vehicle_unmanned_underwater_vehicle_surface_station": ("surface_stations", "Remote Multi-Mission Vehicle Unmanned Underwater Vehicle Surface Station"),
    "surface_warfare_unmanned_underwater_vehicle_surface_station": ("surface_stations", "Surface Warfare Unmanned Underwater Vehicle Surface Station"),
    "shore_control_station": ("surface_stations", "Shore Control Station"),
    # Routes
    "general_route": ("routes", "General Route"),
    "diversion_route": ("routes", "Diversion Route"),
    "picket_route": ("routes", "Picket Route"),
    "point_r_route": ("routes", "Point R Route"),
    "rendezvous_route": ("routes", "Rendezvous Route"),
    "waypoint_route": ("routes", "Waypoint Route"),
    "clutter_stationary_or_cease_reporting": ("routes", "Clutter, Stationary or Cease Reporting"),
    "tentative_or_provisional_track": ("routes", "Tentative or Provisional Track"),
    # Emergency
    "distressed_vessel": ("emergency", "Distressed Vessel"),
    "downed_aircraft": ("emergency", "Downed/Ditched Aircraft"),
    "person_in_water_bailout": ("emergency", "Person in Water/Bailout"),
    # Hazard
    "iceberg": ("hazard", "Iceberg"),
    "oil_rig": ("hazard", "Oil Rig"),
    "sea_mine_like_contact": ("hazard", "Sea Mine-Like Contact"),
    # Sea Subsurface Returns
    "bottom_return_non_mine_mine_like_bottom_object": ("sea_subsurface_returns", "Bottom Return - Non-Mine, Mine-Like Bottom Object (NOMBO)"),
    "bottom_return_installation_manmade": ("sea_subsurface_returns", "Bottom Return - Installation/Manmade"),
    "marine_life": ("sea_subsurface_returns", "Marine Life"),
    "sea_anomaly": ("sea_subsurface_returns", "Sea Anomaly (Wake, Current, Knuckle)"),
    "bottom_return_non_milco_wreck_dangerous": ("sea_subsurface_returns", "Bottom Return - Non-MILCO, Wreck, Dangerous"),
    "bottom_return_non_milco_wreck_non_dangerous": ("sea_subsurface_returns", "Bottom Return - Non-MILCO, Wreck, Non Dangerous"),
}

# **The group genuinely filters the entity list, from 2026-08-12.**
# 105 entries is far too many for one flat list - the maintainer's own
# words, "can we make them into sub menu, otherwise the list is too
# long". This first shipped as a compromise rather than a cascade: the
# group was a PREFIX on every label in one flat 105-entry ValueMap,
# plus a "group" field auto-derived from the chosen entity. The reason
# given was that QGIS's only real filter-one-field-by-another mechanism
# is a ValueRelation cascade, and this project had retired that after a
# native crash while building the old shared unit_layer.py.
#
# The maintainer reopened it from their own experience of that layer:
# "initially when we had land/air/space etc under one layer, in the
# menu selection, if we selected land in group, only land related
# entities came up, and it worked perfectly fine". They are right, and
# docs/roadmap.md says so in as many words. That crash was only ever
# reproduced by driving QgsValueRelationFieldFormatter.createCache()
# DIRECTLY from this headless harness, outside any real form - the
# maintainer's own live smoke test settled it the next day
# ("**Confirmed safe 2026-08-07**: user smoke-tested the real
# interactive attribute form live - the cascading dropdown works
# correctly, no crash"). What got retired with unit_layer.py was its
# one-layer-for-four-domains design, not this widget.
#
# So the form now reads the way it looks: pick a group, and "entity"
# offers only that group's own rows (_configure_points_attribute_form).
# Two consequences follow.
#
# - Entity labels are the table's own plain names, with no group
#   prefix. The prefix was the workaround; the group now sits on the
#   line directly above in the form, so repeating it in all 105 options
#   is just noise.
# - The group is no longer derived from the entity - the dependency
#   runs the other way. A mismatched pair is still reachable by
#   changing the group AFTER the entity (QGIS re-filters the dropdown
#   but leaves the stored value alone), which is exactly the
#   maintainer's own worry: "user may select group as general and
#   entity as reference point - ultimately reference point is displayed
#   which is incorrect". _POINT_ENTITY_GROUP_CONSTRAINT below catches
#   that on save. It is a plain per-feature expression with no
#   current_value() in it, which is also the documented fallback the
#   original crash note itself named.
POINT_ENTITY_LABELS = {
    entity: name
    for entity, (_group, name) in _POINT_ENTITIES.items()
}

# entity -> its own group, as an expression over the feature. Used as a
# hard constraint on "entity" (see above), not as a default value.
_POINT_GROUP_OF_ENTITY_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"entity\" = '{entity}' THEN '{group}'"
    for entity, (group, _name) in _POINT_ENTITIES.items()
) + " ELSE '' END"

_POINT_ENTITY_GROUP_CONSTRAINT = (
    f"({_POINT_GROUP_OF_ENTITY_EXPRESSION}) = \"group\""
)

_POINT_ENTITY_GROUP_CONSTRAINT_DESCRIPTION = (
    "The entity must be one of the chosen group's own entries."
)

# NOT dict(AFFILIATION_LABELS), which is what this was until
# 2026-08-12. That shared dict carries a fifth value, "Unspecified
# (black)", correct for the hand-drawn lines/areas layers - where
# affiliation only picks a Qt colour - but not a SIDC standard
# identity, so on this milsymbol-rendered Points layer choosing it made
# build_sidc() raise and milsymbol drew its unknown-icon fallback. The
# default here was already 'friend', so nothing was broken as shipped;
# the attribute form simply offered one menu entry that silently broke
# the symbol. See POINT_AFFILIATION_LABELS in _control_measure_shared.py.
_POINT_AFFILIATION_LABELS = POINT_AFFILIATION_LABELS

_POINT_STATUS_LABELS = dict(STATUS_LABELS)

_POINTS_DEFAULT_MARKER_SIZE_MM = 8.0

_POINTS_DEFAULT_ENTITY = "plan_ship"

_POINTS_DEFAULT_GROUP = _POINT_ENTITIES[_POINTS_DEFAULT_ENTITY][0]

# Plain `uniqueDesignation`, matching every other Points layer in this
# appendix-by-appendix pass. Not individually verified per icon across
# all 105 - c2_measures.py's own _POINT_TEXT_SLOT_OVERRIDES records
# that milsymbol's slot naming is NOT consistent between icons, so some
# of these will place their designation somewhere other than their own
# template shows. Passing a slot an icon doesn't define is a harmless
# no-op, so nothing breaks; it is a known gap to close if reported,
# exactly as control_measure_points.py already documents for its own
# vocabulary. upper(...) per H.5.4; coalesce(...,'') because QGIS
# short-circuits the whole call to NULL on any NULL argument, which
# would blank the icon rather than just its text.
_POINTS_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false),"
    "upper(coalesce(\"unique_designation\",'')),"
    "'uniqueDesignation'"
    ")"
)


def _point_entity_lookup_layer(name=POINT_ENTITY_LOOKUP_LAYER_NAME):

    """
    The small reference table behind the "Entity" field's cascading
    ValueRelation dropdown - one row per (group, entity) pair. Not user
    data. Rows are built in _POINT_ENTITIES' own order (the standard's
    printed order down pages 474-501) because that is the source
    order, not because the dropdown honours it: QGIS sorts a
    ValueRelation's options itself, by label here (see
    _configure_points_attribute_form's own OrderByValue note).

    It has to be a real registered project layer: a ValueRelation
    addresses its source by layer id, so nothing unregistered will do.
    addToLegend=False keeps it out of the Layers panel, the same narrow
    exception the old unit_layer.py made for the same reason.

    Reused when one of the same name is already registered rather than
    rebuilt - every Points layer this module creates can share the one
    lookup, and rebuilding it would orphan the id that an
    already-created layer's widget config points at.
    """

    project = QgsProject.instance()

    for existing in project.mapLayersByName(name):

        if [field.name() for field in existing.fields()] == [
            "group", "entity", "label"
        ]:

            return existing

    layer = QgsVectorLayer(
        "NoGeometry?field=group:string&field=entity:string&field=label:string",
        name,
        "memory"
    )

    features = []

    for entity, (group, label) in _POINT_ENTITIES.items():

        feature = QgsFeature(layer.fields())

        feature.setAttribute("group", group)
        feature.setAttribute("entity", entity)
        feature.setAttribute("label", label)

        features.append(feature)

    layer.dataProvider().addFeatures(features)

    project.addMapLayer(
        layer,
        False
    )

    return layer


def _configure_points_attribute_form(layer):

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    entity_idx = fields.indexOf("entity")
    status_idx = fields.indexOf("status")
    group_idx = fields.indexOf("group")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_POINT_AFFILIATION_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        entity_idx,
        QgsEditorWidgetSetup(
            "ValueRelation",
            {
                "Layer": _point_entity_lookup_layer().id(),
                "Key": "entity",
                "Value": "label",
                "FilterExpression": "\"group\" = current_value('group')",
                "AllowMulti": False,
                "AllowNull": False,
                # Sort by the displayed label. QGIS sorts a
                # ValueRelation either way - False sorts by the KEY
                # instead, i.e. by the internal entity slug, which is
                # not what the user is reading. Verified in a real
                # QgsAttributeForm, not assumed: an early cut of this
                # used False expecting it to preserve the lookup
                # layer's own row order (the standard's printed order),
                # and the form sorted the list regardless.
                "OrderByValue": True,
                "NofColumns": 1,
                "UseCompleter": False,
            }
        )
    )

    # Belt to the dropdown's braces. The filter stops a mismatched pair
    # being PICKED; this stops one being LEFT behind by changing the
    # group after the entity. Hard, so it blocks the save rather than
    # only warning - a wrong pair here means the drawn symbol disagrees
    # with the recorded group.
    layer.setConstraintExpression(
        entity_idx,
        _POINT_ENTITY_GROUP_CONSTRAINT,
        _POINT_ENTITY_GROUP_CONSTRAINT_DESCRIPTION
    )

    layer.setFieldConstraint(
        entity_idx,
        QgsFieldConstraints.Constraint.ConstraintExpression,
        QgsFieldConstraints.ConstraintStrength.ConstraintStrengthHard
    )

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_POINT_STATUS_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        group_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(POINT_GROUP_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))

    # Derived from each other rather than written out twice: a new
    # feature must open on a pair the constraint above accepts, or
    # every point would arrive invalid.
    layer.setDefaultValueDefinition(
        group_idx,
        QgsDefaultValue(f"'{_POINTS_DEFAULT_GROUP}'")
    )

    layer.setDefaultValueDefinition(
        entity_idx,
        QgsDefaultValue(f"'{_POINTS_DEFAULT_ENTITY}'")
    )


def _build_points_renderer():

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(
        _POINTS_DEFAULT_MARKER_SIZE_MM
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_POINTS_SIDC_EXPRESSION)
    )

    # Holds the icon still when a designation is typed -
    # see stabilised_point_size_expression().
    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(
            stabilised_point_size_expression(
                _POINTS_DEFAULT_MARKER_SIZE_MM, _POINTS_SIDC_EXPRESSION
            )
        )
    )

    symbol.changeSymbolLayer(
        0,
        svg_layer
    )

    return QgsSingleSymbolRenderer(symbol)


def create_maritime_control_measures_points_layer(name=POINTS_LAYER_NAME):

    """
    A fresh, empty point layer for Table H-XIV's own point vocabulary -
    all 105 usable entries from printed pages 474-501, grouped by the
    table's own sub-headings. See this module's own docstring for what
    is deliberately left out and why.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("group", QMetaType.Type.QString),
            QgsField("entity", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    _configure_points_attribute_form(layer)

    layer.setRenderer(
        _build_points_renderer()
    )

    return layer


def add_maritime_control_measures_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_maritime_control_measures_points_layer
    )
