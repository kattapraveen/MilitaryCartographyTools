# -*- coding: utf-8 -*-

"""
Hypsometric tint - a filled, full-coverage elevation raster using the
same blue-below-sea-level, green-through-white-above-it colour
convention as Tanaka Contours, so the two can be layered together:
this raster fills the gaps between (or underneath) a Tanaka Contours
layer's illuminated lines, rather than leaving them blank.

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsColorRampShader,
    QgsProject,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)

from qgis.PyQt.QtGui import QColor

from ._dem_utils import clip_and_reproject_dem
from ._hypsometric_ramp import LAND_RAMP, SEA_RAMP


OUTPUT_LAYER_NAME = "Hypsometric Tint"

DEFAULT_OPACITY = 1.0


def _band_min_max(raster_layer, band=1):

    """
    (minimum, maximum) pixel value for one band of raster_layer.

    QgsRasterDataProvider.bandStatistics() emits a DeprecationWarning
    ("QgsRasterInterface.bandStatistics() is deprecated") on both
    QGIS 3.44.12 and 4.2.0 regardless of which overload/argument types
    are passed - confirmed live before writing this; a binding-level
    quirk rather than something fixable by calling it differently.
    Values returned are correct, so accepted as a known, harmless
    warning rather than a bug (see docs/developer-guide.md).
    """

    provider = raster_layer.dataProvider()

    stats = provider.bandStatistics(
        band,
        Qgis.RasterBandStatistic.Min | Qgis.RasterBandStatistic.Max
    )

    return stats.minimumValue, stats.maximumValue


def _build_color_ramp_items(min_elevation, max_elevation):

    """
    Convert the fraction-keyed SEA_RAMP/LAND_RAMP stops (see
    _hypsometric_ramp.py) into absolute-elevation
    QgsColorRampShader.ColorRampItem entries for this raster's own
    min/max elevation - the same branch logic as
    _hypsometric_ramp.hypsometric_color() (real coastline present ->
    anchor land/sea at 0; otherwise stretch the full LAND_RAMP across
    this raster's own min..max), so the raster fill and any Tanaka
    contour lines drawn over it agree on what colour a given
    elevation gets. QGIS's own shader interpolates between these
    stops at render time - no need to colour every pixel in Python.
    """

    items = []

    if min_elevation < 0:

        for fraction, (r, g, b) in SEA_RAMP:

            elevation = fraction * min_elevation

            items.append(
                QgsColorRampShader.ColorRampItem(elevation, QColor(r, g, b))
            )

        height_span = max(max_elevation, 1e-6)

        for fraction, (r, g, b) in LAND_RAMP:

            elevation = fraction * height_span

            items.append(
                QgsColorRampShader.ColorRampItem(elevation, QColor(r, g, b))
            )

    else:

        span = max(max_elevation - min_elevation, 1e-6)

        for fraction, (r, g, b) in LAND_RAMP:

            elevation = min_elevation + fraction * span

            items.append(
                QgsColorRampShader.ColorRampItem(elevation, QColor(r, g, b))
            )

    items.sort(
        key=lambda item: item.value
    )

    return items


def _apply_raster_style(raster_layer, opacity):

    """
    A single-band pseudocolor renderer driven by a linearly-
    interpolated hypsometric colour ramp built from this raster's own
    elevation range.
    """

    min_elevation, max_elevation = _band_min_max(raster_layer)

    color_ramp_shader = QgsColorRampShader()

    color_ramp_shader.setColorRampType(
        QgsColorRampShader.Type.Linear
    )

    color_ramp_shader.setColorRampItemList(
        _build_color_ramp_items(min_elevation, max_elevation)
    )

    shader = QgsRasterShader()

    shader.setRasterShaderFunction(
        color_ramp_shader
    )

    renderer = QgsSingleBandPseudoColorRenderer(
        raster_layer.dataProvider(),
        1,
        shader
    )

    raster_layer.setRenderer(
        renderer
    )

    raster_layer.setOpacity(
        opacity
    )

    raster_layer.triggerRepaint()


def generate_hypsometric_tint(
    dem_layer,
    extent,
    extent_crs,
    opacity=DEFAULT_OPACITY
):

    """
    Build a hypsometric tint raster layer from dem_layer, clipped to
    extent and coloured by elevation per the standard hypsometric
    convention (see _hypsometric_ramp.py). Added to the current
    project at the bottom of the layer tree - not the default
    top-of-stack position an unqualified addMapLayer() would use - so
    it never covers Tanaka Contours or other vector layers already in
    the project. Returns the layer.
    """

    clipped_dem = clip_and_reproject_dem(
        dem_layer,
        extent,
        extent_crs
    )

    clipped_dem.setName(
        OUTPUT_LAYER_NAME
    )

    _apply_raster_style(
        clipped_dem,
        opacity
    )

    project = QgsProject.instance()

    project.addMapLayer(
        clipped_dem,
        False
    )

    root = project.layerTreeRoot()

    root.insertLayer(
        len(root.children()),
        clipped_dem
    )

    return clipped_dem
