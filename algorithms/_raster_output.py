# -*- coding: utf-8 -*-

"""
Writing a generated raster out to a Processing destination.

The two raster terrain generators hand back a layer that is already
a file on disk - whatever gdal:warpreproject or the hillshade blend
left in Processing's own temporary folder. A Processing algorithm has
to put its result where the OUTPUT parameter says instead, which may
be a path the maintainer chose and expects to keep. gdal:translate
does the copy, and keeps the georeferencing and the band type that a
plain file copy would be trusted to keep but a reprojection would
not.

Military Cartography Tools
"""

import processing

from qgis.core import QgsProcessingException


def write_raster_to_destination(
    generated_layer, destination, feedback=None
):

    """
    Copy generated_layer to destination and return the path actually
    written. Styling is NOT carried over - a raster file holds no
    renderer, so the caller re-applies it in the post-processor.

    `feedback` is passed on so the copy can be cancelled and can
    report progress. It is not a trivial step: the user's own
    hypsometric run on 2026-11-02 wrote 2.25 GB here, and without
    this the Cancel button did nothing for the whole of it.
    """

    result = processing.run(
        "gdal:translate",
        {
            "INPUT": generated_layer,
            "TARGET_CRS": None,
            "NODATA": None,
            "COPY_SUBDATASETS": False,
            "OPTIONS": "",
            "EXTRA": "",
            "DATA_TYPE": 0,
            "OUTPUT": destination,
        },
        feedback=feedback
    )

    written = result.get("OUTPUT")

    if not written:
        raise QgsProcessingException(
            "gdal:translate wrote nothing to "
            f"{destination}. The raster was generated but could not "
            "be saved there - check the folder exists and is "
            "writable."
        )

    return written
