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
practical").

Fortified Line takes that literally: its rampart profile is a fixed
millimetre tile, not generated geometry, because a geometry generator
works in layer units and cannot see page units.

**Fortified Position does not, after the 2026-08-13 smoke test.** It
was built the same way first - a front bar plus two legs held at a
fixed millimetre depth by a rotated SVG marker - and on a real map the
legs did not draw at all. Rather than chase that, the maintainer
called for the construction Table H-XIX's Obstacle Bypass Easy already
uses and this codebase already trusts: three anchor points, PT3's own
perpendicular distance setting the depth, plain ends instead of
arrowheads. See _fortified_position_symbol() for what that trades
away.

What the standard does NOT number, and so is this build's own call:

1. The rampart tile's own size (_RAMPART_TILE_MM and the merlon
   proportions inside the glyph).
2. **Which side Fortified Line's ramparts stand on.** It carries only
   a "typically points toward enemy forces" note, which two anchor
   points cannot express; the template draws them on the LEFT of
   PT1->PT2 travel, so that is the convention here. Fortified Position
   no longer needs a convention at all - PT3 says which side.
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

from qgis.core import QgsDefaultValue, QgsEditorWidgetSetup, QgsField


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

# --- What tiling alone cannot do, and the two glyphs that cover it ---
#
# A marker line lays each tile down straight and rotated to the local
# bearing, so a tile that happens to span a bend is drawn across it -
# leaving a notch on the outside of the corner and an overlap on the
# inside. It also has no idea where the whole line ends. Both showed up
# in the maintainer's 2026-08-13 smoke test.
#
# The obvious fix - draw a plain line under the whole profile - is
# wrong: the profile has no baseline UNDER a merlon (the standard's own
# template is a bare square wave), so a continuous underlay would close
# every merlon into a box. Generating the profile as real geometry is
# also out: it would need page units inside a geometry generator, which
# at the time was believed impossible. **That belief was wrong** - see
# the 2026-08-15 roadmap entry: `@map_scale` does resolve there, and
# Table H-XXI's own Minimum Safe Distance Zone relies on it. This
# construction is left exactly as it is regardless, because it works
# and is signed off; recorded here only so the claim is not carried
# forward as fact.
#
# So the connector is placed only where it is needed. One tile long at
# an inner vertex, which is enough to bridge the bend without reaching
# the next merlon.
_RAMPART_CORNER_CONNECTOR_MM = _RAMPART_TILE_MM / 2.0

# The level run the profile opens and closes with. The tile's own ends
# contribute a quarter tile each; the maintainer asked for twice that
# ("the beginning and end line segment - increase the length by a
# factor of 2"), and the rest cannot come from the tile without
# changing the merlon rhythm they already signed off. So the tiling is
# pushed a quarter tile inward and this glyph fills what it vacates.
_RAMPART_END_RUN_MM = _RAMPART_TILE_MM / 2.0

_RAMPART_TILING_INSET_MM = _RAMPART_TILE_MM / 4.0

def _rampart_connector_layer(placement, length_mm, offset_along_line_mm=0.0):

    """
    One level-segment glyph on a marker line - see
    _RAMPART_CORNER_CONNECTOR_MM for what these are for.
    """

    glyph = QgsSvgMarkerSymbolLayer("")

    glyph.setSize(length_mm)

    glyph.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(
            "mct_rampart_connector_svg({colour}, {length}, {stroke})".format(
                colour=_RAMPART_GLYPH_COLOR_EXPRESSION,
                length=length_mm,
                stroke=_LINE_WIDTH_MM,
            )
        )
    )

    marker = QgsMarkerSymbol()

    marker.changeSymbolLayer(0, glyph)

    marker_line = QgsMarkerLineSymbolLayer(True)

    marker_line.setSubSymbol(marker)

    marker_line.setPlacements(placement)

    marker_line.setRotateSymbols(True)

    if offset_along_line_mm:

        marker_line.setOffsetAlongLine(offset_along_line_mm)

        marker_line.setOffsetAlongLineUnit(Qgis.RenderUnit.Millimeters)

    return marker_line


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
    follows a multi-segment path for free - with two gaps that tiling
    alone leaves, covered by connector glyphs at the inner vertices and
    at the two ends. See _RAMPART_CORNER_CONNECTOR_MM.

    Ramparts rise on the LEFT of PT1->PT2 travel, which is how the
    template draws them - see the module docstring on why that is a
    convention rather than a reading.
    """

    symbol = QgsLineSymbol()

    # Corner bridges first, so a merlon that lands on a bend still
    # draws over its connector rather than under it.
    symbol.changeSymbolLayer(
        0,
        _rampart_connector_layer(
            Qgis.MarkerLinePlacement.InnerVertices,
            _RAMPART_CORNER_CONNECTOR_MM,
        )
    )

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

    # Pushed inward so the opening level run comes out twice the
    # quarter-tile the glyph alone gives.
    marker_line.setOffsetAlongLine(_RAMPART_TILING_INSET_MM)

    marker_line.setOffsetAlongLineUnit(Qgis.RenderUnit.Millimeters)

    # Follow the line's own bearing, or the ramparts stay square to the
    # screen instead of to the rampart.
    marker_line.setRotateSymbols(True)

    symbol.appendSymbolLayer(marker_line)

    for placement in (
        Qgis.MarkerLinePlacement.FirstVertex,
        Qgis.MarkerLinePlacement.LastVertex,
    ):

        symbol.appendSymbolLayer(
            _rampart_connector_layer(placement, _RAMPART_END_RUN_MM)
        )

    return symbol


def _fortified_position_symbol():

    """
    Fortified Position (291000) - a plain bracket: a bar with a leg
    running out from each of its ends.

    **Built on Table H-XIX's own Obstacle Bypass Easy frame, at the
    maintainer's request** ("make the construction same as obstacle
    bypass easy, except the lines dont start/end with arrowhead but
    are plain, the user can figure out how to make it correctly").
    Three anchor points: PT1 and PT2 are the open ends of the two
    legs, and PT3's own perpendicular distance from the PT1-PT2 line
    places the bar and therefore sets the leg depth.

    That does swap the standard's own anchor roles - it calls PT1 and
    PT2 the front corners, i.e. the ends of the BAR. The picture that
    comes out is the same bracket either way, only which point the
    user clicks first changes, and the maintainer took that trade
    knowingly: it buys a construction that is already proven in this
    codebase and it hands the leg depth to the user, where the
    previous attempt tried to hold it at a fixed millimetre depth
    through a rotated SVG marker and did not draw the legs at all on
    a real map.

    Plain ends. Obstacle Bypass's own arrowhead chevrons are the one
    part deliberately not reused.
    """

    symbol = QgsLineSymbol()

    for index, geometry_expression in enumerate((
        "mct_obstacle_bypass_rear_easy($geometry)",
        "mct_obstacle_bypass_arrows($geometry)",
    )):

        line = QgsSimpleLineSymbolLayer()

        line.setWidth(_LINE_WIDTH_MM)

        _apply_affiliation_color(
            line, [QgsSymbolLayer.Property.StrokeColor]
        )

        line.setDataDefinedProperty(
            QgsSymbolLayer.Property.StrokeStyle,
            QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
        )

        inner = QgsLineSymbol()

        inner.changeSymbolLayer(0, line)

        generator = QgsGeometryGeneratorSymbolLayer.create({})

        generator.setSymbolType(QgsSymbol.SymbolType.Line)

        generator.setGeometryExpression(geometry_expression)

        generator.setSubSymbol(inner)

        if index == 0:
            symbol.changeSymbolLayer(0, generator)
        else:
            symbol.appendSymbolLayer(generator)

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

    # Without this a new feature's measure_type starts NULL and QGIS
    # adds its own null entry to the top of the dropdown - the "extra
    # null option unlike any other menu" the maintainer spotted. Every
    # other lines/areas layer in this appendix sets a default; this one
    # was simply missed.
    layer.setDefaultValueDefinition(
        fields.indexOf("measure_type"),
        QgsDefaultValue("'fortified_line'")
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
