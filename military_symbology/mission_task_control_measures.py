# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.26 (Table H-XXIV, "Mission Task Symbols") -
Mini-Phase H21. Printed pages 636-655, 29 code rows.

**Two layers: Points and Lines.** Destroy (340900), Interdict (341400)
and Neutralize (341600) are the table's three POINT symbols - one
anchor point each, milsymbol-rendered. Thirteen LINE tasks followed on
2026-08-15/16: Block, Disrupt, Fix, Secure, Occupy, Penetrate, Seize,
Isolate, Delay, Retire, Withdraw, Withdraw Under Pressure and Bypass.
Everything still unbuilt is listed by code in TABLE_H_XXIV_REMAINING.

**milsymbol has an icon for the three points and for nothing else in
this table** - verified entry by entry against its own
src/numbersidc/sidc/control-measure.js. Every line task here is
hand-built QGIS symbology, and most of them are an existing
construction from another table reused whole (see the LINES section).

**All three are RELOCATED, not new.** They already existed in sidc.py
as destroy_point/interdict_point/neutralize_point and were offered on
the shared control_measure_points.py layer. Moving them here empties
that layer's last three entries; it is retired with this mini-phase.

**Do not confuse these with the same task names elsewhere in Appendix
H.** Several mission tasks share a name with an obstacle-effect or
maneuver control measure that has its OWN, different code and its own
drawn form - Block, Breach, Bypass, Canalize, Disrupt, Fix, Penetrate,
Seize and Withdraw all appear both here and in Tables H-VII/H-XIX.
Conflating the two is a defect this project has already been reported
for once (see docs/roadmap.md's own Phase 10 entry), so both records -
built and unbuilt - are keyed by CODE rather than by name alone.

Military Cartography Tools
"""

from ._control_measure_shared import (
    LABEL_FONT_SIZE,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
)

from ._point_symbol_layer import (
    DEFAULT_MARKER_SIZE_MM,
    build_single_domain_point_layer,
)

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMapUnitScale,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSymbol,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from qgis.PyQt.QtGui import QColor


POINTS_LAYER_NAME = "Mission Task Points"

POINT_ENTITY_LABELS = {
    "destroy_point": "Destroy",
    "interdict_point": "Interdict",
    "neutralize_point": "Neutralize",
}

POINT_ENTITY_CODES = {
    "destroy_point": "340900",
    "interdict_point": "341400",
    "neutralize_point": "341600",
}

# **All three draw smaller than the box-shaped points on the other
# Appendix H layers, and that is milsymbol's bounding boxes, not this
# module.**
#
# Each of these icons is a wide, low pair of crossed lines whose
# declared box is 208x128 - the widest in the whole control-measure
# set. QGIS sizes an SVG marker by its WIDTH, so at one marker size
# they render at 8/208 mm per icon unit against a supply point's
# 8/88: about 42% of the scale, and visibly small beside them.
#
# Their number: 30%, asked for directly and matching the bump Table
# H-XXI's own events got for the same reason ("mission task points -
# increase size by 30% like cbrn events"). Worth being plain that this
# is a legibility call rather than a normalisation - closing the gap to
# the supply points outright would be 208/88, about 136% - so it stays
# the maintainer's to revisit. See cbrn_defense.py, which carries the
# same note.
_MISSION_TASK_MARKER_SIZE_SCALE = 1.30

POINT_MARKER_SIZE_SCALES = {
    entity: _MISSION_TASK_MARKER_SIZE_SCALE for entity in POINT_ENTITY_CODES
}

# --- Audited, NOT built. ---
#
# What is left of Table H-XXIV. 340000 is the section's own parent
# entry, with TEMPLATE and EXAMPLE both reading "N/A", so it will never
# be built.
#
# Every one is a multi-anchor construction rather than a centred glyph,
# and none has a milsymbol icon. Roughly three families:
#
# - Arrow tasks - N anchor points, PT1 at the arrowhead's tip, working
#   back to the rear. Counterattack's own draw rules allow N between 3
#   and 50, which is the reason none of these is a Delay in disguise:
#   the shape is not fixed by the anchor count.
# - Bracket/effect tasks - the shapes Table H-XIX's own obstacle
#   effects already build here, under DIFFERENT codes. See the module
#   docstring: these are not the same symbols.
# - Security tasks (342200 and its three variants) - Cover, Guard and
#   Screen are sub-codes of Security, drawn as an open bracket along
#   the screened front.
#
# **Check each of these against Table H-XIX before building it.** This
# list was annotated "nothing left shares a shape with anything already
# built" once, and Bypass (340300) was Obstacle Bypass Easy (270601)
# whole - two arrows, a joining line, one added letter. The rest look
# like their own geometry, but that has been wrong before.
TABLE_H_XXIV_REMAINING = {
    "340000": "Mission Tasks (section parent; TEMPLATE and EXAMPLE "
              "both N/A)",
    "340200": "Breach",
    "340400": "Canalize",
    "340500": "Clear",
    "340600": "Counterattack",
    "340700": "Counterattack by Fire",
    "341200": "Follow and Assume",
    "341300": "Follow and Support",
    "341900": "Relief in Place (RIP)",
    "342200": "Security",
    "342201": "Security - Cover",
    "342202": "Security - Guard",
    "342203": "Security - Screen",
}


def create_mission_task_points_layer(name=POINTS_LAYER_NAME):

    """Table H-XXIV's own three point symbols, milsymbol-rendered."""

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "destroy_point",
        include_echelon=False,
        include_headquarters=False,
        entity_marker_size_scales=POINT_MARKER_SIZE_SCALES,
    )


def add_mission_task_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_mission_task_points_layer,
    )


# ============================================================
# Mission task LINES
# ============================================================
#
# **Everything in Table H-XXIV lives on a Mission Tasks layer** - point,
# line or area - at the maintainer's own instruction, 2026-08-15. This
# is the line half.
#
# **Block, Disrupt and Fix are the three that share a name with a
# symbol already built here**, and they were held back until the
# maintainer gave explicit instructions for them. Those instructions,
# in their own words:
#
#   Block   - same as 270501, default colour BLACK not green, letter B
#             (masked) on the horizontal shaft.
#   Disrupt - same as 270502 but VERTICALLY MIRRORED (longest arrow at
#             the bottom, shortest at the top), black, letter D
#             (masked) on the central arrow's shaft, halfway from the
#             base line to the arrowhead tip.
#   Fix     - same as 270503, black, letter F on the shaft (lengthened
#             accordingly) before the wavy pattern begins - the initial
#             segment, close to PT2.
#
#   "Construction mechanism for user for all three remains same as
#   270501/2/3" - the same three anchor points, clicked the same way.
#
# So these reuse Table H-XIX's own geometry functions rather than
# reimplementing them. The obstacle versions are untouched: every new
# behaviour reaches them as an OPTIONAL argument that defaults to the
# old one.
LINES_LAYER_NAME = "Mission Task Lines"

LINE_MEASURE_TYPE_LABELS = {
    "block": "Block",
    "disrupt": "Disrupt",
    "fix": "Fix",
    "secure": "Secure",
    "occupy": "Occupy",
    "penetrate": "Penetrate",
    "seize": "Seize",
    "isolate": "Isolate",
    "delay": "Delay",
    "retire": "Retire/Retirement",
    "withdraw": "Withdraw",
    "withdraw_under_pressure": "Withdraw Under Pressure",
    "bypass": "Bypass",
}

LINE_MEASURE_TYPE_CODES = {
    "block": "340100",
    "disrupt": "341000",
    "fix": "341100",
    "secure": "342100",
    "occupy": "341700",
    "penetrate": "341800",
    "seize": "342300",
    "isolate": "341500",
    "delay": "340800",
    "retire": "342000",
    "withdraw": "342400",
    "withdraw_under_pressure": "342500",
    "bypass": "340300",
}


# The letter each one carries, set into its own shaft. **Not every
# line task has one** - Seize is built from a circle, a curve and an
# arrowhead, with no letter in the maintainer's own instruction for it
# - so this is deliberately not keyed by every measure type, and the
# label rules below are built only for the types that appear here.
LINE_LETTERS = {
    "block": "B",
    "disrupt": "D",
    "fix": "F",
    "secure": "S",
    "occupy": "O",
    "penetrate": "P",
    "seize": "S",
    "isolate": "I",
    "delay": "D",
    "retire": "R",
    "withdraw": "W",
    "withdraw_under_pressure": "WP",
    "bypass": "B",
}

# **Four rows, ONE construction** - Delay and the three withdrawal
# tasks are the same three-point shape with a different letter in the
# shaft, at the maintainer's own instruction: "Retire, Withdraw,
# withdraw under pressure - all same as delay; only change being use
# letter R for retire, W for withdraw and WP for withdraw under
# pressure". The standard agrees: their draw rules are word for word
# each other's.
#
# Kept as one tuple rather than four branches so a change to the shape
# cannot reach one of them and miss the others.
DELAY_CONSTRUCTION_MEASURE_TYPES = (
    "delay",
    "retire",
    "withdraw",
    "withdraw_under_pressure",
)

_LINE_WIDTH_MM = 0.4

# The same head Table H-XIX's own Disrupt uses.
_ARROWHEAD_SIZE_MM = 6

# Bypass's own heads scale with the arrows they sit on, capped at that
# size - the same quarter-of-the-arrow Table H-XIX's own 270601 uses,
# so the two symbols keep drawing alike.
_BYPASS_ARROWHEAD_ARROW_FRACTION = 0.25

# **Occupy's cross scales with its own circle.** Fixed, it swamped a
# small Occupy and vanished on a large one - the maintainer's own
# report: "the size is fixed irrespective of the circle's radius -
# let's make the cross 1/5 of the radius subject to max size which is
# the current size". So a fifth of the radius, capped at the plain
# arrowhead's own size and never larger.
_OCCUPY_CROSS_RADIUS_FRACTION = 5.0

# **Penetrate's head scales the same way, and the fraction is measured
# from the manual.** On Table H-XXIV's own template the chevron spans
# about a fifth of the stem it sits on - the same ratio Occupy's cross
# uses, which is a coincidence worth noting rather than a shared rule.
# Capped at 7 mm, the maintainer's own ceiling.
#
# This IS a pixel measurement off the printed template, which this
# project normally distrusts - the draw rules give no number. Asked for
# directly ("get a measurement from the manual - for dimension check"),
# and it only sets a proportion, with the cap doing the real work.
# **Seize's own circle, at PT1.** "Keep the radius 1.5 times that of a
# standard milsymbol (say friend - infantry)" - a point marker on this
# plugin's own layers is DEFAULT_MARKER_SIZE_MM across, so its radius is
# half that, and this is one and a half of those.
#
# A page unit, deliberately: it is a symbol, not a piece of ground, and
# the maintainer pinned it to another page-sized symbol.
_SEIZE_CIRCLE_RADIUS_MM = 1.5 * DEFAULT_MARKER_SIZE_MM / 2.0

_PENETRATE_HEAD_STEM_FRACTION = 5.0
_PENETRATE_HEAD_MAX_MM = 7.0

_PENETRATE_HEAD_SIZE_EXPRESSION = (
    "min({maximum}, coalesce(mct_block_stem_mm(geometry(@feature),"
    " @map_extent, @map_scale), 0) / {fraction})"
).format(
    maximum=_PENETRATE_HEAD_MAX_MM,
    fraction=_PENETRATE_HEAD_STEM_FRACTION,
)

_OCCUPY_CROSS_SIZE_EXPRESSION = (
    # geometry(@feature), NOT $geometry: this size is evaluated inside
    # a geometry generator's own sub-symbol, where $geometry is the
    # short arc-end segment being drawn rather than the feature's own
    # two clicked points - so the radius came out as that segment's
    # length and the cross all but vanished. Same trap as Table
    # H-XXI's own contaminated-area glyph.
    "min({maximum}, coalesce(mct_radius_mm(geometry(@feature),"
    " @map_extent, @map_scale), 0) / {fraction})"
).format(maximum=_ARROWHEAD_SIZE_MM, fraction=_OCCUPY_CROSS_RADIUS_FRACTION)

# Breathing room either side of the letter inside the gap it cuts.
_LETTER_PADDING_MM = 1.2

# LABEL_FONT_SIZE is in POINTS, which is what QgsTextFormat defaults
# to; a gap measured on the page needs millimetres.
_LETTER_SIZE_MM = LABEL_FONT_SIZE * 25.4 / 72.0


def _letter_gap_expression(measure_type):

    """
    How wide, in page millimetres, this symbol's own letter gap has to
    be - the letter's rendered width plus padding at each end,
    measured with Qt's font metrics rather than estimated.

    Zero for a task that carries no letter at all, so the geometry
    functions take their own "no gap" path.
    """

    if measure_type not in LINE_LETTERS:
        return "0"

    return "mct_text_width_mm('{letter}', {size:.4f}) + {padding:.4f}".format(
        letter=LINE_LETTERS[measure_type],
        size=_LETTER_SIZE_MM,
        padding=2.0 * _LETTER_PADDING_MM,
    )


def _line_geometry_expression(measure_type):

    """
    The Table H-XIX geometry function this task borrows, with the gap
    its own letter needs cut into the right shaft.

    @map_scale resolves inside a geometry generator - established by
    probe 2026-08-15 - which is what lets a PAGE-sized gap be cut into
    ground-unit geometry at all.
    """

    gap = _letter_gap_expression(measure_type)

    # **Penetrate is Block's construction**, at the maintainer's own
    # instruction - the same crossbar and perpendicular stem, the same
    # three anchor points, with "P" for "B" and the arrowhead moved to
    # where the stem meets the base.
    if measure_type in ("block", "penetrate"):
        return f"mct_block_geometry($geometry, {gap}, @map_scale)"

    if measure_type == "disrupt":
        return f"mct_disrupt_geometry($geometry, {gap}, @map_scale)"

    # **Secure is Retain's construction, reused whole.** The
    # maintainer's own words: PT1 the centre, PT1-PT2 the radius, a 330
    # degree arc "like we did retain earlier", an arrowhead at the 330
    # degree point and the letter on the perimeter at the 180 degree
    # mark. Retain already draws exactly that, gap and all, so this
    # borrows it rather than restating it - only the letter's own
    # radius differs (see mct_secure_letter_point).
    # **Occupy is Secure, with a different letter and a different end
    # mark.** The maintainer's own words: "everything same as secure,
    # except, replace 'S' with 'O', and have a X - drawn in the same
    # size as the arrowhead twice like this >< in place of the secure's
    # arrowhead". So the arc itself is the same call again.
    # **Isolate is Secure again**, with triangles standing on the same
    # arc - "start with same construction rules as secure including the
    # arrowhead, replace 'S' with 'I'". The triangles are their own
    # symbol layer; the arc itself is this same call a third time.
    if measure_type in ("secure", "occupy", "isolate"):
        return "mct_retain_arc($geometry)"

    # **Seize is Turn's curve with a circle at its start.** The
    # maintainer's own words: "same as turn, only that at p1 instead of
    # beginning the line (bezier curve), insert a circle... and the
    # line pt1-pt2-pt3 does not go through the circle at pt1 but starts
    # from the perimeter of the circle". The curve itself is Turn's
    # call, untouched; the circle and the clearance are symbol layers.
    # The "S" sits ON the curve with the curve broken for it, like
    # every other letter here - the maintainer's own correction after a
    # first build placed it clear of the line on a reading of the
    # template. Broken with line_substring() rather than inside
    # mct_turn_arc(), so Table H-XIX's own Turn is untouched.
    # **Delay is its own construction**, the first line task here that
    # borrows nothing: a straight shaft from PT1 to PT2 with the letter
    # set into it, carrying on into a 180-degree arc that takes PT2-PT3
    # as its diameter. Retire, Withdraw and Withdraw Under Pressure are
    # the same shape with a different letter.
    if measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES:
        return f"mct_delay_geometry($geometry, {gap}, @map_scale)"

    # **Bypass is Table H-XIX's own Obstacle Bypass Easy (270601)**,
    # at the maintainer's own instruction - "same as obstacle bypass
    # easy 270601, except add B (masked) on line segment joining the
    # two arrows, in the middle of the line". The two arrows are that
    # symbol's own call; the rear line they join is a symbol layer
    # below, and the gap for the "B" is cut into it.
    if measure_type == "bypass":
        return "mct_obstacle_bypass_arrows($geometry)"

    if measure_type == "seize":

        curve = "mct_turn_arc($geometry)"

        half = (
            "mct_mm_in_map_units(({gap}) / 2, @map_extent, @map_scale)"
        ).format(gap=gap)

        return (
            "collect_geometries("
            "line_substring({curve}, 0, length({curve}) / 2 - {half}),"
            "line_substring({curve}, length({curve}) / 2 + {half},"
            " length({curve})))"
        ).format(curve=curve, half=half)

    return f"mct_fix_geometry($geometry, {gap}, @map_scale)"


def _task_line_layer():

    """
    A plain stroke in the task's own colour and status style - black by
    default, affiliation-driven, dashed when the feature is anticipated.

    Shared by the symbol's main run and by any extra generated part
    that has to match it, so the two can never drift.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(QColor(0, 0, 0))

    line_layer.setWidth(_LINE_WIDTH_MM)

    _apply_affiliation_color(
        line_layer,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    return line_layer


def _task_line_generator_layer(geometry_expression):

    """One extra generated run, drawn exactly like the symbol's own."""

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, _task_line_layer())

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression(geometry_expression)

    generator.setSubSymbol(inner)

    return generator


def _mission_task_line_symbol(measure_type):

    """
    One of the three, drawn on Table H-XIX's own geometry.

    **Affiliation-coloured, defaulting to BLACK** - the maintainer's
    own instruction. The obstacle versions default to GREEN because
    H.5.21.1 makes obstacles an explicit exception; H.5.26 claims
    nothing like it, so these follow the appendix's ordinary rule and
    the layer's own "Unspecified (black)" default lands on black.
    """

    line_layer = _task_line_layer()

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    # Seize's curve starts on its circle's PERIMETER, not at PT1 -
    # trimmed rather than shortened in the geometry, because the
    # clearance is the circle's own page-unit radius and QGIS applies a
    # trim after projecting. The same tool the convoy bar uses to meet
    # its head.
    if measure_type == "seize":

        line_layer.setTrimDistanceStart(_SEIZE_CIRCLE_RADIUS_MM)

        line_layer.setTrimDistanceStartUnit(Qgis.RenderUnit.Millimeters)

    generator.setGeometryExpression(_line_geometry_expression(measure_type))

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    if measure_type == "disrupt":
        symbol.appendSymbolLayer(_disrupt_arrowhead_layer())

    if measure_type == "fix":
        symbol.appendSymbolLayer(_fix_arrowhead_layer())

    if measure_type == "seize":

        symbol.appendSymbolLayer(_seize_circle_layer())

        symbol.appendSymbolLayer(
            _arrowhead_layer(
                "mct_turn_arc($geometry)",
                Qgis.MarkerLinePlacement.LastVertex,
            )
        )

    if measure_type == "penetrate":
        symbol.appendSymbolLayer(
            _arrowhead_layer(
                "mct_block_stem_foot($geometry)",
                Qgis.MarkerLinePlacement.LastVertex,
                size_expression=_PENETRATE_HEAD_SIZE_EXPRESSION,
            )
        )

    # Isolate carries Secure's own arrowhead, at the maintainer's own
    # instruction - "same construction rules as secure INCLUDING the
    # arrowhead". The standard's template for 341500 draws none; what
    # looks like one there is the leader line pointing at the "PT. 2
    # (START POINT)" caption, and the maintainer asked for a real one.
    if measure_type in ("secure", "isolate"):
        symbol.appendSymbolLayer(
            _arrowhead_layer(
                "mct_retain_arc_end($geometry)",
                Qgis.MarkerLinePlacement.LastVertex,
            )
        )

    if measure_type == "isolate":
        symbol.appendSymbolLayer(
            _task_line_generator_layer("mct_isolate_teeth($geometry)")
        )

    # Rides the shaft run BACKWARDS, so the head lands on PT1 and
    # points out of the symbol - "the arrow points in the direction of
    # the action", and PT1 is where the action concludes.
    if measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES:
        symbol.appendSymbolLayer(
            _arrowhead_layer(
                "mct_delay_shaft($geometry)",
                Qgis.MarkerLinePlacement.LastVertex,
            )
        )

    if measure_type == "bypass":

        symbol.appendSymbolLayer(
            _task_line_generator_layer(
                "mct_obstacle_bypass_rear_easy($geometry, {gap},"
                " @map_scale)".format(gap=_letter_gap_expression("bypass"))
            )
        )

        # A head on each arrow's own tip, at PT1 and PT2. Sized in MAP
        # UNITS as a quarter of the arrow it sits on and capped at the
        # layer's own 6 mm, which is what 270601 does - "arrowhead
        # should also become small if the lines are small, upto the
        # current size which will be the max".
        symbol.appendSymbolLayer(
            _arrowhead_layer(
                "mct_obstacle_bypass_arrows($geometry)",
                Qgis.MarkerLinePlacement.LastVertex,
                map_unit_size_expression=(
                    "mct_obstacle_bypass_arrow_length($geometry) * {}".format(
                        _BYPASS_ARROWHEAD_ARROW_FRACTION
                    )
                ),
            )
        )

    if measure_type == "occupy":

        # ">" and "<" on the same point, tip to tip - the same
        # arrowhead twice, the second turned through 180 degrees.
        for angle in (0.0, 180.0):

            symbol.appendSymbolLayer(
                _arrowhead_layer(
                    "mct_retain_arc_end($geometry)",
                    Qgis.MarkerLinePlacement.LastVertex,
                    angle,
                    _OCCUPY_CROSS_SIZE_EXPRESSION,
                )
            )

    return symbol


def _fix_arrowhead_layer():

    """
    Fix's own arrowhead, at PT1.

    **Table H-XIX's Fix has none** - the maintainer's own construction
    for the obstacle effect deliberately dropped the standard's, and
    that version is untouched. Table H-XXIV's carries one, asked for
    directly: "Fix - pt1 there should be an arrow head".

    Turned through 180 degrees. A marker rotated onto a line's FIRST
    vertex faces along the direction of travel - towards PT2, back into
    the symbol - and an arrowhead at the start has to point the other
    way, out of it.
    """

    head = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        _ARROWHEAD_SIZE_MM
    )

    head.setColor(QColor(0, 0, 0, 0))

    head.setStrokeWidth(_LINE_WIDTH_MM * 1.5)

    head.setAngle(180.0)

    _apply_affiliation_color(
        head,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, head)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.FirstVertex)

    marker_line.setRotateSymbols(True)

    return marker_line


def _seize_circle_layer():

    """
    The circle at Seize's own PT1 - drawn on the CURVE's first vertex
    rather than the feature's, so it stays put whichever way the curve
    bends.
    """

    circle = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.Circle,
        2.0 * _SEIZE_CIRCLE_RADIUS_MM
    )

    circle.setColor(QColor(0, 0, 0, 0))

    circle.setStrokeWidth(_LINE_WIDTH_MM)

    _apply_affiliation_color(circle, [QgsSymbolLayer.Property.StrokeColor])

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, circle)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.FirstVertex)

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, marker_line)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_turn_arc($geometry)")

    generator.setSubSymbol(inner)

    return generator


def _arrowhead_layer(geometry_expression, placement, angle=0.0,
                     size_expression=None, map_unit_size_expression=None):

    """
    An arrowhead riding on its own geometry generator - shared by every
    line task that carries one.

    `geometry_expression` is deliberately a separate, SHORTER geometry
    than the symbol's own: a marker at a LastVertex placement fires on
    the last vertex of EVERY part, and each of these shapes is a
    multi-part geometry once a letter gap is cut into it.

    `size_expression` sizes the head in PAGE millimetres;
    `map_unit_size_expression` sizes it in MAP UNITS instead, capped at
    the layer's own millimetre size, so the head shrinks with a small
    symbol and tops out on a large one. Only one of the two applies -
    Bypass is the only task using the second, matching what Table
    H-XIX's own 270601 already does.
    """

    head = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        _ARROWHEAD_SIZE_MM
    )

    head.setColor(QColor(0, 0, 0, 0))

    head.setStrokeWidth(_LINE_WIDTH_MM * 1.5)

    if angle:
        head.setAngle(angle)

    if size_expression is not None:

        head.setDataDefinedProperty(
            QgsSymbolLayer.Property.Size,
            QgsProperty.fromExpression(size_expression)
        )

    if map_unit_size_expression is not None:

        head.setSizeUnit(Qgis.RenderUnit.MapUnits)

        capped = QgsMapUnitScale()
        capped.maxSizeMMEnabled = True
        capped.maxSizeMM = _ARROWHEAD_SIZE_MM

        head.setSizeMapUnitScale(capped)

        head.setDataDefinedProperty(
            QgsSymbolLayer.Property.Size,
            QgsProperty.fromExpression(map_unit_size_expression)
        )

    _apply_affiliation_color(head, [QgsSymbolLayer.Property.StrokeColor])

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, head)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(placement)

    marker_line.setRotateSymbols(True)

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, marker_line)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression(geometry_expression)

    generator.setSubSymbol(inner)

    return generator


def _disrupt_arrowhead_layer():

    """
    Disrupt's own three arrowheads, one per arrow tip.

    Scoped to mct_disrupt_arrow_tips() rather than the combined
    geometry: a LastVertex placement over base-plus-arrows would also
    mark the BASE's own last vertex, which is not an arrow tip. The
    same two-generator arrangement Table H-XIX's own Disrupt uses, and
    the reason its docstring gives.
    """

    head = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        _ARROWHEAD_SIZE_MM
    )

    head.setColor(QColor(0, 0, 0, 0))

    head.setStrokeWidth(_LINE_WIDTH_MM * 1.5)

    _apply_affiliation_color(
        head,
        [QgsSymbolLayer.Property.StrokeColor]
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, head)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.LastVertex)

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, marker_line)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression("mct_disrupt_arrow_tips($geometry)")

    generator.setSubSymbol(inner)

    return generator


_LINE_SYMBOL_BUILDERS = {
    measure_type: (lambda measure_type=measure_type:
                   _mission_task_line_symbol(measure_type))
    for measure_type in LINE_MEASURE_TYPE_LABELS
}


def _configure_lines_labeling(layer):

    """
    The letter sits in the gap its own geometry cut for it - so this is
    an OverPoint label pinned to that gap's own midpoint, not a label
    placed along the line and masked.

    **No QgsTextMaskSettings**, and that is not an omission: the shaft
    the letter sits on is nested inside a geometry generator, which
    QGIS's Selective Masking cannot reach. The break is in the geometry
    instead - the same answer the Minimum Safe Distance Zone's rings
    needed.
    """

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for measure_type in LINE_LETTERS:

        settings = _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            "'{}'".format(LINE_LETTERS[measure_type]),
            label_geometry_expression=_letter_point_expression(measure_type),
            quadrant=Qgis.LabelQuadrantPosition.Over,
        )

        rule = QgsRuleBasedLabeling.Rule(settings)

        rule.setFilterExpression(
            "\"measure_type\" = '{}'".format(measure_type)
        )

        rule.setDescription(measure_type)

        root_rule.appendChild(rule)

    layer.setLabeling(QgsRuleBasedLabeling(root_rule))

    layer.setLabelsEnabled(True)


def _letter_point_expression(measure_type):

    """
    Where each letter goes - always the middle of the gap its own
    geometry cut, so the two can never drift apart.
    """

    if measure_type in ("block", "penetrate"):
        return "mct_block_letter_point($geometry)"

    if measure_type == "disrupt":
        return "mct_disrupt_letter_point($geometry)"

    if measure_type in ("secure", "occupy", "isolate"):
        return "mct_secure_letter_point($geometry)"

    if measure_type in DELAY_CONSTRUCTION_MEASURE_TYPES:
        return "mct_delay_letter_point($geometry)"

    if measure_type == "bypass":
        return "mct_obstacle_bypass_rear_midpoint($geometry)"

    # The middle of the curve, which is the middle of the gap the
    # curve carries. Not the circle: that holds a boxed Field A in the
    # template, which this build does not offer.
    if measure_type == "seize":
        return (
            "line_interpolate_point(mct_turn_arc($geometry),"
            " length(mct_turn_arc($geometry)) / 2)"
        )

    return "mct_fix_letter_point($geometry, {gap}, @map_scale)".format(
        gap=_letter_gap_expression("fix")
    )


def create_mission_task_lines_layer(name=LINES_LAYER_NAME):

    """Table H-XXIV's own line-type mission tasks."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(f"LineString?crs={crs.authid()}", name, "memory")

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
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
        QgsDefaultValue("'block'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    _configure_lines_labeling(layer)

    return layer


def add_mission_task_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_mission_task_lines_layer,
    )
