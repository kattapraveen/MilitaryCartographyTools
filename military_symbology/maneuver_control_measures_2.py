# -*- coding: utf-8 -*-

"""
Builds ready-to-use layers for MIL-STD-2525D Appendix H.5.14 (Table
H-XII, "Maneuver control measure symbols") - the sixth H.5.x logical
group in this appendix-by-appendix pass. Named `maneuver_control_
measures_2` (not `_h6` or similar) because H.5.14's own section title
is LITERALLY "Maneuver control measure symbols" again - the identical
title H.5.11/Table H-VII (`maneuver_control_measures.py`) already uses -
the standard repeats this heading for a second, later group of
measures, not a naming inconsistency on this project's own part; adding
"_2" avoids a real module-name collision with that earlier file.

**Mini-Phase H6, 2026-08-09.**

**Two entries skipped outright**: **Attack By Fire Position (152000)**
and **Ambush (141700)** both require the SAME real geometric
construction this appendix hasn't needed before - a single arrow shaft
whose own tail connects not to a digitized vertex but to the COMPUTED
MIDPOINT of a separate line between two other anchor points ("the rear
of the arrow should connect to the midpoint of the line between points
2 and 3"). A simple user-digitized path can represent any number of
SEQUENTIAL vertices, but not a shaft branching off a midpoint partway
along a separate segment - genuinely different from every other
"arrow(s) from a shared vertex" construction already built (Principal
Direction of Fire in maneuver_control_measures.py, Search Area/
Reconnaissance Area below), which all have every arm meeting AT a
shared, directly-digitized vertex, not at a computed point between two
others. Deferred, the same "doesn't fit this module's own techniques"
reasoning already applied to compound entries in earlier H-subphases.

**Two entries nominally coded as "Areas" in the standard's own SIDC
numbering (a "15" prefix) are built on the LINES layer here instead**,
because their actual geometry is a multi-point arrow/line, not a closed
boundary a polygon layer could hold: **Support by Fire Position
(152100)** (a 4-point line with an arrowhead at each end - built for
real, since unlike Attack By Fire Position/Ambush its own two arrowheads
connect directly to digitized vertices, no midpoint needed) and
**Search Area/Reconnaissance Area (152200)** (the same "two arrows from
a shared vertex" construction as Principal Direction of Fire, plus a
boxed "A" at the vertex - the standard's own double-notched arrow shaft
decoration is not reproduced, matching this appendix's established
"recognisable, not exact" tolerance for decorative details). This
module organises its own two layers by ACTUAL QGIS GEOMETRY TYPE
(matching every other H.5.x module in this pass), not by the standard's
own SIDC field-code grouping, since a QGIS layer can only ever hold one
geometry type regardless of what the standard's own numbering implies.

**Encirclement's own Friendly (151801) and Enemy (151802) variants are
folded into one "encirclement" measure type**, the same "Field N (ENY)
dropped, so the pair renders identically once affiliation-colour is the
only real difference" reasoning already applied to Friendly/Enemy Area
in maneuver_control_measures.py.

**Airhead Line (141300)** is the first LINE in this whole appendix pass
whose own template draws it as a closed contour with a single, fixed,
CENTRED label ("AIRHEAD LINE") rather than a label repeating along the
line or fixed at each end - built with `Qgis.LabelPlacement.Line`'s own
default (a single label placed wherever PAL finds room), not the
repeating/end-anchored patterns every other labelled line in this
appendix has needed so far.

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
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _end_label_layer,
    _value_map,
    add_layer_if_absent,
)


LINES_LAYER_NAME = "Maneuver Control Measures II (Lines)"
AREAS_LAYER_NAME = "Maneuver Control Measures II (Areas)"

__all__ = [
    "LINES_LAYER_NAME",
    "AREAS_LAYER_NAME",
    "LINE_MEASURE_TYPE_LABELS",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_maneuver_control_measures_2_lines_layer",
    "create_maneuver_control_measures_2_areas_layer",
    "add_maneuver_control_measures_2_lines_layer",
    "add_maneuver_control_measures_2_areas_layer",
]

# Table H-XII, H.5.14 - see module docstring for why these two are on
# the LINES layer despite the standard's own "15" (Area) SIDC prefix,
# and for what was skipped (Attack By Fire Position, Ambush).
LINE_MEASURE_TYPE_LABELS = {
    "support_by_fire_position": "Support by Fire Position",
    "search_area_reconnaissance_area": "Search Area/Reconnaissance Area",
    "airhead_line": "Airhead Line",
    "bridgehead_line": "Bridgehead Line (BL)",
    "holding_line": "Holding Line (HL)",
    "release_line": "Release Line (RL)",
}

AREA_MEASURE_TYPE_LABELS = {
    "encirclement": "Encirclement",
    "penetration_box": "Penetration Box",
}


def _support_by_fire_position_symbol():

    """
    Table H-XII, code 152100, page 443. A plain line with a filled
    arrowhead at BOTH ends - unlike Attack By Fire Position/Ambush, all
    4 of this symbol's own anchor points connect directly (PT3 -> PT1
    -> PT2 -> PT4 in the standard's own numbering: one arrow tip, the
    base's two endpoints, the other arrow tip), so no midpoint
    computation is needed - the same First/LastVertex arrowhead
    technique already used for maneuver_control_measures.py's own
    Principal Direction of Fire, just at both ends instead of a shared
    vertex.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.5
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

    arrow_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "filled_arrowhead",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "size": "4",
        }
    )

    _apply_affiliation_color(
        arrow_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    for placement in (
        Qgis.MarkerLinePlacement.FirstVertex,
        Qgis.MarkerLinePlacement.LastVertex,
    ):

        arrow_layer = QgsMarkerLineSymbolLayer(True)

        arrow_layer.setSubSymbol(
            arrow_marker.clone()
        )

        arrow_layer.setPlacements(
            placement
        )

        symbol.appendSymbolLayer(
            arrow_layer
        )

    return symbol


def _search_area_reconnaissance_area_symbol():

    """
    Table H-XII, code 152200, page 444. Two arrows from a shared vertex
    (PT1) - the same construction as maneuver_control_measures.py's own
    Principal Direction of Fire - plus a fixed boxed "A" at the vertex
    (Field A, via the shared _end_label_layer() at InnerVertices, the
    same fixed-character marker technique used throughout this
    appendix). The standard's own double-notched/zigzag arrow shaft
    decoration is not reproduced - plain arrows only, matching this
    appendix's "recognisable, not exact" tolerance for decorative
    details (see module docstring).
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

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(
        0,
        line_layer
    )

    arrow_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "filled_arrowhead",
            "color": "0,0,0",
            "outline_color": "0,0,0",
            "size": "3.5",
        }
    )

    _apply_affiliation_color(
        arrow_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.FillColor, QgsSymbolLayer.Property.StrokeColor]
    )

    for placement in (
        Qgis.MarkerLinePlacement.FirstVertex,
        Qgis.MarkerLinePlacement.LastVertex,
    ):

        arrow_layer = QgsMarkerLineSymbolLayer(True)

        arrow_layer.setSubSymbol(
            arrow_marker.clone()
        )

        arrow_layer.setPlacements(
            placement
        )

        symbol.appendSymbolLayer(
            arrow_layer
        )

    symbol.appendSymbolLayer(
        _end_label_layer(
            Qgis.MarkerLinePlacement.InnerVertices,
            "A"
        )
    )

    return symbol


def _simple_end_label_line_symbol(character):

    """
    Bridgehead Line/Holding Line/Release Line - a plain status-driven
    line with a fixed abbreviation at each end.

    The end labels do NOT rotate with the line (`rotate_with_line=
    False` on the shared _end_label_layer()) - see that helper's own
    docstring for the 2026-08-12 Bridgehead Line report ("the label on
    both ends should be straight, in our case one of the labels is
    inverted") and the render that confirmed a right-to-left line
    otherwise flips BOTH its labels upside-down. Applied to Bridgehead
    Line first, then to Holding Line and Release Line the same day once
    the maintainer confirmed the same treatment for both ("fix holding
    line and release line as well") - all three share this one builder,
    so there is no per-caller flag to carry any more.
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
            _end_label_layer(
                placement,
                character,
                rotate_with_line=False
            )
        )

    return symbol


def _airhead_line_symbol():

    """
    Table H-XII, code 141300, page 445. A plain status-driven line -
    the fixed, centred "AIRHEAD LINE" label is handled by this layer's
    own shared designation-label expression (see _LINE_DESIGNATION_
    LABEL_EXPRESSION below), not a symbol-layer marker, since it needs
    to sit centred along the line rather than at a fixed end.
    """

    line_layer = QgsSimpleLineSymbolLayer()

    line_layer.setColor(
        QColor(0, 0, 0)
    )

    line_layer.setWidth(
        0.5
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


_LINE_SYMBOL_BUILDERS = {
    "support_by_fire_position": _support_by_fire_position_symbol,
    "search_area_reconnaissance_area": _search_area_reconnaissance_area_symbol,
    "airhead_line": _airhead_line_symbol,
    "bridgehead_line": lambda: _simple_end_label_line_symbol("BL"),
    "holding_line": lambda: _simple_end_label_line_symbol("HL"),
    "release_line": lambda: _simple_end_label_line_symbol("RL"),
}

# Only Airhead Line shows any text through the general label system -
# every other line here either has no label at all or a symbol-layer
# fixed-end-marker (BL/HL/RL, or the boxed "A" on Search Area/
# Reconnaissance Area).
_LINE_DESIGNATION_LABEL_EXPRESSION = (
    "CASE WHEN \"measure_type\" = 'airhead_line' THEN 'AIRHEAD LINE'"
    " ELSE '' END"
)


# Encirclement's own perimeter decoration (2026-08-12): "it is not
# ticks across the perimeter but triangles placed with their base on
# the perimeter, with about 60% of the triangle base length gap between
# the triangles" - the maintainer's own words, replacing the original
# "line"-shape tick marker (a plain repeated stroke, not real triangular
# teeth). QGIS's own built-in "triangle" marker shape at `size` S
# renders base-width ~S (confirmed by probe render); Interval (the
# marker's own repeat spacing, i.e. base-to-base) = base + gap =
# base * (1 + 0.6).
#
# **Same-day follow-up**: "the triangles are filled, make them hollow;
# increase size of triangles by 20%; make the perimeter touch the base
# of the triangles. the perimeter is inside the triangles and not
# outside, the triangles need to be rotated 180 deg, the base is on
# perimeter, not tip" - the maintainer's own words. The first build's
# own `angle=0`/no-offset combination put the LINE through the shape's
# own bounding-box CENTRE (confirmed by probe render: at angle=0 the
# marker's own local apex sits ~half the triangle's own height above
# the anchor and the base ~half below it - the anchor is what actually
# sits on the line), so the perimeter cut across the middle of every
# triangle rather than touching either edge, and the apex - not the
# base - ended up on the OUTWARD side (a right-hand-side-of-travel
# rotation rule confirmed empirically by rendering all four sides of a
# real closed ring and checking which way each side's own triangles
# pointed). `angle=180` alone flips that (apex now inward, base
# outward) - the "rotated 180 degrees" the maintainer asked for - but
# still leaves the line through the centre. Fixed by ALSO offsetting
# the marker by half its own real (measured, not assumed) height along
# its own local -Y - this project's own established "offset is applied
# in the marker's pre-`.setAngle()` frame, then rotated along with the
# shape by both `.setAngle()` and the line's own tangent" rule (first
# documented for Direction of Attack's own bowtie/DTG placement) means
# this single offset, combined with angle=180, lands the BASE exactly
# on the anchor/perimeter and pushes the apex fully to the inward side,
# with nothing left straddling the line.
_ENCIRCLEMENT_TRIANGLE_BASE_MM = 3.0 * 1.2

_ENCIRCLEMENT_TRIANGLE_GAP_RATIO = 0.6

_ENCIRCLEMENT_TRIANGLE_INTERVAL_MM = (
    _ENCIRCLEMENT_TRIANGLE_BASE_MM * (1 + _ENCIRCLEMENT_TRIANGLE_GAP_RATIO)
)

# The triangle's own real rendered height at _ENCIRCLEMENT_TRIANGLE_
# BASE_MM (3.6mm) - measured via a dedicated probe render (a single
# such marker, rendered alone, its own top/bottom pixel extents
# converted to mm) rather than assumed equal to the base: apex-to-anchor
# ~1.8796mm, anchor-to-base ~1.9304mm, averaging to ~1.905mm each side
# (the small asymmetry is stroke-width bleed, not real shape asymmetry).
_ENCIRCLEMENT_TRIANGLE_HALF_HEIGHT_MM = 1.905


def _encirclement_symbol():

    """
    Table H-XII, codes 151801 (Friendly)/151802 (Enemy), page 440-441 -
    folded into one measure type (see module docstring). A closed
    outline with a triangle-toothed border all the way around - see
    _ENCIRCLEMENT_TRIANGLE_BASE_MM's own comment for the triangle
    marker's own construction.
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

    triangle_marker = QgsMarkerSymbol.createSimple(
        {
            "name": "triangle",
            "color": "0,0,0,0",
            "outline_color": "0,0,0",
            "outline_width": "0.3",
            "size": str(_ENCIRCLEMENT_TRIANGLE_BASE_MM),
            "angle": "180",
        }
    )

    triangle_marker.symbolLayer(0).setOffset(
        QPointF(0, -_ENCIRCLEMENT_TRIANGLE_HALF_HEIGHT_MM)
    )

    _apply_affiliation_color(
        triangle_marker.symbolLayer(0),
        [QgsSymbolLayer.Property.StrokeColor]
    )

    triangle_layer = QgsMarkerLineSymbolLayer(True)

    triangle_layer.setSubSymbol(
        triangle_marker
    )

    triangle_layer.setPlacements(
        Qgis.MarkerLinePlacement.Interval
    )

    triangle_layer.setInterval(
        _ENCIRCLEMENT_TRIANGLE_INTERVAL_MM
    )

    triangle_layer.setIntervalUnit(
        Qgis.RenderUnit.Millimeters
    )

    # 2026-08-12, same-day follow-up: "in qgis, when i make this, the
    # triangles are pointing the other way" - the maintainer's own
    # words, with a screenshot of two real hand-digitized polygons both
    # showing triangles pointing INWARD. Confirmed the root cause with a
    # probe render: placing the exact same triangle_layer directly on a
    # polygon's own boundary (as the code did before this fix) makes the
    # apex direction depend on which way the polygon happens to be
    # digitized (clockwise vs counterclockwise) - QGIS does not
    # normalise a manually-drawn polygon's own ring winding, and the
    # probe showed a CCW ring giving an outward apex (matching every
    # render this session confirmed so far) while the SAME ring reversed
    # to CW gave an inward apex, reproducing the maintainer's own report
    # exactly. Fixed by normalising winding BEFORE the markers are
    # placed - a QgsGeometryGeneratorSymbolLayer wrapping triangle_layer,
    # feeding it `boundary(force_polygon_ccw($geometry))` instead of the
    # feature's own raw boundary - so triangle_layer always sees a CCW
    # ring regardless of how the user actually drew it, and the outward
    # orientation already confirmed correct is now guaranteed rather
    # than a coincidence of this one test polygon's own winding.
    triangle_generator_layer = QgsGeometryGeneratorSymbolLayer.create({})

    triangle_generator_layer.setGeometryExpression(
        "boundary(force_polygon_ccw($geometry))"
    )

    triangle_generator_layer.setSymbolType(
        Qgis.SymbolType.Line
    )

    triangle_generator_symbol = QgsLineSymbol()

    triangle_generator_symbol.changeSymbolLayer(
        0,
        triangle_layer
    )

    triangle_generator_layer.setSubSymbol(
        triangle_generator_symbol
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
        triangle_generator_layer
    )

    return symbol


def _penetration_box_symbol():

    # Table H-XII, code 151900, page 441. A plain outline - the
    # example's own dashed grey "penetration corridor" path through the
    # middle is explanatory only, not part of the control measure. No
    # label field shown in the template at all.
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


_AREA_SYMBOL_BUILDERS = {
    "encirclement": _encirclement_symbol,
    "penetration_box": _penetration_box_symbol,
}


def create_maneuver_control_measures_2_lines_layer(name=LINES_LAYER_NAME):

    """
    A fresh, empty line layer for Table H-XII's own line-geometry
    measure types - see this module's own docstring for the full list
    and what's scoped out.
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
        QgsDefaultValue("'bridgehead_line'")
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

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.Line,
        _LINE_DESIGNATION_LABEL_EXPRESSION
    )

    return layer


def create_maneuver_control_measures_2_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XII's own two real
    area-geometry measure types (Encirclement, Penetration Box).
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
        QgsDefaultValue("'encirclement'")
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

    return layer


def add_maneuver_control_measures_2_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_maneuver_control_measures_2_lines_layer
    )


def add_maneuver_control_measures_2_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_maneuver_control_measures_2_areas_layer
    )
