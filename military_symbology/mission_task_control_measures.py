# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.26 (Table H-XXIV, "Mission Task Symbols") -
Mini-Phase H21. Printed pages 636-655, 29 code rows.

**Three of the 29 are points; this module builds those three.** Destroy
(340900), Interdict (341400) and Neutralize (341600) each take ONE
anchor point and draw a centred glyph - checked on the table's own
DRAW RULES ("This symbol requires one anchor point. The center point
defines center of the symbol"), not inferred. Every other row in the
table is an arrow, a bracket or an outlined region built from two to
fifty anchor points, and milsymbol has no icon for any of them: 3 of
29 present, verified entry by entry against milsymbol's own
src/numbersidc/sidc/control-measure.js. The project maintainer scoped
this pass to "all the point symbols derived from milsymbol.js", and
the split falls exactly on that line.

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
for once (see docs/roadmap.md's own Phase 10 entry), so the 26 unbuilt
rows are listed below by code rather than by name alone.

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

from ._point_symbol_layer import build_single_domain_point_layer

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
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
# The 26 remaining rows of Table H-XXIV. 340000 is the section's own
# parent entry, with TEMPLATE and EXAMPLE both reading "N/A", so the
# real drawing work is 25.
#
# Every one is a multi-anchor construction rather than a centred
# glyph, and none has a milsymbol icon. Roughly three families:
#
# - Arrow tasks (Counterattack, Counterattack by Fire, Penetrate,
#   Seize, Withdraw and the rest) - N anchor points, PT1 at the
#   arrowhead's tip, working back to the rear. Counterattack's own
#   draw rules allow N between 3 and 50.
# - Bracket/effect tasks (Block, Breach, Bypass, Canalize, Clear,
#   Delay, Disrupt, Fix, Isolate) - the same shapes Table H-XIX's own
#   obstacle effects already build here, under DIFFERENT codes. See
#   the module docstring: these are not the same symbols.
# - Security tasks (342200 and its three variants) - Cover, Guard and
#   Screen are sub-codes of Security, drawn as an open bracket along
#   the screened front.
TABLE_H_XXIV_REMAINING = {
    "340000": "Mission Tasks (section parent; TEMPLATE and EXAMPLE "
              "both N/A)",
    "340100": "Block",
    "340200": "Breach",
    "340300": "Bypass",
    "340400": "Canalize",
    "340500": "Clear",
    "340600": "Counterattack",
    "340700": "Counterattack by Fire",
    "340800": "Delay",
    "341000": "Disrupt",
    "341100": "Fix",
    "341200": "Follow and Assume",
    "341300": "Follow and Support",
    "341500": "Isolate",
    "341700": "Occupy",
    "341800": "Penetrate",
    "341900": "Relief in Place (RIP)",
    "342000": "Retire/Retirement",
    "342100": "Secure",
    "342200": "Security",
    "342201": "Security - Cover",
    "342202": "Security - Guard",
    "342203": "Security - Screen",
    "342300": "Seize",
    "342400": "Withdraw",
    "342500": "Withdraw Under Pressure",
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
}

LINE_MEASURE_TYPE_CODES = {
    "block": "340100",
    "disrupt": "341000",
    "fix": "341100",
    "secure": "342100",
}


# The letter each one carries, set into its own shaft.
LINE_LETTERS = {
    "block": "B",
    "disrupt": "D",
    "fix": "F",
    "secure": "S",
}

_LINE_WIDTH_MM = 0.4

# The same head Table H-XIX's own Disrupt uses.
_ARROWHEAD_SIZE_MM = 6

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
    """

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

    if measure_type == "block":
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
    if measure_type == "secure":
        return "mct_retain_arc($geometry)"

    return f"mct_fix_geometry($geometry, {gap}, @map_scale)"


def _mission_task_line_symbol(measure_type):

    """
    One of the three, drawn on Table H-XIX's own geometry.

    **Affiliation-coloured, defaulting to BLACK** - the maintainer's
    own instruction. The obstacle versions default to GREEN because
    H.5.21.1 makes obstacles an explicit exception; H.5.26 claims
    nothing like it, so these follow the appendix's ordinary rule and
    the layer's own "Unspecified (black)" default lands on black.
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

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line_layer)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(QgsSymbol.SymbolType.Line)

    generator.setGeometryExpression(_line_geometry_expression(measure_type))

    generator.setSubSymbol(inner)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, generator)

    if measure_type == "disrupt":
        symbol.appendSymbolLayer(_disrupt_arrowhead_layer())

    if measure_type == "fix":
        symbol.appendSymbolLayer(_fix_arrowhead_layer())

    if measure_type == "secure":
        symbol.appendSymbolLayer(
            _arrowhead_layer(
                "mct_retain_arc_end($geometry)",
                Qgis.MarkerLinePlacement.LastVertex,
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


def _arrowhead_layer(geometry_expression, placement, angle=0.0):

    """
    An arrowhead riding on its own geometry generator - shared by every
    line task that carries one.

    `geometry_expression` is deliberately a separate, SHORTER geometry
    than the symbol's own: a marker at a LastVertex placement fires on
    the last vertex of EVERY part, and each of these shapes is a
    multi-part geometry once a letter gap is cut into it.
    """

    head = QgsSimpleMarkerSymbolLayer(
        QgsSimpleMarkerSymbolLayerBase.Shape.ArrowHead,
        _ARROWHEAD_SIZE_MM
    )

    head.setColor(QColor(0, 0, 0, 0))

    head.setStrokeWidth(_LINE_WIDTH_MM * 1.5)

    if angle:
        head.setAngle(angle)

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

    for measure_type in LINE_MEASURE_TYPE_LABELS:

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

    if measure_type == "block":
        return "mct_block_letter_point($geometry)"

    if measure_type == "disrupt":
        return "mct_disrupt_letter_point($geometry)"

    if measure_type == "secure":
        return "mct_secure_letter_point($geometry)"

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
