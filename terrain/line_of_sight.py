# -*- coding: utf-8 -*-

"""
Line of sight - point-to-point visibility between two coordinates over
a DEM. Combines two independent reasons a target can be hidden: real
terrain (a ridge or hill sampled directly from the DEM) and earth
curvature/atmospheric refraction (which can hide even a low target
over otherwise flat ground once it's far enough away).

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsLineSymbol,
    QgsPointXY,
    QgsProject,
    QgsProperty,
    QgsRectangle,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from ._dem_utils import clip_and_reproject_dem as _clip_and_reproject
from ..core.coordinate_utils import WGS84


# The layer name generate_line_of_sight() always creates - shared with
# line_of_sight_dialog.py, which needs it to find and remove a
# previous run's layer when correcting it in place rather than piling
# up a new layer each time (see terrain/_layer_utils.py).
OUTPUT_LAYER_NAME = "Line of Sight"

# Human eye height / ground-level target - reasonable defaults, both
# adjustable per-run in the dialog.
DEFAULT_OBSERVER_HEIGHT_M = 1.7
DEFAULT_TARGET_HEIGHT_M = 0.0

# Mean earth radius, and the standard terrestrial refraction
# coefficient ("k factor") - the fraction by which atmospheric
# refraction counteracts the geometric curvature drop. 0.13 is the
# widely used standard value for line-of-sight/intervisibility work
# (as opposed to e.g. 0.07 sometimes used for radio propagation).
EARTH_RADIUS_M = 6371000.0
REFRACTION_COEFFICIENT = 0.13

# How many points to sample along the profile - derived from the
# clipped DEM's own pixel size and the observer/target distance
# (roughly one sample per pixel), clamped to a sane range so this
# never turns into a tiny handful of samples for a huge distance or an
# absurd number for a spacing coarser than the DEM's own pixels.
MIN_SAMPLE_COUNT = 50
MAX_SAMPLE_COUNT = 2000

# Float noise guard - a sample within this many metres of the
# reference sightline counts as visible rather than blocked.
BLOCK_TOLERANCE_M = 0.01

VISIBLE_COLOR = (34, 139, 34)
BLOCKED_COLOR = (178, 34, 34)

# Padding applied around the observer/target points' own bounding box
# when clipping the DEM - a fraction of the span between them, with a
# floor so two very close (or identical) points still get a sane,
# non-degenerate clip extent rather than a near-zero-area one.
BOUNDING_EXTENT_MARGIN_FRACTION = 0.1
MIN_BOUNDING_EXTENT_MARGIN_DEGREES = 0.001


def curvature_refraction_drop(distance_m):

    """
    How far, in metres, a point at distance_m from the observer sits
    below the observer's own local tangent plane, once atmospheric
    refraction's partial counteraction of earth curvature is taken
    into account. Standard two-point intervisibility formula.
    """

    return (
        (distance_m ** 2)
        * (1.0 - REFRACTION_COEFFICIENT)
        / (2.0 * EARTH_RADIUS_M)
    )


def _sample_count_for(distance_m, pixel_size_m):

    if pixel_size_m <= 0:
        return MIN_SAMPLE_COUNT

    estimate = int(distance_m / pixel_size_m)

    return max(MIN_SAMPLE_COUNT, min(MAX_SAMPLE_COUNT, estimate))


def compute_profile(
    dem_layer,
    observer_point,
    observer_height,
    target_point,
    target_height
):

    """
    dem_layer must already be clipped/reprojected to a projected
    (metric) CRS; observer_point/target_point are QgsPointXY in that
    same CRS.

    Returns None if either endpoint falls outside the DEM. Otherwise
    (visible, blocked_at_distance, samples): visible is True iff no
    point along the profile is blocked; blocked_at_distance is the
    distance (metres, from the observer) of the first blocking point,
    or None if fully visible; samples is a list of dicts with
    "distance", "terrain_elevation", "sightline_elevation", "visible"
    for every successfully sampled point along the profile.
    """

    provider = dem_layer.dataProvider()

    observer_terrain, observer_ok = provider.sample(observer_point, 1)
    target_terrain, target_ok = provider.sample(target_point, 1)

    if not (observer_ok and target_ok):
        return None

    distance = observer_point.distance(target_point)

    observer_eye_z = observer_terrain + observer_height
    target_eye_z = target_terrain + target_height

    # The target's own eye elevation, expressed in the same
    # curvature-corrected frame as every other sample below (see the
    # loop) - this is what makes the reference sightline a straight
    # line in that frame, rather than needing curvature reapplied
    # separately at each end.
    effective_target_eye_z = target_eye_z - curvature_refraction_drop(
        distance
    )

    pixel_size_m = (
        dem_layer.rasterUnitsPerPixelX()
        + dem_layer.rasterUnitsPerPixelY()
    ) / 2.0

    sample_count = _sample_count_for(distance, pixel_size_m)

    dx = target_point.x() - observer_point.x()
    dy = target_point.y() - observer_point.y()

    samples = []
    visible = True
    blocked_at_distance = None

    for i in range(sample_count + 1):

        fraction = i / sample_count
        sample_distance = distance * fraction

        point = QgsPointXY(
            observer_point.x() + dx * fraction,
            observer_point.y() + dy * fraction
        )

        terrain, ok = provider.sample(point, 1)

        if not ok:
            continue

        effective_terrain = terrain - curvature_refraction_drop(
            sample_distance
        )

        sightline = observer_eye_z + (
            effective_target_eye_z - observer_eye_z
        ) * fraction

        point_visible = effective_terrain <= sightline + BLOCK_TOLERANCE_M

        if not point_visible and visible:
            visible = False
            blocked_at_distance = sample_distance

        samples.append(
            {
                "point": point,
                "distance": sample_distance,
                "terrain_elevation": terrain,
                "sightline_elevation": sightline,
                "visible": point_visible,
            }
        )

    return visible, blocked_at_distance, samples


def _build_output_layer(samples, crs):

    """
    A new memory layer with one line feature per consecutive pair of
    profile samples - geometry follows the real observer-to-target
    line on the ground (each sample's own "point", already in the
    DEM's projected CRS), so it draws as an actual line on the map,
    not an abstract distance/elevation chart. Each segment carries its
    starting distance/elevation and whether that stretch is visible
    (both endpoints visible) or blocked (either endpoint blocked).
    """

    output_layer = QgsVectorLayer(
        f"LineString?crs={crs.authid()}",
        OUTPUT_LAYER_NAME,
        "memory"
    )

    output_layer.dataProvider().addAttributes(
        [
            QgsField("DIST", QMetaType.Type.Double),
            QgsField("TERRAIN_ELEV", QMetaType.Type.Double),
            QgsField("VISIBLE", QMetaType.Type.Bool),
        ]
    )

    output_layer.updateFields()

    features = []

    for sample_a, sample_b in zip(samples, samples[1:]):

        geometry = QgsGeometry.fromPolylineXY(
            [
                sample_a["point"],
                sample_b["point"],
            ]
        )

        feature = QgsFeature(
            output_layer.fields()
        )

        feature.setGeometry(
            geometry
        )

        feature.setAttributes(
            [
                sample_a["distance"],
                sample_a["terrain_elevation"],
                sample_a["visible"] and sample_b["visible"],
            ]
        )

        features.append(
            feature
        )

    output_layer.dataProvider().addFeatures(
        features
    )

    output_layer.updateExtents()

    return output_layer


def _apply_style(layer):

    """
    One line symbol, coloured green where a stretch is visible and red
    where it's blocked - the colour itself is the information being
    conveyed here, not a stylistic choice, so unlike Tanaka Contours
    there's no alternate (e.g. monochrome) scheme to switch between.
    """

    symbol = QgsLineSymbol.createSimple(
        {
            "color": "34,139,34",
            "width": "0.6",
            "width_unit": "MM"
        }
    )

    symbol_layer = symbol.symbolLayer(0)

    red, green, blue = VISIBLE_COLOR
    blocked_red, blocked_green, blocked_blue = BLOCKED_COLOR

    symbol_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeColor,
        QgsProperty.fromExpression(
            'CASE WHEN "VISIBLE" THEN '
            f'color_rgb({red}, {green}, {blue}) ELSE '
            f'color_rgb({blocked_red}, {blocked_green}, {blocked_blue}) END'
        )
    )

    layer.renderer().setSymbol(
        symbol
    )

    layer.triggerRepaint()


def _bounding_extent(observer_lonlat, target_lonlat):

    """
    A WGS84 QgsRectangle around observer_lonlat/target_lonlat, padded
    by BOUNDING_EXTENT_MARGIN_FRACTION of their own span - used to
    clip the DEM for exactly the area this check actually needs,
    regardless of whatever the map canvas happens to be showing at
    generate time. Deriving the clip extent from the two points
    themselves (rather than the current canvas extent) matters here
    specifically: unlike Tanaka Contours/Hypsometric Tint, which
    generate for whatever's on-screen, Line of Sight's two points can
    legitimately be far enough apart that panning/zooming between
    clicking the observer and clicking the target moves the first
    point off-screen - if the clip extent were still tied to the
    canvas, that would silently drop the observer out of the clipped
    DEM and fail with no obvious cause.
    """

    x_min = min(observer_lonlat.x(), target_lonlat.x())
    x_max = max(observer_lonlat.x(), target_lonlat.x())
    y_min = min(observer_lonlat.y(), target_lonlat.y())
    y_max = max(observer_lonlat.y(), target_lonlat.y())

    x_margin = max(
        (x_max - x_min) * BOUNDING_EXTENT_MARGIN_FRACTION,
        MIN_BOUNDING_EXTENT_MARGIN_DEGREES
    )

    y_margin = max(
        (y_max - y_min) * BOUNDING_EXTENT_MARGIN_FRACTION,
        MIN_BOUNDING_EXTENT_MARGIN_DEGREES
    )

    return QgsRectangle(
        x_min - x_margin,
        y_min - y_margin,
        x_max + x_margin,
        y_max + y_margin
    )


def generate_line_of_sight(
    dem_layer,
    observer_lonlat,
    observer_height,
    target_lonlat,
    target_height
):

    """
    Build a "Line of Sight" line layer between observer_lonlat and
    target_lonlat (both WGS84 QgsPointXY, x=longitude/y=latitude),
    against dem_layer clipped to a bounding box around the two points
    (see _bounding_extent() - deliberately not the current map canvas
    extent). Green where the target is visible from the observer, red
    where blocked by terrain or earth curvature/refraction. Adds the
    result to the current project and returns it.

    Returns None if either point falls outside dem_layer's own
    coverage - whether the target is actually visible or not is read
    back from the returned layer's own VISIBLE field, not this return
    value.
    """

    transform_to_source_crs = QgsCoordinateTransform(
        WGS84,
        dem_layer.crs(),
        QgsProject.instance()
    )

    source_extent = dem_layer.extent()

    # Checked against the SOURCE DEM's own extent, before any
    # clipping/warping - the clip extent below is now built purely
    # from the two points' own coordinates (see _bounding_extent()),
    # so it no longer has any relationship to what the source DEM
    # actually covers. A point genuinely outside the source raster's
    # footprint can still come back from a post-warp
    # provider.sample() with a plausible-looking value instead of a
    # clean "invalid" flag (GDAL's NoData handling for area outside
    # the source's own coverage isn't a reliable signal to depend on
    # here) - a plain geometric containment check against the
    # untouched source extent sidesteps that entirely.
    for point in (observer_lonlat, target_lonlat):

        if not source_extent.contains(
            transform_to_source_crs.transform(point)
        ):
            return None

    clipped_dem = _clip_and_reproject(
        dem_layer,
        _bounding_extent(observer_lonlat, target_lonlat),
        WGS84
    )

    transform_to_dem_crs = QgsCoordinateTransform(
        WGS84,
        clipped_dem.crs(),
        QgsProject.instance()
    )

    observer_point = transform_to_dem_crs.transform(
        observer_lonlat
    )

    target_point = transform_to_dem_crs.transform(
        target_lonlat
    )

    result = compute_profile(
        clipped_dem,
        observer_point,
        observer_height,
        target_point,
        target_height
    )

    if result is None:
        return None

    _visible, _blocked_at_distance, samples = result

    output_layer = _build_output_layer(
        samples,
        clipped_dem.crs()
    )

    _apply_style(
        output_layer
    )

    QgsProject.instance().addMapLayer(
        output_layer
    )

    return output_layer
