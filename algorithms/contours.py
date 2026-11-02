# -*- coding: utf-8 -*-

"""
Contours as a Processing algorithm.

A thin front end: terrain/contours.py stays the single source of
truth for the geometry, the styling and the guards, and this module
only exposes it to Processing. It was a plain dialog until
2026-10-26; moving it here is task 7's option C, taken because being
an algorithm brings three things for nothing -

  - a progress bar and a working Cancel, which was the whole
    complaint ("the user is kept wondering if the plugin will work or
    not");
  - Run as Batch, and usability inside a model;
  - a NON-modal dialog, which makes "Draw on Canvas" work on the
    extent parameter. It could never work from the old dialog, which
    used exec() and so blocked input to the main window.

Replace-in-place is preserved through the post-processor - see
_replace_in_place.py for why that mattered enough to carry over.

Military Cartography Tools
"""

from qgis.core import (
    QgsFeatureSink,
    QgsProcessing,
    QgsProcessingException,
    QgsProcessingParameterColor,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
)

from qgis.PyQt.QtGui import QColor

from ..terrain.contours import (
    DEFAULT_COLOUR,
    DEFAULT_INDEX_EVERY,
    DEFAULT_INTERVAL,
    OUTPUT_LAYER_NAME,
    _build_labeling,
    _build_renderer,
    default_insert_position,
    generate_contours,
)
from ._replace_in_place import StyleAndReplacePostProcessor
from ._terrain_base import TerrainAlgorithm


class ContoursAlgorithm(TerrainAlgorithm):

    INTERVAL = "INTERVAL"
    INDEX_EVERY = "INDEX_EVERY"
    COLOUR = "COLOUR"

    OUTPUT_LAYER_NAME = OUTPUT_LAYER_NAME

    def name(self):
        return "contours"

    def displayName(self):
        return "Contours"

    def createInstance(self):
        return ContoursAlgorithm()

    def shortHelpString(self):
        return (
            "Plain contour lines, styled the way a topographic sheet "
            "draws them: every fifth line heavier and labelled with "
            "its height, set into a gap cut in the line, the rest "
            "hairlines.\n\n"
            "Not Tanaka Contours. That tool varies line width by "
            "terrain illumination, which means splitting every "
            "contour into segments and sampling the DEM twice per "
            "segment - a map-sheet technique and nothing larger. "
            "This does neither, so a whole country at a sensible "
            "interval is an ordinary run.\n\n"
            "The interval should follow the map scale, not the DEM: "
            "20 m at 1:50,000, 50 m at 1:250,000, 200 m at "
            "1:1,000,000. Anything finer than about 20 m contours "
            "SRTM's own vertical error rather than the ground."
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
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.INDEX_EVERY,
                "Index contour every N lines",
                type=QgsProcessingParameterNumber.Type.Integer,
                defaultValue=DEFAULT_INDEX_EVERY,
                minValue=1,
                maxValue=20,
            )
        )

        self.addParameter(
            QgsProcessingParameterColor(
                self.COLOUR,
                "Line colour",
                defaultValue=QColor(DEFAULT_COLOUR),
                opacityEnabled=False,
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

        index_every = self.parameterAsInt(
            parameters, self.INDEX_EVERY, context
        )

        colour = self.parameterAsColor(parameters, self.COLOUR, context)

        colour_hex = (
            colour.name() if colour is not None and colour.isValid()
            else DEFAULT_COLOUR
        )

        feedback.pushInfo(
            f"Contouring at {interval:g} m, index every {index_every}."
        )

        feedback.setProgress(10)

        layer = self.generate(
            generate_contours,
            dem,
            extent,
            extent_crs,
            interval=interval,
            index_every=index_every,
            colour=colour_hex,
            feedback=feedback,
        )

        if self.cancelledOrMissing(layer, feedback):
            return {}

        feedback.setProgress(80)

        feedback.pushInfo(f"{layer.featureCount():,} contour lines.")

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

            # colour_hex, not the raw parameter: parameterAsColor
            # hands back an INVALID QColor when the value arrives
            # empty (a model, or a blank Run as Batch cell), and an
            # invalid QColor's name() is "#000000". Styling off the
            # raw one drew the loaded layer black while the generator
            # had already fallen back to DEFAULT_COLOUR, so the saved
            # layer and the shown layer disagreed.
            validated = QColor(colour_hex)

            def style(loaded):

                loaded.setRenderer(
                    _build_renderer(validated, interval, index_every)
                )

                loaded.setLabeling(
                    _build_labeling(loaded, validated, interval, index_every)
                )

                loaded.setLabelsEnabled(True)

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
