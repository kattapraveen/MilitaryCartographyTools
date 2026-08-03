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
# bands). Fixed, absolute elevation anchors rather than a per-DEM
# min/max stretch - the same elevation should tint the same colour
# on any map sheet, not shift depending on what else happens to be
# in this particular clipped extent.
SEA_LEVEL_STOPS = (
    (-8000.0, (7, 21, 59)),
    (-4000.0, (13, 55, 117)),
    (-1000.0, (39, 106, 165)),
    (0.0, (168, 218, 250)),
)

LAND_STOPS = (
    (0.0, (57, 130, 69)),
    (300.0, (104, 164, 79)),
    (750.0, (166, 190, 101)),
    (1250.0, (216, 194, 111)),
    (1750.0, (177, 132, 87)),
    (2500.0, (150, 100, 80)),
    (3500.0, (186, 129, 116)),
    (4500.0, (222, 190, 176)),
    (5500.0, (255, 255, 255)),
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


def _hypsometric_color(elevation):

    """
    (r, g, b) for a contour's own elevation, per the hypsometric
    convention in SEA_LEVEL_STOPS/LAND_STOPS above - which band
    applies is decided purely by the sign of elevation, since the
    two stop tables meet (but don't blend into each other) exactly
    at 0.
    """

    stops = SEA_LEVEL_STOPS if elevation < 0 else LAND_STOPS

    return _interpolate_stops(
        elevation,
        stops
    )


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

    features = []

    for segment in segment_layer.getFeatures():

        illumination = _segment_illumination(
            segment.geometry(),
            dem_provider,
            light_vector
        )

        if illumination is None:
            continue

        elevation = segment["ELEV"]

        red, green, blue = _hypsometric_color(
            elevation
        )

        feature = QgsFeature(
            output_layer.fields()
        )

        feature.setGeometry(
            segment.geometry()
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


def _apply_style(layer, min_width_mm, max_width_mm):

    """
    One line symbol whose width is data-defined by each feature's
    own ILLUM value (thin where illuminated, thick where shadowed -
    the classic Tanaka relief effect) and whose color is data-defined
    by its own precomputed R/G/B hypsometric-tint fields (see
    _hypsometric_color()) - width still carries the illumination
    shading, color now carries elevation instead of light/shadow.
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

    symbol_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeColor,
        QgsProperty.fromExpression(
            'color_rgb("R", "G", "B")'
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
    max_width_mm=DEFAULT_MAX_WIDTH_MM
):

    """
    Build a Tanaka (illuminated) contour layer from dem_layer,
    clipped to extent. Line width is data-defined by local terrain
    illumination relative to light_azimuth_deg (thin where lit, thick
    where shadowed); color is data-defined by each contour's own
    elevation, per the standard hypsometric convention (see
    _hypsometric_color()). Adds the result to the current project
    and returns it.
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
        max_width_mm
    )

    QgsProject.instance().addMapLayer(
        output_layer
    )

    return output_layer
