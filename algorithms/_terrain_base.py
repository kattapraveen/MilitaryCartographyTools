# -*- coding: utf-8 -*-

"""
What the four terrain algorithms share.

All four start the same way: a DEM, an extent that means the whole
DEM when left empty, and a "replace the existing layer" switch. All
four end the same way too - the generator in terrain/ raises
ValueError with a message written for the user, and that has to reach
Processing as a QgsProcessingException rather than escaping as a
traceback in QGIS's Python error dialog. That mistake was made once
already, on 2026-10-21, when a considered refusal reached the
maintainer as a stack trace.

Military Cartography Tools
"""

from qgis.core import (
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterExtent,
    QgsProcessingParameterRasterLayer,
)


class TerrainAlgorithm(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    EXTENT = "EXTENT"
    REPLACE = "REPLACE"
    OUTPUT = "OUTPUT"

    # Set by each subclass: the name the dialog version gave its
    # output, which the replace switch is keyed on.
    OUTPUT_LAYER_NAME = None

    def group(self):
        return "Terrain"

    def groupId(self):
        return "terrain"

    def addCommonParameters(self):

        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT,
                "DEM layer",
            )
        )

        self.addParameter(
            QgsProcessingParameterExtent(
                self.EXTENT,
                "Extent (leave empty for the whole DEM)",
                optional=True,
            )
        )

    def addReplaceParameter(self):

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.REPLACE,
                f"Replace any existing \"{self.OUTPUT_LAYER_NAME}\" layer",
                defaultValue=True,
            )
        )

    def demAndExtent(self, parameters, context):

        """
        The DEM, and the extent to clip it to in the DEM's own CRS.
        An empty extent parameter means the whole DEM, matching what
        the dialogs defaulted to and what every caller before them
        expected.
        """

        dem = self.parameterAsRasterLayer(parameters, self.INPUT, context)

        if dem is None:
            raise QgsProcessingException(
                self.invalidRasterError(parameters, self.INPUT)
            )

        extent = self.parameterAsExtent(
            parameters, self.EXTENT, context, dem.crs()
        )

        if extent is None or extent.isEmpty():
            extent = dem.extent()

        return dem, extent, dem.crs()

    def generate(self, generator, *args, **kwargs):

        """
        Run a terrain/ generator, translating its considered refusals
        into something Processing can show.

        The raise is deliberately OUTSIDE the except block, and that
        is not a style choice. Raising from inside it chains the
        original ValueError on as __context__ - `from None` does not
        prevent that, it only sets __cause__ - and the chained
        exception keeps its own traceback, whose frames still hold
        the clipped DEM and the contour layer the generator had built
        before it refused. Those are GDAL-backed layers. Anything
        still holding one when QGIS shuts its GDAL providers down
        segfaults in GDALClose, which is exactly what QGIS 3.44 did
        here on 2026-10-26: the whole suite reported OK and the
        process then died on the way out. Taking the message and
        leaving the handler first drops the chain with it.
        """

        try:
            return generator(*args, **kwargs)

        except ValueError as refusal:
            message = str(refusal)

        raise QgsProcessingException(message)

    def cancelledOrMissing(self, produced, feedback):

        """
        True when the run should stop without an error.

        A generator returns None when it saw the cancellation first -
        see terrain/_progress.py for why a cancellation is a None
        rather than a raise. Both conditions are checked together so
        no caller can test one and forget the other and then
        dereference None.
        """

        return produced is None or feedback.isCanceled()
