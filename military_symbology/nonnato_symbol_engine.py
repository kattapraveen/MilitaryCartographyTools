# -*- coding: utf-8 -*-

"""
Rendering support for non-NATO symbology, on top of the existing
milsymbol.js pipeline (symbol_engine.py) rather than beside it - every
icon here still goes through render_symbol_svg()/mct_sidc_svg() first,
with milsymbol's own `frame`/`fill`/`monoColor` options doing most of
the work (see docs/non-nato-symbology-tracker.md's Part A: rectangle
frame, no fill, affiliation by outline colour for Units; no frame at
all for Equipment). What lives here is only the part milsymbol cannot
do by itself: a handful of entity/echelon-specific SVG fixups, the
Combined Arms rectangle overlay, and one entity with no SIDC at all.

Every fixup here is string/regex surgery on milsymbol's own rendered
SVG output, never an edit to the vendored milsymbol.js source - the
same technique symbol_engine.py's own _inject_text() already uses for
icons milsymbol can't otherwise label, and the one every custom icon
in the rules record was designed and confirmed against.

Military Cartography Tools
"""

import re

from .sidc import build_sidc
from .symbol_engine import (
    _escape_text,
    _injected_text_colour,
    render_symbol_svg,
    scale_svg_stroke_width,
)


# Part D's settled affiliation colour palette - six affiliations, not
# milsymbol's own four, so this is never derived from milsymbol's
# built-in colour modes. Every non-NATO render passes one of these as
# the `monoColor` option.
AFFILIATION_COLOURS = {
    "friend": "#3060c0",
    "hostile": "#c02020",
    "neutral": "#20a020",
    "unknown": "#c08010",
    "friendly_paramilitary": "#8b5a2b",
    "nonstate_hostile": "#8020a0",
}

# Every one of the six maps to the SIDC's own "friend" affiliation,
# and this is NOT a cosmetic default - it is load-bearing. Confirmed
# live: passing `frame: true` to milsymbol does not force a rectangle,
# it only means "draw whichever frame shape this SIDC's own
# affiliation digit selects" - hostile is a diamond, neutral a square,
# unknown a quatrefoil, and only friend is a rectangle. The settled
# rule is ONE frame shape for every affiliation, so the SIDC's own
# affiliation digit must always resolve to friend regardless of which
# of the six the feature actually has - the real colour is entirely
# monoColor's job (see AFFILIATION_COLOURS above), decoupled from this
# on purpose. Do not "simplify" this back to a same-name mapping for
# friend/hostile/neutral/unknown - that reintroduces per-affiliation
# frame shapes, exactly the bug this comment exists to prevent.
SIDC_AFFILIATION_FOR = {
    "friend": "friend",
    "hostile": "friend",
    "neutral": "friend",
    "unknown": "friend",
    "friendly_paramilitary": "friend",
    "nonstate_hostile": "friend",
}

# Same stroke thickening every NATO render already gets by default
# (expressions/military_symbology_functions.py's DEFAULT_STROKE_SCALE)
# - the settled "line weight unchanged from NATO" rule means non-NATO
# should match it exactly, not fall back to milsymbol's own unscaled
# stroke-width="3".
DEFAULT_STROKE_SCALE = 1.3

# Mines default to this green rather than affiliation colour - see the
# rules record's "Mine colour" note, reusing obstacle_control_measures
# .py's own OBSTACLE_GREEN_EXPRESSION shade for consistency.
MINE_GREEN = "#009b00"


def stabilised_nonnato_size_expression(
    base_size_expression, amplified_width_expression, plain_width_expression
):

    """
    `base_size_expression`, scaled so the ICON stays exactly the same
    size when a unique designation is typed into it - the non-NATO
    counterpart to _control_measure_shared.py's own stabilised_point_
    size_expression(), decoupled from that function's hardwired
    mct_sidc_svg()/mct_build_sidc() call shape (it locates those two
    literal substrings inside a single combined expression string,
    which no mct_nonnato_*_svg() call contains). Callers here instead
    pass the two already-built width CALLS directly - one with the
    feature's own designation, one with none - since each non-NATO
    layer already has both in hand (echelon/status/combined_arms vary
    the argument list per layer, so there is no single shared
    "designation-less" transform to derive automatically the way the
    NATO version does).

    Fixed 2026-09-02, reported live against Land Unit ("when i insert a
    land unit with designator, the size of the glyph is reducing making
    it unreadable") - QGIS sizes an SVG marker by its own declared
    width, and milsymbol widens that declared width to fit whatever
    designation text it carries, so a fixed marker size draws a visibly
    smaller icon the moment text is typed in. Dividing the amplified
    width by the plain one and multiplying the base size by that ratio
    holds the icon steady and lets the text hang outside it instead -
    same fix, same reasoning as the NATO one this mirrors, applied
    across every non-NATO layer built so far (Land Unit, Land
    Equipment, SIGINT) - Control Measure Points already had this, since
    nine of its ten entities go through the plain NATO mct_sidc_svg()
    pipeline unchanged (see that layer's own module for why).

    The ratio is guarded the same way, and for the same reason: a NULL
    feature attribute must not null out the whole size expression and
    silently drop the "scale" field's own multiplier with it. nullif()
    also covers a width of 0, which is what the width function returns
    for anything it cannot render at all.
    """

    return (
        f"({base_size_expression}) * coalesce({amplified_width_expression}"
        f" / nullif({plain_width_expression}, 0), 1)"
    )

# --- Mine family (Mines and Obstacles, moved out of Land Equipment
#     2026-09-03 - see mines_and_obstacles_layer_nonnato.py) -----------
#
# Three real APP-6E entities (already render correctly with no fixup,
# see the rules record's "Mine icons" note) plus six synthetic icons
# with no SIDC at all - the whole family defaults to MINE_GREEN
# regardless of the feature's own affiliation, same as obstacle_
# control_measures.py's own NATO-side convention for the same reason.
# This rendering logic is layer-agnostic and unchanged by the 2026-09-03
# move - only which QGIS layer offers these entities changed.
#
# Synthetic keys are outside APP-6E's own numbering on purpose (a
# leading "nonnato_" prefix), so they can never collide with a real
# entity key sidc_2525e.py might add later.
UNKNOWN_MINE_ENTITY = "nonnato_unknown_mine"
INFLUENCE_MINE_ANTI_TANK_ENTITY = "nonnato_influence_mine_anti_tank"
INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY = "nonnato_influence_mine_anti_personnel"
ANTITANK_MINE_BOOBY_TRAPPED_ENTITY = "nonnato_antitank_mine_booby_trapped"
BAR_MINE_ENTITY = "nonnato_bar_mine"
DIRECTIONAL_MINE_ENTITY = "nonnato_directional_mine"

# Every mine-family entity, real or synthetic - checked by
# render_nonnato_equipment_svg() to apply the green-not-affiliation
# rule regardless of which of the two groups an entity is in.
MINE_ENTITIES = frozenset({
    "land_mine",                    # Antipersonnel Mine
    "antitank_mine",                # Antitank Mine
    "antipersonnel_land_mine",      # Antipersonnel Fragmentation Mine
    UNKNOWN_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
    DIRECTIONAL_MINE_ENTITY,
})

_MINE_R = 22
_MINE_CX, _MINE_CY = 100, 100


def _mine_circle(colour, filled):

    fill = colour if filled else "none"

    return (
        f'<circle cx="{_MINE_CX}" cy="{_MINE_CY}" r="{_MINE_R}" '
        f'stroke-width="3" stroke="{colour}" fill="{fill}"></circle>'
    )


def unfilled_antipersonnel_fragmentation_mine(svg):

    """
    antipersonnel_land_mine renders with its circle AND its two horns
    both filled (hardcoded, like every other exception the full sweep
    catalogued). Confirmed 2026-08-31: only the circle is overridden
    to hollow here, to distinguish it from Antitank Mine's solid
    circle - the two horns stay filled exactly as milsymbol draws
    them.
    """

    return re.sub(
        r'<circle cx="100" cy="100" r="22" stroke-width="3" '
        r'stroke="([^"]+)" fill="[^"]+"',
        r'<circle cx="100" cy="100" r="22" stroke-width="3" '
        r'stroke="\1" fill="none"',
        svg,
        count=1,
    )


def unknown_mine_svg(colour):

    """No APP-6E equivalent - a hollow circle with a plain vertical diameter line."""

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="46 46 108 108">'
        + _mine_circle(colour, filled=False)
        + f'<path d="M{_MINE_CX},78 L{_MINE_CX},122" stroke-width="3" '
        f'stroke="{colour}" fill="none"></path>'
        '</svg>'
    )


def _influence_mine_svg(colour, filled):

    # Horn shaft + arrowhead geometry, both sides - confirmed 2026-08-
    # 31 against a rendered comparison. Base points sit on the circle's
    # own edge; arrowhead wings are 9 units back from the tip, 6 units
    # either side of the shaft's own line.
    horns = (
        f'<path d="M119,89 L137,64" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M136.6,74.8 L137,64 L126.9,67.8" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M81,89 L63,64" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M73.1,67.8 L63,64 L63.4,74.8" stroke-width="3" stroke="{colour}" fill="none"></path>'
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="46 46 108 108">'
        + _mine_circle(colour, filled=filled)
        + horns
        + '</svg>'
    )


def influence_mine_anti_tank_svg(colour):

    """No APP-6E equivalent - Antitank Mine's solid circle plus two arrow-tipped horns."""

    return _influence_mine_svg(colour, filled=True)


def influence_mine_anti_personnel_svg(colour):

    """No APP-6E equivalent - identical to Influence Mine (Anti Tank), hollow circle instead."""

    return _influence_mine_svg(colour, filled=False)


def antitank_mine_booby_trapped_svg(colour):

    """
    No APP-6E equivalent - Antitank Mine's solid circle with four
    plain (no arrowhead) horns at exactly 45/135/225/315 degrees,
    25% shorter than Influence Mine's own horn length (30.8 -> 23.1,
    measured from the circle's own edge outward) - confirmed 2026-08-
    31 against a rendered comparison of both the first draft (which
    reused Influence Mine's ~54 degree angle at full length) and this
    corrected version.
    """

    horns = (
        f'<path d="M115.6,84.4 L131.9,68.1" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M84.4,84.4 L68.1,68.1" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M84.4,115.6 L68.1,131.9" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M115.6,115.6 L131.9,131.9" stroke-width="3" stroke="{colour}" fill="none"></path>'
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="46 46 108 108">'
        + _mine_circle(colour, filled=True)
        + horns
        + '</svg>'
    )


def bar_mine_svg(colour):

    """
    No APP-6E equivalent - Antitank Mine's solid circle with a hollow
    rectangle below it (top edge touching the circle's own bottom
    edge, centred): height = circle diameter / 3, width = 2x the
    diameter (revised down from an initial 2.5x). A dashed horizontal
    line runs through the rectangle's own vertical centre, full width;
    dash length is double the standard dash unit used elsewhere in
    this scheme (8 vs 4) while the gap stays at the standard 3 - only
    the dash itself was asked to lengthen, not the gap.
    """

    diameter = _MINE_R * 2
    rect_w = diameter * 2
    rect_h = diameter / 3
    rect_x = _MINE_CX - rect_w / 2
    rect_y = _MINE_CY + _MINE_R
    mid_y = rect_y + rect_h / 2

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="20 46 160 100">'
        + _mine_circle(colour, filled=True)
        + f'<rect x="{rect_x:g}" y="{rect_y:g}" width="{rect_w:g}" '
        f'height="{rect_h:g}" stroke-width="3" stroke="{colour}" fill="none"></rect>'
        + f'<path d="M{rect_x:g},{mid_y:g} L{rect_x + rect_w:g},{mid_y:g}" '
        f'stroke-width="3" stroke="{colour}" stroke-dasharray="8,3" fill="none"></path>'
        '</svg>'
    )


def directional_mine_svg(colour):

    """
    No APP-6E equivalent - designed live, 2026-09-03: "use booby trap
    symbol to begin with, remove the bottom lines at 315 and 225 deg,
    change the top lines to dashed, add a parallel line each to the two
    top lines also dashed". Starts from Control Measure Point's own
    Booby Trap shape (booby_trap_control_measure_svg() - hollow circle
    + four 45/135/225/315-degree horns), drops the two bottom horns
    (225/315 degrees), and makes each of the two remaining top horns
    (45/135 degrees) dashed with a second, parallel dashed line of the
    same length alongside it.

    The horn/offset geometry (perpendicular offset, dash pattern "4,3",
    new line sitting outward - away from the OTHER horn - rather than
    the pair straddling the original's centreline) is not a fresh
    guess: it is recovered from a same-shaped "dashed parallel horns"
    design originally built 2026-09-01 for this same Booby Trap control
    measure, then superseded there once the maintainer clarified the
    circle's FILL (not the horn count/style) was the actual complaint -
    see booby_trap_control_measure_svg()'s own docstring for that
    history. That geometry was never wrong, just built for the wrong
    icon at the time; reused here for Directional Mine instead.

    **Legibility pass, same day, after a real smoke test**: "the horns
    (parallel) lines are not clearly discernable - increase their
    stroke width by 30%, make them 20% longer and increase the gap
    between the parallel lines slightly to make them more distinct".
    Stroke width: the horn's own PRE-scale width goes from 3 to 3.9 -
    not simply 3*1.3 - so that DEFAULT_STROKE_SCALE's own later 1.3x
    (applied uniformly to every stroke in the final render) lands on an
    effective width 30% bigger than before (3*1.3=3.9 -> 3.9*1.3=5.07),
    not 30% of the unscaled base. Length: each horn's own OUTER tip
    (the inner end stays anchored exactly on the circle's own edge)
    moves out along the same 45-degree line by 20% - (131.9,68.1) ->
    (135.2,64.8) and (68.1,68.1) -> (64.8,64.8). Gap: the perpendicular
    offset between each horn and its own parallel twin goes from 5 to
    7 units.
    """

    offset = 7 / (2 ** 0.5)  # perpendicular unit vector at 45 degrees, times 7 (was 5)
    stroke_width = 3.9  # was 3 - see this function's own docstring

    top_right = (
        f'<path d="M115.6,84.4 L135.2,64.8" stroke-width="{stroke_width:g}" '
        f'stroke="{colour}" stroke-dasharray="4,3" fill="none"></path>'
        f'<path d="M{115.6 + offset:g},{84.4 + offset:g} '
        f'L{135.2 + offset:g},{64.8 + offset:g}" stroke-width="{stroke_width:g}" '
        f'stroke="{colour}" stroke-dasharray="4,3" fill="none"></path>'
    )

    top_left = (
        f'<path d="M84.4,84.4 L64.8,64.8" stroke-width="{stroke_width:g}" '
        f'stroke="{colour}" stroke-dasharray="4,3" fill="none"></path>'
        f'<path d="M{84.4 - offset:g},{84.4 + offset:g} '
        f'L{64.8 - offset:g},{64.8 + offset:g}" stroke-width="{stroke_width:g}" '
        f'stroke="{colour}" stroke-dasharray="4,3" fill="none"></path>'
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="46 46 108 108">'
        + _mine_circle(colour, filled=False)
        + top_right + top_left
        + '</svg>'
    )


_SYNTHETIC_MINE_SVG = {
    UNKNOWN_MINE_ENTITY: unknown_mine_svg,
    INFLUENCE_MINE_ANTI_TANK_ENTITY: influence_mine_anti_tank_svg,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY: influence_mine_anti_personnel_svg,
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY: antitank_mine_booby_trapped_svg,
    BAR_MINE_ENTITY: bar_mine_svg,
    DIRECTIONAL_MINE_ENTITY: directional_mine_svg,
}


def is_synthetic_entity(entity):

    """True for any entity with no SIDC/milsymbol render at all - Enemy (Info Unknown), one of the six synthetic mines, or one of the three Vehicle-family entities."""

    # _SYNTHETIC_VEHICLE_SVG is defined further down, beside the rest of
    # the Land Equipment vehicle family's own geometry - a module-level
    # name resolved when this is CALLED, same as ENEMY_INFO_UNKNOWN_
    # ENTITY just below.
    return (
        entity == ENEMY_INFO_UNKNOWN_ENTITY
        or entity in _SYNTHETIC_MINE_SVG
        or entity in _SYNTHETIC_VEHICLE_SVG
    )

# Enemy (Info Unknown) has no APP-6E entity at all - a standalone frame
# variant (two concentric rectangles, no icon glyph inside), always
# hostile red regardless of the feature's own affiliation field, per
# the rules record.
ENEMY_INFO_UNKNOWN_ENTITY = "enemy_info_unknown"

# Three more of the same shape, requested live 2026-09-06: "let's expand
# enemy (info unknown) in land units - enemy (info unknown) remains as
# is / enemy (echelon unknown) - add a "?" on top of the glyph / enemy
# (designation unknown) - add a "?" to the right center of the glyph
# (same place as unique designation right) / enemy (type unknown) - add
# a "?" in the center of the glyph". All four share the same two
# concentric rectangles and the same fixed hostile red; they differ only
# in where a question mark goes, or whether there is one at all.
ENEMY_ECHELON_UNKNOWN_ENTITY = "enemy_echelon_unknown"
ENEMY_DESIGNATION_UNKNOWN_ENTITY = "enemy_designation_unknown"
ENEMY_TYPE_UNKNOWN_ENTITY = "enemy_type_unknown"

ENEMY_ENTITIES = frozenset({
    ENEMY_INFO_UNKNOWN_ENTITY,
    ENEMY_ECHELON_UNKNOWN_ENTITY,
    ENEMY_DESIGNATION_UNKNOWN_ENTITY,
    ENEMY_TYPE_UNKNOWN_ENTITY,
})

_ENEMY_INFO_UNKNOWN_COLOUR = AFFILIATION_COLOURS["hostile"]


def is_enemy_unknown(entity):

    """True for any of the four Enemy entities - they all bypass SIDC and milsymbol entirely."""

    return entity in ENEMY_ENTITIES


def enemy_info_unknown_svg():

    """
    Two concentric rectangles, no milsymbol call at all - confirmed
    against a render 2026-08-31. Outer rectangle matches every other
    Land Unit icon's own frame (150 wide x 100 tall in milsymbol's
    path-space, x 25..175, y 50..150); inner is inset 15 units on every
    side (120 x 70), an arbitrary but reasonable margin, not derived
    from any other measurement in this scheme.
    """

    colour = _ENEMY_INFO_UNKNOWN_COLOUR

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="21 46 158 108">'
        f'<rect x="25" y="50" width="150" height="100" '
        f'stroke-width="4" stroke="{colour}" fill="none"></rect>'
        f'<rect x="40" y="65" width="120" height="70" '
        f'stroke-width="4" stroke="{colour}" fill="none"></rect>'
        '</svg>'
    )


# Every Land Unit icon's own frame occupies the same rectangle in
# milsymbol's path-space - 150 wide x 100 tall, x 25..175, y 50..150 -
# whatever the entity, echelon or affiliation: milsymbol's own frame
# path is `M25,50 l150,0 0,100 -150,0 z`, Enemy's own hand-built outer
# rectangle states the same numbers, and Administration or Logistics'
# circle is sized to match. Its own vertical centre is what the side
# designations are centred on. See inject_side_designations().
_UNIT_FRAME_TOP = 50
_UNIT_FRAME_BOTTOM = 150
_UNIT_FRAME_LEFT = 25
_UNIT_FRAME_RIGHT = 175

_UNIT_FRAME_CENTRE_Y = (_UNIT_FRAME_TOP + _UNIT_FRAME_BOTTOM) / 2

# milsymbol's own Headquarters flag mast, copied exactly rather than
# guessed: rendering any unit with headquarters=True adds
# `M25,150 L25,250` at the frame's own stroke width - straight down
# from the frame's bottom-left corner, as long again as the frame is
# tall. Static Formation Headquarters needs its own copy because it
# never reaches a SIDC for milsymbol to amplify.
_HQ_MAST_LENGTH = _UNIT_FRAME_BOTTOM - _UNIT_FRAME_TOP


def _hq_mast_path(colour):

    return (
        f'<path d="M{_UNIT_FRAME_LEFT:g},{_UNIT_FRAME_BOTTOM:g} '
        f'L{_UNIT_FRAME_LEFT:g},{_UNIT_FRAME_BOTTOM + _HQ_MAST_LENGTH:g}" '
        f'stroke-width="4" stroke="{colour}" fill="none"></path>'
    )


# Static Formation Headquarters - requested live 2026-09-06: "Use a
# basic rectangle with flag mast of headquarters - instead of right line
# of rectangle - replace with a < the resulting rectangle looks like a
# flag". So the frame's own three other sides are drawn as usual and its
# right side becomes a chevron notched inward, turning the rectangle
# into a pennant. No entity glyph inside it, and no SIDC - a standalone
# frame variant, the same shape of thing Enemy and Administration or
# Logistics are.
STATIC_FORMATION_HQ_ENTITY = "nonnato_static_formation_hq"

# A fifth of the frame's own width. Not specified - "replace with a <"
# fixes the shape but not the depth - so this is a starting value chosen
# to read clearly as a pennant at map size.
_STATIC_HQ_NOTCH_DEPTH = (_UNIT_FRAME_RIGHT - _UNIT_FRAME_LEFT) / 5


def static_formation_hq_svg(colour):

    """A pennant-shaped frame plus the Headquarters mast - see this section's own comment."""

    notch_x = _UNIT_FRAME_RIGHT - _STATIC_HQ_NOTCH_DEPTH

    outline = (
        f'<path d="M{_UNIT_FRAME_RIGHT:g},{_UNIT_FRAME_TOP:g} '
        f'L{_UNIT_FRAME_LEFT:g},{_UNIT_FRAME_TOP:g} '
        f'L{_UNIT_FRAME_LEFT:g},{_UNIT_FRAME_BOTTOM:g} '
        f'L{_UNIT_FRAME_RIGHT:g},{_UNIT_FRAME_BOTTOM:g} '
        f'L{notch_x:g},{_UNIT_FRAME_CENTRE_Y:g} Z" '
        f'stroke-width="4" stroke="{colour}" fill="none"></path>'
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="21 46 158 208">'
        + outline
        + _hq_mast_path(colour)
        + '</svg>'
    )


# Administration or Logistics Unit - requested live 2026-09-06: "Add a
# simple circle - same dimensions as the rectangle of land units, option
# to add unique designation left/right as existing". A standalone frame
# variant with no APP-6E entity and no glyph inside it, the same shape
# of thing the Enemy family is - but affiliation-coloured normally, not
# pinned to one colour.
#
# "Same dimensions as the rectangle" is read as the same VERTICAL extent
# (the frame is 150 x 100 at x 25..175, y 50..150, and a circle has only
# one dimension to match): diameter 100, centred at 100,100, so it fills
# the frame's own height and shares its top and bottom edges. The left
# and right designations then hang off it exactly as they do off a
# rectangle, since inject_side_designations() measures whatever ink is
# actually there.
ADMIN_LOGISTICS_ENTITY = "nonnato_admin_logistics"

_ADMIN_LOGISTICS_RADIUS = 50


def admin_logistics_svg(colour):

    """A single hollow circle at the Land Unit frame's own height - see this section's own comment."""

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="21 46 158 108">'
        f'<circle cx="100" cy="100" r="{_ADMIN_LOGISTICS_RADIUS:g}" '
        f'stroke-width="4" stroke="{colour}" fill="none"></circle>'
        '</svg>'
    )


# The question mark the other three Enemy entities carry. Sized to
# _SIDE_DESIGNATION_FONT_SIZE deliberately, not to a constant of its
# own: "enemy (designation unknown) - add a ? to the right center of
# the glyph (same place as unique designation right)" means it has to
# land exactly where a real right designation would, at exactly that
# size, and the other two match it so all three read as one family.
#
# Injected AFTER inject_side_designations(), and positioned from the
# icon's own measured content the same way that function is - so with
# no designation typed, "designation unknown" sits precisely on the
# right designation's own anchor, and with one typed it steps outside
# it rather than colliding.
_ENEMY_QUESTION = "?"


def _enemy_question_above(content, font_size, colour):

    """"on top of the glyph" - centred horizontally, sitting clear above it."""

    left, top, width, _ = content

    return (
        left + width / 2,
        top - _DESIGNATION_GAP,
        "middle",
    )


def _enemy_question_right(content, font_size, colour):

    """"to the right center of the glyph (same place as unique designation right)"."""

    left, top, width, height = content

    return (
        left + width + _DESIGNATION_GAP,
        top + height / 2 + font_size * _CAP_HEIGHT_RATIO / 2,
        "start",
    )


def _enemy_question_centre(content, font_size, colour):

    """"in the center of the glyph"."""

    left, top, width, height = content

    return (
        left + width / 2,
        top + height / 2 + font_size * _CAP_HEIGHT_RATIO / 2,
        "middle",
    )


_ENEMY_QUESTION_PLACEMENTS = {
    ENEMY_ECHELON_UNKNOWN_ENTITY: _enemy_question_above,
    ENEMY_DESIGNATION_UNKNOWN_ENTITY: _enemy_question_right,
    ENEMY_TYPE_UNKNOWN_ENTITY: _enemy_question_centre,
}


def inject_enemy_question_mark(svg, entity, colour):

    """
    Adds the "?" that distinguishes Enemy (Echelon Unknown), (Designation
    Unknown) and (Type Unknown) from plain Enemy (Info Unknown), which
    carries none - see this section's own comment for the placements and
    why the size is the side designation's own.
    """

    placement = _ENEMY_QUESTION_PLACEMENTS.get(entity)

    if placement is None:
        return svg

    match = _VIEWBOX_PATTERN.search(svg)

    if not match:
        return svg

    vb_x, vb_y, vb_w, vb_h = (float(value) for value in match.groups())

    content = _content_bounds(svg, fallback=(vb_x, vb_y, vb_w, vb_h))

    font_size = _SIDE_DESIGNATION_FONT_SIZE

    x, baseline_y, anchor = placement(content, font_size, colour)

    width = _designation_text_width(_ENEMY_QUESTION, font_size)
    cap_height = font_size * _CAP_HEIGHT_RATIO

    left = (
        x - width / 2 if anchor == "middle"
        else x - width if anchor == "end"
        else x
    )

    svg = _expand_viewbox_for_rect(
        svg, left, baseline_y - cap_height, width, cap_height
    )

    element = (
        f'<text x="{x:g}" y="{baseline_y:g}" text-anchor="{anchor}" '
        f'font-size="{font_size:g}" font-family="Arial" stroke="none" '
        f'fill="{colour}">{_ENEMY_QUESTION}</text>'
    )

    return _inject_before_closing_svg(svg, element)


# Requested live 2026-09-06: "Motorised Infantry - start with the
# infantry glyph, add the two wheels under it (from the B vehicle or C
# vehicle glyphs in land equipment)". APP-6E does have its own
# `infantry_motorized`, but it draws milsymbol's own motorized modifier,
# not this scheme's wheels - so this is a synthetic entity over plain
# `infantry`, same pattern as Air Defence Artillery and Air Force.
MOTORISED_INFANTRY_ENTITY = "nonnato_motorised_infantry"

# Same pattern again, 2026-09-06: Infantry's own glyph with a "^" added
# in the lower half - see _mountain_chevron().
MOUNTAIN_INFANTRY_ENTITY = "nonnato_mountain_infantry"

# And again, same day: "start with mechanised infantry - add the wheels
# of the motorised infantry to it". Mechanised Infantry is this layer's
# own label for the real `armored_mechanized_tracked`, and the wheels
# are literally Motorised Infantry's own - so this pairs with the
# existing "Light Armour/Recce & Support (Tracked)" as its wheeled
# counterpart.
RECCE_SUPPORT_WHEELED_ENTITY = "nonnato_recce_support_wheeled"

# Requested live 2026-09-06: "Self Propelled Artillery - Use the
# Artillery glyph (rectangle with a filled dot) - add three wheels (same
# as APV wheeled)" and "Parachute Field Artillery - Use the Artillery
# glyph - add the parachute symbol (from the Parachute unit - inserted
# below the diagonals)". Both sit on the real `field_artillery` glyph.
SELF_PROPELLED_ARTILLERY_ENTITY = "nonnato_self_propelled_artillery"
PARACHUTE_FIELD_ARTILLERY_ENTITY = "nonnato_parachute_field_artillery"

def _motorised_wheels(colour):

    """
    Motorised Infantry's own two wheels below the frame - "add the two
    wheels under it (from the B vehicle or C vehicle glyphs in land
    equipment)", so literally those: the Vehicle family's own wheel
    geometry, reused unchanged.

    It lines up exactly because both shapes are the SAME rectangle -
    Land Unit's frame and the Vehicle family's body are both 150 x 100
    at x 25..175, y 50..150 - so the wheels already sit one radius below
    its bottom edge and one radius inside each side, with no
    re-derivation at all.

    Stroke matches the FRAME's own 4 rather than an interior glyph's 3:
    the wheels hang off the frame's bottom edge and read as part of that
    outline. Deliberately NOT the Vehicle family's own compensated
    stroke, which is scaled for a 166-wide viewBox and a 0.8 size
    multiplier - neither applies on this layer.

    Returns (markup, lowest point reached) - the wheels hang below the
    frame, so the caller has to grow the viewBox for them.
    """

    wheels = "".join(
        f'<circle cx="{centre_x:g}" cy="{_VEHICLE_WHEEL_CENTRE_Y:g}" '
        f'r="{_VEHICLE_WHEEL_RADIUS:g}" stroke-width="4" stroke="{colour}" '
        'fill="none"></circle>'
        for centre_x in _VEHICLE_WHEEL_CENTRE_XS
    )

    return wheels, _VEHICLE_WHEEL_CENTRE_Y + _VEHICLE_WHEEL_RADIUS


# Mountain Infantry - requested live 2026-09-06: "start with normal
# infantry glyph - rectangle with diagonals - in the lower half of the
# rectangle add a "^" or s small triangle with the bottom ends on the
# rectangle bottom line, the height of the "mountain" is 1/3 of the
# rectangle height". Drawn as an open "^" rather than a closed triangle:
# its two ends sit ON the frame's own bottom line, which already closes
# the shape, and "^" is the form the request names first.
#
# Height is a third of the frame's own 100. The base is twice that,
# which puts both slopes at 45 degrees - not specified, chosen so it
# reads as a mountain rather than a spike.
_MOUNTAIN_HEIGHT = (_UNIT_FRAME_BOTTOM - _UNIT_FRAME_TOP) / 3

_MOUNTAIN_HALF_BASE = _MOUNTAIN_HEIGHT


def _mountain_chevron(colour):

    """Mountain Infantry's own "^", sitting on the frame's bottom line."""

    centre_x = (_UNIT_FRAME_LEFT + _UNIT_FRAME_RIGHT) / 2

    mark = (
        f'<path d="M{centre_x - _MOUNTAIN_HALF_BASE:g},{_UNIT_FRAME_BOTTOM:g} '
        f'L{centre_x:g},{_UNIT_FRAME_BOTTOM - _MOUNTAIN_HEIGHT:g} '
        f'L{centre_x + _MOUNTAIN_HALF_BASE:g},{_UNIT_FRAME_BOTTOM:g}" '
        f'stroke-width="4" stroke="{colour}" fill="none"></path>'
    )

    # Entirely inside the frame, so nothing to grow the viewBox for.
    return mark, None


def _self_propelled_wheels(colour):

    """
    Self Propelled Artillery's own three wheels - "add three wheels
    (same as APV wheeled)".

    "Same as APV wheeled" is read as that icon's own RULE, not its
    literal radius: three circles, each sized a third of the shape's own
    semi-minor axis, their tops touching its bottom edge, the outer two
    inset one radius from its sides and the third centring the group.
    Applied to the Land Unit frame that means radius 16.7, not the 6.7
    the APV oval takes - the literal radius would draw three dots barely
    a tenth of the frame's width, and would also clash with Motorised
    Infantry's own wheels sitting on the same layer at the frame's own
    scale. So this is Motorised Infantry's own two wheels with the
    middle one restored, which is exactly what the APV rule gives here.
    """

    centre_x = (_UNIT_FRAME_LEFT + _UNIT_FRAME_RIGHT) / 2

    wheels = "".join(
        f'<circle cx="{x:g}" cy="{_VEHICLE_WHEEL_CENTRE_Y:g}" '
        f'r="{_VEHICLE_WHEEL_RADIUS:g}" stroke-width="4" stroke="{colour}" '
        'fill="none"></circle>'
        for x in (
            _VEHICLE_WHEEL_CENTRE_XS[0], centre_x, _VEHICLE_WHEEL_CENTRE_XS[1]
        )
    )

    return wheels, _VEHICLE_WHEEL_CENTRE_Y + _VEHICLE_WHEEL_RADIUS


# The Parachute unit's own canopy-and-lines glyph, exactly as milsymbol
# emits it for `parachute_rigger` - the same path, so Parachute Field
# Artillery's own parachute is visibly the same object, not a redrawing
# of it.
_PARACHUTE_GLYPH_D = (
    "m 120,100 -20,20  m 0,0 -20,-20  m 0,0 c 0,-25 40,-25 40,0 H 80"
)

# The Parachute unit's own placement, for reference and for the test
# that pins the two to the same path.
_PARACHUTE_GLYPH_TRANSFORM = "translate(20, 49.5) scale(0.8)"

# That path's own extent in its own coordinates. The canopy is a single
# cubic from (80,100) to (120,100) with both controls at y=75, so its
# own crown sits at t=0.5 - (100 + 3*75 + 3*75 + 100) / 8 = 81.25 - not
# at the control points themselves.
_PARACHUTE_NATIVE_TOP = 81.25
_PARACHUTE_NATIVE_BOTTOM = 120
_PARACHUTE_NATIVE_CENTRE_X = 100

_PARACHUTE_NATIVE_HEIGHT = _PARACHUTE_NATIVE_BOTTOM - _PARACHUTE_NATIVE_TOP

# milsymbol's own stroke width for this glyph, before the group's own
# scale and before scale_svg_stroke_width()'s final widening.
_PARACHUTE_STROKE_WIDTH = 3.75

# Artillery's own filled dot, read off its real render.
_ARTILLERY_DOT_CENTRE_Y = 100
_ARTILLERY_DOT_RADIUS = 15
_ARTILLERY_DOT_STROKE_WIDTH = 3

# Resized 2026-09-06, on sight: "reduce the size of the parachute canopy
# just enough that it is clear of the dot and clear from the rectangle".
# At the Parachute unit's own 0.8 the canopy's crown sat about 3.5 units
# behind the dot, because Artillery's dot is filled and 30 across where
# Infantry's diagonal crossing - what that placement was designed
# around - is a thin X.
#
# So the scale is DERIVED rather than picked: fit the glyph's own INK
# (geometry plus a stroke that scales with it) into the clear band
# between the dot's own bottom edge and the frame's own bottom edge,
# leaving _PARACHUTE_CLEARANCE at each end.
_PARACHUTE_CLEARANCE = 3

_PARACHUTE_BAND_TOP = (
    _ARTILLERY_DOT_CENTRE_Y
    + _ARTILLERY_DOT_RADIUS
    + _ARTILLERY_DOT_STROKE_WIDTH / 2
    + _PARACHUTE_CLEARANCE
)

_PARACHUTE_BAND_BOTTOM = (
    _UNIT_FRAME_BOTTOM - 4 / 2 - _PARACHUTE_CLEARANCE
)

# Ink height at scale s is s * (native height + one full stroke width),
# half a stroke reaching past each end - so solving for the band gives
# the scale directly.
_PARACHUTE_ARTILLERY_SCALE = (_PARACHUTE_BAND_BOTTOM - _PARACHUTE_BAND_TOP) / (
    _PARACHUTE_NATIVE_HEIGHT + _PARACHUTE_STROKE_WIDTH
)

_PARACHUTE_ARTILLERY_TRANSLATE_X = _PARACHUTE_NATIVE_CENTRE_X * (
    1 - _PARACHUTE_ARTILLERY_SCALE
)

_PARACHUTE_ARTILLERY_TRANSLATE_Y = (
    _PARACHUTE_BAND_TOP
    + _PARACHUTE_ARTILLERY_SCALE * _PARACHUTE_STROKE_WIDTH / 2
    - _PARACHUTE_ARTILLERY_SCALE * _PARACHUTE_NATIVE_TOP
)


def _parachute_over_artillery(colour):

    """
    Parachute Field Artillery's own parachute - "add the parachute
    symbol (from the Parachute unit - inserted below the diagonals)",
    resized to clear the dot above it and the frame below - see this
    section's own comment for how the scale is derived.
    """

    transform = (
        f"translate({_PARACHUTE_ARTILLERY_TRANSLATE_X:g}, "
        f"{_PARACHUTE_ARTILLERY_TRANSLATE_Y:g}) "
        f"scale({_PARACHUTE_ARTILLERY_SCALE:g})"
    )

    mark = (
        f'<g transform="{transform}">'
        f'<path d="{_PARACHUTE_GLYPH_D}" '
        f'stroke-width="{_PARACHUTE_STROKE_WIDTH:g}" '
        f'stroke="{colour}" fill="none"></path>'
        "</g>"
    )

    return mark, None


_UNIT_ENTITY_MARKS = {
    MOTORISED_INFANTRY_ENTITY: _motorised_wheels,
    MOUNTAIN_INFANTRY_ENTITY: _mountain_chevron,
    # The same wheels, on Mechanised Infantry's own glyph instead.
    RECCE_SUPPORT_WHEELED_ENTITY: _motorised_wheels,
    SELF_PROPELLED_ARTILLERY_ENTITY: _self_propelled_wheels,
    PARACHUTE_FIELD_ARTILLERY_ENTITY: _parachute_over_artillery,
}


def inject_unit_entity_marks(svg, entity, colour):

    """
    The scheme's own additions to a milsymbol unit glyph - Motorised
    Infantry's wheels and Mountain Infantry's "^" so far.

    Injected after the side designations so those stay centred on the
    frame, the same ordering inject_enemy_question_mark() uses and for
    the same reason.
    """

    mark = _UNIT_ENTITY_MARKS.get(entity)

    if mark is None:
        return svg

    markup, lowest = mark(colour)

    if lowest is not None:

        match = _VIEWBOX_PATTERN.search(svg)

        if match:

            vb_x, vb_y, vb_w, _ = (float(value) for value in match.groups())

            svg = _expand_viewbox_for_rect(
                svg,
                vb_x,
                vb_y,
                vb_w,
                (lowest + 4 * DEFAULT_STROKE_SCALE / 2) - vb_y,
            )

    return _inject_before_closing_svg(svg, markup)


# --- Echelon-specific fixup: Detachment (NATO's Team/Crew) -----------

# milsymbol's own Team/Crew echelon glyph is always a circle plus one
# diagonal slash through it - a fixed path signature independent of
# size/colour/entity, since milsymbol's own path coordinates live on
# its own internal grid rather than scaling with the render size.
# Detachment is settled as a plain hollow circle, no slash - milsymbol
# has no option for this, so the slash is stripped after rendering.
_DETACHMENT_SLASH_PATTERN = re.compile(
    r'<path d="M80,40L120,20"\s*></path>'
)


def strip_detachment_slash(svg):

    return _DETACHMENT_SLASH_PATTERN.sub("", svg)


# --- Entity-specific fixup: Army Aviation's propeller -----------------

# aviation_fixed_wing's icon is a filled bowtie/propeller shape - one
# of the hardcoded-fill exceptions the fill:false option cannot reach.
# Confirmed 2026-08-31 as a deliberate carve-out from the general
# accept-as-is policy: swap it to stroke-only, which reads as a hollow
# figure-of-8 instead of a solid bowtie. The path's own `d` is a fixed
# signature; only the colour inside stroke="none" fill="COLOR" varies
# per affiliation, so that part is captured rather than assumed.
_ARMY_AVIATION_PROPELLER_PATTERN = re.compile(
    r'(<path d="M100,100 L130,88 c15,0 15,24 0,24 L100,100 70,112 '
    r'c-15,0 -15,-24 0,-24 Z" stroke-width="3" )stroke="none" '
    r'fill="([^"]+)"'
)


def hollow_army_aviation_propeller(svg):

    return _ARMY_AVIATION_PROPELLER_PATTERN.sub(
        r'\1stroke="\2" fill="none"',
        svg,
    )


# --- Entity-specific fixup: Parachute Rigger's composite icon ---------

# parachute_rigger's own icon (a dome canopy + two lines converging to
# a point below - the parachute itself) is drawn alone, with no
# Infantry frame content. The settled rule composites it: Infantry's
# own two diagonals as a base layer, and the existing parachute glyph
# shrunk 20% and repositioned into the lower wedge (the triangular
# region below the frame's own centroid, bounded by the two diagonals
# and the bottom edge) - confirmed against a render 2026-08-31.
#
# transform = translate(20, 49.5) scale(0.8): maps the parachute
# glyph's own bounding-box centre (100, 100.625) to (100, 130), a
# point comfortably inside the lower wedge (wedge width at the shrunk
# glyph's own top edge, y=114.5, is 43.5 against the glyph's 32 - well
# clear, not just barely fitting). Stroke width is boosted 1/0.8 = 1.25x
# inside the scaled group so the parachute's lines keep the same visual
# weight as the rest of the icon once the group's own scale shrinks
# them back down - see the settled "line weight unchanged from NATO"
# rule under Part D.
_INFANTRY_DIAGONALS = "M25,50 L175,150 M25,150 L175,50"

_PARACHUTE_PATH_PATTERN = re.compile(
    r'<path d="m 120,100 -20,20  m 0,0 -20,-20  m 0,0 '
    r'c 0,-25 40,-25 40,0 H 80" stroke-width="([\d.]+)" '
    r'stroke="([^"]+)" fill="none" ></path>'
)


def composite_parachute_rigger(svg):

    match = _PARACHUTE_PATH_PATTERN.search(svg)

    if not match:
        return svg

    stroke_width, colour = match.group(1), match.group(2)
    scaled_stroke_width = float(stroke_width) / 0.8

    scaled_parachute_path = match.group(0).replace(
        f'stroke-width="{stroke_width}"',
        f'stroke-width="{scaled_stroke_width:g}"',
    )

    replacement = (
        f'<path d="{_INFANTRY_DIAGONALS}" stroke-width="{stroke_width}" '
        f'stroke="{colour}" fill="none" ></path>'
        f'<g transform="translate(20, 49.5) scale(0.8)">'
        f'{scaled_parachute_path}'
        f'</g>'
    )

    return svg[:match.start()] + replacement + svg[match.end():]


# --- Entity-specific fixup: Amphibious's own oval removed -------------

# amphibious's own icon is a stadium-shaped oval sitting above the wave
# glyph - requested live, 2026-09-02: "i want the oval inside the
# rectangle removed - so the result is only the rectangle and the
# wave". The oval's own path is a fixed signature (a stadium shape
# built from two straight sides and two semicircular caps), confirmed
# against a render - stripped out entirely, leaving the frame and the
# wave untouched.
_AMPHIBIOUS_OVAL_PATTERN = re.compile(
    r'<path d="M125,80 C150,80 150,120 125,120 L75,120 C50,120 50,80 '
    r'75,80 Z" stroke-width="3" stroke="[^"]+" fill="none" ></path>'
)


def remove_amphibious_oval(svg):

    return _AMPHIBIOUS_OVAL_PATTERN.sub("", svg)


# --- Synthetic entity: Air Defence Artillery (Air Defence + Artillery) -
#
# No such combined key exists in APP-6E's own ground_unit vocabulary -
# requested live, 2026-09-02: "use the Air Defence Glyph and add a dot
# in the center (basically Air Defence and Artillery glyphs merged)".
# Confirmed by rendering both real entities directly: Air Defence is
# the frame plus one arc path (`M25,150 C25,110 175,110 175,150`),
# Artillery is the frame plus one filled centre dot (`<circle cx="100"
# cy="100" r="15">`, fill = the icon's own colour) - the merge is Air
# Defence's own SIDC render with that exact circle added on top, same
# "nonnato_" prefix convention the synthetic mine family already uses
# (see that section's own comment) so this can never collide with a
# real key sidc_2525e.py might add later. Resolved to the real "air_
# defense" key at SIDC-build time only (_UNIT_ENTITY_KEY_ALIASES) -
# same alias pattern SIGINT's own Radar uses on the Land Equipment
# side (_EQUIPMENT_ENTITY_KEY_ALIASES) - so the fixup below applies
# only to this synthetic entity, never to a plain Air Defence render.
AIR_DEFENSE_ARTILLERY_ENTITY = "nonnato_air_defense_artillery"

# --- Synthetic entity: Air Force (Army Aviation, right arc opened) ----
#
# No such entity exists in APP-6E's own ground_unit vocabulary either -
# requested live, 2026-09-03: "use the Army Aviation glyph, the figure
# of 8 is open on the right - so +-30 deg at 90deg i.e. 60 to 120 deg -
# keep the arc open, rest of the figure of eight remains". Army
# Aviation's own hollow figure-of-8 (hollow_army_aviation_propeller()
# above) is two curved "wings" meeting at the centre (100,100); the
# RIGHT wing's own outer edge is a single cubic bezier from (130,88)
# down to (130,112), bulging right through roughly (145,100) - a ~180
# degree arc around its own local centre (130,100), radius 12.
#
# Angles read as compass bearings (0 deg = up/north, 90 deg = right/
# east, clockwise) - the convention already used elsewhere in this
# plugin for azimuths (e.g. terrain/hillshade_combination.py's own
# light directions), and the only reading that actually lands "on the
# right" as named: (130,88) is due north of the wing's own local centre
# (130,100), (145,100) [the arc's own rightmost bulge] is due east -
# bearing 90 degrees - and (130,112) is due south, bearing 180 degrees.
# So the requested "60 to 120 degree" gap sits astride due-east,
# centred exactly on the arc's own rightmost point - reads as "open on
# the right", confirmed.
#
# The single 180-degree bezier is split into two 60-degree arcs (0-60,
# 120-180), each rebuilt with the standard cubic-bezier circular-arc
# control-point formula (k = 4/3 * tan(angle/4) * radius) rather than
# guessed, leaving a real gap between them - drawn as two separate
# subpaths (a second `M` mid-path) since this shape is stroke-only
# (fill="none"), so an open subpath reads correctly with no unwanted
# closing segment.
AIR_FORCE_ENTITY = "nonnato_air_force"

INFORMATION_WARFARE_ENTITY = "nonnato_information_warfare"
POSTAL_UNIT_ENTITY = "nonnato_postal_unit"
INTELLIGENCE_ENTITY = "nonnato_intelligence"

SUPPLIES_TRANSPORT_ENTITY = "nonnato_supplies_transport"
ORDNANCE_ENTITY = "nonnato_ordnance"
REMOUNT_VETERINARY_ENTITY = "nonnato_remount_veterinary"

_UNIT_ENTITY_KEY_ALIASES = {
    AIR_DEFENSE_ARTILLERY_ENTITY: "air_defense",
    AIR_FORCE_ENTITY: "aviation_fixed_wing",
    MOTORISED_INFANTRY_ENTITY: "infantry",
    MOUNTAIN_INFANTRY_ENTITY: "infantry",
    RECCE_SUPPORT_WHEELED_ENTITY: "armored_mechanized_tracked",
    SELF_PROPELLED_ARTILLERY_ENTITY: "field_artillery",
    PARACHUTE_FIELD_ARTILLERY_ENTITY: "field_artillery",
    INFORMATION_WARFARE_ENTITY: "military_police",
    POSTAL_UNIT_ENTITY: "military_police",
    INTELLIGENCE_ENTITY: "military_police",
    SUPPLIES_TRANSPORT_ENTITY: "military_police",
    ORDNANCE_ENTITY: "military_police",
    REMOUNT_VETERINARY_ENTITY: "military_police",
}

_ARMY_AVIATION_PROPELLER_SOLID_D = (
    "M100,100 L130,88 c15,0 15,24 0,24 L100,100 70,112 "
    "c-15,0 -15,-24 0,-24 Z"
)

_AIR_FORCE_PROPELLER_PATTERN = re.compile(
    r'<path d="' + re.escape(_ARMY_AVIATION_PROPELLER_SOLID_D)
    + r'" stroke-width="3" stroke="none" fill="([^"]+)"'
)

# Arc 1: (130,88) [bearing 0] to (140.4,94) [bearing 60], control points
# computed from the wing's own local centre (130,100), radius 12.
# Arc 2: (140.4,106) [bearing 120] to (130,112) [bearing 180] - the
# mirror image of arc 1 about the centreline y=100, as the geometry
# itself is.
_AIR_FORCE_PROPELLER_D = (
    "M100,100 L130,88 c4.3,0 8.2,2.3 10.4,6 "
    "M140.4,106 c-2.2,3.7 -6.1,6 -10.4,6 L100,100 70,112 "
    "c-15,0 -15,-24 0,-24 L100,100"
)


def open_air_force_propeller_arc(svg):

    """
    Rebuilds Army Aviation's own filled propeller path directly into
    the hollow, right-arc-open Air Force shape in one step (rather than
    chaining onto hollow_army_aviation_propeller()) - see this
    section's own comment above for the geometry.
    """

    def _replacement(match):

        colour = match.group(1)

        return (
            f'<path d="{_AIR_FORCE_PROPELLER_D}" stroke-width="3" '
            f'stroke="{colour}" fill="none"'
        )

    return _AIR_FORCE_PROPELLER_PATTERN.sub(_replacement, svg)


def add_artillery_center_dot(svg):

    """
    Adds Artillery's own filled centre dot on top of Air Defence's own
    arc glyph - see this section's own comment above. Colour read off
    the glyph's own existing stroke (_injected_text_colour(), same
    technique add_radar_center_mast() already uses for Land Equipment's
    Radar mast), so this stays a plain svg-in/svg-out fixup.
    """

    colour = _injected_text_colour(svg)

    dot = (
        f'<circle cx="100" cy="100" r="15" stroke-width="3" '
        f'stroke="{colour}" fill="{colour}"></circle>'
    )

    return _inject_before_closing_svg(svg, dot)


# Dispatch tables - keyed on the feature's own entity, applied after
# the echelon fixup (which is entity-independent) whenever that entity
# is selected, regardless of affiliation/echelon/status.
# Signal's own jagged line runs from the frame's top-LEFT corner to its
# bottom-RIGHT one (`M25,50 100,110 100,90 175,150`, milsymbol's own
# path). Mirrored horizontally about the frame's own centre line
# 2026-09-06 - "horizontally invert the jagged line - it should touch
# the other two vertices of the rectangle" - so it runs top-right to
# bottom-left instead. The two middle vertices sit on x=100 and are
# their own mirror image, which is why only the endpoints move.
_SIGNAL_JAGGED_LINE_D = "M25,50 100,110 100,90 175,150"

_SIGNAL_JAGGED_LINE_MIRRORED_D = "M175,50 100,110 100,90 25,150"


def mirror_signal_jagged_line(svg):

    """Signal's own jagged line, flipped to the frame's other diagonal - see above."""

    return svg.replace(
        f'd="{_SIGNAL_JAGGED_LINE_D}"',
        f'd="{_SIGNAL_JAGGED_LINE_MIRRORED_D}"',
        1,
    )


# Military Police's own glyph is the plain frame with a bold "MP" in the
# middle (font-size 45, text-anchor middle - milsymbol's own). Three
# more entities reuse it with a different pair of letters, requested
# live 2026-09-06: "Information Warfare, Postal Unit and Intelligence -
# use the Military Police Glyph, replace MP with IW, PO and I
# respectively". Nothing but the letters changes: the text stays
# centred, so a one- or two-letter label needs no repositioning.
_MILITARY_POLICE_LETTERS = "MP"

_LETTERED_MILITARY_POLICE_ENTITIES = {
    INFORMATION_WARFARE_ENTITY: "IW",
    POSTAL_UNIT_ENTITY: "PO",
    INTELLIGENCE_ENTITY: "I",
}


def _relabel_military_police(letters):

    def fixup(svg):

        return svg.replace(
            f">{_MILITARY_POLICE_LETTERS}</text>", f">{letters}</text>", 1
        )

    return fixup


# Three more entities take Military Police's own FRAME but replace its
# lettering with a shape of their own, requested live 2026-09-06:
# "Supplies and Transport unit - standard rectangle, insert a circle in
# the middle and add a X (two diagonals) inside the circle only",
# "Ordnance unit - standard rectangle with the [booby trap] glyph
# inside it" (said as "decoy" first, corrected the same day),
# and "Remount and Veterinary corps unit - standard rectangle with \/ -
# starting at the top corners and meeting at the center of the bottom
# line of the rectangle".
#
# Built on a real entity's render rather than as standalone SVGs (the
# way Administration or Logistics and Static Formation Headquarters
# are) precisely so they keep everything milsymbol gives a framed unit:
# echelon amplifiers, Planned status dashing, and the Headquarters flag
# mast. Military Police is the donor because its own interior is a
# single <text> element - the simplest thing in the vocabulary to
# remove cleanly. Its frame is the same rectangle every Land Unit gets:
# all six non-NATO affiliations map to SIDC "friend"
# (SIDC_AFFILIATION_FOR), so the frame shape never varies.
_MILITARY_POLICE_TEXT_PATTERN = re.compile(
    r"<text\b[^>]*>" + _MILITARY_POLICE_LETTERS + r"</text>"
)

# "insert a circle in the middle and add a X (two diagonals) inside the
# circle only". The radius is not specified - 35 leaves a clear margin
# inside the frame's own 100-unit height while staying big enough for
# the X to read at map size.
_SUPPLIES_CIRCLE_RADIUS = 35


def _supplies_transport_glyph(colour):

    centre = (_UNIT_FRAME_LEFT + _UNIT_FRAME_RIGHT) / 2

    # The diagonals end ON the circle, which is what "inside the circle
    # only" asks for - they must not run out to the frame's corners the
    # way Infantry's own do.
    offset = _SUPPLIES_CIRCLE_RADIUS / (2 ** 0.5)

    low, high = centre - offset, centre + offset
    top, bottom = _UNIT_FRAME_CENTRE_Y - offset, _UNIT_FRAME_CENTRE_Y + offset

    return (
        f'<circle cx="{centre:g}" cy="{_UNIT_FRAME_CENTRE_Y:g}" '
        f'r="{_SUPPLIES_CIRCLE_RADIUS:g}" stroke-width="3" stroke="{colour}" '
        'fill="none"></circle>'
        f'<path d="M{low:g},{top:g} L{high:g},{bottom:g} '
        f'M{high:g},{top:g} L{low:g},{bottom:g}" '
        f'stroke-width="3" stroke="{colour}" fill="none"></path>'
    )


def _ordnance_glyph(colour):

    """
    Mines and Obstacles' own Booby Trap shape, drawn in this layer's
    own affiliation colour.

    A first pass used milsymbol's own Decoy glyph, reading "the decoy
    glyph" literally - corrected live the same day: "its booby trap not
    decoy - and the colour affiliation remains standard as per land
    units and not green". So it shares booby_trap_marks() with the
    mines layer rather than copying it, and takes the colour it is
    given: MINE_GREEN is that layer's own rule, not the shape's.

    Its own extent (x/y 68.1..131.9) already sits inside the frame's
    own 100-unit height with room to spare, so it needs no scaling or
    repositioning.
    """

    return booby_trap_marks(colour)


def _remount_veterinary_glyph(colour):

    """Two lines from the frame's own top corners meeting at the middle of its bottom edge."""

    centre = (_UNIT_FRAME_LEFT + _UNIT_FRAME_RIGHT) / 2

    return (
        f'<path d="M{_UNIT_FRAME_LEFT:g},{_UNIT_FRAME_TOP:g} '
        f'L{centre:g},{_UNIT_FRAME_BOTTOM:g} '
        f'L{_UNIT_FRAME_RIGHT:g},{_UNIT_FRAME_TOP:g}" '
        f'stroke-width="3" stroke="{colour}" fill="none"></path>'
    )


_MILITARY_POLICE_REGLYPHED = {
    SUPPLIES_TRANSPORT_ENTITY: _supplies_transport_glyph,
    ORDNANCE_ENTITY: _ordnance_glyph,
    REMOUNT_VETERINARY_ENTITY: _remount_veterinary_glyph,
}


def _reglyph_military_police(draw):

    """Swaps Military Police's own "MP" for a shape of this entity's own - see above."""

    def fixup(svg):

        colour = _injected_text_colour(svg)

        return _inject_before_closing_svg(
            _MILITARY_POLICE_TEXT_PATTERN.sub("", svg, count=1), draw(colour)
        )

    return fixup


_ENTITY_FIXUPS = {
    "amphibious": remove_amphibious_oval,
    "aviation_fixed_wing": hollow_army_aviation_propeller,
    "parachute_rigger": composite_parachute_rigger,
    AIR_DEFENSE_ARTILLERY_ENTITY: add_artillery_center_dot,
    AIR_FORCE_ENTITY: open_air_force_propeller_arc,
    "signal": mirror_signal_jagged_line,
    **{
        entity: _relabel_military_police(letters)
        for entity, letters in _LETTERED_MILITARY_POLICE_ENTITIES.items()
    },
    **{
        entity: _reglyph_military_police(draw)
        for entity, draw in _MILITARY_POLICE_REGLYPHED.items()
    },
}


# --- Combined Arms indicator ------------------------------------------

# Final sizes per echelon (width x height, milsymbol path-space units),
# each already the larger of that echelon's own measured glyph size and
# the no-echelon floor (37.5 x 33.3) - see the rules record's Combined
# Arms note for how every one of these was derived and confirmed.
# Keyed on the SAME echelon values sidc.py's own ECHELONS/build_sidc()
# use - the rename is display-label-only, same as everywhere else in
# this scheme.
_COMBINED_ARMS_FLOOR = (37.5, 100 / 3)

_COMBINED_ARMS_SIZES = {
    "unspecified": _COMBINED_ARMS_FLOOR,
    "team_crew": (54, 40),
    "squad": (37.5, 34.5),
    "platoon": (89, 34.5),
    "company": (37.5, 42),
    "battalion": (37.5, 42),
    "brigade": (39, 42),
    "division": (74, 42),
    "corps": (109, 42),
    "army": (144, 42),
    "army_group": (179, 42),
}

_FRAME_TOP = 50


def combined_arms_bounds(echelon):

    """(x, y, width, height) for the Combined Arms rectangle - see combined_arms_rect_svg()."""

    width, height = _COMBINED_ARMS_SIZES.get(echelon, _COMBINED_ARMS_FLOOR)

    x = 100 - width / 2
    y = _FRAME_TOP - height

    return x, y, width, height


def combined_arms_rect_svg(echelon, colour):

    """
    A `<rect>` element for the Combined Arms indicator: bottom edge on
    the frame's own top edge (y=50), centred horizontally (x=100),
    same affiliation colour/line weight as the frame itself, no fill -
    confirmed against a render as one cohesive glyph rather than a
    bolt-on. `echelon` not in the table (should not happen - every
    ECHELONS value has an entry) falls back to the no-echelon floor
    rather than raising, so a future echelon addition here fails soft.
    """

    x, y, width, height = combined_arms_bounds(echelon)

    return (
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
        f'stroke-width="4" stroke="{colour}" fill="none"></rect>'
    )


def _inject_before_closing_svg(svg, addition):

    return svg.replace("</svg>", addition + "</svg>", 1)


_VIEWBOX_PATTERN = re.compile(
    r'viewBox="([\d.\-]+) ([\d.\-]+) ([\d.\-]+) ([\d.\-]+)"'
)
_WIDTH_HEIGHT_PATTERN = re.compile(
    r'width="([\d.]+)" height="([\d.]+)"'
)


def _expand_viewbox_for_rect(svg, rect_x, rect_y, rect_width, rect_height):

    """
    Widens `svg`'s own viewBox (and width/height, if it declares them)
    just enough to include a rect at (rect_x, rect_y, rect_width,
    rect_height) - never shrinks it. Needed because the Combined Arms
    rectangle can extend past whatever bounds the base render already
    has: milsymbol widens its own viewBox for an echelon amplifier, but
    not by enough to also fit a WIDE Combined Arms rectangle on top of
    it (Army Group's is 179 wide, wider than milsymbol's own
    army_group-echelon viewBox), and Enemy (Info Unknown)'s hand-built
    SVG has no echelon-awareness in its viewBox at all - confirmed live
    that without this, the rectangle is genuinely drawn but clipped
    clean out of the visible picture, not just visually cramped.

    QGIS sizes an SVG marker by its own declared WIDTH attribute (see
    stabilised_point_size_expression()'s own docstring for the general
    principle), so viewBox alone is not enough when width/height are
    present - both are rescaled together, preserving whatever uniform
    scale factor the original render already used. Enemy (Info
    Unknown)'s own SVG declares neither attribute at all; left absent
    here too; a marker with no width/height falls back to the
    viewBox's own units directly, which is how it already rendered
    correctly before Combined Arms was ever added to it.
    """

    match = _VIEWBOX_PATTERN.search(svg)

    if not match:
        return svg

    vb_x, vb_y, vb_w, vb_h = (float(value) for value in match.groups())

    new_x = min(vb_x, rect_x)
    new_y = min(vb_y, rect_y)
    new_w = max(vb_x + vb_w, rect_x + rect_width) - new_x
    new_h = max(vb_y + vb_h, rect_y + rect_height) - new_y

    if (new_x, new_y, new_w, new_h) == (vb_x, vb_y, vb_w, vb_h):
        return svg

    svg = _VIEWBOX_PATTERN.sub(
        f'viewBox="{new_x:g} {new_y:g} {new_w:g} {new_h:g}"', svg, count=1
    )

    # Scoped to the ROOT <svg> tag, not the whole document. milsymbol's
    # own renders always declare width/height on the root, so an
    # unscoped search happened to hit the right pair for them - but a
    # hand-built SVG in this module declares neither, and the first
    # width="..." height="..." pair in the document is then a <rect>
    # the icon actually draws with. Both Bar Mine and 'B'/'C' Vehicle
    # were being silently deformed that way the moment a designation
    # grew the viewBox (Bar Mine's own bar stretched from 14.7 units
    # tall to 72.5) - a real bug, found 2026-09-05 while building the
    # Vehicle family, invisible until a designation was typed.
    root_end = svg.find(">")

    root_tag = svg[: root_end + 1] if root_end != -1 else svg

    wh_match = _WIDTH_HEIGHT_PATTERN.search(root_tag)

    if wh_match:

        scale = float(wh_match.group(1)) / vb_w

        svg = _WIDTH_HEIGHT_PATTERN.sub(
            f'width="{new_w * scale:g}" height="{new_h * scale:g}"',
            root_tag,
            count=1,
        ) + svg[root_end + 1:]

    return svg


def apply_nonnato_unit_fixups(svg, entity, echelon):

    """
    Every post-render fixup a Land Unit icon might need, applied in
    order: the echelon fixup (entity-independent - Detachment's slash
    is stripped whenever that echelon is selected, on any entity),
    then whichever entity-specific fixup applies. Both are no-ops for
    every icon that doesn't match, so this is safe to call
    unconditionally on every render.
    """

    if echelon == "team_crew":
        svg = strip_detachment_slash(svg)

    fixup = _ENTITY_FIXUPS.get(entity)

    if fixup:
        svg = fixup(svg)

    return svg


def render_nonnato_unit_svg(
    affiliation,
    entity,
    echelon="unspecified",
    status="present",
    designation_left=None,
    designation_right=None,
    combined_arms=False,
    headquarters=False,
):

    """
    The full non-NATO Land Unit render, as one SVG string (not yet
    base64-encoded - see land_unit_layer_nonnato.py's own renderer for
    that step, and for why it isn't done here: the expression function
    needs the plain SVG to also compute the stabilised icon size from,
    same as every other point-symbol layer's own renderer already
    does).

    Enemy (Info Unknown) short-circuits everything else - it has no
    APP-6E entity, so there is no SIDC to build and no milsymbol call
    to make at all.

    `designation_left`/`designation_right` no longer reach milsymbol's
    own uniqueDesignation option at all - see inject_side_designations()
    below (defined alongside Land Equipment's own designation mechanism,
    which this one reuses the measurement primitives of) for the two-
    sided replacement requested live 2026-09-02 ("i want two unique
    designators - unique designator (left) and unique designator
    (right)... the present unique designator can be removed or
    ignored"). Applied before Combined Arms, so both designations align
    with the unit glyph/frame itself rather than with Combined Arms' own
    indicator sitting above it.

    `headquarters` is milsymbol's own flag-mast amplifier, passed
    straight through to build_sidc() - the same Field S the NATO layers
    already expose (see _point_symbol_layer.py's own
    include_headquarters). Added 2026-09-06: "there is a choice for
    Headquarters in the NATO symbology wherein a flag mast is added to
    the glyph - implement the same in non-nato also". It has no effect
    on the four Enemy entities, which never reach a SIDC at all.
    """

    if is_enemy_unknown(entity):

        svg = enemy_info_unknown_svg()
        combined_arms_colour = _ENEMY_INFO_UNKNOWN_COLOUR

    elif entity in (ADMIN_LOGISTICS_ENTITY, STATIC_FORMATION_HQ_ENTITY):

        combined_arms_colour = AFFILIATION_COLOURS.get(
            affiliation, AFFILIATION_COLOURS["friend"]
        )

        svg = (
            admin_logistics_svg(combined_arms_colour)
            if entity == ADMIN_LOGISTICS_ENTITY
            else static_formation_hq_svg(combined_arms_colour)
        )

    else:

        sidc = build_sidc(
            affiliation=SIDC_AFFILIATION_FOR.get(affiliation, "friend"),
            entity=_UNIT_ENTITY_KEY_ALIASES.get(entity, entity),
            symbol_set="ground_unit",
            echelon=echelon,
            status=status,
            headquarters=headquarters,
            edition="2525E",
        )

        colour = AFFILIATION_COLOURS.get(
            affiliation, AFFILIATION_COLOURS["friend"]
        )

        options = {"frame": True, "fill": False, "monoColor": colour}

        svg = apply_nonnato_unit_fixups(
            render_symbol_svg(sidc, options), entity, echelon
        )

        combined_arms_colour = colour

    svg = inject_side_designations(
        svg,
        designation_left,
        designation_right,
        combined_arms_colour,
        centre_y=_UNIT_FRAME_CENTRE_Y,
    )

    # After the designations, so a typed right designation keeps its own
    # anchor and Enemy (Designation Unknown)'s own "?" steps outside it -
    # see inject_enemy_question_mark().
    svg = inject_enemy_question_mark(svg, entity, combined_arms_colour)

    svg = inject_unit_entity_marks(svg, entity, combined_arms_colour)

    if combined_arms:

        svg = _expand_viewbox_for_rect(
            svg, *combined_arms_bounds(echelon)
        )

        svg = _inject_before_closing_svg(
            svg, combined_arms_rect_svg(echelon, combined_arms_colour)
        )

    return scale_svg_stroke_width(svg, DEFAULT_STROKE_SCALE)


# --- Land Equipment (also holds SIGINT, merged in 2026-09-02) ----------
#
# SIGINT used to be its own layer/module - retired once the maintainer
# pointed out it only ever had two entities ("merge sigint glyphs
# (since there are only two) with land equipment"). Jammer and Radar
# keep their own SIDC symbol_set ("sigint_land", not "land_equipment"
# - see _EQUIPMENT_SYMBOL_SET_OVERRIDES) but otherwise render through
# the exact same pipeline as every other Land Equipment entity - same
# six-affiliation colour map, same no-frame/no-fill options, same
# designation handling (see inject_centered_designation_below() below).

# Designation text sits centred, directly below the icon's own current
# viewBox - NOT milsymbol's own uniqueDesignation option at all, which
# this layer stopped using entirely. milsymbol's own placement is a
# FIXED offset baked into each icon's own layout config, independent of
# how far down the icon's own artwork actually reaches - reported live
# 2026-09-02, initially against Jammer/Radar's own especially compact
# glyphs ("in both sigint glyphs - the unique designator is too far
# from the icon", fixed that day by nudging milsymbol's own y="160" to
# y="130"), then again days later against the WHOLE Land Equipment
# layer ("the unique designation is still too far from the glyphs...
# I want the unique designation to be directly under the glyph, with
# text centered") - the first fix only patched the two SIGINT glyphs
# specifically; this one replaces the mechanism outright, for every
# entity on the layer, mines included. **Anchored to the declared
# viewBox's own bottom edge at first, then corrected again the same
# day** ("it is a bit far, can we move it as close to the glyph as
# possible with some gap - this should be dynamic as we move ahead
# with the modifications in future"): a declared viewBox is not a tight
# bounding box - Jammer's own "J" and Radar's own hook stop drawing
# 20-30 units above their own declared viewBox bottom (confirmed live:
# tank/antitank_mine sit within ~2 units of their own declared bottom,
# jammer/sigint_radar within ~20-30), so anchoring uniformly to the
# DECLARED viewBox reintroduced exactly the per-icon unevenness the
# original SIGINT-only y="130" hack existed to paper over, just for a
# different subset of icons. Anchored to the ACTUAL rendered content
# bounds instead (_content_bounds() below, via QSvgRenderer's own
# boundsOnElement()) - genuinely dynamic in the sense asked for: every
# icon, present or future, measures its own real ink, no per-icon
# constant to keep in sync by hand.
# milsymbol's own viewBox width for an unamplified glyph, and so the
# width every length in this module is implicitly calibrated against -
# QGIS scales an SVG marker so its declared viewBox WIDTH equals the
# marker size (confirmed against a real render via land_equipment_
# layer_nonnato._MM_PER_ICON_UNIT). Anything authored in a WIDER
# viewBox has to divide that ratio back out or it draws small: the
# Vehicle family's own stroke width does, and so does the designation
# text below.
_STANDARD_EQUIPMENT_VIEWBOX_WIDTH = 108

_DESIGNATION_FONT_SIZE = 28.0
_DESIGNATION_GAP = 6.0

# Cap height as a fraction of font size - the estimate this module
# measures and positions all of its OWN <text> with. Deliberately a
# round approximation: every label here is a short, all-uppercase
# string, so the cap box IS the visible ink and "centred" means that
# box centred.
#
# Note this is NOT symbol_engine._apply_dominant_baseline()'s own
# ratio, and the difference is intentional. That helper reproduces
# what SVG's `dominant-baseline="middle"` is defined to do - shift by
# half the font's X-HEIGHT (0.2595 em for Arial) - because its job is
# to honour an attribute milsymbol emits and Qt ignores. Here there is
# no attribute to honour, only a request to centre visible uppercase
# ink, which is half the CAP height.
_CAP_HEIGHT_RATIO = 0.7

# How far a stroked path's ink reaches past its own geometry, for the
# shapes this module draws: half the width they are authored at (3),
# times the uniform widening scale_svg_stroke_width() applies to
# everything at the very end. Grow a viewBox by the geometry alone and
# the outline hangs outside it - a real, reported bug (see
# inject_mobility_indicator()), and the reason every injected shape
# here adds this.
_INJECTED_HALF_STROKE = 3 * DEFAULT_STROKE_SCALE / 2


def designation_font_size_in_icon_units(viewbox_width, size_multiplier=1.0):

    """
    `_DESIGNATION_FONT_SIZE`, restated in ONE icon's own units so that
    every icon's designation comes out the SAME apparent size on the
    map - the general form of the compensation the Vehicle family's own
    stroke width already needed.

    QGIS scales an SVG marker so its declared viewBox WIDTH equals the
    marker size, so a length written in icon units draws at
    `length * (marker size * entity multiplier / viewBox width)`. Every
    number in this module was calibrated against milsymbol's own
    108-wide viewBox at multiplier 1, so an icon that departs from
    either has to divide both back out. Two ways that happens today:
    - a hand-built SVG with a wider viewBox (the Vehicle family's 166),
      which shrinks the text;
    - a per-entity size multiplier (Jammer/Radar's 1.8, the Vehicle
      family's 0.8), which scales the whole marker and the text with
      it.

    Bar Mine has BOTH and is the reason this is one formula rather than
    two fixes: its 160-wide viewBox and its own 160/108 multiplier
    cancel exactly, which is why its designation was already correct
    and must stay untouched here.

    Flagged 2026-09-05 while the Vehicle family's strokes were being
    compensated, deliberately deferred then, and settled here.
    """

    return (
        _DESIGNATION_FONT_SIZE
        * (viewbox_width / _STANDARD_EQUIPMENT_VIEWBOX_WIDTH)
        / size_multiplier
    )


def _designation_font_size(text, max_width, base_size=_DESIGNATION_FONT_SIZE):

    """
    `base_size`, or smaller if `text` would otherwise spill past
    `max_width` - same QFontMetricsF technique symbol_engine.py's own
    _fitted_font_size() uses, reimplemented here rather than imported
    because that one measures against a single hardcoded constant
    (built for one specific icon's own fixed-width supply box), not a
    caller-supplied width that varies with every icon's own viewBox.

    `base_size` defaults to the plain constant, but an icon in a
    non-108 viewBox passes the compensated size from
    designation_font_size_in_icon_units() instead - the shrink-to-fit
    then works off THAT, so a long designation still shrinks by the
    same proportion it would anywhere else.
    """

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)

        width = (
            QFontMetricsF(font).horizontalAdvance(text)
            / 1000.0
            * base_size
        )

    except Exception:

        return base_size

    if width <= max_width:
        return base_size

    return base_size * max_width / width


def _designation_text_width(text, font_size):

    """
    Plain rendered width of `text` at `font_size` - the side-designation
    counterpart to _designation_font_size()'s own internal measurement,
    without that function's shrink-to-fit behaviour: side text has no
    fixed-width budget to fit inside (the icon's own viewBox simply
    grows sideways to fit it instead - see inject_side_designations()
    below), so there is nothing to shrink against.
    """

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)

        return (
            QFontMetricsF(font).horizontalAdvance(text)
            / 1000.0
            * font_size
        )

    except Exception:

        return len(text) * font_size * 0.6


_TEXT_ELEMENT_PATTERN = re.compile(
    r'<text\s+x="([-\d.]+)"\s+y="([-\d.]+)"([^>]*)>(.*?)</text>', re.S
)


def _text_element_bounds(x, y, attrs, content):

    """
    An approximate (x, y, width, height) for one `<text>` element -
    see _content_bounds()'s own docstring for why this exists instead
    of trusting QSvgRenderer for text. Width comes from QFontMetricsF
    (the same technique _designation_font_size()/symbol_engine.py's own
    _fitted_font_size() already rely on, confirmed reliable on both Qt
    versions this project tests against); height is a fixed cap-height
    estimate (0.7 of the font size) rather than a precise font-metrics
    conversion - more precision than a single-line, mostly-uppercase
    label needs here.

    **`dominant-baseline` is ignored, because Qt ignores it.** An
    earlier version treated `dominant-baseline="middle"` as centring
    the glyph on `y`, per the SVG spec. Measured directly on this
    project's own Qt (rendering one letter at y=100 with and without
    the attribute, then comparing the painted rows: identical, 71..99
    both times), Qt's SVG module honours it on neither version tested -
    `y` is always the BASELINE. The estimate now says so, which moves
    the measured bottom of any such element up by half a cap height.
    Blast radius checked before changing it: two icons, Improvised
    Explosives Device and Jammer, whose designations move ~10 and ~5
    units closer to the glyph (where they were always meant to sit).
    The five Land Unit letter glyphs that also use the attribute are
    unaffected - their frame is the outer bound, not the letter.
    """

    font_size_match = re.search(r'font-size="([\d.]+)"', attrs)
    font_size = float(font_size_match.group(1)) if font_size_match else 16.0

    bold = 'font-weight="bold"' in attrs

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)
        font.setBold(bold)

        width = (
            QFontMetricsF(font).horizontalAdvance(content)
            / 1000.0
            * font_size
        )

    except Exception:

        width = len(content) * font_size * 0.6

    cap_height = font_size * _CAP_HEIGHT_RATIO

    top = y - cap_height

    if 'text-anchor="middle"' in attrs:
        left = x - width / 2
    elif 'text-anchor="end"' in attrs:
        left = x - width
    else:
        left = x

    return left, top, width, cap_height


def _content_bounds(svg, fallback):

    """
    The TIGHT bounding box of whatever `svg` actually draws, in its own
    viewBox units - not the declared viewBox, which is routinely
    bigger than the real ink (see this section's own comment above for
    live-measured examples).

    Path/circle/rect geometry is measured with Qt's own QSvgRenderer
    (QSvgRenderer.boundsOnElement(), after wrapping the content in an
    identifying <g> purely for the query - milsymbol's own markup has
    no ids) - correctly handles bezier curves and transforms without
    this module reimplementing any of that. `<text>` elements are
    measured separately, with _text_element_bounds() instead: confirmed
    live that QSvgRenderer.boundsOnElement() returns an EMPTY rect for
    ANY text content on QGIS 3's own (older) Qt SVG module, regardless
    of attributes - caught by this project's own standing rule to test
    both QGIS versions, not something the QGIS 4 environment this was
    first built and confirmed against could have shown on its own. Text
    elements are stripped out before the geometry query and their own
    bounds unioned back in afterward, so a text-only icon like Jammer's
    bare "J" still measures correctly on both versions.

    `fallback` (a (x, y, width, height) tuple) is returned unchanged if
    Qt's SVG support is unavailable for any reason, or nothing could be
    measured at all - the same defensive pattern _designation_font_
    size() already uses for QFontMetricsF, so a missing/broken Qt SVG
    stack degrades to the old viewBox-edge behaviour rather than
    raising out of a renderer callback.
    """

    try:

        from qgis.PyQt.QtSvg import QSvgRenderer

        text_matches = list(_TEXT_ELEMENT_PATTERN.finditer(svg))

        non_text_svg = _TEXT_ELEMENT_PATTERN.sub("", svg)

        open_tag_end = non_text_svg.index(">") + 1

        wrapped = (
            non_text_svg[:open_tag_end]
            + '<g id="mctContentBounds">'
            + non_text_svg[open_tag_end:-len("</svg>")]
            + "</g></svg>"
        )

        renderer = QSvgRenderer(wrapped.encode("utf-8"))

        geometry_bounds = renderer.boundsOnElement("mctContentBounds")

        boxes = []

        if not geometry_bounds.isEmpty():

            boxes.append((
                geometry_bounds.x(), geometry_bounds.y(),
                geometry_bounds.width(), geometry_bounds.height(),
            ))

        for match in text_matches:

            x, y = float(match.group(1)), float(match.group(2))

            boxes.append(
                _text_element_bounds(x, y, match.group(3), match.group(4))
            )

        if not boxes:
            return fallback

        min_x = min(box[0] for box in boxes)
        min_y = min(box[1] for box in boxes)
        max_x = max(box[0] + box[2] for box in boxes)
        max_y = max(box[1] + box[3] for box in boxes)

        return (min_x, min_y, max_x - min_x, max_y - min_y)

    except Exception:

        return fallback


def inject_centered_designation_below(
    svg, designation, colour, size_multiplier=1.0
):

    """
    Draws `designation`, centred, directly below `svg`'s own actual
    drawn content (not its declared viewBox - see _content_bounds())
    with a small, fixed gap (_DESIGNATION_GAP) - see this section's own
    comment above for the two-round "too far" story this settles.

    The viewBox is widened downward (never sideways) to fit the text,
    reusing _expand_viewbox_for_rect() - the exact same "grow the
    viewBox and rescale width/height together, never shrink" mechanism
    Combined Arms' own rectangle already relies on, including the same
    accepted trade-off (the marker's own geometric centre shifts down
    slightly, since the growth is asymmetric). The text's own font size
    shrinks to fit the icon's own width rather than widening the
    viewBox sideways, mirroring symbol_engine.py's own supply-box
    convention (_fitted_font_size()) - a long designation gets smaller,
    not an ever-wider icon.

    `size_multiplier` is the icon's own per-entity marker multiplier
    (nonnato_entity_size_multiplier()). Together with the icon's own
    viewBox width it decides the font size in icon units, so that the
    text draws the same size on the map whatever viewBox the icon was
    authored in and whatever multiplier scales it - see
    designation_font_size_in_icon_units().
    """

    if not designation:
        return svg

    match = _VIEWBOX_PATTERN.search(svg)

    if not match:
        return svg

    vb_x, vb_y, vb_w, vb_h = (float(value) for value in match.groups())

    content_x, content_y, content_w, content_h = _content_bounds(
        svg, fallback=(vb_x, vb_y, vb_w, vb_h)
    )

    content_bottom = content_y + content_h

    text = str(designation).upper()

    base_font_size = designation_font_size_in_icon_units(vb_w, size_multiplier)

    font_size = _designation_font_size(text, vb_w * 0.9, base_font_size)

    svg = _expand_viewbox_for_rect(
        svg,
        vb_x,
        vb_y,
        vb_w,
        (content_bottom + _DESIGNATION_GAP + font_size * 1.2) - vb_y,
    )

    center_x = content_x + content_w / 2
    baseline_y = content_bottom + _DESIGNATION_GAP + font_size

    text_element = (
        f'<text x="{center_x:g}" y="{baseline_y:g}" text-anchor="middle" '
        f'font-size="{font_size:g}" font-family="Arial" stroke="none" '
        f'fill="{colour}">{_escape_text(text)}</text>'
    )

    return _inject_before_closing_svg(svg, text_element)


# Land Unit's own side-designation font size, deliberately NOT the same
# constant as _DESIGNATION_FONT_SIZE above (Land Equipment's own,
# centred-below designation) - reported live, 2026-09-02: "the font
# size is too small to read, the position is ok, increase the size to
# 8pt or more". Bumped from 28 (the shared constant's own value) to 45
# - not an arbitrary guess: 45 is milsymbol's own established font size
# for legible in-icon text at this exact same coordinate scale (see
# symbol_engine.py's own sonobuoy-family comment, where milsymbol
# itself sets a letter glyph at font-size 45 inside an 80-unit circle).
# Kept as its own constant, not a shared one, so a future Land
# Equipment-only font tweak can't silently move Land Unit's side text
# too, or vice versa.
_SIDE_DESIGNATION_FONT_SIZE = 45.0


def inject_side_designations(
    svg, left_text, right_text, colour, centre_y=None
):

    """
    Land Unit's own two-sided replacement for milsymbol's single, side-
    anchored uniqueDesignation slot - requested live, 2026-09-02: "i
    want two unique designators - unique designator (left) and unique
    designator (right)... both left and right designators should be
    vertically middle aligned to the left or right of the glyph, the
    present unique designator can be removed or ignored". Reuses this
    section's own _content_bounds()/_DESIGNATION_GAP - same "measure
    the icon's own real ink, not its declared viewBox" reasoning as
    inject_centered_designation_below() above - but grows the viewBox
    SIDEWAYS instead of downward, one side at a time, and centres each
    text VERTICALLY on the content's own midpoint instead of centring
    one text horizontally below it. Font size is its own constant,
    _SIDE_DESIGNATION_FONT_SIZE (see above), not the shared
    _DESIGNATION_FONT_SIZE Land Equipment's own mechanism uses.

    Either argument may be empty/None on its own - only the side(s)
    actually supplied get a `<text>` element and widen the viewBox.

    `centre_y` overrides the vertical centre. Land Unit passes its own
    frame's centre (_UNIT_FRAME_CENTRE_Y), because the measured ink is
    NOT what these should centre on - reported live 2026-09-06 against
    the Headquarters flag mast ("even in normal headquarters - the
    unique designations should be center of the rectangle and not the
    entire glyph"). The mast hangs 100 units below the frame, which
    dragged the measured centre from 100 down to 150. Measuring the
    same way showed the identical drift had been there all along for
    every echelon above "unspecified" too - a battalion's own amplifier
    sits above the frame and pulled the centre UP to 82.6 - so this
    fixes more than was reported. Without it the text is centred on the
    icon's bounding box; with it, on the frame a reader actually sees.

    **The vertical centring is computed, not delegated to
    `dominant-baseline="middle"`** - fixed 2026-09-05, during a
    housekeeping sweep. Qt's SVG module ignores that attribute outright
    (measured: one letter at y=100 renders pixel-identically with and
    without it), so asking for it put each label's BASELINE on the
    glyph's centre line rather than its middle. Measured on a plain
    Infantry frame - frame y 50..150, centre 100, font size 45 - the
    text painted 67.6..100, a visual centre of 83.8: **16.2 units
    high**, about a third of the frame's half-height, against an
    explicit "vertically middle aligned" request.

    The plugin already handles this for milsymbol's own labels
    (symbol_engine._apply_dominant_baseline(), written after letters
    collided with centre dots on Appendix H's Reference Points) - but
    that runs INSIDE render_symbol_svg(), and this text is injected
    afterwards, so it never passed through. The baseline is placed at
    `centre + cap height / 2` instead, which puts the cap box's own
    middle exactly on the content's midpoint and makes this agree with
    _text_element_bounds()'s own measurement of the same element.
    """

    left_text = str(left_text).upper().strip() if left_text else ""
    right_text = str(right_text).upper().strip() if right_text else ""

    if not left_text and not right_text:
        return svg

    match = _VIEWBOX_PATTERN.search(svg)

    if not match:
        return svg

    vb_x, vb_y, vb_w, vb_h = (float(value) for value in match.groups())

    content_x, content_y, content_w, content_h = _content_bounds(
        svg, fallback=(vb_x, vb_y, vb_w, vb_h)
    )

    center_y = (
        content_y + content_h / 2 if centre_y is None else centre_y
    )
    font_size = _SIDE_DESIGNATION_FONT_SIZE
    half_height = font_size * 1.2 / 2

    # See this function's own docstring: the cap box is centred on
    # center_y by placing the baseline half a cap height below it.
    baseline_y = center_y + font_size * _CAP_HEIGHT_RATIO / 2

    elements = []

    if left_text:

        width = _designation_text_width(left_text, font_size)
        text_x = content_x - _DESIGNATION_GAP

        svg = _expand_viewbox_for_rect(
            svg,
            text_x - width,
            center_y - half_height,
            width,
            half_height * 2,
        )

        elements.append(
            f'<text x="{text_x:g}" y="{baseline_y:g}" text-anchor="end" '
            f'font-size="{font_size:g}" '
            f'font-family="Arial" stroke="none" fill="{colour}">'
            f'{_escape_text(left_text)}</text>'
        )

    if right_text:

        width = _designation_text_width(right_text, font_size)
        text_x = content_x + content_w + _DESIGNATION_GAP

        svg = _expand_viewbox_for_rect(
            svg,
            text_x,
            center_y - half_height,
            width,
            half_height * 2,
        )

        elements.append(
            f'<text x="{text_x:g}" y="{baseline_y:g}" text-anchor="start" '
            f'font-size="{font_size:g}" '
            f'font-family="Arial" stroke="none" fill="{colour}">'
            f'{_escape_text(right_text)}</text>'
        )

    for element in elements:
        svg = _inject_before_closing_svg(svg, element)

    return svg


# Jammer is a real APP-6E entity, but under symbol_set "sigint_land",
# not "land_equipment". Radar needs the same treatment - EXCEPT Land
# Equipment already had its OWN, genuinely different, real "radar"
# entity too (a physical radar system, symbol_set "land_equipment" -
# one of the originally reviewed 26 base entities, confirmed against
# the maintainer's own check sheet), so the two could not share one
# stored entity key without a collision. SIGINT's own Radar is stored
# as SIGINT_RADAR_ENTITY instead - still resolved to the real APP-6E
# key "radar" at SIDC-build time (see _EQUIPMENT_ENTITY_KEY_ALIASES),
# just under "sigint_land". **Land Equipment's own separate "radar"
# entry was removed from the layer's own ENTITY_LABELS 2026-09-02**, at
# the maintainer's own request, once the two read as visually the same
# thing in practice ("remove radar and keep only radar (sigint) since
# both are same; rename radar (sigint) as radar only") - SIGINT_RADAR_
# ENTITY's own label is now plain "Radar". The alias/symbol_set-
# override mechanism below stays exactly as it was regardless - the
# real land_equipment "radar" entity still exists in APP-6E's own
# vocabulary and build_sidc() can still resolve it directly if ever
# needed again; it is only gone from this ONE layer's own dropdown.
SIGINT_RADAR_ENTITY = "sigint_radar"

BRIDGE_LAYER_TANK_ENTITY = "nonnato_bridge_layer_tank"
ARMOURED_RECCE_VEHICLE_ENTITY = "nonnato_armoured_recce_vehicle"
APV_WHEELED_ENTITY = "nonnato_apv_wheeled"

# The Vehicle family that replaced APP-6E's own real "vehicle" entity
# on this layer, 2026-09-05 - fully synthetic, no SIDC and so no
# _EQUIPMENT_ENTITY_KEY_ALIASES entry. See _SYNTHETIC_VEHICLE_SVG.
B_VEHICLE_ENTITY = "nonnato_b_vehicle"
C_VEHICLE_ENTITY = "nonnato_c_vehicle"
LIGHT_RECCE_VEHICLE_ENTITY = "nonnato_light_recce_vehicle"

_EQUIPMENT_ENTITY_KEY_ALIASES = {
    SIGINT_RADAR_ENTITY: "radar",
    BRIDGE_LAYER_TANK_ENTITY: "armored_protected_vehicle",
    ARMOURED_RECCE_VEHICLE_ENTITY: "armored_protected_vehicle",
    APV_WHEELED_ENTITY: "armored_protected_vehicle",
}

# This is the SAME small-number-of-entities-need-a-different-
# symbol_set case _point_symbol_layer.py's own entity_symbol_set_
# overrides mechanism exists for on the NATO side, just reimplemented
# here directly since this module has no equivalent shared helper.
_EQUIPMENT_SYMBOL_SET_OVERRIDES = {
    "jammer": "sigint_land",
    SIGINT_RADAR_ENTITY: "sigint_land",
}


def add_radar_center_mast(svg):

    """
    Adds a short vertical stroke from the centre of the radar dish's
    own arc, extending downward - requested live, 2026-09-02: "add a
    small vertical line from the center of the arc of the radar,
    length about 1/2 the current height of the radar glyph".

    milsymbol's own Radar (sigint_land) glyph is `M 115,90 -15,15
    0,-15 -15,15 M 80,85 c 0,25 15,35 35,35` - two diagonal "signal"
    strokes above a single cubic-bezier arc (the dish itself, from
    (80,85) to (115,120) via control points (80,110)/(95,120)). "Centre
    of the arc" is read as the curve's own midpoint (t=0.5), computed
    directly from those four bezier points rather than eyeballed:
    (90, 112) - confirmed against a render. The glyph's own drawn
    extent is roughly 35 units tall (y from 85 to 120); half of that
    (~17.5 units) set the mast's own initial length, drawn straight
    down from the arc's midpoint - then lengthened another 20% the same
    day ("increase the mast length by 20%"), to 21 units (129.5 ->
    133).

    Colour is read off the glyph's own existing stroke (same technique
    symbol_engine._injected_text_colour() already uses) rather than
    threaded through as a parameter, so this stays a plain svg-in/svg-
    out fixup matching every other entry in _EQUIPMENT_ENTITY_FIXUPS.
    """

    colour = _injected_text_colour(svg)

    mast = (
        f'<path d="M90,112 L90,133" stroke-width="3" '
        f'stroke="{colour}" fill="none"></path>'
    )

    return _inject_before_closing_svg(svg, mast)


# --- Entity-specific fixup: Missile Launcher family's dome gap --------
#
# All three tiered "missile launcher" families (Air Defence Missile
# Launcher, Antitank Missile Launcher, Missile Launcher) share the same
# dome-shaped cap on their real milsymbol glyph - a single connected
# "inverted U" (two vertical side legs plus the curved dome bridging
# their tops, all one continuous stroke - corrected live, 2026-09-03,
# after a first draft wrongly split the dome away from its own legs:
# "no you misunderstood, the side lines and dome are one entity like an
# inverted U"). The vertical centre line running up the middle pokes
# through this U and touches the dome's own peak exactly, with no gap
# at all - requested live: "adjust the length of the dome on top of the
# glyph so that it does not touch anything, it should have a gap with
# the other lines on top, sides and bottom" plus "reduce the length of
# the domes sides to match that of the anti tank missile launcher"
# (Antitank Missile Launcher's own U-legs are already the SHORTER of
# the three - 45 units vs Air Defence/plain Missile Launcher's own 65;
# confirmed as the right call: "length adjustment is fine").
#
# Applied identically across all three families' Light/Medium/Heavy
# tiers - the tier-line <path> milsymbol appends is a separate element,
# untouched by this fixup, and the BODY path is identical across all
# three tiers within a family (confirmed against a render), so one
# fixup per family covers its own three entity keys.
#
# The fix, with the U itself left fully intact/connected: (1) the
# centre line's own top reach is trimmed short of the dome's peak, by
# _MISSILE_DOME_GAP - doubled live from an initial 5 to 10 ("increase
# the gap between the line and top of dome by 100%") - opening the one
# real touch point this glyph had; (2) Air Defence Missile Launcher's
# and plain Missile Launcher's own U-legs are shortened from 65 to 45
# units (their TOP end, where the dome sits, stays put; only the bottom
# end moves up) to match Antitank's own length, which as a side effect
# also opens a gap versus the base shape below - the same proportion
# Antitank's own U already had before this fix (confirmed live: its own
# legs already stopped 20 units short of its chevron base's own outer
# corners).
_MISSILE_DOME_GAP = 10

# Half the dome-to-centre-line gap - reported live, 2026-09-03, right
# after the dome fix above: "everything is fine except that the dome
# legs are touching the horizontal lines, so introduce a small gap,
# 50% of that between dome top and vertical line, on both sides". "The
# horizontal lines" are the shared Light/Medium/Heavy tier-line overlay
# every tiered weapon family gets (identical x=85..115 span regardless
# of family - the same lines Machine Gun's own tiers use, for example)
# - unrelated to this family's own body, but its fixed x-span happens
# to land exactly on the missile launcher dome's own leg x-coordinates
# (85/115), so the two touch. Inset ON BOTH SIDES, not just shortened
# from one end, so the line stays centred.
_MISSILE_TIER_LINE_GAP = _MISSILE_DOME_GAP / 2


def _inset_missile_tier_line(svg):

    """
    Shrinks the tier-line overlay inward by _MISSILE_TIER_LINE_GAP on
    each side so it clears the missile launcher dome's own legs - see
    this section's own comment above. Only ever called from this
    family's own fixups below (never registered generically), so no
    other tiered weapon family's identical-looking tier line is
    affected.
    """

    return (
        svg
        .replace('d="m 85,100 30,0"', 'd="m 90,100 20,0"')
        .replace(
            'd="m 85,105 30,0 m -30,-10 30,0"',
            'd="m 90,105 20,0 m -20,-10 20,0"',
        )
    )


def separate_antitank_missile_launcher_dome(svg):

    """Antitank Missile Launcher - see this section's own comment above."""

    old_d = (
        "m 85,140 15,-15 15,15 M 85,120 85,75 "
        "c 0,-20 30,-20 30,0 l 0,45 m -15,5 0,-65"
    )
    new_d = (
        "m 85,140 15,-15 15,15 M 85,120 85,75 "
        f"c 0,-20 30,-20 30,0 l 0,45 m -15,5 0,{-(65 - _MISSILE_DOME_GAP):g}"
    )

    return _inset_missile_tier_line(svg.replace(f'd="{old_d}"', f'd="{new_d}"'))


def separate_air_defense_missile_launcher_dome(svg):

    """Air Defence Missile Launcher - see this section's own comment above."""

    old_d = (
        "m 85,140 30,0 c 0,-20 -30,-20 -30,0 z "
        "m 15,-15 0,-65 m -15,80 0,-65 c 0,-20 30,-20 30,0 l 0,65"
    )
    new_d = (
        "m 85,140 30,0 c 0,-20 -30,-20 -30,0 z "
        f"m 15,-15 0,{-(65 - _MISSILE_DOME_GAP):g} "
        "M 85,120 85,75 c 0,-20 30,-20 30,0 l 0,45"
    )

    return _inset_missile_tier_line(svg.replace(f'd="{old_d}"', f'd="{new_d}"'))


def separate_missile_launcher_dome(svg):

    """Missile Launcher (plain) - see this section's own comment above."""

    old_d = "m 100,140 0,-80 m -15,80 0,-65 c 0,-20 30,-20 30,0 l 0,65"
    new_d = (
        f"m 100,140 0,{-(80 - _MISSILE_DOME_GAP):g} "
        "M 85,120 85,75 c 0,-20 30,-20 30,0 l 0,45"
    )

    return _inset_missile_tier_line(svg.replace(f'd="{old_d}"', f'd="{new_d}"'))


# --- Synthetic entities built from Armoured Protected Vehicle's own
# "oval" ------------------------------------------------------------
#
# Requested live, 2026-09-03, three in one batch, all starting from the
# same real entity's glyph: Bridge Layer Tank ("< on the top left,
# slightly inward - say 1/3rd inside"), Armoured Recce Vehicle ("/ at
# the same position" as Bridge Layer Tank's own mark), APV Wheeled
# (three circles below the oval). `armored_protected_vehicle`'s own
# real glyph is NOT a true ellipse - confirmed by rendering it directly
# - it is a stadium/discorectangle: straight top and bottom edges from
# x=75 to x=125 (`M125,80 C150,80 150,120 125,120 L75,120 C50,120
# 50,80 75,80 Z`), semicircular caps left/right centred at (75,100)/
# (125,100), radius 20. Overall bounding box x 50..150 (semi-major axis
# 50), y 80..120 (semi-minor axis 20) - the "semi-minor axis" APV
# Wheeled's own radius spec refers to.
#
# Corrected live, 2026-09-03, after a real smoke test: "shift the < to
# the top of the oval not inside it, and increase the < size by
# double" / "[Armoured Recce Vehicle] same - shift the / to the top of
# the oval, increase size by 50%" - then corrected again the same day:
# "for the other two the bottom of < or / should touch the top of the
# oval". Both marks anchor horizontally at the oval's own top-left
# corner (x=75) and now sit entirely ABOVE the oval's own straight top
# edge (y=80), with their own BOTTOM-most point touching that edge
# exactly, rather than straddling it. Each keeps its own arm length:
# Bridge Layer Tank's own "<" doubled (10 -> 20 units), Armoured Recce
# Vehicle's own "/" up 50% (10 -> 15 units).
_APV_MARK_X = 75
_APV_MARK_Y = 80

_BRIDGE_LAYER_TANK_ARM = 14.1  # 20 units at 45 degrees (20 * cos(45))
_ARMOURED_RECCE_VEHICLE_ARM = 10.6  # 15 units at 45 degrees (15 * cos(45))


def bridge_layer_tank_mark(svg):

    """
    A small "<" chevron above the oval's own top-left corner, its own
    lower arm-tip touching the oval's own top edge exactly - see this
    section's own comment above. Colour read off the glyph's own
    existing stroke (_injected_text_colour()), same technique every
    other fixup in this module uses.
    """

    colour = _injected_text_colour(svg)
    arm = _BRIDGE_LAYER_TANK_ARM

    vertex_y = _APV_MARK_Y - arm

    mark = (
        f'<path d="M{_APV_MARK_X + arm:g},{vertex_y - arm:g} '
        f'L{_APV_MARK_X:g},{vertex_y:g} '
        f'L{_APV_MARK_X + arm:g},{_APV_MARK_Y:g}" '
        f'stroke-width="3" stroke="{colour}" fill="none"></path>'
    )

    return _inject_before_closing_svg(svg, mark)


def armoured_recce_vehicle_mark(svg):

    """
    A small "/" above the oval's own top-left corner, its own lower end
    touching the oval's own top edge exactly - see this section's own
    comment above - with its own, separately-sized arm.
    """

    colour = _injected_text_colour(svg)
    arm = _ARMOURED_RECCE_VEHICLE_ARM

    mark = (
        f'<path d="M{_APV_MARK_X:g},{_APV_MARK_Y:g} '
        f'L{_APV_MARK_X + arm:g},{_APV_MARK_Y - 2 * arm:g}" '
        f'stroke-width="3" stroke="{colour}" fill="none"></path>'
    )

    return _inject_before_closing_svg(svg, mark)


# Armoured Protection Vehicle (Wheeled)'s own three wheels - "add three
# circles below the oval, slightly inside the edges, touching the oval,
# radii size can be 1/3 of semi-minor axis". Radius is a third of the
# oval's own semi-minor axis (20); the centres sit one radius below its
# straight bottom edge (y=120) so each wheel's own top touches it, inset
# one radius from its straight left/right edges (x=75/125), with the
# middle wheel centring the group.
#
# **Simplified back to plain injection 2026-09-06**, at the maintainer's
# own request. These were three separate QGIS simple-marker symbol
# layers for three days, on the strength of a conclusion that QGIS clips
# an SVG marker to milsymbol's own declared draw area so circles below
# the hull could never show. That conclusion was WRONG - disproved by
# injecting exactly these circles into exactly this glyph and rendering
# the marker through a real map render at 4/6/8/9.6/12/20/40 mm on both
# QGIS versions (drawn in full every time), and confirmed independently
# by the maintainer. The symbol-layer version also needed two pieces of
# machinery that exist ONLY to compensate for the wheels not being in
# the SVG - a per-feature rendered-height expression function, and a
# min_content_bottom floor on both the designation and the mobility
# mark - and all of it is gone with this.
_APV_WHEEL_RADIUS = 20 / 3

_APV_WHEEL_CENTRE_Y = 120 + _APV_WHEEL_RADIUS

_APV_WHEEL_CENTRE_XS = (
    75 + _APV_WHEEL_RADIUS,
    100,
    125 - _APV_WHEEL_RADIUS,
)


def apv_wheeled_marks(svg):

    """
    Three hollow wheels below the oval's own bottom edge - see this
    section's own comment. Colour is read off the glyph's own existing
    stroke, the same way every other fixup in this module does it.
    """

    colour = _injected_text_colour(svg)

    wheels = "".join(
        f'<circle cx="{centre_x:g}" cy="{_APV_WHEEL_CENTRE_Y:g}" '
        f'r="{_APV_WHEEL_RADIUS:g}" stroke-width="3" stroke="{colour}" '
        'fill="none"></circle>'
        for centre_x in _APV_WHEEL_CENTRE_XS
    )

    match = _VIEWBOX_PATTERN.search(svg)

    if match:

        vb_x, vb_y, vb_w, _ = (float(value) for value in match.groups())

        svg = _expand_viewbox_for_rect(
            svg,
            vb_x,
            vb_y,
            vb_w,
            (_APV_WHEEL_CENTRE_Y + _APV_WHEEL_RADIUS + _INJECTED_HALF_STROKE)
            - vb_y,
        )

    return _inject_before_closing_svg(svg, wheels)


# --- The Vehicle family: 'B' Vehicle, 'C' Vehicle, Light Recce Vehicle
# ---------------------------------------------------------------------
#
# Requested live, 2026-09-05: "remove the existing vehicle glyph, we
# will replace with 'B' Vehicle and 'C' Vehicle / draw a rectangle,
# similar dimensions as land unit, draw two circles - similar to what
# we did for the APV wheeled with the center wheel removed, insert
# letter 'B' in the center of the rectangle / Similarly - same
# construction for 'C' Vehicle except that 'B' is replaced with 'C' /
# Finally - Light Recce Vehicle - start with vehicle 'B', remove the
# alphabet B and put a "/" on top of the rectangle of same dimensions
# as the Armoured Recce Vehicle".
#
# APP-6E's own real "vehicle" entity (a stadium hull over a ground line
# with two small wheels, confirmed by rendering it) is dropped from
# this layer entirely - these three replace it. They are fully
# synthetic: unlike Bridge Layer Tank/Armoured Recce Vehicle above,
# which decorate a real milsymbol glyph, nothing here starts from a
# milsymbol render at all, so they are built the same way the synthetic
# mine family is (a complete SVG authored here, routed through
# _SYNTHETIC_VEHICLE_SVG below) rather than as an
# _EQUIPMENT_ENTITY_FIXUPS entry.
#
#
# "Similar dimensions as land unit" is read literally: the same
# rectangle every Land Unit icon's own frame uses (150 wide x 100 tall,
# x 25..175, y 50..150 - see enemy_info_unknown_svg(), which states the
# same measurement). The wheels follow APV Wheeled's own rule exactly,
# minus its middle wheel: radius = 1/3 of the shape's own semi-minor
# axis (here half the rectangle's height, 50), centred one radius below
# the bottom edge so each wheel's own top touches it, and inset one
# radius from the left/right edges.
_VEHICLE_RECT_X = 25
_VEHICLE_RECT_Y = 50
_VEHICLE_RECT_WIDTH = 150
_VEHICLE_RECT_HEIGHT = 100

_VEHICLE_RECT_RIGHT = _VEHICLE_RECT_X + _VEHICLE_RECT_WIDTH
_VEHICLE_RECT_BOTTOM = _VEHICLE_RECT_Y + _VEHICLE_RECT_HEIGHT

_VEHICLE_WHEEL_RADIUS = _VEHICLE_RECT_HEIGHT / 2 / 3

_VEHICLE_WHEEL_CENTRE_Y = _VEHICLE_RECT_BOTTOM + _VEHICLE_WHEEL_RADIUS

_VEHICLE_WHEEL_CENTRE_XS = (
    _VEHICLE_RECT_X + _VEHICLE_WHEEL_RADIUS,
    _VEHICLE_RECT_RIGHT - _VEHICLE_WHEEL_RADIUS,
)

# milsymbol's own established letter-in-a-shape proportion, restated
# for this rectangle: it sets a letter glyph at font-size 45 inside an
# 80-unit-tall shape (the same measurement _SIDE_DESIGNATION_FONT_SIZE
# is derived from), so a 100-unit-tall rectangle takes 56.25.
_VEHICLE_LETTER_FONT_SIZE = 45.0 / 80.0 * _VEHICLE_RECT_HEIGHT

# Qt's own SVG engine does not honour dominant-baseline on either
# version this project tests against - confirmed against a render, the
# letter sat a half cap-height high - so the baseline is computed here
# instead, using the same 0.7-of-font-size cap-height estimate
# _text_element_bounds() already works to.
_VEHICLE_LETTER_BASELINE_Y = (
    _VEHICLE_RECT_Y
    + _VEHICLE_RECT_HEIGHT / 2
    + _VEHICLE_LETTER_FONT_SIZE * _CAP_HEIGHT_RATIO / 2
)

# Light Recce Vehicle's own "/" starts as Armoured Recce Vehicle's own
# mark ("of same dimensions as the Armoured Recce Vehicle"), re-anchored
# to the rectangle's own top-left corner instead of the oval's, with its
# own lower end touching the top edge exactly - the same way that mark
# meets the oval.
#
# Corrected live the same day, once the first render showed the mark
# reading as small against a rectangle half again wider than the oval it
# was sized for: "increase the mast height of the light recce vehicle by
# 125%". Read the way every other "increase by N%" on this branch has
# been (a 100% increase doubled the missile dome gap), so 2.25x - and
# applied to the arm, scaling the whole mark uniformly rather than
# stretching it vertically, so it stays the same "/" at the same angle.
_LIGHT_RECCE_VEHICLE_MAST_GROWTH = 2.25

_LIGHT_RECCE_VEHICLE_ARM = (
    _ARMOURED_RECCE_VEHICLE_ARM * _LIGHT_RECCE_VEHICLE_MAST_GROWTH
)

# Enough to clear the widened stroke below (roughly 7.5 units after
# DEFAULT_STROKE_SCALE) wherever it is centred on the ink's own outer
# edge - including Light Recce Vehicle's own diagonal mast, whose line
# cap reaches further sideways than any straight edge does. A 4-unit
# padding, chosen before the stroke was widened, left the mast's own
# cap hanging outside the viewBox - caught by this family's own
# viewBox-contains-the-ink test, not by eye.
_VEHICLE_VIEWBOX_PADDING = 8

_VEHICLE_VIEWBOX_WIDTH = _VEHICLE_RECT_WIDTH + 2 * _VEHICLE_VIEWBOX_PADDING

# Requested live, 2026-09-05, after a smoke test of the first render:
# "reduce the size of all three by 20% - too big now". The Vehicle
# family fills far more of its own viewBox than a milsymbol glyph does
# (a 150-unit rectangle in 158, against roughly 100 in 108) and is
# nearly twice as tall on top of that, so it reads oversized beside its
# neighbours at the same marker size. Applied through Land Equipment's
# own existing per-entity multiplier mechanism (which is why this is
# exported rather than private), the same one Jammer/Radar use.
VEHICLE_SIZE_MULTIPLIER = 0.8

# ...and, from the same message: "increase the line width slightly to
# match with that of APV probably". A stroke's own APPARENT thickness
# is its width in icon units times (marker size / viewBox width), so a
# plain "3" - correct for every 108-wide milsymbol glyph - draws this
# 166-wide icon's lines at 108/166 of everyone else's, thinner again by
# the 20% reduction above. Both are divided back out here so the family
# matches Armoured Protected Vehicle's own line weight exactly on the
# map, which is the comparison the request named.
_VEHICLE_STROKE_WIDTH = (
    3
    * (_VEHICLE_VIEWBOX_WIDTH / _STANDARD_EQUIPMENT_VIEWBOX_WIDTH)
    / VEHICLE_SIZE_MULTIPLIER
)


def _vehicle_body(colour):

    """The rectangle plus its two wheels - shared by all three entities."""

    wheels = "".join(
        f'<circle cx="{centre_x:g}" cy="{_VEHICLE_WHEEL_CENTRE_Y:g}" '
        f'r="{_VEHICLE_WHEEL_RADIUS:g}" stroke-width="{_VEHICLE_STROKE_WIDTH:g}" '
        f'stroke="{colour}" fill="none"></circle>'
        for centre_x in _VEHICLE_WHEEL_CENTRE_XS
    )

    return (
        f'<rect x="{_VEHICLE_RECT_X:g}" y="{_VEHICLE_RECT_Y:g}" '
        f'width="{_VEHICLE_RECT_WIDTH:g}" height="{_VEHICLE_RECT_HEIGHT:g}" '
        f'stroke-width="{_VEHICLE_STROKE_WIDTH:g}" stroke="{colour}" '
        'fill="none"></rect>'
        + wheels
    )


def _vehicle_svg(colour, body, content_top=_VEHICLE_RECT_Y):

    """
    Wraps a vehicle body in its own viewBox, padded evenly around the
    real ink. `content_top` only ever differs for Light Recce Vehicle,
    whose "/" reaches above the rectangle.
    """

    top = content_top - _VEHICLE_VIEWBOX_PADDING
    bottom = (
        _VEHICLE_WHEEL_CENTRE_Y
        + _VEHICLE_WHEEL_RADIUS
        + _VEHICLE_VIEWBOX_PADDING
    )

    left = _VEHICLE_RECT_X - _VEHICLE_VIEWBOX_PADDING

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        f'baseProfile="tiny" viewBox="{left:g} {top:g} '
        f'{_VEHICLE_VIEWBOX_WIDTH:g} {bottom - top:g}">' + body + '</svg>'
    )


def _lettered_vehicle_svg(colour, letter):

    centre_x = _VEHICLE_RECT_X + _VEHICLE_RECT_WIDTH / 2

    glyph = (
        f'<text x="{centre_x:g}" y="{_VEHICLE_LETTER_BASELINE_Y:g}" '
        f'text-anchor="middle" font-size="{_VEHICLE_LETTER_FONT_SIZE:g}" '
        f'font-family="Arial" stroke="none" fill="{colour}">{letter}</text>'
    )

    return _vehicle_svg(colour, _vehicle_body(colour) + glyph)


def b_vehicle_svg(colour):

    """No APP-6E equivalent - the Vehicle family's rectangle-on-two-wheels with a centred "B"."""

    return _lettered_vehicle_svg(colour, "B")


def c_vehicle_svg(colour):

    """No APP-6E equivalent - identical to 'B' Vehicle with a "C" instead."""

    return _lettered_vehicle_svg(colour, "C")


def light_recce_vehicle_svg(colour):

    """No APP-6E equivalent - the same body with no letter, carrying Armoured Recce Vehicle's own "/" above its top-left corner."""

    arm = _LIGHT_RECCE_VEHICLE_ARM

    mark_top = _VEHICLE_RECT_Y - 2 * arm

    mark = (
        f'<path d="M{_VEHICLE_RECT_X:g},{_VEHICLE_RECT_Y:g} '
        f'L{_VEHICLE_RECT_X + arm:g},{mark_top:g}" '
        f'stroke-width="{_VEHICLE_STROKE_WIDTH:g}" stroke="{colour}" '
        'fill="none"></path>'
    )

    return _vehicle_svg(
        colour, _vehicle_body(colour) + mark, content_top=mark_top
    )


_SYNTHETIC_VEHICLE_SVG = {
    B_VEHICLE_ENTITY: b_vehicle_svg,
    C_VEHICLE_ENTITY: c_vehicle_svg,
    LIGHT_RECCE_VEHICLE_ENTITY: light_recce_vehicle_svg,
}


_EQUIPMENT_ENTITY_FIXUPS = {
    "antipersonnel_land_mine": unfilled_antipersonnel_fragmentation_mine,
    SIGINT_RADAR_ENTITY: add_radar_center_mast,
    "antitank_missile_launcher": separate_antitank_missile_launcher_dome,
    "antitank_missile_launcher_light": separate_antitank_missile_launcher_dome,
    "antitank_missile_launcher_medium": separate_antitank_missile_launcher_dome,
    "air_defense_missile_launcher": separate_air_defense_missile_launcher_dome,
    "air_defense_missile_launcher_light": separate_air_defense_missile_launcher_dome,
    "air_defense_missile_launcher_medium": separate_air_defense_missile_launcher_dome,
    "missile_launcher": separate_missile_launcher_dome,
    "missile_launcher_light": separate_missile_launcher_dome,
    "missile_launcher_medium": separate_missile_launcher_dome,
    BRIDGE_LAYER_TANK_ENTITY: bridge_layer_tank_mark,
    ARMOURED_RECCE_VEHICLE_ENTITY: armoured_recce_vehicle_mark,
    APV_WHEELED_ENTITY: apv_wheeled_marks,
}


def apply_nonnato_equipment_fixups(svg, entity):

    """Every post-render fixup a Land Equipment icon might need."""

    fixup = _EQUIPMENT_ENTITY_FIXUPS.get(entity)

    return fixup(svg) if fixup else svg


# --- Per-entity size multipliers ---------------------------------------
#
# Every non-NATO point layer scales its own marker by this, on top of
# its own MARKER_SIZE_MM and the feature's own "scale" field. The table
# lives HERE, not in the layers that apply it, because two things in
# this module have to divide it back out to stay visually correct: the
# Vehicle family's own stroke width, and every icon's own designation
# text (designation_font_size_in_icon_units()). Keeping it in the layer
# split that knowledge in two, which is how the designation text came
# to be wrong for the Vehicle family in the first place.
#
# Entity keys do not collide across layers, so one table serves all of
# them.
_SIGINT_SIZE_MULTIPLIER = 1.8

NONNATO_ENTITY_SIZE_MULTIPLIERS = {
    # Jammer/Radar read visibly smaller than their neighbours -
    # "Jammer and radar (sigint) are still smaller than other land
    # equipment, adjust them same as others" (2026-09-02). 1.8x came
    # from measured bounding boxes, not a guess.
    "jammer": _SIGINT_SIZE_MULTIPLIER,
    SIGINT_RADAR_ENTITY: _SIGINT_SIZE_MULTIPLIER,

    # The opposite problem - the Vehicle family draws nearly edge to
    # edge in its own viewBox and is close to twice as tall as a
    # milsymbol glyph, so it came out oversized ("reduce the size of
    # all three by 20% - too big now", 2026-09-05).
    B_VEHICLE_ENTITY: VEHICLE_SIZE_MULTIPLIER,
    C_VEHICLE_ENTITY: VEHICLE_SIZE_MULTIPLIER,
    LIGHT_RECCE_VEHICLE_ENTITY: VEHICLE_SIZE_MULTIPLIER,

    # Bar Mine's own 160-wide viewBox made the SAME 22-unit circle read
    # smaller than every other mine's - "bar mine - the size of the
    # circle is too small" (2026-09-03). The multiplier is exactly the
    # viewBox-width ratio, so it cancels that ratio completely: this is
    # the entity that proves designation_font_size_in_icon_units() has
    # to account for BOTH factors rather than either one alone.
    BAR_MINE_ENTITY: 160 / _STANDARD_EQUIPMENT_VIEWBOX_WIDTH,
}


def nonnato_entity_size_multiplier(entity):

    """This entity's own marker size multiplier, or 1 for the great majority that need none."""

    return NONNATO_ENTITY_SIZE_MULTIPLIERS.get(entity, 1)


def nonnato_entity_size_multiplier_expression(entities):

    """
    The same table as a QGIS CASE expression over `entities` - each
    layer passes its OWN entity keys, so a layer never carries a branch
    for an entity it does not offer.
    """

    branches = " ".join(
        f"WHEN \"entity\" = '{entity}' THEN {nonnato_entity_size_multiplier(entity):g}"
        for entity in entities
        if entity in NONNATO_ENTITY_SIZE_MULTIPLIERS
    )

    return f"CASE {branches} ELSE 1 END" if branches else "1"


# --- Mobility indicators: Tracked and Self-Propelled -------------------
#
# Requested live, 2026-09-06: "we need to design two add-ons to land
# equipment / tracked and self propelled / both are added to the
# existing glyph at the bottom, so the unique designation text needs to
# shift if selected / they need to appear as choice - maybe from a
# dropdown in the dialog box / for tracked - we use the same glyph as in
# APV i.e. the ellipse but it is 1/3 the size of the actual glyph / for
# self-propelled - we need to add a diamond or rhombus - size 1/3 of the
# standard rectangle view box".
#
# Unlike everything else on this layer these are not entities: any
# entity can carry one, so they are a separate "mobility" field with its
# own dropdown, applied as a post-render addition here.
#
# **Drawn straight into the SVG, deliberately.** The record used to say
# that a shape added below milsymbol's own declared draw area is clipped
# by QGIS's marker rendering, which is why Armoured Protection Vehicle
# (Wheeled)'s own wheels became separate QGIS symbol layers. That
# conclusion was wrong - re-measured 2026-09-06 by injecting exactly
# those wheels into the same APV glyph and rendering the marker through
# a real map render at 4/6/8/9.6/12/20/40 mm on BOTH QGIS versions: the
# wheels draw in full every time, and the rendered ink grows with the
# viewBox exactly as it should. Declaring width/height on the root, or
# omitting them, makes no difference either. The maintainer confirmed
# independently ("the clipped wheels was an incorrect approach - it has
# been fixed since then"). So there is no clipping trap to work around;
# the wheels' own symbol-layer implementation is left alone because it
# works and is tested, not because it is needed.
#
# Injecting rather than composing also gets the designation shift for
# free: inject_centered_designation_below() measures the SVG's own real
# ink, so a mobility mark that is part of the SVG pushes the text down
# by itself, which is exactly what "the unique designation text needs to
# shift if selected" asks for.
MOBILITY_TRACKED = "tracked"
MOBILITY_SELF_PROPELLED = "self_propelled"

MOBILITY_LABELS = {
    "": "None",
    MOBILITY_TRACKED: "Tracked",
    MOBILITY_SELF_PROPELLED: "Self-Propelled",
}

# Zero, by instruction - "the oval and rhombus should touch the glyph
# bottom". They are part of the symbol, not a label hanging off it, so
# there is no gap at all; a designation still sits clear of the whole
# thing by its own _DESIGNATION_GAP.
_MOBILITY_GAP = 0

# "the same glyph as in APV i.e. the ellipse but it is 1/3 the size of
# the actual glyph". Armoured Protected Vehicle's own glyph is not a
# true ellipse but a stadium - `M125,80 C150,80 150,120 125,120 L75,120
# C50,120 50,80 75,80 Z`, bounding box x 50..150 (100 wide) by y 80..120
# (40 tall). Restated here about its own centre so it can be scaled and
# placed anywhere: each pair is an offset from the centre.
_APV_STADIUM_OUTLINE = (
    (25, -20),
    ((50, -20), (50, 20), (25, 20)),
    (-25, 20),
    ((-50, 20), (-50, -20), (-25, -20)),
)

_MOBILITY_SCALE = 1 / 3

TRACKED_WIDTH = 100 * _MOBILITY_SCALE
TRACKED_HEIGHT = 40 * _MOBILITY_SCALE

# "size 1/3 of the standard rectangle view box" - the standard viewBox
# is milsymbol's own 108 square, so 36 across, read as a true diamond
# (equal diagonals), which is the literal reading of a single "size".
#
# Trimmed 20% after seeing it rendered ("reduce the size of rhombus by
# 20%", live the same day): at a full 36 it stood nearly three times
# taller than the Tracked mark beside it, which the two separate size
# rules had not made obvious on paper.
_SELF_PROPELLED_TRIM = 0.8

SELF_PROPELLED_SIZE = (
    _STANDARD_EQUIPMENT_VIEWBOX_WIDTH * _MOBILITY_SCALE * _SELF_PROPELLED_TRIM
)


def _tracked_path(centre_x, centre_y, colour):

    """APV's own stadium at a third of its size - see this section's own comment."""

    def point(offset):
        dx, dy = offset
        return (
            f"{centre_x + dx * _MOBILITY_SCALE:g},"
            f"{centre_y + dy * _MOBILITY_SCALE:g}"
        )

    start, right_cap, corner, left_cap = _APV_STADIUM_OUTLINE

    d = (
        f"M{point(start)} "
        f"C{point(right_cap[0])} {point(right_cap[1])} {point(right_cap[2])} "
        f"L{point(corner)} "
        f"C{point(left_cap[0])} {point(left_cap[1])} {point(left_cap[2])} Z"
    )

    return (
        f'<path d="{d}" stroke-width="3" stroke="{colour}" fill="none"></path>'
    )


def _self_propelled_path(centre_x, centre_y, colour):

    """A hollow diamond, its own diagonals SELF_PROPELLED_SIZE long."""

    half = SELF_PROPELLED_SIZE / 2

    d = (
        f"M{centre_x:g},{centre_y - half:g} "
        f"L{centre_x + half:g},{centre_y:g} "
        f"L{centre_x:g},{centre_y + half:g} "
        f"L{centre_x - half:g},{centre_y:g} Z"
    )

    return (
        f'<path d="{d}" stroke-width="3" stroke="{colour}" fill="none"></path>'
    )


_MOBILITY_MARKS = {
    MOBILITY_TRACKED: (_tracked_path, TRACKED_HEIGHT),
    MOBILITY_SELF_PROPELLED: (_self_propelled_path, SELF_PROPELLED_SIZE),
}


def inject_mobility_indicator(svg, mobility, colour):

    """
    Draws `mobility`'s own mark centred directly below `svg`'s own
    actual drawn content, widening the viewBox downward to fit it -
    the same "measure the real ink, then grow the viewBox" mechanism
    inject_centered_designation_below() uses, and deliberately applied
    BEFORE that one so the designation measures the mark too and drops
    below it.

    Anything falsy, or an unknown value, leaves the SVG untouched.
    """

    mark = _MOBILITY_MARKS.get(mobility) if mobility else None

    if mark is None:
        return svg

    draw, height = mark

    match = _VIEWBOX_PATTERN.search(svg)

    if not match:
        return svg

    vb_x, vb_y, vb_w, vb_h = (float(value) for value in match.groups())

    content_x, content_y, content_w, content_h = _content_bounds(
        svg, fallback=(vb_x, vb_y, vb_w, vb_h)
    )

    content_bottom = content_y + content_h

    centre_x = content_x + content_w / 2
    centre_y = content_bottom + _MOBILITY_GAP + height / 2

    svg = _expand_viewbox_for_rect(
        svg,
        vb_x,
        vb_y,
        vb_w,
        (centre_y + height / 2 + _INJECTED_HALF_STROKE) - vb_y,
    )

    return _inject_before_closing_svg(svg, draw(centre_x, centre_y, colour))


def render_nonnato_equipment_svg(
    affiliation, entity, designation=None, mobility=None
):

    """
    The full non-NATO Land Equipment render, mirroring render_nonnato_
    unit_svg()'s own structure but simpler: no frame, no echelon
    (Equipment never carried one, same as the NATO layer), no status
    (settled as Units-only - see Part D), no Combined Arms (Land Unit
    only). The mine family (real and synthetic alike, see
    MINE_ENTITIES) is green regardless of `affiliation`, same as
    obstacle_control_measures.py's own NATO-side convention - checked
    live that Equipment's own icon glyph does not vary by SIDC
    affiliation at all (unlike the Unit frame's shape), so unlike
    render_nonnato_unit_svg() there is no shape-forcing concern here,
    only colour. Jammer/SIGINT_RADAR_ENTITY (see
    _EQUIPMENT_SYMBOL_SET_OVERRIDES) render through this same path too,
    just against symbol_set "sigint_land" instead of "land_equipment" -
    and SIGINT_RADAR_ENTITY's own STORED key is resolved to the real
    APP-6E key "radar" via _EQUIPMENT_ENTITY_KEY_ALIASES before it ever
    reaches build_sidc(), since "radar" itself is already taken by Land
    Equipment's own distinct entity of the same name.

    `designation` is drawn by inject_centered_designation_below() as a
    separate post-render step, not passed to milsymbol at all - applies
    equally to the SIDC-rendered branch and the synthetic mine branch,
    since both used to have no consistent designation story of their
    own (the mines never took milsymbol's own uniqueDesignation option
    in the first place).

    `mobility` ("tracked"/"self_propelled", or nothing) adds its own
    mark below the glyph BEFORE the designation is placed, so the text
    measures it as part of the icon and drops below it - see
    inject_mobility_indicator(). Mines never carry one; the argument is
    simply never passed from that layer.
    """

    is_mine = entity in MINE_ENTITIES
    colour = (
        MINE_GREEN if is_mine
        else AFFILIATION_COLOURS.get(affiliation, AFFILIATION_COLOURS["friend"])
    )

    synthetic = _SYNTHETIC_MINE_SVG.get(entity) or _SYNTHETIC_VEHICLE_SVG.get(entity)

    if synthetic:

        svg = synthetic(colour)

    else:

        sidc = build_sidc(
            affiliation=SIDC_AFFILIATION_FOR.get(affiliation, "friend"),
            entity=_EQUIPMENT_ENTITY_KEY_ALIASES.get(entity, entity),
            symbol_set=_EQUIPMENT_SYMBOL_SET_OVERRIDES.get(
                entity, "land_equipment"
            ),
            edition="2525E",
        )

        options = {"frame": False, "fill": False, "monoColor": colour}

        svg = apply_nonnato_equipment_fixups(
            render_symbol_svg(sidc, options), entity
        )

    # Order matters: the mark becomes part of the SVG's own ink, so the
    # designation measures it and drops below it without being told.
    svg = inject_mobility_indicator(svg, mobility, colour)

    svg = inject_centered_designation_below(
        svg,
        designation,
        colour,
        size_multiplier=nonnato_entity_size_multiplier(entity),
    )

    return scale_svg_stroke_width(svg, DEFAULT_STROKE_SCALE)


# --- Control Measure Points ---------------------------------------------
#
# Part C's own settled mechanism: "affiliation is coded the same way as
# NATO... no non-NATO-specific treatment needed for that part." Unlike
# Unit/Equipment/SIGINT above, nine of that layer's ten entities
# (Decision Point, Fort, Impact Point, Observation Post, Artillery
# Observation Post, Point Of Interest, Shelter Above Ground, Shelter
# Below Ground, Target/DF Task) get NO new rendering logic at all -
# Pill Box is the one exception, and its fixup is below. They
# render through the plain existing mct_sidc_svg()/mct_build_sidc()
# pipeline, same as every other NATO control-measure-points layer, with
# milsymbol's own real 4-value affiliation colouring and no monoColor
# override. See control_measure_points_layer_nonnato.py's own renderer
# for that half.
#
# Booby Trap needed its own custom render function: "fully replaces its
# current NATO glyph (an ellipse with a triangular peak over it), rather
# than a tweak to the existing icon" (rules record, 2026-08-31), coloured
# MINE_GREEN regardless of affiliation - confirmed against
# obstacle_control_measures.py's own existing green-obstacle default, so
# this is "carrying over unchanged", not a new non-NATO deviation. The
# function itself stays here (rendering logic, layer-agnostic) even
# though the ENTITY moved 2026-09-03 to its own "Mines and Obstacles
# (Non-NATO)" layer, alongside the mine family below - see
# mines_and_obstacles_layer_nonnato.py.

def booby_trap_marks(colour):

    """
    Booby Trap's own shape without an SVG wrapper - a hollow circle and
    four plain horns at 45/135/225/315 degrees, extending x/y 68.1 to
    131.9 about the centre (100,100).

    Factored out 2026-09-06 so Land Unit's own Ordnance entity can draw
    the SAME shape rather than a copy of it - "Ordnance unit - standard
    rectangle with the [booby trap] glyph inside it". `colour` is a
    real argument there: on Mines and Obstacles this is always
    MINE_GREEN, but on Land Unit it takes that layer's own affiliation
    colour ("the colour affiliation remains standard as per land units
    and not green").
    """

    horns = "".join(
        f'<path d="{d}" stroke-width="3" stroke="{colour}" fill="none"></path>'
        for d in (
            "M115.6,84.4 L131.9,68.1",
            "M84.4,84.4 L68.1,68.1",
            "M84.4,115.6 L68.1,131.9",
            "M115.6,115.6 L131.9,131.9",
        )
    )

    return _mine_circle(colour, filled=False) + horns


def booby_trap_control_measure_svg(colour=MINE_GREEN):

    """
    Mines and Obstacles' own Booby Trap (280700, moved 2026-09-03 from
    Control Measure Points - see this section's own comment above) -
    NOT the same layer's own, structurally distinct, Antitank Mine
    Booby Trapped synthetic entity (ANTITANK_MINE_BOOBY_TRAPPED_ENTITY
    above), though the two now share the same horn geometry - see
    below.

    Corrected twice, live, 2026-09-02:
    1. First correction, against a rendered screenshot: "booby trap is
       incorrect - it should be same as antitank mine but with the
       circle only, no fill" - read (wrongly, as it turned out) as
       "drop the horns entirely", replacing the earlier dashed-double-
       horn design with a bare hollow circle.
    2. Second correction, against a screenshot of THAT bare circle:
       "its supposed to have four lines at the four angles as
       described earlier" - the horns were never meant to be dropped,
       only the CIRCLE'S fill was the actual complaint both times. This
       is the tracker's own original "first draft" description
       ("hollow circle + four 45/135/225/315-degree horns"), which
       turns out to have been right all along - it was ANTITANK_MINE_
       BOOBY_TRAPPED_ENTITY's own FILLED circle that was the source of
       the earlier confusion, not the horn count.

    Built from the exact same four-horn coordinates as
    antitank_mine_booby_trapped_svg() (45/135/225/315 degrees, plain
    lines, no dashing), with a hollow circle instead of that function's
    own filled one - the one real difference between the two shapes.
    """

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="46 46 108 108">'
        + booby_trap_marks(colour)
        + '</svg>'
    )


def apply_pillbox_fixup(svg):

    """
    Pill Box (`shelter`, 280900) renders as a solid filled square,
    hardcoded into milsymbol's own icon drawing the same way Field
    Fortification's other hardcoded-fill glyphs are (see Part A's own
    "blanket policy" note on this being common, not rare) - confirmed
    live that milsymbol's own `fill: false` option does nothing for it
    (the rendered fill matches the rendered stroke colour exactly
    either way). Forced hollow here by post-processing instead, per the
    maintainer's own live report, 2026-09-02: "pillbox is rendering as
    filled rectangle, it should be just the outline, no fill". Pill Box
    is a single `<path>` with exactly one fill attribute, so a blunt
    "first fill wins" replace is safe and does not risk touching
    anything else in the icon.
    """

    return re.sub(r'fill="[^"]*"', 'fill="none"', svg, count=1)


def render_nonnato_pillbox_svg(affiliation, status="present", designation=None):

    """
    Pill Box's own render - branched out of the plain mct_sidc_svg()
    pipeline every other Control Measure Point entity still uses (see
    this section's own top-of-file comment), purely because it is the
    one entity needing apply_pillbox_fixup() above. Affiliation/status/
    designation all behave exactly as they would through the plain
    pipeline - NATO's own real colouring, no monoColor override, per
    Part C's own settled "no non-NATO-specific treatment" rule; only
    the fill is forced hollow.
    """

    sidc = build_sidc(
        affiliation=affiliation,
        entity="shelter",
        symbol_set="control_measure",
        echelon="unspecified",
        status=status,
        headquarters=False,
        edition="2525E",
    )

    options = {}

    if designation:
        options["uniqueDesignation"] = str(designation).upper()

    svg = apply_pillbox_fixup(render_symbol_svg(sidc, options or None))

    return scale_svg_stroke_width(svg, DEFAULT_STROKE_SCALE)
