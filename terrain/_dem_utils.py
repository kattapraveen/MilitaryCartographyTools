# -*- coding: utf-8 -*-

"""
Shared DEM helpers for the terrain/ generators (Tanaka contours,
hypsometric tint) - both need the same source DEM clipped to the
current extent and reprojected to a local metric CRS, and both need
that same clipped DEM's own elevation range so their colour ramps
agree on what colour a given elevation gets.

Military Cartography Tools
"""

import processing

from qgis.core import (
    Qgis,
    QgsCoordinateTransform,
    QgsProcessing,
    QgsProject,
    QgsRasterLayer,
)

from ..core.coordinate_utils import WGS84, get_utm_crs


def transform_context(context):

    """
    The coordinate transform context to build a QgsCoordinateTransform
    against, taken from a QgsProcessingContext when there is one.

    This exists because of where these generators are now called
    from. A Processing algorithm runs on a BACKGROUND thread - none
    of the four terrain algorithms overrides flags(), so the dialog
    hands them to QgsProcessingAlgRunnerTask - and
    `QgsProject.instance()` belongs to the GUI thread. Reading it
    from the worker while the GUI thread is adding or removing a
    layer is an unsynchronised read of a main-thread object. Until
    2026-10-26 these generators were only ever called from modal
    dialogs on the GUI thread, so the call was safe; the conversion
    to algorithms changed the threading without changing the call.

    Line of Sight, Viewshed and Sensor Coverage still call them from
    the main thread with no context at all, which is why the fallback
    stays - and why this cannot simply be swapped for
    context.transformContext() at the call site.
    """

    if context is not None:
        return context.transformContext()

    return QgsProject.instance().transformContext()


def clip_and_reproject_dem(
    dem_layer, extent, extent_crs, feedback=None, context=None
):

    """
    Clip dem_layer to extent (given in extent_crs) and reproject it
    to the local UTM zone for that extent's centre, in one
    gdal:warpreproject call. Downstream elevation/geometry math needs
    a projected, metric CRS - the source DEM may well be geographic
    (confirmed true for real SRTM-style data).

    Raises ValueError if the warp produces nothing readable. Six
    features clip through here (Tanaka Contours, Hypsometric Tint,
    Hillshade Combinations, Line of Sight and Viewshed twice), and an
    invalid raster returned silently does not fail where it was made -
    it fails somewhere downstream under a message naming neither this
    step nor the DEM. That cost real time on 2026-10-20: a Tanaka run
    surfaced as "Could not create memory layer" raised by
    native:splitlinesbylength, two calls further on, because an
    invalid layer reports wkbType() == Unknown and the sink built from
    it cannot be created. See docs/roadmap.md's own 2026-10-20 entry.

    `feedback` is optional and is handed to gdal:warpreproject so the
    warp - often the longest single step in a terrain run - can be
    cancelled and can report progress. See terrain/_progress.py.

    `context` is optional too, and for a different reason: a
    Processing algorithm runs this on a background thread, where both
    the transform context and the child algorithm's own context have
    to come from the caller rather than off QgsProject.instance().
    See transform_context() above.
    """

    transform_to_wgs84 = QgsCoordinateTransform(
        extent_crs,
        WGS84,
        transform_context(context)
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
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        },
        feedback=feedback,
        context=context
    )

    clipped = QgsRasterLayer(
        result["OUTPUT"],
        "clipped_dem"
    )

    if not clipped.isValid():

        raise ValueError(
            "Could not clip and reproject the DEM "
            f"'{dem_layer.name()}': gdal:warpreproject produced no "
            f"readable raster at {result['OUTPUT']}. The source DEM "
            "may be unreadable, outside the requested extent, or in a "
            "format GDAL cannot warp from here - a raster stored "
            "inside a GeoPackage is one known case."
        )

    return clipped


def band_min_max(raster_layer, band=1):

    """
    (minimum, maximum) pixel value for one band of raster_layer - the
    single source of truth both Tanaka contours and hypsometric tint
    normalise their colour ramp against, so the same elevation gets
    the same colour in both when generated over the same DEM/extent.
    Previously Tanaka normalised against the elevation range of its
    own *drawn contour lines* instead (quantised to the contour
    interval, so it rarely reached the DEM's true min/max) while
    hypsometric tint used the raw pixel range - a real mismatch,
    confirmed live by the two disagreeing over an identical area.

    **The DeprecationWarning this logs is deliberate, and the obvious
    fix for it is a pessimisation.** QgsRasterDataProvider.
    bandStatistics() logs "QgsRasterInterface.bandStatistics() is
    deprecated: Since 3.40. Use Qgis.RasterBandStatistic instead of int
    for `stats`" whenever a `stats` argument is passed AT ALL - including
    the very enum the message asks for. Re-probed 2026-08-21 on QGIS
    4.2.1, all four forms returning identical, correct values:

        Min | Max (this call)              warns
        Qgis.RasterBandStatistics(Min|Max) warns
        Qgis.RasterBandStatistic.All       warns
        plain int                          warns
        NO stats argument                  silent

    So the warning is not about the argument's type; passing one at all
    selects the deprecated overload. Omitting it is the only way to
    silence it, and that is why the argument stays: with no argument
    QGIS computes the whole statistics set (mean, standard deviation)
    rather than just the two values wanted here. Measured on a virgin
    16-megapixel raster with no cached .aux.xml sidecar, both orders:
    0.058 s with Min|Max against 0.224 s without it, roughly four times
    the work, once per Tanaka Contours or Hypsometric Tint run.

    A logged line of noise is worth less than that, so the argument
    stays and the warning is accepted. Do not "fix" it by dropping the
    argument without re-measuring first (see
    docs/developer-guide.md).
    """

    provider = raster_layer.dataProvider()

    stats = provider.bandStatistics(
        band,
        Qgis.RasterBandStatistic.Min | Qgis.RasterBandStatistic.Max
    )

    return stats.minimumValue, stats.maximumValue
