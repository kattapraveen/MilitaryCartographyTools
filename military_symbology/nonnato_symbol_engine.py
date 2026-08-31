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
from .symbol_engine import render_symbol_svg, scale_svg_stroke_width


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

# The SIDC format itself only encodes four standard-identity values
# (friend/hostile/neutral/unknown) - Friendly Paramilitary and
# Non-state Hostile are non-NATO's OWN colour choices, layered on top
# via monoColor, with no real SIDC digit of their own. This maps each
# of the six to whichever real SIDC affiliation is closest, purely so
# build_sidc() has a valid value to encode - it has no effect on what
# actually renders, since monoColor overrides milsymbol's own
# affiliation-driven colour entirely.
SIDC_AFFILIATION_FOR = {
    "friend": "friend",
    "hostile": "hostile",
    "neutral": "neutral",
    "unknown": "unknown",
    "friendly_paramilitary": "friend",
    "nonstate_hostile": "hostile",
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

    width, height = _COMBINED_ARMS_SIZES.get(echelon, _COMBINED_ARMS_FLOOR)

    x = 100 - width / 2
    y = _FRAME_TOP - height

    return (
        f'<rect x="{x:g}" y="{y:g}" width="{width:g}" height="{height:g}" '
        f'stroke-width="4" stroke="{colour}" fill="none"></rect>'
    )


def _inject_before_closing_svg(svg, addition):

    return svg.replace("</svg>", addition + "</svg>", 1)


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

        svg = _inject_before_closing_svg(
            svg, combined_arms_rect_svg(echelon, combined_arms_colour)
        )

    return scale_svg_stroke_width(svg, DEFAULT_STROKE_SCALE)
