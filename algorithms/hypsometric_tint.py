# -*- coding: utf-8 -*-

"""
Hypsometric Tint as a Processing algorithm.

A thin front end: terrain/hypsometric_tint.py stays the single source
of truth for the colour ramp and the clipping, and this module only
exposes it to Processing. It was a plain dialog until 2026-10-26 -
see algorithms/contours.py for why all four terrain tools moved.

Military Cartography Tools
"""

from qgis.core import QgsProcessingParameterNumber, QgsProcessingParameterBoolean
from qgis.core import QgsProcessingParameterRasterDestination

from ..terrain.hypsometric_tint import (
    DEFAULT_OPACITY,
    OUTPUT_LAYER_NAME,
    _apply_raster_style,
    default_insert_position,
    generate_hypsometric_tint,
)
from ._raster_output import write_raster_to_destination
from ._replace_in_place import StyleAndReplacePostProcessor
from ._terrain_base import TerrainAlgorithm


class HypsometricTintAlgorithm(TerrainAlgorithm):

    OPACITY = "OPACITY"
    DISCRETE = "DISCRETE"

    OUTPUT_LAYER_NAME = OUTPUT_LAYER_NAME

    def name(self):
        return "hypsometrictint"

    def displayName(self):
        return "Hypsometric Tint"

    def createInstance(self):
        return HypsometricTintAlgorithm()

    def shortHelpString(self):
        return (
            "Fills the ground with colour by height, on the "
            "conventional hypsometric sequence - greens through "
            "yellows and browns to grey and white - stretched to the "
            "elevation range actually present in the extent.\n\n"
            "A smooth gradient by default. Switch on discrete bands "
            "for the stepped, layer-cake look most published "
            "hypsometric sheets use.\n\n"
            "Drop a Combined Hillshade over the top: that one "
            "renders with an Overlay blend, which keeps these hues "
            "rather than muddying them."
        )

    def initAlgorithm(self, config=None):

        self.addCommonParameters()

        self.addParameter(
            QgsProcessingParameterNumber(
                self.OPACITY,
                "Opacity in per cent",
                type=QgsProcessingParameterNumber.Type.Integer,
                defaultValue=int(DEFAULT_OPACITY * 100),
                minValue=0,
                maxValue=100,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.DISCRETE,
                "Hard-edged bands instead of a smooth gradient",
                defaultValue=False,
            )
        )

        self.addReplaceParameter()

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                OUTPUT_LAYER_NAME,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        dem, extent, extent_crs = self.demAndExtent(parameters, context)

        opacity = self.parameterAsInt(
            parameters, self.OPACITY, context
        ) / 100.0

        discrete = self.parameterAsBoolean(
            parameters, self.DISCRETE, context
        )

        feedback.pushInfo(
            "Clipping and reprojecting the DEM to its local UTM zone."
        )

        feedback.setProgress(10)

        tint = self.generate(
            generate_hypsometric_tint,
            dem,
            extent,
            extent_crs,
            opacity=opacity,
            discrete=discrete,
            feedback=feedback,
        )

        if self.cancelledOrMissing(tint, feedback):
            return {}

        feedback.setProgress(70)

        destination = self.parameterAsOutputLayer(
            parameters, self.OUTPUT, context
        )

        written = write_raster_to_destination(
            tint, destination, feedback=feedback
        )

        if feedback.isCanceled():
            return {}

        feedback.setProgress(100)

        if context.willLoadLayerOnCompletion(written):

            replace = self.parameterAsBoolean(
                parameters, self.REPLACE, context
            )

            def style(loaded):

                # A raster file carries no renderer, so the ramp is
                # rebuilt from the written raster's own band range -
                # the same data the generator read it from.
                _apply_raster_style(loaded, opacity, discrete=discrete)

            details = context.layerToLoadOnCompletionDetails(written)

            details.name = OUTPUT_LAYER_NAME

            details.setPostProcessor(
                StyleAndReplacePostProcessor.create(
                    OUTPUT_LAYER_NAME,
                    style,
                    replace,
                    default_insert_position,
                )
            )

        return {self.OUTPUT: written}
