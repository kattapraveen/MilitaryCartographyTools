# -*- coding: utf-8 -*-

"""
Military symbology expression functions
for Military Cartography Tools
"""

import base64
import math
import random
import re

from qgis.core import (
    QgsDistanceArea,
    QgsExpression,
    QgsGeometry,
    QgsPointXY,
    QgsScaleCalculator,
    QgsProject,
    QgsRectangle,
    qgsfunction,
)

from ..military_symbology.sidc import build_sidc
from ..military_symbology.symbol_engine import (
    render_symbol_base64_path,
    render_symbol_svg,
    scale_svg_stroke_width,
)


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

    **A few slots are not milsymbol's at all.** Some icons have an
    amplifier box in the standard's own template that milsymbol defines
    NO option for - Table H-XXIII's NATO Multiple Supply Class Point
    and Table H-XXII's Ambulance Exchange Point both draw as a bare box
    otherwise. Those positions are drawn by this plugin instead, under
    the slot names in symbol_engine.INJECTED_TEXT_SLOTS, at coordinates
    lifted from a sibling icon milsymbol does define; see that module's
    own _INJECTED_TEXT table.

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

    # Optional SIXTH and SEVENTH arguments: a SECOND text and its own
    # slot, for the one icon that needs two amplifiers at once - Table
    # H-XXIII's NATO Multiple Supply Class Point, which carries its
    # supply class numbers in field A and its designation in T1. Every
    # other caller omits them.
    extra_text = values[5] if len(values) > 5 else None
    extra_slot = str(values[6]) if len(values) > 6 and values[6] else None

    options = {}

    if text:
        options[slot] = str(text)

    if extra_text and extra_slot:
        options[extra_slot] = str(extra_text)

    if mono_color:
        options["monoColor"] = mono_color

    return render_symbol_base64_path(
        sidc, options or None, stroke_scale
    )


@qgsfunction(
    'mct_sidc_svg_width',
    group='Military Cartography Tools'
)
def mct_sidc_svg_width(values, feature=None, parent=None):

    """
    The rendered WIDTH, in milsymbol's own icon units, of exactly the
    symbol mct_sidc_svg() would return for the same arguments.

    Exists so a marker's size can compensate for its own bounding box.
    QGIS sizes an SVG marker by its width, and milsymbol widens an
    icon's box to take in whatever amplifier text it carries - so at a
    fixed marker size, adding a unique designation SHRINKS the icon
    it belongs to. The maintainer's own report, on Table H-XXI: "now
    the symbol size is reducing when the Field T is added -
    inconsistent from a UI point of view. can we have the size of the
    main symbol remaining same?"

    Dividing the amplified width by the plain one gives exactly the
    factor that holds the icon still and lets the text hang outside it,
    which is how the standard's own examples draw amplifiers anyway
    (Table H-XIV's sonobuoys put "99" and "HOT" clear of the circle;
    Table H-XXI puts Field T to the right of the box).

    Takes mct_sidc_svg's own argument list so the two can be called
    side by side with the same expression text.
    """

    if len(values) < 1:
        return 0.0

    sidc = str(values[0])

    text = values[1] if len(values) > 1 else None
    slot = (
        str(values[2])
        if len(values) > 2 and values[2]
        else "uniqueDesignation"
    )

    mono_color = str(values[3]) if len(values) > 3 and values[3] else None
    stroke_scale = float(values[4]) if len(values) > 4 and values[4] else None

    # Optional SIXTH and SEVENTH arguments: a SECOND text and its own
    # slot, for the one icon that needs two amplifiers at once - Table
    # H-XXIII's NATO Multiple Supply Class Point, which carries its
    # supply class numbers in field A and its designation in T1. Every
    # other caller omits them.
    extra_text = values[5] if len(values) > 5 else None
    extra_slot = str(values[6]) if len(values) > 6 and values[6] else None

    options = {}

    if text:
        options[slot] = str(text)

    if extra_text and extra_slot:
        options[extra_slot] = str(extra_text)

    if mono_color:
        options["monoColor"] = mono_color

    svg = scale_svg_stroke_width(
        render_symbol_svg(sidc, options or None),
        stroke_scale
    )

    match = re.search(r'viewBox="\S+ \S+ (\S+) \S+"', svg)

    return float(match.group(1)) if match else 0.0


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


def _pole_of_inaccessibility(geometry):

    """
    A polygon's own pole of inaccessibility - the point furthest from
    any edge, i.e. the centre of the largest circle that fits inside it
    - and the boundary it was measured against, or (None, None) for
    anything that isn't a usable polygon.

    Shared by mct_inscribed_centre() and mct_inscribed_radius_m() so
    the two can never disagree about WHERE the circle is centred. They
    are separate expression functions because one feeds a geometry
    generator (placement) and the other a data-defined size, and a
    QGIS expression cannot return both at once - but a glyph placed at
    one point and sized for a circle centred on another would sit
    partly outside the area, which is precisely what this construction
    exists to prevent.
    """

    if geometry is None or geometry.isEmpty():
        return None, None

    boundary = geometry.constGet().boundary()

    if boundary is None:
        return None, None

    # A tolerance proportional to the polygon's own size, not a fixed
    # number: poleOfInaccessibility() takes its precision in MAP units,
    # so a constant would be far too coarse for a 200 m area in degrees
    # and needlessly slow for a 400 km one in metres.
    bounding_box = geometry.boundingBox()

    precision = max(
        max(bounding_box.width(), bounding_box.height()) / 200.0,
        1e-12
    )

    pole, _ = geometry.poleOfInaccessibility(precision)

    if pole is None or pole.isEmpty():
        return None, None

    return pole, QgsGeometry(boundary)


@qgsfunction(
    'mct_inscribed_centre',
    group='Military Cartography Tools'
)
def mct_inscribed_centre(values, feature=None, parent=None):

    """
    A polygon's own pole of inaccessibility, as a point geometry - the
    centre of the circle mct_inscribed_radius_m() measures. Use as
    mct_inscribed_centre($geometry), in a geometry generator.

    NOT point_on_surface(): that only guarantees a point somewhere
    INSIDE the polygon, and for anything other than a near-circle it
    lands well off centre. Rendered offscreen with a glyph sized from
    the inscribed radius but drawn at point_on_surface, the glyph's own
    corners crossed the outline - the size was right for a circle
    centred somewhere the glyph wasn't.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    pole, _ = _pole_of_inaccessibility(values[0])

    return pole


@qgsfunction(
    'mct_inscribed_radius_mm',
    group='Military Cartography Tools'
)
def mct_inscribed_radius_mm(values, feature=None, parent=None):

    """
    The radius, in PAGE MILLIMETRES, of the largest circle that fits
    inside a polygon - measured from the pole of inaccessibility
    mct_inscribed_centre() returns to the nearest point on the
    polygon's own boundary. Use as
    mct_inscribed_radius_mm($geometry, @map_extent, @map_scale), in a
    data-defined SIZE property (never a geometry generator, where
    neither @map_scale nor @map_extent resolves).

    Written for Table H-XXI's contaminated areas, whose glyph fills the
    area it sits in while keeping a fixed millimetre clearance from the
    outline. The clearance is in page units, so the radius has to be
    too.

    **Page millimetres, deliberately NOT ground metres.** The first
    build measured this leg geodesically, like mct_area_km2() does, and
    the glyph rendered 13% too large - its corners crossed the outline
    the 3 mm gap was supposed to keep it clear of. The reason is that a
    map drawn in a geographic CRS gives a degree of longitude and a
    degree of latitude exactly the same width on the page while they
    are NOT the same distance on the ground: at 28 degrees north a
    degree of latitude is about 1.13 times the length of a degree of
    longitude. A ground measurement therefore answers a different
    question from the one the page is asking. So the radius is measured
    plainly in map units - which the page renders linearly, which is
    the whole point - and only the map-units-to-millimetres factor is
    derived on the ellipsoid, below.
    """

    if len(values) < 3:
        return "Need a geometry, @map_extent and @map_scale"

    pole, boundary = _pole_of_inaccessibility(values[0])

    if pole is None:
        return 0.0

    nearest = boundary.nearestPoint(pole)

    if nearest is None or nearest.isEmpty():
        return 0.0

    pole_point = pole.asPoint()
    nearest_point = nearest.asPoint()

    radius_units = math.hypot(
        nearest_point.x() - pole_point.x(),
        nearest_point.y() - pole_point.y()
    )

    millimetres_per_unit = _map_millimetres_per_unit(values[1], values[2])

    return radius_units * millimetres_per_unit


def _map_millimetres_per_unit(map_extent, map_scale):

    """
    How many page millimetres one map unit spans in the current map
    view - the factor that turns a distance measured in the layer's own
    coordinates into a distance on the printed/displayed page.

    **Asks QGIS's own QgsScaleCalculator rather than measuring the
    ground distance independently.** The obvious implementation -
    measure the extent's width on the ellipsoid, divide by its width in
    map units - is wrong, and wrong by a lot: for a view 0.2 degrees
    wide at 28 degrees north, a geodesic measurement gives 98,344 m per
    degree, while the number QGIS itself used to arrive at @map_scale
    is 76,402. Since the whole point is to agree with @map_scale, the
    answer has to come from whatever QGIS's own scale calculation does,
    not from an independently defensible measurement of the Earth.
    Built the geodesic way first, which drew the glyph 29% oversized.

    Recovered rather than read off directly, because a symbol
    expression cannot see the render context's own DPI or pixel width:
    the calculator is asked for the scale of this same extent at an
    arbitrary reference DPI and pixel width, and metres-per-unit is
    divided back out. Both arbitrary choices cancel exactly - scale is
    inversely proportional to page width, and page width in metres is
    pixels/DPI - confirmed by computing it at two different widths.

    Takes the unit type from the PROJECT's own CRS, exactly as
    _distance_area() does and for the same reason - see its docstring.
    """

    if map_extent is None or map_extent.isEmpty() or not map_scale:
        return 0.0

    bounding_box = map_extent.boundingBox()

    if bounding_box.width() <= 0:
        return 0.0

    reference_dpi = 96.0
    reference_width_px = 1000

    calculator = QgsScaleCalculator(
        reference_dpi,
        QgsProject.instance().crs().mapUnits()
    )

    reference_scale = calculator.calculate(
        bounding_box,
        reference_width_px
    )

    reference_page_width_m = reference_width_px / reference_dpi * 0.0254

    metres_per_unit = (
        reference_scale * reference_page_width_m / bounding_box.width()
    )

    return metres_per_unit * 1000.0 / map_scale


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
    Table H-XIX's own Trip Wire (290500). Rebuilt 2026-08-13 to the
    maintainer's own dictated construction, replacing an earlier
    reading of the standard's own template picture (which used three
    clicked anchor points, not two) after the maintainer reviewed that
    render and gave the exact steps instead:

    "user clicks PT1 and PT2 - draw a line connecting PT1 and 2, now at
    1/7 pt from PT1, draw a line 90 deg to the line between PT1 and
    PT2, length 0.5 of the distance between PT1 and PT2, now at midway
    point, draw another line 90 deg or perpendicular to the line
    between PT1 and PT2, length 1.2 times the distance between PT1 and
    PT2, finally at PT2, draw an arc of 90 deg anticlockwise, radius
    1/5 of the distance between PT1 and PT2"

    Only two anchor points now (PT1, PT2), taken from the feature's own
    digitized vertices - everything else is derived from them:

    - The main line, PT1 to PT2, drawn as-is.
    - A crossbar at 1/7 of the way from PT1 to PT2, perpendicular to
      the main line, running 0.5x the PT1-PT2 distance to EACH side of
      it - corrected 2026-08-13 from an initial one-sided build: "both
      the horizontal lines are on one side of the line connecting pt1
      and 2, they should be on both sides". The dictated length is
      kept as the length of each side, so the crossbar's own total
      span is twice the stated multiplier.
    - A second crossbar at the midpoint, same symmetric treatment,
      1.2x the PT1-PT2 distance to each side.
    - A 90 degree arc at PT2, anticlockwise, radius 0.2x (1/5) the
      PT1-PT2 distance, starting tangent to the main line's own
      direction of travel (continuing past PT2) and sweeping
      anticlockwise from there - standard mathematical sense
      (increasing angle, toward the main line's own left side, in a
      Y-up plane, which is how a digitized map's own coordinates read).
      Not corrected to be symmetric - the maintainer's own "both the
      horizontal lines" named the crossbars specifically, not the arc.

    Which side "anticlockwise" reads as on screen was not pinned down
    beyond the dictated wording - the arc is built on the main line's
    own left by the standard right-hand/CCW convention, a placement
    call rather than a measurement, exactly the kind of thing the
    maintainer said they would give further correction on after seeing
    a render.

    Returned as a MultiLineString: the main line fused with the arc
    (they share PT2, so it is one continuous path), plus the two
    crossbars as their own separate parts, since neither crossbar
    shares an endpoint with anything else it is drawn against.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    segments = int(values[1]) if len(values) > 1 else 12

    vertices = geometry.asPolyline()

    if len(vertices) < 2:
        return geometry

    pt1 = QgsPointXY(vertices[0])
    pt2 = QgsPointXY(vertices[1])

    dx = pt2.x() - pt1.x()
    dy = pt2.y() - pt1.y()

    length = math.hypot(dx, dy)

    if length == 0:
        return geometry

    # u: unit vector along PT1->PT2. n: u rotated 90 degrees
    # anticlockwise (standard maths sense, Y-up) - the one consistent
    # side every perpendicular element in this symbol is built on.
    ux, uy = dx / length, dy / length
    nx, ny = -uy, ux

    def point_along(fraction):

        return QgsPointXY(
            pt1.x() + fraction * dx,
            pt1.y() + fraction * dy,
        )

    def crossbar(fraction, length_multiplier):

        # Symmetric about the base point - "both the horizontal lines
        # are on one side of the line connecting pt1 and 2, they should
        # be on both sides", the maintainer's own correction to an
        # initial one-sided build. The dictated length is kept as the
        # length of EACH side, so the arm on the +n side and the arm on
        # the -n side both run the full length_multiplier x length.
        base = point_along(fraction)

        arm = length * length_multiplier

        near = QgsPointXY(
            base.x() - arm * nx,
            base.y() - arm * ny,
        )

        far = QgsPointXY(
            base.x() + arm * nx,
            base.y() + arm * ny,
        )

        return [near, far]

    crossbar_near_pt1 = crossbar(1.0 / 7.0, 0.5)
    crossbar_midpoint = crossbar(0.5, 1.2)

    radius = length * (1.0 / 5.0)

    # Centre of the arc's own circle: PT2 offset by one radius along n
    # (u rotated 90 CCW). Derived, not guessed - the only centre for
    # which a point starting at PT2, moving with tangent u, and
    # sweeping ANTICLOCKWISE (standard maths sense: increasing angle)
    # is consistent. The vector from centre back to PT2 is then -n;
    # rotating THAT vector anticlockwise by the sweep angle traces the
    # arc, ending with vector +u from the centre (tangent there is n -
    # a quarter-turn CCW from the starting tangent u, as it should be).
    center_x = pt2.x() + radius * nx
    center_y = pt2.y() + radius * ny

    start_x, start_y = -nx, -ny

    arc_points = []

    for index in range(segments + 1):

        t = (index / segments) * (math.pi / 2.0)

        dir_x = start_x * math.cos(t) - start_y * math.sin(t)
        dir_y = start_x * math.sin(t) + start_y * math.cos(t)

        arc_points.append(
            QgsPointXY(
                center_x + radius * dir_x,
                center_y + radius * dir_y,
            )
        )

    main_line_and_arc = [pt1] + arc_points

    return QgsGeometry.fromMultiPolylineXY(
        [main_line_and_arc, crossbar_near_pt1, crossbar_midpoint]
    )


@qgsfunction(
    'mct_block_geometry',
    group='Military Cartography Tools'
)
def mct_block_geometry(values, feature=None, parent=None):

    """
    Table H-XIX's own Block (270501, printed page 575) - a "T": the
    crossbar is PT1-PT2 ("points 1 and 2 define the endpoints of the
    symbol's vertical line"), the stem runs from the crossbar's own
    MIDPOINT out to a length set by PT3 ("the length of the horizontal
    line is determined by plotting point 3 on a plane extending
    perpendicularly from the midpoint of the vertical line") - the
    PERPENDICULAR distance from PT3 to the infinite line through
    PT1-PT2, the same projection already used in mct_trip_wire_geometry
    and mct_block_geometry's own sibling functions, general enough that
    PT3 need not be clicked exactly perpendicular.

    Three anchor points, reinterpreted from the feature's own digitized
    vertices rather than drawn as the raw PT1-PT2-PT3 polyline.

    Returned as a MultiLineString: the crossbar (PT1 to PT2, straight)
    and the stem (midpoint to tip) as two separate parts, since they
    only share the crossbar's own midpoint, not an end-to-end path.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

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

    ux, uy = dx / span, dy / span

    to_pt3_x = pt3.x() - pt1.x()
    to_pt3_y = pt3.y() - pt1.y()

    along = to_pt3_x * ux + to_pt3_y * uy

    foot_x = pt1.x() + along * ux
    foot_y = pt1.y() + along * uy

    perp_x = pt3.x() - foot_x
    perp_y = pt3.y() - foot_y

    length = math.hypot(perp_x, perp_y)

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0,
        (pt1.y() + pt2.y()) / 2.0,
    )

    if length == 0:
        # PT3 sits ON the PT1-PT2 line - no direction for the stem, so
        # it collapses to a point at the midpoint rather than guessing.
        return QgsGeometry.fromMultiPolylineXY([[pt1, pt2], [midpoint]])

    nx, ny = perp_x / length, perp_y / length

    tip = QgsPointXY(
        midpoint.x() + length * nx,
        midpoint.y() + length * ny,
    )

    # An optional gap in the STEM, for a letter set into it. Added
    # 2026-08-15 for Table H-XXIV's own Block, which carries a "B"
    # there; Table H-XIX's own Block passes nothing and is unchanged.
    #
    # Cut into the geometry rather than masked, because QGIS's
    # Selective Masking cannot reach a symbol layer nested inside a
    # geometry generator - the same reason the Minimum Safe Distance
    # Zone's rings carry their own break.
    gap_units = _page_gap_in_map_units(values, 1, midpoint)

    if gap_units > 0 and 2.0 * gap_units < length:

        half = gap_units / 2.0

        centre_along = length / 2.0

        before = QgsPointXY(
            midpoint.x() + (centre_along - half) * nx,
            midpoint.y() + (centre_along - half) * ny,
        )

        after = QgsPointXY(
            midpoint.x() + (centre_along + half) * nx,
            midpoint.y() + (centre_along + half) * ny,
        )

        return QgsGeometry.fromMultiPolylineXY(
            [[pt1, pt2], [midpoint, before], [after, tip]]
        )

    return QgsGeometry.fromMultiPolylineXY(
        [[pt1, pt2], [midpoint, tip]]
    )


def _page_gap_in_map_units(values, first_index, reference_point):

    """
    A gap given in PAGE millimetres, converted to the MAP UNITS the
    geometry is in - `values[first_index]` the width, `values[first_index
    + 1]` the map scale, and `reference_point` somewhere on the feature.

    Returns 0.0 when either value is missing, which is what makes every
    gap parameter in this module optional and leaves every existing
    caller unaffected.

    **@map_scale DOES resolve inside a geometry generator** - probed
    2026-08-15, correcting a note this project carried for days.

    **The last step is a map-unit conversion, and skipping it is the
    error to avoid.** A scale relates ground metres to page
    millimetres, but a layer in a geographic CRS holds DEGREES, and a
    gap of "600 metres" cut as 600 degrees is off by five orders of
    magnitude. Metres-per-unit is measured on the ellipsoid at the
    feature's own latitude, along the x axis - which is the same
    quantity QGIS's own scale calculation uses, so the two agree.
    """

    if len(values) <= first_index + 1:
        return 0.0

    try:
        gap_mm = float(values[first_index])
        map_scale = float(values[first_index + 1])
    except (TypeError, ValueError):
        return 0.0

    if gap_mm <= 0 or map_scale <= 0:
        return 0.0

    ground_metres = gap_mm / 1000.0 * map_scale

    distance_area = _distance_area()

    metres_per_unit = distance_area.measureLine(
        reference_point,
        QgsPointXY(reference_point.x() + 1.0, reference_point.y())
    )

    if metres_per_unit <= 0:
        return 0.0

    return ground_metres / metres_per_unit


@qgsfunction(
    'mct_block_letter_point',
    group='Military Cartography Tools'
)
def mct_block_letter_point(values, feature=None, parent=None):

    """
    The midpoint of Block's own stem - where the letter sits, and the
    middle of the gap mct_block_geometry() cuts for it. Use as
    mct_block_letter_point($geometry).

    Computed here rather than by calling mct_block_geometry through its
    own decorator: a @qgsfunction's `.func` is invoked by QGIS with an
    extra context argument, so calling it with the three arguments the
    body declares raises, the expression evaluates to NULL, and the
    label silently never draws. Found by render - the "T" was right and
    the "B" simply absent.
    """

    if len(values) < 1:
        return QgsGeometry()

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return QgsGeometry()

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return QgsGeometry()

    pt1, pt2, pt3 = (QgsPointXY(vertices[i]) for i in range(3))

    dx, dy = pt2.x() - pt1.x(), pt2.y() - pt1.y()

    span = math.hypot(dx, dy)

    if span == 0:
        return QgsGeometry()

    ux, uy = dx / span, dy / span

    along = (pt3.x() - pt1.x()) * ux + (pt3.y() - pt1.y()) * uy

    perp_x = pt3.x() - (pt1.x() + along * ux)
    perp_y = pt3.y() - (pt1.y() + along * uy)

    length = math.hypot(perp_x, perp_y)

    if length == 0:
        return QgsGeometry()

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
    )

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            midpoint.x() + length / 2.0 * perp_x / length,
            midpoint.y() + length / 2.0 * perp_y / length,
        )
    )


@qgsfunction(
    'mct_disrupt_letter_point',
    group='Military Cartography Tools'
)
def mct_disrupt_letter_point(values, feature=None, parent=None):

    """
    Where Disrupt's own letter sits: on the CENTRAL arrow's shaft,
    halfway from the base line to that arrow's tip - the maintainer's
    own placement. Use as mct_disrupt_letter_point($geometry).

    **No mirror.** A first build made this the mirrored twin of Table
    H-XIX's Disrupt, on a reading of "vertically mirrored" in the
    instruction. The maintainer settled it instead: draw it exactly as
    270502, and let the user decide which way up it sits by the order
    they click PT1 and PT2 - "let's not complicate a simple situation".
    """

    points = _three_anchor_points(values)

    if points is None:
        return QgsGeometry()

    pt1, pt2, pt3 = points

    _base, _a, _b, arrow_c = _disrupt_arrows(pt1, pt2, pt3)

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
    )

    tip = arrow_c[1]

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            (midpoint.x() + tip.x()) / 2.0,
            (midpoint.y() + tip.y()) / 2.0,
        )
    )


@qgsfunction(
    'mct_fix_letter_point',
    group='Military Cartography Tools'
)
def mct_fix_letter_point(values, feature=None, parent=None):

    """
    Where Fix's own letter sits: in the middle of the flat run at the
    PT2 end, before the toothed pattern begins. Use as
    mct_fix_letter_point($geometry, <gap in mm>, @map_scale) - the same
    arguments mct_fix_geometry() gets, so the letter and the gap it
    sits in are computed from one set of numbers.
    """

    points = _three_anchor_points(values)

    if points is None:
        return QgsGeometry()

    pt1, pt2, pt3 = points

    # Recomputed rather than read back off the geometry: a
    # @qgsfunction's own `.func` is invoked by QGIS with an extra
    # context argument, so calling it directly raises and the label
    # silently never draws.
    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None:
        return QgsGeometry()

    (ux, uy), _normal, tooth_length = projection

    total_length = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    if tooth_length == 0 or total_length <= 0:
        return QgsGeometry()

    letter_gap = _page_gap_in_map_units(values, 1, pt2)

    lead_extra = 2.0 * letter_gap

    if lead_extra >= total_length - 2.0 * tooth_length:
        return QgsGeometry()

    usable = total_length - 2.0 * tooth_length - lead_extra

    tooth_count = max(0, int(usable // tooth_length)) if usable > 0 else 0

    leftover = usable - tooth_count * tooth_length if usable > 0 else 0.0

    start_flat = tooth_length + (leftover / 2.0 if usable > 0 else 0.0)

    end_of_teeth = start_flat + tooth_count * tooth_length

    centre = end_of_teeth + (total_length - end_of_teeth) / 2.0

    return QgsGeometry.fromPointXY(
        QgsPointXY(pt1.x() + centre * ux, pt1.y() + centre * uy)
    )


def _three_anchor_points(values):

    """The first three vertices of a line geometry, or None."""

    if not values:
        return None

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return None

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return None

    return tuple(QgsPointXY(vertices[index]) for index in range(3))


@qgsfunction(
    'mct_turn_arc',
    group='Military Cartography Tools'
)
def mct_turn_arc(values, feature=None, parent=None):

    """
    Table H-XIX's own Turn (270504). Rebuilt 2026-08-13 to the
    maintainer's own dictated construction, replacing a first reading
    of the standard's own draw-rules text (a true 90 degree circular
    arc between only PT1/PT2, with PT3 as a side-selector) after two
    reported problems with it: "rendering in the opposite direction of
    the points, and the line is getting trimmed instead of being from
    PT1 to PT3" - the old construction never reached PT3 at all, since
    PT3 only picked a bulge side rather than being an endpoint, which
    reads as "trimmed" next to a curve that should run the symbol's
    full length.

    The maintainer's own words: "User clicks three points PT1, PT2 and
    PT3 - just connect the three with a curved line, something like
    [a] bezier curve from PT1 to PT3." Built as exactly that - a
    quadratic Bezier with PT1 as the start, PT2 as the CONTROL point
    (not a second endpoint), PT3 as the end - reusing
    _quadratic_bezier_points(), already used elsewhere in this module
    for Main Attack's own criss-crossing ribbon curve.

    The arrowhead (drawn by the caller, _turn_symbol) sits at the
    curve's own LAST point, i.e. PT3 - "the rear of the symbol
    identifies the enemy's location and the arrow points in the
    direction the obstacle should force the enemy to turn" still
    holds, just with the tip moved from PT2 to PT3 to match the new
    3-point curve.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    segments = int(values[1]) if len(values) > 1 else 16

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1 = QgsPointXY(vertices[0])
    pt2 = QgsPointXY(vertices[1])
    pt3 = QgsPointXY(vertices[2])

    points = _quadratic_bezier_points(pt1, pt2, pt3, segments)

    return QgsGeometry.fromPolylineXY(points)


def _perpendicular_projection(pt1, pt2, pt3):

    """
    Shared by mct_block_geometry, mct_disrupt_geometry and
    mct_fix_geometry: the perpendicular distance from PT3 to the
    infinite line through PT1-PT2, plus u (unit vector along PT1->PT2)
    and n (unit vector from that line TOWARD PT3). Returns
    (u, n, length) - length is 0.0 if PT3 sits on the line, same
    degenerate case every caller already needs to handle.
    """

    dx = pt2.x() - pt1.x()
    dy = pt2.y() - pt1.y()

    span = math.hypot(dx, dy)

    if span == 0:
        return None

    ux, uy = dx / span, dy / span

    to_pt3_x = pt3.x() - pt1.x()
    to_pt3_y = pt3.y() - pt1.y()

    along = to_pt3_x * ux + to_pt3_y * uy

    foot_x = pt1.x() + along * ux
    foot_y = pt1.y() + along * uy

    perp_x = pt3.x() - foot_x
    perp_y = pt3.y() - foot_y

    length = math.hypot(perp_x, perp_y)

    if length == 0:
        return (ux, uy), (0.0, 0.0), 0.0

    nx, ny = perp_x / length, perp_y / length

    return (ux, uy), (nx, ny), length


def _disrupt_arrows(pt1, pt2, pt3):

    """
    The three "arrows" Disrupt (270502) is built from, per the
    maintainer's own dictated construction (quoted in full in
    mct_disrupt_geometry's own docstring). Returns
    (base, arrow_a, arrow_b, arrow_c), each a [start, tip] pair (arrow_c
    is [tail, tip], tail being the shaft's own extension past the
    base) - shared between mct_disrupt_geometry (every part, for the
    plain line) and mct_disrupt_arrow_tips (the three arrows only, tail
    end first, for arrowhead placement), so the geometry is computed
    once, not twice.
    """

    base = [pt1, pt2]

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:
        # Degenerate: PT1==PT2, or PT3 sits on the base line - no
        # perpendicular direction to build the arrows from. Collapse
        # every arrow to its own start point rather than guessing.
        return base, [pt1, pt1], [pt2, pt2], [pt1, pt1]

    (ux, uy), (nx, ny), length = projection

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0,
        (pt1.y() + pt2.y()) / 2.0,
    )

    def offset(point, distance):

        return QgsPointXY(
            point.x() + distance * nx,
            point.y() + distance * ny,
        )

    # "Draw an arrow from PT2 to PT3... shift PT3 accordingly to get a
    # perpendicular" - PT2's own arrow runs the full perpendicular
    # distance.
    arrow_a = [pt2, offset(pt2, length)]

    # "Draw another arrow from PT1 parallel to the arrow PT2 to PT3,
    # half of the length."
    arrow_b = [pt1, offset(pt1, length / 2.0)]

    # "At the midpoint... length adjusted such that the tip of the
    # arrow is halfway as compared to the tips of the other two arrows"
    # - halfway between the full-length and half-length tips is 0.75x.
    # "Extend the shaft below the base, length same as base to the tip
    # of the arrow" - the same 0.75x again, on the OPPOSITE side, so
    # the middle shaft is symmetric about the base.
    middle_length = (length + length / 2.0) / 2.0

    arrow_c = [offset(midpoint, -middle_length), offset(midpoint, middle_length)]

    return base, arrow_a, arrow_b, arrow_c


@qgsfunction(
    'mct_disrupt_geometry',
    group='Military Cartography Tools'
)
def mct_disrupt_geometry(values, feature=None, parent=None):

    """
    Table H-XIX's own Disrupt (270502). Rebuilt 2026-08-13 to the
    maintainer's own dictated construction, replacing a first reading
    of the standard's own template picture (a vertical spine with three
    arrows of an inexact, only-pixel-measured proportion - see this
    project's own roadmap for that measurement and why it wasn't
    trusted). The maintainer's own words:

    "user clicks three points PT1, PT2 and PT3; Connect PT1 and PT2,
    call it base. Draw an arrow from PT2 to PT3 - this arrow should be
    perpendicular to the base so Shift PT3 accordingly to get a
    perpendicular. Draw another arrow from PT1 parallel to the arrow
    PT2 to PT3, half of the length of PT2-PT3 arrow. Now at the
    midpoint of base, draw another arrow parallel to the other two
    arrows, length adjusted such that the tip of the arrow is halfway
    as compared to the tips of the other two arrows from the base,
    extend the shaft below the base, length same as base to the tip of
    the arrow."

    All four parts (base, 3 arrows) computed once in _disrupt_arrows()
    and shared with mct_disrupt_arrow_tips(), which returns only the
    three arrows (for arrowhead placement) - the base itself has no
    arrowhead.

    Returned as a MultiLineString, since the base and the three arrows
    only share single points (PT1, PT2, the midpoint), not a
    continuous path.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1 = QgsPointXY(vertices[0])
    pt2 = QgsPointXY(vertices[1])
    pt3 = QgsPointXY(vertices[2])

    base, arrow_a, arrow_b, arrow_c = _disrupt_arrows(pt1, pt2, pt3)

    # An optional gap in the MIDDLE arrow's shaft, for a letter set
    # into it - Table H-XXIV's own Disrupt carries a "D" there, halfway
    # from the base line to that arrow's tip. Table H-XIX's own Disrupt
    # passes nothing and is unchanged.
    gap_units = _page_gap_in_map_units(values, 1, arrow_c[0])

    tail, tip = arrow_c[0], arrow_c[1]

    shaft = math.hypot(tip.x() - tail.x(), tip.y() - tail.y())

    if gap_units > 0 and shaft > 2.0 * gap_units:

        midpoint = QgsPointXY(
            (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
        )

        # Halfway from the base to the tip, which is where the letter
        # sits - see mct_disrupt_letter_point(), which must agree.
        letter = QgsPointXY(
            (midpoint.x() + tip.x()) / 2.0,
            (midpoint.y() + tip.y()) / 2.0,
        )

        ux = (tip.x() - tail.x()) / shaft
        uy = (tip.y() - tail.y()) / shaft

        half = gap_units / 2.0

        before = QgsPointXY(letter.x() - half * ux, letter.y() - half * uy)
        after = QgsPointXY(letter.x() + half * ux, letter.y() + half * uy)

        return QgsGeometry.fromMultiPolylineXY(
            [base, arrow_a, arrow_b, [tail, before], [after, tip]]
        )

    return QgsGeometry.fromMultiPolylineXY(
        [base, arrow_a, arrow_b, arrow_c]
    )


@qgsfunction(
    'mct_disrupt_arrow_tips',
    group='Military Cartography Tools'
)
def mct_disrupt_arrow_tips(values, feature=None, parent=None):

    """
    The three "arrows" from mct_disrupt_geometry, WITHOUT the base -
    used by _disrupt_symbol's own arrowhead marker layer, so an
    arrowhead lands on each arrow's own tip and not (via a stray
    LastVertex on the base's own final point, PT2) an extra one at the
    base's own end too.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1 = QgsPointXY(vertices[0])
    pt2 = QgsPointXY(vertices[1])
    pt3 = QgsPointXY(vertices[2])

    _base, arrow_a, arrow_b, arrow_c = _disrupt_arrows(pt1, pt2, pt3)

    return QgsGeometry.fromMultiPolylineXY([arrow_a, arrow_b, arrow_c])


@qgsfunction(
    'mct_fix_geometry',
    group='Military Cartography Tools'
)
def mct_fix_geometry(values, feature=None, parent=None):

    """
    Table H-XIX's own Fix (270503). Rebuilt 2026-08-13 to the
    maintainer's own dictated construction, replacing the standard's
    own zigzag template (whose exact proportions the draw rules never
    numbered - see this project's own roadmap for the pixel measurement
    that wasn't trusted) with a deliberately different, simpler shape,
    at the maintainer's own explicit instruction ("I know it is
    slightly different from what manual suggests, go with it"):

    "Simplest build - user clicks three points PT1, PT2 and PT3: Draw a
    line segment followed by upright open triangle, inverted triangle -
    continue alternate triangles, end with a line segment, the length
    of line segment and the sides of the open triangle is the
    perpendicular distance between a line joining PT1-PT2 and PT3."

    PT1-PT2 is the symbol's own full run (not a separate base the
    teeth are added to, unlike Block/Disrupt - the teeth themselves
    replace the straight line for however much of PT1-PT2 they cover).
    PT3 sets ONE length, L (the perpendicular distance to the PT1-PT2
    line), that both the flat end segments AND each triangle's own two
    sides are built from.

    The dictation fixes side length but not the triangle's own APEX
    ANGLE - not stated, only shown as "open triangle" (two sides, no
    base). Built at 60 degrees/equilateral proportions (half-span L/2,
    height L*sqrt(3)/2), reusing the exact proportions this project's
    own antitank wall/obstacle line "vee" tiles already settled on for
    the same kind of open-triangle tooth - a placement call, not a
    measurement, the one part of this construction to check.

    Complete teeth (each consuming a horizontal span of L) are packed
    between two flat runs of at least L each; since PT1-PT2's own
    length is unlikely to be an exact multiple of L, any leftover
    distance is split evenly between the two flat runs so the whole
    tooothed pattern sits centred on the line rather than jammed
    against one end.

    No arrowhead - the maintainer's own construction doesn't have one,
    unlike the standard's own template.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1 = QgsPointXY(vertices[0])
    pt2 = QgsPointXY(vertices[1])
    pt3 = QgsPointXY(vertices[2])

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None:
        return geometry

    (ux, uy), (nx, ny), tooth_length = projection

    total_length = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    if tooth_length == 0 or total_length <= 0:
        return QgsGeometry.fromPolylineXY([pt1, pt2])

    half_span = tooth_length / 2.0
    height = tooth_length * math.sqrt(3.0) / 2.0

    # An optional run of extra flat line at the PT2 end, for a letter
    # set into it - Table H-XXIV's own Fix carries an "F" there. Twice
    # the gap, so a length of line still shows either side of it.
    # Table H-XIX's own Fix passes nothing and is unchanged.
    letter_gap = _page_gap_in_map_units(values, 1, pt2)

    lead_extra = 2.0 * letter_gap

    if lead_extra >= total_length - 2.0 * tooth_length:
        lead_extra = 0.0
        letter_gap = 0.0

    usable = total_length - 2.0 * tooth_length - lead_extra

    tooth_count = max(0, int(usable // tooth_length)) if usable > 0 else 0

    leftover = usable - tooth_count * tooth_length if usable > 0 else 0.0

    start_flat = tooth_length + (leftover / 2.0 if usable > 0 else 0.0)

    def point_at(distance, height_sign=0.0):

        return QgsPointXY(
            pt1.x() + distance * ux + height_sign * height * nx,
            pt1.y() + distance * uy + height_sign * height * ny,
        )

    points = [pt1]

    cursor = min(start_flat, total_length)

    points.append(point_at(cursor))

    sign = 1.0

    for _tooth in range(tooth_count):

        cursor += half_span
        points.append(point_at(cursor, sign))

        cursor += half_span
        points.append(point_at(cursor))

        sign = -sign

    if letter_gap <= 0:

        points.append(pt2)

        return QgsGeometry.fromPolylineXY(points)

    # The lengthened lead run, broken around the letter. Returned as a
    # MultiLineString - the teeth and the first part of the run are one
    # continuous path, the tail past the letter is the other.
    flat_start = cursor

    flat_length = total_length - flat_start

    before = flat_start + (flat_length - letter_gap) / 2.0

    after = before + letter_gap

    points.append(point_at(before))

    return QgsGeometry.fromMultiPolylineXY(
        [points, [point_at(after), pt2]]
    )


def _obstacle_bypass_frame(pt1, pt2, pt3):

    """
    Table H-XIX's own Obstacle Bypass family (270601-270603). Per the
    standard's own draw rules: "Points 1 and 2 define the tips of the
    arrowheads and point 3 defines the rear of the symbol... the
    vertical line at the rear of the symbol will be the same length as
    the opening" - so PT1/PT2 are the two arrow TIPS, and PT3's own
    perpendicular distance from the PT1-PT2 line sets both the rear
    line's offset and the arrows' own length.

    Returns (rear_top, rear_bottom, arrow_top, arrow_bottom, depth) -
    rear_top/rear_bottom are PT1/PT2 shifted toward PT3 by that
    perpendicular distance (`depth`), and each arrow is a [rear, tip]
    pair. Degenerate (PT1==PT2, or PT3 on the PT1-PT2 line) collapses
    every part to PT1 rather than guessing, same convention as
    _disrupt_arrows.
    """

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:

        return pt1, pt1, [pt1, pt1], [pt1, pt1], 0.0

    (_ux, _uy), (nx, ny), depth = projection

    rear_top = QgsPointXY(pt1.x() + depth * nx, pt1.y() + depth * ny)
    rear_bottom = QgsPointXY(pt2.x() + depth * nx, pt2.y() + depth * ny)

    return rear_top, rear_bottom, [rear_top, pt1], [rear_bottom, pt2], depth


@qgsfunction(
    'mct_obstacle_bypass_arrows',
    group='Military Cartography Tools'
)
def mct_obstacle_bypass_arrows(values, feature=None, parent=None):

    """
    The two arrows shared by every Obstacle Bypass variant (Easy/
    Difficult/Impossible) - from the rear line's own top/bottom ends
    out to PT1/PT2's own tips. Used both to draw the arrow shafts and,
    scoped to just this expression, to place the arrowhead markers
    (LastVertex lands on PT1 and PT2, the tips).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    _rear_top, _rear_bottom, arrow_top, arrow_bottom, _depth = (
        _obstacle_bypass_frame(pt1, pt2, pt3)
    )

    return QgsGeometry.fromMultiPolylineXY([arrow_top, arrow_bottom])


@qgsfunction(
    'mct_obstacle_bypass_arrow_length',
    group='Military Cartography Tools'
)
def mct_obstacle_bypass_arrow_length(values, feature=None, parent=None):

    """
    How long each Obstacle Bypass arrow is, in LAYER UNITS - PT3's own
    perpendicular distance to the PT1-PT2 line. Used to scale the
    arrowhead marker with the drawn symbol: "the arrow head dimension
    remains same whether i draw a small obstacle or big... arrowhead
    should also become small if the lines are small, upto the current
    size which will be the max" (the maintainer, 2026-08-13). The
    caller sizes the marker in MAP UNITS from this and caps it in mm
    via QgsMapUnitScale, so a small obstacle gets a proportionally
    small arrowhead while a large one tops out at the fixed size the
    first build used everywhere.

    Accepts EITHER form of input, which is not optional politeness:
    this is evaluated as a data-defined size on a marker nested inside
    a geometry generator, and inside a generator's own sub-symbol
    `$geometry` is the GENERATED geometry (here, the two arrows as a
    MultiLineString), not the feature's raw three clicked points.
    `asPolyline()` RAISES on a MultiLineString rather than returning
    empty, so a raw-geometry-only version errors out, QGIS falls back
    to the marker's static size, and every arrowhead renders the same
    size no matter the obstacle - exactly the bug this function was
    added to fix, silently reintroduced. Each generated arrow part is
    [rear, tip], so its own length IS this same distance.

    Returns 0 for degenerate input, which the caller's own cap turns
    into "draw nothing" rather than an error.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return 0.0

    if geometry.isMultipart():

        parts = geometry.asMultiPolyline()

        if not parts or len(parts[0]) < 2:
            return 0.0

        start, end = parts[0][0], parts[0][1]

        return math.hypot(end.x() - start.x(), end.y() - start.y())

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return 0.0

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None:
        return 0.0

    return projection[2]


@qgsfunction(
    'mct_obstacle_bypass_rear_easy',
    group='Military Cartography Tools'
)
def mct_obstacle_bypass_rear_easy(values, feature=None, parent=None):

    """
    Obstacle Bypass Easy (270601) - the plain rear line, PT1/PT2
    shifted toward PT3 by PT3's own perpendicular distance.

    Optional `gap` (page millimetres) and `map_scale` break it at its
    own midpoint, for Table H-XXIV's own Bypass (340300), which is this
    same symbol with a "B" set into that line. Table H-XIX's own 270601
    passes neither and is unchanged.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    rear_top, rear_bottom, _at, _ab, _depth = _obstacle_bypass_frame(
        pt1, pt2, pt3
    )

    span = math.hypot(
        rear_bottom.x() - rear_top.x(), rear_bottom.y() - rear_top.y()
    )

    gap_units = _page_gap_in_map_units(values, 1, rear_top)

    if span == 0 or gap_units <= 0 or gap_units >= span:
        return QgsGeometry.fromPolylineXY([rear_top, rear_bottom])

    ux = (rear_bottom.x() - rear_top.x()) / span
    uy = (rear_bottom.y() - rear_top.y()) / span

    before = (span - gap_units) / 2.0
    after = (span + gap_units) / 2.0

    return QgsGeometry.fromMultiPolylineXY(
        [
            [
                rear_top,
                QgsPointXY(
                    rear_top.x() + before * ux, rear_top.y() + before * uy
                ),
            ],
            [
                QgsPointXY(
                    rear_top.x() + after * ux, rear_top.y() + after * uy
                ),
                rear_bottom,
            ],
        ]
    )


@qgsfunction(
    'mct_obstacle_bypass_rear_midpoint',
    group='Military Cartography Tools'
)
def mct_obstacle_bypass_rear_midpoint(values, feature=None, parent=None):

    """
    The anchor for Table H-XXIV Bypass's own "B" - the middle of the
    rear line, which is the middle of the gap
    mct_obstacle_bypass_rear_easy() cuts for it.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    rear_top, rear_bottom, _at, _ab, _depth = _obstacle_bypass_frame(
        pt1, pt2, pt3
    )

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            (rear_top.x() + rear_bottom.x()) / 2.0,
            (rear_top.y() + rear_bottom.y()) / 2.0,
        )
    )


# Obstacle Bypass Difficult's own zigzag. Corrected twice on
# 2026-08-13 from the maintainer's own render reviews: first "from the
# arrows, initially start with a small line segment, the zig-zag, then
# another line segment to connect with the next arrow base" (flat runs
# at both ends, not a zigzag spanning the full rear line), then "the
# teeth angles are too wide, reduce the angle to 30 deg, making the
# teeth closer and more in number."
#
# That second correction is why the tooth count is now DERIVED rather
# than fixed. The first build set a segment count and let the apex
# angle fall out of it (~83 degrees, measured after the fact); the
# apex angle is the thing actually specified, so it is now the input:
# a tooth alternates between the rear axis and a peak `amplitude` out,
# and its own apex angle is 2*atan(step/amplitude), so pinning that at
# 30 degrees fixes step = amplitude * tan(15 degrees) and the count
# follows from however much rear line there is to fill. Narrower teeth
# mean more of them, exactly as asked.
_BYPASS_ZIGZAG_AMPLITUDE_RATIO = 0.2
_BYPASS_ZIGZAG_FLAT_RATIO = 0.1
_BYPASS_ZIGZAG_APEX_ANGLE_DEG = 30


@qgsfunction(
    'mct_obstacle_bypass_rear_difficult',
    group='Military Cartography Tools'
)
def mct_obstacle_bypass_rear_difficult(values, feature=None, parent=None):

    """
    Obstacle Bypass Difficult (270602) - the rear line's own "spring"
    zigzag: a flat run from rear_top, then the zigzag body (bulging
    toward PT3 and touching the flat run's own axis at every other
    vertex), then a flat run into rear_bottom. The tooth COUNT is
    derived from the dictated 30-degree apex angle rather than fixed -
    see _BYPASS_ZIGZAG_APEX_ANGLE_DEG's own comment.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:
        return QgsGeometry.fromPolylineXY([pt1, pt1])

    (_ux, _uy), (nx, ny), depth = projection

    rear_top, rear_bottom, _at, _ab, _depth = _obstacle_bypass_frame(
        pt1, pt2, pt3
    )

    amplitude = depth * _BYPASS_ZIGZAG_AMPLITUDE_RATIO

    flat_start = QgsPointXY(
        rear_top.x()
        + _BYPASS_ZIGZAG_FLAT_RATIO * (rear_bottom.x() - rear_top.x()),
        rear_top.y()
        + _BYPASS_ZIGZAG_FLAT_RATIO * (rear_bottom.y() - rear_top.y()),
    )
    flat_end = QgsPointXY(
        rear_top.x()
        + (1 - _BYPASS_ZIGZAG_FLAT_RATIO) * (rear_bottom.x() - rear_top.x()),
        rear_top.y()
        + (1 - _BYPASS_ZIGZAG_FLAT_RATIO) * (rear_bottom.y() - rear_top.y()),
    )

    body_length = math.hypot(
        flat_end.x() - flat_start.x(), flat_end.y() - flat_start.y()
    )

    # step = amplitude * tan(apex/2) is what makes each tooth's own
    # apex angle come out at _BYPASS_ZIGZAG_APEX_ANGLE_DEG. The count
    # is then whatever fills the body, rounded to an EVEN number so
    # the zigzag starts and ends back on the rear axis rather than
    # stranded at a peak.
    step = amplitude * math.tan(
        math.radians(_BYPASS_ZIGZAG_APEX_ANGLE_DEG / 2.0)
    )

    if step <= 0 or body_length <= 0:
        return QgsGeometry.fromPolylineXY([rear_top, rear_bottom])

    segments = max(2, int(round(body_length / step / 2.0)) * 2)

    points = [rear_top]

    for i in range(segments + 1):

        t = i / segments

        base_x = flat_start.x() + t * (flat_end.x() - flat_start.x())
        base_y = flat_start.y() + t * (flat_end.y() - flat_start.y())

        bulge = amplitude if (0 < i < segments and i % 2 == 1) else 0.0

        points.append(
            QgsPointXY(base_x + bulge * nx, base_y + bulge * ny)
        )

    points.append(rear_bottom)

    return QgsGeometry.fromPolylineXY(points)


# Obstacle Bypass Impossible's own hook stubs, as fractions of the
# symbol's own height (|PT1-PT2|, the stub) and depth (PT3's own
# perpendicular distance, the cap tick). "Reduce the distance between
# the stubs by 30%, the stub length is fine" - asked TWICE on
# 2026-08-13, each time compounding on the last, so the gap has gone
# 0.5 -> 0.35 -> 0.245 of the height and STUB_RATIO with it
# (0.25 -> 0.325 -> 0.3775, always (1 - gap) / 2).
_BYPASS_HOOK_STUB_RATIO = 0.3775
_BYPASS_HOOK_TICK_RATIO = 0.35


@qgsfunction(
    'mct_obstacle_bypass_rear_impossible',
    group='Military Cartography Tools'
)
def mct_obstacle_bypass_rear_impossible(values, feature=None, parent=None):

    """
    Obstacle Bypass Impossible (270603) - the rear line is replaced by
    two independent hooks (nothing spanning the gap between them,
    matching the standard's own template, which shows the opening as
    fully closed off at each end rather than spanned). Each hook is a
    stub running along the rear axis from its own arrow base, plus a
    perpendicular tick crossing that stub's far end - so FOUR parts,
    not two: the tick meets the stub in a T, which no single polyline
    can trace.

    The tick is CENTRED on the rear axis (corrected 2026-08-13 - "the
    center or middle of the stub should touch the perpendicular,
    presently the end is touching": it used to run from the stub's own
    end outward, so only its near end sat on the axis; it now straddles
    it, from -tick/2 to +tick/2).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:
        return QgsGeometry.fromMultiPolylineXY([[pt1, pt1]])

    (ux, uy), (nx, ny), depth = projection

    rear_top, rear_bottom, _at, _ab, _depth = _obstacle_bypass_frame(
        pt1, pt2, pt3
    )

    height = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    stub = height * _BYPASS_HOOK_STUB_RATIO
    half_tick = depth * _BYPASS_HOOK_TICK_RATIO / 2.0

    def hook(base, direction):

        elbow = QgsPointXY(
            base.x() + direction * stub * ux,
            base.y() + direction * stub * uy,
        )

        tick = [
            QgsPointXY(
                elbow.x() - half_tick * nx, elbow.y() - half_tick * ny
            ),
            QgsPointXY(
                elbow.x() + half_tick * nx, elbow.y() + half_tick * ny
            ),
        ]

        return [base, elbow], tick

    stub_top, tick_top = hook(rear_top, 1.0)
    stub_bottom, tick_bottom = hook(rear_bottom, -1.0)

    return QgsGeometry.fromMultiPolylineXY(
        [stub_top, tick_top, stub_bottom, tick_bottom]
    )


def _roadblock_frame(pt1, pt2, pt3):

    """
    Shared by the Roadblock family (271201-271204, under "Roadblocks,
    Craters and Blown Bridges"): "Points 1 and 2 determine the
    centerline of the symbol and point 3 determines its width" - the
    drawn main line sits ON PT1-PT2 (arrowhead at PT1, per every
    variant's own template), and a second line runs parallel to it,
    offset toward PT3 by PT3's own perpendicular distance from the
    PT1-PT2 line.

    Returns (main, parallel, offset_pt1, offset_pt2) - main/parallel
    are [start, end] pairs, offset_pt1/offset_pt2 are PT1/PT2 shifted
    toward PT3 (also needed by Roadblock Complete's own crossed
    variant). Degenerate cases collapse to PT1.
    """

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:
        return [pt1, pt1], [pt1, pt1], pt1, pt1

    (_ux, _uy), (nx, ny), depth = projection

    offset_pt1 = QgsPointXY(pt1.x() + depth * nx, pt1.y() + depth * ny)
    offset_pt2 = QgsPointXY(pt2.x() + depth * nx, pt2.y() + depth * ny)

    return [pt1, pt2], [offset_pt1, offset_pt2], offset_pt1, offset_pt2


def _roadblock_vertices(geometry):

    if geometry is None or geometry.isEmpty():
        return None

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return None

    return tuple(QgsPointXY(v) for v in vertices[:3])


@qgsfunction(
    'mct_roadblock_main_line',
    group='Military Cartography Tools'
)
def mct_roadblock_main_line(values, feature=None, parent=None):

    """
    The Roadblock family's own main line, PT1-PT2 - drawn on every
    variant (Planned/Readiness 1/Readiness 2), with an arrowhead at
    PT1 (LastVertex needs the tip last, so this returns [PT2, PT1]).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    points = _roadblock_vertices(values[0])

    if points is None:
        return values[0]

    pt1, pt2, _pt3 = points

    return QgsGeometry.fromPolylineXY([pt2, pt1])


@qgsfunction(
    'mct_roadblock_parallel_line',
    group='Military Cartography Tools'
)
def mct_roadblock_parallel_line(values, feature=None, parent=None):

    """The Roadblock family's own second line, parallel to PT1-PT2,
    offset toward PT3 by PT3's own perpendicular distance. No
    arrowhead - every variant's own template draws it plain."""

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    points = _roadblock_vertices(values[0])

    if points is None:
        return values[0]

    pt1, pt2, pt3 = points

    _main, parallel, _op1, _op2 = _roadblock_frame(pt1, pt2, pt3)

    return QgsGeometry.fromPolylineXY(parallel)


def _rotate_point(point, center, angle_degrees):

    """Rotate `point` about `center` by `angle_degrees`, counter-
    clockwise in a standard (x right, y up) frame. Shared by Roadblock
    Complete's own doubled X."""

    angle = math.radians(angle_degrees)

    cos_a, sin_a = math.cos(angle), math.sin(angle)

    dx, dy = point.x() - center.x(), point.y() - center.y()

    return QgsPointXY(
        center.x() + dx * cos_a - dy * sin_a,
        center.y() + dx * sin_a + dy * cos_a,
    )


# Roadblock Complete's own second pair of parallel lines, per the
# maintainer's own render review: "add another set of parallel lines
# of same dimensions at 50 deg angle to the first set" - "set" means
# the SAME main-plus-parallel pair the other three roadblock variants
# draw, copied and rotated about the pair's own centre, so the symbol
# reads as two parallel pairs crossing (which is what the standard's
# own template actually shows). This project's first build had
# mis-read that template as a single X built from the pair's own
# diagonals.
_ROADBLOCK_COMPLETE_SECOND_SET_ANGLE_DEG = 50


def _roadblock_complete_parts(pt1, pt2, pt3):

    """
    Roadblock Complete's four lines: the ordinary main/parallel pair,
    plus that same pair rotated _ROADBLOCK_COMPLETE_SECOND_SET_ANGLE_DEG
    about its own centre. Main lines come back tip-last (PT2 -> PT1) so
    an arrowhead's own LastVertex placement lands on the tip, matching
    mct_roadblock_main_line's own convention.

    Returns (mains, parallels) - each a list of two [start, end] pairs,
    so callers can scope arrowheads to the mains alone.
    """

    main, parallel, offset_pt1, offset_pt2 = _roadblock_frame(pt1, pt2, pt3)

    center = QgsPointXY(
        (pt1.x() + pt2.x() + offset_pt1.x() + offset_pt2.x()) / 4.0,
        (pt1.y() + pt2.y() + offset_pt1.y() + offset_pt2.y()) / 4.0,
    )

    angle = _ROADBLOCK_COMPLETE_SECOND_SET_ANGLE_DEG

    def rotated(pair):

        return [_rotate_point(p, center, angle) for p in pair]

    main_tip_last = [main[1], main[0]]

    mains = [main_tip_last, rotated(main_tip_last)]
    parallels = [list(parallel), rotated(parallel)]

    return mains, parallels


@qgsfunction(
    'mct_roadblock_complete_geometry',
    group='Military Cartography Tools'
)
def mct_roadblock_complete_geometry(values, feature=None, parent=None):

    """
    Roadblock Complete/Executed (271204) - all four lines: the same
    main-plus-parallel pair the other three roadblock variants draw,
    plus that pair rotated 50 degrees about its own centre, so the two
    pairs cross (see _ROADBLOCK_COMPLETE_SECOND_SET_ANGLE_DEG's own
    comment). Still ASSUMED, not CONFIRMED - the standard's own draw
    rules give no numbered angle, so 50 degrees is the maintainer's own
    call rather than a measured one.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    points = _roadblock_vertices(values[0])

    if points is None:
        return values[0]

    mains, parallels = _roadblock_complete_parts(*points)

    return QgsGeometry.fromMultiPolylineXY(mains + parallels)


# Bridge or Gap (271100), rebuilt 2026-08-13 per the maintainer's own
# correction to the first, standard-template-derived build: "user will
# click only two points PT1 and PT2, make two parallel lines and
# require unique designation Field T, so the gap between the lines
# will be slightly more than the text, wings or flares at both ends,
# outwards at 30deg." PT1-PT2 is the CENTRELINE, not one side of a
# 4-point gap.
#
# **The channel is a fixed MILLIMETRE width, not a fraction of the
# line's own length** - "keep the gap at a fixed unit rather than
# making it length of line dependent, as such it is a linear feature,
# so the width increasing with the length is not practical" (the
# maintainer, after two length-proportional versions - 0.12 then 0.18
# of the length - both looked wrong). That is right, and it also
# settles the text-fitting question left open by those versions: the
# label is sized in millimetres too, so a millimetre channel holds it
# at any zoom and any bridge length, which no ratio-of-length could.
#
# The consequence for THIS module is that Bridge or Gap's own
# cross-section is no longer built here. A geometry generator works in
# layer units and has no access to page units, so the parallel offset
# and the end flares both moved to the SYMBOLOGY layer - millimetre
# line offsets and a millimetre end-cap glyph, see
# _bridge_or_gap_symbol(). All this function does is hand back the
# centreline itself.


@qgsfunction(
    'mct_bridge_or_gap_geometry',
    group='Military Cartography Tools'
)
def mct_bridge_or_gap_geometry(values, feature=None, parent=None):

    """
    Bridge or Gap (271100) - the symbol's own centreline, PT1 to PT2.

    Deliberately the first two clicked points rather than the raw
    geometry: the two parallel lines are drawn from this by
    millimetre-offset symbol layers, so any extra vertices a user
    happened to click would otherwise bend the whole symbol. See this
    function's own preamble comment for why the cross-section is
    millimetre-based and so lives in the symbology, not here.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 2:
        return geometry

    pt1, pt2 = QgsPointXY(vertices[0]), QgsPointXY(vertices[1])

    if pt1 == pt2:
        return geometry

    return QgsGeometry.fromPolylineXY([pt1, pt2])


@qgsfunction(
    'mct_bridge_flare_svg',
    group='Military Cartography Tools'
)
def mct_bridge_flare_svg(values, feature=None, parent=None):

    """
    Bridge or Gap's own end cap - the pair of outward "wings" at one
    end of the channel - as an inline "base64:<...>" SVG, for a marker
    placed on the centreline's first or last vertex.

    Drawn as a glyph rather than as geometry because the whole
    cross-section is fixed in MILLIMETRES (see the preamble above), and
    a rotating marker is the only thing in QGIS sized that way that can
    also follow the line's own direction.

    Arguments: colour, half_width_mm (the channel's own half-width, so
    each wing starts exactly on its parallel line), flare_mm, angle_deg
    (30, the maintainer's own number), stroke_mm, and at_end (True for
    the last vertex, False for the first - the two are mirror images,
    because QGIS rotates a marker to the LINE's direction at both ends
    rather than reversing it at the start).

    The viewBox is deliberately SYMMETRIC about the origin so the glyph
    centres itself on the vertex needing no offset. QGIS sizes an SVG
    marker by its WIDTH, so with a viewBox `2*run` wide and the marker
    size set to that same number of millimetres, one viewBox unit is
    exactly one millimetre and the height follows correctly.
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"
    half_width = float(values[1]) if len(values) > 1 else 2.28
    flare = float(values[2]) if len(values) > 2 else 3.0
    angle_deg = float(values[3]) if len(values) > 3 else 30.0
    stroke = float(values[4]) if len(values) > 4 else 0.4
    at_end = bool(values[5]) if len(values) > 5 else True

    angle = math.radians(angle_deg)

    run = flare * math.cos(angle)
    rise = flare * math.sin(angle)

    if run <= 0:
        return ""

    direction = 1.0 if at_end else -1.0

    outer = half_width + rise

    # SVG y grows DOWNWARD, hence the negative y for the "upper" wing.
    # Both wings start ON their own parallel line (+/- the channel's
    # half-width) and bend further out from there.
    paths = [
        "M 0,{:.4f} L {:.4f},{:.4f}".format(
            -half_width, direction * run, -outer
        ),
        "M 0,{:.4f} L {:.4f},{:.4f}".format(
            half_width, direction * run, outer
        ),
    ]

    body = "".join(
        '<path d="{}" fill="none" stroke="{}" stroke-width="{:.4f}"'
        ' stroke-linecap="round"/>'.format(path, colour, stroke)
        for path in paths
    )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="{minx:.4f} {miny:.4f} {width:.4f} {height:.4f}"'
        ' width="{width:.4f}" height="{height:.4f}">{body}</svg>'
    ).format(
        minx=-run, miny=-outer, width=2 * run, height=2 * outer, body=body
    )

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


# Overhead Wire's pylon, drawn by the maintainer themselves and used
# verbatim - the path data below is theirs, not derived from anything.
# It replaces a borrowed SIDC glyph (Land Installation's
# Telecommunications Tower, 121203) which rendered correctly but came
# with an installation frame and indicator bar that had to be stripped.
#
# The viewBox is 100 wide by 160 tall, and QGIS sizes an SVG marker by
# its WIDTH - so a 6mm tower is a 3.75mm marker
# (6 * 100/160), not a 6mm one. _OVERHEAD_WIRE_TOWER_MM derives that
# rather than restating it, so the two cannot disagree.
_TOWER_VIEWBOX_WIDTH = 100
_TOWER_VIEWBOX_HEIGHT = 160

_TOWER_PATHS = (
    # Top vertical mast
    "M50 8 L50 35",
    # Horizontal crossbar
    "M18 35 L82 35",
    # Downturned ends of crossbar
    "M18 35 L18 44",
    "M82 35 L82 44",
    # Main left leg
    "M48 35 L32 148",
    # Main right leg
    "M52 35 L68 148",
    # Internal horizontal brace
    "M38 88 L62 88",
    # Lower V brace
    "M32 148 L50 122 L68 148",
    # Right diagonal support
    "M52 35 L91 124",
)

_TOWER_STROKE_WIDTH = 6


@qgsfunction(
    'mct_overhead_wire_tower_svg',
    group='Military Cartography Tools'
)
def mct_overhead_wire_tower_svg(values, feature=None, parent=None):

    """
    Overhead Wire's own transmission pylon as an inline
    "base64:<...>" SVG, for a marker on every vertex of the wire.

    The geometry is the maintainer's own drawing, reproduced exactly;
    only the stroke colour is parameterised, so the pylon follows the
    obstacle colour field (green or black) like every other glyph in
    this table.
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"

    body = "".join(
        '<path d="{}"/>'.format(path) for path in _TOWER_PATHS
    )

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="0 0 {width} {height}"'
        ' width="{width}" height="{height}">'
        '<g fill="none" stroke="{colour}" stroke-width="{stroke}"'
        ' stroke-linecap="round" stroke-linejoin="round">'
        "{body}</g></svg>"
    ).format(
        width=_TOWER_VIEWBOX_WIDTH,
        height=_TOWER_VIEWBOX_HEIGHT,
        colour=colour,
        stroke=_TOWER_STROKE_WIDTH,
        body=body,
    )

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


# ============================================================
# Table H-XX - field fortification (Mini-Phase H17)
# ============================================================

@qgsfunction(
    'mct_rampart_svg',
    group='Military Cartography Tools'
)
def mct_rampart_svg(values, feature=None, parent=None):

    """
    One tile of Fortified Line's own crenellated rampart (290900), as
    an inline "base64:<...>" SVG for a marker tiled along the line.

    The tile is a single square wave - one merlon with half a gap on
    either side of it - drawn so consecutive tiles butt together into a
    continuous profile: it runs level from x=0 to x=25, rises, runs
    along the merlon top to x=75, drops back to the baseline and runs
    level to x=100, where the next tile's own level run continues it.

    **The gap is split across the tile's two ends deliberately, not
    just tucked after the merlon.** The merlon is 50 wide with 50 of
    gap between merlons either way, so the rhythm is identical; what
    changes is the phase. With the whole gap trailing, the very first
    tile opened with a merlon rising straight out of PT1, and Table
    H-XX's own template does not - it starts with a short level run,
    exactly as it ends with one at PT2, and that run is what tells the
    reader which side the ramparts stand on. The maintainer's own
    words: "at pt1 it is directly starting with the open square, it
    should start with a small line segment like it ends at pt2. that
    line segment actually determines which way the ramparts are
    pointing."

    The profile IS the line here, exactly as Table H-XIX's antitank
    wall and Obstacle Line are, so nothing draws a straight line
    underneath. Ramparts rise toward NEGATIVE y, which a marker
    rotated to the line's own bearing puts on the LEFT of travel - the
    side the standard's own template draws them.
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"
    stroke = float(values[1]) if len(values) > 1 and values[1] else 11.0

    # Baseline at y=50 of a 0..100 box, merlon top at y=12 - so the
    # merlon stands a little under half the tile's own width. The
    # standard numbers none of this; see field_fortification.py's own
    # module docstring.
    path = "M 0,50 L 25,50 L 25,12 L 75,12 L 75,50 L 100,50"

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="0 0 100 100" width="100" height="100">'
        '<path d="{path}" fill="none" stroke="{colour}"'
        ' stroke-width="{stroke}" stroke-linecap="butt"'
        ' stroke-linejoin="miter"/></svg>'
    ).format(path=path, colour=colour, stroke=stroke)

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


# ============================================================
# Table H-VIII: Contain (151204) and Retain (151205)
# ============================================================
#
# The two entries H4 deferred in 2026-08-09 as "procedural circle/arc
# constructions [that] don't fit the one-polygon-one-symbol pattern".
# They still don't - so they are built as LINES from their own anchor
# points instead, the same call Base Defense Zone already made in
# airspace_control_measures.py.
#
# **Everything below is a fraction of the construction's own radius,
# never a millimetre.** That is what makes them buildable at all: a
# geometry generator works in layer units and cannot see page units
# (`@map_scale` does not resolve there - confirmed twice, see
# offensive_control_measures.py). A tick length of "1/3 of the radius"
# is scale-free and generates cleanly; the standard's own rule ties
# tick length to the echelon field's text height instead, which is a
# page unit this project cannot reach from here and which the
# maintainer replaced with these fractions on 2026-08-14.

# Contain: 180 degrees of arc, opening on PT3's own side.
_CONTAIN_TOOTH_STEP_DEG = 18.0
_CONTAIN_TOOTH_LENGTH_RATIO = 1.0 / 3.0

# Retain: 330 degrees drawn, leaving a 30-degree opening.
#
# **The standard contradicts itself here.** Its DRAW RULES text says
# "The opening will be a 30-degree arc of the circle", which makes the
# drawn arc 330 - but its own template and example both draw an opening
# of roughly 55-60 degrees. Built at 300 first, on the maintainer's own
# dictated geometry ("draw a circle of 300deg"), then settled at 330 by
# them after seeing it rendered, 2026-08-14: the written rule wins over
# the drawing. One constant, so either reading stays one line away.
_RETAIN_ARC_DEG = 330.0
_RETAIN_TOOTH_STEP_DEG = 15.0
_RETAIN_TOOTH_LENGTH_RATIO = 1.0 / 5.0

# Both letters sit ON the perimeter, in a gap in the arc rather than
# floating beside it - the maintainer's own instruction ("should be on
# the perimeter, not next to it, with mask") and what both templates
# draw.
_LETTER_RADIUS_RATIO = 1.0

# **That gap is cut into the GEOMETRY, not painted by a mask.**
#
# QGIS's own Selective Masking was tried first, and it is the right
# tool anywhere else: c2_measures.py's own Boundary uses it, and it
# works there. It does NOT reach symbol layers that live inside a
# QgsGeometryGeneratorSymbolLayer - probed both ways, referencing the
# nested line layer's own id and the generator's, and neither takes.
# (What looked at first like a working mask on the arc turned out to be
# the letter glyph simply covering it, same colour.) Every part of
# Contain and Retain is generated, so nothing here can be masked at
# all, and the gap has to be real geometry.
#
# The angle is a compromise the fixed-size letter forces: the glyph is
# a label in MILLIMETRES while the arc is in layer units, so no single
# figure is right at every zoom. 14 degrees suits the sizes these are
# drawn at.
_LETTER_GAP_DEG = 14.0

# The gap cut into Contain's own arrow shaft for the "ENY" label, as a
# fraction of the RADIUS - scale-free, the same principle as
# _LETTER_GAP_DEG above and for the same reason.
#
# **The gap is geometry because the mask is not available here.**
# "ENY" was built with a painted mask on the arrow, on the belief that
# Selective Masking worked there even though it demonstrably did not on
# the arc. It does not work there either - the arrow is a geometry
# generator like everything else in these two symbols, and QGIS cannot
# reach a symbol layer nested inside one. Reported by the maintainer
# 2026-08-14: "the ENY text on the shaft is not masked, so the shaft is
# running through the text". The mask is gone; the shaft is cut
# instead, exactly as the "C" and "R" gaps are.
#
# Three glyphs against the letters' one, so this is wider than
# _LETTER_GAP_DEG's own 0.244 radians of arc - settled by render at a
# typical symbol size, like that one.
_CONTAIN_ENY_GAP_RATIO = 0.62

# ...but never more than this fraction of the arrow's own LENGTH. The
# radius and the arrow are independent - PT3 sets the arrow, PT1/PT2
# the radius - so a short arrow on a wide semicircle would otherwise be
# cut away completely, leaving the arrowhead floating with no shaft.
_CONTAIN_ENY_MAX_GAP_OF_ARROW = 0.5

# Points per 180 degrees when flattening an arc to a polyline. High
# enough that the curve reads as a curve at any zoom this plugin is
# used at.
_ARC_SEGMENTS_PER_SEMICIRCLE = 72


def _arc_points(centre, radius, start_rad, sweep_rad, segments):

    """A flattened arc as a list of QgsPointXY, inclusive of both ends."""

    return [
        QgsPointXY(
            centre.x() + radius * math.cos(start_rad + sweep_rad * i / segments),
            centre.y() + radius * math.sin(start_rad + sweep_rad * i / segments),
        )
        for i in range(segments + 1)
    ]


def _arc_with_letter_gap(centre, radius, start_rad, sweep_rad, segments,
                         gap_at_rad):

    """
    An arc split into two parts, leaving a gap for the "C"/"R" that
    sits on it - see _LETTER_GAP_DEG for why this is geometry rather
    than a mask.
    """

    half_gap = math.radians(_LETTER_GAP_DEG) / 2.0

    direction = 1.0 if sweep_rad >= 0 else -1.0

    before_end = gap_at_rad - half_gap * direction
    after_start = gap_at_rad + half_gap * direction

    parts = []

    for part_start, part_sweep in (
        (0.0, before_end),
        (after_start, sweep_rad - after_start),
    ):

        if abs(part_sweep) < 1e-9:
            continue

        count = max(
            2, int(round(segments * abs(part_sweep) / abs(sweep_rad)))
        )

        parts.append(
            _arc_points(
                centre, radius, start_rad + part_start, part_sweep, count
            )
        )

    if not parts:
        return QgsGeometry()

    return QgsGeometry.fromMultiPolylineXY(parts)


def _radial_teeth(centre, radius, start_rad, sweep_rad, step_deg,
                  length, inward, drop_last=False, skip_deg=None):

    """
    Ticks along an arc, every `step_deg` of sweep, INCLUSIVE of both
    ends - so the first and last land exactly on the arc's own two
    endpoints.

    A half-step offset was tried first, on the reading that both
    templates leave their ends bare. They do not: "the last tooth in
    contain on both ends should be at pt1 and pt2, not slightly
    inside", and Retain's template draws a tick hard against each end
    of its opening too.

    `drop_last` leaves the final one off. Retain needs it: its arc ends
    under the arrowhead, and a tick there reads as part of the arrow -
    "the last tooth near the arrow head can be dropped, it is
    confusing".

    `skip_deg` marks where a letter sits. Both letters land exactly on
    a tick - 180 degrees is a whole number of steps for both spacings -
    and the manual does not drop that tick, it just hides the part the
    letter covers. So the tick stays and its inner end is pulled back
    instead, by the same amount of arc the letter's own gap takes out
    of the perimeter.
    """

    step = math.radians(step_deg) * (1 if sweep_rad >= 0 else -1)

    if step == 0:
        return []

    count = int(round(abs(sweep_rad) / math.radians(step_deg)))

    teeth = []

    for i in range(count + (0 if drop_last else 1)):

        angle = start_rad + step * i

        # The tick at the letter starts clear of it rather than at the
        # perimeter, so the letter reads against blank paper.
        inset = (
            radius * math.radians(_LETTER_GAP_DEG) / 2.0
            if skip_deg is not None
            and abs(i * step_deg - skip_deg) < 1e-6
            else 0.0
        )

        cos_a, sin_a = math.cos(angle), math.sin(angle)

        reach = -length if inward else length

        foot = radius - inset if inward else radius + inset

        outer = QgsPointXY(
            centre.x() + foot * cos_a, centre.y() + foot * sin_a
        )

        teeth.append(
            [
                outer,
                QgsPointXY(
                    centre.x() + (radius + reach) * cos_a,
                    centre.y() + (radius + reach) * sin_a,
                ),
            ]
        )

    return teeth


def _contain_frame(geometry):

    """
    (centre, radius, start_rad, sweep_rad, n) for Contain, or None.

    PT1 and PT2 are the endpoints of the semicircle's OPENING, so they
    are the ends of the diameter; PT3 sets the arrow's length and which
    side the opening faces. `n` is the unit vector from the PT1-PT2
    line toward PT3 - the arc bulges the OTHER way, leaving the opening
    facing PT3, which is the template's own layout.
    """

    if geometry is None or geometry.isEmpty():
        return None

    try:
        vertices = geometry.asPolyline()
    except (TypeError, ValueError):
        return None

    if len(vertices) < 3:
        return None

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None:
        return None

    (_ux, _uy), (nx, ny), _depth = projection

    centre = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
    )

    radius = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y()) / 2.0

    if radius == 0:
        return None

    start = math.atan2(pt1.y() - centre.y(), pt1.x() - centre.x())

    # Of the two 180-degree arcs from PT1 to PT2, take the one whose
    # own midpoint lies AWAY from PT3.
    sweep = math.pi

    mid = start + sweep / 2.0

    if math.cos(mid) * nx + math.sin(mid) * ny > 0:
        sweep = -sweep

    return centre, radius, start, sweep, (nx, ny)


@qgsfunction(
    'mct_contain_arc',
    group='Military Cartography Tools'
)
def mct_contain_arc(values, feature=None, parent=None):

    """
    Contain's own semicircle (151204) - PT1 to PT2, bulging away from
    PT3. The chord is deliberately NOT drawn: it is the symbol's
    opening.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _contain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep, _n = frame

    return _arc_with_letter_gap(
        centre, radius, start, sweep, _ARC_SEGMENTS_PER_SEMICIRCLE,
        sweep / 2.0,
    )


@qgsfunction(
    'mct_contain_teeth',
    group='Military Cartography Tools'
)
def mct_contain_teeth(values, feature=None, parent=None):

    """
    Contain's own ticks - every 18 degrees, one third of the radius
    long, pointing INWARD from the arc. Inward is the template's own
    (read off the picture at 480 dpi, and confirmed by the maintainer);
    Retain's point the other way.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _contain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep, _n = frame

    return QgsGeometry.fromMultiPolylineXY(
        _radial_teeth(
            centre, radius, start, sweep,
            _CONTAIN_TOOTH_STEP_DEG,
            radius * _CONTAIN_TOOTH_LENGTH_RATIO,
            inward=True,
            skip_deg=90.0,
        )
    )


def _contain_arrow_axis(geometry, frame):

    """
    (centre, tail, unit normal, depth, radius) for Contain's own arrow,
    or None when PT3 falls on the wrong side.

    The tip is the arc's own centre; the tail is `depth` back along the
    perpendicular, where `depth` is PT3's own distance from the PT1-PT2
    line. A PT3 clicked off that perpendicular is projected onto it
    rather than bending the arrow - the standard says the arrow "will
    project perpendicularly from the line between points 1 and 2".
    """

    centre, radius, _start, _sweep, (nx, ny) = frame

    try:
        pt3 = QgsPointXY(geometry.asPolyline()[2])
    except (IndexError, TypeError, ValueError):
        return None

    depth = (pt3.x() - centre.x()) * nx + (pt3.y() - centre.y()) * ny

    if depth <= 0:
        return None

    tail = QgsPointXY(centre.x() + depth * nx, centre.y() + depth * ny)

    return centre, tail, (nx, ny), depth, radius


def _contain_eny_gap(depth, radius):

    """The gap in the shaft the "ENY" label sits in - see its ratio."""

    return min(
        _CONTAIN_ENY_GAP_RATIO * radius,
        _CONTAIN_ENY_MAX_GAP_OF_ARROW * depth,
    )


@qgsfunction(
    'mct_contain_arrow',
    group='Military Cartography Tools'
)
def mct_contain_arrow(values, feature=None, parent=None):

    """
    Contain's own arrow - drawn along the perpendicular through the
    semicircle's centre, tip AT that centre.

    PT3 sets the length and the side, not the tail's own position: the
    standard says the arrow "will project perpendicularly from the line
    between points 1 and 2", so a PT3 clicked off that perpendicular is
    projected onto it rather than bending the arrow.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    frame = _contain_frame(geometry)

    if frame is None:
        return geometry

    axis = _contain_arrow_axis(geometry, frame)

    if axis is None:
        return geometry

    centre, tail, (nx, ny), depth, radius = axis

    gap = _contain_eny_gap(depth, radius)

    # Two parts with the label's own gap between them. The tip half is
    # returned LAST so the shaft still reads tail-to-tip.
    return QgsGeometry.fromMultiPolylineXY(
        [
            [
                tail,
                QgsPointXY(
                    centre.x() + (depth / 2.0 + gap / 2.0) * nx,
                    centre.y() + (depth / 2.0 + gap / 2.0) * ny,
                ),
            ],
            [
                QgsPointXY(
                    centre.x() + (depth / 2.0 - gap / 2.0) * nx,
                    centre.y() + (depth / 2.0 - gap / 2.0) * ny,
                ),
                centre,
            ],
        ]
    )


@qgsfunction(
    'mct_contain_arrow_head',
    group='Military Cartography Tools'
)
def mct_contain_arrow_head(values, feature=None, parent=None):

    """
    The tip half of Contain's own arrow, as ONE unbroken part - what
    the arrowhead marker rides on.

    It cannot ride on mct_contain_arrow() itself any more: that returns
    two parts now, and **a marker at LastVertex fires on the last
    vertex of EVERY part**, which would put a second arrowhead in the
    middle of the shaft where the "ENY" gap starts. Exactly the bug
    Retain hit when its arc was split, and fixed there the same way
    (see mct_retain_arc_end).
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    frame = _contain_frame(geometry)

    if frame is None:
        return geometry

    axis = _contain_arrow_axis(geometry, frame)

    if axis is None:
        return geometry

    centre, _tail, (nx, ny), depth, radius = axis

    gap = _contain_eny_gap(depth, radius)

    return QgsGeometry.fromPolylineXY(
        [
            QgsPointXY(
                centre.x() + (depth / 2.0 - gap / 2.0) * nx,
                centre.y() + (depth / 2.0 - gap / 2.0) * ny,
            ),
            centre,
        ]
    )


@qgsfunction(
    'mct_contain_arrow_midpoint',
    group='Military Cartography Tools'
)
def mct_contain_arrow_midpoint(values, feature=None, parent=None):

    """
    The midpoint of Contain's own arrow - where the "ENY" label sits.

    A LABEL rather than a marker glyph, because the label engine is the
    only thing in QGIS that can cut a real hole in the shaft it sits
    on: this project established in offensive_control_measures.py that
    a marker glyph has no QgsTextMaskSettings of its own. Labels place
    on the FEATURE's geometry, and the feature here is the three
    clicked points, not the arrow - so the arrow's own midpoint is
    handed to the label's data-defined position instead.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    frame = _contain_frame(geometry)

    if frame is None:
        return geometry

    axis = _contain_arrow_axis(geometry, frame)

    if axis is None:
        return geometry

    centre, _tail, (nx, ny), depth, _radius = axis

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            centre.x() + depth * nx / 2.0,
            centre.y() + depth * ny / 2.0,
        )
    )


@qgsfunction(
    'mct_contain_letter_point',
    group='Military Cartography Tools'
)
def mct_contain_letter_point(values, feature=None, parent=None):

    """The anchor for Contain's own "C", just outside the arc's midpoint."""

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _contain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep, _n = frame

    mid = start + sweep / 2.0

    reach = radius * _LETTER_RADIUS_RATIO

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            centre.x() + reach * math.cos(mid),
            centre.y() + reach * math.sin(mid),
        )
    )


def _retain_frame(geometry):

    """
    (centre, radius, start_rad, sweep_rad) for Retain, or None.

    PT1 is the centre and PT2 is both the start point and the radius.
    The sweep runs CLOCKWISE from PT2 - negative, since these are map
    coordinates with y increasing northward.
    """

    if geometry is None or geometry.isEmpty():
        return None

    try:
        vertices = geometry.asPolyline()
    except (TypeError, ValueError):
        return None

    if len(vertices) < 2:
        return None

    centre, start_point = QgsPointXY(vertices[0]), QgsPointXY(vertices[1])

    radius = math.hypot(
        start_point.x() - centre.x(), start_point.y() - centre.y()
    )

    if radius == 0:
        return None

    start = math.atan2(
        start_point.y() - centre.y(), start_point.x() - centre.x()
    )

    return centre, radius, start, -math.radians(_RETAIN_ARC_DEG)


@qgsfunction(
    'mct_retain_arc',
    group='Military Cartography Tools'
)
def mct_retain_arc(values, feature=None, parent=None):

    """
    Retain's own arc (151205) - 330 degrees clockwise from PT2, leaving
    the standard's own 30-degree opening.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _retain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep = frame

    segments = int(
        _ARC_SEGMENTS_PER_SEMICIRCLE * abs(sweep) / math.pi
    )

    # The "R" sits 180 degrees along the sweep, which is clockwise -
    # hence negative, matching _retain_letter_point().
    return _arc_with_letter_gap(
        centre, radius, start, sweep, max(segments, 2), -math.pi
    )


@qgsfunction(
    'mct_retain_arc_end',
    group='Military Cartography Tools'
)
def mct_retain_arc_end(values, feature=None, parent=None):

    """
    The last short segment of Retain's arc, for the arrowhead alone.

    It cannot ride on mct_retain_arc(): that returns TWO parts once the
    "R" gap is cut into it, and a marker on the last vertex then lands
    on the end of each - putting a second arrowhead right beside the
    letter. Caught in a render.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _retain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep = frame

    step = math.radians(2.0) * (1 if sweep >= 0 else -1)

    return QgsGeometry.fromPolylineXY(
        _arc_points(centre, radius, start + sweep - step, step, 1)
    )


@qgsfunction(
    'mct_retain_teeth',
    group='Military Cartography Tools'
)
def mct_retain_teeth(values, feature=None, parent=None):

    """
    Retain's own ticks - every 15 degrees, one fifth of the radius
    long, pointing OUTWARD. The opposite of Contain's.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _retain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep = frame

    return QgsGeometry.fromMultiPolylineXY(
        _radial_teeth(
            centre, radius, start, sweep,
            _RETAIN_TOOTH_STEP_DEG,
            radius * _RETAIN_TOOTH_LENGTH_RATIO,
            inward=False,
            drop_last=True,
            skip_deg=180.0,
        )
    )


@qgsfunction(
    'mct_retain_letter_point',
    group='Military Cartography Tools'
)
def mct_retain_letter_point(values, feature=None, parent=None):

    """
    The anchor for Retain's own "R" - half way round the sweep, just
    outside the perimeter.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _retain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, _sweep = frame

    mid = start - math.pi

    reach = radius * _LETTER_RADIUS_RATIO

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            centre.x() + reach * math.cos(mid),
            centre.y() + reach * math.sin(mid),
        )
    )


@qgsfunction(
    'mct_block_stem_foot',
    group='Military Cartography Tools'
)
def mct_block_stem_foot(values, feature=None, parent=None):

    """
    A short segment ending where Block's stem MEETS its crossbar, run
    from the tip towards that meeting point - so an arrowhead placed on
    its last vertex sits at the join and points INTO the base.

    Table H-XXIV's own Penetrate (341800) is Block's construction with
    the head there rather than at the far end: the maintainer's own
    words, "arrowhead at the point of contact between the perpendicular
    and the base".

    Its own short geometry, not the symbol's: the stem is multi-part
    once the letter gap is cut into it, and a marker on a LastVertex
    placement fires on the last vertex of EVERY part.
    """

    if len(values) < 1:
        return QgsGeometry()

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return QgsGeometry()

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return QgsGeometry()

    pt1, pt2, pt3 = (QgsPointXY(vertices[index]) for index in range(3))

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:
        return QgsGeometry()

    (_ux, _uy), (nx, ny), length = projection

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
    )

    # A twentieth of the stem is plenty to set the angle, and short
    # enough never to show from under the head itself.
    step = length / 20.0

    return QgsGeometry.fromPolylineXY(
        [
            QgsPointXY(midpoint.x() + step * nx, midpoint.y() + step * ny),
            midpoint,
        ]
    )


@qgsfunction(
    'mct_block_stem_mm',
    group='Military Cartography Tools'
)
def mct_block_stem_mm(values, feature=None, parent=None):

    """
    The length of Block's/Penetrate's stem - the perpendicular distance
    from PT3 to the PT1-PT2 line - in PAGE MILLIMETRES. Use as
    mct_block_stem_mm($geometry, @map_extent, @map_scale).

    Page, not ground, for the same reason every other size here is: the
    thing being sized from it is drawn on the page.
    """

    if len(values) < 3:
        return 0.0

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return 0.0

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return 0.0

    projection = _perpendicular_projection(
        *(QgsPointXY(vertices[index]) for index in range(3))
    )

    if projection is None:
        return 0.0

    return projection[2] * _map_millimetres_per_unit(values[1], values[2])


@qgsfunction(
    'mct_mm_in_map_units',
    group='Military Cartography Tools'
)
def mct_mm_in_map_units(values, feature=None, parent=None):

    """
    A page distance in millimetres, expressed in MAP UNITS. Use as
    mct_mm_in_map_units(<mm>, @map_extent, @map_scale).

    The inverse of mct_radius_mm(), and the thing that lets a
    page-sized gap be cut out of ground-unit geometry with QGIS's own
    line_substring() - which is how Table H-XXIV's own Seize breaks its
    curve for the "S".
    """

    if len(values) < 3:
        return 0.0

    try:
        millimetres = float(values[0])
    except (TypeError, ValueError):
        return 0.0

    per_unit = _map_millimetres_per_unit(values[1], values[2])

    if per_unit <= 0:
        return 0.0

    return millimetres / per_unit


@qgsfunction(
    'mct_radius_mm',
    group='Military Cartography Tools'
)
def mct_radius_mm(values, feature=None, parent=None):

    """
    The PT1-PT2 radius of an arc-type control measure, in PAGE
    MILLIMETRES. Use as
    mct_radius_mm($geometry, @map_extent, @map_scale).

    For Table H-XXIV's own Occupy, whose end mark is "1/5 of the
    radius subject to max size" - a page size derived from a ground
    one, so it needs the same page-not-ground conversion the
    contaminated areas' glyph does. See _map_millimetres_per_unit()
    for why a geodesic measurement is the wrong tool here.
    """

    if len(values) < 3:
        return 0.0

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return 0.0

    vertices = geometry.asPolyline()

    if len(vertices) < 2:
        return 0.0

    radius_units = math.hypot(
        vertices[1].x() - vertices[0].x(),
        vertices[1].y() - vertices[0].y()
    )

    return radius_units * _map_millimetres_per_unit(values[1], values[2])


@qgsfunction(
    'mct_secure_letter_point',
    group='Military Cartography Tools'
)
def mct_secure_letter_point(values, feature=None, parent=None):

    """
    The anchor for Secure's own "S" (Table H-XXIV, 342100) - half way
    round the sweep, ON the perimeter.

    Retain's own letter sits just OUTSIDE its arc; the maintainer asked
    for this one "on the perimeter of circle, masked", so it takes the
    radius itself. Everything else about the two is the same
    construction, and Secure reuses mct_retain_arc() and
    mct_retain_arc_end() unchanged rather than restating a 330-degree
    arc with a letter gap in it.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _retain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, _sweep = frame

    mid = start - math.pi

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            centre.x() + radius * math.cos(mid),
            centre.y() + radius * math.sin(mid),
        )
    )



# --- Isolate (Table H-XXIV, 341500) ---
#
# **Secure's construction with triangles standing on it**, at the
# maintainer's own instruction: the same 330-degree arc, the same
# arrowhead where it ends, "I" for "S", and then "draw triangles facing
# inwards, based on the perimeter, base is not drawn the perimeter arc
# acts like the base, triangles start 30 deg from pt2, and end 30 deg
# before the arrow head, size of triangles (base to tip) 1/3 of
# radius".
#
# Two figures that instruction leaves open, both taken off the
# standard's own template (page 646, measured on the rendered page):
#
# - The SPACING. The template's triangles sit 45 degrees apart - their
#   apexes measure out at 0, 42, 93 and 142 degrees round the half of
#   the drawing its captions do not cross. 45 also divides the 270
#   degrees the instruction leaves for them exactly six times, so seven
#   triangles land on 30, 75, 120, 165, 210, 255 and 300 degrees of
#   sweep, the first and last exactly where they were asked for.
# - The BASE WIDTH, which the instruction does not give at all. Set
#   equal to the height - a third of the radius - which sits inside the
#   18 to 25 degrees of arc the template's own bases subtend. Base and
#   radius scale together, so the half-angle it subtends is a CONSTANT,
#   asin(1/6), and the triangles hold their shape at every radius.
_ISOLATE_TOOTH_START_DEG = 30.0
_ISOLATE_TOOTH_END_MARGIN_DEG = 30.0
_ISOLATE_TOOTH_STEP_DEG = 45.0
_ISOLATE_TOOTH_HEIGHT_RATIO = 1.0 / 3.0
_ISOLATE_TOOTH_BASE_RATIO = 1.0 / 3.0


def _polar_point(centre, radius, angle_rad):

    """A point at `radius` and `angle_rad` from `centre`."""

    return QgsPointXY(
        centre.x() + radius * math.cos(angle_rad),
        centre.y() + radius * math.sin(angle_rad),
    )


def _isolate_triangles(centre, radius, start_rad, sweep_rad):

    """
    Isolate's inward triangles, each a THREE-point open run - corner,
    apex, corner.

    **The base is not drawn**: the arc the triangle stands on is its
    base, which is why this returns an open polyline rather than a ring.
    """

    direction = 1.0 if sweep_rad >= 0 else -1.0

    span = (
        abs(math.degrees(sweep_rad))
        - _ISOLATE_TOOTH_START_DEG
        - _ISOLATE_TOOTH_END_MARGIN_DEG
    )

    if span < 0:
        return []

    count = int(round(span / _ISOLATE_TOOTH_STEP_DEG))

    half_base = math.asin(_ISOLATE_TOOTH_BASE_RATIO / 2.0)

    apex_radius = radius * (1.0 - _ISOLATE_TOOTH_HEIGHT_RATIO)

    triangles = []

    for i in range(count + 1):

        middle = start_rad + direction * math.radians(
            _ISOLATE_TOOTH_START_DEG + i * _ISOLATE_TOOTH_STEP_DEG
        )

        triangles.append(
            [
                _polar_point(centre, radius, middle - half_base),
                _polar_point(centre, apex_radius, middle),
                _polar_point(centre, radius, middle + half_base),
            ]
        )

    return triangles


@qgsfunction(
    'mct_isolate_teeth',
    group='Military Cartography Tools'
)
def mct_isolate_teeth(values, feature=None, parent=None):

    """
    Isolate's own inward-facing triangles (341500), standing on the
    perimeter of the arc mct_retain_arc() draws.

    Reads the same PT1/PT2 frame Retain and Secure read, so the
    triangles can never drift off the arc they stand on.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _retain_frame(values[0])

    if frame is None:
        return values[0]

    centre, radius, start, sweep = frame

    triangles = _isolate_triangles(centre, radius, start, sweep)

    if not triangles:
        return QgsGeometry()

    return QgsGeometry.fromMultiPolylineXY(triangles)





# --- Clear (Table H-XXIV, 340500) ---
#
# **Penetrate's construction with two more arrows on it**, at the
# maintainer's own instruction: "start with penetrate of mission task,
# same construction, just add another two arrows of same lengths,
# distance from the middle arrow - 3/4 of the length between the
# midpoint of base shaft to the end; on both sides".
#
# So the base line, the middle arrow, its letter gap and its head are
# all Block's own calls, unchanged. Only the outer pair is new.
#
# That 3/4 is the standard's own proportion too - "the spacing between
# the symbol's arrows will stay proportional to the symbol's height",
# and its template puts the outer arrows about 0.73 of the way from the
# midpoint to each end of the vertical line. It is a fraction of the
# HALF base, so the outer arrows sit at three eighths of the whole base
# either side of the middle one, and they scale with the symbol rather
# than with the page.
_CLEAR_SIDE_ARROW_HALF_BASE_FRACTION = 0.75


@qgsfunction(
    'mct_clear_side_stems',
    group='Military Cartography Tools'
)
def mct_clear_side_stems(values, feature=None, parent=None):

    """
    Clear's own OUTER two arrows (340500) - the middle one is Block's
    stem and is drawn by mct_block_geometry().

    Each runs TIP TO FOOT, so an arrowhead on a last-vertex placement
    lands on the base line and points into it, the way Penetrate's
    does. Two parts, so one head each and no more.

    Empty when PT3 sits on the base line - there is no direction for
    the arrows then, the same case mct_block_stem_foot() declines.
    """

    if len(values) < 1:
        return QgsGeometry()

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return QgsGeometry()

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return QgsGeometry()

    pt1, pt2, pt3 = (QgsPointXY(vertices[index]) for index in range(3))

    projection = _perpendicular_projection(pt1, pt2, pt3)

    if projection is None or projection[2] == 0:
        return QgsGeometry()

    (ux, uy), (nx, ny), length = projection

    half_base = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y()) / 2.0

    if half_base == 0:
        return QgsGeometry()

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
    )

    offset = _CLEAR_SIDE_ARROW_HALF_BASE_FRACTION * half_base

    stems = []

    for side in (1.0, -1.0):

        foot = QgsPointXY(
            midpoint.x() + side * offset * ux,
            midpoint.y() + side * offset * uy,
        )

        stems.append(
            [
                QgsPointXY(
                    foot.x() + length * nx, foot.y() + length * ny
                ),
                foot,
            ]
        )

    return QgsGeometry.fromMultiPolylineXY(stems)


# --- Breach (340200) and Canalize (340400), Table H-XXIV ---
#
# Both are Bypass's own construction with the ARROWHEADS REPLACED by a
# slanting line across each arm's tip, at the maintainer's own
# instruction: Breach is "same as bypass, replace the arrowheads with
# slanting lines at the edges, converging out"; Canalize is "same as
# breach, replace B with C, and reverse the orientation slanting lines,
# converging in".
#
# **Which way a tick leans has to come from the geometry, not from
# which arm it is.** A marker rotated onto each arm's last vertex takes
# ONE angle, and the two ticks are mirror images of each other - so a
# fixed angle per part would flip the whole symbol between Breach's
# look and Canalize's the moment a user clicked PT1 and PT2 the other
# way round. These are real line geometry instead, with each tick's
# outward direction taken from that tip's own side of the opening.
#
# **The tilt is 30 degrees off the perpendicular** - 60 degrees to the
# arm. Fitted to the standard's own template and example on printed
# pages 645-646: four ticks, principal axes at 66, 62, 59 and 53
# degrees to their arm, which is a hand-drawn spread with 60 through
# the middle of it.
_BYPASS_TICK_TILT_DEG = 30.0

# How long each tick is, as a fraction of the arm it crosses - the same
# quarter the Bypass arrowhead it replaces uses, so the three symbols
# keep drawing at the same size. Capped in PAGE millimetres by the
# caller, for the same reason that head is.
_BYPASS_TICK_ARM_FRACTION = 0.25


@qgsfunction(
    'mct_bypass_ticks',
    group='Military Cartography Tools'
)
def mct_bypass_ticks(values, feature=None, parent=None):

    """
    The slanting lines that stand in for Bypass's arrowheads on Breach
    (340200) and Canalize (340400) - one across each arm's own tip,
    centred on it.

    `converging_out` true leans each tick's OUTER end back toward the
    rear, so the pair closes as it goes outward: Breach. False mirrors
    them: Canalize. `max_mm` and `map_scale` cap the length on the
    page, the way the arrowhead they replace is capped.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return geometry

    vertices = geometry.asPolyline()

    if len(vertices) < 3:
        return geometry

    pt1, pt2, pt3 = (QgsPointXY(v) for v in vertices[:3])

    _rear_top, _rear_bottom, arrow_top, arrow_bottom, depth = (
        _obstacle_bypass_frame(pt1, pt2, pt3)
    )

    opening = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    if depth == 0 or opening == 0:
        return QgsGeometry()

    converging_out = True if len(values) < 2 else bool(values[1])

    # Along the arms, rear to tip - the same for both, since the two
    # arms are parallel by construction.
    ux = (arrow_top[1].x() - arrow_top[0].x()) / depth
    uy = (arrow_top[1].y() - arrow_top[0].y()) / depth

    length = _BYPASS_TICK_ARM_FRACTION * depth

    cap = _page_gap_in_map_units(values, 2, pt1)

    if cap > 0:
        length = min(length, cap)

    lean = math.sin(math.radians(_BYPASS_TICK_TILT_DEG))
    across = math.cos(math.radians(_BYPASS_TICK_TILT_DEG))

    if not converging_out:
        lean = -lean

    ticks = []

    for tip, other in ((pt1, pt2), (pt2, pt1)):

        # Outward across the opening - away from the other tip, so it
        # follows the points the user actually clicked rather than
        # which arm this is.
        sx = (tip.x() - other.x()) / opening
        sy = (tip.y() - other.y()) / opening

        dx = across * sx - lean * ux
        dy = across * sy - lean * uy

        ticks.append(
            [
                QgsPointXY(
                    tip.x() - length / 2.0 * dx, tip.y() - length / 2.0 * dy
                ),
                QgsPointXY(
                    tip.x() + length / 2.0 * dx, tip.y() + length / 2.0 * dy
                ),
            ]
        )

    return QgsGeometry.fromMultiPolylineXY(ticks)


# --- Delay (Table H-XXIV, 340800) ---
#
# The maintainer's own construction: "user clicks pt1, pt2 and pt3.
# arrowhead at pt1, shaft from pt1 to pt2, then join pt2 and pt3 with a
# semicircle, pt2 to pt3 being the diameter; letter D masked, on the
# shaft between pt1 and pt2".
#
# **The arc is FORCED PERPENDICULAR to the shaft**, which is the
# standard's own draw rule - "The 180 degree circular arc is always
# perpendicular to the line" - and the maintainer's decision on
# 2026-08-16 after it was raised. Built first taking PT2-PT3 as the
# diameter exactly as clicked, which is what their construction said
# and what a square click gives either way.
#
# So PT3 sets the diameter's LENGTH and its SIDE, not its direction:
# the diameter is the PERPENDICULAR distance from PT3 to the infinite
# line through PT1-PT2. That is the same projection mct_block_geometry,
# mct_contain_arc and mct_trip_wire_geometry all use for a third point
# that sets a depth, so a third point behaves the same way everywhere
# in this module.
#
# The one thing PT3 cannot settle at all is which way the semicircle
# bulges: a diameter admits two. It bulges AWAY FROM PT1, which is what
# the template draws and the only reading that keeps the arc clear of
# the shaft.


def _delay_frame(values):

    """
    (pt1, pt2, pt3) for Delay, or None when the geometry cannot carry
    one - fewer than three vertices, or a zero-length shaft.
    """

    points = _three_anchor_points(values)

    if points is None:
        return None

    pt1, pt2, pt3 = points

    if math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y()) == 0:
        return None

    return pt1, pt2, pt3


def _delay_semicircle(pt1, pt2, pt3):

    """
    The 180-degree arc leaving PT2 square to the shaft, bulging away
    from PT1, its diameter PT3's own perpendicular distance from the
    shaft's own infinite line.

    Empty when PT3 sits ON that line - there is no side to be on then,
    and a guessed one would put an arc somewhere the user never
    pointed.
    """

    span = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    if span == 0:
        return []

    ux, uy = (pt2.x() - pt1.x()) / span, (pt2.y() - pt1.y()) / span

    to_pt3_x, to_pt3_y = pt3.x() - pt2.x(), pt3.y() - pt2.y()

    along = to_pt3_x * ux + to_pt3_y * uy

    perp_x = to_pt3_x - along * ux
    perp_y = to_pt3_y - along * uy

    diameter = math.hypot(perp_x, perp_y)

    if diameter == 0:
        return []

    centre = QgsPointXY(
        pt2.x() + perp_x / 2.0, pt2.y() + perp_y / 2.0
    )

    radius = diameter / 2.0

    start = math.atan2(pt2.y() - centre.y(), pt2.x() - centre.x())

    # The two ways a semicircle can sit on one diameter, a quarter turn
    # either side of PT2. Take whichever crown lands further from PT1.
    crowns = [
        (sweep, _polar_point(centre, radius, start + sweep / 2.0))
        for sweep in (math.pi, -math.pi)
    ]

    sweep = max(
        crowns,
        key=lambda crown: math.hypot(
            crown[1].x() - pt1.x(), crown[1].y() - pt1.y()
        )
    )[0]

    return _arc_points(
        centre, radius, start, sweep, _ARC_SEGMENTS_PER_SEMICIRCLE
    )


@qgsfunction(
    'mct_delay_geometry',
    group='Military Cartography Tools'
)
def mct_delay_geometry(values, feature=None, parent=None):

    """
    Delay's whole run (340800) - the shaft from PT1 to PT2 and the
    semicircle carrying on from PT2 round to PT3's own perpendicular
    reflection across the shaft. Shared with Retire, Withdraw and
    Withdraw Under Pressure, which differ only in their letter.

    Optional `gap` (page millimetres) and `map_scale` cut a break in the
    SHAFT for the "D", the same way every other letter on this layer is
    set into its own geometry rather than masked.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _delay_frame(values)

    if frame is None:
        return values[0]

    pt1, pt2, pt3 = frame

    arc = _delay_semicircle(pt1, pt2, pt3)

    midpoint = QgsPointXY(
        (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
    )

    gap_units = _page_gap_in_map_units(values, 1, midpoint)

    shaft = math.hypot(pt2.x() - pt1.x(), pt2.y() - pt1.y())

    # The arc carries on from PT2 without a break, so it belongs to the
    # same part as the shaft's second half - one continuous run.
    tail = [pt2] + arc[1:] if arc else [pt2]

    if gap_units <= 0 or 2.0 * gap_units >= shaft:
        return QgsGeometry.fromPolylineXY([pt1] + tail)

    ux = (pt2.x() - pt1.x()) / shaft
    uy = (pt2.y() - pt1.y()) / shaft

    half = gap_units / 2.0

    before = QgsPointXY(
        midpoint.x() - half * ux, midpoint.y() - half * uy
    )

    after = QgsPointXY(
        midpoint.x() + half * ux, midpoint.y() + half * uy
    )

    return QgsGeometry.fromMultiPolylineXY(
        [[pt1, before], [after] + tail]
    )


@qgsfunction(
    'mct_delay_shaft',
    group='Military Cartography Tools'
)
def mct_delay_shaft(values, feature=None, parent=None):

    """
    Delay's shaft alone, run BACKWARDS - PT2 to PT1 - so an arrowhead
    on its last vertex sits at PT1 and points out of the symbol.

    It cannot ride on mct_delay_geometry(): that is two parts once the
    "D" gap is cut into it, and a marker on the last vertex would land
    on the end of each, dropping a second arrowhead at PT3.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _delay_frame(values)

    if frame is None:
        return values[0]

    pt1, pt2, _pt3 = frame

    return QgsGeometry.fromPolylineXY([pt2, pt1])


@qgsfunction(
    'mct_delay_letter_point',
    group='Military Cartography Tools'
)
def mct_delay_letter_point(values, feature=None, parent=None):

    """
    The anchor for Delay's own "D" - the middle of the shaft, which is
    the middle of the gap mct_delay_geometry() cuts for it.
    """

    if len(values) < 1:
        return "Need a geometry (e.g. $geometry)"

    frame = _delay_frame(values)

    if frame is None:
        return values[0]

    pt1, pt2, _pt3 = frame

    return QgsGeometry.fromPointXY(
        QgsPointXY(
            (pt1.x() + pt2.x()) / 2.0, (pt1.y() + pt2.y()) / 2.0
        )
    )


# --- Weapon/Sensor Range Fan (Table H-XVIII, 242100 and 242200) ---
#
# **Two codes, one construction** - Circular (242100) is the Sector
# (242200) case with the default angles, which is the maintainer's own
# reading and the reason this is built once rather than twice.
#
# Angles are COMPASS BEARINGS: degrees clockwise from north, because
# "the centerline is always north". A sweep of 0 (or 360, or left equal
# to right) means the whole circle.
_RANGE_FAN_FULL_CIRCLE_SEGMENTS = 144

_RANGE_FAN_MIN_SEGMENTS = 12


# Minimum Safe Distance Zone: where its rings break for their labels,
# and how far that break is allowed to open. Due east is the standard's
# own placement - every number in Table H-XXI's example sits level with
# the centre, to its right. The cap keeps a ring whose label is wider
# than the ring itself from inverting.
_SAFE_DISTANCE_LABEL_BEARING_DEG = 90.0
_SAFE_DISTANCE_MAX_HALF_GAP_DEG = 60.0


def _range_fan_arc_points(centre, radius_m, start_deg, sweep_deg):

    """
    Points along one ring's arc, projected GEODESICALLY.

    The range is a real ground distance - unlike every glyph in this
    appendix, which is millimetres on the page - so the ring cannot be
    a circle of constant coordinate radius: at any distance from the
    equator that draws an ellipse, and the further from it the worse.
    QgsDistanceArea.computeSpheroidProject() walks the ellipsoid
    surface instead, the same machinery core/coordinate_utils.py's own
    bearing/range tool uses.
    """

    distance_area = _distance_area()

    segments = max(
        _RANGE_FAN_MIN_SEGMENTS,
        int(round(_RANGE_FAN_FULL_CIRCLE_SEGMENTS * abs(sweep_deg) / 360.0))
    )

    points = []

    for step in range(segments + 1):

        bearing = start_deg + sweep_deg * step / segments

        points.append(
            distance_area.computeSpheroidProject(
                centre, radius_m, math.radians(bearing)
            )
        )

    return points


@qgsfunction(
    'mct_text_width_mm',
    group='Military Cartography Tools'
)
def mct_text_width_mm(values, feature=None, parent=None):

    """
    How wide `text` renders at `font_size_mm`, in millimetres - measured
    with the same Qt font machinery that will draw it rather than
    estimated. Use as mct_text_width_mm('1500M', 3.175).

    Exposed as an expression function for Table H-XXI's own Minimum
    Safe Distance Zone, whose rings have to break by exactly the width
    of the label sitting in the break. The measurement itself is the
    same one supply-route glyph sizing already used privately.
    """

    if len(values) < 2:
        return "Need a text and a font size in millimetres"

    text = str(values[0]) if values[0] is not None else ""

    try:
        font_size_mm = float(values[1])
    except (TypeError, ValueError):
        return 0.0

    if not text or font_size_mm <= 0:
        return 0.0

    return _text_width_mm(text, font_size_mm)


@qgsfunction(
    'mct_safe_distance_ring',
    group='Military Cartography Tools'
)
def mct_safe_distance_ring(values, feature=None, parent=None):

    """
    One ring of a Minimum Safe Distance Zone: a full circle of
    `range_metres` around a centre point, BROKEN on its right-hand side
    by a gap `gap_mm` wide on the page. Use as
    mct_safe_distance_ring($geometry, "range1", <gap in mm>, @map_scale).

    The break is not decoration: Table H-XXI's own example draws each
    circle stopping either side of the number that labels it, due east
    of the centre and horizontal. Cutting it into the geometry is also
    the only way to get it - QGIS's Selective Masking cannot reach a
    symbol layer nested inside a geometry generator, and a generated
    ring has nowhere else to live.

    **The gap is given in page millimetres and converted here**, which
    is what makes it exactly as wide as the text however far the map is
    zoomed. @map_scale DOES resolve inside a geometry generator -
    verified by probe on 2026-08-15, correcting a note this project had
    carried since 2026-08-11 (see mct_range_fan_ring's own neighbours);
    the earlier finding came from an offscreen harness that never
    populated the map-settings scope at all, so every variable read
    NULL there, not just this one.

    Returns an empty geometry for a ring with no range, which is how a
    symbol carrying five ring layers draws only the ones filled in.
    """

    if len(values) < 4:
        return QgsGeometry()

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return QgsGeometry()

    try:
        radius = float(values[1])
    except (TypeError, ValueError):
        return QgsGeometry()

    if radius <= 0:
        return QgsGeometry()

    centre = geometry.asPoint()

    try:
        gap_mm = float(values[2])
    except (TypeError, ValueError):
        gap_mm = 0.0

    try:
        map_scale = float(values[3])
    except (TypeError, ValueError):
        map_scale = 0.0

    gap_metres = max(gap_mm, 0.0) / 1000.0 * max(map_scale, 0.0)

    # Half the gap as an angle at the centre. Clamped well short of a
    # quarter turn: a ring small enough on the page for its own label to
    # span it would otherwise open into an arc shorter than the gap, or
    # invert outright.
    half_gap_deg = min(
        math.degrees(gap_metres / 2.0 / radius) if radius else 0.0,
        _SAFE_DISTANCE_MAX_HALF_GAP_DEG
    )

    # Due east, where the standard puts the numbers.
    start = _SAFE_DISTANCE_LABEL_BEARING_DEG + half_gap_deg

    sweep = 360.0 - 2.0 * half_gap_deg

    return QgsGeometry.fromPolylineXY(
        _range_fan_arc_points(centre, radius, start, sweep)
    )


def _range_fan_frame(values):

    """(centre, left, right, radius) for one ring, or None."""

    if len(values) < 4:
        return None

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return None

    try:
        centre = geometry.asPoint()
    except (TypeError, ValueError):
        return None

    try:
        left = float(values[1]) if values[1] is not None else 0.0
        right = float(values[2]) if values[2] is not None else 360.0
        radius = float(values[3]) if values[3] is not None else 0.0
    except (TypeError, ValueError):
        return None

    if radius <= 0:
        return None

    return centre, left, right, radius


@qgsfunction(
    'mct_range_fan_ring',
    group='Military Cartography Tools'
)
def mct_range_fan_ring(values, feature=None, parent=None):

    """
    One ring of a Weapon/Sensor Range Fan: `mct_range_fan_ring(
    $geometry, left_deg, right_deg, range_metres)`.

    A full CIRCLE when the two angles describe the whole turn (the
    0/360 default), and otherwise an ANNULUS SEGMENT: the arc from the
    left angle clockwise to the right one, with a straight side at each
    end running back only as far as `inner_range_metres` - the previous
    ring's own range.

    **The sides are restricted to the annulus, always.** The first
    build ran every ring's sides all the way to the centre, so the
    outer rings drew straight through the inner ones - reported by the
    maintainer against the standard's own picture, where each ring's
    sides span only its own band. Only ring 1 reaches the vertex, and
    only because its inner range is 0.

    **A ring with an inner range is CLOSED - its inner arc is drawn
    too.** Where two rings share their angles that arc lands exactly on
    the inner ring's own outer arc and is invisible; where they differ,
    it is the only thing closing the band. Without it a ring wider than
    the one inside it hangs open at the corners, which is what the
    maintainer reported: "the inner ring should also be drawn otherwise
    there is a gap".

    Returns an empty geometry for a ring with no range, which is how a
    symbol carrying five ring layers draws only the ones filled in.
    """

    frame = _range_fan_frame(values)

    if frame is None:
        return QgsGeometry()

    centre, left, right, radius = frame

    try:
        inner = float(values[4]) if len(values) > 4 and values[4] else 0.0
    except (TypeError, ValueError):
        inner = 0.0

    if not 0.0 < inner < radius:
        inner = 0.0

    sweep = (right - left) % 360.0

    # Left equal to right, or a full turn, means the whole circle -
    # not a zero-width sector. The 0/360 default lands here, and a
    # circle has no sides to restrict.
    if sweep == 0:

        return QgsGeometry.fromPolylineXY(
            _range_fan_arc_points(centre, radius, 0.0, 360.0)
        )

    outer = _range_fan_arc_points(centre, radius, left, sweep)

    if inner == 0.0:

        return QgsGeometry.fromPolylineXY([centre] + outer + [centre])

    # Closed: out along the left side, round the outer arc, back down
    # the right side, and home along the inner arc.
    inner_arc = _range_fan_arc_points(centre, inner, right, -sweep)

    return QgsGeometry.fromPolylineXY(outer + inner_arc + [outer[0]])


@qgsfunction(
    'mct_range_fan_axis',
    group='Military Cartography Tools'
)
def mct_range_fan_axis(values, feature=None, parent=None):

    """
    The fan's own north axis: `mct_range_fan_axis($geometry,
    length_metres)`.

    A line due north from the centre, running slightly beyond the
    outermost ring so its arrowhead sits clear of the arc - the
    maintainer's own addition after the first build, matching the
    standard's own picture, which draws exactly this axis through every
    ring. The caller sets the length; see RANGE_FAN_AXIS_OVERSHOOT_M.
    """

    if len(values) < 2:
        return QgsGeometry()

    geometry = values[0]

    if geometry is None or geometry.isEmpty():
        return QgsGeometry()

    try:
        centre = geometry.asPoint()
        length = float(values[1]) if values[1] else 0.0
    except (TypeError, ValueError):
        return QgsGeometry()

    if length <= 0:
        return QgsGeometry()

    return QgsGeometry.fromPolylineXY(
        [
            centre,
            _distance_area().computeSpheroidProject(centre, length, 0.0),
        ]
    )


@qgsfunction(
    'mct_range_fan_label_point',
    group='Military Cartography Tools'
)
def mct_range_fan_label_point(values, feature=None, parent=None):

    """
    Where one ring's own "RG/ALT" label sits: `mct_range_fan_label_point(
    $geometry, left_deg, right_deg, range_metres, inner_range_metres)`.

    Inside the ring and outside the one before it - half way between
    the two radii - and on the sector's own CENTRELINE, so a narrow fan
    labels down its middle rather than off its edge. For the full-circle
    case that centreline is north, which is where the standard's own
    example puts its ring numbers.
    """

    frame = _range_fan_frame(values)

    if frame is None:
        return QgsGeometry()

    centre, left, right, radius = frame

    try:
        inner = float(values[4]) if len(values) > 4 and values[4] else 0.0
    except (TypeError, ValueError):
        inner = 0.0

    if inner >= radius:
        inner = 0.0

    sweep = (right - left) % 360.0

    bearing = 0.0 if sweep == 0 else left + sweep / 2.0

    return QgsGeometry.fromPointXY(
        _distance_area().computeSpheroidProject(
            centre, (inner + radius) / 2.0, math.radians(bearing)
        )
    )


@qgsfunction(
    'mct_supply_route_arrow_svg',
    group='Military Cartography Tools'
)
def mct_supply_route_arrow_svg(values, feature=None, parent=None):

    """
    One traffic arrow for Table H-XXIII's own supply routes (330301-
    330303, 330401-330403), as an inline "base64:<...>" SVG.

    `mode` picks which of the table's three variants this is:

    - "forward"     - one arrow along the direction of travel (One Way)
    - "backward"    - one arrow against it (the second of Two Way's pair)
    - "alternating" - a head at BOTH ends with "ALT" set into the gap
                      between them, which is how the standard draws
                      Alternating Traffic: a literal "<- ALT ->".

    **The heads are FILLED**, unlike every arrowhead this project has
    drawn so far. That is not an inconsistency: the open heads on
    Contain and Retain were open because the solid triangles on those
    pages turned out to be annotation pointers to the "PT. 1" labels
    rather than symbol geometry. Here the arrows ARE the symbol - they
    appear in the EXAMPLE column, filled, on a route that has no
    anchor-point callouts at all.

    Sized in MILLIMETRES on the page, like Navigational's own flanks and
    for the same reason - the route's length is the user's, the arrow's
    is the standard's. The viewBox is symmetric about the origin so the
    glyph centres on whatever point the marker line puts it at, and one
    viewBox unit is one millimetre (QGIS sizes an SVG marker by its
    WIDTH, so the caller sets the marker size to `length_mm`).
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"
    length = float(values[1]) if len(values) > 1 and values[1] else 12.0
    stroke = float(values[2]) if len(values) > 2 and values[2] else 0.4
    mode = str(values[3]) if len(values) > 3 and values[3] else "forward"
    text = str(values[4]) if len(values) > 4 and values[4] else "ALT"

    # Explicit rather than a fraction of the glyph, which is the whole
    # point: the text is the same size whatever the assembly's length,
    # so lengthening the glyph buys shaft rather than bigger letters.
    # Deriving it from the length instead made the first Alternating
    # render two heads pressed against the word with no shaft at all,
    # and lengthening the glyph changed nothing.
    text_height = (
        float(values[5]) if len(values) > 5 and values[5]
        else length / 3.6
    )

    if length <= 0:
        return ""

    half = length / 2.0

    # Proportions of the arrow itself. Nothing in the standard gives
    # these - it draws the arrow and never dimensions it - so they are
    # fractions of the arrow's own length, which keeps the head in
    # proportion if the length is ever retuned.
    head_length = length / 6.0
    head_half_width = length / 13.0

    parts = []

    def head(tip_x, direction):

        base = tip_x - direction * head_length

        return (
            '<path d="M {tip:.4f},0 L {base:.4f},{up:.4f} '
            'L {base:.4f},{down:.4f} Z" fill="{colour}" '
            'stroke="{colour}" stroke-width="{stroke:.4f}"/>'
        ).format(
            tip=tip_x, base=base,
            up=-head_half_width, down=head_half_width,
            colour=colour, stroke=stroke,
        )

    if mode == "alternating":

        gap = _text_width_mm(text, text_height) / 2.0 + text_height * 0.3

        parts.append(
            '<path d="M {left:.4f},0 L {gap_left:.4f},0 M {gap_right:.4f},0 '
            'L {right:.4f},0" fill="none" stroke="{colour}" '
            'stroke-width="{stroke:.4f}"/>'.format(
                left=-half, right=half,
                gap_left=-gap, gap_right=gap,
                colour=colour, stroke=stroke,
            )
        )

        parts.append(head(-half, -1))
        parts.append(head(half, 1))

        # Qt's SVG renderer ignores dominant-baseline (established in
        # symbol_engine.py), so the baseline is placed explicitly: half
        # the cap height below the centre line puts the text visually
        # centred on it.
        parts.append(
            '<text x="0" y="{y:.4f}" text-anchor="middle" '
            'font-family="Arial" font-weight="bold" '
            'font-size="{size:.4f}" fill="{colour}" '
            'stroke="none">{text}</text>'.format(
                y=text_height * 0.36, size=text_height,
                colour=colour, text=text,
            )
        )

    else:

        direction = -1 if mode == "backward" else 1

        parts.append(
            '<path d="M {tail:.4f},0 L {tip:.4f},0" fill="none" '
            'stroke="{colour}" stroke-width="{stroke:.4f}"/>'.format(
                tail=-direction * half, tip=direction * half,
                colour=colour, stroke=stroke,
            )
        )

        parts.append(head(direction * half, direction))

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="{minx:.4f} {minx:.4f} {size:.4f} {size:.4f}"'
        ' width="{size:.4f}" height="{size:.4f}">{body}</svg>'
    ).format(minx=-half, size=length, body="".join(parts))

    return "base64:" + base64.b64encode(svg.encode("utf-8")).decode("ascii")


# Table H-XXIII's own two convoys. The body is a bar of fixed page
# height with an end piece at PT1; these are the end pieces, in a
# coordinate system where the BODY is _CONVOY_SVG_BODY units tall and
# the drawing runs left (towards the rear) to right (towards PT1).
_CONVOY_SVG_BODY = 100.0
_CONVOY_SVG_STROKE = 10.0

# How far the arrowhead flares beyond the body, each side. The standard
# draws the head clearly wider than the bar it grows out of but gives
# no number for it - as it gives none for the bar's own height either.
_CONVOY_SVG_HEAD_FLARE = 40.0


def _convoy_moving_head_svg(length_units):

    """
    Moving Convoy's own end piece: an OPEN arrowhead flaring out of the
    body and closing at the tip, drawn as strokes rather than a filled
    triangle - the template's arrow is an outline throughout. The short
    vertical step at each side is what joins the head to the bar, so
    the outline runs body edge, out to the flare, down to the tip and
    back, continuously.

    **Drawn MIRRORED - tip at x=0, the join at x=length.** A marker
    rotated onto a line's LAST vertex has its own +x running BACK
    along the line, not forward. Established by render, not assumed.
    """

    body_half = _CONVOY_SVG_BODY / 2.0

    half = body_half + _CONVOY_SVG_HEAD_FLARE

    height = 2.0 * half + _CONVOY_SVG_STROKE

    path = (
        "M %.1f,%.1f L %.1f,%.1f L 0,0 L %.1f,%.1f L %.1f,%.1f"
        % (length_units, -body_half, length_units, -half,
           length_units, half, length_units, body_half)
    )

    return _convoy_svg(length_units, height, half, path, closed=False)


def _convoy_halted_head_svg(length_units):

    """
    Halted Convoy's own end piece: the same triangle REVERSED - its
    apex points back into the body and its base stands at PT1. That
    reversal is the only thing separating a halted convoy from a moving
    one, and it is drawn open, like the body.

    Two parts, because a halted convoy's box is CLOSED where a moving
    one's opens into its head: the bar closing the body, and the
    triangle standing outside it. Mirrored for the same reason as the
    moving head.
    """

    body_half = _CONVOY_SVG_BODY / 2.0

    half = body_half + _CONVOY_SVG_HEAD_FLARE

    height = 2.0 * half + _CONVOY_SVG_STROKE

    bar = (
        "M %.1f,%.1f L %.1f,%.1f"
        % (length_units, -body_half, length_units, body_half)
    )

    triangle = (
        "M 0,%.1f L %.1f,0 L 0,%.1f Z" % (-half, length_units, half)
    )

    return _convoy_svg(length_units, height, half, bar, closed=False,
                       extra_path=triangle)


def _convoy_svg(width, height, half, path, closed=False, extra_path=None):

    """The shared wrapper every convoy end piece is drawn into."""

    top = -half - _CONVOY_SVG_STROKE / 2.0

    parts = [path] if extra_path is None else [path, extra_path]

    body = "".join(
        '<path d="%s" fill="none" stroke="black" stroke-width="%.1f"'
        ' stroke-linejoin="miter" />' % (part, _CONVOY_SVG_STROKE)
        for part in parts
    )

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%.1f"'
        ' height="%.1f" viewBox="0 %.1f %.1f %.1f">%s</svg>'
        % (width, height, top, width, height, body)
    )

def _convoy_rear_svg():

    """
    The bar closing the body at PT2 - one stroke the body's own height,
    square across the line.
    """

    half = _CONVOY_SVG_BODY / 2.0

    width = _CONVOY_SVG_STROKE

    height = _CONVOY_SVG_BODY + _CONVOY_SVG_STROKE

    return (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        f' width="{width:.1f}" height="{height:.1f}"'
        f' viewBox="{-width / 2.0:.1f} {-half - _CONVOY_SVG_STROKE / 2.0:.1f}'
        f' {width:.1f} {height:.1f}">'
        f'<path d="M 0,{-half:.1f} L 0,{half:.1f}" fill="none"'
        f' stroke="black" stroke-width="{_CONVOY_SVG_STROKE:.1f}" /></svg>'
    )


@qgsfunction(
    'mct_convoy_end_svg',
    group='Military Cartography Tools'
)
def mct_convoy_end_svg(values, feature=None, parent=None):

    """
    One end piece of a convoy symbol (Table H-XXIII, 330100/330200), as
    an inline "base64:<...>" SVG. Use as
    mct_convoy_end_svg('moving', <length as a multiple of the body
    height>, '<colour>').

    `mode` is "moving" (an open arrowhead pointing forward), "halted"
    (the same triangle reversed, apex back into the body) or "rear"
    (the bar closing the body at PT2).

    The colour comes in as a STRING, not a QGIS colour: color_rgb()
    yields a bare "0,0,255", which a QGIS colour property accepts and
    an SVG silently ignores - a trap this project has hit before.
    """

    if not values:
        return ""

    mode = str(values[0])

    try:
        length = float(values[1]) if len(values) > 1 else 1.0
    except (TypeError, ValueError):
        length = 1.0

    colour = str(values[2]) if len(values) > 2 and values[2] else "black"

    length_units = max(length, 0.1) * _CONVOY_SVG_BODY

    if mode == "moving":
        svg = _convoy_moving_head_svg(length_units)
    elif mode == "halted":
        svg = _convoy_halted_head_svg(length_units)
    else:
        svg = _convoy_rear_svg()

    svg = svg.replace('stroke="black"', f'stroke="{colour}"')

    return "base64:" + base64.b64encode(svg.encode("utf-8")).decode("ascii")


def _text_width_mm(text, font_size_mm):

    """
    How wide `text` renders at `font_size_mm`, measured with the same Qt
    font machinery that will draw it rather than estimated - the same
    approach symbol_engine.py uses to fit injected amplifier text.
    """

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)
        font.setBold(True)

        return (
            QFontMetricsF(font).horizontalAdvance(text)
            / 1000.0
            * font_size_mm
        )

    except Exception:

        # Arial bold averages a shade over 0.6 em per upper-case
        # character; only reached if Qt fonts are unavailable.
        return len(text) * font_size_mm * 0.62


@qgsfunction(
    'mct_navigational_flank_svg',
    group='Military Cartography Tools'
)
def mct_navigational_flank_svg(values, feature=None, parent=None):

    """
    One of Navigational's own two corner flanks (Table H-XIV, 218400),
    as an inline "base64:<...>" SVG for a marker.

    **A glyph rather than generated geometry, because the length is in
    MILLIMETRES.** The standard's own draw rules say the symbol "varies
    only in length" - the two clicked points set the middle run, and the
    flanks are a fixed size on the page whatever the map scale. Nothing
    inside a geometry generator can express that: `@map_scale` does not
    resolve there (probed, twice), so anything in page units has to be a
    mm-sized symbol layer or a marker glyph. Same reasoning as Fortified
    Line's own rampart tile.

    `angle_deg` is measured COUNTER-CLOCKWISE from the direction of
    travel, PT1 toward PT2 - 40 at the first vertex and 220 at the last,
    per the maintainer's own dictated construction, which is 180 apart
    and so draws the anti-parallel pair the template shows.

    The viewBox is square and symmetric about the origin so the glyph
    centres on the vertex the marker line puts it at, with the segment
    radiating from that centre. One viewBox unit is one millimetre, and
    QGIS sizes an SVG marker by its WIDTH - so the caller sets the
    marker size to TWICE `length_mm`, not to `length_mm`.
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"
    length = float(values[1]) if len(values) > 1 and values[1] else 6.0
    angle = float(values[2]) if len(values) > 2 and values[2] is not None else 40.0
    stroke = float(values[3]) if len(values) > 3 and values[3] else 0.4

    if length <= 0:
        return ""

    radians = math.radians(angle)

    # SVG's own y axis points DOWN, so a counter-clockwise angle on the
    # map is a negative y here.
    end_x = length * math.cos(radians)
    end_y = -length * math.sin(radians)

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="{minx:.4f} {minx:.4f} {size:.4f} {size:.4f}"'
        ' width="{size:.4f}" height="{size:.4f}">'
        '<path d="M 0,0 L {end_x:.4f},{end_y:.4f}" fill="none"'
        ' stroke="{colour}" stroke-width="{stroke:.4f}"'
        ' stroke-linecap="butt"/></svg>'
    ).format(
        minx=-length, size=length * 2.0,
        end_x=end_x, end_y=end_y,
        colour=colour, stroke=stroke,
    )

    return "base64:" + base64.b64encode(svg.encode("utf-8")).decode("ascii")


@qgsfunction(
    'mct_rampart_connector_svg',
    group='Military Cartography Tools'
)
def mct_rampart_connector_svg(values, feature=None, parent=None):

    """
    A plain level segment of Fortified Line's own baseline (290900), as
    an inline "base64:<...>" SVG for a marker.

    Two jobs, both of which fall out of the rampart profile being TILED
    rather than generated - a marker line lays each tile down straight
    and rotated, so it cannot follow a bend inside a tile, and it has
    no idea where the whole line ends:

    - At an inner vertex it bridges the corner. The maintainer's own
      report: "in a multi-line or poly-line, at the corners, there is a
      slight break in pattern, at times a gap - maybe add a simple line
      segment to connect them?"
    - At the two ends it lengthens the level run the profile opens and
      closes with, which the tile alone can only make a quarter of a
      tile long without changing the merlon rhythm.

    The viewBox is symmetric about the origin so the glyph centres on
    whatever point the marker line puts it at, and one viewBox unit is
    one millimetre (QGIS sizes an SVG marker by its WIDTH, so the
    caller sets the marker size to `length_mm`).
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"
    length = float(values[1]) if len(values) > 1 and values[1] else 1.5
    stroke = float(values[2]) if len(values) > 2 and values[2] else 0.4

    if length <= 0:
        return ""

    half = length / 2.0

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="{minx:.4f} {minx:.4f} {size:.4f} {size:.4f}"'
        ' width="{size:.4f}" height="{size:.4f}">'
        '<path d="M {minx:.4f},0 L {half:.4f},0" fill="none"'
        ' stroke="{colour}" stroke-width="{stroke:.4f}"'
        ' stroke-linecap="butt"/></svg>'
    ).format(
        minx=-half, size=length, half=half,
        colour=colour, stroke=stroke,
    )

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


@qgsfunction(
    'mct_ford_zigzag_svg',
    group='Military Cartography Tools'
)
def mct_ford_zigzag_svg(values, feature=None, parent=None):

    """
    Ford Difficult's own zigzag (271600) - the single thing the
    standard varies between Ford Easy and Ford Difficult - as an inline
    "base64:<...>" SVG for a marker at the centreline's midpoint.

    A glyph rather than generated geometry for the same reason as
    Bridge or Gap's end wings: the whole crossing family is sized in
    MILLIMETRES so it does not grow with the feature's own length, and
    a geometry generator cannot see page units.

    The zigzag runs ACROSS the channel (along the marker's own y, which
    rotation then squares to the line) and overhangs it at both ends,
    which is what makes it read as crossing the ford rather than
    sitting inside it. Arguments: colour, length_mm, amplitude_mm,
    teeth, stroke_mm.

    The viewBox is symmetric about the origin so the glyph centres
    itself on the midpoint. QGIS sizes an SVG marker by its WIDTH, so
    the caller sets the marker size to `length_mm` and the viewBox is
    emitted `length_mm` wide - making one viewBox unit one millimetre.
    """

    colour = str(values[0]) if values and values[0] else "rgb(0,0,0)"
    length = float(values[1]) if len(values) > 1 else 9.0
    amplitude = float(values[2]) if len(values) > 2 else 1.1
    teeth = int(values[3]) if len(values) > 3 else 4
    stroke = float(values[4]) if len(values) > 4 else 0.4

    if length <= 0 or teeth < 1:
        return ""

    # Walk from one end of the crossing run to the other, alternating
    # side to side. y is the crossing direction, x the zigzag's own
    # swing.
    steps = teeth * 2

    points = []

    for index in range(steps + 1):

        y = -length / 2.0 + length * index / steps

        if index == 0 or index == steps:
            x = 0.0
        else:
            x = amplitude if index % 2 == 1 else -amplitude

        points.append("{:.4f},{:.4f}".format(x, y))

    path = "M " + " L ".join(points)

    body = (
        '<path d="{}" fill="none" stroke="{}" stroke-width="{:.4f}"'
        ' stroke-linecap="round" stroke-linejoin="round"/>'
    ).format(path, colour, stroke)

    # Width is the caller's own marker size; height is the crossing
    # run. Both halves of the viewBox are symmetric so the glyph sits
    # centred on the midpoint.
    half_width = max(amplitude, length / 2.0)

    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg"'
        ' viewBox="{minx:.4f} {miny:.4f} {width:.4f} {height:.4f}"'
        ' width="{width:.4f}" height="{height:.4f}">{body}</svg>'
    ).format(
        minx=-half_width, miny=-length / 2.0,
        width=2 * half_width, height=length, body=body
    )

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded


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
    mct_sidc_svg_width,
    mct_build_sidc,
    mct_area_km2,
    mct_perimeter_km,
    mct_length_km,
    mct_inscribed_centre,
    mct_inscribed_radius_mm,
    mct_block_letter_point,
    mct_disrupt_letter_point,
    mct_fix_letter_point,
    mct_block_stem_foot,
    mct_block_stem_mm,
    mct_mm_in_map_units,
    mct_radius_mm,
    mct_secure_letter_point,
    mct_isolate_teeth,
    mct_delay_geometry,
    mct_delay_shaft,
    mct_delay_letter_point,
    mct_convoy_end_svg,
    mct_safe_distance_ring,
    mct_text_width_mm,
    mct_crenellate_outline,
    mct_serrate_outline,
    mct_decoy_chevron,
    mct_decoy_chevron_svg,
    mct_scatter_points,
    mct_abatis_line,
    mct_mine_cluster_arc,
    mct_trip_wire_geometry,
    mct_block_geometry,
    mct_turn_arc,
    mct_disrupt_geometry,
    mct_disrupt_arrow_tips,
    mct_fix_geometry,
    mct_obstacle_bypass_arrows,
    mct_obstacle_bypass_arrow_length,
    mct_obstacle_bypass_rear_easy,
    mct_obstacle_bypass_rear_midpoint,
    mct_bypass_ticks,
    mct_clear_side_stems,
    mct_obstacle_bypass_rear_difficult,
    mct_obstacle_bypass_rear_impossible,
    mct_roadblock_main_line,
    mct_roadblock_parallel_line,
    mct_roadblock_complete_geometry,
    mct_bridge_or_gap_geometry,
    mct_bridge_flare_svg,
    mct_ford_zigzag_svg,
    mct_contain_arc,
    mct_contain_arrow_midpoint,
    mct_contain_teeth,
    mct_contain_arrow,
    mct_contain_arrow_head,
    mct_contain_letter_point,
    mct_retain_arc,
    mct_retain_arc_end,
    mct_retain_teeth,
    mct_retain_letter_point,
    mct_range_fan_ring,
    mct_range_fan_axis,
    mct_range_fan_label_point,
    mct_supply_route_arrow_svg,
    mct_navigational_flank_svg,
    mct_rampart_connector_svg,
    mct_rampart_svg,
    mct_overhead_wire_tower_svg,
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
