# -*- coding: utf-8 -*-

"""
Viewshed / dead-ground analysis - a full coverage sweep from one
observer point, out to a maximum range, rather than the one-target
check Line of Sight does. Wraps GDAL's own gdal_viewshed binary
(exposed by QGIS's Processing framework as gdal:viewshed) instead of
hand-writing a per-pixel radial sweep in Python - the same
"wrap the native GDAL tool" pattern already used for Tanaka Contours
(gdal:contour) and Hillshade Combinations (gdal:hillshade).

Military Cartography Tools
"""

import math

import processing

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsFillSymbol,
    QgsGeometry,
    QgsProcessing,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsVectorLayer,
)

from .line_of_sight import REFRACTION_COEFFICIENT, VISIBLE_COLOR
from ._dem_utils import clip_and_reproject_dem
from ..core.coordinate_utils import WGS84


OUTPUT_LAYER_NAME = "Viewshed"

DEFAULT_MAX_DISTANCE_M = 5000.0
DEFAULT_OPACITY = 0.65

# The coverage polygon's own appearance, both user-adjustable from
# the dialog (see viewshed_dialog.py). The default colour stays
# line_of_sight.py's own VISIBLE_COLOR so an untouched viewshed still
# speaks the same green "this is visible" language as a Line of Sight
# run; a user picking their own colour is departing from that
# deliberately - most often to tell two sensors' coverage apart, or
# to stay legible over a base map the default green disappears into.
DEFAULT_COLOR = VISIBLE_COLOR
DEFAULT_OUTLINE_ONLY = False

# Matches line_of_sight.py's own visible-segment line width, so an
# outline-only viewshed and a Line of Sight result drawn together
# read as the same weight of mark.
OUTLINE_WIDTH_MM = 0.6

# gdal_viewshed's own output pixel values, chosen explicitly rather
# than left at its defaults (-vv 255/-iv 0/-ov 0, a plain binary
# mask). 0 doubles as this raster's own NoData value (see
# _run_viewshed()'s matching -ov/-a_nodata). Both this raw raster and
# the DEAD_GROUND_VALUE class are purely an intermediate step now -
# see _polygonize_visible_area() - only VISIBLE_VALUE ever reaches the
# final layer.
OUT_OF_RANGE_VALUE = 0
DEAD_GROUND_VALUE = 1
VISIBLE_VALUE = 2

# Standard latitude/longitude-to-metres approximation, used only to
# size the pre-clip box below - gdal_viewshed's own -md parameter
# enforces the real metric radius precisely, in the reprojected DEM's
# own (metric) CRS, once clipping/reprojection has happened.
METERS_PER_DEGREE_LATITUDE = 111320.0
MIN_COS_LATITUDE = 0.01

# Extra padding applied to max_distance_m before converting to a
# clip box, matching line_of_sight.py's own margin convention around
# its two points' bounding box.
OBSERVER_EXTENT_MARGIN_FRACTION = 0.1

# Segments per quadrant when building the maximum-range circle the
# fixed-altitude path is clipped back to (see _clip_to_range()). 36 puts
# a vertex every 2.5 degrees, far finer than the DEM pixels the coverage
# polygon is already quantised to, so the circle never becomes the
# visibly coarse edge.
RANGE_CIRCLE_SEGMENTS = 36


def _observer_extent(observer_lonlat, max_distance_m):

    """
    A WGS84 QgsRectangle centred on observer_lonlat, sized to
    comfortably contain a circle of radius max_distance_m - used to
    clip the DEM to only the area a viewshed at this range could
    possibly need, rather than processing the DEM's entire extent.
    Longitude padding widens away from the equator (a degree of
    longitude covers less ground at higher latitudes), clamped away
    from zero for the near-pole edge case.
    """

    padded_distance_m = max_distance_m * (
        1.0 + OBSERVER_EXTENT_MARGIN_FRACTION
    )

    half_height_deg = padded_distance_m / METERS_PER_DEGREE_LATITUDE

    cos_latitude = max(
        math.cos(math.radians(observer_lonlat.y())),
        MIN_COS_LATITUDE
    )

    half_width_deg = half_height_deg / cos_latitude

    return QgsRectangle(
        observer_lonlat.x() - half_width_deg,
        observer_lonlat.y() - half_height_deg,
        observer_lonlat.x() + half_width_deg,
        observer_lonlat.y() + half_height_deg
    )


def _clamp_to_sea_level(clipped_dem):

    """
    A bathymetric DEM (e.g. GMRT) holds negative values below mean
    sea level for open water - genuine seafloor depth, not a surface
    anyone stands or sails on. An observer or target over water sits
    at the sea surface (elevation 0), not the seabed, so any elevation
    below 0 is clamped up to 0 before gdal:viewshed ever sees it - the
    same "below zero is sea" simplification hypsometric_tint.py's own
    colour ramp already relies on elsewhere in this plugin. This also
    clamps a genuine below-sea-level inland depression the same way,
    an accepted trade-off since nothing in a DEM alone distinguishes
    that from ocean floor. gdal:viewshed has no such option of its
    own, so this has to happen as a pre-processing pass on the raster
    itself, unlike line_of_sight.py's own version of this same clamp,
    which can just clamp each Python-sampled point directly.
    """

    result = processing.run(
        "gdal:rastercalculator",
        {
            "INPUT_A": clipped_dem,
            "BAND_A": 1,
            "FORMULA": "numpy.maximum(A, 0)",
            "NO_DATA": None,
            "RTYPE": 5,  # Float32 - matches a typical DEM's own dtype
            "OPTIONS": "",
            "EXTRA": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "clamped_dem"
    )


def _run_viewshed(
    clamped_dem,
    observer_point,
    observer_height,
    target_height,
    max_distance
):

    """
    A single gdal:viewshed run against clamped_dem (already clipped,
    reprojected to a metric CRS, and sea-level-clamped - see
    generate_viewshed()), producing a raster with three distinct pixel
    values instead of a plain binary mask: visible, dead ground
    (blocked by terrain, within range), and out of range (also this
    raster's own NoData - see OUT_OF_RANGE_VALUE). -cc is set
    explicitly from line_of_sight.py's own REFRACTION_COEFFICIENT
    (cc = 1 - k) rather than left at GDAL's own default (0.85714, a
    different standard refraction coefficient than the 0.87 Line of
    Sight uses), so the two features agree on the same physical
    assumption. Passed via EXTRA as one multi-flag string rather than
    individual parameters - confirmed against GdalUtils.py that a
    string starting with "-" followed by a non-digit is deliberately
    never quoted by escapeAndJoin(), specifically so a multi-flag EXTRA
    string like this one survives as separate arguments once the fused
    command line is re-split for execution.
    """

    curvature_coefficient = 1.0 - REFRACTION_COEFFICIENT

    result = processing.run(
        "gdal:viewshed",
        {
            "INPUT": clamped_dem,
            "BAND": 1,
            "OBSERVER": observer_point,
            "OBSERVER_HEIGHT": observer_height,
            "TARGET_HEIGHT": target_height,
            "MAX_DISTANCE": max_distance,
            "OPTIONS": "",
            "CREATION_OPTIONS": "",
            "EXTRA": (
                f"-vv {VISIBLE_VALUE} -iv {DEAD_GROUND_VALUE} "
                f"-ov {OUT_OF_RANGE_VALUE} -a_nodata {OUT_OF_RANGE_VALUE} "
                f"-cc {curvature_coefficient}"
            ),
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "viewshed_raw"
    )


def _run_min_visible_altitude(
    clamped_dem,
    observer_point,
    observer_height,
    refraction_coefficient
):

    """
    gdal:viewshed in its DEM output mode, which returns something quite
    different from _run_viewshed()'s visible/not-visible mask: every
    pixel holds the MINIMUM ABSOLUTE ALTITUDE - in the DEM's own
    vertical datum, i.e. AMSL - at which a target over that pixel first
    becomes visible from the observer.

    That is the right primitive for a target at a constant altitude (an
    aircraft flying level), which the plain mask cannot express at all:
    -tz is a height above the terrain at each target cell, so a fixed
    -tz makes the "aircraft" ride up and down over every ridge instead
    of flying level. Threshold this raster at an altitude Z instead and
    the answer is exact, terrain masking included for free - ground
    standing above Z simply reports a minimum higher than Z and drops
    out, which is also why a target cannot be seen "through" a mountain
    taller than it is.

    Verified by probe 2026-08-20 against a 200 m synthetic ridge:
    values behind it climb 200 -> 217.7 -> 235.5 as the grazing
    sightline projects outward, and are 0 (visible at ground level) in
    front of it.

    **-md does NOT apply in this mode** - confirmed by probe, output is
    byte-identical with -md unset and -md 1500. Maximum range has to be
    imposed afterwards; see _clip_to_range().
    """

    result = processing.run(
        "gdal:viewshed",
        {
            "INPUT": clamped_dem,
            "BAND": 1,
            "OBSERVER": observer_point,
            "OBSERVER_HEIGHT": observer_height,
            "TARGET_HEIGHT": 0.0,
            "MAX_DISTANCE": 0,
            "OPTIONS": "",
            "CREATION_OPTIONS": "",
            "EXTRA": (
                f"-om DEM -cc {1.0 - refraction_coefficient}"
            ),
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "min_visible_altitude"
    )


def _threshold_at_altitude(min_altitude_raster, target_altitude):

    """
    A minimum-visible-altitude raster (see
    _run_min_visible_altitude()) reduced to the same
    visible/out-of-range classification _run_viewshed() produces
    directly, so _polygonize_visible_area() can consume either: a pixel
    whose minimum is at or below target_altitude is visible, everything
    else is not.
    """

    result = processing.run(
        "gdal:rastercalculator",
        {
            "INPUT_A": min_altitude_raster,
            "BAND_A": 1,
            "FORMULA": (
                f"numpy.where(A <= {target_altitude}, "
                f"{VISIBLE_VALUE}, {OUT_OF_RANGE_VALUE})"
            ),
            "NO_DATA": OUT_OF_RANGE_VALUE,
            "RTYPE": 0,  # Byte - the output only ever holds 0 or 2
            "OPTIONS": "",
            "EXTRA": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "visible_at_altitude"
    )


def _clip_to_range(layer, centre_point, max_distance):

    """
    Cuts `layer` back to a circle of radius max_distance around
    centre_point (both in layer's own metric CRS). Needed only on the
    fixed-altitude path, where gdal:viewshed's own -md is ignored (see
    _run_min_visible_altitude()) - without this the result would run
    out to the corners of the clip box, which reach roughly 1.4x the
    intended range on the diagonal.
    """

    circle = QgsVectorLayer(
        f"Polygon?crs={layer.crs().authid()}",
        "range_circle",
        "memory"
    )

    feature = QgsFeature()

    feature.setGeometry(
        QgsGeometry.fromPointXY(centre_point).buffer(
            max_distance,
            RANGE_CIRCLE_SEGMENTS
        )
    )

    circle.dataProvider().addFeature(feature)
    circle.updateExtents()

    result = processing.run(
        "native:clip",
        {
            "INPUT": layer,
            "OVERLAY": circle,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    return result["OUTPUT"]


def visible_area_at_altitude(
    dem_layer,
    observer_lonlat,
    observer_height,
    detection_height,
    max_distance,
    refraction_coefficient=REFRACTION_COEFFICIENT
):

    """
    The area from which a target flying LEVEL at a fixed altitude is
    visible to an observer at observer_lonlat - the sensor-coverage
    counterpart to visible_area_for_observer(), which instead answers
    "what ground can be seen from here".

    `detection_height` is the sensor's own vertical capability measured
    ABOVE ITS OWN ANTENNA, not above the terrain and not above sea
    level. The target's absolute altitude is therefore
    (terrain under the sensor) + observer_height + detection_height, so
    the same radar covers a higher slice of airspace when sited higher:
    a 5 m mast at sea level with a 3,300 m capability reaches 3,305 m
    AMSL, while the same set on a 2,000 m plateau reaches 5,305 m. That
    is the maintainer's own model, worked through on 2026-08-20, and it
    is the reason this cannot be expressed with a plain -tz.

    `refraction_coefficient` defaults to this module's own optical
    value so a caller that does not care is unchanged; radar callers
    pass their own (see sensor_coverage.RADAR_REFRACTION_COEFFICIENT).

    Returns None if observer_lonlat falls outside dem_layer's coverage.
    """

    transform_to_source_crs = QgsCoordinateTransform(
        WGS84,
        dem_layer.crs(),
        QgsProject.instance()
    )

    if not dem_layer.extent().contains(
        transform_to_source_crs.transform(observer_lonlat)
    ):
        return None

    clipped_dem = clip_and_reproject_dem(
        dem_layer,
        _observer_extent(observer_lonlat, max_distance),
        WGS84
    )

    clamped_dem = _clamp_to_sea_level(
        clipped_dem
    )

    transform_to_dem_crs = QgsCoordinateTransform(
        WGS84,
        clamped_dem.crs(),
        QgsProject.instance()
    )

    observer_point = transform_to_dem_crs.transform(
        observer_lonlat
    )

    # The sea-level-clamped DEM, deliberately, not the raw one: a
    # sensor on a boat sits on the water surface at 0 m, not on the
    # seabed - the same reasoning as _clamp_to_sea_level() itself.
    terrain_elevation, sampled = clamped_dem.dataProvider().sample(
        observer_point,
        1
    )

    if not sampled:
        return None

    target_altitude = (
        terrain_elevation + observer_height + detection_height
    )

    min_altitude_raster = _run_min_visible_altitude(
        clamped_dem,
        observer_point,
        observer_height,
        refraction_coefficient
    )

    visible_mask = _threshold_at_altitude(
        min_altitude_raster,
        target_altitude
    )

    return _clip_to_range(
        _polygonize_visible_area(visible_mask),
        observer_point,
        max_distance
    )


def _polygonize_visible_area(raster_layer):

    """
    Converts the raster's visible/dead-ground/out-of-range
    classification into a vector polygon layer containing ONLY the
    visible area. Rendering visible AND dead ground together (as an
    earlier version of this feature did) fills nearly the whole
    analysis circle solid, which reads as "the whole circle is
    relevant" rather than highlighting the specific area that's
    actually visible - confirmed confusing in practice. This matches
    how most other viewshed tools present a result by default: just
    the visible footprint. gdal:polygonize already skips this raster's
    own NoData value (out of range - see _run_viewshed()) on its own,
    so only dead ground needs filtering out explicitly afterwards.
    """

    polygonize_result = processing.run(
        "gdal:polygonize",
        {
            "INPUT": raster_layer,
            "BAND": 1,
            "FIELD": "DN",
            "EIGHT_CONNECTEDNESS": False,
            "EXTRA": None,
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    polygonized_layer = QgsVectorLayer(
        polygonize_result["OUTPUT"],
        "viewshed_polygonized",
        "ogr"
    )

    filter_result = processing.run(
        "native:extractbyattribute",
        {
            "INPUT": polygonized_layer,
            "FIELD": "DN",
            "OPERATOR": 0,  # "="
            "VALUE": str(VISIBLE_VALUE),
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    # Unlike a GDAL-wrapped algorithm, native:extractbyattribute's
    # TEMPORARY_OUTPUT resolves to an already-loaded QgsVectorLayer
    # object directly (confirmed live), not a file path to re-wrap.
    return filter_result["OUTPUT"]


def _apply_polygon_style(
    layer,
    opacity,
    color=DEFAULT_COLOR,
    outline_only=DEFAULT_OUTLINE_ONLY
):

    """
    Styles the coverage polygon in `color` (an (r, g, b) tuple),
    either as a flat fill (the default) or as outline only. Dead
    ground has no colour of its own any more - see
    _polygonize_visible_area()'s own docstring for why.

    Outline only exists because a filled coverage polygon, even at
    65% opacity, still washes out whatever it sits on - and what a
    viewshed sits on (contours, hillshade, a unit's own symbology) is
    frequently the very thing being judged against it. Drawing just
    the boundary keeps the shape of the coverage while leaving the
    ground underneath fully readable. It also makes overlapping
    coverage from two observers legible, which stacked translucent
    fills are not.
    """

    red, green, blue = color

    if outline_only:

        symbol = QgsFillSymbol.createSimple(
            {
                "style": "no",
                "outline_style": "solid",
                "outline_color": f"{red},{green},{blue}",
                "outline_width": str(OUTLINE_WIDTH_MM),
                "outline_width_unit": "MM",
            }
        )

    else:

        symbol = QgsFillSymbol.createSimple(
            {
                "color": f"{red},{green},{blue}",
                "outline_style": "no",
            }
        )

    layer.renderer().setSymbol(
        symbol
    )

    layer.setOpacity(
        opacity
    )

    layer.triggerRepaint()


def default_insert_position(project, layer):

    """
    Viewshed's own default placement for a brand new layer - top of
    the tree, since like Line of Sight this is an analysis-result
    overlay meant to sit above whatever base terrain rendering
    (Hypsometric Tint, Combined Hillshade) is underneath, not a
    full-coverage base layer itself. Only used when there's no
    previous layer's position to inherit (see core/_layer_utils.py's
    replace_named_layer()).
    """

    project.layerTreeRoot().insertLayer(
        0,
        layer
    )


def visible_area_for_observer(
    dem_layer,
    observer_lonlat,
    observer_height,
    target_height,
    max_distance
):

    """
    The whole clip/clamp/viewshed/polygonize pipeline for ONE observer,
    returning an unnamed, unstyled polygon layer of just the visible
    area - or None if observer_lonlat falls outside dem_layer's own
    coverage. The returned layer is in the local UTM zone
    clip_and_reproject_dem() picked for this observer, NOT a fixed CRS:
    two observers far enough apart genuinely land in different zones,
    so a caller combining several results must reproject them to a
    common CRS itself (see sensor_coverage.py).

    Split out of generate_viewshed() (2026-08-20) so multi-sensor
    coverage can run the same pipeline per point and merge the results,
    rather than owning a second copy of it that could drift from this
    one - the same reasoning that made stabilised_point_size_
    expression() shared.
    """

    transform_to_source_crs = QgsCoordinateTransform(
        WGS84,
        dem_layer.crs(),
        QgsProject.instance()
    )

    if not dem_layer.extent().contains(
        transform_to_source_crs.transform(observer_lonlat)
    ):
        return None

    clipped_dem = clip_and_reproject_dem(
        dem_layer,
        _observer_extent(observer_lonlat, max_distance),
        WGS84
    )

    clamped_dem = _clamp_to_sea_level(
        clipped_dem
    )

    transform_to_dem_crs = QgsCoordinateTransform(
        WGS84,
        clamped_dem.crs(),
        QgsProject.instance()
    )

    observer_point = transform_to_dem_crs.transform(
        observer_lonlat
    )

    raw_viewshed = _run_viewshed(
        clamped_dem,
        observer_point,
        observer_height,
        target_height,
        max_distance
    )

    return _polygonize_visible_area(
        raw_viewshed
    )


def generate_viewshed(
    dem_layer,
    observer_lonlat,
    observer_height,
    target_height,
    max_distance,
    opacity=DEFAULT_OPACITY,
    color=DEFAULT_COLOR,
    outline_only=DEFAULT_OUTLINE_ONLY
):

    """
    Build a "Viewshed" polygon layer covering just the area visible
    from observer_lonlat (a WGS84 QgsPointXY), out to max_distance,
    against dem_layer clipped to a box sized from max_distance (see
    _observer_extent() - deliberately not the DEM's full extent or the
    current map canvas). Deliberately does NOT add the layer to the
    project - see core/_layer_utils.py's module docstring for why.

    color (an (r, g, b) tuple) and outline_only control how the
    coverage polygon is drawn, not what it contains - see
    _apply_polygon_style(). Both default to the original appearance,
    so an existing caller passing neither is unaffected.

    Returns None if observer_lonlat falls outside dem_layer's own
    coverage.
    """

    output_layer = visible_area_for_observer(
        dem_layer,
        observer_lonlat,
        observer_height,
        target_height,
        max_distance
    )

    if output_layer is None:
        return None

    output_layer.setName(
        OUTPUT_LAYER_NAME
    )

    _apply_polygon_style(
        output_layer,
        opacity,
        color,
        outline_only
    )

    return output_layer
