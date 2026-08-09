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

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsFontMarkerSymbolLayer,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    ECHELON_LABELS,
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
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "C2 Measures (Lines)"
AREAS_LAYER_NAME = "C2 Measures (Areas)"

# Re-exported for callers/tests that only need this module's own
# constants, not every H control-measure module's shared ones.
__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "ECHELON_LABELS",
    "create_c2_measures_lines_layer",
    "create_c2_measures_areas_layer",
    "add_c2_measures_lines_layer",
    "add_c2_measures_areas_layer",
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


def _end_label_layer(placement, character):

    """
    Shared by _light_line_symbol() (and any future line type with the
    same "fixed abbreviation at each end" convention) - `character`
    (e.g. "LL") as a small font-marker label at the given end
    (FirstVertex/LastVertex), offset above the line so it doesn't overlap
    the line's own stroke.

    **2026-08-09 correction**: an earlier version of this helper also
    drew a short perpendicular "tick" mark at each end, reading Table
    H-IV's own TEMPLATE column (page 397) as if the up-arrows connecting
    "LL"/"PT 1"/"PT 2" to the line were a drawn tick that's part of the
    symbol. The project maintainer corrected this: those arrows are the
    same kind of pointer/callout used throughout this appendix's own
    diagrams to show where a label attaches or which point is PT1 vs
    PT2 (compare Table H-III's own Boundary template, which uses
    identical arrows purely to point at anchor points) - not geometry to
    be rendered. Confirmed against the EXAMPLE column too: the real
    drawn symbol there is just the line with "LL" above each end: no
    separate tick. General lesson, not just this one symbol: this
    appendix's own EXAMPLE columns mark explanatory-only additions in
    GREY (e.g. the same Light Line example's own "PL CRAB" name) - grey
    is the signal for "not part of the control measure", not the
    presence or absence of an arrow/callout shape, which appears in
    black throughout this appendix purely as diagram annotation.
    """

    font_layer = QgsFontMarkerSymbolLayer()

    font_layer.setFontFamily(
        "Arial"
    )

    font_layer.setSize(
        3.5
    )

    font_layer.setColor(
        QColor(0, 0, 0)
    )

    font_layer.setCharacter(
        character
    )

    # Offset is in the marker's own tangent-rotated frame (see this
    # module's other FirstVertex/LastVertex uses), so a plain Y offset
    # moves perpendicular to the line - negative Y confirmed (by
    # rendering both signs) to be the one that reads above the line
    # rather than below it, regardless of the line's own drawn
    # direction.
    font_layer.setOffset(
        QPointF(0, -2.5)
    )

    _apply_affiliation_color(
        font_layer,
        [QgsSymbolLayer.Property.FillColor]
    )

    label_marker = QgsMarkerSymbol()

    label_marker.changeSymbolLayer(
        0,
        font_layer
    )

    label_layer = QgsMarkerLineSymbolLayer()

    label_layer.setSubSymbol(
        label_marker
    )

    label_layer.setPlacements(
        placement
    )

    return label_layer


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


def _status_driven_area_outline_symbol():

    """
    Shared by Area of Operations/Named Area of Interest/Target Area of
    Interest/Airfield Zone (Table H-V, Mini-Phase H2) - every one of
    them is a plain unfilled, status-driven solid/dashed outline
    (H.5.1.1.3/Table H-I; that rule's own text explicitly covers "area
    control measures", not just linear ones, so it applies here the same
    way it does to Boundary - see _STATUS_LINE_STYLE_EXPRESSION's own
    comment) with no other shape distinction between them in their own
    template pictures (page 399-400) - what differs between these four
    is only the label (_AREA_DESIGNATION_LABEL_EXPRESSION) and, for
    Airfield Zone alone, a centred icon (see _airfield_zone_symbol()'s
    own comment).
    """

    outline_layer = QgsSimpleLineSymbolLayer()

    outline_layer.setColor(
        QColor(0, 0, 0)
    )

    outline_layer.setWidth(
        0.4
    )

    _apply_affiliation_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    outline_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
        }
    )

    symbol.changeSymbolLayer(
        0,
        outline_layer
    )

    return symbol


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
_BOUNDARY_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'boundary' THEN "
    "upper(\"unique_designation\")"
    " || CASE WHEN \"echelon\" IS NOT NULL AND \"echelon\" != ''"
    " THEN '\\n' || (" + _ECHELON_CHARACTER_EXPRESSION + ") ELSE '' END"
    " || CASE WHEN \"far_designation\" IS NOT NULL AND \"far_designation\" != ''"
    " THEN '\\n' || upper(\"far_designation\") ELSE '' END"
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
