# -*- coding: utf-8 -*-

"""
Military symbology expression functions
for Military Cartography Tools
"""

import math

from qgis.core import (
    QgsDistanceArea,
    QgsExpression,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
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

    if text:
        return render_symbol_base64_path(sidc, {slot: str(text)})

    return render_symbol_base64_path(sidc)


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


_FUNCTIONS = [
    mct_sidc_svg,
    mct_build_sidc,
    mct_area_km2,
    mct_perimeter_km,
    mct_length_km,
    mct_crenellate_outline,
    mct_axis_of_advance_ribbon,
    mct_axis_of_advance_crossing_point,
    mct_axis_of_advance_outer_chevron,
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
