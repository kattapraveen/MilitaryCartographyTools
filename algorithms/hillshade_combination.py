# -*- coding: utf-8 -*-

"""
Hillshade Combinations as a Processing algorithm.

A thin front end: terrain/hillshade_combination.py stays the single
source of truth for the blend and the Overlay rendering, and this
module only exposes it to Processing. It was a plain dialog until
2026-10-26 - see algorithms/contours.py for why all four terrain
tools moved.

Military Cartography Tools
"""

from qgis.core import (
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterRasterDestination,
)

from ..terrain.hillshade_combination import (
    DEFAULT_ALTITUDE,
    DEFAULT_OPACITY,
    DEFAULT_Z_FACTOR,
    OUTPUT_LAYER_NAME,
    THREE_DIRECTION_AZIMUTHS,
    TWO_DIRECTION_AZIMUTHS,
    _apply_raster_style,
    default_insert_position,
    generate_hillshade_combination,
)
from ._raster_output import write_raster_to_destination
from ._replace_in_place import StyleAndReplacePostProcessor
from ._terrain_base import TerrainAlgorithm


# Label and azimuths, in the dialog's own order.
PRESETS = (
    ("Two-direction (NW 315° + NE 45°)", TWO_DIRECTION_AZIMUTHS),
    (
        "Three-direction (NW 315° + NE 45° + S 180°)",
        THREE_DIRECTION_AZIMUTHS,
    ),
)

PRESET_LABELS = [label for label, _ in PRESETS]

DEFAULT_PRESET_INDEX = 1


class HillshadeCombinationAlgorithm(TerrainAlgorithm):

    PRESET = "PRESET"
    ALTITUDE = "ALTITUDE"
    Z_FACTOR = "Z_FACTOR"
    OPACITY = "OPACITY"

    OUTPUT_LAYER_NAME = OUTPUT_LAYER_NAME

    def name(self):
        return "hillshadecombination"

    def displayName(self):
        return "Hillshade Combinations"

    def createInstance(self):
        return HillshadeCombinationAlgorithm()

    def shortHelpString(self):
        return (
            "Shades the terrain from two or three light directions "
            "at once and averages the results. A single light leaves "
            "whole slopes facing away from it flat and unreadable; "
            "lighting from several directions lifts those out "
            "without washing the relief away.\n\n"
            "Rendered grayscale with an Overlay blend, so it is "
            "meant to sit over something - Hypsometric Tint, or the "
            "map itself. Overlay darkens shadowed slopes and "
            "lightens sunlit ones against whatever is beneath, "
            "rather than dragging it all darker the way Multiply "
            "does.\n\n"
            "The grey values are not stretched. Flat ground sits at "
            "its true mid-grey, so open water reads as flat rather "
            "than black."
        )

    def initAlgorithm(self, config=None):

        self.addCommonParameters()

        self.addParameter(
            QgsProcessingParameterEnum(
                self.PRESET,
                "Light directions",
                options=PRESET_LABELS,
                defaultValue=DEFAULT_PRESET_INDEX,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.ALTITUDE,
                "Light altitude in degrees above the horizon",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_ALTITUDE,
                minValue=0.0,
                maxValue=90.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.Z_FACTOR,
                "Vertical exaggeration",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_Z_FACTOR,
                minValue=0.01,
                maxValue=100.0,
            )
        )

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

        self.addReplaceParameter()

        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT,
                OUTPUT_LAYER_NAME,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        dem, extent, extent_crs = self.demAndExtent(parameters, context)

        preset_index = self.parameterAsEnum(
            parameters, self.PRESET, context
        )

        try:
            azimuths = PRESETS[preset_index][1]

        except IndexError:
            # An index out of a model saved against a shorter list.
            azimuths = PRESETS[DEFAULT_PRESET_INDEX][1]

        altitude = self.parameterAsDouble(
            parameters, self.ALTITUDE, context
        )

        z_factor = self.parameterAsDouble(
            parameters, self.Z_FACTOR, context
        )

        opacity = self.parameterAsInt(
            parameters, self.OPACITY, context
        ) / 100.0

        feedback.pushInfo(
            "Shading from "
            + ", ".join(f"{azimuth:g}°" for azimuth in azimuths)
            + f" at {altitude:g}° altitude."
        )

        feedback.setProgress(10)

        combined = self.generate(
            generate_hillshade_combination,
            dem,
            extent,
            extent_crs,
            azimuths=azimuths,
            altitude=altitude,
            z_factor=z_factor,
            opacity=opacity,
            feedback=feedback,
            context=context,
        )

        if self.cancelledOrMissing(combined, feedback):
            return {}

        feedback.setProgress(70)

        destination = self.parameterAsOutputLayer(
            parameters, self.OUTPUT, context
        )

        written = write_raster_to_destination(
            combined, destination, feedback=feedback,
            context=context
        )

        if feedback.isCanceled():
            return {}

        feedback.setProgress(100)

        if context.willLoadLayerOnCompletion(written):

            replace = self.parameterAsBoolean(
                parameters, self.REPLACE, context
            )

            def style(loaded):

                # A raster file carries no renderer, and the Overlay
                # blend mode is the whole point of this layer, so it
                # has to be set again on the written raster.
                _apply_raster_style(loaded, opacity)

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
