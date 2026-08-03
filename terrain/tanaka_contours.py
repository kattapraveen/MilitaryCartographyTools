# -*- coding: utf-8 -*-

"""
Tanaka (illuminated) contours - contour lines whose width varies by
local terrain illumination (giving a pseudo-3D relief effect without
needing a hillshade raster underneath) and whose color varies by
elevation, per the standard hypsometric ("layer tint") convention
used on topographic/military maps.

Military Cartography Tools
"""

import math
import tempfile

import processing

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsLineSymbol,
    QgsPointXY,
    QgsProject,
    QgsProperty,
    QgsRasterLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from ..core.coordinate_utils import WGS84, get_utm_crs


# Matches the default light direction QgsHillshadeRenderer/
# gdal:hillshade already use, so a Tanaka layer reads consistently
# alongside any hillshade a user layers underneath it.
DEFAULT_LIGHT_AZIMUTH = 315.0

DEFAULT_INTERVAL = 20.0
DEFAULT_SEGMENT_LENGTH = 50.0
DEFAULT_MIN_WIDTH_MM = 0.15
DEFAULT_MAX_WIDTH_MM = 0.6

# The layer name generate_tanaka_contours() always creates - shared
# with tanaka_dialog.py, which needs it to find and remove a
# previous run's layer when the user wants their edited settings
# applied in place rather than piling up a new layer each time.
OUTPUT_LAYER_NAME = "Tanaka Contours"

# How far, in the reprojected DEM's own map units (always metres -
# see _clip_and_reproject()), to sample perpendicular to a segment
# when determining which side is uphill. Too small risks landing on
# the same DEM pixel on both sides at coarse resolutions; too large
# starts sampling terrain that isn't really local to this segment.
UPHILL_SAMPLE_OFFSET_M = 15.0

# Standard hypsometric ("layer tint") colour convention used on
# topographic/military maps: shades of blue below sea level, then
# green -> yellow -> brown -> red -> white with increasing elevation
# above it (white standing in for permanent snow/ice at the highest
# bands). Defined as (fraction 0-1, colour) rather than fixed
# absolute elevations - a single Tanaka generation typically only
# spans a few hundred metres of local relief, so a fixed global scale
# (e.g. 0-5500m) would leave any one run stuck inside one narrow
# slice of it and read as basically monochrome (confirmed live: a
# real Tanzania DEM clip came out entirely brown against the first,
# fixed-elevation version of this ramp). Stretched per-generation
# instead, against that output's own min/max elevation - see
# _hypsometric_color() - so every run shows the full ramp regardless
# of the area's absolute elevation.
SEA_RAMP = (
    (0.0, (168, 218, 250)),
    (0.35, (39, 106, 165)),
    (0.7, (13, 55, 117)),
    (1.0, (7, 21, 59)),
)

LAND_RAMP = (
    (0.0, (57, 130, 69)),
    (0.1, (104, 164, 79)),
    (0.2, (166, 190, 101)),
    (0.3, (216, 194, 111)),
    (0.4, (177, 132, 87)),
    (0.55, (150, 100, 80)),
    (0.7, (186, 129, 116)),
    (0.85, (222, 190, 176)),
    (1.0, (255, 255, 255)),
)


def _clip_and_reproject(dem_layer, extent, extent_crs):

    """
    Clip dem_layer to extent (given in extent_crs) and reproject it
    to the local UTM zone for that extent's centre, in one
    gdal:warpreproject call. Segment length/bearing math downstream
    needs a projected, metric CRS - the source DEM may well be
    geographic (confirmed true for real SRTM-style data).
    """

    transform_to_wgs84 = QgsCoordinateTransform(
        extent_crs,
        WGS84,
        QgsProject.instance()
    )

    centre_wgs84 = transform_to_wgs84.transform(
        extent.center()
    )

    utm_crs = get_utm_crs(
        centre_wgs84.y(),
        centre_wgs84.x()
    )

    result = processing.run(
        "gdal:warpreproject",
        {
            "INPUT": dem_layer,
            "SOURCE_CRS": dem_layer.crs(),
            "TARGET_CRS": utm_crs,
            "RESAMPLING": 0,
            "NODATA": None,
            "TARGET_RESOLUTION": None,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "TARGET_EXTENT": extent,
            "TARGET_EXTENT_CRS": extent_crs,
            "MULTITHREADING": False,
            "EXTRA": None,
            "OUTPUT": tempfile.mktemp(suffix=".tif")
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "tanaka_dem_clip"
    )


def _generate_contour_segments(dem_layer, interval, segment_length):

    """
    Contour lines from dem_layer at the given interval, split into
    roughly uniform segment_length pieces so illumination can vary
    smoothly along a line rather than in one chunk per original
    (unevenly spaced) contour vertex run.
    """

    contour_result = processing.run(
        "gdal:contour",
        {
            "INPUT": dem_layer,
            "BAND": 1,
            "INTERVAL": interval,
            "FIELD_NAME": "ELEV",
            "CREATE_3D": False,
            "IGNORE_NODATA": False,
            "NODATA": None,
            "OFFSET": 0.0,
            "EXTRA": None,
            "OPTIONS": "",
            "OUTPUT": tempfile.mktemp(suffix=".gpkg")
        }
    )

    contour_layer = QgsVectorLayer(
        contour_result["OUTPUT"],
        "tanaka_contours_raw",
        "ogr"
    )

    split_result = processing.run(
        "native:splitlinesbylength",
        {
            "INPUT": contour_layer,
            "LENGTH": segment_length,
            "OUTPUT": tempfile.mktemp(suffix=".gpkg")
        }
    )

    return QgsVectorLayer(
        split_result["OUTPUT"],
        "tanaka_contours_segments",
        "ogr"
    )


def _light_vector(azimuth_degrees):

    """
    Unit vector pointing from the terrain toward the light source,
    as (easting, northing) map-unit components.
    """

    azimuth_radians = math.radians(
        azimuth_degrees
    )

    return (
        math.sin(azimuth_radians),
        math.cos(azimuth_radians)
    )


def _interpolate_stops(elevation, stops):

    """
    Linear-interpolate an (r, g, b) colour between the two stops
    bracketing elevation, clamping to the nearest end colour beyond
    either edge rather than extrapolating.
    """

    if elevation <= stops[0][0]:
        return stops[0][1]

    if elevation >= stops[-1][0]:
        return stops[-1][1]

    for (elev_a, color_a), (elev_b, color_b) in zip(stops, stops[1:]):

        if elev_a <= elevation <= elev_b:

            ratio = (elevation - elev_a) / (elev_b - elev_a)

            return tuple(
                round(a + (b - a) * ratio)
                for a, b in zip(color_a, color_b)
            )

    return stops[-1][1]


def _clamp01(value):

    return max(0.0, min(1.0, value))


def _hypsometric_color(elevation, min_elevation, max_elevation):

    """
    (r, g, b) for a contour's own elevation, normalised against
    min_elevation/max_elevation - the actual range present in this
    generation's own output, not a fixed global scale (see the
    SEA_RAMP/LAND_RAMP comment above for why).

    A real coastline (min_elevation < 0, i.e. this generation's own
    output actually dips below sea level) still anchors land and sea
    exactly at 0, each normalised over its own side independently
    (0..max_elevation for land, min_elevation..0 for sea) - elevation
    relative to sea level still means something concrete whenever sea
    level is actually present in the data. Otherwise (the common
    case: an inland area with no negative elevations at all) the
    whole output is land, so the full LAND_RAMP is stretched across
    min_elevation..max_elevation instead of forcing it to start at 0,
    guaranteeing the full ramp is visible regardless of how high up
    that elevation range happens to sit.
    """

    if min_elevation < 0:

        if elevation < 0:

            depth_span = max(-min_elevation, 1e-6)

            fraction = _clamp01(-elevation / depth_span)

            return _interpolate_stops(fraction, SEA_RAMP)

        height_span = max(max_elevation, 1e-6)

        fraction = _clamp01(elevation / height_span)

        return _interpolate_stops(fraction, LAND_RAMP)

    span = max(max_elevation - min_elevation, 1e-6)

    fraction = _clamp01(
        (elevation - min_elevation) / span
    )

    return _interpolate_stops(fraction, LAND_RAMP)


def _segment_illumination(segment_geometry, dem_provider, light_vector):

    """
    -1 (fully shadowed) to +1 (fully lit) for one contour segment:
    the dot product of its local uphill direction and the light
    source's direction.

    A contour segment's own bearing is always perpendicular to the
    true slope direction at that point (a contour traces constant
    elevation), so no separate aspect raster is needed - just
    whichever of the two perpendicular directions from the segment
    is higher, sampled directly from the DEM.

    Returns None if the geometry is degenerate or either sample
    point falls outside the DEM (e.g. right at its edge).
    """

    polyline = segment_geometry.asPolyline()

    if len(polyline) < 2:
        return None

    start, end = polyline[0], polyline[-1]

    dx = end.x() - start.x()
    dy = end.y() - start.y()

    length = math.hypot(dx, dy)

    if length == 0:
        return None

    tangent = (dx / length, dy / length)

    perpendicular_a = (-tangent[1], tangent[0])
    perpendicular_b = (tangent[1], -tangent[0])

    midpoint = QgsPointXY(
        (start.x() + end.x()) / 2,
        (start.y() + end.y()) / 2
    )

    point_a = QgsPointXY(
        midpoint.x() + perpendicular_a[0] * UPHILL_SAMPLE_OFFSET_M,
        midpoint.y() + perpendicular_a[1] * UPHILL_SAMPLE_OFFSET_M
    )

    point_b = QgsPointXY(
        midpoint.x() + perpendicular_b[0] * UPHILL_SAMPLE_OFFSET_M,
        midpoint.y() + perpendicular_b[1] * UPHILL_SAMPLE_OFFSET_M
    )

    value_a, ok_a = dem_provider.sample(point_a, 1)
    value_b, ok_b = dem_provider.sample(point_b, 1)

    if not (ok_a and ok_b):
        return None

    uphill = perpendicular_a if value_a >= value_b else perpendicular_b

    return (
        uphill[0] * light_vector[0]
        + uphill[1] * light_vector[1]
    )


def _build_output_layer(segment_layer, dem_layer, light_azimuth_deg, crs):

    """
    A new memory layer holding every segment with a valid
    illumination value, plus its elevation, ready for styling.
    """

    output_layer = QgsVectorLayer(
        f"LineString?crs={crs.authid()}",
        OUTPUT_LAYER_NAME,
        "memory"
    )

    output_layer.dataProvider().addAttributes(
        [
            QgsField("ELEV", QMetaType.Type.Double),
            QgsField("ILLUM", QMetaType.Type.Double),
            QgsField("R", QMetaType.Type.Int),
            QgsField("G", QMetaType.Type.Int),
            QgsField("B", QMetaType.Type.Int),
        ]
    )

    output_layer.updateFields()

    dem_provider = dem_layer.dataProvider()

    light_vector = _light_vector(
        light_azimuth_deg
    )

    # Two passes: colour is normalised against this generation's own
    # elevation range (see _hypsometric_color()), so the range has to
    # be known before any feature's colour can be computed - buffer
    # the valid (geometry, elevation, illumination) tuples first,
    # then assign colours once min/max are known.
    valid_segments = []

    min_elevation = None
    max_elevation = None

    for segment in segment_layer.getFeatures():

        illumination = _segment_illumination(
            segment.geometry(),
            dem_provider,
            light_vector
        )

        if illumination is None:
            continue

        elevation = segment["ELEV"]

        if min_elevation is None or elevation < min_elevation:
            min_elevation = elevation

        if max_elevation is None or elevation > max_elevation:
            max_elevation = elevation

        valid_segments.append(
            (segment.geometry(), elevation, illumination)
        )

    features = []

    for geometry, elevation, illumination in valid_segments:

        red, green, blue = _hypsometric_color(
            elevation,
            min_elevation,
            max_elevation
        )

        feature = QgsFeature(
            output_layer.fields()
        )

        feature.setGeometry(
            geometry
        )

        feature.setAttributes(
            [
                elevation,
                illumination,
                red,
                green,
                blue
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


# Monochrome mode's grayscale range - dark shadow-grey to near-white
# lit, not full 0-255 black-to-white, so even a fully-shadowed
# segment stays legible against a white page background rather than
# vanishing into pure black.
MONOCHROME_SHADOW_GRAY = 40
MONOCHROME_LIT_GRAY = 235


def _apply_style(layer, min_width_mm, max_width_mm, monochrome=False):

    """
    One line symbol whose width is always data-defined by each
    feature's own ILLUM value (thin where illuminated, thick where
    shadowed - the classic Tanaka relief effect).

    Color is data-defined two different ways depending on
    monochrome:
    - False (default): each feature's own precomputed R/G/B
      hypsometric-tint fields (see _hypsometric_color()) - color
      carries elevation, independently of the illumination-driven
      width.
    - True: a grayscale blend driven by ILLUM instead (dark where
      shadowed, light where lit) - the classic monochrome Tanaka
      look, where both width and tone come from the same
      illumination value.
    """

    symbol = QgsLineSymbol.createSimple(
        {
            "color": "128,128,128",
            "width": str(min_width_mm),
            "width_unit": "MM"
        }
    )

    symbol_layer = symbol.symbolLayer(0)

    symbol_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeWidth,
        QgsProperty.fromExpression(
            f'scale_linear("ILLUM", -1, 1, {max_width_mm}, {min_width_mm})'
        )
    )

    if monochrome:

        color_expression = (
            "color_mix_rgb("
            f"color_rgb({MONOCHROME_SHADOW_GRAY}, {MONOCHROME_SHADOW_GRAY}, {MONOCHROME_SHADOW_GRAY}), "
            f"color_rgb({MONOCHROME_LIT_GRAY}, {MONOCHROME_LIT_GRAY}, {MONOCHROME_LIT_GRAY}), "
            'scale_linear("ILLUM", -1, 1, 0, 1))'
        )

    else:

        color_expression = 'color_rgb("R", "G", "B")'

    symbol_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeColor,
        QgsProperty.fromExpression(
            color_expression
        )
    )

    layer.renderer().setSymbol(
        symbol
    )

    layer.triggerRepaint()


def generate_tanaka_contours(
    dem_layer,
    extent,
    extent_crs,
    interval=DEFAULT_INTERVAL,
    segment_length=DEFAULT_SEGMENT_LENGTH,
    light_azimuth_deg=DEFAULT_LIGHT_AZIMUTH,
    min_width_mm=DEFAULT_MIN_WIDTH_MM,
    max_width_mm=DEFAULT_MAX_WIDTH_MM,
    monochrome=False
):

    """
    Build a Tanaka (illuminated) contour layer from dem_layer,
    clipped to extent. Line width is always data-defined by local
    terrain illumination relative to light_azimuth_deg (thin where
    lit, thick where shadowed). Color is data-defined by each
    contour's own elevation, per the standard hypsometric convention
    (see _hypsometric_color()), unless monochrome=True, in which case
    it's a grayscale blend driven by illumination instead (the
    classic monochrome Tanaka look). Adds the result to the current
    project and returns it.
    """

    clipped_dem = _clip_and_reproject(
        dem_layer,
        extent,
        extent_crs
    )

    segment_layer = _generate_contour_segments(
        clipped_dem,
        interval,
        segment_length
    )

    output_layer = _build_output_layer(
        segment_layer,
        clipped_dem,
        light_azimuth_deg,
        clipped_dem.crs()
    )

    _apply_style(
        output_layer,
        min_width_mm,
        max_width_mm,
        monochrome=monochrome
    )

    QgsProject.instance().addMapLayer(
        output_layer
    )

    return output_layer
