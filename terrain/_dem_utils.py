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


def clip_and_reproject_dem(dem_layer, extent, extent_crs):

    """
    Clip dem_layer to extent (given in extent_crs) and reproject it
    to the local UTM zone for that extent's centre, in one
    gdal:warpreproject call. Downstream elevation/geometry math needs
    a projected, metric CRS - the source DEM may well be geographic
    (confirmed true for real SRTM-style data).
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
            "OUTPUT": QgsProcessing.TEMPORARY_OUTPUT
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "clipped_dem"
    )


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
