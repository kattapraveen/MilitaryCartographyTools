# -*- coding: utf-8 -*-

"""
Tanaka (illuminated) Contours as a Processing algorithm.

A thin front end: terrain/tanaka_contours.py stays the single source
of truth for the illumination maths, the styling and the two size
guards, and this module only exposes it to Processing. It was a plain
dialog until 2026-10-26 - see algorithms/contours.py for why all four
terrain tools moved.

Of the four this is the one that needed it most. A Tanaka run splits
every contour into segments and samples the DEM twice per segment, so
it is the slowest tool in the plugin by a wide margin and the one a
maintainer is most likely to think has hung. It now reports its stage
and can be cancelled.

Military Cartography Tools
"""

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingParameterEnum,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
)

from ..terrain.tanaka_contours import (
    DEFAULT_INTERVAL,
    DEFAULT_LIGHT_AZIMUTH,
    DEFAULT_MAX_WIDTH_MM,
    DEFAULT_MIN_WIDTH_MM,
    DEFAULT_SEGMENT_LENGTH,
    DEFAULT_STYLE_MODE,
    OUTPUT_LAYER_NAME,
    STYLE_ELEVATION_COLOR,
    STYLE_ILLUMINATED_OVERLAY,
    STYLE_MONOCHROME,
    _apply_style,
    default_insert_position,
    generate_tanaka_contours,
)
from ..terrain.hypsometric_tint import (
    OUTPUT_LAYER_NAME as HYPSOMETRIC_TINT_LAYER_NAME,
)
from ._replace_in_place import StyleAndReplacePostProcessor
from ._terrain_base import TerrainAlgorithm


# Label and stored value, in the dialog's own order so a maintainer
# reads the same list in the same sequence.
STYLE_MODES = (
    ("Elevation colour", STYLE_ELEVATION_COLOR),
    ("Monochrome (grayscale by illumination)", STYLE_MONOCHROME),
    (
        "Illuminated overlay (use with Hypsometric Tint)",
        STYLE_ILLUMINATED_OVERLAY,
    ),
)

STYLE_MODE_LABELS = [label for label, _ in STYLE_MODES]

DEFAULT_STYLE_INDEX = [
    mode for _, mode in STYLE_MODES
].index(DEFAULT_STYLE_MODE)


class TanakaContoursAlgorithm(TerrainAlgorithm):

    INTERVAL = "INTERVAL"
    SEGMENT_LENGTH = "SEGMENT_LENGTH"
    AZIMUTH = "AZIMUTH"
    MIN_WIDTH = "MIN_WIDTH"
    MAX_WIDTH = "MAX_WIDTH"
    STYLE_MODE = "STYLE_MODE"

    OUTPUT_LAYER_NAME = OUTPUT_LAYER_NAME

    def name(self):
        return "tanakacontours"

    def displayName(self):
        return "Tanaka Contours"

    def createInstance(self):
        return TanakaContoursAlgorithm()

    def shortHelpString(self):
        return (
            "Illuminated contours: line width varies with how each "
            "stretch of contour lies to the light, so slopes facing "
            "it and slopes in its shadow both draw heavy and slopes "
            "grazing it draw fine. The hill shape reads off the "
            "lines themselves, with no hillshade underneath.\n\n"
            "A map-sheet technique, not a country one. Every contour "
            "is split into segments and the DEM is sampled twice per "
            "segment, so the work grows with area, with relief and "
            "with the inverse of both the interval and the segment "
            "length. For anything larger than a sheet use Contours "
            "instead.\n\n"
            "If it refuses, it will say how far to raise the "
            "interval."
        )

    def initAlgorithm(self, config=None):

        self.addCommonParameters()

        self.addParameter(
            QgsProcessingParameterNumber(
                self.INTERVAL,
                "Contour interval in metres",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_INTERVAL,
                minValue=0.1,
                maxValue=10000.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SEGMENT_LENGTH,
                "Segment length in metres",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_SEGMENT_LENGTH,
                minValue=1.0,
                maxValue=100000.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.AZIMUTH,
                "Light azimuth in degrees",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_LIGHT_AZIMUTH,
                minValue=0.0,
                maxValue=360.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MIN_WIDTH,
                "Min line width in mm (perpendicular to light)",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_MIN_WIDTH_MM,
                minValue=0.01,
                maxValue=10.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MAX_WIDTH,
                "Max line width in mm (facing toward/away from light)",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=DEFAULT_MAX_WIDTH_MM,
                minValue=0.01,
                maxValue=10.0,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.STYLE_MODE,
                "Style",
                options=STYLE_MODE_LABELS,
                defaultValue=DEFAULT_STYLE_INDEX,
            )
        )

        self.addReplaceParameter()

        self.addParameter(
            QgsProcessingParameterVectorDestination(
                self.OUTPUT,
                OUTPUT_LAYER_NAME,
                type=QgsProcessing.SourceType.TypeVectorLine,
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        dem, extent, extent_crs = self.demAndExtent(parameters, context)

        interval = self.parameterAsDouble(
            parameters, self.INTERVAL, context
        )

        segment_length = self.parameterAsDouble(
            parameters, self.SEGMENT_LENGTH, context
        )

        azimuth = self.parameterAsDouble(
            parameters, self.AZIMUTH, context
        )

        min_width = self.parameterAsDouble(
            parameters, self.MIN_WIDTH, context
        )

        max_width = self.parameterAsDouble(
            parameters, self.MAX_WIDTH, context
        )

        style_index = self.parameterAsEnum(
            parameters, self.STYLE_MODE, context
        )

        try:
            style_mode = STYLE_MODES[style_index][1]

        except IndexError:
            # An index out of a model saved against a shorter list.
            style_mode = DEFAULT_STYLE_MODE

        # context.project(), never QgsProject.instance(): this method
        # runs on a background thread (the dialog hands it to
        # QgsProcessingAlgRunnerTask, since this algorithm does not
        # set FlagNoThreading), and the project's layer registry
        # belongs to the GUI thread, which may be adding or removing
        # a layer while this reads it. A context with no project at
        # all - possible from a script - is left alone rather than
        # warned about: there is nothing to look in, so there is
        # nothing truthful to say.
        project = context.project()

        if (
            style_mode == STYLE_ILLUMINATED_OVERLAY
            and project is not None
            and not project.mapLayersByName(HYPSOMETRIC_TINT_LAYER_NAME)
        ):

            # Non-blocking, exactly as the dialog had it - the layer
            # is still useful (a Hypsometric Tint might get added
            # afterwards), this mode just needs one for the result to
            # look like anything other than near-invisible lines on a
            # blank canvas.
            feedback.pushWarning(
                "Illuminated overlay mode is meant to be used "
                "together with a Hypsometric Tint layer - without "
                "one, lit segments will look nearly invisible."
            )

        feedback.pushInfo(
            f"Contouring at {interval:g} m, splitting into "
            f"{segment_length:g} m segments, light from {azimuth:g}°."
        )

        feedback.pushInfo(
            "Sampling the DEM twice per segment - this is the slow "
            "part."
        )

        feedback.setProgress(10)

        layer = self.generate(
            generate_tanaka_contours,
            dem,
            extent,
            extent_crs,
            interval=interval,
            segment_length=segment_length,
            light_azimuth_deg=azimuth,
            min_width_mm=min_width,
            max_width_mm=max_width,
            style_mode=style_mode,
            feedback=feedback,
            context=context,
        )

        if self.cancelledOrMissing(layer, feedback):
            return {}

        feedback.setProgress(80)

        feedback.pushInfo(f"{layer.featureCount():,} illuminated segments.")

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            layer.fields(),
            layer.wkbType(),
            layer.crs(),
        )

        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT)
            )

        for feature in layer.getFeatures():

            if feedback.isCanceled():
                return {}

            sink.addFeature(feature, QgsFeatureSink.FastInsert)

        feedback.setProgress(100)

        if context.willLoadLayerOnCompletion(dest_id):

            replace = self.parameterAsBoolean(
                parameters, self.REPLACE, context
            )

            def style(loaded):

                # Width and colour are both data-defined off fields
                # the sink carried over, so the style re-applies to
                # the written layer exactly as it did to the one the
                # generator built.
                _apply_style(
                    loaded,
                    min_width,
                    max_width,
                    style_mode=style_mode,
                )

            details = context.layerToLoadOnCompletionDetails(dest_id)

            details.name = OUTPUT_LAYER_NAME

            details.setPostProcessor(
                StyleAndReplacePostProcessor.create(
                    OUTPUT_LAYER_NAME,
                    style,
                    replace,
                    default_insert_position,
                )
            )

        return {self.OUTPUT: dest_id}
