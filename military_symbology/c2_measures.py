# -*- coding: utf-8 -*-

"""
Builds ready-to-use C2 Measures layers - MIL-STD-2525D Appendix H's own
Boundaries (Table H-III, H.5.5), Command and Control Lines (Table H-IV,
H.5.10 - Light Line only, see LINE_MEASURE_TYPE_LABELS' own comment),
and Command and Control Areas (Table H-V, H.5.9/H.5.10) - one line
layer, one area layer, each styled via a QgsRuleBasedRenderer keyed on a
"measure_type" field, mirroring grid/mgrs_sub_grid.py's own rule-based
renderer pattern.

**2026-08-09: renamed from control_measures.py/"Control Measures
(Lines)"/"(Areas)" to c2_measures.py/"C2 Measures (Lines)"/"(Areas)",
at the project maintainer's own request.** Appendix H covers ~17
logical sections (C2 Measures, Maneuver, Defensive, Offensive, Airspace,
Maritime, Deception, Fire Support, Targets, Target Acquisition,
Obstacles, Field Fortification, CBRN, Sustainment, Supply, Mission
Tasks, Intelligence - see docs/roadmap.md's own H3-H22 mini-phase
table), and the original control_measures.py had started accreting all
of them into ONE shared "Control Measures (Lines)"/"(Areas)" pair, keyed
only by GEOMETRY TYPE (line vs. area) rather than by LOGICAL SECTION.
The maintainer flagged this before it grew further: as H3-H22 land, that
pair would eventually hold ~150 measure types in two giant rule trees
and attribute tables (every field from every section, whether or not a
given feature uses it), and clicking one "Control Measures" toolbar
button would keep adding all of them at once regardless of what the user
actually needs - exactly the "own layer, own icon" problem Appendices
B-L already solved for their point symbols by NOT sharing one "Tactical
Graphics" layer. The fix mirrors that precedent: each H.5.x logical
section gets its own layer(s) and its own module, added to its own
"Control Measures" submenu entry (nested inside the NATO Symbols
toolbar dropdown - see plugin.py's own _setup_control_measures_menu())
only when that section's own mini-phase actually lands. This module -
C2 Measures - is the first one, covering what Mini-Phases H0 and H2
already built (Boundary/Light Line/Area of Operations/Named Area of
Interest/Target Area of Interest/Airfield Zone); Maneuver/Defensive/
Offensive/etc. will each get their own new module (e.g.
maneuver_control_measures.py) as H3 onward complete, reusing this
module's own genuinely-shared helpers via _control_measure_shared.py
rather than each reinventing affiliation colouring, status/echelon
fields, or the designation-labeling machinery.

"military_symbology/control_measure_points.py" (a separate, already-
built layer covering MANY of Appendix H's point-type control measures
across several different H.5.x sections in one flat 80-entity dropdown,
via milsymbol.js rather than this module's hand-built QGIS line/area
symbology) was deliberately NOT split apart in this same rename - it
needs its own coverage audit against each H.5.x section first (already
tracked separately, see task #33 - Table H-VI/Command and Control
points specifically), so splitting it correctly belongs to whichever
future H-subphase actually reaches each of its entities' own section,
not to this rename.

The COLOURING is verified directly against the standard's own H.5.1.1.1/
H.5.3 Coloring rules (read from the actual MIL-STD-2525D PDF, not a
paraphrase) - see _control_measure_shared.py's own AFFILIATION_LABELS
comment for the friend=blue/hostile=red/neutral=green/unknown=yellow/
unspecified=black citation, shared by every H control-measure module.

Two separate layers, not one, because a QgsVectorLayer is always a single
geometry type - there's no "LineString or Polygon" layer in QGIS.

**2026-08-09: Mini-Phase H0 (H.5.1-H.5.4 general rules + H.5.5
Boundaries)**, the first mini-phase of the appendix-by-appendix
completion plan's own Appendix H pass (see docs/roadmap.md). Re-auditing
H.5.1-H.5.4 against the actual standard text (not assumed from the
previous pass) found two real, general defects, both fixed here:
  - **H.5.1.1.1/H.5.3 Coloring was wrong for neutral/unknown affiliation**
    - see _control_measure_shared.py's own AFFILIATION_LABELS/
    DEFAULT_AFFILIATION comments for the full citation and fix
    (neutral=green, unknown=yellow, not both folded into "black as
    standard").
  - **H.5.4 Labeling's "all text labeling shall be in upper case
    letters" was never implemented** - now applied via upper() in every
    designation label expression, regardless of what case the user
    actually types.
Two further H fields - STATUS_LABELS (H.5.1.1.3/Table H-I: present=
solid, planned=dashed) and ECHELON_LABELS (H.5.1.1.6, Table D-III of the
Land appendix) - were added to the Lines layer's schema, since Boundary
needs both; every future measure type can reuse the same two fields
rather than each reinventing them. Boundary itself was rebuilt from an
invented dash-dash-dot placeholder into the real Table H-III
construction: a status-driven solid/dashed line (see
_STATUS_LINE_STYLE_EXPRESSION) with the near designation, Field B
echelon glyph (Table D-III), and far designation stacked as one repeating
label along the line, QGIS's own Selective Masking cutting a genuine
gap in the line under whatever that label renders - see
_boundary_symbol()'s and _control_measure_shared.py's own
_configure_designation_labeling() docstrings for the construction
(including two earlier, wrong echelon-glyph attempts before masking)
and what's still approximated (an interval-based repeat standing in for
the standard's own per-segment repeat rule, no attempt at Figure H-3's
compass-relative label rotation, no monochrome "ENY" fallback). sidc.py's
own ECHELONS (and every point-symbol layer's Echelon dropdown, via
_point_symbol_layer.py's _ECHELON_LABELS) gained the three highest
Table D-III levels - Army Group, Theater, Command - that had been
missing entirely since sub-phase 10.1, found while reading H.5.1.1.6's
own cross-reference to that table.

**2026-08-09: Mini-Phase H2 (H.5.9 Area of Operations + H.5.10 C2
measure symbols)** built Light Line (Table H-IV) and the four Table H-V
areas (Area of Operations/Named Area of Interest/Target Area of
Interest/Airfield Zone, previously empty since H0). Area of Operations/
Named+Target Area of Interest/Airfield Zone all share one status-driven
solid/dashed outline recipe (_status_driven_area_outline_symbol());
Area of Operations/NAI/TAI are each labelled with a fixed type
abbreviation ("AO"/"NAI"/"TAI") plus an optional name
(_AREA_DESIGNATION_LABEL_EXPRESSION, e.g. "AO BUFFALO"); the
template/example pictures' own hexagon for NAI/TAI is confirmed
illustrative, not mandated (the DRAW RULES text ties the shape to the
user's own anchor points, identical wording to Area of Operations/
Airfield Zone). Live testing then caught real construction mistakes,
each documented on the specific function it fixed:
  - Light Line's first version drew an invented perpendicular "tick" at
    each end (misreading the template's own up-arrow callouts as drawn
    geometry) and put its own "LL" label below the line instead of
    above - see _end_label_layer()'s own docstring for the full
    correction and the general "grey = explanatory, not the arrow
    itself" lesson this taught for reading the rest of this appendix.
  - Airfield Zone's first version used a symmetric "X" icon and centred
    its own runway-length label inside the boundary, overlapping the
    icon - see _airfield_zone_symbol()'s and
    _configure_area_designation_labeling()'s own docstrings for both
    corrections (an asymmetric two-line icon, and QGIS's own
    Qgis.LabelPlacement.OutsidePolygons placement via
    QgsRuleBasedLabeling).

**2026-08-10: this module gained a third layer, Points (Table H-VI,
Command and control points, H.5.10)**, moved out of the shared, ~90-entry
control_measure_points.py dropdown at the project maintainer's own
request - the same "own layer(s)" convention Lines/Areas already follow
here, extended to this group's own point-type entities too. Rendered
through milsymbol.js (mct_build_sidc/mct_sidc_svg), a completely
different mechanism from this module's own hand-built Lines/Areas
symbology above - see POINT_ENTITY_LABELS' own comment for the full
entity list and control_measure_points.py's own _ENTITY_LABELS comment
for what moved where. This also closes out task #33's own "Table H-VI
pending audit" note by construction.

Military Cartography Tools
"""

import math

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    stabilised_point_size_expression,
    AFFILIATION_LABELS,
    ECHELON_LABELS,
    POINT_AFFILIATION_LABELS,
    STATUS_LABELS,
    _ECHELON_CHARACTER_EXPRESSION,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_echelon_field,
    _configure_status_field,
    _end_label_layer,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "C2 Measures (Lines)"
AREAS_LAYER_NAME = "C2 Measures (Areas)"
POINTS_LAYER_NAME = "C2 Measures (Points)"

# Re-exported for callers/tests that only need this module's own
# constants, not every H control-measure module's shared ones.
__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "POINTS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "POINT_ENTITY_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "ECHELON_LABELS",
    "create_c2_measures_lines_layer",
    "create_c2_measures_areas_layer",
    "add_c2_measures_lines_layer",
    "add_c2_measures_areas_layer",
    "create_c2_measures_points_layer",
    "add_c2_measures_points_layer",
]

# Boundary (H0) and Light Line (H2, Table H-IV - the only other buildable
# entry in that table; "Lateral/Forward/Rear Boundary" are usage examples
# of Boundary itself, not separate control measures, per that table's own
# "see Table H-III" cross-reference) are the only line measure types
# re-verified against the real standard so far.
LINE_MEASURE_TYPE_LABELS = {
    "boundary": "Boundary",
    "light_line": "Light Line (LL)",
}

# Table H-V (Command and Control Areas, Mini-Phase H2) - Area of
# Operations, Named/Target Area of Interest, and Airfield Zone. Battle
# Position/Strong Point/Engagement Area (H.5.12.1), Assembly Area
# (H.5.11), and Encirclement (H.5.14) all belong to OTHER H.5.x logical
# sections (Defensive/Maneuver), so they'll live in THOSE sections' own
# future modules, not here, once built.
AREA_MEASURE_TYPE_LABELS = {
    "area_of_operations": "Area of Operations (AO)",
    "named_area_of_interest": "Named Area of Interest (NAI)",
    "target_area_of_interest": "Target Area of Interest (TAI)",
    "airfield_zone": "Airfield Zone",
}

# _boundary_symbol()'s/_light_line_symbol()'s own line symbol layers'
# stable ids - referenced by _control_measure_shared.py's own
# _configure_designation_labeling()'s QgsSymbolLayerReference list so the
# Lines layer's shared label mask knows which symbol layers to cut a
# hole in (masking is configured once per LAYER, on the shared
# QgsTextFormat every rule's label uses - so every line measure type
# whose own name/glyph should be masked needs its line's own id added
# here).
_BOUNDARY_LINE_SYMBOL_LAYER_ID = "boundary_line"
_LIGHT_LINE_SYMBOL_LAYER_ID = "light_line_line"

# Table H-V (Mini-Phase H2): each of these areas is labelled with its own
# fixed type abbreviation (Field A) followed by an optional name (Field
# T) - "AO BUFFALO", "NAI 1", "TAI YUKON" in the standard's own examples.
# Airfield Zone has no Field A abbreviation in its own template (an icon
# instead - see _airfield_zone_symbol()'s own comment), so it's
# deliberately not one of these three and falls through to the plain
# expression below.
_AREA_LABEL_PREFIXES = {
    "area_of_operations": "AO",
    "named_area_of_interest": "NAI",
    "target_area_of_interest": "TAI",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN "
    f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
) + f" ELSE {_PLAIN_DESIGNATION_LABEL_EXPRESSION} END"


def _boundary_symbol():

    """
    Table H-III. Rebuilt 2026-08-09 (Mini-Phase H0) after comparing the
    previous version - an invented dash-dash-dot pattern with no
    echelon/designation content at all - against the actual template
    picture (page 395): a Present boundary is a plain SOLID line and a
    Planned/On Order one is DASHED (H.5.1.1.3/Table H-I, see
    _STATUS_LINE_STYLE_EXPRESSION).

    The Field B echelon amplifier and the two units' own designations
    (Field T/AS) are NOT built here as symbol layers at all - see
    _control_measure_shared.py's own _configure_designation_labeling()
    comment for why they're all folded into a single, masked, repeating
    LABEL instead. This function only builds the line itself, but gives
    its one symbol layer a stable `.setId()` (_BOUNDARY_LINE_SYMBOL_
    LAYER_ID) so that label masking can target it specifically by
    reference.

    This function went through three real, wrong attempts at the
    echelon glyph before landing on labelling+masking, each one caught by
    the project maintainer rendering a real boundary over a non-white
    (terrain) background rather than QGIS's own white canvas default -
    text alone never surfaced any of these, only rendering did:
      1. A bordered white square behind the glyph (obviously a box
         against colour - Table H-III's own EXAMPLE column shows a clean
         line GAP, no box of any kind).
      2. Dropping just the border, keeping a solid white fill (still
         plainly a flat white rectangle against anything but a white
         background - the fill itself was the problem, not the outline).
      3. A white HALO around the glyph's own character outline (a stroke
         on QgsFontMarkerSymbolLayer, no background shape at all) - closer
         in spirit, but QGIS's own font-glyph stroke rendering produced a
         messy, spiky white burst around "X" rather than a clean hourglass
         gap, confirmed by the maintainer's own live-QGIS screenshot (not
         reproduced in this project's own offscreen renders, which looked
         fine - real-world font rendering differed enough to matter).
    The actual fix: QGIS's own Selective Masking feature
    (QgsTextMaskSettings + QgsSymbolLayerReference) - the label engine
    genuinely cuts a hole in the referenced symbol layer's own rendered
    geometry, in the exact shape of the rendered text, at every position
    the text renders in the entire label pass. This lets whatever is
    actually underneath (terrain, imagery, other layers) show through
    correctly, is crisp for any glyph width (no adjacent-character
    blur), and requires no bespoke shape-fitting per echelon level - the
    correct tool for this job, not an approximation of one.
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

    line_layer.setId(
        _BOUNDARY_LINE_SYMBOL_LAYER_ID
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    return symbol


def _light_line_symbol():

    """
    Table H-IV, code 110200 (page 397). "Designated line forward of
    which vehicles are required to use black-out lights at night." A
    plain status-driven solid/dashed line (H.5.1.1.3) with a fixed "LL"
    label above each end (PT1/PT2 in the standard's own template
    picture) - see _end_label_layer()'s own comment for why an earlier
    version of this also drew a perpendicular tick at each end, and why
    that was wrong (the template's own up-arrows are diagram callouts,
    not drawn geometry).

    The template's own EXAMPLE column also shows an illustrative
    "PL CRAB" name in GREY next to the (real, black) "LL" labels -
    H.5.7's own text confirms naming any line as a phase line is
    optional, not mandatory, "labeled... at both ends of the line... or
    as often as necessary for clarity" (its own words for a NAMED line's
    own purpose field, T1) - an optional name the user enters in
    "unique_designation" already renders via this layer's general
    along-line labelling, REPEATING along the line the same way
    Boundary's own label does (see _BOUNDARY_DESIGNATION_LABEL_
    EXPRESSION's own ELSE branch and _BOUNDARY_LABEL_REPEAT_DISTANCE_MM),
    which happens to already match H.5.7's own "as often as necessary"
    wording - not planned when that repeat distance was first added for
    Boundary alone, but confirmed correct here by rendering a long Light
    Line and checking the name repeats legibly rather than assuming.
    This line's own symbol layer gets a stable `.setId()`
    (_LIGHT_LINE_SYMBOL_LAYER_ID) for the same reason Boundary's does -
    so that repeating name can be masked with a real gap too, not just
    text painted over the line (confirmed by rendering both ways; a
    plain top-of-line label instead of a proper mask still let the line
    show through the open parts of each letter, e.g. inside a "C" or "R"
    - a smaller version of the exact box-vs-halo-vs-mask lesson
    documented on _boundary_symbol() itself) - independent of the tick
    correction above, since this optional name sits on the line either
    way.
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

    line_layer.setId(
        _LIGHT_LINE_SYMBOL_LAYER_ID
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    for placement in (
        QgsTemplatedLineSymbolLayerBase.Placement.FirstVertex,
        QgsTemplatedLineSymbolLayerBase.Placement.LastVertex,
    ):

        symbol.appendSymbolLayer(
            _end_label_layer(placement, "LL")
        )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "boundary": _boundary_symbol,
    "light_line": _light_line_symbol,
}


def _area_of_operations_symbol():

    # Table H-V, code 120100. "An area of operations is an operational
    # area defined by a joint commander for land or maritime forces to
    # conduct military activities" (H.5.9) - "AO" + an optional name
    # (e.g. "AO BUFFALO"), see _AREA_DESIGNATION_LABEL_EXPRESSION.
    return _status_driven_area_outline_symbol()


def _named_area_of_interest_symbol():

    # Table H-V, code 120200. "A geographical area where information is
    # gathered to satisfy specific intelligence requirements." The
    # template/example pictures both draw this (and Target Area of
    # Interest below) as a hexagon, but the DRAW RULES text itself ties
    # the shape to the user's own anchor points exactly like every other
    # area here ("at least three anchor points... Size/Shape. Determined
    # by the anchor points") - the hexagon is this appendix's own
    # illustrative example, not a mandated regular shape, so this
    # renders whatever polygon the user actually digitizes, the same as
    # Area of Operations/Airfield Zone, rather than forcing a regular
    # hexagon onto arbitrary anchor points.
    return _status_driven_area_outline_symbol()


def _target_area_of_interest_symbol():

    # Table H-V, code 120300. "The geographical area where high-value
    # targets can be acquired and engaged by friendly forces" - see
    # _named_area_of_interest_symbol()'s own comment for why this
    # doesn't force the template picture's own hexagon shape either
    # (identical DRAW RULES text, anchor-point-determined).
    return _status_driven_area_outline_symbol()


def _airfield_zone_symbol():

    """
    Table H-V, code 120400. The only one of this table's four areas
    whose own template picture has no Field A text abbreviation at all -
    instead a crossed-runway-lines icon sits at the area's own centre
    ("Note: The Field 'H' for this symbol includes type of airfield,
    length of runway and other pertinent information" - Field H is a
    free-text amplifier this layer doesn't render as its own visual
    element, the same scope choice already made for every other H field
    this module doesn't dedicate a symbol layer to).

    **Corrected 2026-08-09** after live-testing: the template/example
    picture (page 400) draws two runway lines crossing at an *unequal*
    angle (one nearly flat, the other roughly 35 degrees off it) -
    recognisably two intersecting runways, not a symmetric X. The first
    version used QGIS's own "cross2" simple-marker shape (a plain,
    symmetric 90-degree X), which the maintainer flagged as wrong.
    Rebuilt as two independent "line" simple-marker layers at different
    angles instead of one "cross2" layer - still a "recognisable, not
    exact" stand-in for the standard's own specific glyph (no attempt to
    match a real runway heading), just an asymmetric one this time.
    """

    symbol = _status_driven_area_outline_symbol()

    icon_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "line",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.6",
            "size": "6",
            "angle": "90",
        }
    )

    second_runway = QgsMarkerSymbol.createSimple(
        {
            "name": "line",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.6",
            "size": "6",
            "angle": "50",
        }
    )

    icon_marker.appendSymbolLayer(
        second_runway.symbolLayer(0).clone()
    )

    for layer_index in range(icon_marker.symbolLayerCount()):

        _apply_affiliation_color(
            icon_marker.symbolLayer(layer_index),
            [QgsSymbolLayer.Property.StrokeColor]
        )

    icon_layer = QgsGeometryGeneratorSymbolLayer.create({})

    icon_layer.setGeometryExpression(
        "centroid($geometry)"
    )

    icon_layer.setSymbolType(
        Qgis.SymbolType.Marker
    )

    icon_layer.setSubSymbol(
        icon_marker
    )

    symbol.appendSymbolLayer(
        icon_layer
    )

    return symbol


_AREA_SYMBOL_BUILDERS = {
    "area_of_operations": _area_of_operations_symbol,
    "named_area_of_interest": _named_area_of_interest_symbol,
    "target_area_of_interest": _target_area_of_interest_symbol,
    "airfield_zone": _airfield_zone_symbol,
}

# Table H-III shows THREE things stacked at each anchor-point segment:
# the near unit's Field T/AS above, the Field B echelon amplifier in a
# gap in the line, and the far unit's Field T/AS below - built here as a
# single 3-line label rather than a separate marker for the echelon glyph
# (see _boundary_symbol()'s own comment for the two earlier, wrong
# attempts at a separate marker), with QGIS's own Selective Masking
# cutting the actual line-gap around whatever this label renders (see
# _control_measure_shared.py's own _configure_designation_labeling()
# comment). The echelon line and the far-designation line are each
# independently optional - CASE expressions add them only when
# populated, so a boundary with no echelon selected still gets a clean
# 2-line (or 1-line, with no far designation either) label instead of a
# blank middle row. upper() wraps only the two text fields (H.5.4's own
# "all caps" rule is about TEXT labeling, not the echelon's own graphic
# amplifier), not the glyph itself (harmless either way for "X"/"Ø"/
# "++", but scoped correctly on principle). Falls through to the plain
# expression for every other measure type (which has no reason to ever
# populate echelon/far_designation), so nothing here changes their own
# rendering.
# **2026-08-18 fix, from the maintainer's own smoke test.** Two faults,
# both in the expression below, and both invisible until someone selected
# an echelon WITHOUT also typing designations:
#
# 1. **An echelon on its own rendered nothing at all.** The expression
#    opened with a bare `upper("unique_designation")`, and QGIS collapses
#    the whole `||` chain to NULL the moment any operand is NULL - the
#    same trap this project has hit before (see grid_labels.py). With no
#    near designation typed, the label was NULL and the echelon glyph
#    the user had explicitly chosen simply never drew. Every part is now
#    coalesce()-wrapped.
#
# 2. **The glyph landed in the wrong place unless all three were set.**
#    Table H-III stacks THREE rows - near designation, echelon glyph in
#    the line gap, far designation - and the mask cuts the line around
#    the label's MIDDLE. Building the label from only the populated rows
#    meant that with two rows the echelon was the bottom one, so it sat
#    below the line instead of in it; with three it happened to be right.
#    The maintainer's own report: "if I select an echelon and unique
#    modifier then it shows unique designation on top of the line and
#    echelon on the bottom... if I select all three then it renders
#    fine."
#
# So when an echelon IS chosen the label is always three rows, padding
# absent designations with a single space to hold the glyph in the middle
# - the maintainer's own suggested fix. When no echelon is chosen nothing
# needs holding in place, so the label stays compact and a boundary with
# no amplifiers at all still renders no label rather than three blank
# rows with a gap cut through the line for them.
_BOUNDARY_NEAR = 'coalesce(upper("unique_designation"), \' \')'
_BOUNDARY_FAR = 'coalesce(upper("far_designation"), \' \')'

_BOUNDARY_HAS_ECHELON = '"echelon" IS NOT NULL AND "echelon" != \'\''

_BOUNDARY_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'boundary' THEN "
    f"CASE WHEN {_BOUNDARY_HAS_ECHELON} THEN "
    f"{_BOUNDARY_NEAR} || '\\n' || ("
    + _ECHELON_CHARACTER_EXPRESSION
    + f") || '\\n' || {_BOUNDARY_FAR}"
    " ELSE "
    f"{_BOUNDARY_NEAR}"
    " || CASE WHEN \"far_designation\" IS NOT NULL AND \"far_designation\" != ''"
    f" THEN '\\n' || upper(\"far_designation\") ELSE '' END"
    " END"
    f" ELSE {_PLAIN_DESIGNATION_LABEL_EXPRESSION} END"
)

# How often the boundary label (and the line-gap masked around it)
# repeats along a digitized boundary - approximates Table H-III's own
# "the line segment between each pair of anchor points will repeat all
# information" rule, which is genuinely per-SEGMENT (one repeat per
# digitized vertex pair, regardless of segment length) - QGIS's own
# label repeat is interval-based (evenly spaced by real screen distance,
# not tied to vertex positions), so this is a practical approximation of
# the standard's own per-segment rule rather than an exact match, the
# same "recognisable, not exact" standard this module applies elsewhere.
# Picked at a size that reads clearly repeated on a real multi-segment
# boundary without crowding a short one - confirmed by rendering one.
_BOUNDARY_LABEL_REPEAT_DISTANCE_MM = 80


def _configure_area_designation_labeling(layer):

    """
    Table H-V's own four areas don't all label the same way. Area of
    Operations/Named Area of Interest/Target Area of Interest are all
    labelled INSIDE their own boundary, centred over the polygon (the
    standard's own "AO BUFFALO"/"NAI 1"/"TAI YUKON" examples) -
    Qgis.LabelPlacement.OverPoint, unchanged from before. Airfield
    Zone's own runway-length label (page 400's own "750M" example, Field
    H - "type of airfield, length of runway and other pertinent
    information") sits OUTSIDE the bounded area instead, just past its
    edge - flagged as a real construction error during live testing
    (the first version centred it inside, over the crossed-runway icon,
    like every other area here).

    That's a genuinely different PLACEMENT, not just different text, so
    one shared QgsPalLayerSettings (what every other labelled layer in
    this module gets by with) can't express it - QGIS's own rule-based
    labeling (QgsRuleBasedLabeling, the labeling analogue of
    _control_measure_shared.py's own _build_rule_based_renderer()'s
    QgsRuleBasedRenderer) is the correct tool, one rule per placement.
    Qgis.LabelPlacement.OutsidePolygons is QGIS's own dedicated
    placement mode for exactly this situation - label a polygon by
    placing the label just outside its own boundary, on whichever side
    actually clears it - rather than hand-computing a fixed offset from
    the polygon's own bounding box, which would sit inside a large
    Airfield Zone or float an unnecessarily large distance from a small
    one.
    """

    # Explicit, mutually-exclusive filters on both rules rather than
    # setIsElse(True) on the default one - each rule in
    # QgsRuleBasedLabeling gets its own independent sub-provider, and
    # (confirmed by rendering both ways) an else-flagged rule's provider
    # still placed its own label for airfield_zone features too, giving
    # every Airfield Zone feature two labels (one centred, one outside)
    # instead of one - unlike QgsRuleBasedRenderer's single-provider
    # tree walk, where isElse means what its name suggests. Two
    # explicit, non-overlapping expressions sidestep that entirely.
    default_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _AREA_DESIGNATION_LABEL_EXPRESSION
        )
    )

    default_rule.setFilterExpression(
        '"measure_type" IS NULL OR "measure_type" != \'airfield_zone\''
    )

    airfield_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OutsidePolygons,
            _AREA_DESIGNATION_LABEL_EXPRESSION
        )
    )

    airfield_rule.setFilterExpression(
        '"measure_type" = \'airfield_zone\''
    )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(
        airfield_rule
    )

    root_rule.appendChild(
        default_rule
    )

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )


def create_c2_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for C2 measures - a "measure_type"
    ValueMap dropdown (currently Boundary/Light Line - see this module's
    own docstring) plus a "unique_designation" text field, labelled
    directly on each line. Digitized with QGIS's own native "Add Line
    Feature" tool - see this module's own docstring and unit_layer.py's
    for why no custom drawing tool exists.

    "status"/"echelon"/"far_designation" were added 2026-08-09 (Mini-
    Phase H0) for Boundary's own rebuild - see _control_measure_shared.
    py's own STATUS_LABELS/ECHELON_LABELS comments for why they're
    general-purpose H fields present on the schema for every measure
    type, but so far only wired into rendering for "boundary"
    specifically.
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
            QgsField("echelon", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("far_designation", QMetaType.Type.QString),
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
        QgsDefaultValue("'boundary'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)
    _configure_echelon_field(layer)

    # applyOnUpdate=True ("Recalculate value on update") keeps this in
    # sync as the line is reshaped, not just at initial digitizing -
    # confirmed live via QgsVectorLayerUtils.createFeature() (what the
    # GUI's own "Add Line Feature" tool calls) and via a geometry-only
    # edit through updateFeature()/commitChanges().
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
        _BOUNDARY_DESIGNATION_LABEL_EXPRESSION,
        repeat_distance_mm=_BOUNDARY_LABEL_REPEAT_DISTANCE_MM,
        masked_symbol_layer_ids=[
            _BOUNDARY_LINE_SYMBOL_LAYER_ID, _LIGHT_LINE_SYMBOL_LAYER_ID
        ]
    )

    return layer


def create_c2_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for area-type C2 measures - same shape
    as create_c2_measures_lines_layer(). Currently offers Table H-V's
    own four areas (Mini-Phase H2). Digitized with QGIS's own native
    "Add Polygon Feature" tool.

    "status" was added 2026-08-09 (Mini-Phase H2) - H.5.1.1.3/Table H-I's
    present=solid/planned=dashed rule explicitly covers "area control
    measures" by its own text, not just linear ones (see the Lines
    layer's own STATUS_LABELS comment for the general-field precedent).
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
        QgsDefaultValue("'area_of_operations'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    # applyOnUpdate=True - see create_c2_measures_lines_layer()'s own
    # comment on length_km for why, and
    # expressions/military_symbology_functions.py's _distance_area()
    # docstring for why these expressions take only $geometry, not
    # $geometry + @layer.
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

    _configure_area_designation_labeling(layer)

    return layer


def add_c2_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_c2_measures_lines_layer
    )


def add_c2_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_c2_measures_areas_layer
    )


# Table H-VI (Command and control points, H.5.10) - moved into its own
# dedicated layer here 2026-08-10, out of the shared, ~90-entry
# control_measure_points.py dropdown (the project maintainer's own
# request: "command and control points should have their own dedicated
# layer... that will also reduce the number of symbols in the Control
# Measure Points" - the same "own layer(s)" convention this module's own
# docstring already documents for Lines/Areas, extended to this group's
# own points too. Closes task #33's own "Table H-VI pending audit" note
# by construction - every entry here is now this table's own, not a
# guess at which of the shared layer's ~90 entries belonged to it).
# Rendered through milsymbol.js (mct_build_sidc/mct_sidc_svg), the SAME
# mechanism control_measure_points.py itself uses - a completely
# different rendering pipeline from this module's own hand-built Lines/
# Areas symbology above, so this section is self-contained.
#
# **2026-08-10 correction, found by the project maintainer's own live
# testing via the Appendix H smoke-test tracker**: Fly-To Point
# (Sonobuoy/Weapon/Normal, codes 131001-131003) and Point of Interest -
# Launch Event (131301) were both missing entirely - a real gap in the
# original ~80-entry curation (sidc.py's own ENTITIES["control_measure"]),
# not something built elsewhere under a different name (confirmed by
# grepping the whole codebase). Added here, and to sidc.py's own dict,
# after confirming the exact codes/names directly against the vendored
# milsymbol.js source (`t[131001]=C["TP.FLY-TO-POINT (SONOBUOY)"]`, etc.)
# rather than guessing - the same "check milsymbol.js first" discipline
# every other entity addition in this project follows.
POINT_ENTITY_LABELS = {
    "unspecified_control_point": "Unspecified Control Point",
    "amnesty_point": "Amnesty Point",
    "checkpoint": "Checkpoint",
    "center_of_main_effort": "Center of Main Effort",
    "contact_point": "Contact Point",
    "coordinating_point": "Coordinating Point",
    "decision_point": "Decision Point",
    "distress_call": "Distress Call",
    "entry_control_point": "Entry Control Point",
    "fly_to_point_sonobuoy": "Fly-To Point (Sonobuoy)",
    "fly_to_point_weapon": "Fly-To Point (Weapon)",
    "fly_to_point_normal": "Fly-To Point (Normal)",
    "linkup_point": "Linkup Point",
    "passage_point": "Passage Point",
    "point_of_interest": "Point of Interest",
    "point_of_interest_launch_event": "Point of Interest - Launch Event",
    "rally_point": "Rally Point",
    "release_point": "Release Point",
    "start_point": "Start Point",
    "special_point": "Special Point",
    "waypoint": "Waypoint",
}

# H.5.3's own affiliation rule for POINT control measures is the base
# standard's ordinary friend/hostile/neutral/unknown vocabulary (no
# "unspecified" 5th value) - milsymbol.js already renders it correctly
# with no extra code needed, exactly as control_measure_points.py's own
# docstring documents; this is deliberately NOT the same
# AFFILIATION_LABELS this module's own Lines/Areas layers import from
# _control_measure_shared (that 5-value, "unspecified"-inclusive set is
# specific to the hand-built line/fill symbology's own data-defined
# colour expression, a different rendering mechanism entirely).
# The four real SIDC standard identities - see
# POINT_AFFILIATION_LABELS in _control_measure_shared.py for why a
# Points layer must not use the lines/areas AFFILIATION_LABELS.
_POINT_AFFILIATION_LABELS = POINT_AFFILIATION_LABELS

_POINT_STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned",
}

DEFAULT_POINT_MARKER_SIZE_MM = 8.0

# **2026-08-10, found by the project maintainer's own live testing**:
# several icons render visibly smaller/fainter than their siblings at
# the same nominal marker size - not a stroke-width difference (every
# icon's own rendered SVG uses the identical stroke-width="3", confirmed
# by rendering each one's raw SVG directly and comparing), but simply
# that a fixed mm marker size reads differently depending on how much of
# that icon's own bounding box the actual drawn shape fills. milsymbol.js
# has no separate "make the lines bolder" option (checked - no
# strokeWidth-style option exists in its own source), so the only lever
# available is the overall marker size, which the project maintainer
# gave explicit target increases for: Decision Point +20% (Airfield had the same, but was removed
# 2026-08-12 as AEGIS-only),
# Coordinating Point/Contact Point +15% each. Center of Main Effort
# started at +10%, still reported too small/faint, raised to +15% to
# match the others.
#
# The three Fly-To Point variants are a related but distinct case, found
# the same way (the maintainer's own live testing): their OUTER box+cone
# shape is actually identical in size to Checkpoint's own (confirmed by
# comparing raw SVG output dimensions directly, both 30.8x58.8 at the
# same milsymbol {size} option) - what reads smaller/fainter is the MAIN
# TEXT inside it, since "FTP" plus a 3-letter code needs two lines
# ("FTP"/"SBY") where Checkpoint's own "CKP" only needs one, and
# milsymbol.js shrinks the font to fit two lines into the same box
# height. Same fix, same lever (no separate font-size option either) -
# +15%, matching Coordinating/Contact Point's own successful fix.
_POINT_SIZE_MULTIPLIERS = {
    "decision_point": 1.20,
    "center_of_main_effort": 1.15,
    "coordinating_point": 1.15,
    "contact_point": 1.15,
    "fly_to_point_sonobuoy": 1.15,
    "fly_to_point_weapon": 1.15,
    "fly_to_point_normal": 1.15,
}

_POINT_SIZE_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"entity\" = '{entity}' THEN {DEFAULT_POINT_MARKER_SIZE_MM * multiplier}"
    for entity, multiplier in _POINT_SIZE_MULTIPLIERS.items()
) + f" ELSE {DEFAULT_POINT_MARKER_SIZE_MM} END"

# Which of milsymbol.js's own several text-modifier options actually
# renders this module's single "unique_designation" attribute in the
# position the standard's own EXAMPLE column shows for THAT SPECIFIC
# icon - read directly from milsymbol.js's own per-icon position-config
# objects (2026-08-10, found while investigating the project
# maintainer's own live-testing reports that several entities weren't
# showing their designation "in the centre"/"below the main text" as
# expected, and that Unspecified Control Point's own showed up entirely
# outside the icon instead of inside). See mct_sidc_svg()'s own
# docstring for why this is an entity-by-entity lookup, not a global
# constant - milsymbol.js's own option naming is NOT consistent across
# icons. Every entity not named here either uses the default
# `uniqueDesignation` (Contact Point, Decision Point, Point of Interest,
# Airfield, Waypoint, and by extension anything else not yet
# individually checked) or has no text-modifier slot at all (Center of
# Main Effort, Coordinating Point, Special Point, Point of Interest -
# Launch Event) - passing a slot to an icon that doesn't define it is a
# harmless no-op (confirmed live), so those don't need special-casing.
_POINT_TEXT_SLOT_OVERRIDES = {
    "amnesty_point": "uniqueDesignation1",
    "checkpoint": "uniqueDesignation1",
    "distress_call": "uniqueDesignation1",
    "entry_control_point": "uniqueDesignation1",
    "linkup_point": "uniqueDesignation1",
    "passage_point": "uniqueDesignation1",
    "rally_point": "uniqueDesignation1",
    "release_point": "uniqueDesignation1",
    "start_point": "uniqueDesignation1",
    "unspecified_control_point": "additionalInformation1",
}

_POINT_TEXT_SLOT_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"entity\" = '{entity}' THEN '{slot}'"
    for entity, slot in _POINT_TEXT_SLOT_OVERRIDES.items()
) + " ELSE 'uniqueDesignation' END"

# Literal 'control_measure'/'unspecified'/false for the symbol_set/
# echelon/headquarters positions mct_build_sidc() still requires - this
# layer has no fields for them, matching control_measure_points.py's own
# _SIDC_EXPRESSION exactly. The "unique_designation" field IS passed
# through - as mct_sidc_svg()'s own second argument, routed to whichever
# slot _POINT_TEXT_SLOT_EXPRESSION picks for that entity via the third -
# see that function's own docstring for the 2026-08-10 fix this was
# missing entirely before. coalesce(...,'') - never a bare NULL - because
# QGIS's own expression engine short-circuits an ENTIRE function call to
# NULL the moment any argument evaluates to NULL (confirmed live: a bare
# `"unique_designation"` reference on a feature that left that field
# blank silently broke the whole rendered icon, not just the missing
# text), and mct_sidc_svg() itself already treats an empty string as "no
# designation" so this is safe either way. upper(...) around it - per
# H.5.4 Labeling ("All text labeling shall be in upper case letters"),
# the same rule already enforced on this appendix's own hand-built line/
# area labels via _PLAIN_DESIGNATION_LABEL_EXPRESSION - missed here at
# first (2026-08-10, found by the project maintainer's own live testing)
# since this expression reaches milsymbol.js's own text options directly
# rather than going through that shared expression at all.
_POINT_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false),"
    "upper(coalesce(\"unique_designation\",'')),"
    + _POINT_TEXT_SLOT_EXPRESSION +
    ")"
)


def _configure_points_attribute_form(layer):

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    entity_idx = fields.indexOf("entity")
    status_idx = fields.indexOf("status")

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
            "ValueMap",
            {"map": _value_map(POINT_ENTITY_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_POINT_STATUS_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue("'checkpoint'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))


# Every entity sharing the box+cone icon construction (confirmed by an
# IDENTICAL rendered SVG path across all of them, not assumed from name
# similarity alone) shares the SAME "Anchor Points" draw rule too: "This
# symbol requires one anchor point. The point defines the TIP of the
# inverted cone" (read directly for Unspecified Control Point/Amnesty
# Point/Checkpoint/Distress Call - pages 401-403 - and inferred for the
# rest of this identically-shaped group by construction, not guessed
# blind). QGIS's own default SVG marker anchor is the drawn content's
# own bounding-box CENTRE, which is wrong for all of these - the
# project maintainer's own observation, generalising past what was
# first flagged only for Distress Call's own missing diagonal line:
# "in all these symbols, it is better if the symbol is drawn where the
# user clicks... if you notice even in the manual, the symbol is drawn
# AT the anchor point and not around it". Fixed via QGIS's own built-in
# `VerticalAnchor` symbol layer property (confirmed empirically -
# `Qgis.LabelQuadrantPosition`-style guessing wasn't needed here, a
# `verticalAnchorPoint`/`horizontalAnchorPoint` pair exists on
# QgsMarkerSymbolLayer specifically for this - a controlled 3-value
# render comparison, "center"/"bottom"/"top", confirmed "bottom" moves
# the SVG's own bottom edge - the cone's tip, for this whole group - to
# exactly the feature's own digitized point), data-defined per entity so
# every OTHER entity on this layer keeps the default centred anchor its
# own draw rules actually call for (e.g. Contact Point/Coordinating
# Point/Waypoint/Airfield's own text: "typically centered over the
# desired location").
_POINT_ENTITIES_ANCHORED_AT_TIP = (
    "'unspecified_control_point', 'amnesty_point', 'checkpoint', "
    "'distress_call', 'entry_control_point', 'linkup_point', "
    "'passage_point', 'rally_point', 'release_point', 'start_point'"
)

_POINT_VERTICAL_ANCHOR_EXPRESSION = (
    "CASE WHEN \"entity\" IN (" + _POINT_ENTITIES_ANCHORED_AT_TIP + ")"
    " THEN 'bottom' ELSE 'center' END"
)

# Distress Call's own diagonal anchor-point line (Table H-VI, code
# 130800, page 403) - confirmed missing entirely from milsymbol.js's own
# vendored icon definition (found by decoding its raw SVG path data
# directly: the drawn shape stops exactly at the cone's own tip, with no
# further segment). Rather than hand-patch the vendored third-party
# file, drawn as a SEPARATE QgsMarkerSymbol layer stacked on top of the
# SVG marker, enabled only for this one entity via a data-defined
# LayerEnabled property. Now that the SVG marker's own anchor IS the
# cone's tip (see above), this line's own construction is simple: start
# at (0, 0) - the feature's own point, now genuinely the tip - and
# extend outward by its own full length.
#
# The line's own LENGTH comes from the icon's own known local SVG
# coordinates (not measured by eye): the box+cone shape spans local x
# [60,140] (width 80); at the same DEFAULT_POINT_MARKER_SIZE_MM scale
# this project already uses, that's `DEFAULT_POINT_MARKER_SIZE_MM * 80
# / 215.33` mm (215.33 being the icon's own full local viewBox width,
# the value milsymbol.js scales to DEFAULT_POINT_MARKER_SIZE_MM in the
# first place) - matching the standard's own template text: "same
# length as the width of the rectangle".
#
# The line's own ANGLE (shallow, down-and-left) was measured directly
# from the standard's own template picture (page 403) by pixel-tracing
# the drawn diagonal there, not guessed - approximately 15 degrees below
# horizontal, "recognisable, not exact" like every other decorative
# construction in this project (Fortified Area's own crenellation,
# etc.).
_DISTRESS_CALL_LOCAL_UNITS_TO_MM = DEFAULT_POINT_MARKER_SIZE_MM * 80 / 215.33

_DISTRESS_CALL_ANCHOR_LINE_LENGTH_MM = _DISTRESS_CALL_LOCAL_UNITS_TO_MM

# Degrees below horizontal, measured directly by pixel-tracing the
# standard's own template picture (page 403), not guessed.
_DISTRESS_CALL_ANCHOR_LINE_DEGREES_BELOW_HORIZONTAL = 15

_DISTRESS_CALL_ANCHOR_LINE_ANGLE = (
    90 - _DISTRESS_CALL_ANCHOR_LINE_DEGREES_BELOW_HORIZONTAL
)


# QgsSimpleMarkerSymbolLayer's own `angle` rotates BOTH the drawn shape
# AND its own `offset` together, around the feature's own placement
# point - confirmed with a standalone 4-angle/fixed-offset test render
# (angle=0/90/180/270 against a fixed (0, 5mm) offset) rather than
# assumed: the offset vector (0, D) rotates to (-D, 0)/(0, -D)/(D, 0)
# at angle=90/180/270 respectively, i.e. `angle` is applied as a
# standard counter-clockwise rotation of the (x, y) offset vector
# (y increasing downward, screen convention) by `math.radians(angle)`.
# The line's own anchor is now the correctly-repositioned tip itself
# (see above), so the only offset needed is "extend outward by half the
# line's own length" (the same "shift by half the segment's own length"
# technique already used for Strong Point's own outward-only ticks in
# defensive_control_measures.py, so the drawn segment runs from the tip
# outward only, not back through the box) - pre-rotated by the INVERSE
# of `angle` so QGIS's own forward rotation lands it correctly.
def _distress_call_anchor_line_offset():

    angle_radians = math.radians(_DISTRESS_CALL_ANCHOR_LINE_ANGLE)

    half_length = _DISTRESS_CALL_ANCHOR_LINE_LENGTH_MM / 2

    final_x = half_length * -math.sin(angle_radians)
    final_y = half_length * math.cos(angle_radians)

    inverse = -angle_radians

    return QPointF(
        final_x * math.cos(inverse) - final_y * math.sin(inverse),
        final_x * math.sin(inverse) + final_y * math.cos(inverse),
    )


def _distress_call_anchor_line_layer():

    # Built directly via the concrete QgsSimpleMarkerSymbolLayer class,
    # not extracted from a QgsMarkerSymbol.createSimple() wrapper (the
    # pattern this project's OWN other tick/line markers use, e.g.
    # defensive_control_measures.py's Strong Point) - that pattern keeps
    # the wrapper symbol alive as a genuine SUB-symbol (via
    # setSubSymbol(), which takes real ownership); extracting a wrapper's
    # own symbolLayer(0) and returning it directly, with the wrapper
    # itself going out of scope, segfaulted here on first render - a
    # dangling PyQt/SIP reference, the same class of bug this project's
    # own test-writing conventions already warn about elsewhere.
    line_layer = QgsSimpleMarkerSymbolLayer()

    line_layer.setShape(
        QgsSimpleMarkerSymbolLayerBase.Shape.Line
    )

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setStrokeColor(
        QColor(0, 0, 0)
    )

    line_layer.setStrokeWidth(
        0.5
    )

    line_layer.setSize(
        _DISTRESS_CALL_ANCHOR_LINE_LENGTH_MM
    )

    line_layer.setAngle(
        _DISTRESS_CALL_ANCHOR_LINE_ANGLE
    )

    line_layer.setOffset(
        _distress_call_anchor_line_offset()
    )

    line_layer.setOffsetUnit(
        Qgis.RenderUnit.Millimeters
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.LayerEnabled,
        QgsProperty.fromExpression("\"entity\" = 'distress_call'")
    )

    return line_layer


def _build_points_renderer():

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(
        DEFAULT_POINT_MARKER_SIZE_MM
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_POINT_SIDC_EXPRESSION)
    )

    # Holds the icon still when a designation is typed -
    # see stabilised_point_size_expression().
    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(
            stabilised_point_size_expression(
                _POINT_SIZE_EXPRESSION, _POINT_SIDC_EXPRESSION
            )
        )
    )

    # Re-anchors the box+cone entity family at the cone's own tip instead
    # of QGIS's own default (the drawn shape's bounding-box centre) -
    # see _POINT_VERTICAL_ANCHOR_EXPRESSION's own comment above for why.
    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.VerticalAnchor,
        QgsProperty.fromExpression(_POINT_VERTICAL_ANCHOR_EXPRESSION)
    )

    symbol.changeSymbolLayer(
        0,
        svg_layer
    )

    symbol.appendSymbolLayer(
        _distress_call_anchor_line_layer()
    )

    return QgsSingleSymbolRenderer(symbol)


def create_c2_measures_points_layer(name=POINTS_LAYER_NAME):

    """
    A fresh, empty point layer for Table H-VI (Command and control
    points, H.5.10) - see module docstring for why this is a separate
    layer from Lines/Areas rather than one shared layer (QGIS layers are
    always a single geometry type).
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


def add_c2_measures_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_c2_measures_points_layer
    )
