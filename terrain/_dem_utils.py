# -*- coding: utf-8 -*-

"""
Shared DEM clip/reproject helper for the terrain/ generators
(Tanaka contours, hypsometric tint) - both need the same source DEM
clipped to the current extent and reprojected to a local metric CRS
before doing any further elevation math.

Military Cartography Tools
"""

import tempfile

import processing

from qgis.core import (
    QgsCoordinateTransform,
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
            "OUTPUT": tempfile.mktemp(suffix=".tif")
        }
    )

    return QgsRasterLayer(
        result["OUTPUT"],
        "clipped_dem"
    )
