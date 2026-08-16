# -*- coding: utf-8 -*-

"""
Builds ready-to-use Offensive Control Measures layers - MIL-STD-2525D
Appendix H.5.13 (Table H-X "Offensive Control Measure Symbols"/Axis of
Advance, and Table H-XI "Direction of attack"), the fourth H.5.x
logical group after c2_measures.py, maneuver_control_measures.py, and
defensive_control_measures.py - see c2_measures.py's own docstring for
the full "why a separate module per logical group" rationale and
_control_measure_shared.py for the cross-group helpers this module
reuses.

**Mini-Phase H5, 2026-08-09.**

**Table H-X (Axis of Advance, H.5.13.1) mixes a genuinely real
construction with several still-APPROXIMATED ones.** Every real entry
in it (Friendly Airborne, Friendly Aviation, Attack Helicopter, Main
Attack, Supporting Attack, Axis of Advance for a Feint, Enemy Confirmed/
Templated) is defined by the standard's own DRAW RULES as a variable-
width, tapered "ribbon" - points 1 through N-2 trace a centerline,
point N-1 is the rear, point N sets the width of a triangular
arrowhead in the standard's own general N-point form (3 to 50 anchor
points). **All seven of Table H-X's own "real" entries now have the
real construction, built one at a time 2026-08-10/2026-08-11** ("one
at a time" - the project maintainer's own framing throughout) - see
_axis_of_advance_ribbon_symbol()'s own docstring and expressions/
military_symbology_functions.py's own mct_axis_of_advance_ribbon() -
simplified to exactly 3 clicks (origin/bend/tip) rather than the
standard's own general N-point case, per the project maintainer's own
explicit request. In order: Friendly Airborne first, then Friendly
Aviation (same ribbon, Aviation Rotary Wing icon instead of Infantry+
Airborne-modifier), then Attack Helicopter (same base icon as
Aviation, plus its own crossing-point glyph - see
_attack_helicopter_direction_glyph_layer()'s own docstring), then Main
Attack - a genuinely different case from the other three (no crossing
edges, no unit-context icon, Field T on the shaft at 1/3 distance
instead of at the tip, no Field W-W1, a 20%-wider double-lined
arrowhead - see mct_axis_of_advance_ribbon()'s own `crossed`/
`arrow_width_ratio`/`double_lined_arrowhead` docstrings), finalised
and named "the master arrow" by the project maintainer (see
_MASTER_ARROW_VARIANTS's own comment). Then three more variants, each
reusing the master arrow's own BASE (no double-lined arrowhead - see
_DOUBLE_LINED_ARROWHEAD_VARIANTS's own comment, Main Attack's own
only) but otherwise verbatim: Supporting Attack ("just replicate the
master arrow... no other changes to it"), Axis of Advance for a Feint
(Supporting Attack's own base plus its own distinguishing mark, a
dashed chevron outside the arrowhead - see
_axis_of_advance_outer_chevron_layer()'s own docstring), and Enemy
Confirmed/Templated ("just use the master arrow and default colour to
red" - already true by construction via the shared
_OFFENSIVE_LINE_COLOR_EXPRESSION, not a new colour rule). The old
single-thick-line-plus-arrowhead approximation (`_axis_of_advance_
symbol()`) had no callers left in Table H-X once Enemy moved off it,
so it was deleted outright rather than kept as dead code - Table
H-XI's own Direction of Attack family still uses the analogous
_direction_of_attack_symbol() approximation, unaffected by any of
this.

**Friendly Airborne and Friendly Aviation are two separate selectable
measure_type values sharing one SIDC (151401)** - the standard's own
Table H-X lists them under a single code with two illustrative EXAMPLE
pictures ("Airborne", "Aviation"); split into two dropdown entries
2026-08-10 per the project maintainer's own explicit request ("they
are two different tasks"), the same "one shared construction, several
selectable meanings" pattern Supporting Attack's own Present/Planned
pair already used above.

**Table H-XI (Direction of attack, H.5.13.2) is much more tractable**
- despite reusing several of the same sub-type names (Main Attack,
Supporting Attack, ...), it's a genuinely different, simpler
construction: a plain 2-point line with a small UNFILLED chevron
arrowhead at the end - built for real, not approximated, the same way
Phase Line/FEBA already are. The rest of Table H-XI is a mix of already-
familiar simple line/area patterns (Final Coordination Line, Limit of
Advance, Line of Departure, Line of Departure/Line of Contact, Probable
Line of Deployment, Assault/Attack Position, Objective Area), a two-
parallel-line-plus-Field-T construction (Infiltration Lane, see the
2026-08-10 entry below), and one point symbol (Point of Departure,
likewise see below):
  - **Probable Line of Deployment is ALWAYS dashed** ("the dashed lines
    in this graphic shall be displayed in present AND anticipated
    status" - the standard's own explicit note) - the only line type in
    this whole appendix so far where the shared "status" field's own
    solid-vs-dashed switch doesn't apply; this measure type ignores the
    status field for its own line style.

**Field N ("ENY") is not rendered** on the Enemy-flagged Axis of
Advance/Direction of Attack variants, for the same reason already
established in maneuver_control_measures.py - a colour system doesn't
need the monochrome-only "ENY" fallback text.

**2026-08-10, live-testing follow-up - a large batch of real construction
gaps, all confirmed directly against Table H-X/H-XI's own template
pictures (pages 428-439) before fixing, not from memory**:

  - **Field T (unique designation) and Field W/W1 (DTG range) were
    never rendered at all** on any Axis of Advance/Direction of Attack
    variant, despite both fields already sitting on this layer's own
    schema (Field W/W1 newly added this round - "dtg_start"/"dtg_end",
    matching maneuver_control_measures.py's own Table H-VII precedent
    for the same two fields). Every one of the standard's own EXAMPLE
    pictures shows both - a name ("SWORD", "MAIN", "AVON", ...) and,
    when both DTGs are given, a "DDHHMMZMON YY-DDHHMMZMON YY" range.
    Added via the same data-defined-Character QgsFontMarkerSymbolLayer
    technique maneuver_control_measures.py's own Phase Line already
    established for a per-feature dynamic string (`_end_designation_
    label_layer()`'s own docstring explains why a marker, not the
    general along-line PAL label, is needed) - placed at the line's
    own LastVertex (alongside the arrowhead) rather than the standard's
    own "between points 1 and 2"/"on the shaft near the tip" position,
    close enough to read as "near the tip" for an approximated
    construction that already collapses N anchor points to a single
    line.
  - **Every Axis of Advance sub-type rendered identically** - the
    module's own earlier docstring admitted this outright ("it just
    renders identically to its siblings"). Restored the three
    decorations the standard's own template pictures actually show:
    Attack Helicopter's own perpendicular crossbar near the tip (a
    "line"-shape marker, the same rotate-with-line convention Strong
    Point's own ticks already established in defensive_control_
    measures.py), Main Attack's own doubled/parallel-line outline (two
    close offset copies of the same line, the same technique this
    round's own Infiltration Lane needs anyway), and Direction of
    Attack's own Friendly Aviation bowtie glyph (two opposed Triangle
    marker layers, since QGIS has no native "bowtie" shape) partway
    along the line.
  - **Enemy-flagged variants (Axis of Advance - Enemy, Direction of
    Attack - Enemy) didn't automatically render red** - both still
    respected the ordinary "affiliation" field's own friend/hostile/
    neutral/unknown colour, so a user who picked the "Enemy" measure
    type but left "affiliation" at its own default got a blue (friend-
    coloured) enemy arrow. Fixed with a small local override,
    `_OFFENSIVE_LINE_COLOR_EXPRESSION` (forces red for exactly these
    two measure types, defers to the ordinary shared affiliation
    expression for everything else in this module) - the standard's
    own colour system doesn't need the user to separately confirm
    "yes, this actually is hostile" a second time via a different
    field once the measure type itself already says so.
  - **Infiltration Lane (140800) was skipped at first, then built** -
    re-reading its own draw rules directly (page 435) showed it's NOT the same
    kind of variable-width tapered-ribbon construction as the Axis of
    Advance family (which really does need genuine polygon-offset
    synthesis this project still doesn't build) - it's just two
    parallel lines (a fixed-width lane, approximated the same way
    Main Attack's own doubled outline is) with a plain "T" designation
    centred between them. Built for real; the small grey "S" mark
    crossing both lines in the template picture measured out as a
    flat mid-grey fill (confirmed by direct pixel sampling, not
    assumed), meaning it's explanatory/illustrative content per this
    appendix's own EXAMPLE-column convention, not drawn geometry - not
    reproduced, matching every other grey annotation already excluded
    elsewhere in this project.
  - **Point of Departure (160400) had no dedicated Points layer at
    all** - it was left inside the shared, general-purpose
    `control_measure_points.py` dropdown, the one entry this whole
    H.5.13 section still lacked its own "own layer(s)" treatment for
    (every sibling H.5.x group already got this: Table H-VI/H-IX in
    c2_measures.py/defensive_control_measures.py). Given its own
    dedicated `Offensive Control Measures (Points)` layer here,
    matching that established convention, and removed from
    control_measure_points.py's own dropdown (not left duplicated -
    same migration pattern as every earlier one). Its own unique
    designation also didn't render in the template's own position
    (immediately right of the box, vertically centred on it) -
    milsymbol.js's own position config for this SIDC (`t[160400]=E`,
    `E={additionalInformation:{...x:100,y:-70...}}`) only defines a
    slot ABOVE the box, and passing text through the WRONG default
    slot ("uniqueDesignation", which this icon has no config for at
    all) fell back to some other icon's leftover position instead
    (rendering top-right of the box, confirmed directly by rendering
    real SVG output for both slot names before choosing a fix) -
    neither matched the template, so this uses the same real-QGIS-
    label workaround Table H-IX's own Observation Post family already
    established, positioned with an explicit (x, y) mm offset computed
    from the icon's own real local SVG coordinates (measured
    empirically, same render-and-measure discipline as every other
    icon-geometry question this project has settled so far) rather
    than either of milsymbol's own mismatched slots.

Military Cartography Tools
"""

import base64

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFontMarkerSymbolLayer,
    QgsGeometryGeneratorSymbolLayer,
    QgsLabelLineSettings,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF, Qt
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    stabilised_point_size_expression,
    AFFILIATION_LABELS,
    POINT_AFFILIATION_LABELS,
    STATUS_LABELS,
    _AFFILIATION_COLOR_EXPRESSION,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _end_label_layer,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Offensive Control Measures (Lines)"
AREAS_LAYER_NAME = "Offensive Control Measures (Areas)"
POINTS_LAYER_NAME = "Offensive Control Measures (Points)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "POINTS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "POINT_ENTITY_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_offensive_control_measures_lines_layer",
    "create_offensive_control_measures_areas_layer",
    "create_offensive_control_measures_points_layer",
    "add_offensive_control_measures_lines_layer",
    "add_offensive_control_measures_areas_layer",
    "add_offensive_control_measures_points_layer",
]

# Table H-X, H.5.13.1 - approximated (see module docstring). Axis of
# Advance for a Feint/Enemy Confirmed/Enemy Templated fold their own
# status pairs (140605 has none shown, 140407/408 do) the same way
# Supporting Attack's own Present/Planned pair (151404/151405) does -
# via the shared status field, not a separate measure_type.
_AXIS_OF_ADVANCE_LABELS = {
    "axis_of_advance_airborne": "Axis of Advance - Friendly Airborne",
    "axis_of_advance_aviation": "Axis of Advance - Friendly Aviation",
    "axis_of_advance_attack_helicopter": "Axis of Advance - Attack Helicopter",
    "axis_of_advance_main_attack": "Axis of Advance - Main Attack",
    "axis_of_advance_supporting_attack": "Axis of Advance - Supporting Attack",
    "axis_of_advance_feint": "Axis of Advance for a Feint",
    "axis_of_advance_enemy": "Axis of Advance - Enemy",
}

# "Airborne" and "Aviation" share one SIDC code in the standard (151401,
# Table H-X page 428 - its own EXAMPLE column shows two separate
# illustrations, "Airborne" and "Aviation", under that single code) -
# split into two selectable measure_type values anyway, per the project
# maintainer's own explicit request ("they are two different tasks").
# Both render identically (see _axis_of_advance_ribbon_symbol()) and
# share the same code deliberately, the same "one construction, several
# selectable meanings" pattern already used for Supporting Attack's own
# Present/Planned pair above.
# Table H-XI, H.5.13.2 - a real (not approximated) plain line + open
# chevron arrowhead construction.
_DIRECTION_OF_ATTACK_LABELS = {
    "direction_of_attack_aviation": "Direction of Attack - Friendly Aviation",
    "direction_of_attack_main": "Direction of Attack - Main Attack",
    "direction_of_attack_supporting": "Direction of Attack - Supporting Attack",
    "direction_of_attack_ground_axis": "Direction of Attack - Friendly Ground Axis",
    "direction_of_attack_feint": "Direction of Attack for a Feint",
    "direction_of_attack_enemy": "Direction of Attack - Enemy",
}

LINE_MEASURE_TYPE_LABELS = {
    **_AXIS_OF_ADVANCE_LABELS,
    **_DIRECTION_OF_ATTACK_LABELS,
    "infiltration_lane": "Infiltration Lane",
    "final_coordination_line": "Final Coordination Line (FCL)",
    "limit_of_advance": "Limit of Advance (LOA)",
    "line_of_departure": "Line of Departure (LD)",
    "line_of_departure_and_contact": "Line of Departure/Line of Contact (LD/LC)",
    "probable_line_of_deployment": "Probable Line of Deployment (PLD)",
}

# Field T/Field W-W1 - see module docstring's 2026-08-10 entry. Shared by
# both Axis of Advance and Direction of Attack; both fields are also on
# c2_measures.py's own Boundary and maneuver_control_measures.py's own
# action-area schemas as "unique_designation"/"dtg_start"/"dtg_end", the
# same field names, so this isn't a new naming scheme.
_UNIQUE_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"unique_designation\" IS NOT NULL AND \"unique_designation\" != ''"
    f" THEN {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
)

# 2026-08-12: split onto two lines, matching the standard's own EXAMPLE
# picture (page 432 - "080400ZOCT08 -" / "120300ZOCT08") and the project
# maintainer's own explicit request ("split it into two lines"). TWO
# separate expressions/marker layers, not one expression with an
# embedded "\n" - confirmed by a dedicated probe render that
# QgsFontMarkerSymbolLayer (unlike a real PAL label) has no multi-line
# text layout of its own; it silently drops embedded newlines and
# renders everything on one line regardless. Also dropped the trailing
# literal "Z" the old single-expression version appended after
# "dtg_end" - each raw DTG value already carries its own embedded
# Zulu-time designator mid-string (DDHHMMZ MON YY), confirmed against
# both the standard's own example and this project's own test fixtures
# ("120300ZOCT08"), so that trailing "Z" was a redundant double-Z, not
# something the maintainer asked to keep.
_DTG_START_LINE_EXPRESSION = (
    "CASE WHEN \"dtg_start\" IS NOT NULL AND \"dtg_start\" != ''"
    " AND \"dtg_end\" IS NOT NULL AND \"dtg_end\" != ''"
    " THEN \"dtg_start\" || ' -' ELSE '' END"
)

_DTG_END_LINE_EXPRESSION = (
    "CASE WHEN \"dtg_start\" IS NOT NULL AND \"dtg_start\" != ''"
    " AND \"dtg_end\" IS NOT NULL AND \"dtg_end\" != ''"
    " THEN \"dtg_end\" ELSE '' END"
)

# Direction of Attack - Friendly Aviation's own Field T (2026-08-11):
# "the unique designation should be just behind the arrow head with
# suitable masking, in line with the arrow shaft" - the maintainer's own
# words, moving Field T off the _designation_end_marker_layer() font-
# marker technique every other Direction of Attack/Axis of Advance
# variant still uses (see that function's own docstring) and onto a
# genuine PAL label instead, the ONLY way to get real masking (a font
# marker glyph has no QgsTextMaskSettings of its own - see c2_measures.
# py's own _boundary_symbol() docstring for the three-attempts history
# that already ruled out every non-PAL alternative). Scoped to this ONE
# measure type via the CASE's own guard - every other Direction of
# Attack/Axis of Advance measure type still renders '' from this label
# and keeps its own existing font-marker Field T untouched.
_DIRECTION_OF_ATTACK_AVIATION_LINE_SYMBOL_LAYER_ID = (
    "direction_of_attack_aviation_line"
)

_DIRECTION_OF_ATTACK_AVIATION_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'direction_of_attack_aviation' THEN ("
    + _UNIQUE_DESIGNATION_LABEL_EXPRESSION + ") ELSE '' END"
)

# 2026-08-12, cross-checked against the standard's own Table H-XI
# (pages 432-433) at the maintainer's own explicit request ("that
# clears all chapter X/XI - cross check please"): every real template/
# example there clusters Field T (and Field W-W1 below it) right past
# PT2 - the line's own START - not near the tip the way this constant
# originally placed it (0.9, "just behind the arrow head" - built
# without ever checking the standard, per that same day's earlier
# "don't refer the manual for now" instruction). The maintainer's own
# words once shown the discrepancy: "it's ok, from a cartography point
# of view, it is not an issue. but you can go ahead and fix the DTG and
# Field T" - confirmed to apply to every variant, including Main Attack
# (which had its own separate CENTRE-of-shaft constant, _DIRECTION_OF_
# ATTACK_MAIN_LABEL_ANCHOR_PERCENT, retired the same day and folded
# into this one shared value) and Enemy ("you can fix Field T along
# with others" - content/DTG-presence stay exactly as before per that
# same round's own separate ruling, only the POSITION moves).
# 0.12 - close enough to the line's own start (0.0) to read as "just
# past PT2", tuned by render-and-compare the same way 0.9 originally
# was. AnchorTextPoint.StartOfText (not EndOfText any more) pins the
# text's own LEADING edge to that point, so the label now extends
# FORWARD from there along the shaft towards the tip, matching the
# standard's own left-to-right reading direction.
_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT = 0.12

# Direction of Attack - Main Attack's own Field T (2026-08-12): "Field T
# - unique designator should have a mask so that line is not seen below
# it" - the maintainer's own words, once Field T moved to the centre of
# the shaft (see _direction_of_attack_symbol()'s own "moving on to Main
# Attack" comment) where the shaft's own drawn line runs directly
# beneath it. The exact same real-masking technique Friendly Aviation's
# own Field T already uses above, masking THIS variant's own line id
# instead of aviation's - a different id for a different feature, not
# the "two rules masking the SAME feature's own line" case that failed
# for the bowtie (see that own dead-end's comment on _direction_of_
# attack_bowtie_layer()) - each rule below only ever matches its own
# single measure type, so there is exactly one masked label per
# feature, never two competing for the same mask. Main Attack's own
# CENTRE-of-shaft anchor (0.5) was retired the same day as every other
# variant's own near-tip anchor - see _DIRECTION_OF_ATTACK_LABEL_
# ANCHOR_PERCENT's own comment for the cross-check that replaced both
# with one shared near-start value.
_DIRECTION_OF_ATTACK_MAIN_LINE_SYMBOL_LAYER_ID = (
    "direction_of_attack_main_line"
)

_DIRECTION_OF_ATTACK_MAIN_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'direction_of_attack_main' THEN ("
    + _UNIQUE_DESIGNATION_LABEL_EXPRESSION + ") ELSE '' END"
)

# Direction of Attack - Supporting Attack (2026-08-12): "start with the
# friendly aviation symbol, drop the milsymbol, horizontal stub and bow
# tie" - the maintainer's own words. Everything else Friendly Aviation
# has stays, including its own masked-PAL Field T (same anchor percent,
# same position near the arrowhead, same affiliation colouring) - just
# without the unit icon/bowtie/stub, and without Field T's font-marker
# fallback (no `else` branch appends one for this variant either).
_DIRECTION_OF_ATTACK_SUPPORTING_LINE_SYMBOL_LAYER_ID = (
    "direction_of_attack_supporting_line"
)

_DIRECTION_OF_ATTACK_SUPPORTING_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'direction_of_attack_supporting' THEN ("
    + _UNIQUE_DESIGNATION_LABEL_EXPRESSION + ") ELSE '' END"
)

# Direction of Attack - Enemy (2026-08-12): "start with the supporting
# attack, default the colour to red, that's all" - the maintainer's own
# words. Same construction as Supporting Attack (plain shaft, single
# chevron, masked-PAL Field T at the same anchor percent near the
# arrowhead, no unit icon/bowtie/stub) - just its own line-symbol-layer
# id/label-filter pair, since a masked PAL label rule needs to match
# only its own measure type. The colour itself needs no new code at
# all: "direction_of_attack_enemy" is already in _ENEMY_MEASURE_TYPES
# below, so every _apply_offensive_line_color()/_OFFENSIVE_LINE_COLOR_
# EXPRESSION call this variant's own construction already goes through
# (line, chevron, PAL label colour) renders red automatically.
_DIRECTION_OF_ATTACK_ENEMY_LINE_SYMBOL_LAYER_ID = (
    "direction_of_attack_enemy_line"
)

_DIRECTION_OF_ATTACK_ENEMY_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'direction_of_attack_enemy' THEN ("
    + _UNIQUE_DESIGNATION_LABEL_EXPRESSION + ") ELSE '' END"
)

# Direction of Attack - Friendly Ground Axis (2026-08-12): "replicate
# the supporting attack symbol for friendly ground axis, that's all, no
# change to the symbol required" - the maintainer's own words. Same
# construction as Supporting Attack/Enemy (plain shaft, single chevron,
# masked-PAL Field T at the same anchor percent near the arrowhead, no
# unit icon/bowtie/stub), own line-symbol-layer id/label-filter pair
# only. Ordinary affiliation colouring, no override needed (unlike
# Enemy) - _OFFENSIVE_LINE_COLOR_EXPRESSION already falls through to
# _AFFILIATION_COLOR_EXPRESSION for any measure type not in
# _ENEMY_MEASURE_TYPES.
_DIRECTION_OF_ATTACK_GROUND_AXIS_LINE_SYMBOL_LAYER_ID = (
    "direction_of_attack_ground_axis_line"
)

_DIRECTION_OF_ATTACK_GROUND_AXIS_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'direction_of_attack_ground_axis' THEN ("
    + _UNIQUE_DESIGNATION_LABEL_EXPRESSION + ") ELSE '' END"
)

# Direction of Attack for a Feint (2026-08-12): "start with the
# supporting attack symbol, add a dashed chevron outside the main
# arrowhead..." - the maintainer's own words. Same base construction/
# own line-symbol-layer id/label-filter pair as the other "start with
# the supporting attack" variants above - see _direction_of_attack_
# feint_outer_chevron_layer()'s own comment for the added chevron
# itself.
_DIRECTION_OF_ATTACK_FEINT_LINE_SYMBOL_LAYER_ID = (
    "direction_of_attack_feint_line"
)

_DIRECTION_OF_ATTACK_FEINT_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'direction_of_attack_feint' THEN ("
    + _UNIQUE_DESIGNATION_LABEL_EXPRESSION + ") ELSE '' END"
)

# Enemy-flagged Axis of Advance/Direction of Attack variants render red
# regardless of the ordinary "affiliation" field - see module docstring's
# 2026-08-10 entry. A local override, not a change to the shared
# _AFFILIATION_COLOR_EXPRESSION itself (every other measure type in this
# module, and every other H group's own module, still needs the ordinary
# friend/hostile/neutral/unknown behaviour unchanged).
_ENEMY_MEASURE_TYPES = ("axis_of_advance_enemy", "direction_of_attack_enemy")

# **2026-08-12**: "all friendly symbols must be blue and all enemy red,
# rest should depend on affiliation selection" - the maintainer's own
# words, extending the enemy-red rule above to its mirror image. These
# are exactly the measure types whose own NAME already commits them to
# a side ("... - Friendly Airborne/Aviation/Ground Axis"), so leaving
# their colour on a dropdown the user could set to "hostile" would let
# the two contradict each other.
#
# Deliberately NOT swept in, per the maintainer's own explicit scoping
# decision when asked:
#   - Encirclement (maneuver_control_measures_2.py) and Area
#     (maneuver_control_measures.py) each FOLD the standard's own
#     separate Friendly/Enemy codes into ONE measure type and use the
#     affiliation field itself as the friendly/enemy discriminator -
#     forcing either colour would break that fold outright.
#   - Critical Friendly Zone, Enemy Prisoner of War Collection Point and
#     Suppression of Enemy Air Defence merely CONTAIN the words: a CFZ
#     is a zone to protect, an EPW collection point is a friendly-run
#     facility, and SEAD is a friendly mission against enemy air
#     defence. None is an enemy symbol; all keep the dropdown.
_FRIENDLY_MEASURE_TYPES = (
    "axis_of_advance_airborne",
    "axis_of_advance_aviation",
    "direction_of_attack_aviation",
    "direction_of_attack_ground_axis",
)

# The "master arrow" (the project maintainer's own naming, 2026-08-10/
# 2026-08-11) - the finalised, non-crossed ribbon construction built
# and iterated for Main Attack (see _axis_of_advance_ribbon_symbol()'s
# own `variant` docstring and mct_axis_of_advance_ribbon()'s own
# `crossed`/`arrow_width_ratio` docstrings for the full construction),
# then replicated for Supporting Attack 2026-08-11 ("just replicate
# the master arrow for the supporting attack, no other changes to it"
# - the maintainer's own words), as its own base for Axis of Advance
# for a Feint the same day ("use the arrow and unique identification
# of supporting attack as the base"), and again verbatim for Axis of
# Advance - Enemy Confirmed/Templated ("just use the master arrow and
# default colour to red" - already true by construction, see
# _ENEMY_MEASURE_TYPES's own comment, not a new colour rule). Every
# variant listed here shares the SAME shaft/arrowhead/Field-T/no-DTG/
# no-icon treatment in _axis_of_advance_ribbon_symbol()'s own master-
# arrow branch - add a measure type here, not a new branch, when a
# future variant turns out to be "just the master arrow" too.
_MASTER_ARROW_VARIANTS = ("main_attack", "supporting_attack", "feint", "enemy")

# The one part of the master arrow that is NOT shared: the double-
# lined (inset chevron) arrowhead is Main Attack's own only, frozen
# once confirmed - Supporting Attack and Feint both replicate
# everything else but explicitly not this ("main attack requires the
# inner chevron, supporting attack does not require it" - the
# maintainer's own words, 2026-08-11, after an earlier over-broad edit
# removed it from BOTH). Once a measure type's own construction is
# confirmed, don't touch it again for an unrelated variant's own
# request - see this project's own standing "scope fixes to one
# symbol" convention.
_DOUBLE_LINED_ARROWHEAD_VARIANTS = ("main_attack",)

# Axis of Advance for a Feint's own distinguishing mark, on top of the
# master arrow's own base (Supporting Attack's own shape, minus the
# inner chevron) - a second, DASHED chevron OUTSIDE the real arrowhead,
# a fixed gap out from it, per the maintainer's own explicit 2026-08-11
# instruction. See _axis_of_advance_outer_chevron_layer()'s own
# docstring and mct_axis_of_advance_outer_chevron()'s own docstring for
# the full construction.
_OUTER_CHEVRON_VARIANTS = ("feint",)


def _axis_of_advance_master_arrow_expression(variant):

    """
    The master arrow's own mct_axis_of_advance_ribbon() call, per
    `variant` - identical for every _MASTER_ARROW_VARIANTS member
    except the trailing `double_lined_arrowhead` argument, which only
    Main Attack gets (see _DOUBLE_LINED_ARROWHEAD_VARIANTS's own
    comment for why this is the one part of "the master arrow" that
    isn't actually shared).
    """

    if variant in _DOUBLE_LINED_ARROWHEAD_VARIANTS:

        return "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2, true)"

    return "mct_axis_of_advance_ribbon($geometry, 0.08, false, 1.2)"


def _axis_of_advance_outer_chevron_layer():

    """
    Axis of Advance for a Feint's own distinguishing mark - a second,
    DASHED chevron OUTSIDE the real arrowhead, a fixed gap out from it
    (see mct_axis_of_advance_outer_chevron()'s own docstring for the
    full construction). A SEPARATE QgsGeometryGeneratorSymbolLayer from
    the main ribbon's own (not an extra piece inside
    mct_axis_of_advance_ribbon()'s own MultiLineString the way Main
    Attack's inner chevron is) - this one is fixed dashed regardless of
    the feature's own "status", not status-driven like the shaft/
    arrowhead's shared stroke style, so it needs its own independent
    pen.
    """

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setGeometryExpression(
        # gap_ratio tuned across three rounds of direct maintainer
        # feedback: 1.0 (first render) -> 0.8 ("reduce it by 1/5th") ->
        # 0.2 ("still too high, reduce the gap by 75%") -> 0.32
        # ("increase gap by 60%", i.e. 0.2 * 1.6). No separate "size"
        # parameter is needed - the chevron's own shape is a pure
        # function of `gap`, so it stays proportionate at any value.
        "mct_axis_of_advance_outer_chevron($geometry, 0.08, 1.2, 0.32)"
    )

    generator_layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    outer_chevron_symbol = QgsLineSymbol()

    outline_layer = outer_chevron_symbol.symbolLayer(0)

    outline_layer.setWidth(
        0.5
    )

    outline_layer.setPenStyle(
        Qt.PenStyle.DashLine
    )

    _apply_offensive_line_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    generator_layer.setSubSymbol(
        outer_chevron_symbol
    )

    return generator_layer


# Enemy tested before friendly purely for readability - the two tuples
# are disjoint by construction, so the order can't actually matter.
# Anything in neither falls through to the ordinary affiliation hue.
_OFFENSIVE_LINE_COLOR_EXPRESSION = (
    "CASE WHEN \"measure_type\" IN ("
    + ", ".join(f"'{measure_type}'" for measure_type in _ENEMY_MEASURE_TYPES)
    + ") THEN color_rgb(255, 0, 0)"
    " WHEN \"measure_type\" IN ("
    + ", ".join(f"'{measure_type}'" for measure_type in _FRIENDLY_MEASURE_TYPES)
    + ") THEN color_rgb(0, 0, 255) ELSE " + _AFFILIATION_COLOR_EXPRESSION + " END"
)


def _apply_offensive_line_color(symbol_layer, properties):

    color_property = QgsProperty.fromExpression(_OFFENSIVE_LINE_COLOR_EXPRESSION)

    for property_key in properties:

        symbol_layer.setDataDefinedProperty(
            property_key,
            color_property
        )


def _designation_font_marker(expression, size, offset=None):

    """
    The shared QgsMarkerSymbol (a single QgsFontMarkerSymbolLayer with
    a DATA-DEFINED Character) behind both _designation_end_marker_
    layer() (a rotate-with-line QgsMarkerLineSymbolLayer, text follows
    the line's own direction) and _shaft_fraction_label_layer() (a
    QgsGeometryGeneratorSymbolLayer at a computed fractional-distance
    point, text stays horizontal) - factored out since both need the
    identical font/colour/Character setup, only the wrapping symbol
    layer (and whether it rotates) differs.
    """

    font_layer = QgsFontMarkerSymbolLayer()

    font_layer.setFontFamily(
        "Arial"
    )

    font_layer.setSize(
        size
    )

    font_layer.setColor(
        QColor(0, 0, 0)
    )

    font_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Character,
        QgsProperty.fromExpression(expression)
    )

    if offset is not None:

        font_layer.setOffset(
            offset
        )

    _apply_offensive_line_color(
        font_layer,
        [QgsSymbolLayer.Property.FillColor]
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(
        0,
        font_layer
    )

    return marker


def _designation_end_marker_layer(
    expression,
    offset,
    size=3.2,
    placement=Qgis.MarkerLinePlacement.LastVertex
):

    """
    A QgsMarkerLineSymbolLayer whose own sub-symbol is a single
    QgsFontMarkerSymbolLayer with a DATA-DEFINED Character (`expression`)
    - the same technique maneuver_control_measures.py's own Phase Line
    uses for a per-feature dynamic string via `_end_designation_label_
    layer()`, generalised here to take any expression/offset/placement
    rather than a fixed "prefix + name at each end" shape. Defaults to
    Qgis.MarkerLinePlacement.LastVertex (Axis of Advance/Direction of
    Attack both need their own T/DTG text near the arrowhead, not at
    both ends) - Infiltration Lane's own centred Field T overrides this
    to CentralPoint. Text rotates WITH the line - see _shaft_fraction_
    label_layer() for the horizontal-text alternative.
    """

    line_layer = QgsMarkerLineSymbolLayer(True)

    line_layer.setSubSymbol(
        _designation_font_marker(expression, size, offset)
    )

    line_layer.setPlacements(
        placement
    )

    return line_layer


def _shaft_fraction_label_layer(expression, fraction, size=3.2):

    """
    Field T at a FRACTIONAL distance along the shaft (not a named
    vertex), text kept HORIZONTAL regardless of the line's own
    direction - Main Attack's own layout, 2026-08-10 ("move the unique
    designation to the shaft, about 1/3 distance from the edge, text
    orientation should be horizontal", the project maintainer's own
    words - "the edge" read as Point 1, the shaft's own start).
    QGIS's own `line_interpolate_point()` gives the fractional point
    directly (no need for a custom Python function, unlike the ribbon's
    own construction - this is a single built-in expression). Wrapped
    in a QgsGeometryGeneratorSymbolLayer producing a Marker (not a
    QgsMarkerLineSymbolLayer placement) for the same reason Attack
    Helicopter's own crossing glyph is - a geometry-generator marker has
    no placement-driven rotation to begin with, which is exactly what
    "horizontal regardless of direction" needs, confirmed by the same
    technique already working for that glyph.
    """

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setGeometryExpression(
        f"line_interpolate_point($geometry, length($geometry) * {fraction})"
    )

    generator_layer.setSymbolType(
        Qgis.SymbolType.Marker
    )

    generator_layer.setSubSymbol(
        _designation_font_marker(expression, size)
    )

    return generator_layer


# Table H-XI's own three areas (H.5.13.2's own "Areas" sub-section) -
# same "prefix + optional name" pattern as every other simple area in
# this appendix (c2_measures.py's own AO/NAI/TAI, maneuver_control_
# measures.py's own DZ/EZ/LZ/PZ, ...).
_AREA_LABEL_PREFIXES = {
    "assault_position": "ASLT",
    "attack_position": "ATK",
    "objective_area": "OBJ",
}

AREA_MEASURE_TYPE_LABELS = {
    "assault_position": "Assault Position (ASLT)",
    "attack_position": "Attack Position (ATK)",
    "objective_area": "Objective Area (OBJ)",
}


def _axis_of_advance_shaft_layer(offset_mm=0.0):

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        1.2
    )

    if offset_mm:

        line_layer.setOffset(
            offset_mm
        )

    _apply_offensive_line_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    return line_layer


def _unit_context_icon_layer(entity, airborne_modifier=False, offset=None, rotate=True):

    """
    The small "what kind of unit" context icon the project maintainer
    asked to have drawn at the shaft's own start (Point 1) - the REAL
    land-unit icon already in this project's own vocabulary
    (`sidc.py`'s own ENTITIES["ground_unit"][entity]), rendered through
    the same milsymbol.js pipeline every other real symbol in this
    project uses (mct_build_sidc()/mct_sidc_svg()), per the maintainer's
    own explicit correction on the first (Friendly Airborne) round of
    this - an earlier version hand-built an approximate rectangle+cross
    instead of using the real, already-catalogued Infantry entity.
    `entity` - e.g. "infantry" (Friendly Airborne), "aviation_rotary_
    wing" (Friendly Aviation, 2026-08-10), "aviation_fixed_wing"
    (Direction of Attack - Friendly Aviation's own unit icon, 2026-08-11
    - see _direction_of_attack_symbol()'s own comment) - all share the
    SAME generic Ground Unit rectangle frame (confirmed directly by
    rendering multiple of these SIDCs and comparing their own SVG
    `viewBox`: identical "21 46 158 108", 158 wide by 108 tall, before
    this was assumed to carry over from Infantry to Aviation Rotary
    Wing), only the icon glyph inside the frame differs - which is also
    why this same real icon already comes "bounded in a rectangle" with
    no extra frame of this project's own construction needed.

    `offset` (None by default - every existing caller's own at-the-
    anchor-point placement is unchanged) shifts the icon along the
    line's own local X axis, the same rotate-with-line convention
    _direction_of_attack_bowtie_layer()'s own docstring establishes -
    Direction of Attack - Friendly Aviation's own call is the first user
    of this, placing its unit icon BEFORE the line's own origin rather
    than on top of it.

    `rotate` (True by default, matching every caller's own behaviour
    before 2026-08-12) controls whether the icon turns to match the
    line's own direction (QgsMarkerLineSymbolLayer's own rotateSymbols
    flag) or always renders upright/level regardless of which way the
    arrow points. Axis of Advance - Friendly Airborne/Aviation/Attack
    Helicopter all pass `rotate=False` ("the symbol at the base of the
    shaft... should not be rotated but be straight" - the project
    maintainer's own words, 2026-08-12, extended to Attack Helicopter's
    own base icon in the same round: "same is the case for... attack
    helicopter") - this is the shaft's own base UNIT icon specifically,
    not Attack Helicopter's own separate crossing-point glyph (already
    fixed-orientation by construction, see _attack_helicopter_
    direction_glyph_layer()'s own docstring) and not Direction of
    Attack - Friendly Aviation's own icon (still rotates - not part of
    this correction, a different call site, different placement logic).

    `airborne_modifier` - MIL-STD-2525D's own Airborne modifier glyph,
    overlaid in the icon's own bottom half, Friendly Airborne only -
    confirmed directly against milsymbol.js's own vendored source
    (`icn["GR.M2.AIRBORNE"]` in milsymbol-3.0.4's own src/iconparts/
    ground.js): `"M75,140 C75,125 100,125 100,140 C100,125 125,125
    125,140"`, two side-by-side semicircular humps - exactly the shape
    this project's own `Shape.HalfArc` marker already draws (already
    used for FLOT/Line of Contact's own arc chains in maneuver_control_
    measures.py), so it's built the same way here rather than hand-
    authoring separate bezier path data. Not routed through
    milsymbol.js itself as a real sector-2 modifier - MODIFIERS in
    sidc.py has no "ground_unit" entry at all yet (sector 1/2 modifier
    support was only ever built for the point-symbol appendices, a
    known gap - see the project's own roadmap), so this one glyph is
    still hand-built and layered on top of the otherwise-real Infantry
    render, the same "hand-build the one glyph actually needed" choice
    Direction of Attack's own bowtie already made. **Friendly Aviation
    does NOT get this modifier** - the Aviation Rotary Wing entity's own
    icon (a rotor-blade glyph) already identifies the unit type on its
    own, per the project maintainer's own explicit instruction ("remove
    the infantry symbol and the 'm'... replace with the aviation
    symbol... rest remains same").

    Tuned in an isolated standalone render (not the full arrow symbol)
    at the project maintainer's own request, so the plugin code only
    ever received the finalised version rather than several rounds of
    in-place edits: the SVG's own default orientation put the frame
    rectangle's own narrow dimension along the shaft, not its broad
    one, so `svg_angle=90` on the SVG layer corrects that (confirmed by
    render, the maintainer's own instruction was "rotate the entire
    icon 90 deg, so that the breadth of the rectangle is aligned with
    the shaft"); the same 90-degree angle is applied to the airborne
    modifier's own hump layers too, so they stay aligned with the (now
    rotated) rectangle. The humps are fixed BLACK (not affiliation-
    coloured) - a modifier glyph, like Field N elsewhere in this
    appendix, is a structural indicator, not something that should
    change colour with the feature's own affiliation. Their own size
    and Y offset were tuned down/further from centre in two more rounds
    after the maintainer's own direct feedback on each render ("reduce
    the size... by 50%", then "move the m slightly lower", then "shift
    the m slightly downwards, it should not touch the diagonals").
    """

    icon = QgsMarkerSymbol()

    frame_layer = QgsSvgMarkerSymbolLayer("")

    frame_layer.setSize(
        6.0
    )

    # The 90-degree correction was tuned for the rotate-with-line case
    # (rotate=True): the SVG's own native orientation puts its broad
    # dimension along local Y, not local X, and the outer line-rotation
    # treats local X (angle=0) as "along the line" - see this function's
    # own docstring. With rotate=False that outer reference no longer
    # applies, and the same fixed 90-degree value renders the frame 90
    # degrees off ("all three icons are 90 deg off, rotate them counter
    # clockwise by 90 deg" - the project maintainer's own words,
    # 2026-08-12, confirmed by render). QGIS's own angle increases
    # clockwise (see _direction_of_attack_bowtie_layer()'s own "angle=0
    # points up, 90 right..." comment) - rotating counter-clockwise by
    # 90 degrees from the rotate=True value is angle=0.
    frame_layer.setAngle(
        90 if rotate else 0
    )

    if offset is not None:

        frame_layer.setOffset(
            offset
        )

    # 2026-08-10 fix, found by the project maintainer's own live smoke
    # test: a freshly-digitized feature's own "affiliation" field
    # defaults to DEFAULT_AFFILIATION ("unspecified", this layer's own
    # genuine 5th value for the standard's own "black, no standard
    # identity asserted" colour - see _control_measure_shared.py's own
    # comment) - a value sidc.py's own AFFILIATIONS dict has no entry
    # for (point symbols only have friend/hostile/neutral/unknown, per
    # that same comment). Passed straight through, mct_build_sidc()
    # raises KeyError, returns an error string instead of a real SIDC,
    # and mct_sidc_svg() can't render that - QGIS then shows its own
    # generic broken/placeholder SVG glyph for the icon specifically
    # (the arrow's own line colour and Field T's own text both still
    # rendered fine, since their own CASE expressions already have a
    # safe ELSE fallback - only this icon's SIDC-building call didn't).
    # Mapped to 'unknown' here, for the icon's own affiliation argument
    # only - the field itself still needs its real 5-value range for
    # the line's own colour.
    frame_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_sidc_svg(mct_build_sidc("
            "CASE WHEN \"affiliation\" IN ('friend', 'hostile', 'neutral', 'unknown')"
            " THEN \"affiliation\" ELSE 'unknown' END,"
            f"'{entity}','ground_unit','unspecified',"
            "\"status\",false"
            "))"
        )
    )

    icon.changeSymbolLayer(
        0,
        frame_layer
    )

    if airborne_modifier:

        # Offsets are in this marker's own rotate-with-line local frame
        # (X along the line's own direction, Y perpendicular - the same
        # convention _direction_of_attack_bowtie_layer()'s own comment
        # establishes). The two humps sit side by side across X,
        # shifted down along Y into the (now correctly rotated)
        # rectangle's own lower half, clear of the diagonal cross.
        for hump_offset_x in (-0.35, 0.35):

            hump_layer = QgsSimpleMarkerSymbolLayer(
                QgsSimpleMarkerSymbolLayerBase.Shape.HalfArc,
                0.7
            )

            hump_layer.setColor(
                QColor(0, 0, 0, 0)
            )

            hump_layer.setStrokeColor(
                QColor(0, 0, 0)
            )

            hump_layer.setStrokeWidth(
                0.25
            )

            hump_layer.setAngle(
                90 if rotate else 0
            )

            hump_layer.setOffset(
                QPointF(hump_offset_x, 1.45)
            )

            icon.appendSymbolLayer(
                hump_layer
            )

    icon_line_layer = QgsMarkerLineSymbolLayer(rotate)

    icon_line_layer.setSubSymbol(
        icon
    )

    icon_line_layer.setPlacements(
        Qgis.MarkerLinePlacement.FirstVertex
    )

    return icon_line_layer


# Attack Helicopter's own crossing-point glyph (151402) - a fixed-
# orientation vertical arrow crossed by an unfilled bowtie/hourglass
# outline, plus a short tail and horizontal foot below the bowtie.
# milsymbol.js has no vendored equivalent (confirmed by direct source
# search - its own "ROTARY WING" sector modifiers, COM.M1/M2.ROTARY
# WING, are a plain filled bowtie parallelogram-pair, not this arrow-
# through-bowtie combination), so this is a genuinely custom glyph,
# supplied by the project maintainer as exact SVG path/polygon data
# (not derived or approximated by this project) and rendered verbatim
# via a QgsSvgMarkerSymbolLayer - the same "base64:" inline-SVG
# technique this project already uses for real milsymbol.js renders.
# fill/stroke use QGIS's own "param(fill)"/"param(outline)" placeholder
# syntax (confirmed live that QgsSvgMarkerSymbolLayer.setColor()/
# setStrokeColor() - and their own data-defined equivalents - recolour
# an inline base64 SVG through these placeholders exactly like QGIS's
# own bundled parametrised SVG library) - per the project maintainer's
# own explicit request to standardise this glyph's colour with the
# rest of the affiliation system (friend/hostile/neutral/unknown/
# unspecified) rather than leaving it fixed black like Field N/the
# Airborne modifier's own humps/the Direction of Attack bowtie.
_ATTACK_HELICOPTER_GLYPH_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400" width="400" height="400">
  <g transform="translate(0, 5)">
    <path d="M 60,130 L 200,200 L 60,270 Z
             M 340,130 L 200,200 L 340,270 Z
             M 60,130 L 60,270
             M 340,130 L 340,270"
          fill="none" stroke="param(outline)" stroke-width="16" stroke-linecap="round" stroke-linejoin="miter" stroke-miterlimit="4" />
    <path d="M 200,315 L 200,105
             M 150,315 L 250,315"
          fill="none" stroke="param(outline)" stroke-width="16" stroke-linecap="round" stroke-linejoin="miter" stroke-miterlimit="4" />
    <polygon points="200,65 172,112 228,112" fill="param(fill)" stroke="param(outline)" stroke-width="4" stroke-linejoin="miter" />
  </g>
</svg>"""


def _attack_helicopter_direction_glyph_layer():

    """
    Placed at "the point of intersection" - the ribbon's own ACTUAL
    crossing point, via expressions/military_symbology_functions.py's
    own mct_axis_of_advance_crossing_point() (a real line-line
    intersection of the ribbon's own two edges, not merely the
    arithmetic midpoint of Point 2 and Point 3 - see that function's
    own docstring for why an earlier midpoint-based version placed the
    glyph consistently off-centre, confirmed by the project maintainer
    across several different arrow geometries, not a one-off). A
    QgsGeometryGeneratorSymbolLayer producing a Marker (not Line) from
    that computed POINT - deliberately NOT a QgsMarkerLineSymbolLayer
    placement, since a geometry-generator marker has no placement-
    driven rotation to begin with, which is exactly what "the
    orientation of the symbol will remain vertical irrespective of the
    direction of arrow" (the maintainer's own explicit requirement)
    needs - confirmed by render, not assumed.
    """

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setGeometryExpression(
        "mct_axis_of_advance_crossing_point($geometry)"
    )

    generator_layer.setSymbolType(
        Qgis.SymbolType.Marker
    )

    glyph_symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer(
        "base64:" + base64.b64encode(
            _ATTACK_HELICOPTER_GLYPH_SVG.encode("utf-8")
        ).decode("ascii")
    )

    # 12.0mm - 50% larger than the glyph's own first-cut size, tuned by
    # the project maintainer's own direct comparison against the
    # ribbon's own arrowhead triangle in a live render ("increase the
    # size of the glyph by 50% - matching 75% of triangle's
    # dimensions").
    svg_layer.setSize(
        12.0
    )

    _apply_offensive_line_color(
        svg_layer,
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    glyph_symbol.changeSymbolLayer(
        0,
        svg_layer
    )

    generator_layer.setSubSymbol(
        glyph_symbol
    )

    return generator_layer


def _axis_of_advance_ribbon_symbol(variant="aviation"):

    """
    Table H-X, code 151401 (Friendly Airborne/Aviation) - the standard's
    own REAL construction, not the single-thick-line approximation the
    rest of this Axis of Advance family still uses (see module docstring
    for the standing "one at a time" plan to bring the others over to
    this same technique next). A genuine variable-width tapered ribbon
    computed from the feature's own 3-point line by expressions/
    military_symbology_functions.py's own mct_axis_of_advance_ribbon()
    - see that function's own docstring for the full construction and
    for why it's a plain Python function rather than a QGIS expression
    built from chained with_variable() calls (the first attempt at
    exactly that, timed and confirmed to blow up exponentially with
    chain depth on a real render, not merely slow).

    `variant` - "airborne", "aviation" (default), or "attack_helicopter".
    All three get the same unit-context icon + Field T layout at the
    shaft's own start (Point 1) - built for Friendly Airborne first
    (Infantry icon + the Airborne modifier's own humps), then brought
    over to Friendly Aviation 2026-08-10 at the project maintainer's own
    explicit request ("remove the infantry symbol and the 'm'... replace
    with the aviation symbol i.e. Land Unit - Aviation Rotary Wing
    symbol... rest remains same") - see _unit_context_icon_layer()'s own
    docstring for why the variants share one builder (identical SVG
    frame, confirmed by comparing both entities' own rendered
    `viewBox`) that only swaps the icon's own entity and whether the
    Airborne modifier is drawn on top. Attack Helicopter (151402) reuses
    the SAME Aviation Rotary Wing base icon as Friendly Aviation ("base
    of the shaft remains same - aviation rotary wing icon", the
    maintainer's own words) but adds one more layer on top: Attack
    Helicopter's own crossing-point glyph - see
    _attack_helicopter_direction_glyph_layer()'s own docstring. Field T
    reuses the same _designation_end_marker_layer() every other Axis of
    Advance variant already uses, unaffected by the ribbon's own real
    geometry since it reads the FEATURE's own (unmodified, still
    3-point) geometry directly, not the generated one.

    Field W-W1 (DTG) does NOT appear on Friendly Airborne, Friendly
    Aviation, or Attack Helicopter - tried as a two-stacked-font-marker
    construction 2026-08-10 (QgsFontMarkerSymbolLayer's own Character
    property silently drops an embedded '\\n', so a genuine two-line DTG
    needs two separate markers), but the maintainer judged the result
    not worth the added complexity for these specific measure types and
    asked for it to be dropped ("remove the dtg from this, not worth the
    effort") - explicitly scoped to that trio, not the rest of the Axis
    of Advance/Direction of Attack family. Direction of Attack's own
    Field W-W1 DID get the two-separate-markers treatment 2026-08-12 -
    see _DTG_START_LINE_EXPRESSION's own comment.

    `variant` in `_MASTER_ARROW_VARIANTS` (Main Attack 2026-08-10,
    Supporting Attack and Feint 2026-08-11) is a genuinely different
    case from "airborne"/"aviation"/"attack_helicopter", not just
    another icon swap - the "master arrow"'s own ribbon does NOT cross
    ("this arrow is similar except the lines do not crossover", the
    maintainer's own words, see mct_axis_of_advance_ribbon()'s own
    `crossed` docstring), gets no unit-context icon, and Field T moves
    onto the shaft at a fractional distance instead of the tip, with no
    Field W-W1 at all - handled as an early return below rather than
    folded into the icon-focused branches, since it shares almost
    nothing with them beyond the ribbon generator layer itself.
    Supporting Attack reuses the master arrow's own BASE verbatim
    ("just replicate the master arrow... no other changes to it"), but
    NOT Main Attack's own double-lined arrowhead (see
    _DOUBLE_LINED_ARROWHEAD_VARIANTS's own comment - that stays Main
    Attack's own distinguishing feature, frozen). Feint reuses
    Supporting Attack's own base in turn ("use the arrow and unique
    identification of supporting attack as the base") and adds its own
    distinguishing mark on top - a dashed chevron OUTSIDE the arrowhead
    - see _axis_of_advance_outer_chevron_layer()'s own docstring and
    _OUTER_CHEVRON_VARIANTS's own comment.
    """

    generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    generator_layer.setGeometryExpression(
        _axis_of_advance_master_arrow_expression(variant)
        if variant in _MASTER_ARROW_VARIANTS
        else "mct_axis_of_advance_ribbon($geometry)"
    )

    generator_layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    ribbon_outline = QgsLineSymbol()

    outline_layer = ribbon_outline.symbolLayer(0)

    outline_layer.setWidth(
        0.6
    )

    _apply_offensive_line_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    outline_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    generator_layer.setSubSymbol(
        ribbon_outline
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        generator_layer
    )

    if variant in _MASTER_ARROW_VARIANTS:

        # The "master arrow" - no unit-context icon (not an aviation-
        # specific sub-type like Airborne/Aviation/Attack Helicopter),
        # Field T on the shaft itself at a fractional distance ("about
        # 1/3 distance from the edge"), text kept horizontal rather
        # than rotating with the line - see _shaft_fraction_label_
        # layer()'s own docstring - and Field W-W1 (DTG) dropped
        # entirely, the same "not worth the effort" call already made
        # for Airborne/Aviation/Attack Helicopter, extended here at the
        # maintainer's own explicit request. See _MASTER_ARROW_VARIANTS'
        # own comment for which measure types this applies to.
        symbol.appendSymbolLayer(
            _shaft_fraction_label_layer(
                _UNIQUE_DESIGNATION_LABEL_EXPRESSION,
                1 / 3
            )
        )

        if variant in _OUTER_CHEVRON_VARIANTS:

            symbol.appendSymbolLayer(
                _axis_of_advance_outer_chevron_layer()
            )

        return symbol

    if variant == "airborne":

        icon_entity = "infantry"
        airborne_modifier = True

    else:

        # "aviation" and "attack_helicopter" both use the Aviation
        # Rotary Wing base icon - the maintainer's own explicit
        # instruction for Attack Helicopter ("base of the shaft remains
        # same - aviation rotary wing icon").
        icon_entity = "aviation_rotary_wing"
        airborne_modifier = False

    symbol.appendSymbolLayer(
        _unit_context_icon_layer(
            icon_entity,
            airborne_modifier=airborne_modifier,
            rotate=False
        )
    )

    if variant == "attack_helicopter":

        symbol.appendSymbolLayer(
            _attack_helicopter_direction_glyph_layer()
        )

    # Field T sits just above the context icon, still within the shaft,
    # near Point 1 - the maintainer's own explicit layout instruction.
    # FirstVertex + a positive X offset (the "along the line, in its
    # own direction of travel" axis for a rotate-with-line marker - see
    # _direction_of_attack_bowtie_layer()'s own comment for this
    # established convention) moves it forward from the very start
    # point, clear of the icon. Field W-W1 (DTG) was dropped from this
    # construction (and every other Axis of Advance/Direction of Attack
    # variant) - see module docstring's 2026-08-10 entry: the standard's
    # own two-stacked-line layout wasn't judged worth the added display
    # complexity for a font marker.
    symbol.appendSymbolLayer(
        _designation_end_marker_layer(
            _UNIQUE_DESIGNATION_LABEL_EXPRESSION,
            QPointF(9.0, 0),
            placement=Qgis.MarkerLinePlacement.FirstVertex
        )
    )

    return symbol


# The bowtie's own two triangles' shared "size" parameter - pulled out
# to its own module constant (was a local variable inside
# _direction_of_attack_bowtie_layer() only) so its own footprint can be
# computed from the SAME number elsewhere, not a second, independently-
# guessed one.
_DIRECTION_OF_ATTACK_BOWTIE_TRIANGLE_SIZE_MM = 3.2

# **2026-08-12, second same-day follow-up**: "the line should not be
# visible below the bowtie" turned into a real rabbit hole - a second
# masked PAL label didn't compose with the first (see this project's
# own git history/roadmap for that dead end), and the follow-up
# `line_substring()`-based trim that replaced it turned out to depend
# on `@map_scale` behaving inside a geometry-generator expression the
# same way `QgsMapSettings.scale()` reports it beforehand - confirmed
# by render that it DIDN'T (the trimmed-away region came out far larger
# than intended at actual render time, eating the shaft on both sides
# of the bowtie instead of just the bowtie's own footprint).
#
# **What that actually was, established 2026-08-15**: not `@map_scale`
# failing to resolve - it does resolve inside a geometry generator -
# but a map-unit conversion. A scale relates ground metres to page
# millimetres, and on a layer in a geographic CRS the geometry is in
# DEGREES; treating the one as the other is exactly the kind of error
# that overshoots by orders of magnitude. See the roadmap's own
# 2026-08-15 entry and mct_safe_distance_ring(), which does the
# conversion properly. The construction below is left as it is - it
# works, it is signed off, and the alternative was never better.
#
# The maintainer's own simpler alternative, adopted instead: don't
# trim or mask the real line at ALL. Move the bowtie so it sits
# ENTIRELY BEFORE the line's own start (Point 2) - its own RIGHT edge
# touching the origin exactly, not overlapping the drawn line at any
# point - so there is nothing to hide under it in the first place. The
# real shaft then draws normally, untouched, for every variant
# (aviation included). "The arrow shaft should protrude slightly
# beyond the bowtie" is a second, purely decorative fixed-size stub
# (_direction_of_attack_bowtie_stub_layer()) drawn at the bowtie's own
# LEFT edge - not real line geometry, just another small mm-sized
# marker glyph positioned the same way every other fixed glyph in this
# module already is.
_DIRECTION_OF_ATTACK_BOWTIE_CENTER_OFFSET_MM = (
    -_DIRECTION_OF_ATTACK_BOWTIE_TRIANGLE_SIZE_MM
)

# The decorative stub's own length and position - a short line sitting
# just past the bowtie's own LEFT edge (centre_offset - triangle_size),
# extending further back (more negative) by its own length, so its own
# right end touches the bowtie with no gap and no overlap.
_DIRECTION_OF_ATTACK_BOWTIE_STUB_LENGTH_MM = 3.0

_DIRECTION_OF_ATTACK_BOWTIE_LEFT_EDGE_MM = (
    _DIRECTION_OF_ATTACK_BOWTIE_CENTER_OFFSET_MM
    - _DIRECTION_OF_ATTACK_BOWTIE_TRIANGLE_SIZE_MM
)

_DIRECTION_OF_ATTACK_BOWTIE_STUB_CENTER_OFFSET_MM = (
    _DIRECTION_OF_ATTACK_BOWTIE_LEFT_EDGE_MM
    - _DIRECTION_OF_ATTACK_BOWTIE_STUB_LENGTH_MM / 2
)

_DIRECTION_OF_ATTACK_BOWTIE_STUB_LEFT_EDGE_MM = (
    _DIRECTION_OF_ATTACK_BOWTIE_STUB_CENTER_OFFSET_MM
    - _DIRECTION_OF_ATTACK_BOWTIE_STUB_LENGTH_MM / 2
)

# 2026-08-12: "shift the aviation symbol left of the stub with some
# gap" - the project maintainer's own words, once the stub itself (see
# above) landed almost exactly where the unit icon already sat. A
# clear gap past the stub's own left edge, not the bowtie's, so the
# icon/stub/bowtie read as three visually distinct pieces left to
# right instead of two overlapping ones.
_DIRECTION_OF_ATTACK_AVIATION_ICON_GAP_MM = 3.0

_DIRECTION_OF_ATTACK_AVIATION_ICON_OFFSET_MM = (
    _DIRECTION_OF_ATTACK_BOWTIE_STUB_LEFT_EDGE_MM
    - _DIRECTION_OF_ATTACK_AVIATION_ICON_GAP_MM
)


def _direction_of_attack_bowtie_layer():

    """
    Friendly Aviation's own bowtie/hourglass glyph (140601, page 432),
    drawn ON the line near its own origin (Point 2) - this is the
    construction's own fixed arrow-glyph, not a unit icon (see
    _unit_context_icon_layer()'s own call in _direction_of_attack_
    symbol() for the SEPARATE, real "Aviation - Fixed Wing" unit icon
    the template picture also shows, boxed, BEFORE this same origin
    point). QGIS has no native "bowtie" marker shape, so this is two
    opposed Triangle marker layers sharing one anchor - angle=90/270
    (confirmed empirically with a standalone 4-angle test render, not
    assumed: angle=0 points up, 90 right, 180 down, 270 left) points one
    triangle's own tip right and the other's tip left.

    Each triangle's own `setOffset()` is NOT a plain final-space
    translation - QGIS applies it in the marker's own PRE-rotation local
    frame, then rotates the result by that marker's own `angle`
    (confirmed empirically with a dedicated probe script measuring
    rendered centroids at several angle/offset combinations, not
    assumed - naive "obvious" offset math looked right on paper twice
    and broke the render both times). For angle=90, local (x,y) rotates
    to final (-y,x); for angle=270, local (x,y) rotates to final (y,-x).
    Each triangle needs its own DIFFERENT local offset to land on the
    SAME shared final anchor point (that's what makes the tips meet) -
    solving both rotations for a shared final target of
    (_DIRECTION_OF_ATTACK_BOWTIE_CENTER_OFFSET_MM, 0) gives right_
    triangle local offset (0, triangle_size/2 - centre) and left_
    triangle local offset (0, triangle_size/2 + centre), used directly
    below (not the "obvious" ±triangle_size/2 baseline, which the same
    probe showed converges on its own to a shared point offset
    vertically by -triangle_size/2 from the true anchor - a small
    pre-existing bias, never previously corrected, that was very likely
    PART of what the project maintainer was seeing as "left and above
    the line").

    **2026-08-12 follow-up**, per the project maintainer's own direct
    comparison against the standard's own EXAMPLE picture (page 432):
    "it is filled instead of being an outline only and is left and
    above the line, it should be at the beginning of the shaft moved
    inward slightly". Both triangles now render UNFILLED (transparent
    fill, affiliation-coloured stroke only - the standard's own hollow
    bowtie, not a solid one).

    **Same-day second follow-up**: "only the tips should touch each
    other - shape like a bowtie, right now they are overlapping". The
    first fix above moved BOTH triangles' own reference point to the
    exact SAME shared final point (see this function's own first
    2026-08-12 comment for the rotation maths) - correct for making
    them meet, but that shared point is each triangle's own CENTRE, not
    its tip, so the two shapes ended up concentric (heavily
    overlapping) rather than tip-to-tip. Fixed by solving the same
    rotation equations for each triangle's own CENTRE landing
    `triangle_size / 2` on its own AWAY side of the shared meeting
    point instead of AT it - confirmed by a dedicated probe measuring
    the two rendered triangles' own pixel bounds directly: zero
    overlapping pixels, red's own rightmost column exactly equal to
    blue's own leftmost column.

    **Same-day third follow-up**: after a real rabbit hole trying to
    mask/trim the real shaft line where it passed under the bowtie
    (see _DIRECTION_OF_ATTACK_BOWTIE_CENTER_OFFSET_MM's own comment for
    the full, unsuccessful history), the maintainer's own simpler
    alternative: don't overlap the line with the bowtie AT ALL. The
    glyph's own shared centre moved from a small POSITIVE offset (on
    top of the drawn line) to `-triangle_size` (fully BEFORE the line's
    own start) - its own right edge now touches Point 2 exactly, with
    nothing to hide underneath because there's nothing drawn there in
    the first place. See _direction_of_attack_bowtie_stub_layer() for
    the separate decorative stub this leaves room for.
    """

    bowtie = QgsMarkerSymbol()

    triangle_size = _DIRECTION_OF_ATTACK_BOWTIE_TRIANGLE_SIZE_MM

    right_triangle = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.Triangle,
        triangle_size
    )

    right_triangle.setAngle(
        90
    )

    right_triangle.setColor(
        QColor(0, 0, 0, 0)
    )

    right_triangle.setStrokeWidth(
        0.5
    )

    right_triangle.setOffset(
        QPointF(
            0,
            triangle_size / 2 - _DIRECTION_OF_ATTACK_BOWTIE_CENTER_OFFSET_MM
        )
    )

    _apply_offensive_line_color(
        right_triangle,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    bowtie.changeSymbolLayer(
        0,
        right_triangle
    )

    left_triangle = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.Triangle,
        triangle_size
    )

    left_triangle.setAngle(
        270
    )

    left_triangle.setColor(
        QColor(0, 0, 0, 0)
    )

    left_triangle.setStrokeWidth(
        0.5
    )

    left_triangle.setOffset(
        QPointF(
            0,
            triangle_size / 2 + _DIRECTION_OF_ATTACK_BOWTIE_CENTER_OFFSET_MM
        )
    )

    _apply_offensive_line_color(
        left_triangle,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    bowtie.appendSymbolLayer(
        left_triangle
    )

    bowtie_layer = QgsMarkerLineSymbolLayer(True)

    bowtie_layer.setSubSymbol(
        bowtie
    )

    bowtie_layer.setPlacements(
        Qgis.MarkerLinePlacement.FirstVertex
    )

    return bowtie_layer


def _direction_of_attack_bowtie_stub_layer():

    """
    "the arrow shaft should protrude slightly beyond the bowtie" - the
    project maintainer's own words, 2026-08-12, once the bowtie itself
    moved fully before the line's own start (see _direction_of_attack_
    bowtie_layer()'s own "third follow-up" comment) and left nothing
    for a real shaft segment to visually connect to on that side. This
    is NOT real line geometry - just a short, fixed-length `Shape.Line`
    marker (QGIS's own literal line-segment shape), positioned at the
    bowtie's own left edge the same "fixed mm offset, rotated into the
    line's own local frame" way every other glyph in this module is
    (see _direction_of_attack_bowtie_layer()'s own comment for the
    angle=90 rotation maths this reuses directly).
    """

    stub = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.Line,
        _DIRECTION_OF_ATTACK_BOWTIE_STUB_LENGTH_MM
    )

    stub.setAngle(
        90
    )

    stub.setStrokeWidth(
        0.5
    )

    stub.setOffset(
        QPointF(
            0,
            -_DIRECTION_OF_ATTACK_BOWTIE_STUB_CENTER_OFFSET_MM
        )
    )

    _apply_offensive_line_color(
        stub,
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    stub_marker = QgsMarkerSymbol()

    stub_marker.changeSymbolLayer(
        0,
        stub
    )

    stub_layer = QgsMarkerLineSymbolLayer(True)

    stub_layer.setSubSymbol(
        stub_marker
    )

    stub_layer.setPlacements(
        Qgis.MarkerLinePlacement.FirstVertex
    )

    return stub_layer


# Direction of Attack - Main Attack's own double chevron (140602, page
# 433) - a SMALLER chevron nested inside a LARGER (OUTER) one, both
# pointing the same way, with their own open (back) ends joined by a
# short strut on each side. Originally (2026-08-12) built as a single
# fully hand-authored SVG (the real Shape.ArrowHead's own exact corner
# coordinates weren't known at the time) through four rounds of direct
# maintainer correction (parallel arms, inner-vs-outer swap, angle
# matched to the real chevron's own ~43.7-degree half-angle measured by
# probe render). **Rebuilt the same day** once Direction of Attack for
# a Feint (see _direction_of_attack_feint_outer_chevron_layer()'s own
# comment) established a real probe measurement of the built-in
# Shape.ArrowHead's own exact corner coordinates and a proven parallel-
# offset technique for a genuine outer chevron: "start with the symbol
# for feint; change the outer chevron to solid line, add line segments
# to join ends of both the stubs" - the maintainer's own words. Main
# Attack's INNER chevron is now the same real, shared QgsSimpleMarker
# SymbolLayer(Shape.ArrowHead) every other variant uses (built once,
# universally, in _direction_of_attack_symbol() below - no more special
# case), and only the OUTER chevron - plus the two struts connecting
# each of its own back corners to the real inner chevron's own back
# corners - is Main Attack's own extra hand-authored SVG layer, reusing
# Feint's own exact offset geometry (same gap = side_length/6 ratio,
# same corner coordinates) with two changes: SOLID stroke (no
# stroke-dasharray) and two more path segments for the struts.
_DIRECTION_OF_ATTACK_MAIN_ATTACK_OUTER_CHEVRON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" width="10" height="10">
  <path d="M 6.170,5.000 L 2.054,8.937
           M 6.170,5.000 L 2.054,1.063
           M 1.495,8.353 L 2.054,8.937
           M 1.495,1.647 L 2.054,1.063"
        fill="none" stroke="param(outline)" stroke-width="0.5" stroke-linecap="round" stroke-linejoin="round" />
</svg>"""


def _direction_of_attack_main_attack_outer_chevron_layer():

    """
    See _DIRECTION_OF_ATTACK_MAIN_ATTACK_OUTER_CHEVRON_SVG's own
    comment for the construction. Placed at LastVertex, rotating with
    the line, on top of the real inner chevron every variant already
    gets - lined up on the same anchor (both markers' own viewBox
    centres sit at the real chevron's own tip), so the struts drawn
    here against the real chevron's own corner coordinates (measured,
    not guessed - see _direction_of_attack_feint_outer_chevron_layer()'s
    own comment) land exactly on it with no extra offset needed.
    """

    svg_layer = QgsSvgMarkerSymbolLayer(
        "base64:" + base64.b64encode(
            _DIRECTION_OF_ATTACK_MAIN_ATTACK_OUTER_CHEVRON_SVG.encode("utf-8")
        ).decode("ascii")
    )

    svg_layer.setSize(
        10.0
    )

    _apply_offensive_line_color(
        svg_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    chevron_marker = QgsMarkerSymbol()

    chevron_marker.changeSymbolLayer(
        0,
        svg_layer
    )

    chevron_line_layer = QgsMarkerLineSymbolLayer(True)

    chevron_line_layer.setSubSymbol(
        chevron_marker
    )

    chevron_line_layer.setPlacements(
        Qgis.MarkerLinePlacement.LastVertex
    )

    return chevron_line_layer


# Direction of Attack for a Feint (2026-08-12): "start with the
# supporting attack symbol, add a dashed chevron outside the main
# arrowhead, at a gap 1/6 of the length of arrowhead side, the new
# chevron being parallel to the existing arrowhead" - the maintainer's
# own words. The real arrowhead every other variant uses is the
# built-in QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead (size 6,
# strokeWidth 0.5) - not a hand-authored SVG like Main Attack's own
# double chevron - so its exact corner coordinates aren't exposed to
# build a genuine parallel offset against directly. Measured it with a
# dedicated probe render instead (a single such marker, rendered alone,
# located precisely via a column-wise min-y-spread scan to find the
# true tip regardless of stroke bleed - confirmed the marker's own
# ANCHOR point IS the tip itself, offset from the expected pixel by
# under 0.05mm, not the shape's bounding-box centre): half-angle from
# the centreline ~43.727 degrees (consistent with the ~43.7 degrees
# already measured for Main Attack's own inner chevron - the same
# shape, same size, same probe technique) and arm (side) length
# ~4.8505mm.
#
# Built the outer chevron with the same proven technique Main Attack's
# own outer chevron and Axis of Advance's own mct_axis_of_advance_
# outer_chevron() both already established: offset EACH arm of the
# real chevron perpendicular, outward (away from the centreline) by a
# fixed distance - here gap = side_length / 6 = 4.8505/6 = 0.8084mm,
# per the maintainer's own explicit ratio - then re-intersect the two
# offset lines for the new chevron's own tip, rather than picking
# points independently (which is exactly what produced non-parallel
# arms the first time this technique was tried, for Main Attack's own
# original hand-authored double chevron - see _DIRECTION_OF_ATTACK_
# MAIN_ATTACK_OUTER_CHEVRON_SVG's own comment for how that first
# attempt was later replaced by a real probe-measured version of this
# same technique). This naturally pushes the new tip further along the
# direction of travel than the real tip (by gap/sin(half-angle) ~=
# 1.1696mm) and spreads
# the new back corners wider - a true nested "V" outside the real one,
# each arm mathematically parallel to its own real counterpart, not
# just visually similar.
#
# Drawn in a viewBox scaled 1 SVG unit = 1mm (a 10x10 square, so the
# ambiguity Main Attack's own non-square 460x300 viewBox had over which
# dimension QgsSvgMarkerSymbolLayer's own `size` maps to doesn't apply
# here - width and height are equal, so any mapping gives the same
# scale) with the real chevron's own tip placed at the square's centre
# (5,5) - the same "declared viewBox's own geometric centre = anchor"
# convention every other hand-authored SVG glyph in this module uses -
# so this marker's own anchor lines up with the real chevron's own tip/
# LastVertex exactly, and the offset geometry above (computed relative
# to that real tip at the origin) only needs a flat +5/+5 shift into
# SVG space. Dashed via the SVG's own stroke-dasharray (no QgsLineSymbol
# dash-style property exists for a marker layer) - not connected to the
# real chevron by struts (unlike Main Attack's own nested pair) since
# the maintainer only asked for a second, separate outer chevron here,
# matching Axis of Advance's own Feint precedent.
_DIRECTION_OF_ATTACK_FEINT_OUTER_CHEVRON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10" width="10" height="10">
  <path d="M 6.170,5.000 L 2.054,8.937
           M 6.170,5.000 L 2.054,1.063"
        fill="none" stroke="param(outline)" stroke-width="0.5" stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1,0.6" />
</svg>"""


def _direction_of_attack_feint_outer_chevron_layer():

    """
    See _DIRECTION_OF_ATTACK_FEINT_OUTER_CHEVRON_SVG's own comment for
    the construction. Placed at LastVertex, rotating with the line, the
    same convention every other fixed-orientation arrowhead/glyph in
    this module already uses - lined up on the SAME anchor point as the
    real chevron (both markers' own viewBox centres sit at the real
    chevron's own tip), so it renders correctly nested around it
    without any extra offset needed here.
    """

    svg_layer = QgsSvgMarkerSymbolLayer(
        "base64:" + base64.b64encode(
            _DIRECTION_OF_ATTACK_FEINT_OUTER_CHEVRON_SVG.encode("utf-8")
        ).decode("ascii")
    )

    svg_layer.setSize(
        10.0
    )

    _apply_offensive_line_color(
        svg_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    chevron_marker = QgsMarkerSymbol()

    chevron_marker.changeSymbolLayer(
        0,
        svg_layer
    )

    chevron_line_layer = QgsMarkerLineSymbolLayer(True)

    chevron_line_layer.setSubSymbol(
        chevron_marker
    )

    chevron_line_layer.setPlacements(
        Qgis.MarkerLinePlacement.LastVertex
    )

    return chevron_line_layer


def _direction_of_attack_symbol(aviation=False, main_attack=False, supporting_attack=False, enemy=False, ground_axis=False, feint=False):

    """
    Table H-XI, H.5.13.2 - a plain status-driven line with a small,
    UNFILLED chevron arrowhead ("ArrowHead", not "ArrowHeadFilled") at
    the last vertex - built for real (not approximated), confirmed
    against the standard's own template pictures (pages 432-433) that
    every Direction of Attack variant shares this exact same base
    construction.

    **2026-08-10 follow-up** (see module docstring for the full report):
    the chevron's own stroke was too thin to read as the standard's own
    bold, thick-lined open arrowhead (confirmed by directly zooming the
    standard's own template picture, page 433) - widened along with
    Field T (on the shaft, near the tip) and Field W-W1 (below the
    shaft). Friendly Aviation additionally gets its own bowtie glyph
    partway along the line - see _direction_of_attack_bowtie_layer()'s
    own docstring.

    **2026-08-11 follow-up**, Friendly Aviation only, per the project
    maintainer's own explicit instruction: the template picture (page
    432) also shows a real "Aviation - Fixed Wing" unit icon, boxed,
    BEFORE the line's own origin - added via _unit_context_icon_layer()
    ("we can use the aviation - fixed wing symbol from the milsymbol.js"
    - the maintainer's own words, once told QGIS has no non-square
    Rectangle marker shape of its own to hand-build a frame with; the
    real SIDC render already comes framed, so this was the simpler and
    more standard-compliant fix anyway). Field T also moved off its
    shared _designation_end_marker_layer() font-marker technique, for
    Friendly Aviation only, onto a genuine PAL label with real Selective
    Masking - "just behind the arrow head... in line with the arrow
    shaft" - see create_offensive_control_measures_lines_layer()'s own
    labelling call and _DIRECTION_OF_ATTACK_AVIATION_DESIGNATION_LABEL_
    EXPRESSION's own comment for the construction; this line's own
    symbol layer gets a stable `.setId()` (_DIRECTION_OF_ATTACK_
    AVIATION_LINE_SYMBOL_LAYER_ID) so that label can mask it. Every
    other Direction of Attack variant is untouched - still the plain
    font-marker Field T, no unit icon.

    **2026-08-12 follow-up**, per the project maintainer's own direct
    comparison against the standard's own EXAMPLE picture: Friendly
    Aviation's own unit icon now renders upright/level ("like axis of
    advance, the symbol for aviation should be straight" - `rotate=
    False`, same correction Axis of Advance's own base icons got the
    round before). Field W-W1 (DTG)'s own fix is NOT aviation-specific -
    it moved from a centred-on-the-tip single-line label to a two-line
    one pulled back behind the arrowhead ("the DTG... is going ahead of
    the arrow" - see _DTG_START_LINE_EXPRESSION's own comment) for
    every Direction of Attack variant, since that part of the
    construction is shared, generic code, not aviation-only styling.

    **Same-day second follow-up**, Friendly Aviation only: "the line
    should not be visible below the bowtie" led to a real rabbit hole
    (a second masked label, then a `line_substring()`-based trim, both
    tried and abandoned - see _direction_of_attack_bowtie_layer()'s own
    "third follow-up" comment for the full history) before landing on
    the maintainer's own simpler fix: move the bowtie so it never
    overlaps the real line in the first place. `line_layer` is plain
    again here, exactly like every other Direction of Attack variant -
    nothing to trim or mask.

    **2026-08-12, moving on to Main Attack**: "using with the DOA -
    Friendly aviation symbol, drop the aviation symbol, bowtie and line
    segment stub" - the maintainer's own words, confirmed against the
    standard's own template/example pictures for 140602 (page 433):
    Main Attack shares the SAME plain status-driven shaft every other
    Direction of Attack variant has, but with NO unit icon/bowtie/stub
    (those were Friendly Aviation's own, per H.5.13.2's own drawing),
    and its own DOUBLE chevron arrowhead in place of the single one -
    originally a fully hand-authored SVG, later rebuilt (see this
    function's own "back to Main Attack" entry below) once the real
    chevron's own exact geometry was measured for Feint - see
    _DIRECTION_OF_ATTACK_MAIN_ATTACK_OUTER_CHEVRON_SVG's own comment.
    Field T moved to the CENTRE of the shaft, and (a same-round follow-
    up once the shaft's own line ran directly under it there) onto a
    genuine masked PAL label - the exact same technique Friendly
    Aviation's own Field T uses, see _DIRECTION_OF_ATTACK_MAIN_
    DESIGNATION_LABEL_EXPRESSION's own comment - rather than the
    rotate-with-line font-marker technique every other variant still
    uses. Scoped to `direction_of_attack_main` only via the new `main_
    attack` parameter - every other variant (Supporting Attack/Ground
    Axis/Feint/Enemy) is untouched, still the single chevron and
    LastVertex font-marker Field T.

    **2026-08-12, Supporting Attack**: "start with the friendly aviation
    symbol, drop the milsymbol, horizontal stub and bow tie" - the
    maintainer's own words. Friendly Aviation's own base minus the unit
    icon/bowtie/stub - single chevron, masked PAL Field T at the same
    0.9 anchor percent near the arrowhead, DTG unchanged. Scoped via the
    new `supporting_attack` parameter.

    **Same day, Enemy**: "start with the supporting attack, default the
    colour to red, that's all" - the maintainer's own words. Identical
    construction to Supporting Attack (`enemy` parameter mirrors
    `supporting_attack` everywhere in this function); the red colour
    needs no new code, since `direction_of_attack_enemy` is already in
    _ENEMY_MEASURE_TYPES and every colour call this construction goes
    through is already `_apply_offensive_line_color()`.

    **Same day, Friendly Ground Axis**: "replicate the supporting attack
    symbol for friendly ground axis, that's all, no change to the
    symbol required" - the maintainer's own words. Identical
    construction again (`ground_axis` parameter mirrors `supporting_
    attack`/`enemy`); ordinary affiliation colouring, since `direction_
    of_attack_ground_axis` is not in _ENEMY_MEASURE_TYPES.

    **Same day, Feint**: "start with the supporting attack symbol, add
    a dashed chevron outside the main arrowhead, at a gap 1/6 of the
    length of arrowhead side, the new chevron being parallel to the
    existing arrowhead" - the maintainer's own words. Same base as
    Supporting Attack (`feint` parameter mirrors `ground_axis`/`enemy`
    everywhere above), plus one extra symbol layer appended right after
    the real chevron - see _direction_of_attack_feint_outer_chevron_
    layer()'s own comment for the construction.

    **Same day, back to Main Attack**: "start with the symbol for
    feint; change the outer chevron to solid line, add line segments to
    join ends of both the stubs" - the maintainer's own words. Main
    Attack's own base (icon-free construction, Field T at the CENTRE of
    the shaft rather than the near-arrowhead 0.9 anchor every other
    variant uses - see this docstring's own "moving on to Main Attack"
    entry above) is UNCHANGED here; only the arrowhead is rebuilt, and
    only the two deltas the maintainer actually named. Main Attack no
    longer has its own special-cased chevron branch at all - it now
    goes through the SAME real, shared single-chevron construction
    (`chevron_line_layer` below) every other variant uses, universally
    built rather than only for non-main-attack variants, then gets ONE
    extra layer appended on top: _direction_of_attack_main_attack_
    outer_chevron_layer() - Feint's own outer-chevron geometry (the
    same measured half-angle/gap-ratio/corner coordinates), but SOLID
    instead of dashed, with two more path segments strutting each of
    its own back corners to the real inner chevron's own back corners
    - see that function's own comment for the construction.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.5
    )

    _apply_offensive_line_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    if aviation:

        line_layer.setId(
            _DIRECTION_OF_ATTACK_AVIATION_LINE_SYMBOL_LAYER_ID
        )

    elif main_attack:

        line_layer.setId(
            _DIRECTION_OF_ATTACK_MAIN_LINE_SYMBOL_LAYER_ID
        )

    elif supporting_attack:

        line_layer.setId(
            _DIRECTION_OF_ATTACK_SUPPORTING_LINE_SYMBOL_LAYER_ID
        )

    elif enemy:

        line_layer.setId(
            _DIRECTION_OF_ATTACK_ENEMY_LINE_SYMBOL_LAYER_ID
        )

    elif ground_axis:

        line_layer.setId(
            _DIRECTION_OF_ATTACK_GROUND_AXIS_LINE_SYMBOL_LAYER_ID
        )

    elif feint:

        line_layer.setId(
            _DIRECTION_OF_ATTACK_FEINT_LINE_SYMBOL_LAYER_ID
        )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    # 2026-08-12: "start with the symbol for feint; change the outer
    # chevron to solid line, add line segments to join ends of both the
    # stubs" - the maintainer's own words. Main Attack no longer has
    # its own special-cased chevron branch - this real, single-chevron
    # QgsSimpleMarkerSymbolLayer(Shape.ArrowHead) is now built for
    # EVERY variant, universally (see this function's own docstring's
    # "back to Main Attack" entry).
    chevron_marker = QgsMarkerSymbol()

    chevron_layer = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        6
    )

    chevron_layer.setColor(
        QColor(0, 0, 0, 0)
    )

    # 2026-08-12: "reduce the arrowhead width to match the shaft
    # width" - the project maintainer's own words. Matches line_
    # layer's own 0.5mm width above - the 2026-08-10 widening to
    # 1.3 (see this function's own docstring) overshot into
    # looking noticeably thicker than the shaft itself, not just
    # "bold enough to read".
    chevron_layer.setStrokeWidth(
        0.5
    )

    _apply_offensive_line_color(
        chevron_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    chevron_marker.changeSymbolLayer(
        0,
        chevron_layer
    )

    chevron_line_layer = QgsMarkerLineSymbolLayer(True)

    chevron_line_layer.setSubSymbol(
        chevron_marker
    )

    chevron_line_layer.setPlacements(
        Qgis.MarkerLinePlacement.LastVertex
    )

    symbol.appendSymbolLayer(
        chevron_line_layer
    )

    if feint:

        symbol.appendSymbolLayer(
            _direction_of_attack_feint_outer_chevron_layer()
        )

    if main_attack:

        symbol.appendSymbolLayer(
            _direction_of_attack_main_attack_outer_chevron_layer()
        )

    if aviation:

        symbol.appendSymbolLayer(
            _unit_context_icon_layer(
                "aviation_fixed_wing",
                offset=QPointF(_DIRECTION_OF_ATTACK_AVIATION_ICON_OFFSET_MM, 0),
                rotate=False
            )
        )

        symbol.appendSymbolLayer(
            _direction_of_attack_bowtie_layer()
        )

        symbol.appendSymbolLayer(
            _direction_of_attack_bowtie_stub_layer()
        )

    elif not (main_attack or supporting_attack or enemy or ground_axis or feint):

        symbol.appendSymbolLayer(
            _designation_end_marker_layer(
                _UNIQUE_DESIGNATION_LABEL_EXPRESSION,
                QPointF(0, -1.0)
            )
        )

    # 2026-08-12, cross-checked against the standard's own Table H-XI
    # (see _DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT's own comment for
    # the full "that clears all chapter X/XI - cross check please"
    # story): Field W-W1 (DTG) clusters right below Field T, near PT2 -
    # the line's own START - not pulled back from the tip the way this
    # code originally placed it ("the DTG in the plugin is going ahead
    # of the arrow" - built the same "don't refer the manual" day as
    # Field T's own now-retired 0.9 anchor). Moved from LastVertex (a
    # large NEGATIVE X pull-back from the tip) to FirstVertex (a small
    # POSITIVE X push past the start) - QgsFontMarkerSymbolLayer still
    # centres its own text block ON the anchor point, so a small
    # positive offset clears the FirstVertex point itself without
    # colliding with Friendly Aviation's own icon/bowtie/stub, which
    # all sit at NEGATIVE offsets (before the start) on the opposite
    # side. Still below the shaft (positive Y, this project's
    # established convention). Two separate marker layers, one per line
    # (see _DTG_START_LINE_EXPRESSION's own comment for why a single
    # marker with an embedded newline doesn't work), stacked with a Y
    # offset roughly one font-size apart.
    symbol.appendSymbolLayer(
        _designation_end_marker_layer(
            _DTG_START_LINE_EXPRESSION,
            QPointF(8.0, 2.2),
            size=2.6,
            placement=Qgis.MarkerLinePlacement.FirstVertex
        )
    )

    symbol.appendSymbolLayer(
        _designation_end_marker_layer(
            _DTG_END_LINE_EXPRESSION,
            QPointF(8.0, 4.8),
            size=2.6,
            placement=Qgis.MarkerLinePlacement.FirstVertex
        )
    )

    return symbol


def _simple_end_label_line_symbol(character, always_dashed=False):

    """
    Final Coordination Line/Limit of Advance/Line of Departure/Line of
    Departure and Contact/Probable Line of Deployment - a plain line
    with a fixed abbreviation at each end (the same construction as
    c2_measures.py's own Light Line/maneuver_control_measures.py's own
    FEBA, via the shared _end_label_layer()). `always_dashed` is for
    Probable Line of Deployment only - see module docstring for the
    standard's own explicit "always dashed" note.
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

    if always_dashed:

        line_layer.setPenStyle(
            Qt.PenStyle.DashLine
        )

    else:

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


def _infiltration_lane_symbol():

    """
    Table H-XI, code 140800, page 435. "A control measure that
    coordinates forward and lateral movement of infiltrating units and
    fixes fire planning responsibilities." Re-read directly against its
    own draw rules (not the variable-width tapered-ribbon construction
    this module's own docstring originally assumed it was, alongside
    Table H-X's Axis of Advance family) - it's two parallel lines (the
    "lane") with a plain Field T centred between them, approximated the
    same way Main Attack's own doubled outline is: two fixed-offset
    copies of one status-driven line, rather than genuine polygon-offset
    geometry synthesised from a real "point 3 sets the width" anchor
    point (this module still has no general mechanism for that - see
    module docstring). The small grey "S" mark crossing both lines in
    the template picture measured out as flat mid-grey fill (direct
    pixel sampling, not assumed) - illustrative per this appendix's own
    EXAMPLE-column convention, not drawn geometry, so it's not
    reproduced.
    """

    symbol = QgsLineSymbol()

    # 2.0mm each side (not the tighter 1.2mm Main Attack's own doubled
    # outline uses) - found by live render-and-compare, not guessed:
    # a gap that tight left Field T's own text overlapping both lines
    # at once, and since the text and lines share the same affiliation-
    # driven colour, the overlap made the text unreadable (visible only
    # as a negative-space silhouette) rather than merely crowded.
    symbol.changeSymbolLayer(
        0,
        _axis_of_advance_shaft_layer(offset_mm=2.0)
    )

    symbol.appendSymbolLayer(
        _axis_of_advance_shaft_layer(offset_mm=-2.0)
    )

    symbol.appendSymbolLayer(
        _designation_end_marker_layer(
            _UNIQUE_DESIGNATION_LABEL_EXPRESSION,
            QPointF(0, 0),
            size=2.4,
            placement=Qgis.MarkerLinePlacement.CentralPoint
        )
    )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "axis_of_advance_airborne": lambda: _axis_of_advance_ribbon_symbol(variant="airborne"),
    "axis_of_advance_aviation": lambda: _axis_of_advance_ribbon_symbol(variant="aviation"),
    "axis_of_advance_attack_helicopter": lambda: _axis_of_advance_ribbon_symbol(variant="attack_helicopter"),
    "axis_of_advance_main_attack": lambda: _axis_of_advance_ribbon_symbol(variant="main_attack"),
    "axis_of_advance_supporting_attack": lambda: _axis_of_advance_ribbon_symbol(variant="supporting_attack"),
    "axis_of_advance_feint": lambda: _axis_of_advance_ribbon_symbol(variant="feint"),
    "axis_of_advance_enemy": lambda: _axis_of_advance_ribbon_symbol(variant="enemy"),
    "direction_of_attack_aviation": lambda: _direction_of_attack_symbol(aviation=True),
    "direction_of_attack_main": lambda: _direction_of_attack_symbol(main_attack=True),
    "direction_of_attack_supporting": lambda: _direction_of_attack_symbol(supporting_attack=True),
    "direction_of_attack_ground_axis": lambda: _direction_of_attack_symbol(ground_axis=True),
    "direction_of_attack_feint": lambda: _direction_of_attack_symbol(feint=True),
    "direction_of_attack_enemy": lambda: _direction_of_attack_symbol(enemy=True),
    "infiltration_lane": _infiltration_lane_symbol,
    "final_coordination_line": lambda: _simple_end_label_line_symbol("FCL"),
    "limit_of_advance": lambda: _simple_end_label_line_symbol("LOA"),
    "line_of_departure": lambda: _simple_end_label_line_symbol("LD"),
    "line_of_departure_and_contact": lambda: _simple_end_label_line_symbol("LD/LC"),
    "probable_line_of_deployment": lambda: _simple_end_label_line_symbol(
        "PLD", always_dashed=True
    ),
}

_AREA_SYMBOL_BUILDERS = {
    measure_type: _status_driven_area_outline_symbol
    for measure_type in AREA_MEASURE_TYPE_LABELS
}

_AREA_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN "
    f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" ' ' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
) + " ELSE '' END"


def create_offensive_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Offensive Control Measures (Tables
    H-X/H-XI) - see this module's own docstring for the full
    measure-type list and what was approximated/scoped out.
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
            QgsField("dtg_start", QMetaType.Type.QString),
            QgsField("dtg_end", QMetaType.Type.QString),
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
        QgsDefaultValue("'line_of_departure'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    # Overrides _configure_affiliation_field()'s own shared cross-
    # appendix default (DEFAULT_AFFILIATION, "unspecified"/black) for
    # THIS layer only - per the project maintainer's own observation
    # while smoke-testing Friendly Airborne: nearly every measure type
    # on this specific layer is an inherently friendly, own-force
    # graphic (only the two Enemy-flagged variants aren't, and those
    # already render red regardless of this field - see
    # _OFFENSIVE_LINE_COLOR_EXPRESSION), so defaulting to "friend"
    # matches the common case without the user needing to change it
    # by hand every time. Scoped to just this module's own Lines
    # layer, not the shared helper other H control-measure layers
    # (Boundaries, Maneuver, Defensive, C2 Measures) still use
    # unchanged.
    layer.setDefaultValueDefinition(
        layer.fields().indexOf("affiliation"),
        QgsDefaultValue("'friend'")
    )

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("length_km"),
        QgsDefaultValue("mct_length_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    # No general along-line label for most measure types - Axis of
    # Advance/Direction of Attack carry Field T/W-W1 via their own data-
    # defined symbol-layer markers (see _designation_end_marker_layer()),
    # Infiltration Lane's own Field T likewise, and the simple end-
    # labelled lines (FCL/LOA/LD/...) use a FIXED abbreviation via a
    # symbol-layer marker instead (see _simple_end_label_line_symbol()),
    # the same "PL"/"FEBA" pattern already established.
    #
    # Direction of Attack - Friendly Aviation and Main Attack are the
    # two exceptions so far (2026-08-11/12) - their own Field T needs
    # real Selective Masking (see _direction_of_attack_symbol()'s own
    # comments), which only a genuine PAL label can give. Each gets its
    # own QgsRuleBasedLabeling rule, filtered to its own measure type
    # only - a different tool from Boundary's own single shared
    # QgsPalLayerSettings (there, ALL boundaries share one expression;
    # here, each variant's own rule is entirely independent, matching
    # _configure_area_designation_labeling()'s own rule-per-placement
    # precedent in c2_measures.py). Every other measure type on this
    # layer still gets no label at all (no rule matches it), same as
    # before.
    #
    # BOTH rules pass the SAME COMBINED masked_symbol_layer_ids list
    # (not each its own single id) - confirmed by render that giving
    # each rule a DIFFERENT set logs "Different sets of symbol layers
    # are masked by different sources! Only one (arbitrary) set will be
    # retained!" and silently drops one variant's own masking. QGIS's
    # own Selective Masking configuration is apparently LAYER-wide, not
    # per-rule/per-provider, unlike the label CONTENT itself (which
    # correctly stays per-rule via each rule's own filterExpression).
    # Masking a symbol layer id that a given feature doesn't even have
    # is harmless - the cut only ever happens where that rule's own
    # label text actually renders.
    _direction_of_attack_masked_line_ids = [
        _DIRECTION_OF_ATTACK_AVIATION_LINE_SYMBOL_LAYER_ID,
        _DIRECTION_OF_ATTACK_MAIN_LINE_SYMBOL_LAYER_ID,
        _DIRECTION_OF_ATTACK_SUPPORTING_LINE_SYMBOL_LAYER_ID,
        _DIRECTION_OF_ATTACK_ENEMY_LINE_SYMBOL_LAYER_ID,
        _DIRECTION_OF_ATTACK_GROUND_AXIS_LINE_SYMBOL_LAYER_ID,
        _DIRECTION_OF_ATTACK_FEINT_LINE_SYMBOL_LAYER_ID,
    ]

    aviation_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _DIRECTION_OF_ATTACK_AVIATION_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_direction_of_attack_masked_line_ids,
            line_anchor_percent=_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT,
            anchor_text_point=QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )
    )

    aviation_rule.setFilterExpression(
        '"measure_type" = \'direction_of_attack_aviation\''
    )

    main_attack_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _DIRECTION_OF_ATTACK_MAIN_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_direction_of_attack_masked_line_ids,
            line_anchor_percent=_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT,
            anchor_text_point=QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )
    )

    main_attack_rule.setFilterExpression(
        '"measure_type" = \'direction_of_attack_main\''
    )

    supporting_attack_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _DIRECTION_OF_ATTACK_SUPPORTING_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_direction_of_attack_masked_line_ids,
            line_anchor_percent=_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT,
            anchor_text_point=QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )
    )

    supporting_attack_rule.setFilterExpression(
        '"measure_type" = \'direction_of_attack_supporting\''
    )

    # 2026-08-12: "start with the supporting attack, default the colour
    # to red, that's all" - the maintainer's own words. Same rule shape
    # as Supporting Attack's own (same anchor percent/text point); the
    # colour comes for free below, since _OFFENSIVE_LINE_COLOR_EXPRESSION
    # already forces red for "direction_of_attack_enemy".
    enemy_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _DIRECTION_OF_ATTACK_ENEMY_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_direction_of_attack_masked_line_ids,
            line_anchor_percent=_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT,
            anchor_text_point=QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )
    )

    enemy_rule.setFilterExpression(
        '"measure_type" = \'direction_of_attack_enemy\''
    )

    # 2026-08-12: "replicate the supporting attack symbol for friendly
    # ground axis, that's all, no change to the symbol required" - the
    # maintainer's own words. Same rule shape as Supporting Attack's
    # own; ordinary affiliation colouring below (not in _ENEMY_MEASURE_
    # TYPES).
    ground_axis_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _DIRECTION_OF_ATTACK_GROUND_AXIS_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_direction_of_attack_masked_line_ids,
            line_anchor_percent=_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT,
            anchor_text_point=QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )
    )

    ground_axis_rule.setFilterExpression(
        '"measure_type" = \'direction_of_attack_ground_axis\''
    )

    # 2026-08-12: "start with the supporting attack symbol, add a
    # dashed chevron outside the main arrowhead..." - the maintainer's
    # own words. Same rule shape as Supporting Attack's own; the added
    # outer chevron is a separate symbol layer entirely (see
    # _direction_of_attack_feint_outer_chevron_layer()'s own comment),
    # not part of this label.
    feint_rule = QgsRuleBasedLabeling.Rule(
        _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.Line,
            _DIRECTION_OF_ATTACK_FEINT_DESIGNATION_LABEL_EXPRESSION,
            masked_symbol_layer_ids=_direction_of_attack_masked_line_ids,
            line_anchor_percent=_DIRECTION_OF_ATTACK_LABEL_ANCHOR_PERCENT,
            anchor_text_point=QgsLabelLineSettings.AnchorTextPoint.StartOfText
        )
    )

    feint_rule.setFilterExpression(
        '"measure_type" = \'direction_of_attack_feint\''
    )

    # 2026-08-12: "change the colour of the unique designation also
    # into blue (friend)" - the maintainer's own words, matching the
    # rest of this construction's own affiliation-driven colouring (the
    # line, the bowtie, the icon) instead of the plain black every PAL
    # label gets by default. A genuine PAL label has its own DATA-
    # DEFINED colour property - set directly on each rule's own
    # settings here (both variants, not just aviation - Main Attack's
    # own font-marker Field T was already affiliation-coloured via
    # _designation_font_marker()'s own _apply_offensive_line_color()
    # call, so keeping that same colouring once it moved to a PAL label
    # avoids a visual regression, not a new ask).
    for rule in (
        aviation_rule,
        main_attack_rule,
        supporting_attack_rule,
        enemy_rule,
        ground_axis_rule,
        feint_rule,
    ):

        rule.settings().dataDefinedProperties().setProperty(
            QgsPalLayerSettings.Property.Color,
            QgsProperty.fromExpression(_OFFENSIVE_LINE_COLOR_EXPRESSION)
        )

    root_rule = QgsRuleBasedLabeling.Rule(None)

    root_rule.appendChild(
        aviation_rule
    )

    root_rule.appendChild(
        main_attack_rule
    )

    root_rule.appendChild(
        supporting_attack_rule
    )

    root_rule.appendChild(
        enemy_rule
    )

    root_rule.appendChild(
        ground_axis_rule
    )

    root_rule.appendChild(
        feint_rule
    )

    layer.setLabeling(
        QgsRuleBasedLabeling(root_rule)
    )

    layer.setLabelsEnabled(
        True
    )

    return layer


def create_offensive_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Offensive Control Measures - Table
    H-XI's own "Areas" sub-section (Assault Position, Attack Position,
    Objective Area).
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
        QgsDefaultValue("'objective_area'")
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


# Table H-XI's own "Points" sub-section (H.5.13.2, page 439) - a single
# entry, Point of Departure (160400), the box+cone construction the
# Table H-VI/H-IX point families already share (c2_measures.py/
# defensive_control_measures.py) - anchored at its own tip, same as
# every other member of that family. See module docstring's 2026-08-10
# entry for why this got its own dedicated layer (matching every other
# H.5.x group's own "own layer(s)" convention).
#
# **2026-08-12 rebuild**, per the project maintainer's own explicit
# request: "same construction of symbol as Fly-To-Point except instead
# of FLY it has PD and the unique designation is outside the symbol on
# top right as in the Fly-To symbol". The ORIGINAL build here used a
# hand-computed QgsPalLayerSettings offset (own local-SVG-coordinate
# probe, own mm-per-unit scale factor) instead of milsymbol.js's own
# native `uniqueDesignation` text-modifier slot, per a comment claiming
# both of milsymbol's own text slots were "wrong" for this SIDC - a
# claim a direct probe render this same day disproved: rendering SIDC
# 10032500001604000000 with `{"uniqueDesignation": "1"}` shows milsymbol
# placing the designation at (x=150, y=-30), the SAME y as the "PD" text
# itself (also y=-30) and just past the box's own right edge (x=140) -
# exactly "outside the symbol on top right", matching the standard's own
# example (page 439) precisely. Whatever produced that original "both
# wrong" finding wasn't this plain slot, checked correctly here with a
# real probe, not assumed either way. Rebuilt to use the exact same
# `mct_sidc_svg(...)` two-extra-argument technique c2_measures.py's own
# _POINT_SIDC_EXPRESSION already established for Fly-To-Point and every
# other entry in that shared family - see this module's own
# _POINTS_SIDC_EXPRESSION below - dropping the custom PAL label
# entirely (_configure_points_labeling()/_point_of_departure_label_
# offset() and their own three local-coordinate constants all retired
# with it, no longer needed).
POINT_ENTITY_LABELS = {
    "point_of_departure": "Point of Departure",
}

# The four real SIDC standard identities - see
# POINT_AFFILIATION_LABELS in _control_measure_shared.py for why a
# Points layer must not use the lines/areas AFFILIATION_LABELS.
_POINT_AFFILIATION_LABELS = POINT_AFFILIATION_LABELS

_POINT_STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned",
}

_POINTS_DEFAULT_MARKER_SIZE_MM = 8.0

# Second/third arguments route the feature's own "unique_designation"
# through milsymbol.js's own native `uniqueDesignation` text-modifier
# slot - see this constant's own preceding comment for the probe that
# confirmed this slot already positions the text correctly for 160400,
# and c2_measures.py's own _POINT_SIDC_EXPRESSION for the identical
# pattern this mirrors. upper(...) per H.5.4's "all text labeling in
# upper case" rule, coalesce(...,'') so a blank field passes an empty
# string rather than short-circuiting the whole function call to NULL
# (mct_sidc_svg()'s own docstring documents both, the same footguns
# already worked out for that shared family).
_POINTS_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false),"
    "upper(coalesce(\"unique_designation\",'')),"
    "'uniqueDesignation'"
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
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue("'point_of_departure'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))


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

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.VerticalAnchor,
        QgsProperty.fromValue("bottom")
    )

    symbol.changeSymbolLayer(
        0,
        svg_layer
    )

    return QgsSingleSymbolRenderer(symbol)


def create_offensive_control_measures_points_layer(name=POINTS_LAYER_NAME):

    """
    A fresh, empty point layer for Table H-XI's own "Points"
    sub-section - Point of Departure (160400) - see this module's own
    docstring for why this moved out of the shared control_measure_
    points.py layer into its own dedicated one here.
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


def add_offensive_control_measures_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_offensive_control_measures_lines_layer
    )


def add_offensive_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_offensive_control_measures_areas_layer
    )


def add_offensive_control_measures_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_offensive_control_measures_points_layer
    )
