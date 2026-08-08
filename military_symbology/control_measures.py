# -*- coding: utf-8 -*-

"""
Builds ready-to-use control-measure layers - one for line-type measures
(phase lines, boundaries, axis of advance), one for area-type measures
(objectives, named areas of interest) - each styled via a
QgsRuleBasedRenderer keyed on a "measure_type" field, mirroring
grid/mgrs_sub_grid.py's own rule-based renderer pattern.

Unlike military_symbology/sidc.py's point symbols (verified exactly
against milsymbol.js's own parsing source - see that module's docstring),
there is no equivalent programmatic renderer for MIL-STD-2525/APP-6
tactical graphics lines and areas to verify against: milsymbol.js's own
source has no multipoint/polygon/linestring code at all, and the one
library that attempted this (milgraphics) is archived/incomplete (see
docs/roadmap.md's Phase 10 entry). The line/area SHAPES below (dashed
boundary pattern, arrowhead placement, NAI's dashed-outline-on-any-polygon)
remain a hand-authored, practically-recognisable approximation rather
than a verified-correct rendition of MIL-STD-2525D Appendix H's own
templates (which specify, e.g., an actual hexagon for NAI and
echelon-symbol line ends for boundaries) - a further pass to match those
templates precisely is tracked as a future sub-phase in docs/roadmap.md,
deliberately deferred since it needs custom QGIS symbol construction with
no rendering library to lean on, unlike the point-symbol side.

The COLOURING, however, is verified directly against the standard's own
H.5.3 Coloring rule (read from the actual MIL-STD-2525D PDF, not a
paraphrase): friendly control measures in black or blue, hostile in red.
This module uses the same "affiliation" vocabulary as sidc.py's own
AFFILIATIONS (friend/hostile/neutral/unknown) and colours friend=blue,
hostile=red, neutral/unknown=black (black is also the default affiliation,
matching "black as standard" for a control measure with no stated
affiliation) - a data-defined colour expression applied on top of each
measure type's own shape, not a rule-tree branch per affiliation. Every
symbol layer below - including the smaller decorative ones (tick marks,
arrowheads, the circle-from-line layers) - is wired through
_apply_affiliation_color() the same way; none hardcode black.

Two separate layers, not one, because a QgsVectorLayer is always a single
geometry type - there's no "LineString or Polygon" layer in QGIS.

**2026-08-07: added Maneuver/Defensive/Offensive control measures (Appendix
H, H.5.11-H.5.14) and Mission Task symbols (H.5.26)**, reading the actual
standard text (not milsymbol.js, which has no coverage here at all - see
above) for each one's real anchor-point/draw rules before approximating.
As with the original five measure types, these are hand-authored QGIS-
native renditions, not verified-exact reproductions - see each _xxx_symbol()
function's own comment for what specific detail is approximated and why.
Two recurring approximation techniques introduced by this pass, reused
across several measure types rather than one-off per type:
  - A "tick mark" - a stroke-only "line"-shape QgsMarkerSymbol placed via
    QgsMarkerLineSymbolLayer with an extra 90-degree angle on top of the
    marker line's own tangent-following rotation, so it reads as a mark
    perpendicular to the line/boundary it sits on (Block's cross-bar,
    Strong Point's fortification ticks, Disrupt's ladder of arrows,
    Penetrate's perpendicular arrow). None of these attempt the standard's
    own echelon-text-height-driven tick spacing (see Strong Point/Contain's
    own draw rules in the PDF) - this layer has no echelon field at all
    (see the deferred-shapes note under sub-phase 10.3 in docs/roadmap.md),
    so tick size/interval are fixed constants instead.
  - A "circle from a line" - several Mission Task symbols (Isolate, Secure,
    Seize) and one Defensive maneuver control measure (Retain, H.5.12.1 -
    despite being commonly grouped with Mission Tasks, it is NOT one; see
    _retain_symbol()'s own comment) are defined by the standard as a
    circle: point 1 is the centre, point 2 is a point on the circle
    defining the radius. That is a 2-point LINE's own natural shape, not a
    digitized polygon boundary, so each is a QgsLineSymbol whose one
    symbol layer is a QgsGeometryGeneratorSymbolLayer computing
    buffer(start_point($geometry), length($geometry)) rather than being
    moved to the Areas layer (which would lose the centre+radius semantics
    the standard itself specifies). The standard's own circle has a
    30-degree open arc (the friendly side); a full closed circle is
    rendered instead, since QGIS has no simple "arc with a gap" primitive
    to build on - documented per-function, not silently dropped.

**Deliberately NOT implemented in this pass, with the actual reason
found in the standard's own text, not assumed:**
  - **Observation Post (H.5.12.2)** and the Mission Task symbols
    **Destroy, Interdict, and Neutralize (H.5.26)** are all defined by the
    standard as requiring exactly ONE anchor point ("the center point
    defines the center of the symbol") - genuinely point symbols, not
    lines or areas. This module only has Lines/Areas layers; a Points-type
    control-measures layer is a bigger, separate design decision (its own
    native-QGIS-marker layer, still not the point-symbol/milsymbol.js
    pipeline in sidc.py/symbol_engine.py) left for a future sub-phase.
  - **"Disengage"**, one of the tasks the plugin's own maintainer asked
    for, does not appear anywhere in MIL-STD-2525D at all (confirmed by
    text-searching the entire 885-page PDF, not just Appendix H) - nothing
    was invented under that name rather than guess at a mapping the
    standard doesn't make.
  - **"Contain"**, also asked for, IS in the standard, but not as a
    Mission Task: it is a Defensive maneuver control measure (H.5.12.1,
    code 151204) with a real, distinctive semicircle-plus-arrow geometry
    (a 3-anchor-point shape: two points set a semicircle's diameter, the
    third sets an arrow projecting from its centre) - meaningfully more
    custom QGIS symbol construction than this pass's other approximations
    for what would be one more measure type, so it is deferred alongside
    the already-deferred exact-shape work from sub-phase 10.3 (NAI's real
    hexagon, boundary's echelon-symbol line ends) rather than rushed.
  - The rest of Table H-VII/H-VIII/H-IX/H-X/H-XI/H-XII (H.5.11-H.5.14) and
    Table H-XXIV (H.5.26) - e.g. Assault Position, Attack Position,
    Bypass, Clear, Counterattack, Drop/Extraction/Landing/Pickup Zone,
    Encirclement's own Enemy variant, Follow and Assume/Support, Infiltration
    Lane, Limit of Advance, Line of Departure, Occupy, Probable Line of
    Deployment, Relief in Place, Retire/Retirement, Withdraw Under
    Pressure, and the friendly/enemy/planned-or-on-order sub-variants of
    nearly every entry above - were intentionally not added. This pass
    covers the sections and named tasks actually requested (H.5.11-H.5.14,
    H.5.26's named BLOCK/BREACH/CANALIZE/DELAY/DISRUPT/FIX/ISOLATE/
    PENETRATE/SECURE/SEIZE/WITHDRAW), not the whole of Appendix H - the
    remaining sections (H.5.15-H.5.25, H.5.27 and beyond) remain for a
    future sub-phase, same as sub-phase 10.3's own explicitly-deferred
    shape work.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsFillSymbol,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedRenderer,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsSymbolLayerUtils,
    QgsTemplatedLineSymbolLayerBase,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ..core._layer_utils import add_layer_at_default_position
from ..core.text_format import build_text_format
from .sidc import AFFILIATIONS


LINES_LAYER_NAME = "Tactical Graphics - Control Measures (Lines)"
AREAS_LAYER_NAME = "Tactical Graphics - Control Measures (Areas)"

LABEL_FONT_SIZE = 9

LINE_MEASURE_TYPE_LABELS = {
    "phase_line": "Phase Line",
    "boundary": "Boundary",
    "axis_of_advance": "Axis of Advance",
    # H.5.11 Maneuver Control Measure Symbols (Table H-VII).
    "forward_line_of_troops": "Forward Line of Troops (FLOT)",
    "line_of_contact": "Line of Contact (LC)",
    "forward_edge_of_battle_area": "Forward Edge of the Battle Area (FEBA)",
    "principal_direction_of_fire": "Principal Direction of Fire (PDF)",
    # H.5.13.2 Direction of attack (Table H-XI).
    "direction_of_attack": "Direction of Attack",
    # H.5.12.1 Defensive maneuver, but a circle-from-line shape (see
    # this module's own docstring) rather than a digitized area.
    "retain": "Retain",
    # H.5.26 Mission Task Symbols (Table H-XXIV).
    "block": "Block (Mission Task)",
    "breach": "Breach (Mission Task)",
    "canalize": "Canalize (Mission Task)",
    "disrupt": "Disrupt (Mission Task)",
    "fix": "Fix (Mission Task)",
    "penetrate": "Penetrate (Mission Task)",
    "delay": "Delay (Mission Task)",
    "withdraw": "Withdraw (Mission Task)",
    "isolate": "Isolate (Mission Task)",
    "secure": "Secure (Mission Task)",
    "seize": "Seize (Mission Task)",
}

AREA_MEASURE_TYPE_LABELS = {
    "objective": "Objective",
    "nai": "Named Area of Interest (NAI)",
    # H.5.12.1 Defensive maneuver - Areas (Table H-VIII).
    "battle_position": "Battle Position",
    "strong_point": "Strong Point",
    "engagement_area": "Engagement Area (EA)",
    # H.5.11 Maneuver Areas (Table H-VII).
    "assembly_area": "Assembly Area (AA)",
    # H.5.14 Maneuver control measure symbols (Table H-XII).
    "encirclement": "Encirclement",
}

# Keys match sidc.py's own AFFILIATIONS (the same "standard identity"
# concept MIL-STD-2525D uses for units) - labels are this module's own
# presentation layer, same separation-of-concerns convention as
# unit_layer.py's _AFFILIATION_LABELS.
AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

DEFAULT_AFFILIATION = "unknown"

# Per MIL-STD-2525D H.5.3 Coloring, as scoped by the user: friendly control
# measures in blue, hostile in red, everything else (neutral/unknown/the
# default) in black - "black as standard". A single shared expression
# applied to every measure type's own stroke/fill colour, rather than
# threading affiliation through each symbol builder's own parameters.
_AFFILIATION_COLOR_EXPRESSION = (
    "CASE "
    "WHEN \"affiliation\" = 'friend' THEN color_rgb(0, 0, 255) "
    "WHEN \"affiliation\" = 'hostile' THEN color_rgb(255, 0, 0) "
    "ELSE color_rgb(0, 0, 0) "
    "END"
)


def _apply_affiliation_color(symbol_layer, properties):

    """
    Makes the given symbol_layer's colour properties (e.g. StrokeColor,
    FillColor) data-defined by _AFFILIATION_COLOR_EXPRESSION, so every
    control measure's own "affiliation" attribute drives its colour
    automatically - the same data-defined-property pattern
    unit_layer.py's own SIDC rendering already uses, rather than
    QgsRuleBasedRenderer rules per affiliation (which would multiply
    the existing measure_type rule tree by every affiliation value for
    no benefit, since only colour - not shape - varies by affiliation).
    """

    color_property = QgsProperty.fromExpression(_AFFILIATION_COLOR_EXPRESSION)

    for property_key in properties:

        symbol_layer.setDataDefinedProperty(
            property_key,
            color_property
        )


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _phase_line_symbol():

    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


def _boundary_symbol():

    # A distinctive dash-dash-dot pattern to read as "boundary" at a
    # glance rather than an ordinary line - not claimed to match the
    # spec's own exact dash ratios (see this module's own docstring).
    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.4
    )

    line_layer.setUseCustomDashPattern(
        True
    )

    line_layer.setCustomDashVector(
        [8, 2, 1, 2, 1, 2]
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


def _axis_of_advance_symbol():

    # A solid line with a filled arrowhead at its last vertex, pointing
    # in the drawn direction of advance.
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.5",
        }
    )

    # "arrowhead" is a stroke-only shape (no fillable interior), so its
    # boldness comes entirely from outline_width - the createSimple()
    # default is outline_width=0, which Qt draws as a 1-device-pixel
    # cosmetic hairline regardless of zoom, reading as too faint next to
    # the 0.5mm line it caps. Set explicitly, heavier than the line
    # itself so the arrowhead reads clearly.
    arrow_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "arrowhead",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.8",
            "size": "4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    _apply_affiliation_color(
        arrow_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    marker_line = QgsMarkerLineSymbolLayer()

    marker_line.setSubSymbol(
        arrow_marker
    )

    marker_line.setPlacements(
        QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
    )

    symbol.appendSymbolLayer(
        marker_line
    )

    return symbol


def _objective_symbol():

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,0,0",
            "outline_width": "0.5",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


def _nai_symbol():

    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "dash",
            "outline_color": "0,0,0",
            "outline_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol



# --- Shared helpers for the H.5.11-H.5.14 / H.5.26 additions below -------
#
# The original five measure types above each build their own one-off
# QgsSymbol from scratch. The Mission Task (H.5.26) and Maneuver/
# Defensive/Offensive (H.5.11-H.5.14) additions below share a much
# smaller set of recurring shapes (an arrow-tipped line, a perpendicular
# tick, a circle generated from a 2-point line) across many measure
# types, so those recurring shapes are factored into helpers here instead
# of being re-typed per measure type - see this module's own docstring
# for why each technique looks the way it does.

def _arrow_marker_symbol(size=4, outline_width=0.8, angle=0):

    """
    A filled chevron arrowhead marker, sized/weighted the same way
    _axis_of_advance_symbol()'s own arrow_marker already established
    (outline_width set explicitly, since "arrowhead" has no fillable
    interior and createSimple()'s own outline_width default of 0 is a
    barely-visible cosmetic hairline - see that function's own comment).
    `angle` rotates the marker on top of whatever tangent-following
    rotation QgsMarkerLineSymbolLayer itself applies at the placement
    point - 0 leaves the arrow pointing in the drawn direction of travel
    (matching axis_of_advance's own LastVertex arrow), 180 flips it to
    point the opposite way (used by principal_direction_of_fire's
    FirstVertex arrow, so it points away from the shared vertex rather
    than back into it).
    """

    marker = QgsMarkerSymbol.createSimple(
        {
            "name": "arrowhead",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": str(outline_width),
            "size": str(size),
            "angle": str(angle),
        }
    )

    _apply_affiliation_color(
        marker.symbolLayer(0),
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    return marker


def _tick_marker_symbol(size=5, outline_width=0.9):

    """
    A short perpendicular tick - a stroke-only "line"-shape marker (same
    "no fillable interior, set outline_width explicitly" lesson as
    "arrowhead" above). Left at angle 0: confirmed by rendering it against
    a real, non-axis-aligned line that a "line"-shape marker's own neutral
    pose (angle 0) is ALREADY perpendicular to the line/boundary once
    QgsMarkerLineSymbolLayer's default tangent-following rotation is
    applied - an earlier version of this function added an extra 90
    degrees on top, on the mistaken assumption that the neutral pose was
    parallel to the line; that actually rendered the tick lying flat
    along the line instead, at every placement type (CentralPoint,
    Interval, FirstVertex, LastVertex all confirmed affected), making it
    functionally invisible since it fully overlapped the base line's own
    stroke. Size bumped from 3mm/0.5mm to 5mm/0.9mm at the same time -
    even oriented correctly, 3mm/0.5mm proved too faint to read reliably
    against the base line at ordinary map zoom. Used for Block's
    cross-bar, Strong Point's fortification ticks, Disrupt's ladder of
    arrows, and (in _penetrate_symbol(), combined with an arrow instead)
    Penetrate's perpendicular arrow. Fixed size/spacing rather than the
    standard's own echelon-text-height-driven tick rule - see this
    module's own docstring for why.
    """

    marker = QgsMarkerSymbol.createSimple(
        {
            "name": "line",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "outline_width": str(outline_width),
            "size": str(size),
            "angle": "0",
        }
    )

    _apply_affiliation_color(
        marker.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return marker


def _marker_line_layer(marker_symbol, placement, interval=None):

    """Wires a marker sub-symbol onto a line at the given placement."""

    layer = QgsMarkerLineSymbolLayer()

    layer.setSubSymbol(
        marker_symbol
    )

    layer.setPlacements(
        placement
    )

    if interval is not None:

        layer.setInterval(
            interval
        )

    return layer


def _wavy_line_layers(interval=4, outline_width=0.6, offset=0):

    """
    Two marker-line layers that together draw a continuous serpentine/wave
    line, matching the standard's own actual drawn appearance for FLOT
    (H.5.11, Table H-VII, code 140101) - found only by rendering the
    template page's own picture, since the "Anchor Points"/"Size/Shape"
    text just says "requires at least two points... to define the line"
    with no mention of the line being wavy at all (this module's own
    recurring lesson: text alone is not enough). QGIS has no built-in wavy
    pen style (Qt's own PenStyle enum only offers
    solid/dash/dot/dash-dot/dash-dot-dot), so this approximates one from two
    "half_arc" marker-line layers repeating at the same interval but offset
    by half of it from each other, with opposite rotations (angle 0 vs
    180) - each layer's arcs alternate with the other's, producing one
    continuous-looking wave rather than a row of disconnected bumps.
    Returns a list of layers (not a full symbol) so line_of_contact can
    combine two offset copies - one per side - into a single symbol.
    """

    layers = []

    for angle, offset_along_line in ((0, 0), (180, interval / 2.0)):

        marker = QgsMarkerSymbol.createSimple(
            {
                "name": "half_arc",
                "color": "0,0,0",
                "outline_color": "0,0,0",
                "outline_width": str(outline_width),
                "size": str(interval),
                "angle": str(angle),
            }
        )

        _apply_affiliation_color(
            marker.symbolLayer(0),
            [QgsSymbolLayer.Property.StrokeColor]
        )

        layer = QgsMarkerLineSymbolLayer()
        layer.setSubSymbol(marker)
        layer.setPlacements(QgsTemplatedLineSymbolLayerBase.Placement.Interval)
        layer.setInterval(interval)
        layer.setOffsetAlongLine(offset_along_line)
        layer.setOffset(offset)

        layers.append(layer)

    return layers


def _wavy_line_symbol(interval=4, outline_width=0.6):

    """A single wavy line - see _wavy_line_layers() for the technique."""

    layers = _wavy_line_layers(interval=interval, outline_width=outline_width)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        layers[0]
    )

    symbol.appendSymbolLayer(
        layers[1]
    )

    return symbol


def _arrow_line_symbol(
    line_width=0.4,
    line_style="solid",
    arrow_size=4,
    arrow_outline_width=0.8,
    tip_at_first_vertex=False
):

    """
    A plain line - solid or dashed - ending in a single filled arrowhead.
    Several Mission Task (H.5.26) graphics and direction_of_attack
    (H.5.13.2) reduce to exactly this shape once approximated down to what
    QGIS's native symbol layers can build (the standard's own tables give
    each of these its own precise arrowhead length/width ratio and, for
    delay/withdraw, an additional 180-degree arc at the base - none of that
    further detail is attempted here, the same "recognisable, not exact"
    approximation this module's docstring already applies to
    axis_of_advance's own wide-arrow-band simplification).

    `tip_at_first_vertex` matters and is NOT cosmetic: most of these
    graphics' own text doesn't say which end is the tip (direction_of_attack
    and axis_of_advance both leave it to "orientation is determined by the
    anchor points", so the default/False case - arrowhead at the LAST
    vertex, matching axis_of_advance's own already-confirmed-correct
    behaviour - is used). But Delay and Fix explicitly say "point 1 defines
    the tip of the arrowhead, point 2 defines the rear" - the opposite of
    the default - found only by reading that text carefully, not assumed
    from the shared shape. When True, the arrow is placed at FirstVertex
    with a 180-degree marker rotation on top of QgsMarkerLineSymbolLayer's
    own tangent-following rotation, so it points away from the rest of the
    line rather than back into it - the exact same rotation
    principal_direction_of_fire's own FirstVertex arrow already uses for
    the same reason.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        line_width
    )

    line_layer.setPenStyle(
        QgsSymbolLayerUtils.decodePenStyle(line_style)
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

    if tip_at_first_vertex:

        arrow_layer = _marker_line_layer(
            _arrow_marker_symbol(
                size=arrow_size, outline_width=arrow_outline_width, angle=180
            ),
            QgsTemplatedLineSymbolLayerBase.Placement.FirstVertex
        )

    else:

        arrow_layer = _marker_line_layer(
            _arrow_marker_symbol(size=arrow_size, outline_width=arrow_outline_width),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )

    symbol.appendSymbolLayer(
        arrow_layer
    )

    return symbol


def _circle_from_line_symbol(outline_style="solid", outline_width=0.4, with_ticks=False):

    """
    Several Mission Task (H.5.26) graphics - Isolate, Secure, Seize - and
    one Defensive maneuver control measure - Retain, H.5.12.1, NOT a
    Mission Task despite being commonly grouped with them, see
    _retain_symbol()'s own comment - are all defined by the standard as a
    circle: point 1 is the centre, point 2 is a point on the circle
    defining the radius. That is a 2-point LINE's own natural shape (draw
    from centre to edge), not a digitized polygon boundary, so this stays
    on the Lines layer: a QgsLineSymbol whose one symbol layer is a
    QgsGeometryGeneratorSymbolLayer computing
    buffer(start_point($geometry), distance(start_point($geometry),
    point_n($geometry, 2))) - a circle centred on the line's first vertex,
    with its radius taken from the distance to the SECOND vertex only
    (deliberately not length($geometry), which sums every segment - Seize
    digitizes a 3rd point for its own arrow via the same geometry, and
    using the whole line's length as the radius there inflated the circle
    by the extra segment's length; confirmed by rendering both the 2-point
    and 3-point cases side by side) - rendered with an ordinary unfilled
    QgsFillSymbol, the same "style": "no" outline-only recipe
    _objective_symbol()/_nai_symbol() already use. The standard's own
    circle has a 30-degree open arc (the friendly side); a full closed
    circle instead is a deliberate simplification, since QGIS has no
    simple "arc with a gap" primitive to build on here.

    `with_ticks` adds perpendicular tick marks around the whole
    circumference (Retain's own template shows exactly this - "the
    default tic length should be the same as the text height of the
    echelon field", the same tick convention Strong Point already uses on
    its own polygon boundary) - reusing that same "a nominally Fill
    symbol's layer(0) can be a plain line layer, with a QgsMarkerLineSymbolLayer
    appended for the ticks" trick, just applied to this generated circle
    instead of a digitized polygon.
    """

    fill_symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": outline_style,
            "outline_color": "0,0,0",
            "outline_width": str(outline_width),
        }
    )

    _apply_affiliation_color(
        fill_symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    if with_ticks:

        fill_symbol.appendSymbolLayer(
            _marker_line_layer(
                _tick_marker_symbol(),
                QgsTemplatedLineSymbolLayerBase.Placement.Interval,
                interval=4
            )
        )

    circle_layer = QgsGeometryGeneratorSymbolLayer.create({})

    circle_layer.setGeometryExpression(
        "buffer(start_point($geometry),"
        " distance(start_point($geometry), point_n($geometry, 2)))"
    )

    circle_layer.setSymbolType(
        Qgis.SymbolType.Fill
    )

    circle_layer.setSubSymbol(
        fill_symbol
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        circle_layer
    )

    return symbol


def _p1_p2_vertical_line_layer():

    """
    Block and Penetrate (H.5.26) are both a genuine 3-anchor-point shape:
    "Points 1 and 2 define the endpoints of the graphic's vertical line.
    Point 3 defines the endpoint of the [...] line, which will project
    perpendicularly from the MIDPOINT of the vertical line." An earlier
    version of both functions approximated this as an ordinary 2-point
    digitized line plus a small FIXED-size tick/arrow at its own
    CentralPoint - which ignored point 3 entirely, rendering a decorative
    mark instead of a real anchor-point-driven shape (caught by comparing
    a real render against the standard's own template diagram, which
    shows point 3 placed far from the vertical line, not adjacent to it).
    This helper renders just the P1-P2 segment (the "vertical line" - any
    length/orientation the user digitizes, not necessarily true vertical,
    same "the diagram's labels are illustrative, not compass directions"
    convention every other multi-anchor-point shape in this module
    already follows, e.g. principal_direction_of_fire). See
    _p3_to_midpoint_layer() for the P3 side.
    """

    layer = QgsGeometryGeneratorSymbolLayer.create({})

    layer.setGeometryExpression(
        "make_line(point_n($geometry, 1), point_n($geometry, 2))"
    )

    layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    line = QgsSimpleLineSymbolLayer()
    line.setColor(QColor(0, 0, 0))
    line.setWidth(0.4)

    _apply_affiliation_color(
        line,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    sub_symbol = QgsLineSymbol()

    sub_symbol.changeSymbolLayer(
        0,
        line
    )

    layer.setSubSymbol(
        sub_symbol
    )

    return layer


def _p3_to_midpoint_layer(sub_symbol):

    """
    The P3 side of Block/Penetrate's 3-anchor-point shape (see
    _p1_p2_vertical_line_layer() above) - a line from point 3 to the
    MIDPOINT of the P1-P2 segment, whose length is however far the user
    actually places point 3, not a fixed size. `sub_symbol` carries
    whatever is drawn along that segment: a plain line for Block, or a
    line ending in an arrowhead at the midpoint end for Penetrate (its
    own arrow points INTO the vertical line, matching "point 3 defines
    the REAR of the symbol" - point 3 is the arrow's tail).
    """

    layer = QgsGeometryGeneratorSymbolLayer.create({})

    layer.setGeometryExpression(
        "make_line(point_n($geometry, 3),"
        " centroid(make_line(point_n($geometry, 1), point_n($geometry, 2))))"
    )

    layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    layer.setSubSymbol(
        sub_symbol
    )

    return layer


def _bracket_symbol():

    """
    Breach (340200) and Canalize (340400) share one exact 3-anchor-point
    shape - confirmed identical by comparing their two template pictures
    side by side, not assumed from their similar-sounding text alone (the
    same "text alone doesn't prove two things are identical" caution this
    module already applies elsewhere, e.g. FLOT vs. phase_line). "Points 1
    and 2 define the endpoints of the symbol's opening and point 3 defines
    the rear of the symbol... the vertical line at the rear of the symbol
    will be the same height as the opening and parallel to it" - an open
    bracket/"C" shape: an earlier version of both functions approximated
    this as a plain 2-point dashed line with a decorative tick, dropping
    the opening/rear-line structure entirely (the same class of mistake as
    Block's own earlier version - a fixed decorative mark standing in for
    a real anchor-point-driven shape).

    Reconstructed as ONE continuous 5-point path -
    P1 -> rear-top -> P3 -> rear-bottom -> P2 - where the rear corners are
    computed from P3 (the rear's own position) offset by half of P1-P2's
    own length, along P1-P2's own direction (so the rear segment really is
    "the same height as the opening and parallel to it", for whatever
    height/orientation the user's own P1/P2 happen to give it). QGIS has
    no vector/perpendicular-offset expression function directly, but
    `project(point, distance, azimuth)` plus `azimuth(point1, point2)`
    together do the same job, chained through `with_variable()` so the
    height/azimuth are each computed once rather than repeated in every
    branch of the expression.
    """

    layer = QgsGeometryGeneratorSymbolLayer.create({})

    layer.setGeometryExpression(
        "with_variable('h',"
        " distance(point_n($geometry, 1), point_n($geometry, 2)),"
        " with_variable('az',"
        " azimuth(point_n($geometry, 1), point_n($geometry, 2)),"
        " make_line("
        "  point_n($geometry, 1),"
        "  project(point_n($geometry, 3), @h / 2, @az + pi()),"
        "  point_n($geometry, 3),"
        "  project(point_n($geometry, 3), @h / 2, @az),"
        "  point_n($geometry, 2)"
        " )))"
    )

    layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    line = QgsSimpleLineSymbolLayer()
    line.setColor(QColor(0, 0, 0))
    line.setWidth(0.4)

    _apply_affiliation_color(
        line,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    sub_symbol = QgsLineSymbol()

    sub_symbol.changeSymbolLayer(
        0,
        line
    )

    layer.setSubSymbol(
        sub_symbol
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        layer
    )

    return symbol


# --- H.5.11 Maneuver Control Measure Symbols (Table H-VII) ---------------

def _forward_line_of_troops_symbol():

    # Code 140100/140101. The extracted DRAW RULES text gives FLOT no
    # distinguishing line style beyond "requires at least two points... to
    # define the line" - which reads like a plain line, and an earlier
    # version of this function rendered exactly that. The template
    # PICTURE (page 410, "Friendly Present") shows otherwise: a real
    # serpentine/wave line, not a straight one - only caught by rendering
    # the actual page image, this module's own recurring lesson that text
    # alone is not enough. See _wavy_line_layers()'s own comment for the
    # technique.
    return _wavy_line_symbol()


def _line_of_contact_symbol():

    # Code 140200. "The line of contact symbol is created when both the
    # friendly and enemy forward line of troops symbols are displayed" -
    # the template page (412) shows this literally: two parallel wavy FLOT
    # lines (see _wavy_line_layers()'s own comment - an earlier version of
    # this function used two plain offset straight lines instead, the same
    # "text alone doesn't show the wave" gap FLOT itself had). Approximated
    # as two wavy lines offset to either side, rather than actually
    # rendering a second, independently coloured enemy FLOT underneath
    # (this layer's "affiliation" field is one value per feature, not two)
    # - the template's own small connecting "hook" marks between the two
    # lines and its circled coordination-point markers are not attempted.
    symbol = QgsLineSymbol()

    near_layers = _wavy_line_layers(offset=3)
    far_layers = _wavy_line_layers(offset=-3)

    symbol.changeSymbolLayer(
        0,
        near_layers[0]
    )

    for layer in (near_layers[1], far_layers[0], far_layers[1]):

        symbol.appendSymbolLayer(
            layer
        )

    return symbol


def _forward_edge_of_battle_area_symbol():

    # Code 140400. The template page (413) shows a distinctive shape - a
    # small triangular peak in the middle of the line, labelled PT1 (left
    # baseline end), PT2 (the peak), PT3 (right baseline end) - which reads
    # like it needs special construction, but doesn't: it's simply the raw
    # 3-vertex path P1->P2->P3, exactly the same "additional points can be
    # defined to extend the line" convention Phase Line/FLOT already
    # support, with point 2 placed above the P1-P3 baseline. Confirmed by
    # rendering a real 3-vertex feature through this exact plain-line
    # symbol - no geometry-generator or other special-case code was
    # needed, only checking whether one was before assuming so. The line
    # itself is rendered slightly heavier (0.6mm vs FLOT/phase_line's
    # 0.4mm) purely so the visually-similar line types can be told apart
    # on screen at a glance, not because the standard specifies a
    # different weight.
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.6",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


def _principal_direction_of_fire_symbol():

    # Code 140500. "This symbol requires three anchor points. Point 1
    # defines the vertex of the symbol. Points 2 and 3 define the tips of
    # the arrowheads" - two rays diverging from a shared vertex.
    # Approximated as a single 3-vertex line digitized tip-vertex-tip
    # (point order: arrow tip, shared vertex, other arrow tip - NOT the
    # standard's own point-1-is-the-vertex numbering, a necessary
    # deviation since a single LineString path can't branch the way two
    # true diverging rays from one point would need to), with an
    # arrowhead at each end: LastVertex uses the default (unrotated)
    # arrow, pointing away from the vertex in the drawn direction, and
    # FirstVertex uses a 180-degree-rotated arrow so it also points away
    # from the vertex rather than back into it. This rotation reasoning
    # follows directly from how axis_of_advance's own LastVertex arrow is
    # already confirmed (via that measure type's own manual smoke test)
    # to point in the drawn direction of travel - it has NOT itself been
    # confirmed with a live render, so is worth double-checking in the
    # project maintainer's own smoke test of this sub-phase.
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "0,0,0",
            "line_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol.appendSymbolLayer(
        _marker_line_layer(
            _arrow_marker_symbol(),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )
    )

    symbol.appendSymbolLayer(
        _marker_line_layer(
            _arrow_marker_symbol(angle=180),
            QgsTemplatedLineSymbolLayerBase.Placement.FirstVertex
        )
    )

    return symbol


# --- H.5.13.2 Direction of attack (Table H-XI) ----------------------------

def _direction_of_attack_symbol():

    # Code 140600 (the base "Direction of Attack" entry is itself N/A in
    # the standard's own table - a category header; the real shape comes
    # from its Friendly Aviation/Main Attack/Supporting Attack
    # sub-variants at 140601-140607, all of which reduce to "a plain line
    # with a single arrowhead", differentiated from each other only by an
    # amplifier bracket - e.g. [A], [R] - prefixed to the label, which
    # this module doesn't attempt). Rendered thinner (0.35mm) than
    # axis_of_advance's approximation (0.5mm line + separately-sized
    # arrow) so the two read as different weights of arrow, since
    # axis_of_advance is meant to approximate a wide arrow *band* while
    # this is meant to approximate a plain arrow *line*.
    return _arrow_line_symbol(line_width=0.35, arrow_size=4, arrow_outline_width=0.8)


# --- H.5.12.1 Defensive maneuver - Areas (Table H-VIII) -------------------

def _battle_position_symbol():

    # Code 151200. "A defensive location oriented on a likely enemy
    # avenue of approach" - an unfilled outline, same recipe as
    # _objective_symbol(), since the standard's own draw rule here is
    # generic anchor-point/size-shape boilerplate with no further
    # distinguishing stroke detail beyond "the side opposite Field B
    # (Echelon) faces toward the hostile force" (an orientation rule for
    # where the echelon amplifier goes, not a shape difference - this
    # layer has no echelon field, see this module's own docstring).
    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,0,0",
            "outline_width": "0.5",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


def _strong_point_symbol():

    # Code 151203. "The default tic length should be the same as the
    # text height of the echelon field... spacing between the tics
    # should also be the height of B" - a fortified outline with regular
    # perpendicular tick marks. This layer has no echelon field to size
    # ticks from (see this module's own docstring), so a thin continuous
    # outline plus fixed-size/fixed-interval perpendicular ticks
    # (_tick_marker_symbol() at a 4mm Interval) stands in for the
    # standard's own dynamically-sized fortification texture.
    outline_layer = QgsSimpleLineSymbolLayer()
    outline_layer.setColor(QColor(0, 0, 0))
    outline_layer.setWidth(0.35)

    _apply_affiliation_color(
        outline_layer,
        [QgsSymbolLayer.Property.StrokeColor]
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

    symbol.appendSymbolLayer(
        _marker_line_layer(
            _tick_marker_symbol(),
            QgsTemplatedLineSymbolLayerBase.Placement.Interval,
            interval=4
        )
    )

    return symbol


def _engagement_area_symbol():

    # Code 151300. "An area where the commander intends to contain and
    # destroy an enemy force" - the template page (424) shows a plain
    # SOLID outline, no dash pattern at all. An earlier version of this
    # function gave it an invented "dash dot" style to keep it visually
    # distinct from NAI on screen - but the standard doesn't use dash
    # style to distinguish area TYPES from each other at all (it reserves
    # dash for a "planned/on-order" STATUS variant of the same area type,
    # e.g. Battle Position/Assembly Area's own Present-vs-Planned pair,
    # which this layer has no status field to represent) - confirmed by
    # checking the actual template picture, not assumed from wanting two
    # area types to look different.
    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,0,0",
            "outline_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


# --- H.5.11 Maneuver Areas (Table H-VII) ----------------------------------

def _assembly_area_symbol():

    # Code 150200. "An area in which a command is assembled preparatory
    # to further action" - the template page (415) shows a plain SOLID
    # outline ("Friendly Present" - the dashed variant shown right below
    # it is a separate, unimplemented "Planned/On Order" status this
    # layer has no field for). An earlier version of this function used an
    # invented "dash dot dot" style to keep it visually distinct from NAI/
    # Engagement Area on screen - see _engagement_area_symbol()'s own
    # comment for why that reasoning doesn't hold up against the actual
    # template picture.
    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "solid",
            "outline_color": "0,0,0",
            "outline_width": "0.4",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


# --- H.5.14 Maneuver control measure symbols (Table H-XII) ---------------

def _encirclement_symbol():

    # Code 151800 (base entry, N/A in the standard's own table; the real
    # polygon shape comes from the Friendly/Enemy sub-variants at
    # 151801/151802 - both a plain closed area with no further
    # distinguishing stroke detail given). "The loss of freedom of
    # maneuver resulting from enemy control of all ground routes of
    # evacuation and reinforcement" - rendered with a dotted outline
    # (distinct from every other dashed-outline area type here) as an
    # arbitrary but clearly-documented visual choice, evoking a
    # tightening ring, since the standard's own text gives nothing more
    # specific to render than "a closed area".
    symbol = QgsFillSymbol.createSimple(
        {
            "style": "no",
            "outline_style": "dot",
            "outline_color": "0,0,0",
            "outline_width": "0.5",
        }
    )

    _apply_affiliation_color(
        symbol.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    return symbol


# --- H.5.12.1 Defensive maneuver (Table H-VIII), NOT a Mission Task ------

def _retain_symbol():

    # Code 151205. Despite being named alongside the H.5.26 Mission Task
    # symbols in this sub-phase's own request, "Retain" is actually
    # defined under H.5.12.1 Defensive maneuver, not Table H-XXIV Mission
    # Task Symbols - confirmed by reading the standard's own text, not
    # assumed from the name (see this module's own docstring for the
    # "Disengage"/"Contain" findings from the same check). "Point 1
    # defines the center point of the graphic and point 2 defines the
    # graphic's start point and radius... The opening will be a 30-degree
    # arc of the circle" - the same centre+radius circle shape as the
    # H.5.26 Isolate/Secure/Seize graphics below, so it reuses
    # _circle_from_line_symbol(). The template page's own picture (423)
    # shows the circle bristling with perpendicular tick marks all around
    # it (matching the text: "the default tic length should be the same
    # as the text height of the echelon field") - an earlier version of
    # this function used an invented "dash dot" outline instead, which
    # doesn't match the picture at all.
    return _circle_from_line_symbol(outline_width=0.4, with_ticks=True)


# --- H.5.26 Mission Task Symbols (Table H-XXIV) ---------------------------

def _block_symbol():

    # Code 340100. "Points 1 and 2 define the endpoints of the graphic's
    # vertical line. Point 3 defines the endpoint of the graphic's
    # horizontal line, which will project perpendicularly from the
    # MIDPOINT of the vertical line" - a genuine 3-anchor-point shape (see
    # _p1_p2_vertical_line_layer()'s own comment for why an earlier
    # 2-point-plus-fixed-tick version of this function was wrong, not
    # just approximate). Requires a 3-vertex digitized line (P1, P2, P3,
    # in that order) - with only 2 vertices, point_n($geometry, 3)
    # resolves to NULL and the horizontal line simply doesn't render,
    # degrading to a plain P1-P2 line rather than erroring.
    plain_line = QgsSimpleLineSymbolLayer()
    plain_line.setColor(QColor(0, 0, 0))
    plain_line.setWidth(0.4)

    _apply_affiliation_color(
        plain_line,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    horizontal_sub_symbol = QgsLineSymbol()

    horizontal_sub_symbol.changeSymbolLayer(
        0,
        plain_line
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        _p1_p2_vertical_line_layer()
    )

    symbol.appendSymbolLayer(
        _p3_to_midpoint_layer(horizontal_sub_symbol)
    )

    return symbol


def _breach_symbol():

    # Code 340200. "Points 1 and 2 define the endpoints of the symbol's
    # opening and point 3 defines the rear of the symbol... The vertical
    # line at the rear of the symbol will be the same height as the
    # opening and parallel to it" - a real open bracket/"C" shape,
    # confirmed identical to Canalize's own template picture. An earlier
    # version of this function dropped that shape entirely (a plain dashed
    # 2-point line with a decorative tick standing in for it) - see
    # _bracket_symbol()'s own comment for the real construction and why it
    # was wrong.
    return _bracket_symbol()


def _canalize_symbol():

    # Code 340400. Same exact bracket shape as Breach above - see
    # _bracket_symbol()'s own comment. Confirmed identical (not merely
    # similar-sounding text) by comparing both control measures' template
    # pictures side by side; kept as its own measure_type/rule despite
    # sharing Breach's exact rendering recipe, the same reason
    # delay/withdraw are kept separate despite an identical shape.
    return _bracket_symbol()


def _disrupt_symbol():

    # Code 341000. "Points 1 and 2 define the endpoints of the graphic's
    # vertical line. Point 3 defines the tip of the longest arrow... The
    # arrows are perpendicular to the baseline (vertical line) and
    # parallel to each other" - a baseline with a row of perpendicular
    # arrows. Approximated as the baseline plus repeated perpendicular
    # ticks along its length (QgsTemplatedLineSymbolLayerBase.Placement.
    # Interval), standing in for the row of arrows without attempting
    # each one's own increasing length.
    line_layer = QgsSimpleLineSymbolLayer()
    line_layer.setColor(QColor(0, 0, 0))
    line_layer.setWidth(0.4)

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    symbol.appendSymbolLayer(
        _marker_line_layer(
            _tick_marker_symbol(size=3, outline_width=0.5),
            QgsTemplatedLineSymbolLayerBase.Placement.Interval,
            interval=3
        )
    )

    return symbol


def _fix_symbol():

    # Code 341100. "This graphic requires 2 anchor points. Point 1 defines
    # the tip of the arrowhead, and point 2 defines the rear of the
    # graphic" - explicit, and the OPPOSITE of this module's own default
    # arrow-line convention (last vertex = tip, matching axis_of_advance's
    # already-confirmed-correct behaviour) - found only by reading this
    # text carefully, a real bug in the first version of this function
    # which put the tip at point 2 instead. Rendered dashed purely so it
    # stays visually distinguishable on screen from direction_of_attack's
    # own solid arrow (both being, per their own text, otherwise the same
    # shape) - not because the standard specifies a dashed style.
    return _arrow_line_symbol(
        line_width=0.3, line_style="dash", arrow_size=3, arrow_outline_width=0.7,
        tip_at_first_vertex=True
    )


def _penetrate_symbol():

    # Code 341800. "Points 1 and 2 define the endpoints of the symbol's
    # vertical line. Point 3 defines the rear of the symbol... The arrow
    # will project perpendicularly from the midpoint of the vertical
    # line" - the same genuine 3-anchor-point shape as Block above (see
    # _p1_p2_vertical_line_layer()'s own comment), except the P3-side
    # segment ends in an arrowhead at the midpoint end rather than a
    # plain line: point 3 is "the rear of the symbol" (the arrow's tail),
    # so the arrow points FROM point 3 INTO the vertical line, matching
    # Penetrate's own meaning of piercing through a position. The default
    # (unrotated) arrow marker already points in the drawn direction of
    # travel - from P3 toward the midpoint here - so no extra angle is
    # needed, unlike this module's other perpendicular-tick uses.
    shaft_line = QgsSimpleLineSymbolLayer()
    shaft_line.setColor(QColor(0, 0, 0))
    shaft_line.setWidth(0.4)

    _apply_affiliation_color(
        shaft_line,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    arrow_sub_symbol = QgsLineSymbol()

    arrow_sub_symbol.changeSymbolLayer(
        0,
        shaft_line
    )

    arrow_sub_symbol.appendSymbolLayer(
        _marker_line_layer(
            _arrow_marker_symbol(size=4, outline_width=0.7),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )
    )

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        _p1_p2_vertical_line_layer()
    )

    symbol.appendSymbolLayer(
        _p3_to_midpoint_layer(arrow_sub_symbol)
    )

    return symbol


def _delay_symbol():

    # Code 340800. "Point 1 defines the tip of the arrowhead. Point 2
    # defines the end of the straight line portion of the symbol. Point 3
    # defines the diameter and orientation of the 180 degree circular
    # arc" - an arrow with a perpendicular semicircular arc at its base.
    # Point 1 = tip is explicit and, like Fix, the opposite of this
    # module's own default arrow-line convention - the first version of
    # this function put the tip at point 2 instead, a real bug. The arc
    # detail is dropped entirely (approximated as a plain arrow line), the
    # same "recognisable core shape only" simplification this module
    # already applies to axis_of_advance's own wide-band shape - see
    # _withdraw_symbol()'s own comment for why it shares this exact same
    # approximation and is kept as a separate measure_type anyway.
    return _arrow_line_symbol(
        line_width=0.4, arrow_size=4, arrow_outline_width=0.8,
        tip_at_first_vertex=True
    )


def _withdraw_symbol():

    # Code 342400. Its own draw rule text is close to verbatim identical
    # to Delay's above (arrowhead + straight line + perpendicular 180-
    # degree arc) - the standard differentiates Withdraw from Delay (and
    # from the not-implemented Retire/Retirement and Withdraw Under
    # Pressure, which share the same family again) mainly by name/context
    # rather than a different drawn shape, the same situation already
    # documented for forward_line_of_troops vs. phase_line. Kept as its
    # own measure_type/rule despite sharing _delay_symbol()'s exact
    # rendering recipe, for the same reason FLOT is kept separate from
    # Phase Line - including the same point-1-is-the-tip fix.
    return _arrow_line_symbol(
        line_width=0.4, arrow_size=4, arrow_outline_width=0.8,
        tip_at_first_vertex=True
    )


def _isolate_symbol():

    # Code 341500. "Point 1 defines the center point of the symbol and
    # point 2 defines the symbol's start point and radius... The opening
    # will be a 30 degree arc of the circle" - see
    # _circle_from_line_symbol()'s own comment for the centre+radius/
    # full-circle approximation this and the other circle-shaped Mission
    # Tasks below share. Dashed outline, distinguishing it from Secure's
    # solid one.
    return _circle_from_line_symbol(outline_style="dash", outline_width=0.4)


def _secure_symbol():

    # Code 342100. Same centre+radius/30-degree-opening shape as Isolate
    # above, rendered with a solid outline instead of Isolate's dashed
    # one as the one visual difference between the two.
    return _circle_from_line_symbol(outline_style="solid", outline_width=0.4)


def _seize_symbol():

    # Code 342300. The standard actually defines TWO different point
    # recipes, not one "3-or-4-point variant" as an earlier version of
    # this comment assumed - reading the full text (not just the "point 4
    # defines the end of the arrow" fragment) matters here:
    #   - Where FOUR points are available: point 1 = circle centre, point 2
    #     = circle radius, point 3 = curvature of the connecting arc, point
    #     4 = end of the arrow.
    #   - Where THREE points are available: point 1 = circle centre, point
    #     2 = the tip of the arrowhead DIRECTLY (no radius role at all),
    #     point 3 = which side a 90-degree arc sits on. The circle's size
    #     isn't derived from any point in this recipe - it's auto-sized
    #     "large enough to accommodate a tactical symbol".
    # These two recipes assign completely different meanings to point 2 -
    # radius in one, arrowhead tip in the other - so a 3-point input can't
    # be safely reinterpreted as a trimmed-down 4-point one (an earlier
    # version of this function effectively did exactly that, appending an
    # arrow at whatever the digitized line's own last vertex happened to
    # be). Rather than guess which recipe a given point count means, this
    # only implements the 4-point recipe explicitly - centre/radius from
    # points 1-2 (via _circle_from_line_symbol(), already shared with
    # Isolate/Secure/Retain) plus an arrow from point 2's own position on
    # the circle's edge to point 4 - and drops the arc-curvature detail of
    # point 3 (the same "recognisable core shape only" simplification this
    # module already applies elsewhere). With only 2 or 3 points, only the
    # plain circle renders - no arrow - rather than rendering one in a
    # position the standard doesn't actually specify for that point count.
    symbol = _circle_from_line_symbol(outline_style="solid", outline_width=0.4)

    shaft_line = QgsSimpleLineSymbolLayer()
    shaft_line.setColor(QColor(0, 0, 0))
    shaft_line.setWidth(0.4)

    _apply_affiliation_color(
        shaft_line,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    arrow_shaft = QgsLineSymbol()

    arrow_shaft.changeSymbolLayer(
        0,
        shaft_line
    )

    arrow_shaft.appendSymbolLayer(
        _marker_line_layer(
            _arrow_marker_symbol(size=3.5, outline_width=0.7),
            QgsTemplatedLineSymbolLayerBase.Placement.LastVertex
        )
    )

    arrow_layer = QgsGeometryGeneratorSymbolLayer.create({})

    arrow_layer.setGeometryExpression(
        "make_line(point_n($geometry, 2), point_n($geometry, 4))"
    )

    arrow_layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    arrow_layer.setSubSymbol(
        arrow_shaft
    )

    symbol.appendSymbolLayer(
        arrow_layer
    )

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "phase_line": _phase_line_symbol,
    "boundary": _boundary_symbol,
    "axis_of_advance": _axis_of_advance_symbol,
    "forward_line_of_troops": _forward_line_of_troops_symbol,
    "line_of_contact": _line_of_contact_symbol,
    "forward_edge_of_battle_area": _forward_edge_of_battle_area_symbol,
    "principal_direction_of_fire": _principal_direction_of_fire_symbol,
    "direction_of_attack": _direction_of_attack_symbol,
    "retain": _retain_symbol,
    "block": _block_symbol,
    "breach": _breach_symbol,
    "canalize": _canalize_symbol,
    "disrupt": _disrupt_symbol,
    "fix": _fix_symbol,
    "penetrate": _penetrate_symbol,
    "delay": _delay_symbol,
    "withdraw": _withdraw_symbol,
    "isolate": _isolate_symbol,
    "secure": _secure_symbol,
    "seize": _seize_symbol,
}

_AREA_SYMBOL_BUILDERS = {
    "objective": _objective_symbol,
    "nai": _nai_symbol,
    "battle_position": _battle_position_symbol,
    "strong_point": _strong_point_symbol,
    "engagement_area": _engagement_area_symbol,
    "assembly_area": _assembly_area_symbol,
    "encirclement": _encirclement_symbol,
}


def _build_rule_based_renderer(root_symbol, symbol_builders):

    root_rule = QgsRuleBasedRenderer.Rule(None)

    for measure_type, build_symbol in symbol_builders.items():

        rule = QgsRuleBasedRenderer.Rule(
            build_symbol()
        )

        rule.setFilterExpression(
            f'"measure_type" = \'{measure_type}\''
        )

        rule.setLabel(
            measure_type
        )

        root_rule.appendChild(
            rule
        )

    return QgsRuleBasedRenderer(root_rule)


def _configure_affiliation_field(layer):

    """
    Shared by both layers - a "Friend"/"Hostile"/"Neutral"/"Unknown"
    ValueMap dropdown driving _AFFILIATION_COLOR_EXPRESSION, defaulting
    to DEFAULT_AFFILIATION ("unknown", which renders black - "black as
    standard" per the user's own scoping of this feature).
    """

    affiliation_idx = layer.fields().indexOf("affiliation")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AFFILIATION_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        affiliation_idx,
        QgsDefaultValue(f"'{DEFAULT_AFFILIATION}'")
    )


def _configure_designation_labeling(layer, placement):

    settings = QgsPalLayerSettings()

    settings.fieldName = "unique_designation"

    settings.placement = placement

    settings.setFormat(
        build_text_format(LABEL_FONT_SIZE)
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(settings)
    )

    layer.setLabelsEnabled(
        True
    )


def create_control_measures_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for phase lines/boundaries/axis of
    advance - a "measure_type" ValueMap dropdown plus a
    "unique_designation" text field, labelled along each line. Digitized
    with QGIS's own native "Add Line Feature" tool - see this module's
    own docstring and unit_layer.py's for why no custom drawing tool
    exists.
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
        QgsDefaultValue("'phase_line'")
    )

    _configure_affiliation_field(layer)

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
        Qgis.LabelPlacement.Line
    )

    return layer


def create_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for objectives/NAIs - same shape as
    create_control_measures_lines_layer(), for area-type measures.
    Digitized with QGIS's own native "Add Polygon Feature" tool.
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
        QgsDefaultValue("'objective'")
    )

    _configure_affiliation_field(layer)

    # applyOnUpdate=True - see create_control_measures_lines_layer()'s
    # own comment on length_km for why, and
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

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.OverPoint
    )

    return layer


def default_insert_position(project, layer):

    """
    Top of the layer tree - matches unit_layer.py's own convention for
    an operational overlay meant to sit above whatever base terrain
    rendering is underneath.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


def _add_layer_if_absent(iface, name, create_layer):

    """
    Shared guard for both add_control_measures_lines_layer()/
    add_control_measures_areas_layer() - see unit_layer.py's own
    add_unit_layer() for why a control-measures layer must never be
    silently replaced the way a generate_*() layer would be: its
    content is hand-drawn operational data, not derived from a DEM/AO,
    so a second click must warn rather than risk destroying it.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(name):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'A "{name}" layer already exists - use the Layers panel '
            "to work with it, or rename it first if you want a second "
            "one."
        )

        return None

    layer = create_layer()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )


def add_control_measures_lines_layer(iface):

    return _add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_control_measures_lines_layer
    )


def add_control_measures_areas_layer(iface):

    return _add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_control_measures_areas_layer
    )
