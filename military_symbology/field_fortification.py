# -*- coding: utf-8 -*-

"""
MIL-STD-2525D Appendix H.5.22 (Table H-XX, "Field fortification control
measure symbols") - Mini-Phase H17, and one of the smallest tables in
this appendix: six entries over printed pages 603-605.

**Two layers**, following the same "each H.5.x group owns its layers"
convention every group since H-XIII has used:

- **Points** (4): Shelter (280900), Above Ground Shelter (281000),
  Below Ground Shelter (281100) and Fort (281200). All four are static
  icons centred on one anchor point, all four already exist in
  sidc.py's ENTITIES["control_measure"], and all four were verified to
  render as real glyphs through milsymbol rather than the unknown icon
  before this module was written - the defect class that has bitten
  this project three times. They are RELOCATED here out of the shared
  control_measure_points.py layer, exactly as Table H-VI's, H-IX's,
  H-XIII's and H-XIX's own point entries were before them.

- **Lines** (2): Fortified Line (290900) and Fortified Position
  (291000). Neither has a SIDC entity - like every other line in this
  appendix they are drawn by hand.

**Colour: affiliation, not green.** H.5.21.1 makes obstacles green as
an explicit exception; H.5.22.1 says nothing of the kind, so field
fortification takes the ordinary H.5.3 affiliation colouring. For the
points that comes free from milsymbol (see control_measure_points.py's
own docstring for the live confirmation); for the two lines it comes
from the shared _apply_affiliation_color().

**What the standard numbers here, and what it does not.** Both lines
say their symbol "varies only in length", which is the standard's own
way of saying the CROSS-SECTION is fixed - the same principle the
maintainer applied to Table H-XIX's Bridge or Gap ("as such it is a
linear feature, so the width increasing with the length is not
practical"). So both cross-sections are fixed MILLIMETRES here, and
neither is built as generated geometry: a geometry generator works in
layer units and cannot see page units.

What it does NOT number, and so is this build's own call - flagged for
the maintainer's smoke test rather than presented as read off the page:

1. The rampart tile's own size (_RAMPART_TILE_MM and the merlon
   proportions inside the glyph).
2. Fortified Position's own depth (_FORTIFIED_POSITION_DEPTH_MM).
3. **Which side the front faces.** Both entries carry only a "typically
   points/faces toward enemy forces" note, which two anchor points
   cannot express. Both templates draw the front on the LEFT of PT1->
   PT2 travel - ramparts rising to the left, Fortified Position's legs
   trailing to the right so its closed side faces left - so that is the
   convention used, consistently, for both. A third anchor point would
   be the alternative, and the standard does not ask for one.
"""

from qgis.core import (
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerLineSymbolLayer,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleLineSymbolLayer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbol,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.core import Qgis

from qgis.PyQt.QtCore import QMetaType

from ._control_measure_shared import (
    _AFFILIATION_COLOR_EXPRESSION,
    _STATUS_LINE_STYLE_EXPRESSION,
    _apply_affiliation_color,
    _build_rule_based_renderer,
    _configure_affiliation_field,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
)

from ._point_symbol_layer import build_single_domain_point_layer

from qgis.core import QgsEditorWidgetSetup, QgsField


POINTS_LAYER_NAME = "Field Fortification Points"
LINES_LAYER_NAME = "Field Fortification Lines"

# Table H-XX's own four point entries, in the standard's own order.
# The keys are sidc.py's own ENTITIES["control_measure"] keys - these
# are relocated from control_measure_points.py, not new vocabulary.
POINT_ENTITY_LABELS = {
    "shelter": "Shelter",
    "shelter_above_ground": "Shelter, Above Ground",
    "shelter_below_ground": "Shelter, Below Ground",
    "fort": "Fort",
}

POINT_ENTITY_CODES = {
    "shelter": "280900",
    "shelter_above_ground": "281000",
    "shelter_below_ground": "281100",
    "fort": "281200",
}

LINE_MEASURE_TYPE_LABELS = {
    "fortified_line": "Fortified Line",
    "fortified_position": "Fortified Position",
}

LINE_MEASURE_TYPE_CODES = {
    "fortified_line": "290900",
    "fortified_position": "291000",
}

_LINE_WIDTH_MM = 0.4

# The affiliation hue as a CSS colour, for the two glyphs that go into
# SVG MARKUP rather than into a QGIS colour property.
#
# This has to exist separately because the shared
# _AFFILIATION_COLOR_EXPRESSION is built from color_rgb(), which
# evaluates to a bare "0,0,255" - correct for a QGIS colour property
# and silently invalid inside an SVG, where it renders the glyph as
# NOTHING AT ALL. That exact mistake cost a debugging round on Table
# H-XIX's Overhead Wire towers. The two are pinned as agreeing by
# TestFieldFortificationLines, so they cannot drift apart.
_RAMPART_GLYPH_COLOR_EXPRESSION = (
    "CASE "
    "WHEN \"affiliation\" = 'friend' THEN 'rgb(0,0,255)' "
    "WHEN \"affiliation\" = 'hostile' THEN 'rgb(255,0,0)' "
    "WHEN \"affiliation\" = 'neutral' THEN 'rgb(0,255,0)' "
    "WHEN \"affiliation\" = 'unknown' THEN 'rgb(255,255,0)' "
    "ELSE 'rgb(0,0,0)' "
    "END"
)

# --- The two unnumbered cross-sections. See the module docstring. ---

# One rampart tile - a merlon plus the gap after it. The glyph's own
# viewBox is square, so the merlon's height is set inside
# mct_rampart_svg by its path rather than here.
_RAMPART_TILE_MM = 3.0

# Tiles butt edge to edge; at exactly one tile width apart they leave a
# visible hairline at every join, the same effect the antitank wall hit
# in Table H-XIX (see _WIRE_TILE_OVERLAP_MM there).
_RAMPART_TILE_OVERLAP_MM = 0.12

# How far Fortified Position's legs trail back from its front bar.
# Fixed, because the standard says the symbol "varies only in length".
_FORTIFIED_POSITION_DEPTH_MM = 4.0


def _fortified_line_symbol():

    """
    Fortified Line (290900) - a crenellated rampart profile tiled along
    the whole line. The profile IS the line: there is no separate
    straight line underneath it, the same way Table H-XIX's antitank
    wall and Obstacle Line are their own line rather than a decoration
    on one.

    Tiled rather than generated, because the standard lets this symbol
    run over as many anchor points as the user wants ("additional
    points can be defined to extend the line") and a marker line
    follows a multi-segment path for free.

    Ramparts rise on the LEFT of PT1->PT2 travel, which is how the
    template draws them - see the module docstring on why that is a
    convention rather than a reading.
    """

    marker = QgsMarkerSymbol()

    glyph = QgsSvgMarkerSymbolLayer("")

    glyph.setSize(_RAMPART_TILE_MM)

    glyph.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_rampart_svg({colour})".format(
                colour=_RAMPART_GLYPH_COLOR_EXPRESSION
            )
        )
    )

    marker.changeSymbolLayer(0, glyph)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(Qgis.MarkerLinePlacement.Interval)

    marker_line.setInterval(_RAMPART_TILE_MM - _RAMPART_TILE_OVERLAP_MM)

    marker_line.setIntervalUnit(Qgis.RenderUnit.Millimeters)

    # Follow the line's own bearing, or the ramparts stay square to the
    # screen instead of to the rampart.
    marker_line.setRotateSymbols(True)

    symbol = QgsLineSymbol()

    symbol.changeSymbolLayer(0, marker_line)

    return symbol


def _fortified_position_symbol():

    """
    Fortified Position (291000) - PT1 and PT2 are the two front
    corners, and a leg trails back from each. The standard says the
    symbol "varies only in length", so the legs are a fixed
    millimetre depth rather than any fraction of the front bar, and
    they are therefore drawn as a marker glyph rather than as geometry
    (a geometry generator cannot see page units).

    The legs trail to the RIGHT of PT1->PT2 travel, putting the closed
    front on the left - see the module docstring.
    """

    symbol = QgsLineSymbol()

    front = QgsSimpleLineSymbolLayer()

    front.setWidth(_LINE_WIDTH_MM)

    _apply_affiliation_color(
        front, [QgsSymbolLayer.Property.StrokeColor]
    )

    front.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    front_generator = QgsGeometryGeneratorSymbolLayer.create({})

    front_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    front_generator.setGeometryExpression(
        "mct_fortified_position_front($geometry)"
    )

    front_inner = QgsLineSymbol()

    front_inner.changeSymbolLayer(0, front)

    front_generator.setSubSymbol(front_inner)

    symbol.changeSymbolLayer(0, front_generator)

    leg_marker = QgsMarkerSymbol()

    leg = QgsSvgMarkerSymbolLayer("")

    leg.setSize(2.0 * _FORTIFIED_POSITION_DEPTH_MM)

    leg.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_fortified_position_leg_svg({colour}, {depth}, {stroke})"
            .format(
                colour=_RAMPART_GLYPH_COLOR_EXPRESSION,
                depth=_FORTIFIED_POSITION_DEPTH_MM,
                stroke=_LINE_WIDTH_MM,
            )
        )
    )

    leg_marker.changeSymbolLayer(0, leg)

    leg_line = QgsMarkerLineSymbolLayer(True)

    leg_line.setSubSymbol(leg_marker)

    # The front geometry is trimmed to exactly two points, so "every
    # vertex" is precisely the two front corners.
    leg_line.setPlacements(Qgis.MarkerLinePlacement.Vertex)

    leg_line.setRotateSymbols(True)

    leg_inner = QgsLineSymbol()

    leg_inner.changeSymbolLayer(0, leg_line)

    leg_generator = QgsGeometryGeneratorSymbolLayer.create({})

    leg_generator.setSymbolType(QgsSymbol.SymbolType.Line)

    leg_generator.setGeometryExpression(
        "mct_fortified_position_front($geometry)"
    )

    leg_generator.setSubSymbol(leg_inner)

    symbol.appendSymbolLayer(leg_generator)

    return symbol


_LINE_SYMBOL_BUILDERS = {
    "fortified_line": _fortified_line_symbol,
    "fortified_position": _fortified_position_symbol,
}


def create_field_fortification_points_layer(name=POINTS_LAYER_NAME):

    """
    Table H-XX's own four static point symbols, milsymbol-rendered.

    No echelon and no headquarters flag: Appendix H's own amplifier
    table gives control-measure points neither, the same call
    control_measure_points.py already makes for this symbol set.
    """

    return build_single_domain_point_layer(
        name,
        "control_measure",
        POINT_ENTITY_LABELS,
        "shelter",
        include_echelon=False,
        include_headquarters=False,
    )


def add_field_fortification_points_layer(iface):

    return add_layer_if_absent(
        iface,
        POINTS_LAYER_NAME,
        create_field_fortification_points_layer,
    )


def create_field_fortification_lines_layer(name=LINES_LAYER_NAME):

    """Table H-XX's own two line symbols."""

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

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("measure_type"),
        QgsEditorWidgetSetup(
            "ValueMap", {"map": _value_map(LINE_MEASURE_TYPE_LABELS)}
        )
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setRenderer(
        _build_rule_based_renderer(layer, _LINE_SYMBOL_BUILDERS)
    )

    return layer


def add_field_fortification_lines_layer(iface):

    return add_layer_if_absent(
        iface,
        LINES_LAYER_NAME,
        create_field_fortification_lines_layer
    )
