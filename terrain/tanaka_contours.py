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

import processing

from qgis.core import (
    QgsFeature,
    QgsField,
    QgsLineSymbol,
    QgsPointXY,
    QgsProcessing,
    QgsProperty,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QPainter

from ._dem_utils import (
    band_min_max as _band_min_max,
    clip_and_reproject_dem as _clip_and_reproject,
)
from ._hypsometric_ramp import (
    hypsometric_color as _hypsometric_color,
    LAND_RAMP,
    SEA_RAMP,
)


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
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
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
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    # Unlike a GDAL-wrapped algorithm, native:splitlinesbylength's
    # TEMPORARY_OUTPUT resolves to an already-loaded QgsVectorLayer
    # object directly (confirmed live), not a file path to re-wrap.
    return split_result["OUTPUT"]


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


def _build_output_layer(
    segment_layer,
    dem_layer,
    light_azimuth_deg,
    crs,
    min_elevation,
    max_elevation
):

    """
    A new memory layer holding every segment with a valid
    illumination value, plus its elevation, ready for styling.

    min_elevation/max_elevation come from dem_layer's own raw pixel
    range (see generate_tanaka_contours()), not from the drawn
    contour lines' own elevation range - contour levels are quantised
    to the interval, so they rarely reach the DEM's true min/max,
    which previously made Tanaka's colours normalise against a
    narrower range than hypsometric tint's (which already used the
    raw DEM range), a real, confirmed-live mismatch between the two
    layers over the same area. Using the same source for both fixes
    that: an identical DEM/extent now produces identical colours in
    both.
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
            elevation,
            min_elevation,
            max_elevation
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


# Monochrome mode's grayscale range - dark shadow-grey to near-white
# lit, not full 0-255 black-to-white, so even a fully-shadowed
# segment stays legible against a white page background rather than
# vanishing into pure black.
MONOCHROME_SHADOW_GRAY = 40
MONOCHROME_LIT_GRAY = 235

# The three contour styling modes - see _apply_style()'s own
# docstring for what each one does.
STYLE_ELEVATION_COLOR = "elevation_color"
STYLE_MONOCHROME = "monochrome"
STYLE_ILLUMINATED_OVERLAY = "illuminated_overlay"

DEFAULT_STYLE_MODE = STYLE_ELEVATION_COLOR


def _apply_style(layer, min_width_mm, max_width_mm, style_mode=DEFAULT_STYLE_MODE):

    """
    One line symbol whose width is always data-defined by each
    feature's own ILLUM value - thick where a segment faces directly
    toward OR directly away from the light (extreme illumination or
    extreme shadow), thin only where it's perpendicular/grazing to
    the light (ILLUM near 0). Confirmed against multiple independent
    descriptions of the classic Tanaka technique (Manifold's own
    docs, the anitagraser.com tutorial) that this is meant to be
    symmetric in the *magnitude* of illumination, not a plain ramp
    from one extreme to the other - a segment fully facing the light
    should be exactly as thick as one fully in shadow, not the
    thinnest line on the map.

    Color is data-defined three different ways depending on
    style_mode:
    - STYLE_ELEVATION_COLOR (default): each feature's own precomputed
      R/G/B hypsometric-tint fields (see _hypsometric_color()) -
      color carries elevation, independently of the illumination-
      driven width. Not how any conventional Tanaka source actually
      does it (see STYLE_ILLUMINATED_OVERLAY below), but this is the
      look already shipped and approved - kept as the default.
    - STYLE_MONOCHROME: a soft grayscale blend driven by ILLUM (dark
      where shadowed, light where lit) - the classic monochrome
      Tanaka look, using MONOCHROME_SHADOW_GRAY/MONOCHROME_LIT_GRAY
      rather than full black/white so a fully-shadowed line stays
      legible standing alone against a white page.
    - STYLE_ILLUMINATED_OVERLAY: the conventional "colourful Tanaka"
      technique multiple independent sources use to combine
      elevation colour with illumination - the line itself carries
      full 0-255 black/white by ILLUM (not the softened monochrome
      range; both Overlay and Soft Light blending need true black/
      white to drive properly) and the layer's own blend mode is set
      to Soft Light, so its actual displayed colour comes from
      compositing against whatever's underneath (a Hypsometric Tint
      layer, ideally) at render time, rather than carrying independent
      elevation colour that could drift out of sync with it. Soft
      Light rather than Overlay - confirmed live against a real DEM
      with densely-packed 200m contour rings on steep terrain: Overlay
      applies its full darken/lighten swing per segment, and with many
      short (50m) segments flipping between strongly lit and strongly
      shadowed as a ring's bearing rotates around a peak, the shadowed
      sides darkened the tint's own light peak colours into a muddy
      dark red/maroon rather than the clean bright highlights
      references show. Soft Light applies a gentler version of the
      same darken/lighten effect (never pushes all the way to black/
      white the way Overlay can), which keeps the tint's own hue
      recognisable through the shading instead of overpowering it.
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
            f'scale_linear(abs("ILLUM"), 0, 1, {min_width_mm}, {max_width_mm})'
        )
    )

    if style_mode == STYLE_MONOCHROME:

        color_expression = (
            "color_mix_rgb("
            f"color_rgb({MONOCHROME_SHADOW_GRAY}, {MONOCHROME_SHADOW_GRAY}, {MONOCHROME_SHADOW_GRAY}), "
            f"color_rgb({MONOCHROME_LIT_GRAY}, {MONOCHROME_LIT_GRAY}, {MONOCHROME_LIT_GRAY}), "
            'scale_linear("ILLUM", -1, 1, 0, 1))'
        )

    elif style_mode == STYLE_ILLUMINATED_OVERLAY:

        color_expression = (
            "color_mix_rgb("
            "color_rgb(0, 0, 0), "
            "color_rgb(255, 255, 255), "
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

    # Soft Light only for the illuminated-overlay mode - explicitly
    # set back to the ordinary compositing mode for the other two
    # rather than relying on a fresh layer's own default, since this
    # is the one place that owns this layer's rendering.
    layer.setBlendMode(
        QPainter.CompositionMode.CompositionMode_SoftLight
        if style_mode == STYLE_ILLUMINATED_OVERLAY
        else QPainter.CompositionMode.CompositionMode_SourceOver
    )

    layer.triggerRepaint()


def default_insert_position(project, layer):

    """
    Tanaka Contours' own default placement for a brand new layer -
    top of the tree, since it's a vector overlay meant to sit above
    the coarser grid/raster layers. Only used when there's no
    previous layer's position to inherit (see
    core/_layer_utils.py's replace_named_layer()).
    """

    project.layerTreeRoot().insertLayer(
        0,
        layer
    )


def generate_tanaka_contours(
    dem_layer,
    extent,
    extent_crs,
    interval=DEFAULT_INTERVAL,
    segment_length=DEFAULT_SEGMENT_LENGTH,
    light_azimuth_deg=DEFAULT_LIGHT_AZIMUTH,
    min_width_mm=DEFAULT_MIN_WIDTH_MM,
    max_width_mm=DEFAULT_MAX_WIDTH_MM,
    style_mode=DEFAULT_STYLE_MODE
):

    """
    Build a Tanaka (illuminated) contour layer from dem_layer,
    clipped to extent. Line width is always data-defined by local
    terrain illumination relative to light_azimuth_deg (thick where a
    segment faces directly toward or away from the light, thin only
    where perpendicular/grazing to it). Color/blend mode depend on
    style_mode - see _apply_style()'s own docstring for what each of
    STYLE_ELEVATION_COLOR/STYLE_MONOCHROME/STYLE_ILLUMINATED_OVERLAY
    does. Adds the result to the current project and returns it.
    """

    clipped_dem = _clip_and_reproject(
        dem_layer,
        extent,
        extent_crs
    )

    min_elevation, max_elevation = _band_min_max(
        clipped_dem
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
        clipped_dem.crs(),
        min_elevation,
        max_elevation
    )

    _apply_style(
        output_layer,
        min_width_mm,
        max_width_mm,
        style_mode=style_mode
    )

    return output_layer
