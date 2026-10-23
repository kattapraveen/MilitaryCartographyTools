"""
Range rings (geodesic circles) - QGIS Processing script

For every input point, draws a circle of a given radius (in km) that is
accurate on the ground (each circle is built in an azimuthal equidistant
projection centred on its own point, then returned in EPSG:4326).
Overlapping circles can be merged into one outline.
The result is an outline-only polygon layer with a label placed outside.

Install: Processing Toolbox -> Scripts (Python icon) -> Add Script to Toolbox...
Written for QGIS 4.x (also works on recent 3.x).
"""

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor
from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsFields,
    QgsField,
    QgsFillSymbol,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
)

COLOURS = [
    ("Red", "#d40000"),
    ("Blue", "#0033cc"),
    ("Black", "#000000"),
]

# label shown in the dialog -> QGIS simple line style name
LINE_STYLES = [
    ("Solid line", "solid"),
    ("Dash line", "dash"),
    ("Dot line", "dot"),
    ("Dash dot line", "dash dot"),
    ("Dash dot dot line", "dash dot dot"),
]


class _StylePostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Applies the outline-only symbol and the outside label to the output layer."""

    instance = None  # keep a reference so it is not garbage collected

    def __init__(self, colour_hex, line_style, line_width, label_on):
        super().__init__()
        self.colour_hex = colour_hex
        self.line_style = line_style
        self.line_width = line_width
        self.label_on = label_on

    def postProcessLayer(self, layer, context, feedback):
        symbol = QgsFillSymbol.createSimple({
            "color": "0,0,0,0",                      # no fill, perimeter only
            "style": "no",
            "outline_color": self.colour_hex,
            "outline_style": self.line_style,
            "outline_width": str(self.line_width),
            "outline_width_unit": "MM",
        })
        layer.renderer().setSymbol(symbol)

        if self.label_on:
            settings = QgsPalLayerSettings()
            settings.fieldName = "label"
            try:
                settings.placement = Qgis.LabelPlacement.OutsidePolygons
            except AttributeError:
                settings.placement = QgsPalLayerSettings.OutsidePolygons
            settings.dist = 2  # mm away from the outline

            fmt = QgsTextFormat()
            fmt.setSize(10)
            fmt.setColor(QColor(self.colour_hex))
            buf = QgsTextBufferSettings()
            buf.setEnabled(True)
            buf.setSize(0.8)
            buf.setColor(QColor("#ffffff"))
            fmt.setBuffer(buf)
            settings.setFormat(fmt)

            layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
            layer.setLabelsEnabled(True)
        else:
            layer.setLabelsEnabled(False)

        layer.triggerRepaint()

    @staticmethod
    def create(colour_hex, line_style, line_width, label_on):
        _StylePostProcessor.instance = _StylePostProcessor(
            colour_hex, line_style, line_width, label_on)
        return _StylePostProcessor.instance


class RangeRings(QgsProcessingAlgorithm):
    INPUT = "INPUT"
    DISTANCE = "DISTANCE"
    COLOUR = "COLOUR"
    LINE_STYLE = "LINE_STYLE"
    LINE_WIDTH = "LINE_WIDTH"
    MERGE = "MERGE"
    LABEL_ON = "LABEL_ON"
    LABEL_TEXT = "LABEL_TEXT"
    OUTPUT = "OUTPUT"

    def name(self):
        return "rangerings"

    def displayName(self):
        return "Range rings (merged circles)"

    def group(self):
        return "Range rings"

    def groupId(self):
        return "rangerings"

    def createInstance(self):
        return RangeRings()

    def shortHelpString(self):
        return (
            "Draws a circle of the given radius (km) around each input point. "
            "Distances are true ground distances (geodesic-accurate), so the "
            "result is correct even when the project CRS is EPSG:4326.\n\n"
            "Overlapping circles can be merged into one outline. The output is "
            "an outline-only layer in the chosen colour and line type, with the "
            "label placed outside the circle.\n\n"
            "Tip: tick 'Selected features only' to use just the points you have "
            "selected."
        )

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT, "Input points",
            [QgsProcessing.TypeVectorPoint]))
        self.addParameter(QgsProcessingParameterNumber(
            self.DISTANCE, "Radius (km)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=900.0, minValue=0.001, maxValue=19000.0))
        self.addParameter(QgsProcessingParameterEnum(
            self.COLOUR, "Line colour",
            options=[c[0] for c in COLOURS], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.LINE_STYLE, "Line type",
            options=[s[0] for s in LINE_STYLES], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.LINE_WIDTH, "Line width (mm)",
            type=QgsProcessingParameterNumber.Double,
            defaultValue=0.5, minValue=0.05, maxValue=5.0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.MERGE, "Merge overlapping circles", defaultValue=True))
        self.addParameter(QgsProcessingParameterBoolean(
            self.LABEL_ON, "Add label (outside the circle)",
            defaultValue=True))
        self.addParameter(QgsProcessingParameterString(
            self.LABEL_TEXT, "Label text (leave blank for e.g. '900 km')",
            defaultValue="", optional=True))
        self.addParameter(QgsProcessingParameterFeatureSink(
            self.OUTPUT, "Range rings",
            type=QgsProcessing.TypeVectorPolygon))

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        distance_km = self.parameterAsDouble(parameters, self.DISTANCE, context)
        colour_hex = COLOURS[self.parameterAsEnum(parameters, self.COLOUR, context)][1]
        line_style = LINE_STYLES[self.parameterAsEnum(parameters, self.LINE_STYLE, context)][1]
        line_width = self.parameterAsDouble(parameters, self.LINE_WIDTH, context)
        merge = self.parameterAsBoolean(parameters, self.MERGE, context)
        label_on = self.parameterAsBoolean(parameters, self.LABEL_ON, context)
        label_text = (self.parameterAsString(parameters, self.LABEL_TEXT, context) or "").strip()
        if not label_text:
            label_text = "{:g} km".format(distance_km)

        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        to_wgs = QgsCoordinateTransform(source.sourceCrs(), wgs84, context.transformContext())

        fields = QgsFields()
        fields.append(QgsField("label", QMetaType.Type.QString))
        fields.append(QgsField("radius_km", QMetaType.Type.Double))

        sink, dest_id = self.parameterAsSink(
            parameters, self.OUTPUT, context, fields, Qgis.WkbType.Polygon, wgs84)
        if sink is None:
            raise QgsProcessingException(self.invalidSinkError(parameters, self.OUTPUT))

        circles = []
        total = source.featureCount() or 1
        radius_m = distance_km * 1000.0

        for i, feat in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break
            geom = feat.geometry()
            if geom is None or geom.isNull() or geom.isEmpty():
                continue
            pt = geom.centroid().asPoint()
            pt = to_wgs.transform(QgsPointXY(pt))

            # circle in a local azimuthal equidistant projection = true ground radius
            aeqd = QgsCoordinateReferenceSystem.fromProj(
                "+proj=aeqd +lat_0={} +lon_0={} +datum=WGS84 +units=m +no_defs".format(
                    pt.y(), pt.x()))
            to_wgs_local = QgsCoordinateTransform(aeqd, wgs84, context.transformContext())
            circle = QgsGeometry.fromPointXY(QgsPointXY(0, 0)).buffer(radius_m, 90)
            circle.transform(to_wgs_local)
            circles.append(circle)
            feedback.setProgress(int(100 * (i + 1) / total))

        if not circles:
            raise QgsProcessingException("No valid input points found.")

        if merge:
            parts = QgsGeometry.unaryUnion(circles).asGeometryCollection()
        else:
            parts = circles

        for part in parts:
            out = QgsFeature(fields)
            out.setGeometry(part)
            out.setAttributes([label_text, distance_km])
            sink.addFeature(out, QgsFeatureSink.FastInsert)

        if context.willLoadLayerOnCompletion(dest_id):
            details = context.layerToLoadOnCompletionDetails(dest_id)
            details.name = "Range rings {:g} km".format(distance_km)
            details.setPostProcessor(_StylePostProcessor.create(
                colour_hex, line_style, line_width, label_on))

        return {self.OUTPUT: dest_id}
