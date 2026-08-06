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
    QgsGradientColorRamp,
    QgsGradientStop,
    QgsRasterMinMaxOrigin,
    QgsRasterShader,
    QgsSingleBandPseudoColorRenderer,
)

from qgis.PyQt.QtGui import QColor

from ._dem_utils import band_min_max, clip_and_reproject_dem
from ._hypsometric_ramp import LAND_RAMP, SEA_RAMP


OUTPUT_LAYER_NAME = "Hypsometric Tint"

DEFAULT_OPACITY = 1.0


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

    SEA_RAMP's own top stop and LAND_RAMP's own bottom stop both land
    on elevation 0 exactly - a genuine tie in the sorted item list.
    hypsometric_color() resolves elevation 0 unambiguously to LAND
    (its own `if elevation < 0` branch treats 0 as non-negative), but
    QgsColorRampShader's shade() resolves a tied value to whichever
    stop sorts first, which - confirmed live against a real DEM - is
    SEA_RAMP's blue, not LAND_RAMP's green, producing a real colour
    seam at every coastline where a raster pixel or Tanaka contour
    segment landed at exactly 0. Nudging SEA_RAMP's tied stop a
    hair below zero breaks the tie in LAND_RAMP's favour, matching
    hypsometric_color() exactly, with no visible effect on the
    gradient itself.
    """

    items = []

    if min_elevation < 0:

        for fraction, (r, g, b) in SEA_RAMP:

            elevation = fraction * min_elevation

            if elevation == 0.0:
                elevation = -1e-6

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


def _build_source_color_ramp(items):

    """
    A QgsGradientColorRamp mirroring items (already sorted,
    absolute-elevation-valued ColorRampItems) as a real, registered
    QgsColorRamp object - needed so QGIS's own Symbology UI recognises
    and preserves this ramp. Without a source ramp attached,
    QgsColorRampShader.setColorRampItemList() alone leaves the shader
    with no ramp QGIS's Properties dialog can identify - confirmed
    live: simply opening and closing Layer Properties (no edits made)
    silently replaced the hypsometric colours with QGIS's own default
    ramp, since its Symbology widget rebuilds the shader from whatever
    source ramp it finds (or a fallback default, if none) whenever the
    dialog is confirmed.
    """

    min_value = items[0].value
    max_value = items[-1].value

    span = max(max_value - min_value, 1e-9)

    stops = [
        QgsGradientStop((item.value - min_value) / span, item.color)
        for item in items[1:-1]
    ]

    return QgsGradientColorRamp(
        items[0].color,
        items[-1].color,
        False,
        stops
    )


def _apply_raster_style(raster_layer, opacity, discrete=False):

    """
    A single-band pseudocolor renderer driven by the hypsometric
    colour ramp built from this raster's own elevation range - a
    smooth gradient by default (Type.Linear), or hard-edged bands
    (Type.Discrete, using the same stops as class upper bounds) if
    discrete is True. Every "colourful Tanaka"/layer-tint reference
    reviewed for this plugin (Anita Graser's tutorial, Manifold's
    docs, the QGIS Hub style page, the GIS StackExchange "layer cake"
    thread, TopoToolbox, Evelyn Uuemaa's tutorial) uses stepped
    classification rather than a smooth gradient - discrete is opt-in
    rather than the default since the smooth gradient is the
    already-shipped, already-approved look.
    """

    min_elevation, max_elevation = band_min_max(raster_layer)

    items = _build_color_ramp_items(min_elevation, max_elevation)

    color_ramp_shader = QgsColorRampShader()

    color_ramp_shader.setColorRampType(
        QgsColorRampShader.Type.Discrete if discrete else QgsColorRampShader.Type.Linear
    )

    color_ramp_shader.setColorRampItemList(
        items
    )

    color_ramp_shader.setSourceColorRamp(
        _build_source_color_ramp(items)
    )

    # QgsColorRampShader()'s no-arg constructor leaves minimumValue()/
    # maximumValue() at their default 0.0/255.0 - confirmed live as
    # the real root cause of a colour-shift bug: the Layers panel's
    # legend read 0/255 (not this raster's real elevation range) for
    # a freshly generated layer, and setMinimumValue()/
    # setMaximumValue() also rebuild an internal shading lookup table
    # QGIS uses for continuous-mode rendering - left at the 0-255
    # default, real elevation values (e.g. -1252..275) fall almost
    # entirely outside that table's domain, visibly skewing the
    # rendered colours until something else (confirmed: opening and
    # closing Layer Properties) finally calls these setters with the
    # real range.
    color_ramp_shader.setMinimumValue(
        items[0].value
    )

    color_ramp_shader.setMaximumValue(
        items[-1].value
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

    # QgsRasterMinMaxOrigin()'s own default (limits=NotSet,
    # statAccuracy=Estimated - confirmed via a direct check of a
    # fresh instance) is what actually caused the colour-shift bug
    # setMinimumValue()/setMaximumValue() above didn't fully fix:
    # with limits left at NotSet, QGIS's own Symbology widget treats
    # nothing as pinned and, on load, recomputes its own min/max from
    # a fast SAMPLED estimate rather than trusting the exact values
    # this module already computed via band_min_max() - confirmed
    # live, the estimate came out narrower (missing the true peak
    # pixel) and visibly changed the rendered colours despite no user
    # edits. Pinning limits to MinimumMaximum with Exact/WholeRaster
    # tells QGIS these values already ARE the real whole-raster
    # min/max, so it has no reason to recompute them.
    min_max_origin = QgsRasterMinMaxOrigin()

    min_max_origin.setLimits(
        Qgis.RasterRangeLimit.MinimumMaximum
    )

    min_max_origin.setExtent(
        Qgis.RasterRangeExtent.WholeRaster
    )

    min_max_origin.setStatAccuracy(
        Qgis.RasterRangeAccuracy.Exact
    )

    renderer.setMinMaxOrigin(
        min_max_origin
    )

    raster_layer.setRenderer(
        renderer
    )

    raster_layer.setOpacity(
        opacity
    )

    raster_layer.triggerRepaint()


def default_insert_position(project, layer):

    """
    Hypsometric Tint's own default placement for a brand new layer -
    bottom of the tree, not the default top-of-stack position an
    unqualified addMapLayer() would use, so it never covers Tanaka
    Contours or other vector layers already in the project. Only used
    when there's no previous layer's position to inherit (see
    core/_layer_utils.py's replace_named_layer()).
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        len(root.children()),
        layer
    )


def generate_hypsometric_tint(
    dem_layer,
    extent,
    extent_crs,
    opacity=DEFAULT_OPACITY,
    discrete=False
):

    """
    Build a hypsometric tint raster layer from dem_layer, clipped to
    extent and coloured by elevation per the standard hypsometric
    convention (see _hypsometric_ramp.py) - a smooth gradient, or
    hard-edged discrete bands if discrete=True (see
    _apply_raster_style()'s own docstring). Deliberately does NOT add
    the layer to the project - see core/_layer_utils.py's module
    docstring for why. Returns the layer.
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
        opacity,
        discrete=discrete
    )

    return clipped_dem
