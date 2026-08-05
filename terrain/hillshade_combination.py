# -*- coding: utf-8 -*-

"""
Hillshade combinations - a multi-directional relief shading raster,
blending 2-3 light azimuths into one layer. QGIS/GDAL's own hillshade
tools (gdal:hillshade, the raster "Hillshade" render type) only cast
light from a single direction; GDAL's own -multidirectional flag uses
a fixed, non-user-configurable light set and ignores the azimuth
parameter entirely when enabled. Meant to be layered (with an Overlay
blend, applied automatically here) over Hypsometric Tint for a fuller,
textured relief look - see docs/roadmap.md's own note on doing this
combination by hand with QGIS's native tools; this feature automates
it for a multi-directional blend instead of a single light direction.

Military Cartography Tools
"""

import tempfile

import processing

from qgis.core import (
    QgsContrastEnhancement,
    QgsRasterLayer,
    QgsSingleBandGrayRenderer,
)

from qgis.PyQt.QtGui import QPainter

from ._dem_utils import clip_and_reproject_dem
from .hypsometric_tint import OUTPUT_LAYER_NAME as HYPSOMETRIC_TINT_LAYER_NAME


OUTPUT_LAYER_NAME = "Combined Hillshade"

DEFAULT_ALTITUDE = 45.0
DEFAULT_Z_FACTOR = 1.0
DEFAULT_OPACITY = 1.0

# 315 degrees (north-west) matches tanaka_contours.DEFAULT_LIGHT_AZIMUTH's
# own convention, so a hillshade generated here reads consistently
# alongside a Tanaka Contours layer.
TWO_DIRECTION_AZIMUTHS = (315.0, 45.0)
THREE_DIRECTION_AZIMUTHS = (315.0, 45.0, 180.0)

DEFAULT_AZIMUTHS = THREE_DIRECTION_AZIMUTHS


def _run_hillshade(dem_layer, azimuth_deg, altitude_deg, z_factor):

    """
    A single-direction gdal:hillshade run against dem_layer, one band,
    Byte output (0-255). COMPUTE_EDGES=True fills in the outermost
    pixel ring instead of leaving it NoData - without it, averaging
    several of these together in _combine_hillshades() would bake an
    unmasked NoData border into a visible dark ring around this
    plugin's typically tight DEM clips.
    """

    result = processing.run(
        "gdal:hillshade",
        {
            "INPUT": dem_layer,
            "BAND": 1,
            "Z_FACTOR": z_factor,
            "SCALE": 1.0,
            "AZIMUTH": azimuth_deg,
            "ALTITUDE": altitude_deg,
            "COMPUTE_EDGES": True,
            "ZEVENBERGEN": False,
            "COMBINED": False,
            "MULTIDIRECTIONAL": False,
            "OPTIONS": "",
            "EXTRA": None,
            "OUTPUT": tempfile.mktemp(suffix=".tif")
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        f"hillshade_{azimuth_deg:g}"
    )


def _combine_hillshades(hillshade_layers):

    """
    Average 2 or 3 single-direction hillshade rasters, pixel by pixel,
    via gdal:rastercalculator. The final average is always back in
    0-255 range, but gdal:rastercalculator evaluates the FORMULA using
    each input's own on-disk dtype (Byte/uint8 for a gdal:hillshade
    output) - confirmed live: "(A+B+C)/3" silently overflowed the
    intermediate SUM before the division ever happened (e.g.
    174+184+182=540 wraps to 28 in 8-bit arithmetic, then /3 rounds to
    9), producing near-black garbage for ordinary mid-gray hillshade
    values instead of their real ~180 average. Casting each operand to
    float32 in the formula itself forces the addition to happen at
    full precision before the divide; RTYPE stays Byte (index 0) since
    the final divided value is safely back in 0-255 range.
    """

    count = len(hillshade_layers)

    if count not in (2, 3):

        raise ValueError(
            f"_combine_hillshades() needs 2 or 3 hillshade layers, got {count}"
        )

    params = {
        "INPUT_A": hillshade_layers[0],
        "BAND_A": 1,
        "INPUT_B": hillshade_layers[1],
        "BAND_B": 1,
        "NO_DATA": None,
        "RTYPE": 0,
        "OPTIONS": "",
        "EXTRA": None,
        "OUTPUT": tempfile.mktemp(suffix=".tif")
    }

    if count == 2:

        params["FORMULA"] = (
            "(A.astype(numpy.float32)+B.astype(numpy.float32))/2"
        )

    else:

        params["INPUT_C"] = hillshade_layers[2]
        params["BAND_C"] = 1
        params["FORMULA"] = (
            "(A.astype(numpy.float32)+B.astype(numpy.float32)"
            "+C.astype(numpy.float32))/3"
        )

    result = processing.run(
        "gdal:rastercalculator",
        params
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "combined_hillshade"
    )


def _apply_raster_style(raster_layer, opacity):

    """
    Plain grayscale rendering (no elevation semantics here, unlike
    Hypsometric Tint's colour ramp) at the raw 0-255 hillshade values -
    deliberately NOT a per-generation min/max stretch. Unlike
    elevation, a hillshade's 0-255 scale is already meaningful on an
    absolute basis (flat ground legitimately sits around a fixed
    mid-gray for a given light altitude); stretching whatever narrow
    range happens to be present in one generation crushes a genuinely
    low-relief area (e.g. open water) down toward black instead of
    showing it as the neutral flat value it actually is - confirmed
    live: a near-flat area came out almost solid black once "Stretch
    to MinMax" amplified its tiny real variance across the full
    range, and Multiply blend then dragged everything beneath it dark
    too.

    Blend mode is Overlay, not Multiply - confirmed live against a
    real DEM (Kilimanjaro, Tanzania SRTM) layered over Hypsometric
    Tint: Multiply can only ever darken, so it dragged the whole
    mid/high elevation band toward a muddy, desaturated brown-purple
    that didn't read as the source ramp's own colours any more.
    Overlay instead darkens shadowed slopes and lightens sunlit ones
    relative to each pixel's own colour, which visibly preserved the
    tint's own hue far better in that same comparison, at the cost of
    being a less mathematically simple relationship than Multiply's
    - an accepted trade-off since the visual result is what matters
    here.
    """

    renderer = QgsSingleBandGrayRenderer(
        raster_layer.dataProvider(),
        1
    )

    raster_layer.setRenderer(
        renderer
    )

    raster_layer.setContrastEnhancement(
        QgsContrastEnhancement.ContrastEnhancementAlgorithm.NoEnhancement
    )

    raster_layer.setBlendMode(
        QPainter.CompositionMode.CompositionMode_Overlay
    )

    raster_layer.setOpacity(
        opacity
    )

    raster_layer.triggerRepaint()


def default_insert_position(project, raster_layer):

    """
    Combined Hillshade's own default placement for a brand new layer -
    directly above (in front of) an existing "Hypsometric Tint" layer,
    if one exists, so the Overlay blend set in _apply_raster_style()
    actually combines with it - otherwise fall back to the same
    bottom-of-tree default generate_hypsometric_tint() itself uses, so
    this layer still never covers vector layers like Tanaka Contours
    or the grids. Only used when there's no previous layer's position
    to inherit (see terrain/_layer_utils.py's replace_named_layer()) -
    deliberately doesn't retroactively reposition this layer above a
    Hypsometric Tint layer added *after* it already exists, consistent
    with never overriding a position the user may have organised
    manually.
    """

    root = project.layerTreeRoot()

    tint_layers = project.mapLayersByName(
        HYPSOMETRIC_TINT_LAYER_NAME
    )

    if tint_layers:

        tint_node = root.findLayer(
            tint_layers[0].id()
        )

        parent = tint_node.parent()

        index = parent.children().index(tint_node)

        parent.insertLayer(
            index,
            raster_layer
        )

    else:

        root.insertLayer(
            len(root.children()),
            raster_layer
        )


def generate_hillshade_combination(
    dem_layer,
    extent,
    extent_crs,
    azimuths=DEFAULT_AZIMUTHS,
    altitude=DEFAULT_ALTITUDE,
    z_factor=DEFAULT_Z_FACTOR,
    opacity=DEFAULT_OPACITY
):

    """
    Build a multi-directional hillshade blend from dem_layer, clipped
    to extent, by running gdal:hillshade once per azimuth in azimuths
    (2 or 3) and averaging the results. Rendered single-band grayscale
    with an Overlay blend mode. Deliberately does NOT add the layer to
    the project - see terrain/_layer_utils.py's module docstring for
    why. Returns the layer.
    """

    clipped_dem = clip_and_reproject_dem(
        dem_layer,
        extent,
        extent_crs
    )

    hillshade_layers = [
        _run_hillshade(clipped_dem, azimuth, altitude, z_factor)
        for azimuth in azimuths
    ]

    combined = _combine_hillshades(
        hillshade_layers
    )

    combined.setName(
        OUTPUT_LAYER_NAME
    )

    _apply_raster_style(
        combined,
        opacity
    )

    return combined
