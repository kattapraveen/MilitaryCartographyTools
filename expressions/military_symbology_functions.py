# -*- coding: utf-8 -*-

"""
Military symbology expression functions
for Military Cartography Tools
"""

import base64
import math
import random

from qgis.core import (
    QgsDistanceArea,
    QgsExpression,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    qgsfunction,
)

from ..military_symbology.sidc import build_sidc
from ..military_symbology.symbol_engine import render_symbol_base64_path


def _distance_area():

    """
    A QgsDistanceArea set up for geodesic (ellipsoid-surface)
    measurement in the current project's own CRS - matches
    core/coordinate_utils.py's true_bearing_and_distance() convention
    exactly, rather than a flat-plane calculation that would silently
    return nonsense (square degrees) for a layer in a geographic CRS
    like the AO/NAI area layers this plugin creates by default.

    Deliberately uses QgsProject.instance().crs() rather than taking a
    layer argument (e.g. via an @layer expression variable) - @layer is
    only populated when the calling UI explicitly builds its expression
    context with a layer scope, and that turned out NOT to be true of
    every QGIS expression entry point (confirmed live: QGIS's
    in-place/attribute-table field calculator toolbar evaluates
    mct_area_km2($geometry, @layer) with @layer unresolved, silently
    producing NULL - shown as "nan" in that widget's numeric preview -
    even though $geometry itself resolves fine). QgsProject.instance()
    is a plain Python singleton, always available regardless of which
    UI built the expression context, so this sidesteps that class of
    failure entirely. Correct for every layer this plugin itself
    creates (military_symbology/c2_measures.py and unit_layer.py
    both build their layers in the project's own CRS) - would be wrong
    only if a layer were later reprojected independently of the
    project, an edge case not worth the fragility of the @layer
    alternative.
    """

    distance_area = QgsDistanceArea()

    distance_area.setEllipsoid(
        "WGS84"
    )

    distance_area.setSourceCrs(
        QgsProject.instance().crs(),
        QgsProject.instance().transformContext()
    )

    return distance_area


# ============================================================
# SIDC-to-symbol renderer
# ============================================================

@qgsfunction(
    'mct_sidc_svg',
    group='Military Cartography Tools'
)
def mct_sidc_svg(values, feature=None, parent=None):

    """
    Renders a MIL-STD-2525/APP-6 symbol for a SIDC string, returning a
    "base64:<...>" path a QgsSvgMarkerSymbolLayer's own data-defined path
    property can use directly. Used as the one link between a feature's
    own attributes (usually via mct_build_sidc(), below) and the symbol
    drawn for it - see military_symbology/unit_layer.py.

    Optional second/third arguments: this plugin's own single "unique
    designation" attribute value (`text`), and which of milsymbol.js's
    own several render options it should be passed through as (`slot`,
    default `"uniqueDesignation"` if the text is given but no slot is) -
    so it appears wherever that SPECIFIC icon's own layout actually
    places it, rather than assuming every icon uses the same option key
    for what this project treats as one field. **Which slot to use is an
    ENTITY-SPECIFIC choice, not a global one** - see military_symbology/
    c2_measures.py's own _POINT_SIDC_EXPRESSION comment for the full
    2026-08-10 finding (confirmed by reading milsymbol.js's own per-icon
    position-config objects directly, not guessed): most icons use plain
    `uniqueDesignation` (Field T) for the position the standard's own
    EXAMPLE column shows; several (Amnesty Point, Checkpoint, Distress
    Call, and similar) use `uniqueDesignation1` instead for that same
    visual position; at least one (Unspecified Control Point) uses
    `additionalInformation1` instead again - milsymbol.js's own internal
    option NAMING doesn't consistently line up with the base standard's
    own Field T/T1 naming, or with itself across icons, so this can't be
    assumed and has to be checked per icon. A slot passed on an icon
    that doesn't define it is a harmless no-op (confirmed live).

    **2026-08-10 fix, found by the project maintainer's own live
    testing**: every Points layer's own "Unique designation" field
    (c2_measures.py's Points layer, defensive_control_measures.py's,
    control_measure_points.py's) was being collected in the attribute
    table but never actually passed into the rendered symbol at all -
    the SIDC string itself has no room for free text (it only encodes
    structured attributes), so it has to go through this SEPARATE options
    channel, which nothing was doing. Blank/None/empty values are
    treated as "no designation" rather than passing an empty string
    through (confirmed live: an empty option value still reserves the
    text's own layout space in some icons, drawing a subtle empty box/
    line where nothing should be).
    """

    if len(values) < 1:
        return "Need a SIDC string"

    sidc = str(values[0])

    text = values[1] if len(values) > 1 else None
    slot = str(values[2]) if len(values) > 2 and values[2] else "uniqueDesignation"

    # Optional FOURTH argument: a single colour for the whole icon, via
    # milsymbol's own `monoColor` option. Added 2026-08-12 for Table
    # H-XIX (Obstacles), whose symbols draw GREEN rather than in the
    # affiliation hue H.5.3 gives every other control measure - see
    # military_symbology/obstacle_control_measures.py. Without it the
    # obstacle POINTS would be the one part of that table stuck on
    # milsymbol's own affiliation colouring while its hand-built lines
    # and areas followed the green rule.
    #
    # Additive and default-off: every existing caller omits it and is
    # unaffected. Confirmed by probe that monoColor recolours stroke
    # AND fill across the whole icon, so it needs no post-processing of
    # the returned SVG.
    mono_color = str(values[3]) if len(values) > 3 and values[3] else None
    stroke_scale = float(values[4]) if len(values) > 4 and values[4] else None

    options = {}

    if text:
        options[slot] = str(text)

    if mono_color:
        options["monoColor"] = mono_color

    return render_symbol_base64_path(
        sidc, options or None, stroke_scale
    )


# ============================================================
# SIDC builder from named components
# ============================================================

@qgsfunction(
    'mct_build_sidc',
    group='Military Cartography Tools'
)
def mct_build_sidc(values, feature=None, parent=None):

    """
    Builds a 20-character SIDC from named components (affiliation, entity,
    symbol_set, echelon, status, headquarters, and optionally
    sector1_modifier, sector2_modifier) - calls straight into
    military_symbology/sidc.py's build_sidc() rather than re-implementing
    its field-position/code logic here, so that logic lives in exactly one
    place. Lets a unit layer's renderer go straight from a feature's own
    friendly attribute values to a rendered symbol
    (mct_sidc_svg(mct_build_sidc(...))) with no intermediate stored SIDC
    field to keep in sync. The two modifier arguments are optional (a
    6-argument call still works, e.g. mine_warfare's own expression,
    which has no sector modifier fields at all) - omitted or empty/falsy
    means "no modifier", matching build_sidc()'s own default.
    """

    if len(values) < 6:
        return (
            "Need affiliation, entity, symbol_set, echelon, status, "
            "headquarters"
        )

    affiliation, entity, symbol_set, echelon, status, headquarters = values[:6]
    sector1_modifier = values[6] if len(values) > 6 else None
    sector2_modifier = values[7] if len(values) > 7 else None

    try:

        return build_sidc(
            affiliation=str(affiliation),
            entity=str(entity),
            symbol_set=str(symbol_set),
            echelon=str(echelon),
            status=str(status),
            headquarters=bool(headquarters),
            sector1_modifier=str(sector1_modifier) if sector1_modifier else None,
            sector2_modifier=str(sector2_modifier) if sector2_modifier else None,
        )

    except KeyError as error:

        return str(error)


# ============================================================
# AO/NAI area & perimeter reporting
# ============================================================

@qgsfunction(
    'mct_area_km2',
    group='Military Cartography Tools'
)
def mct_area_km2(values, feature=None, parent=None):

    """
    A polygon's own geodesic area in square kilometres - the standard
    military reporting unit for an AO/NAI - via QgsDistanceArea rather
    than QGIS's own $area (which returns square DEGREES, not metres,
    on a layer in a geographic CRS unless the project's own Ellipsoidal
    measurement settings happen to be configured - not something this
    function should depend on to be correct). Use as
    mct_area_km2($geometry) - see _distance_area()'s own docstring for
    why this takes only a geometry, not a layer.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    area_m2 = _distance_area().measureArea(
        geometry
    )

    return area_m2 / 1_000_000.0


@qgsfunction(
    'mct_perimeter_km',
    group='Military Cartography Tools'
)
def mct_perimeter_km(values, feature=None, parent=None):

    """
    A polygon's own geodesic perimeter in kilometres - see
    mct_area_km2()'s own docstring for why QgsDistanceArea rather than
    QGIS's own $perimeter. Use as mct_perimeter_km($geometry).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    perimeter_m = _distance_area().measurePerimeter(
        geometry
    )

    return perimeter_m / 1000.0


@qgsfunction(
    'mct_length_km',
    group='Military Cartography Tools'
)
def mct_length_km(values, feature=None, parent=None):

    """
    A line's own geodesic length in kilometres - the line equivalent of
    mct_perimeter_km(), for phase lines/boundaries/axis of advance. Use
    as mct_length_km($geometry).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    length_m = _distance_area().measureLength(
        geometry
    )

    return length_m / 1000.0


# ============================================================
# Fortified Area's crenellated outline
# ============================================================

def _crenellated_ring_points(ring_points, tooth_count):

    """
    The actual crenellation algorithm behind mct_crenellate_outline() -
    factored out so it can be unit-tested directly on plain QgsPointXY
    lists, without going through the QgsExpression machinery. Walks the
    ring at `tooth_count` evenly-spaced "tooth" cycles (a tooth-plus-gap
    pair each), alternating a flat ground segment with a rectangular
    tooth offset outward by the same step distance - the same "square
    wave around a closed ring" construction used for the standard's own
    Fortified Area symbol (Table H-VII, code 151000). Confirmed by
    render-and-compare against the standard's own "TANGO" example: the
    output reads as a proper continuous castellated silhouette, matching
    that template, rather than the "beaded chain of floating squares"
    two earlier QgsMarkerLineSymbolLayer-based attempts both produced
    (see maneuver_control_measures.py's own module docstring for that
    history) - a real geometry construction was needed here, not a
    styling trick.

    Outward direction is resolved ONCE per ring from its own winding
    order (a shoelace signed-area test), not re-tested per segment
    against the centroid - the centroid-distance approach that was
    tried first gets confused in concave stretches of the boundary
    (flips the wrong way), where "farther from the centroid" stops
    reliably meaning "outward". Winding order is robust for any simple
    (non-self-intersecting) ring, concave included.
    """

    points = list(ring_points)

    if points[0] != points[-1]:
        points.append(points[0])

    ring_geometry = QgsGeometry.fromPolylineXY(points)
    perimeter = ring_geometry.length()

    if perimeter <= 0:
        return points

    tooth_count = max(4, int(tooth_count))
    step = perimeter / (tooth_count * 2)

    signed_area = 0.0

    for i in range(len(points) - 1):
        signed_area += (
            points[i].x() * points[i + 1].y()
            - points[i + 1].x() * points[i].y()
        )

    is_counterclockwise = signed_area > 0

    def interpolate(distance):

        point = ring_geometry.interpolate(distance % perimeter).asPoint()

        return QgsPointXY(point.x(), point.y())

    samples = [
        interpolate(k * step)
        for k in range(tooth_count * 2 + 1)
    ]

    output = [samples[0]]

    for k in range(0, tooth_count * 2, 2):

        ground_end = samples[k + 1]
        tooth_end = samples[k + 2]

        output.append(ground_end)

        dx = tooth_end.x() - ground_end.x()
        dy = tooth_end.y() - ground_end.y()
        length = math.hypot(dx, dy)

        if length == 0:
            output.append(tooth_end)
            continue

        dx, dy = dx / length, dy / length

        # For a counterclockwise ring, the outward normal is (dy, -dx);
        # for clockwise, the opposite.
        if is_counterclockwise:
            perp_x, perp_y = dy, -dx
        else:
            perp_x, perp_y = -dy, dx

        outer_start = QgsPointXY(
            ground_end.x() + perp_x * step,
            ground_end.y() + perp_y * step,
        )
        outer_end = QgsPointXY(
            tooth_end.x() + perp_x * step,
            tooth_end.y() + perp_y * step,
        )

        output.append(outer_start)
        output.append(outer_end)
        output.append(tooth_end)

    return output


@qgsfunction(
    'mct_crenellate_outline',
    group='Military Cartography Tools'
)
def mct_crenellate_outline(values, feature=None, parent=None):

    """
    A polygon's own exterior ring, redrawn as a continuous castellated
    (square-wave) outline - see _crenellated_ring_points()'s own
    comment for the algorithm and why it exists. Used as
    mct_crenellate_outline($geometry, 14) inside a
    QgsGeometryGeneratorSymbolLayer's own geometry expression (see
    maneuver_control_measures.py's own Fortified Area symbol) - the
    second argument is the number of teeth around the whole perimeter,
    defaulting to 14 if omitted (matching the standard's own "TANGO"
    example's own rough tooth density).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]
    tooth_count = int(values[1]) if len(values) > 1 else 14

    if geometry is None or geometry.isEmpty():
        return geometry

    polygon = geometry.constGet()

    if hasattr(polygon, "geometryN"):
        polygon = polygon.geometryN(0)

    exterior_ring = polygon.exteriorRing()

    ring_points = [
        QgsPointXY(exterior_ring.pointN(i))
        for i in range(exterior_ring.numPoints())
    ]

    crenellated_points = _crenellated_ring_points(
        ring_points,
        tooth_count
    )

    return QgsGeometry.fromPolylineXY(crenellated_points)


def _serrated_ring_points(ring_points, tooth_count, outward=True):

    """
    The sawtooth counterpart to _crenellated_ring_points() above, and
    deliberately the same walk-the-ring construction: Table H-XIX's own
    four obstacle zones (Obstacle Belt/Zone/Free Zone/Restricted Zone,
    270100-270400) draw a SERRATED boundary where Fortified Area draws
    a castellated one. Read off the standard's own template pictures
    (printed pages 573-574) at high magnification rather than from its
    text layer, which is badly OCR-mangled throughout this table.

    The tooth cycle is identical - a flat "ground" segment alternating
    with a tooth - so this shares crenellation's own hard-won details:
    outward direction resolved ONCE per ring from its winding order (a
    shoelace signed-area test), because the centroid-distance test that
    was tried first flips the wrong way in concave stretches.

    The one real difference is the tooth itself. Crenellation emits TWO
    offset corners, giving a square wave; serration emits ONE apex at
    the tooth's own midpoint, giving a triangle. Measured off the
    enlarged template: the apex rises about one tooth-base above the
    boundary, so the offset is `step`, exactly as crenellation offsets
    its corners - the two differ in shape, not in scale.

    `outward` picks which way the teeth point, and the four zones are
    NOT all the same: Obstacle Belt and Obstacle Zone spike outward,
    while Obstacle Free Zone and Obstacle Restricted Zone cut their
    teeth INWARD as notches bitten out of the shape. Caught by the
    project maintainer against the template pictures - the first build
    drew all four outward.
    """

    points = list(ring_points)

    if points[0] != points[-1]:
        points.append(points[0])

    ring_geometry = QgsGeometry.fromPolylineXY(points)
    perimeter = ring_geometry.length()

    if perimeter <= 0:
        return points

    tooth_count = max(4, int(tooth_count))
    step = perimeter / (tooth_count * 2)

    signed_area = 0.0

    for i in range(len(points) - 1):
        signed_area += (
            points[i].x() * points[i + 1].y()
            - points[i + 1].x() * points[i].y()
        )

    is_counterclockwise = signed_area > 0

    def interpolate(distance):

        point = ring_geometry.interpolate(distance % perimeter).asPoint()

        return QgsPointXY(point.x(), point.y())

    samples = [
        interpolate(k * step)
        for k in range(tooth_count * 2 + 1)
    ]

    output = [samples[0]]

    for k in range(0, tooth_count * 2, 2):

        ground_end = samples[k + 1]
        tooth_end = samples[k + 2]

        # The flat stretch between two teeth.
        output.append(ground_end)

        dx = tooth_end.x() - ground_end.x()
        dy = tooth_end.y() - ground_end.y()
        length = math.hypot(dx, dy)

        if length == 0:
            output.append(tooth_end)
            continue

        dx, dy = dx / length, dy / length

        # For a counterclockwise ring, the outward normal is (dy, -dx);
        # for clockwise, the opposite. Same test as crenellation.
        if is_counterclockwise:
            perp_x, perp_y = dy, -dx
        else:
            perp_x, perp_y = -dy, dx

        if not outward:
            perp_x, perp_y = -perp_x, -perp_y

        apex = QgsPointXY(
            (ground_end.x() + tooth_end.x()) / 2.0 + perp_x * step,
            (ground_end.y() + tooth_end.y()) / 2.0 + perp_y * step,
        )

        output.append(apex)
        output.append(tooth_end)

    return output


# The repeating glyphs of Table H-XIX's own wire-obstacle family
# (290301-290309). Only TWO shapes exist across all nine - a cross and
# an oval - which is the maintainer's own reading of the manual:
# every measure type is "a series of Xs" or "a series of 0s", varying
# only in the spacing and in which straight lines run through them.
#
# Inline SVG rather than QgsFontMarkerSymbolLayer: a font marker would
# tie the shapes to whatever glyphs the host machine's fonts happen to
# contain, on a standard this project renders against template
# pictures.
#
# "double_cross" is one marker holding TWO crosses, because Double
# Fence spaces the pair differently from the gap between pairs - and a
# marker line has only one interval, so the pair has to be a single
# glyph. Its viewBox is wider than the others' 100, so the caller sizes
# it up to keep each cross the same size as its siblings' (see
# _double_cross_geometry, which derives both from one number).
# Each entry is (viewBox width, paths, filled). The glyph box is 100
# tall; a marker line rotates these to follow the line, so "up" in the
# box is the side of the line the tooth points to.
_WIRE_GLYPH_GEOMETRY = {
    "cross": (100, ["M 16,16 L 84,84", "M 84,16 L 16,84"], False),
    # An OVAL, not a circle - the maintainer was explicit that the
    # concertina glyph is a "0" rather than an "O".
    "oval": (100, ["M 50,12 C 22,12 22,88 50,88 C 78,88 78,12 50,12 Z"],
             False),
    # Antitank Ditch: a triangular tooth standing off the line, hollow
    # while under construction and solid once completed. Its base sits
    # ON the line (y=100) and it points away from it.
    "ditch_tooth": (100, ["M 0,100 L 100,100 L 50,6 Z"], False),
    "ditch_tooth_filled": (100, ["M 0,100 L 100,100 L 50,6 Z"], True),
    # The same filled tooth pointing DOWN, for the reinforced ditch,
    # whose triangles hang below its line.
    "ditch_tooth_filled_down": (100, ["M 0,0 L 100,0 L 50,94 Z"], True),
    # Antitank Wall: "--v--v--v--", one CONTINUOUS path that runs
    # flat, dips into a V and comes back up. The line joins the edges
    # of the Vs; it does not run past them, and the Vs do not hang off
    # it - the maintainer's own correction, twice over.
    #
    # Laid out so tiles join seamlessly at gap 0: the V is equilateral
    # with side 50, and each tile carries half the flat at either end,
    # so consecutive tiles leave exactly one side length (50) of flat
    # between Vs - the spacing the maintainer specified.
    #
    # The flats sit at the box's VERTICAL CENTRE, so the glyph needs no
    # offset: centred on the line, its flats land on the geometry.
    "wall_vee": (100, ["M 0,50 L 25,50 L 50,93.3 L 75,50 L 100,50"], False),
    # Obstacle Line: the antitank wall's own profile with the triangles
    # the other way up - the maintainer's own description. Same tiling
    # and same spacing, mirrored about the flats.
    "obstacle_line_vee": (100, ["M 0,50 L 25,50 L 50,6.7 L 75,50 L 100,50"],
                          False),
    # Abatis: a single hump on an otherwise straight line, its legs
    # meeting the line - "_^____", in the maintainer's own notation.
    # Placed once near the start, NOT repeated.
    "abatis_hump": (100, ["M 4,100 L 50,12 L 96,100"], False),
}

_CROSS_PATHS = _WIRE_GLYPH_GEOMETRY["cross"][1]


def _double_cross_geometry(pair_gap):

    """
    Two crosses `pair_gap` glyph-widths apart, in a viewBox exactly
    wide enough to hold them.

    Both the viewBox width and the caller's own size multiplier are
    derived from `pair_gap` rather than written down separately - they
    are the same fact, and an earlier version had them as two literals
    (a 250 viewBox and a 2.5 multiplier) that would silently disagree
    the moment the spacing changed. Which it then did.
    """

    second = 100 * (1 + pair_gap)

    paths = list(_CROSS_PATHS) + [
        "M {},16 L {},84".format(second + 16, second + 84),
        "M {},16 L {},84".format(second + 84, second + 16),
    ]

    return 100 * (2 + pair_gap), paths, False


@qgsfunction(
    'mct_wire_glyph_svg',
    group='Military Cartography Tools'
)
def mct_wire_glyph_svg(values, feature=None, parent=None):

    """
    One wire-obstacle glyph as an inline "base64:<...>" SVG path.
    `kind` is a key of _WIRE_GLYPH_GEOMETRY, or "double_cross";
    `colour` is the obstacle's own green or black; `pair_gap` is the
    space between the two crosses of a double_cross, in glyph widths.
    """

    kind = str(values[0]) if values else "cross"
    colour = str(values[1]) if len(values) > 1 and values[1] else "rgb(0,155,0)"
    pair_gap = float(values[2]) if len(values) > 2 else 0.25

    if kind == "double_cross":
        geometry = _double_cross_geometry(pair_gap)
    else:
        geometry = _WIRE_GLYPH_GEOMETRY.get(kind)

    if geometry is None:
        return ""

    width, paths, filled = geometry

    body = "".join(
        '<path d="{}" fill="{}" stroke="{}" stroke-width="11"'
        ' stroke-linecap="round" stroke-linejoin="round"/>'.format(
            path, colour if filled else "none", colour
        )
        for path in paths
    )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="0 0 {width} 100" width="{width}" height="100">'
        "{body}</svg>"
    ).format(width=width, body=body)

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_abatis_line',
    group='Military Cartography Tools'
)
def mct_abatis_line(values, feature=None, parent=None):

    """
    Table H-XIX's own Abatis (280100): the line with a single triangular
    KINK near its start - "_^____", in the maintainer's own notation.

    Built as real geometry rather than a marker riding the line,
    because the hump must INTERRUPT the line: "the base of triangle
    touching the line should be clear, so it is like a kink in the
    beginning of line, not a full triangle". A marker drawn on top
    still leaves the straight line running underneath it, closing the
    triangle - which is exactly what the first attempt did.

    `at` is where the kink sits along the line and `size` how big it
    is, both as fractions of the line's own length, so the symbol
    scales with the feature.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    at = float(values[1]) if len(values) > 1 else 0.10
    size = float(values[2]) if len(values) > 2 else 0.06

    length = geometry.length()

    if length <= 0:
        return geometry

    half_width = length * size * 0.5
    height = length * size

    centre = length * at

    start_distance = max(0.0, centre - half_width)
    end_distance = min(length, centre + half_width)

    def at_distance(distance):

        point = geometry.interpolate(distance).asPoint()

        return QgsPointXY(point.x(), point.y())

    foot_in = at_distance(start_distance)
    foot_out = at_distance(end_distance)

    # Apex perpendicular to the line at the kink's own midpoint.
    dx = foot_out.x() - foot_in.x()
    dy = foot_out.y() - foot_in.y()

    span = math.hypot(dx, dy)

    if span == 0:
        return geometry

    apex = QgsPointXY(
        (foot_in.x() + foot_out.x()) / 2.0 - dy / span * height,
        (foot_in.y() + foot_out.y()) / 2.0 + dx / span * height,
    )

    points = [at_distance(0.0), foot_in, apex, foot_out]

    # The rest of the original line, kept vertex for vertex so a
    # multi-segment abatis still follows what was digitized.
    vertices = geometry.asPolyline()

    for vertex in vertices:

        if geometry.lineLocatePoint(
            QgsGeometry.fromPointXY(vertex)
        ) > end_distance:
            points.append(vertex)

    points.append(at_distance(length))

    return QgsGeometry.fromPolylineXY(points)


@qgsfunction(
    'mct_mine_cluster_arc',
    group='Military Cartography Tools'
)
def mct_mine_cluster_arc(values, feature=None, parent=None):

    """
    Table H-XIX's own Mine Cluster (290400): a dashed arc drawn OVER the
    dashed straight line between the feature's own two clicked points -
    the maintainer's own construction, corrected twice the same day.
    First: "make a semi-circle over it, radius 1/3... of the line" (not
    1/2, the standard's own printed figure). Then: "you are trimming
    the line instead of extending the semi-circle, the user when he
    clicks pt1 and pt2 expects the mine cluster to span that much, not
    reduce" - i.e. the arc's own SPAN must reach both clicked points,
    which a true 1/3-radius semicircle cannot do without leaving the
    line's own ends bare (the previous build's fix for THAT was to
    trim the line down to the arc's shorter span instead - exactly the
    "reduce" the maintainer rejected here).

    Reconciling both: this is a half-ELLIPSE, not a true semicircle.
    Its horizontal semi-axis is locked to exactly half the PT1-PT2
    span, so it touches both clicked points with nothing trimmed or
    left bare; "radius 1/3" is honoured as the vertical semi-axis (the
    dome's own height), which is flatter than a true semicircle (whose
    height would equal the full half-span) rather than narrower than
    one.

    The straight line is the feature's own digitized geometry, drawn
    separately and at its full length (see _mine_cluster_symbol); this
    returns only the arc. Real generated geometry rather than a
    fixed-size marker, so it scales with however far apart the two
    clicks are, the same reason mct_abatis_line and mct_decoy_chevron
    are geometry rather than markers.

    The dome bulges to the LEFT of the PT1->PT2 direction of travel
    (rotate the direction vector 90 degrees counterclockwise), which
    reads as "above" a left-to-right line on a normally-oriented map.
    The standard does not mandate a side, so this is a placement call
    rather than a measurement - the one part of this construction to
    re-check against a live smoke test.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    height_fraction = float(values[1]) if len(values) > 1 else (1.0 / 3.0)
    segments = int(values[2]) if len(values) > 2 else 24

    length = geometry.length()

    if length <= 0:
        return QgsGeometry()

    vertices = geometry.asPolyline()

    if len(vertices) < 2:
        return QgsGeometry()

    start = QgsPointXY(vertices[0])
    end = QgsPointXY(vertices[-1])

    dx = end.x() - start.x()
    dy = end.y() - start.y()

    span = math.hypot(dx, dy)

    if span == 0:
        return QgsGeometry()

    ux, uy = dx / span, dy / span
    nx, ny = -uy, ux

    mid_x = (start.x() + end.x()) / 2.0
    mid_y = (start.y() + end.y()) / 2.0

    # Horizontal semi-axis is HALF THE SPAN itself, not a fraction of
    # it - this is what makes the dome touch PT1/PT2 exactly, whatever
    # the height fraction is set to.
    half_span = span / 2.0
    height = length * height_fraction

    points = []

    for index in range(segments + 1):

        theta = math.pi * index / segments

        points.append(
            QgsPointXY(
                mid_x + half_span * math.cos(theta) * ux
                + height * math.sin(theta) * nx,
                mid_y + half_span * math.cos(theta) * uy
                + height * math.sin(theta) * ny,
            )
        )

    return QgsGeometry.fromPolylineXY(points)


@qgsfunction(
    'mct_trip_wire_geometry',
    group='Military Cartography Tools'
)
def mct_trip_wire_geometry(values, feature=None, parent=None):

    """
    Table H-XIX's own Trip Wire (290500, printed page 598) - the one
    the maintainer flagged in advance as "slightly complex, we will
    figure it out when it comes to that". Read directly off the
    standard's own template/draw-rules text.

    Three clicked anchor points, taken from the feature's own digitized
    vertices in order (NOT the raw PT1-PT2-PT3 polyline the digitizing
    tool connects them into - like mct_abatis_line and
    mct_mine_cluster_arc, this reinterprets the anchor POSITIONS rather
    than drawing the raw segments between them):

    - PT1, PT2: "Points 1 and 2 define the vertical straight line
      portion of the symbol." Drawn as a plain straight segment.
    - PT3: "defines an end of the horizontal line" - the OTHER end is
      PT1 itself (the only anchor left once PT2 is spent on the arc),
      giving a right-angle "horizontal" segment off the TOP of the
      vertical one, matching the template picture (the short segment
      sits right at PT1, not partway down). "Horizontal" only in the
      template's own axis-aligned example; here it is whatever
      direction PT3 was actually clicked in.
    - The template's own longer, unlabelled line running further down
      and past the vertical line is the same convention already caught
      once in this appendix (Light Line, H2): an EXAMPLE-column
      explanatory addition - here it links to a mine glyph the picture
      uses to show the trip wire's PURPOSE - not part of the control
      measure's own geometry, and not drawn here.

    "The distance between the line connecting points 1 and 2 and point
    3 is the radius of the 90 degree arc at the bottom of the symbol" -
    the PERPENDICULAR distance from PT3 to the infinite line through
    PT1-PT2, general enough to keep working even if PT3 is not clicked
    exactly perpendicular to PT1-PT2. The arc starts at PT2 tangent to
    the PT1->PT2 direction (continuing the vertical line's own way of
    travel) and curves 90 degrees to end tangent AWAY from PT3's own
    side - the hook in the template curls opposite the horizontal
    segment, not underneath it.

    Returned as ONE connected polyline (PT3 -> PT1 -> PT2 -> arc),
    since every segment genuinely shares an endpoint with the next.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    segments = int(values[1]) if len(values) > 1 else 12

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1 = QgsPointXY(vertices[0])
    pt2 = QgsPointXY(vertices[1])
    pt3 = QgsPointXY(vertices[2])

    dx = pt2.x() - pt1.x()
    dy = pt2.y() - pt1.y()

    span = math.hypot(dx, dy)

    if span == 0:
        return geometry

    # u: unit vector along PT1->PT2, the direction the arc continues
    # travelling in as it leaves PT2.
    ux, uy = dx / span, dy / span

    # Perpendicular distance from PT3 to the infinite line through
    # PT1-PT2, via the standard vector projection - not just
    # |PT3.x - PT1.x|, so an off-axis PT3 still resolves sensibly.
    to_pt3_x = pt3.x() - pt1.x()
    to_pt3_y = pt3.y() - pt1.y()

    along = to_pt3_x * ux + to_pt3_y * uy

    foot_x = pt1.x() + along * ux
    foot_y = pt1.y() + along * uy

    perp_x = pt3.x() - foot_x
    perp_y = pt3.y() - foot_y

    radius = math.hypot(perp_x, perp_y)

    if radius == 0:
        # PT3 sits ON the PT1-PT2 line - no side to curl toward, so the
        # arc collapses to a point at PT2 rather than guessing a side.
        return QgsGeometry.fromPolylineXY([pt3, pt1, pt2])

    # n: unit vector from the PT1-PT2 line TOWARD PT3. The arc curls in
    # the OPPOSITE direction (-n), away from the horizontal segment,
    # matching the template's own hook.
    nx, ny = perp_x / radius, perp_y / radius

    center_x = pt2.x() - radius * nx
    center_y = pt2.y() - radius * ny

    arc_points = []

    for index in range(segments + 1):

        # Sweeps from the radius vector pointing along +n (PT2's own
        # position relative to the centre) to +u (continuing PT1->PT2's
        # own direction) - a quarter turn, derived rather than assumed,
        # since n and u are perpendicular by construction.
        t = (index / segments) * (math.pi / 2.0)

        dir_x = nx * math.cos(t) + ux * math.sin(t)
        dir_y = ny * math.cos(t) + uy * math.sin(t)

        arc_points.append(
            QgsPointXY(
                center_x + radius * dir_x,
                center_y + radius * dir_y,
            )
        )

    return QgsGeometry.fromPolylineXY([pt3, pt1, pt2] + arc_points[1:])


@qgsfunction(
    'mct_scatter_points',
    group='Military Cartography Tools'
)
def mct_scatter_points(values, feature=None, parent=None):

    """
    Up to `count` points scattered inside a polygon, held clear of its
    own boundary AND of each other - the mine positions for Table
    H-XIX's own dynamic minefields.

    QgsRandomMarkerFillSymbolLayer was used first and is not good
    enough here: it clips the POINTS to the polygon, so a marker
    centred near the edge still hangs over the boundary, and it has no
    notion of minimum separation, so glyphs collide. The project
    maintainer's own report - "should not touch the perimeter, should
    not touch each other".

    Both distances are fractions of the shape's own size (sqrt of its
    area) rather than absolute map units, so one setting reads the same
    on a small minefield and a large one.

    Placement is seeded dart-throwing: sample, keep a point only if it
    clears the inset boundary and every point already kept, give up
    after a bounded number of attempts and return however many fitted.
    A long thin sliver simply gets fewer mines rather than no symbol at
    all.

    The seed is derived from the geometry's own centroid, so each
    feature gets its own arrangement while any one feature stays stable
    across repaints - QGIS re-evaluates this on every pan and zoom, and
    an unseeded scatter would crawl.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    count = int(values[1]) if len(values) > 1 else 7
    gap_fraction = float(values[2]) if len(values) > 2 else 0.26
    inset_fraction = float(values[3]) if len(values) > 3 else 0.14

    # Optional 5th/6th arguments return only every `modulus`-th placed
    # point starting at `remainder`. That is how a scattered field
    # alternates two mine types: the caller draws the same scatter
    # twice, taking (2, 0) with one glyph and (2, 1) with the other.
    # Splitting the SAME placement keeps both halves clear of each
    # other, which two independent scatters could not guarantee.
    modulus = int(values[4]) if len(values) > 4 else 1
    remainder = int(values[5]) if len(values) > 5 else 0

    area = geometry.area()

    if area <= 0:
        return QgsGeometry()

    scale = math.sqrt(area)

    inset = geometry.buffer(-inset_fraction * scale, 12)

    # A shape too thin to inset keeps its own outline as the limit
    # rather than vanishing.
    if inset is None or inset.isEmpty():
        inset = geometry

    minimum_gap = gap_fraction * scale

    box = inset.boundingBox()

    centroid = geometry.centroid().asPoint()

    # A STRING seed, not a tuple - random.Random accepts only
    # None/int/float/str/bytes, and a tuple raises TypeError, which
    # QgsExpression swallows into a null result (so the mines simply
    # vanished rather than erroring visibly).
    generator = random.Random(
        "{:.6f},{:.6f},{}".format(centroid.x(), centroid.y(), count)
    )

    placed = []

    for _ in range(count * 220):

        if len(placed) >= count:
            break

        x = generator.uniform(box.xMinimum(), box.xMaximum())
        y = generator.uniform(box.yMinimum(), box.yMaximum())

        candidate = QgsPointXY(x, y)

        if not inset.contains(QgsGeometry.fromPointXY(candidate)):
            continue

        if any(
            candidate.distance(existing) < minimum_gap
            for existing in placed
        ):
            continue

        placed.append(candidate)

    if not placed:
        return QgsGeometry.fromPointXY(
            inset.pointOnSurface().asPoint()
        )

    if modulus > 1:

        placed = [
            point
            for index, point in enumerate(placed)
            if index % modulus == remainder
        ]

        if not placed:
            return QgsGeometry()

    return QgsGeometry.fromMultiPointXY(placed)


@qgsfunction(
    'mct_decoy_chevron_svg',
    group='Military Cartography Tools'
)
def mct_decoy_chevron_svg(values, feature=None, parent=None):

    """
    The decoy chevron as an inline "base64:<...>" SVG path, for the
    FIXED-SIZE case - Dummy Minefield (270705), where the chevron sits
    above a static box on a single anchor point.

    mct_decoy_chevron() cannot serve here: it returns map-unit geometry
    sized from a polygon, and a minefield point has no polygon and must
    not change size with the zoom.

    QGIS's own marker shapes have no symmetric open V. ArrowHead was
    tried first and renders as a diagonal arrow, not a chevron (caught
    by render), and a Triangle would close the bottom edge the template
    leaves open. Drawing the two strokes directly is exact, and reuses
    the same base64 inline-SVG path format the milsymbol pipeline
    already feeds to QgsSvgMarkerSymbolLayer.
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,155,0)"

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 60"'
        ' width="100" height="60">'
        '<path d="M 4,54 L 50,8 L 96,54" fill="none"'
        f' stroke="{colour}" stroke-width="6"'
        ' stroke-dasharray="13,9" stroke-linecap="butt"/>'
        '</svg>'
    )

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_decoy_chevron',
    group='Military Cartography Tools'
)
def mct_decoy_chevron(values, feature=None, parent=None):

    """
    The dashed inverted-V drawn inside Table H-XIX's own Decoy Mined
    Area and Decoy Mined Area, Fenced (270900/270901, printed pages
    592-593) - the mark that distinguishes a decoy from a real Mined
    Area, which is otherwise the identical boundary-plus-"M" symbol.

    Returned as real map-unit geometry for a geometry generator rather
    than drawn as a fixed-size marker, because the standard's own draw
    rules make this block "moveable and scalable as a block within the
    area" - it has to grow with the polygon, not sit at a fixed
    millimetre size.

    Proportions measured off the enlarged template rather than guessed:
    the apex sits about 0.185 of the shape's height above centre and
    the two arms end about 0.20 below it.

    The half-span is the one caller-tunable part (second argument,
    default 0.24 of the width). Decoy Mined Area and Decoy Mined Area,
    Fenced draw the chevron INSIDE the shape, where the template keeps
    it well short of the sides. Dummy Minefield, Dynamic draws it ABOVE
    the shape instead, and the maintainer asked for it to span the
    area's full horizontal extent there - so that caller passes 0.5.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    half_span_fraction = float(values[1]) if len(values) > 1 else 0.24

    box = geometry.boundingBox()

    centre_x = (box.xMinimum() + box.xMaximum()) / 2.0
    centre_y = (box.yMinimum() + box.yMaximum()) / 2.0

    half_span = box.width() * half_span_fraction
    apex_rise = box.height() * 0.185
    arm_drop = box.height() * 0.20

    return QgsGeometry.fromPolylineXY(
        [
            QgsPointXY(centre_x - half_span, centre_y - arm_drop),
            QgsPointXY(centre_x, centre_y + apex_rise),
            QgsPointXY(centre_x + half_span, centre_y - arm_drop),
        ]
    )


@qgsfunction(
    'mct_serrate_outline',
    group='Military Cartography Tools'
)
def mct_serrate_outline(values, feature=None, parent=None):

    """
    A polygon's own exterior ring, redrawn as a continuous SERRATED
    (sawtooth) outline - see _serrated_ring_points() for the algorithm.
    Used as mct_serrate_outline($geometry, 14) inside a
    QgsGeometryGeneratorSymbolLayer's own geometry expression (see
    obstacle_control_measures.py's own obstacle-zone symbols).

    Second argument: teeth around the whole perimeter, default 14.
    Third argument: whether the teeth point OUTWARD, default true -
    pass false for the two zones whose teeth bite inward (Obstacle Free
    Zone and Obstacle Restricted Zone).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]
    tooth_count = int(values[1]) if len(values) > 1 else 14
    outward = bool(values[2]) if len(values) > 2 else True

    if geometry is None or geometry.isEmpty():
        return geometry

    polygon = geometry.constGet()

    if hasattr(polygon, "geometryN"):
        polygon = polygon.geometryN(0)

    exterior_ring = polygon.exteriorRing()

    if exterior_ring is None:
        return geometry

    ring_points = [
        QgsPointXY(exterior_ring.pointN(i))
        for i in range(exterior_ring.numPoints())
    ]

    return QgsGeometry.fromPolylineXY(
        _serrated_ring_points(ring_points, tooth_count, outward)
    )



def _azimuth_radians(start, end):

    """
    Compass bearing (0 = due "up"/+Y, clockwise-positive) from start to
    end, in radians - plain Python trig, not QGIS's own azimuth()/
    project() expression functions. Those two ARE available inside a
    QgsGeometryGeneratorSymbolLayer's own expression, and an earlier
    attempt at mct_axis_of_advance_ribbon() (below) was built entirely
    that way, chaining ~20 nested with_variable() calls - it produced
    the right shape (confirmed against a plain-Python/PIL debug
    render), but each variable reference re-evaluates every variable it
    depends on from scratch, and QGIS's own with_variable() doesn't
    memoize, so the total cost grows exponentially with chain depth: a
    direct measurement of the real expression (not a hunch) showed
    evaluation time roughly DOUBLING at every added variable, reaching
    over a second by variable 17 of ~24 and timing out completely with
    the remaining ones added. Moved to a plain Python function for
    exactly the reason mct_crenellate_outline() already is above -
    real point/trig math belongs in Python, not a deeply chained
    expression.
    """

    return math.atan2(end.x() - start.x(), end.y() - start.y())


def _project_point(origin, distance, azimuth_radians):

    return QgsPointXY(
        origin.x() + distance * math.sin(azimuth_radians),
        origin.y() + distance * math.cos(azimuth_radians),
    )


def _distance(a, b):

    return math.hypot(b.x() - a.x(), b.y() - a.y())


def _quadratic_bezier_points(start, control, end, segment_count=8):

    """
    `segment_count + 1` points tracing a quadratic Bezier curve from
    start to end through control - used to give the ribbon's own
    criss-crossing region a soft curve instead of two straight lines
    meeting at a sharp point, per the project maintainer's own explicit
    request ("can we have the criss-crossing lines slightly curved so
    as to look natural"). Returns plain points, not a QgsGeometry - the
    caller threads these into its own larger polyline alongside the
    straight shaft/arrowhead segments.
    """

    points = []

    for step in range(segment_count + 1):

        t = step / segment_count
        one_minus_t = 1 - t

        x = (
            one_minus_t * one_minus_t * start.x()
            + 2 * one_minus_t * t * control.x()
            + t * t * end.x()
        )

        y = (
            one_minus_t * one_minus_t * start.y()
            + 2 * one_minus_t * t * control.y()
            + t * t * end.y()
        )

        points.append(QgsPointXY(x, y))

    return points


def _rounded_corner_points(previous_point, corner, next_point, radius, segment_count=4):

    """
    A short curve replacing the sharp vertex at `corner` on the
    polyline previous_point -> corner -> next_point - classic "corner
    cutting": the curve runs from a point `radius` back toward
    previous_point to a point `radius` forward toward next_point, using
    `corner` itself as the Bezier control point. `radius` is clamped to
    40% of whichever adjoining segment is shorter, so a short segment
    never gets over-cut past its own midpoint.

    Deliberately built by cutting back along the polyline's own ALREADY-
    STRAIGHT segments (not by computing two separately-offset points
    using different headings, the way an earlier attempt at rounding
    Point 2 did) - that earlier version produced a real self-
    intersecting loop on the inner side of a bend (confirmed on a real
    render), because the two offset points could end up on the wrong
    side of each other. Cutting back along one single, already-
    well-defined direction on each side avoids that failure mode
    entirely.
    """

    radius = min(
        radius,
        _distance(corner, previous_point) * 0.4,
        _distance(corner, next_point) * 0.4,
    )

    fraction_back = radius / _distance(corner, previous_point)
    fraction_forward = radius / _distance(corner, next_point)

    fillet_start = QgsPointXY(
        corner.x() + (previous_point.x() - corner.x()) * fraction_back,
        corner.y() + (previous_point.y() - corner.y()) * fraction_back,
    )

    fillet_end = QgsPointXY(
        corner.x() + (next_point.x() - corner.x()) * fraction_forward,
        corner.y() + (next_point.y() - corner.y()) * fraction_forward,
    )

    return _quadratic_bezier_points(fillet_start, corner, fillet_end, segment_count)


def _line_intersection(a1, a2, b1, b2):

    """
    The point where the INFINITE lines through (a1,a2) and (b1,b2)
    cross - not a segment-bounded intersection, since both callers here
    (mct_axis_of_advance_ribbon()'s own ribbon edges and the crossing-
    point function below) want the crossing of the two edges' own
    underlying straight lines, and the actual drawn segments are
    already known (from other geometry) to cross within their own
    bounds. Returns None for parallel/degenerate input rather than
    raising - callers fall back to a simpler approximation in that case.
    Standard two-line determinant formula.
    """

    x1, y1 = a1.x(), a1.y()
    x2, y2 = a2.x(), a2.y()
    x3, y3 = b1.x(), b1.y()
    x4, y4 = b2.x(), b2.y()

    denominator = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)

    if denominator == 0:
        return None

    t = (
        (x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)
    ) / denominator

    return QgsPointXY(x1 + t * (x2 - x1), y1 + t * (y2 - y1))


def _axis_of_advance_ribbon_geometry(p1, p2, p3, width_ratio, arrow_width_ratio=1.0):

    """
    The shared point/measurement math behind mct_axis_of_advance_
    ribbon()'s own outline AND the crossing-point glyph's own placement
    (military_symbology/offensive_control_measures.py's Attack
    Helicopter variant) - factored out so both stay in lock-step if the
    ribbon's own tuning (width_ratio, attach_ratio, ...) ever changes;
    see mct_axis_of_advance_ribbon()'s own docstring for the full
    construction narrative this implements. Returns a dict of every
    named point/measurement either caller needs.

    `arrow_width_ratio` (default 1.0, i.e. the arrowhead is exactly as
    wide as the shaft) - Main Attack's own arrowhead is 20% WIDER than
    its shaft (2026-08-10, the project maintainer's own explicit
    instruction), unlike Airborne/Aviation/Attack Helicopter's own
    crossed ribbon, whose arrowhead is already effectively wider than
    the shaft through the crossing itself. `corner_left`/`corner_right`
    below are always the ARROWHEAD's own corners (using `arrow_width`);
    `shaft_corner_left`/`shaft_corner_right` are the shaft's own
    narrower width projected onto the same back-edge point, needed only
    by the non-crossed construction's own straight gap-closing segment
    out to the (now possibly wider) arrowhead corner - see
    mct_axis_of_advance_ribbon()'s own `crossed=False` branch.
    """

    total = math.hypot(p3.x() - p1.x(), p3.y() - p1.y())

    if total == 0:
        return None

    width = total * width_ratio
    arrow_width = width * arrow_width_ratio

    # Equilateral triangle: base = 2 * arrow_width, so height = base *
    # sin(60 degrees) = arrow_width * sqrt(3).
    barb_length = arrow_width * math.sqrt(3)

    # How far in from each back corner the shaft's own edges actually
    # attach, as a fraction of the way from the base's own centre to
    # that corner (0 = dead centre, 1 = exactly at the corner) - see
    # mct_axis_of_advance_ribbon()'s own docstring for the full history.
    attach_ratio = 0.55

    az12 = _azimuth_radians(p1, p2)
    az23 = _azimuth_radians(p2, p3)
    az_bend = (az12 + az23) / 2

    half_pi = math.pi / 2

    p1_left = _project_point(p1, width, az12 - half_pi)
    p1_right = _project_point(p1, width, az12 + half_pi)

    p2_left = _project_point(p2, width, az_bend - half_pi)
    p2_right = _project_point(p2, width, az_bend + half_pi)

    barb_base = _project_point(p3, barb_length, az23 + math.pi)
    corner_left = _project_point(barb_base, arrow_width, az23 - half_pi)
    corner_right = _project_point(barb_base, arrow_width, az23 + half_pi)

    shaft_corner_left = _project_point(barb_base, width, az23 - half_pi)
    shaft_corner_right = _project_point(barb_base, width, az23 + half_pi)

    attach_left = QgsPointXY(
        barb_base.x() + (corner_left.x() - barb_base.x()) * attach_ratio,
        barb_base.y() + (corner_left.y() - barb_base.y()) * attach_ratio,
    )

    attach_right = QgsPointXY(
        barb_base.x() + (corner_right.x() - barb_base.x()) * attach_ratio,
        barb_base.y() + (corner_right.y() - barb_base.y()) * attach_ratio,
    )

    return {
        "width": width,
        "p1_left": p1_left,
        "p1_right": p1_right,
        "p2_left": p2_left,
        "p2_right": p2_right,
        "corner_left": corner_left,
        "corner_right": corner_right,
        "shaft_corner_left": shaft_corner_left,
        "shaft_corner_right": shaft_corner_right,
        "attach_left": attach_left,
        "attach_right": attach_right,
    }


@qgsfunction(
    'mct_axis_of_advance_crossing_point',
    group='Military Cartography Tools'
)
def mct_axis_of_advance_crossing_point(values, feature=None, parent=None):

    """
    The ribbon's own actual "point of intersection" - where the two
    ribbon edges genuinely cross, computed as the true line-line
    intersection of edge(p2_left, attach_right) and edge(p2_right,
    attach_left) (the same two lines mct_axis_of_advance_ribbon() draws
    as the STRAIGHT run of each edge, past its own fillet at Point 2 -
    the fillet only trims the corner, it doesn't change that line's own
    direction, so the infinite-line intersection lands in the same spot
    the drawn, fillet-trimmed segments actually cross).

    Added 2026-08-10 for Attack Helicopter's own crossing-point glyph
    (_attack_helicopter_direction_glyph_layer()) - an EARLIER version of
    that glyph used a plain midpoint-of-Point-2-and-Point-3 expression
    instead, which the project maintainer found consistently placed the
    glyph "slightly right and above the point of intersection" across
    several different arrow geometries they tried - a systematic offset
    (not a per-geometry fluke), because the ribbon's own crossing point
    is a function of `width` (which scales with the line's own total
    length) and `attach_ratio`, not simply the arithmetic midpoint of
    Point 2 and Point 3. This function computes the REAL crossing
    directly from the same geometry math the ribbon itself uses (see
    _axis_of_advance_ribbon_geometry()), rather than approximating it.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    width_ratio = float(values[1]) if len(values) > 1 else 0.08

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    p1 = QgsPointXY(line.pointN(0))
    p2 = QgsPointXY(line.pointN(1))
    p3 = QgsPointXY(line.pointN(2))

    ribbon = _axis_of_advance_ribbon_geometry(p1, p2, p3, width_ratio)

    if ribbon is None:
        return geometry

    crossing = _line_intersection(
        ribbon["p2_left"], ribbon["attach_right"],
        ribbon["p2_right"], ribbon["attach_left"],
    )

    if crossing is None:

        # Parallel/degenerate edges (shouldn't happen for a real
        # 3-point axis of advance) - fall back to the simple Point-2/
        # Point-3 midpoint rather than failing the expression outright.
        crossing = QgsPointXY(
            (p2.x() + p3.x()) / 2,
            (p2.y() + p3.y()) / 2,
        )

    return QgsGeometry.fromPointXY(crossing)


def _offset_arrowhead_chevron(
    corner_left, corner_right, tip,
    shaft_corner_left, shaft_corner_right
):

    """
    A second chevron nested inside the arrowhead's own two front edges
    (corner_left->tip, corner_right->tip) - Main Attack's own "double
    lined" arrowhead, 2026-08-10 ("add another line connecting the two
    edges of the shaft near the triangle following the shape of the
    triangle keeping the same distance", the project maintainer's own
    words, with a reference image showing two parallel chevron lines).
    Main Attack's own only, frozen once confirmed - Supporting Attack
    replicates the rest of "the master arrow" but explicitly NOT this
    part ("main attack requires the inner chevron, supporting attack
    does not require it", the maintainer's own words, 2026-08-11).

    The inner chevron's own two base points are `shaft_corner_left`/
    `shaft_corner_right` EXACTLY - "touching the tip of the arrow
    shaft, where the small line joining the triangle begins", the
    maintainer's own correction after an earlier attempt placed them
    elsewhere. Each inner edge then runs from its own base point along
    the SAME AZIMUTH as the corresponding real edge (`corner_left`-to-
    `tip`'s own azimuth for the left side, `corner_right`-to-`tip`'s
    own for the right) - a genuine parallel line through a FIXED point,
    not an arbitrary perpendicular offset distance. This is the
    2026-08-11 correction: an earlier version offset the real edges
    inward by a chosen constant distance first and only THEN forced
    the base points onto `shaft_corner_left`/`shaft_corner_right`,
    which - since that offset distance was independent of how far
    `shaft_corner_left` itself actually sits from the real edge line -
    made the inner edge visibly NOT parallel to the real one ("the
    inner chevron is slanting slightly with respect to the main
    triangle", the maintainer's own words). Anchoring the base point
    AND the direction together, rather than the base point and an
    independently-chosen offset distance, is what actually guarantees
    parallel sides.

    Returns a 3-point polyline [shaft_corner_left, inner_tip,
    shaft_corner_right], or None if the two inner edges are parallel to
    each other (no real intersection - shouldn't happen for a real
    axis of advance, but checked rather than assumed).
    """

    az_left = _azimuth_radians(corner_left, tip)
    az_right = _azimuth_radians(corner_right, tip)

    inner_left_b = _project_point(shaft_corner_left, 1.0, az_left)
    inner_right_b = _project_point(shaft_corner_right, 1.0, az_right)

    inner_tip = _line_intersection(
        shaft_corner_left, inner_left_b, shaft_corner_right, inner_right_b
    )

    if inner_tip is None:
        return None

    return QgsGeometry.fromPolylineXY(
        [shaft_corner_left, inner_tip, shaft_corner_right]
    )


@qgsfunction(
    'mct_axis_of_advance_ribbon',
    group='Military Cartography Tools'
)
def mct_axis_of_advance_ribbon(values, feature=None, parent=None):

    """
    Table H-X's own real Axis of Advance construction (H.5.13.1, page
    428) - a variable-width tapered ribbon computed from the user's own
    3-point digitized line (Point 1 = origin/shaft start, Point 2 =
    turn/bend, Point 3 = arrowhead tip), replacing the single-thick-
    line-plus-filled-arrowhead approximation every Axis of Advance
    sub-type used until 2026-08-10 (see offensive_control_measures.py's
    own module docstring for that history, and _axis_of_advance_ribbon_
    symbol()'s own comment for how this is wired into a
    QgsGeometryGeneratorSymbolLayer).

    Only the first 3 vertices of the feature's own geometry are used -
    matching the standard's own minimum anchor-point count for this
    family (Point 1/N-1/N in the standard's own numbering, here always
    exactly 3 rather than the general N-point case, a deliberate
    simplification for a mouse-driven 3-click digitizing workflow, per
    the project maintainer's own request).

    **2026-08-10, three rounds of follow-up, each matched directly
    against a reference picture of the standard's own template (or the
    project maintainer's own live QGIS render) rather than guessed**:
      - The shaft is exactly as wide as the arrowhead's own widest
        point - `width_ratio` drives both, a single shared value.
      - The arrowhead is a true EQUILATERAL triangle, not merely
        isosceles - its own height (`barb_length`) is DERIVED from
        `width` (`width * sqrt(3)`, the height of an equilateral
        triangle whose base is `2 * width`) rather than a second,
        independently-tunable ratio that could drift out of an
        equilateral proportion.
      - The shaft's two edges do NOT terminate at the arrowhead's own
        back CORNERS - they cross to the opposite side and attach
        partway along the back EDGE instead (`_ARROWHEAD_ATTACH_
        RATIO`, a fraction of the way from the base's own centre
        toward each corner), per the project maintainer's own direct
        observation against a zoomed crop of the real template picture
        ("the lines from the shaft do not hit the triangle edges but
        slightly along the third side").
      - The bend (Point 2) gets a short, ROUNDED fillet - not a long
        bulging curve spanning the whole shaft-to-arrowhead distance,
        which read as bulging too far outward once actually compared
        against a live render. After the fillet, each edge runs dead
        STRAIGHT the rest of the way to its own attachment point -
        the project maintainer's own explicit simplification ("at the
        point of turn, let the turn be a natural curve thereafter it
        can be straight").

    Construction, in the feature's own local coordinates:
      - Point 1 to a short distance before Point 2: a straight shaft,
        offset `width` either side of the centreline.
      - AT Point 2: a short rounded fillet (see _quadratic_bezier_
        points()) between the "as if the shaft kept its Point-1-to-
        Point-2 heading" offset point and the "as if it already had
        Point-2-to-Point-3's heading" offset point - softens the sharp
        mitred corner a straight offset alone would produce.
      - From just past the fillet, straight to the OPPOSITE side's own
        attachment point on the arrowhead's back edge (this is what
        creates the criss-cross - each edge ends up on the side
        opposite the one it started on).
      - The arrowhead's own tip is Point 3; its own two sides
        (attachment point to tip) are straight.
    Returned as a single MultiLineString (3 pieces: two ribbon edges +
    the arrowhead's own outline) via QgsGeometry.collectGeometry() - an
    unfilled outline, matching the standard's own template picture (a
    bold outline, not a solid fill).

    `width_ratio` is relative to the drawn Point-1-to-Point-3 distance,
    not an absolute map-unit width - deliberately, so the same symbol
    reads correctly regardless of whether the layer's own CRS is
    geographic (degrees) or projected (metres); an earlier, fixed-
    absolute-width version (following an outside suggestion that
    assumed a projected metric CRS) would have produced a symbol the
    size of a small country in this project's own default WGS84 layers.
    **The default width ratio and the attachment inset (`attach_ratio`
    below) are both explicit placeholders, not yet tuned against the
    standard's own template picture precisely** - the project
    maintainer's own explicit instruction was to get the construction
    technique right first, "we will fill the data later".

    `crossed` (third argument, default true) - whether the shaft's own
    two edges cross to the OPPOSITE side's attachment point near the
    arrowhead (Friendly Airborne/Aviation/Attack Helicopter, all built
    this way first) or run straight to their OWN SAME-SIDE corner
    instead (Main Attack, added 2026-08-10 - "this arrow is similar
    except the lines do not crossover", the project maintainer's own
    words). `False` skips the attachment-inset math entirely.

    `arrow_width_ratio` (fourth argument, default 1.0) - how much wider
    the arrowhead is than the shaft, as a multiplier on `width_ratio`.
    Main Attack's own arrowhead is 20% wider than its shaft (2026-08-10,
    the project maintainer's own explicit instruction, "the arrowhead
    is of the same width as the shaft, increase the arrowhead width by
    20%... join the edge of the shaft tip and the arrowhead tips with a
    straight line") - when the arrowhead is wider than the shaft AND
    `crossed=False`, each edge needs one extra straight segment from its
    own shaft-width corner out to the (now wider) arrowhead corner, the
    same "close the visible gap" technique the CROSSED construction's
    own inset attachment points already needed for a different reason -
    see _axis_of_advance_ribbon_geometry()'s own docstring for the full
    `shaft_corner_left`/`shaft_corner_right` vs `corner_left`/
    `corner_right` distinction this relies on.

    `double_lined_arrowhead` (fifth argument, default false) - Main
    Attack's own turn only (see this project's own "master arrow"
    naming - _MASTER_ARROW_VARIANTS in offensive_control_measures.py -
    and _offset_arrowhead_chevron()'s own docstring for why Supporting
    Attack, which otherwise replicates the master arrow verbatim,
    explicitly does NOT get this): a second chevron line nested inside
    the arrowhead's own two front edges, with its own two base points
    landing exactly on the actual shaft edges. Adds a 4th piece to the
    returned MultiLineString when true.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    width_ratio = float(values[1]) if len(values) > 1 else 0.08
    crossed = bool(values[2]) if len(values) > 2 else True
    arrow_width_ratio = float(values[3]) if len(values) > 3 else 1.0
    double_lined_arrowhead = bool(values[4]) if len(values) > 4 else False

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    p1 = QgsPointXY(line.pointN(0))
    p2 = QgsPointXY(line.pointN(1))
    p3 = QgsPointXY(line.pointN(2))

    ribbon = _axis_of_advance_ribbon_geometry(
        p1, p2, p3, width_ratio, arrow_width_ratio
    )

    if ribbon is None:
        return geometry

    width = ribbon["width"]
    p1_left = ribbon["p1_left"]
    p1_right = ribbon["p1_right"]
    p2_left = ribbon["p2_left"]
    p2_right = ribbon["p2_right"]
    corner_left = ribbon["corner_left"]
    corner_right = ribbon["corner_right"]
    shaft_corner_left = ribbon["shaft_corner_left"]
    shaft_corner_right = ribbon["shaft_corner_right"]
    attach_left = ribbon["attach_left"]
    attach_right = ribbon["attach_right"]

    # Each edge runs STRAIGHT from Point 2's own offset point to the
    # opposite attachment point - the criss-crossing curve two earlier
    # rounds tried (first a short one confined to the bend, then a
    # long shallow one spanning the whole way to the arrowhead) both
    # read as visibly wrong once the maintainer compared a real render
    # side-by-side with the standard's own template picture. Only the
    # corner AT Point 2 itself gets a small rounding (see
    # _rounded_corner_points()) - "the corner where the lines turn can
    # be slightly rounded", the maintainer's own explicit request,
    # everything else straight.
    fillet_radius = width * 1.5

    if crossed:

        left_edge = QgsGeometry.fromPolylineXY(
            [p1_left]
            + _rounded_corner_points(p1_left, p2_left, attach_right, fillet_radius)
            + [attach_right, corner_right]
        )

        right_edge = QgsGeometry.fromPolylineXY(
            [p1_right]
            + _rounded_corner_points(p1_right, p2_right, attach_left, fillet_radius)
            + [attach_left, corner_left]
        )

    else:

        # Each edge runs to its own SAME-SIDE shaft-width corner, then
        # (when the arrowhead is wider than the shaft) one more
        # straight segment out to the arrowhead's own actual corner -
        # otherwise there'd be a visible gap/notch where the narrower
        # shaft meets the wider arrowhead, the non-crossed equivalent
        # of the crossed construction's own gap-closing fix.
        left_edge = QgsGeometry.fromPolylineXY(
            [p1_left]
            + _rounded_corner_points(p1_left, p2_left, shaft_corner_left, fillet_radius)
            + [shaft_corner_left, corner_left]
        )

        right_edge = QgsGeometry.fromPolylineXY(
            [p1_right]
            + _rounded_corner_points(p1_right, p2_right, shaft_corner_right, fillet_radius)
            + [shaft_corner_right, corner_right]
        )

    arrowhead = QgsGeometry.fromPolylineXY(
        [corner_left, p3, corner_right]
    )

    pieces = [left_edge, right_edge, arrowhead]

    if double_lined_arrowhead:

        inner_chevron = _offset_arrowhead_chevron(
            corner_left, corner_right, p3,
            shaft_corner_left, shaft_corner_right
        )

        if inner_chevron is not None:

            pieces.append(inner_chevron)

    return QgsGeometry.collectGeometry(pieces)


@qgsfunction(
    'mct_axis_of_advance_outer_chevron',
    group='Military Cartography Tools'
)
def mct_axis_of_advance_outer_chevron(values, feature=None, parent=None):

    """
    Axis of Advance for a Feint's own distinguishing mark (2026-08-11,
    the project maintainer's own explicit instruction, built on top of
    Supporting Attack's own base construction - see this project's own
    "master arrow" naming): a second chevron OUTSIDE the real
    arrowhead, at a constant perpendicular `gap` from each of its own
    two front edges - the mirror image of _offset_arrowhead_chevron()'s
    own inner chevron (Main Attack's own only), same "parallel line
    through a fixed point" technique, just offset outward instead of
    inward, and with its own two base points anchored a fixed `gap`
    distance out from the real arrowhead's own corners (not touching
    the shaft the way the inner chevron does - the maintainer's own
    instruction described this one purely in terms of "outside the
    arrowhead", not the shaft).

    Rendered DASHED regardless of the feature's own "status" (present/
    planned) - this is a fixed structural mark distinguishing a Feint,
    not the shaft/arrowhead's own status-driven solid/dashed line style
    - so this returns a geometry for its OWN separate
    QgsGeometryGeneratorSymbolLayer with a fixed dashed pen, not an
    extra piece folded into mct_axis_of_advance_ribbon()'s own
    MultiLineString (which shares one status-driven stroke style for
    the whole shaft+arrowhead).

    `gap_ratio` (fourth argument, default 1.0) is relative to `width`
    (the shaft's own real width, `total * width_ratio`), the same
    "proportional to the drawn geometry, not an absolute map-unit
    distance" convention every other measurement in this construction
    already uses.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    width_ratio = float(values[1]) if len(values) > 1 else 0.08
    arrow_width_ratio = float(values[2]) if len(values) > 2 else 1.2
    gap_ratio = float(values[3]) if len(values) > 3 else 1.0

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    p1 = QgsPointXY(line.pointN(0))
    p2 = QgsPointXY(line.pointN(1))
    p3 = QgsPointXY(line.pointN(2))

    ribbon = _axis_of_advance_ribbon_geometry(
        p1, p2, p3, width_ratio, arrow_width_ratio
    )

    if ribbon is None:
        return geometry

    width = ribbon["width"]
    corner_left = ribbon["corner_left"]
    corner_right = ribbon["corner_right"]

    gap = width * gap_ratio

    az23 = _azimuth_radians(p2, p3)
    half_pi = math.pi / 2

    outer_left_anchor = _project_point(corner_left, gap, az23 - half_pi)
    outer_right_anchor = _project_point(corner_right, gap, az23 + half_pi)

    az_left = _azimuth_radians(corner_left, p3)
    az_right = _azimuth_radians(corner_right, p3)

    outer_left_b = _project_point(outer_left_anchor, 1.0, az_left)
    outer_right_b = _project_point(outer_right_anchor, 1.0, az_right)

    outer_tip = _line_intersection(
        outer_left_anchor, outer_left_b, outer_right_anchor, outer_right_b
    )

    if outer_tip is None:
        return geometry

    return QgsGeometry.fromPolylineXY(
        [outer_left_anchor, outer_tip, outer_right_anchor]
    )


def _attack_by_fire_frame(p1, p2, p3):

    """
    The shared local frame both halves of Attack By Fire Position/
    Ambush are built in: the midpoint of PT2-PT3, a unit vector along
    that line, a unit NORMAL to it pointing towards PT1, and PT1's own
    perpendicular distance from the line.

    Deriving the normal's own direction from PT1 via the cross product
    (rather than from screen direction) is what keeps the whole symbol
    correct whichever side of the back line PT1 sits on and whichever
    order PT2/PT3 were digitized in - the same class of winding bug
    that turned Encirclement's own triangles inward.

    Returns None when the three points are collinear: there is then no
    meaningful "towards PT1" side, so callers draw nothing rather than
    picking an arbitrary direction.
    """

    back_dx = p3.x() - p2.x()
    back_dy = p3.y() - p2.y()

    back_length = math.hypot(back_dx, back_dy)

    if back_length == 0:
        return None

    ux = back_dx / back_length
    uy = back_dy / back_length

    # Left-hand normal, then flipped if PT1 is on the other side. The
    # cross product is positive exactly when PT1 lies on the left-hand
    # side of PT2 -> PT3.
    cross = back_dx * (p1.y() - p2.y()) - back_dy * (p1.x() - p2.x())

    if cross == 0:
        return None

    towards = 1.0 if cross > 0 else -1.0

    return {
        "midpoint": QgsPointXY(
            (p2.x() + p3.x()) / 2.0,
            (p2.y() + p3.y()) / 2.0,
        ),
        "ux": ux,
        "uy": uy,
        "nx": towards * -uy,
        "ny": towards * ux,
        "back_length": back_length,
        "perpendicular_distance": abs(cross) / back_length,
    }


def _swept_back_line_geometry(start, end, ax, ay, wing_ratio, wing_angle_deg):

    """
    The "back side" shape shared by Attack By Fire Position and Support
    by Fire Position: the straight line `start`-`end` plus one wing at
    each end, swept `wing_angle_deg` away from the line towards the
    (already-decided) `ax`/`ay` unit direction.

    The two callers differ only in how they work out that away
    direction - Attack By Fire derives it from its own third anchor
    point, Support by Fire from its digitizing direction - so it is
    passed in rather than computed here.
    """

    back_dx = end.x() - start.x()
    back_dy = end.y() - start.y()

    back_length = math.hypot(back_dx, back_dy)

    if back_length == 0:
        return None

    ux = back_dx / back_length
    uy = back_dy / back_length

    angle = math.radians(wing_angle_deg)

    wing_length = back_length * wing_ratio

    cos_a = math.cos(angle)
    sin_a = math.sin(angle)

    # Each wing runs outward along the back line (away from the other
    # end) and `wing_angle_deg` swept towards the away direction.
    start_wing = QgsPointXY(
        start.x() + wing_length * (-ux * cos_a + ax * sin_a),
        start.y() + wing_length * (-uy * cos_a + ay * sin_a),
    )

    end_wing = QgsPointXY(
        end.x() + wing_length * (ux * cos_a + ax * sin_a),
        end.y() + wing_length * (uy * cos_a + ay * sin_a),
    )

    # One open path so the back line and both wings share their own
    # corners exactly (three separate pieces would leave hairline gaps
    # at the joins at some zoom levels).
    return QgsGeometry.fromPolylineXY(
        [start_wing, QgsPointXY(start), QgsPointXY(end), end_wing]
    )


def _attack_by_fire_back_geometry(p1, p2, p3, wing_ratio, wing_angle_deg):

    """
    The back side of Attack By Fire Position/Ambush. Factored out so it
    can be unit-tested directly on plain QgsPointXY values, the same
    convention _axis_of_advance_ribbon_geometry() above already follows.

    Both wings sweep AWAY from PT1, which is what makes the back side
    "encompass the firing position" (the standard's own wording) rather
    than opening towards the target.
    """

    frame = _attack_by_fire_frame(p1, p2, p3)

    if frame is None:
        return None

    return _swept_back_line_geometry(
        p2,
        p3,
        -frame["nx"],
        -frame["ny"],
        wing_ratio,
        wing_angle_deg,
    )


def _ambush_geometry_frame(p1, p2, p3, sagitta_ratio, tooth_ratio):

    """
    Ambush's own shared measurements - the arc through PT2/PT3 bulging
    towards PT1, plus the constant tooth length both the teeth and the
    arrow's own tail are set back by.

    **2026-08-12 correction**, per the project maintainer: "the teeth
    behind the curve are all of equal length, also the distance between
    the arrow shaft end and the teeth is also equal". The first build
    ran each tooth from the arc all the way to the chord, which makes
    them longest in the middle and vanishing at PT2/PT3 - wrong. Every
    tooth is instead the SAME length, set back from the arc, so their
    own tails trace a curve congruent to it; and the arrow's tail sits
    on that same curve rather than on the chord.

    Confirmed against the standard's own EXAMPLE picture (printed page
    447) by least-squares circle fit rather than by eye - the first
    reading of the apex was contaminated by the arrow overlapping the
    arc at exactly that row. Fitted: sagitta 0.333 x chord, tooth
    0.273 x chord, which predicts the arrow's own tail at x=67.4 in
    that picture's own pixels against 67 measured.

    Note this puts the arrow's tail a little SHORT of the chord's
    midpoint (0.27 x chord back from the apex, where the chord itself
    is 0.33 back), so it follows the standard's own drawing rather than
    its prose, which says the rear "should connect to the midpoint of
    the line between points 2 and 3". The two disagree slightly; the
    maintainer chose the drawing.
    """

    frame = _attack_by_fire_frame(p1, p2, p3)

    if frame is None:
        return None

    chord_length = frame["back_length"]

    sagitta = chord_length * sagitta_ratio

    if sagitta <= 0:
        return None

    radius = (chord_length * chord_length / 4.0 + sagitta * sagitta) / (2.0 * sagitta)

    frame["chord_length"] = chord_length
    frame["sagitta"] = sagitta
    frame["radius"] = radius
    frame["centre_offset"] = radius - sagitta
    frame["tooth_length"] = chord_length * tooth_ratio

    return frame


def _ambush_arc_height(frame, along):

    """
    Perpendicular height of Ambush's own arc above its chord, `along`
    measured from the chord's own midpoint.
    """

    return math.sqrt(
        max(frame["radius"] * frame["radius"] - along * along, 0.0)
    ) - frame["centre_offset"]


def _ambush_back_geometry(
    p1, p2, p3, sagitta_ratio, tooth_ratio, tooth_count, segments=48
):

    """
    The back side of Ambush (141700) - a circular arc from PT2 to PT3
    bulging TOWARDS PT1, with equal-length comb teeth set back from it.

    Same three anchor points as Attack By Fire Position, and the same
    "which side is PT1 on" frame, but the standard draws this one's back
    side as a CURVE rather than a straight line with wings ("Points 2
    and 3 define the endpoints of the curved line on the back side of
    the symbol"), so it gets its own geometry rather than sharing
    _swept_back_line_geometry(). See _ambush_geometry_frame() for the
    measured proportions and for why the teeth are constant-length.
    """

    frame = _ambush_geometry_frame(p1, p2, p3, sagitta_ratio, tooth_ratio)

    if frame is None:
        return None

    midpoint = frame["midpoint"]

    ux = frame["ux"]
    uy = frame["uy"]
    nx = frame["nx"]
    ny = frame["ny"]

    chord_length = frame["chord_length"]
    tooth_length = frame["tooth_length"]

    def point_at(along, height):

        return QgsPointXY(
            midpoint.x() + ux * along + nx * height,
            midpoint.y() + uy * along + ny * height,
        )

    arc = [
        point_at(
            (step / segments - 0.5) * chord_length,
            _ambush_arc_height(frame, (step / segments - 0.5) * chord_length),
        )
        for step in range(segments + 1)
    ]

    parts = [arc]

    for index in range(1, tooth_count + 1):

        along = (index / (tooth_count + 1) - 0.5) * chord_length

        height = _ambush_arc_height(frame, along)

        # Constant length, set back from the arc - so every tooth is the
        # same and their own tails trace a curve congruent to it.
        parts.append([
            point_at(along, height - tooth_length),
            point_at(along, height),
        ])

    return QgsGeometry.fromMultiPolylineXY(parts)


@qgsfunction(
    'mct_ambush_shaft',
    group='Military Cartography Tools'
)
def mct_ambush_shaft(values, feature=None, parent=None):

    """
    Table H-XII, Ambush (141700) - the arrow. Runs along the true NORMAL
    to the PT2-PT3 chord, exactly as Attack By Fire Position's own does
    (see mct_attack_by_fire_shaft() for the maintainer's own "always
    perpendicular" correction, which applies to both), so PT1 sets only
    how far out and which side.

    It differs from Attack By Fire's shaft in where the TAIL sits: not
    on the chord, but set back from the arc's own apex by the same
    constant distance the teeth are - "the distance between the arrow
    shaft end and the teeth is also equal", the maintainer's own words.
    That is why this is its own function rather than reusing Attack By
    Fire's.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    sagitta_ratio = float(values[1]) if len(values) > 1 else 0.33
    tooth_ratio = float(values[2]) if len(values) > 2 else 0.27

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    frame = _ambush_geometry_frame(
        QgsPointXY(line.pointN(0)),
        QgsPointXY(line.pointN(1)),
        QgsPointXY(line.pointN(2)),
        sagitta_ratio,
        tooth_ratio,
    )

    if frame is None:
        return geometry

    tail_height = frame["sagitta"] - frame["tooth_length"]
    tip_height = frame["perpendicular_distance"]

    # A PT1 closer in than the arrow's own tail would give a zero or
    # backwards arrow; leave the digitized geometry alone rather than
    # draw one.
    if tip_height <= tail_height:
        return geometry

    midpoint = frame["midpoint"]

    return QgsGeometry.fromPolylineXY([
        QgsPointXY(
            midpoint.x() + frame["nx"] * tail_height,
            midpoint.y() + frame["ny"] * tail_height,
        ),
        QgsPointXY(
            midpoint.x() + frame["nx"] * tip_height,
            midpoint.y() + frame["ny"] * tip_height,
        ),
    ])


@qgsfunction(
    'mct_ambush_back',
    group='Military Cartography Tools'
)
def mct_ambush_back(values, feature=None, parent=None):

    """
    Table H-XII, Ambush (141700) - the curved back side plus its comb
    teeth, from the same 3-point digitized line Attack By Fire Position
    uses (PT1 = arrowhead tip, PT2/PT3 = the curved line's own
    endpoints). See _ambush_back_geometry() for the construction.

    Ambush's own ARROW is not built here - see mct_ambush_shaft().

    `sagitta_ratio` (default 0.33) is how far the arc bulges off its own
    chord, `tooth_ratio` (default 0.27) the teeth's own constant length,
    and `tooth_count` (default 7) how many there are - all as fractions
    of the chord, so the symbol scales with whatever PT2/PT3 the user
    places. **None is given anywhere in the standard's own text** - its
    Size/Shape rules cover only the chord's length and the arrow's own
    midpoint connection - so all three were fitted to the standard's own
    EXAMPLE picture (printed page 447); see _ambush_geometry_frame().
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    sagitta_ratio = float(values[1]) if len(values) > 1 else 0.33
    tooth_ratio = float(values[2]) if len(values) > 2 else 0.27
    tooth_count = int(values[3]) if len(values) > 3 else 7

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    back = _ambush_back_geometry(
        QgsPointXY(line.pointN(0)),
        QgsPointXY(line.pointN(1)),
        QgsPointXY(line.pointN(2)),
        sagitta_ratio,
        tooth_ratio,
        tooth_count,
    )

    return geometry if back is None else back


@qgsfunction(
    'mct_area_label_anchor',
    group='Military Cartography Tools'
)
def mct_area_label_anchor(values, feature=None, parent=None):

    """
    A point INSIDE a polygon, biased towards its own top-left corner -
    for area labels the standard places in the corner rather than at the
    centre. 2026-08-12, Table H-XIII's own zones (HIDACZ/ROZ/WEZ/...):
    "the zones names and unique identifier ... just need to be on to top
    left corner of polygon, within it" - the project maintainer's own
    words.

    A polygon's own bounding-box corner is NOT usable directly: for
    anything non-rectangular it falls outside the polygon, which would
    put the label off the shape entirely. So this clips the polygon to
    its own top band, then clips THAT to its own left portion, and
    returns `pointOnSurface()` of the result - a point guaranteed to lie
    within the polygon, as far towards the top-left as the shape
    actually allows. Each clip falls back to the previous geometry if it
    comes back empty (a very thin or very angular polygon), so the
    worst case is a centred label rather than no label at all.

    `top_fraction` (second argument, default 0.30) and `left_fraction`
    (third, default 0.45) are how much of the shape's own height and
    width to keep - deliberately generous, since the label only needs to
    read as "in the corner", and tighter bands make the fallbacks fire
    more often on real, irregular operational polygons.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    top_fraction = float(values[1]) if len(values) > 1 else 0.30
    left_fraction = float(values[2]) if len(values) > 2 else 0.45

    def clipped(source, keep_top, keep_left):

        box = source.boundingBox()

        rectangle = QgsRectangle(
            box.xMinimum(),
            box.yMaximum() - box.height() * keep_top,
            box.xMinimum() + box.width() * keep_left,
            box.yMaximum(),
        )

        result = source.intersection(QgsGeometry.fromRect(rectangle))

        return source if result is None or result.isEmpty() else result

    # Top band first, then the left of THAT band - doing both in one
    # rectangle would cut the corner off diagonally on a shape whose own
    # top-left is empty.
    band = clipped(geometry, top_fraction, 1.0)

    corner = clipped(band, 1.0, left_fraction)

    anchor = corner.pointOnSurface()

    return geometry if anchor is None or anchor.isEmpty() else anchor


@qgsfunction(
    'mct_search_area_arms',
    group='Military Cartography Tools'
)
def mct_search_area_arms(values, feature=None, parent=None):

    """
    Table H-XII, Search Area/Reconnaissance Area (152200) - the two
    NOTCHED arms, rebuilt 2026-08-12 from the standard's own template
    (printed page 444). Until now this measure type drew the digitized
    path as-is - two plain straight arrows - and the module's own
    docstring openly recorded the standard's "double-notched arrow shaft
    decoration is not reproduced". It is reproduced here.

    The user clicks THREE points in the standard's own drawing order -
    **PT2 first, PT1 second, PT3 third** (the maintainer's own
    instruction, and what this measure type already expected): PT2/PT3
    are the two arrowhead tips and PT1, in the middle, is the vertex
    both arms spring from.

    Each arm runs PT1 -> outer barb corner -> back in towards the axis
    -> tip, which is what gives the standard's own barbed/fletched
    look. The three shape constants are fractions of that arm's OWN
    length, so the two arms stay correct even though the standard lets
    their "length and orientation ... vary independently". They were
    measured off the template by projecting its own vertices onto each
    arm's axis: the outer corner sits 0.554 along and 0.131 out, and the
    step back returns to 0.481 along and 0.035 INSIDE the axis - rounded
    here to 0.55/0.13/0.48/0.035.

    Returned as a two-part MultiLineString, each part ordered PT1 ->
    tip, so a single LastVertex marker line heads both arms outward -
    the same trick Support by Fire Position's own arrows use. (Drawing
    it as one PT2 -> PT1 -> PT3 path instead would put the head at
    FirstVertex pointing back INWARDS, along the line's own outgoing
    direction.)
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    along_out = float(values[1]) if len(values) > 1 else 0.55
    outward = float(values[2]) if len(values) > 2 else 0.13
    along_in = float(values[3]) if len(values) > 3 else 0.48
    inward = float(values[4]) if len(values) > 4 else 0.035

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    tip_a = QgsPointXY(line.pointN(0))
    vertex = QgsPointXY(line.pointN(1))
    tip_b = QgsPointXY(line.pointN(2))

    def arm(tip, other_tip):

        dx = tip.x() - vertex.x()
        dy = tip.y() - vertex.y()

        length = math.hypot(dx, dy)

        if length == 0:
            return None

        ux = dx / length
        uy = dy / length

        # Perpendicular pointing AWAY from the other arm, so both arms
        # barb outwards however the user placed the two tips.
        px = -uy
        py = ux

        if px * (other_tip.x() - vertex.x()) + py * (other_tip.y() - vertex.y()) > 0:
            px, py = -px, -py

        def point(along_ratio, perp_ratio):

            return QgsPointXY(
                vertex.x() + ux * length * along_ratio + px * length * perp_ratio,
                vertex.y() + uy * length * along_ratio + py * length * perp_ratio,
            )

        return [
            QgsPointXY(vertex),
            point(along_out, outward),
            point(along_in, -inward),
            QgsPointXY(tip),
        ]

    arms = [
        part for part in (arm(tip_a, tip_b), arm(tip_b, tip_a))
        if part is not None
    ]

    if not arms:
        return geometry

    return QgsGeometry.fromMultiPolylineXY(arms)


def _support_by_fire_frame(geometry):

    """
    Support by Fire Position's own local frame, from the TWO points the
    user digitizes (PT1, PT2 - the back line's own endpoints, equivalent
    to Attack By Fire's own PT2/PT3).

    With only two anchor points there is nothing in the geometry itself
    to say which side the firing position faces, so it is fixed by
    convention: the arrows go to the LEFT of PT1 -> PT2 and the wings
    sweep RIGHT. That matches the standard's own EXAMPLE picture read
    left-to-right (page 443: PT1 left, PT2 right, arrows up, wings
    down), and it means the user orients the symbol simply by choosing
    which end to click first.
    """

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 2:
        return None

    start = QgsPointXY(line.pointN(0))
    end = QgsPointXY(line.pointN(line.numPoints() - 1))

    dx = end.x() - start.x()
    dy = end.y() - start.y()

    length = math.hypot(dx, dy)

    if length == 0:
        return None

    ux = dx / length
    uy = dy / length

    return {
        "start": start,
        "end": end,
        "ux": ux,
        "uy": uy,
        # Left-hand normal of PT1 -> PT2 - the arrows' own side.
        "nx": -uy,
        "ny": ux,
        "back_length": length,
    }


@qgsfunction(
    'mct_support_by_fire_back',
    group='Military Cartography Tools'
)
def mct_support_by_fire_back(values, feature=None, parent=None):

    """
    Table H-XII, Support by Fire Position (152100) - the back side, from
    the two points the user digitizes. Identical construction to Attack
    By Fire Position's own back side (same shared
    _swept_back_line_geometry(), same default wing ratio/angle), with
    the wings swept to the side OPPOSITE the arrows - see
    _support_by_fire_frame()'s own docstring for that convention.

    **2026-08-12**, per the project maintainer: the standard's own
    version takes FOUR anchor points (PT1/PT2 the back line, PT3/PT4 the
    arrowhead tips). This build deliberately takes only the two back-line
    points and DERIVES the arrows from them - "the user will click two
    points PT1 and PT2 - they are equivalent to PT2 and PT3 of the
    attack by fire... now at the two vertex where the wings touch the
    horizontal line, make two arrows of same length as the wings" - a
    simpler two-click symbol whose arrows can no longer be placed
    inconsistently with the back line.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    wing_ratio = float(values[1]) if len(values) > 1 else 0.37
    wing_angle_deg = float(values[2]) if len(values) > 2 else 53.0

    frame = _support_by_fire_frame(geometry)

    if frame is None:
        return geometry

    back = _swept_back_line_geometry(
        frame["start"],
        frame["end"],
        -frame["nx"],
        -frame["ny"],
        wing_ratio,
        wing_angle_deg,
    )

    return geometry if back is None else back


@qgsfunction(
    'mct_support_by_fire_arrows',
    group='Military Cartography Tools'
)
def mct_support_by_fire_arrows(values, feature=None, parent=None):

    """
    Table H-XII, Support by Fire Position (152100) - the two arrows,
    rising from the same two corners where the wings meet the back line
    (PT1 and PT2 themselves).

    Each arrow is the same length as a wing and leaves its own corner
    perpendicular to the back line, then tilted `tilt_deg` OUTWARD -
    away from the symbol's own centre, so the pair splay apart the way
    the standard's own picture shows ("the arrowheads typically indicate
    the left and right limits of coverage that the firing position is
    meant to support"). Per the project maintainer, 2026-08-12: "the two
    arrows are tilted slightly outward from perpendicular, say about
    15deg".

    Returned as a two-part MultiLineString with each part ordered
    base -> tip, so a single QgsMarkerLineSymbolLayer at LastVertex
    puts an arrowhead on both, each picking up its own part's rotation.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    wing_ratio = float(values[1]) if len(values) > 1 else 0.37
    tilt_deg = float(values[2]) if len(values) > 2 else 15.0

    frame = _support_by_fire_frame(geometry)

    if frame is None:
        return geometry

    ux = frame["ux"]
    uy = frame["uy"]
    nx = frame["nx"]
    ny = frame["ny"]

    arrow_length = frame["back_length"] * wing_ratio

    tilt = math.radians(tilt_deg)

    cos_t = math.cos(tilt)
    sin_t = math.sin(tilt)

    # Outward = away from the other corner, so the start arrow leans
    # back along -u and the end arrow forward along +u.
    start_tip = QgsPointXY(
        frame["start"].x() + arrow_length * (nx * cos_t - ux * sin_t),
        frame["start"].y() + arrow_length * (ny * cos_t - uy * sin_t),
    )

    end_tip = QgsPointXY(
        frame["end"].x() + arrow_length * (nx * cos_t + ux * sin_t),
        frame["end"].y() + arrow_length * (ny * cos_t + uy * sin_t),
    )

    return QgsGeometry.fromMultiPolylineXY([
        [frame["start"], start_tip],
        [frame["end"], end_tip],
    ])


@qgsfunction(
    'mct_attack_by_fire_back',
    group='Military Cartography Tools'
)
def mct_attack_by_fire_back(values, feature=None, parent=None):

    """
    Table H-XII, Attack By Fire Position (152000) and Ambush (141700) -
    the back side of the symbol, from a 3-point digitized line
    (PT1 = arrowhead tip, PT2/PT3 = the endpoints of the straight line
    on the back side, per the standard's own Anchor Points rules).

    Returns the straight PT2-PT3 line plus a swept-back wing at each
    end, as one open path so the corners join exactly. The arrow itself
    is NOT included - it is a separate symbol layer, so its own
    arrowhead marker can sit at the shaft's own last vertex and pick up
    the shaft's rotation automatically; see maneuver_control_measures_2.
    py's own _attack_by_fire_position_symbol() for how the two combine.

    `wing_ratio` (second argument, default 0.37) is the wing's own
    length as a fraction of the PT2-PT3 distance, and `wing_angle_deg`
    (third, default 53.0) is how far each wing is swept back from the
    back line itself. **Neither is specified anywhere in the standard's
    own text** - its Size/Shape rules only cover the straight line and
    the arrow's own midpoint connection - so both were measured off the
    standard's own EXAMPLE picture (printed page 442, rendered at 150
    dpi and measured by pixel analysis: wing ~0.37x the back line's own
    width, swept ~55 degrees back from it) and made proportional so the
    symbol scales with whatever PT2/PT3 the user actually places.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    wing_ratio = float(values[1]) if len(values) > 1 else 0.37
    wing_angle_deg = float(values[2]) if len(values) > 2 else 53.0

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    back = _attack_by_fire_back_geometry(
        QgsPointXY(line.pointN(0)),
        QgsPointXY(line.pointN(1)),
        QgsPointXY(line.pointN(2)),
        wing_ratio,
        wing_angle_deg,
    )

    return geometry if back is None else back


@qgsfunction(
    'mct_attack_by_fire_shaft',
    group='Military Cartography Tools'
)
def mct_attack_by_fire_shaft(values, feature=None, parent=None):

    """
    Table H-XII, Attack By Fire Position (152000)/Ambush (141700) - the
    arrow, from the midpoint of PT2-PT3 out to PT1's own side of that
    line. Its own layer (not folded into mct_attack_by_fire_back()'s
    geometry) so the arrowhead marker can ride this line's own last
    vertex and inherit its rotation.

    **2026-08-12 correction**, per the project maintainer: "the arrow is
    not perpendicular to the base, especially when PT2 and PT3 are not
    equidistant from PT1, make the arrow always perpendicular halfway
    between PT2 and PT3". The first version simply drew midpoint -> PT1,
    which is only perpendicular in the special case where PT1 happens to
    sit directly over the midpoint - any other PT1 gave a visibly
    skewed arrow. The arrow now always leaves the midpoint along the
    true NORMAL to PT2-PT3, and PT1 contributes only its own
    PERPENDICULAR DISTANCE from that line (which side, and how far out).
    So PT1 still controls the arrow's length and which way it points,
    but can no longer tilt it. In the equidistant case the two
    definitions coincide exactly, so already-correct symbols are
    unchanged.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    line = geometry.constGet()

    if hasattr(line, "geometryN"):
        line = line.geometryN(0)

    if line.numPoints() < 3:
        return geometry

    frame = _attack_by_fire_frame(
        QgsPointXY(line.pointN(0)),
        QgsPointXY(line.pointN(1)),
        QgsPointXY(line.pointN(2)),
    )

    if frame is None:
        return geometry

    midpoint = frame["midpoint"]
    reach = frame["perpendicular_distance"]

    return QgsGeometry.fromPolylineXY([
        midpoint,
        QgsPointXY(
            midpoint.x() + frame["nx"] * reach,
            midpoint.y() + frame["ny"] * reach,
        ),
    ])


_FUNCTIONS = [
    mct_sidc_svg,
    mct_build_sidc,
    mct_area_km2,
    mct_perimeter_km,
    mct_length_km,
    mct_crenellate_outline,
    mct_serrate_outline,
    mct_decoy_chevron,
    mct_decoy_chevron_svg,
    mct_scatter_points,
    mct_abatis_line,
    mct_mine_cluster_arc,
    mct_trip_wire_geometry,
    mct_wire_glyph_svg,
    mct_axis_of_advance_ribbon,
    mct_axis_of_advance_crossing_point,
    mct_axis_of_advance_outer_chevron,
    mct_attack_by_fire_back,
    mct_attack_by_fire_shaft,
    mct_support_by_fire_back,
    mct_support_by_fire_arrows,
    mct_ambush_back,
    mct_ambush_shaft,
    mct_search_area_arms,
    mct_area_label_anchor,
]


def register():

    for function in _FUNCTIONS:

        QgsExpression.registerFunction(
            function
        )


def unregister():

    for function in _FUNCTIONS:

        QgsExpression.unregisterFunction(
            function.name()
        )
