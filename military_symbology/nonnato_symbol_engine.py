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
    ten of its eleven entities go through the plain NATO mct_sidc_svg()
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

# --- Mine family (Land Equipment) -------------------------------------
#
# Three real APP-6E entities (already render correctly with no fixup,
# see the rules record's "Mine icons" note) plus five synthetic icons
# with no SIDC at all - the whole family defaults to MINE_GREEN
# regardless of the feature's own affiliation, same as obstacle_
# control_measures.py's own NATO-side convention for the same reason.
#
# Synthetic keys are outside APP-6E's own numbering on purpose (a
# leading "nonnato_" prefix), so they can never collide with a real
# entity key sidc_2525e.py might add later.
UNKNOWN_MINE_ENTITY = "nonnato_unknown_mine"
INFLUENCE_MINE_ANTI_TANK_ENTITY = "nonnato_influence_mine_anti_tank"
INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY = "nonnato_influence_mine_anti_personnel"
ANTITANK_MINE_BOOBY_TRAPPED_ENTITY = "nonnato_antitank_mine_booby_trapped"
BAR_MINE_ENTITY = "nonnato_bar_mine"

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


_SYNTHETIC_MINE_SVG = {
    UNKNOWN_MINE_ENTITY: unknown_mine_svg,
    INFLUENCE_MINE_ANTI_TANK_ENTITY: influence_mine_anti_tank_svg,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY: influence_mine_anti_personnel_svg,
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY: antitank_mine_booby_trapped_svg,
    BAR_MINE_ENTITY: bar_mine_svg,
}


def is_synthetic_entity(entity):

    """True for any entity with no SIDC/milsymbol render at all - Enemy (Info Unknown) or one of the five synthetic mines."""

    return entity == ENEMY_INFO_UNKNOWN_ENTITY or entity in _SYNTHETIC_MINE_SVG

# Enemy (Info Unknown) has no APP-6E entity at all - a standalone frame
# variant (two concentric rectangles, no icon glyph inside), always
# hostile red regardless of the feature's own affiliation field, per
# the rules record.
ENEMY_INFO_UNKNOWN_ENTITY = "enemy_info_unknown"

_ENEMY_INFO_UNKNOWN_COLOUR = AFFILIATION_COLOURS["hostile"]


def is_enemy_info_unknown(entity):

    return entity == ENEMY_INFO_UNKNOWN_ENTITY


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


# Dispatch tables - keyed on the feature's own entity, applied after
# the echelon fixup (which is entity-independent) whenever that entity
# is selected, regardless of affiliation/echelon/status.
_ENTITY_FIXUPS = {
    "aviation_fixed_wing": hollow_army_aviation_propeller,
    "parachute_rigger": composite_parachute_rigger,
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

    wh_match = _WIDTH_HEIGHT_PATTERN.search(svg)

    if wh_match:

        scale = float(wh_match.group(1)) / vb_w

        svg = _WIDTH_HEIGHT_PATTERN.sub(
            f'width="{new_w * scale:g}" height="{new_h * scale:g}"',
            svg,
            count=1,
        )

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
    designation=None,
    combined_arms=False,
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
    """

    if is_enemy_info_unknown(entity):

        svg = enemy_info_unknown_svg()
        combined_arms_colour = _ENEMY_INFO_UNKNOWN_COLOUR

    else:

        sidc = build_sidc(
            affiliation=SIDC_AFFILIATION_FOR.get(affiliation, "friend"),
            entity=entity,
            symbol_set="ground_unit",
            echelon=echelon,
            status=status,
            headquarters=False,
            edition="2525E",
        )

        colour = AFFILIATION_COLOURS.get(
            affiliation, AFFILIATION_COLOURS["friend"]
        )

        options = {"frame": True, "fill": False, "monoColor": colour}

        if designation:
            options["uniqueDesignation"] = str(designation).upper()

        svg = apply_nonnato_unit_fixups(
            render_symbol_svg(sidc, options), entity, echelon
        )

        combined_arms_colour = colour

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
# entity on the layer, mines included.
_DESIGNATION_FONT_SIZE = 28.0
_DESIGNATION_GAP = 10.0


def _designation_font_size(text, max_width):

    """
    `_DESIGNATION_FONT_SIZE`, or smaller if `text` would otherwise spill
    past `max_width` - same QFontMetricsF technique symbol_engine.py's
    own _fitted_font_size() uses, reimplemented here rather than
    imported because that one measures against a single hardcoded
    constant (built for one specific icon's own fixed-width supply
    box), not a caller-supplied width that varies with every icon's own
    viewBox.
    """

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)

        width = (
            QFontMetricsF(font).horizontalAdvance(text)
            / 1000.0
            * _DESIGNATION_FONT_SIZE
        )

    except Exception:

        return _DESIGNATION_FONT_SIZE

    if width <= max_width:
        return _DESIGNATION_FONT_SIZE

    return _DESIGNATION_FONT_SIZE * max_width / width


def inject_centered_designation_below(svg, designation, colour):

    """
    Draws `designation`, centred, directly below `svg`'s own current
    viewBox - see this section's own comment above for why. No-ops on
    an empty/None designation or an svg with no parseable viewBox.

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
    """

    if not designation:
        return svg

    match = _VIEWBOX_PATTERN.search(svg)

    if not match:
        return svg

    vb_x, vb_y, vb_w, vb_h = (float(value) for value in match.groups())

    text = str(designation).upper()

    font_size = _designation_font_size(text, vb_w * 0.9)

    text_block_height = _DESIGNATION_GAP + font_size * 1.2

    svg = _expand_viewbox_for_rect(
        svg, vb_x, vb_y, vb_w, vb_h + text_block_height
    )

    center_x = vb_x + vb_w / 2
    baseline_y = vb_y + vb_h + _DESIGNATION_GAP + font_size

    text_element = (
        f'<text x="{center_x:g}" y="{baseline_y:g}" text-anchor="middle" '
        f'font-size="{font_size:g}" font-family="Arial" stroke="none" '
        f'fill="{colour}">{_escape_text(text)}</text>'
    )

    return _inject_before_closing_svg(svg, text_element)


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

_EQUIPMENT_ENTITY_KEY_ALIASES = {
    SIGINT_RADAR_ENTITY: "radar",
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


_EQUIPMENT_ENTITY_FIXUPS = {
    "antipersonnel_land_mine": unfilled_antipersonnel_fragmentation_mine,
    SIGINT_RADAR_ENTITY: add_radar_center_mast,
}


def apply_nonnato_equipment_fixups(svg, entity):

    """Every post-render fixup a Land Equipment icon might need."""

    fixup = _EQUIPMENT_ENTITY_FIXUPS.get(entity)

    return fixup(svg) if fixup else svg


def render_nonnato_equipment_svg(affiliation, entity, designation=None):

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
    """

    is_mine = entity in MINE_ENTITIES
    colour = (
        MINE_GREEN if is_mine
        else AFFILIATION_COLOURS.get(affiliation, AFFILIATION_COLOURS["friend"])
    )

    if entity in _SYNTHETIC_MINE_SVG:

        svg = _SYNTHETIC_MINE_SVG[entity](colour)

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

    svg = inject_centered_designation_below(svg, designation, colour)

    return scale_svg_stroke_width(svg, DEFAULT_STROKE_SCALE)


# --- Control Measure Points ---------------------------------------------
#
# Part C's own settled mechanism: "affiliation is coded the same way as
# NATO... no non-NATO-specific treatment needed for that part." Unlike
# Unit/Equipment/SIGINT above, the ten other required entities (Decision
# Point, Fort, Impact Point, Observation Post, Artillery Observation
# Post, Point Of Interest, Pill Box, Shelter Above Ground, Shelter Below
# Ground, Target) get NO new rendering logic at all here - they render
# through the plain existing mct_sidc_svg()/mct_build_sidc() pipeline,
# same as every other NATO control-measure-points layer, with milsymbol's
# own real 4-value affiliation colouring and no monoColor override. See
# control_measure_points_layer_nonnato.py's own renderer for that half.
#
# Booby Trap is the one exception needing code here: "fully replaces its
# current NATO glyph (an ellipse with a triangular peak over it), rather
# than a tweak to the existing icon" (rules record, 2026-08-31), coloured
# MINE_GREEN regardless of affiliation - confirmed against
# obstacle_control_measures.py's own existing green-obstacle default, so
# this is "carrying over unchanged", not a new non-NATO deviation.

def booby_trap_control_measure_svg(colour=MINE_GREEN):

    """
    Control Measure Point's own Booby Trap (280700) - NOT the Land
    Equipment mine family's own, structurally distinct, Antitank Mine
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

    horns = (
        f'<path d="M115.6,84.4 L131.9,68.1" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M84.4,84.4 L68.1,68.1" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M84.4,115.6 L68.1,131.9" stroke-width="3" stroke="{colour}" fill="none"></path>'
        f'<path d="M115.6,115.6 L131.9,131.9" stroke-width="3" stroke="{colour}" fill="none"></path>'
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" version="1.2" '
        'baseProfile="tiny" viewBox="46 46 108 108">'
        + _mine_circle(colour, filled=False)
        + horns
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
