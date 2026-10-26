# -*- coding: utf-8 -*-

"""
Range rings - geodesic circles around points, for marking an
aircraft's radius of action.

Grown from a standalone Processing script the maintainer supplied
(kept at prototypes/range_rings.py); the geometry is that script's,
the ring-type model is not.

**A ring is a NAME and a radius, and merging is keyed on the name.**
Rings of the same type union where they overlap - three bases with a
600 km combat radius give one continuous envelope, which is the thing
a planner actually wants to see. Rings of different types never merge
with each other, so a 600 km combat radius and a 1,200 km ferry range
stay as two readable outlines rather than one blob. Asked for in
exactly those terms on 2026-10-26: "I want the rings of same type
merged if overlapping, so the main condition is the name of the
ring".

An ROA ring is pure geometry - how far an aircraft can fly and
return. It needs no DEM, no line of sight and no horizon, so none of
Sensor Coverage's limits apply here despite the shared word "range".
See docs/roadmap.md's task 6.

Military Cartography Tools
"""

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsFeatureSink,
    QgsField,
    QgsFields,
    QgsFillSymbol,
    QgsGeometry,
    QgsPalLayerSettings,
    QgsPointXY,
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingParameterBoolean,
    QgsProcessingParameterColor,
    QgsProcessingParameterEnum,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterNumber,
    QgsProcessingParameterString,
    QgsSingleSymbolRenderer,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsVectorLayerSimpleLabeling,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

# The standard-identity colours this plugin already draws NATO control
# measures in - lifted from _control_measure_shared.py's own
# _AFFILIATION_COLOR_EXPRESSION rather than invented here, and a test
# asserts the two still agree so they cannot drift apart.
#
# "Custom" is last and takes its value from the CUSTOM_COLOUR
# parameter, so the common case is one click and anything else is
# still reachable.
NATO_COLOURS = (
    ("Friend (blue)", "#0000ff"),
    ("Hostile (red)", "#ff0000"),
    ("Neutral (green)", "#00ff00"),
    ("Unknown (yellow)", "#ffff00"),
    ("Black", "#000000"),
)

CUSTOM_COLOUR_LABEL = "Custom..."

COLOUR_OPTIONS = tuple(
    label for label, _ in NATO_COLOURS
) + (CUSTOM_COLOUR_LABEL,)

CUSTOM_COLOUR_INDEX = len(NATO_COLOURS)

DEFAULT_CUSTOM_COLOUR = "#d40000"

# Every pen style QGIS's simple line offers, bar "no pen", which
# would draw nothing.
LINE_STYLES = (
    ("Solid line", "solid"),
    ("Dash line", "dash"),
    ("Dot line", "dot"),
    ("Dash dot line", "dash dot"),
    ("Dash dot dot line", "dash dot dot"),
)

DEFAULT_RADII = "900"

# Segments per quarter circle. 90 gives a 360-sided polygon, smooth
# at any scale a ring this size is drawn at.
BUFFER_SEGMENTS = 90


def parse_rings(radii_text, names_text):

    """
    Turn the two text parameters into an ordered list of
    (name, radius_km).

    `radii_text` is comma-separated kilometres - "600, 1200". Names
    are optional and positional; a name left out or left blank falls
    back to "600 km", which means that by default one radius IS one
    ring type and same-radius rings merge, without the user having to
    name anything.

    Raises ValueError with a readable message rather than letting a
    float() blow up somewhere less helpful.
    """

    radii = []

    for piece in radii_text.replace(";", ",").split(","):

        piece = piece.strip()

        if not piece:
            continue

        try:
            radius = float(piece)

        except ValueError:
            raise ValueError(
                f"{piece!r} is not a number. Give the radii in "
                "kilometres, separated by commas - for example "
                "\"600, 1200\"."
            )

        if radius <= 0:
            raise ValueError(
                f"A radius must be greater than zero, got {radius:g}."
            )

        radii.append(radius)

    if not radii:
        raise ValueError(
            "No radii given. Enter at least one, in kilometres."
        )

    names = [part.strip() for part in (names_text or "").split(",")]

    rings = []

    for index, radius in enumerate(radii):

        name = names[index] if index < len(names) else ""

        rings.append((name or f"{radius:g} km", radius))

    return rings


def resolve_colour(colour_index, custom_colour):

    """
    The hex colour for a chosen option.

    Anything but the last entry is one of the standard identities;
    the last is "Custom...", which takes whatever the colour picker
    holds. An out-of-range index falls back to the first standard
    colour rather than raising - Processing can hand one over from a
    saved model written against a shorter list.
    """

    if colour_index == CUSTOM_COLOUR_INDEX:

        if hasattr(custom_colour, "name"):
            return custom_colour.name()

        return str(custom_colour) or DEFAULT_CUSTOM_COLOUR

    if 0 <= colour_index < len(NATO_COLOURS):
        return NATO_COLOURS[colour_index][1]

    return NATO_COLOURS[0][1]


def geodesic_circle(point_wgs84, radius_m, transform_context):

    """
    A circle of true ground radius around `point_wgs84`, returned in
    EPSG:4326.

    Built in an azimuthal equidistant projection centred on the point
    itself, where a plain buffer IS a ground-distance circle, then
    transformed back. Buffering in EPSG:4326 instead would buffer in
    DEGREES, which is neither circular nor the requested distance
    anywhere but the equator.
    """

    aeqd = QgsCoordinateReferenceSystem.fromProj(
        "+proj=aeqd +lat_0={} +lon_0={} +datum=WGS84 +units=m +no_defs".format(
            point_wgs84.y(), point_wgs84.x()
        )
    )

    to_wgs84 = QgsCoordinateTransform(aeqd, WGS84, transform_context)

    circle = QgsGeometry.fromPointXY(
        QgsPointXY(0, 0)
    ).buffer(radius_m, BUFFER_SEGMENTS)

    circle.transform(to_wgs84)

    return circle


class _StylePostProcessor(QgsProcessingLayerPostProcessorInterface):

    """
    Outline-only fill plus a label outside each ring.

    Held in a class-level registry because Processing keeps only a
    weak reference: without it Python collects the post-processor
    before the layer is loaded and the styling silently never
    happens.
    """

    _instances = []

    def __init__(self, colour_hex, line_style, line_width, label_on):

        super().__init__()

        self.colour_hex = colour_hex
        self.line_style = line_style
        self.line_width = line_width
        self.label_on = label_on

    @classmethod
    def create(cls, colour_hex, line_style, line_width, label_on):

        instance = cls(colour_hex, line_style, line_width, label_on)

        cls._instances.append(instance)

        return instance

    def postProcessLayer(self, layer, context, feedback):

        symbol = QgsFillSymbol.createSimple(
            {
                "color": "0,0,0,0",
                "style": "no",
                "outline_color": self.colour_hex,
                "outline_style": self.line_style,
                "outline_width": str(self.line_width),
            }
        )

        layer.setRenderer(
            QgsSingleSymbolRenderer(symbol)
        )

        if not self.label_on:
            layer.setLabelsEnabled(False)
            return

        settings = QgsPalLayerSettings()

        settings.fieldName = "ring"
        settings.isExpression = False

        settings.placement = Qgis.LabelPlacement.OutsidePolygons
        settings.dist = 2.0

        text_format = QgsTextFormat()
        text_format.setSize(9.0)
        text_format.setColor(QColor(self.colour_hex))

        buffer_settings = QgsTextBufferSettings()
        buffer_settings.setEnabled(True)
        buffer_settings.setSize(0.8)
        buffer_settings.setColor(QColor("#ffffff"))

        text_format.setBuffer(buffer_settings)

        settings.setFormat(text_format)

        layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
        layer.setLabelsEnabled(True)


class RangeRingsAlgorithm(QgsProcessingAlgorithm):

    INPUT = "INPUT"
    RADII = "RADII"
    NAMES = "NAMES"
    COLOUR = "COLOUR"
    CUSTOM_COLOUR = "CUSTOM_COLOUR"
    LINE_STYLE = "LINE_STYLE"
    LINE_WIDTH = "LINE_WIDTH"
    MERGE = "MERGE"
    LABEL_ON = "LABEL_ON"
    OUTPUT = "OUTPUT"

    def name(self):
        return "rangerings"

    def displayName(self):
        return "Range rings (radius of action)"

    def group(self):
        return "Planning"

    def groupId(self):
        return "planning"

    def createInstance(self):
        return RangeRingsAlgorithm()

    def shortHelpString(self):
        return (
            "Draws geodesic range rings around each input point - for "
            "marking an aircraft's radius of action.\n\n"
            "Give one or more radii in kilometres, separated by "
            "commas. Each radius is a ring TYPE, named after its "
            "distance unless you name it yourself.\n\n"
            "Rings of the SAME type merge where they overlap, so "
            "several bases sharing a combat radius give one "
            "continuous envelope. Rings of different types never "
            "merge with each other.\n\n"
            "Each circle is built in an azimuthal equidistant "
            "projection centred on its own point, so the radius is a "
            "true ground distance rather than a distance in degrees."
        )

    def initAlgorithm(self, config=None):

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                "Points",
                [QgsProcessing.SourceType.TypeVectorPoint],
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.RADII,
                "Radii in km, comma separated",
                defaultValue=DEFAULT_RADII,
            )
        )

        self.addParameter(
            QgsProcessingParameterString(
                self.NAMES,
                "Ring names, comma separated (optional)",
                defaultValue="",
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.COLOUR,
                "Line colour",
                options=list(COLOUR_OPTIONS),
                defaultValue=0,
            )
        )

        self.addParameter(
            QgsProcessingParameterColor(
                self.CUSTOM_COLOUR,
                f"Custom colour (used when Line colour is {CUSTOM_COLOUR_LABEL})",
                defaultValue=QColor(DEFAULT_CUSTOM_COLOUR),
                opacityEnabled=False,
                optional=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterEnum(
                self.LINE_STYLE,
                "Line type",
                options=[name for name, _ in LINE_STYLES],
                defaultValue=0,
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.LINE_WIDTH,
                "Line width in mm",
                type=QgsProcessingParameterNumber.Type.Double,
                defaultValue=0.5,
                minValue=0.01,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.MERGE,
                "Merge overlapping rings of the same type",
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.LABEL_ON,
                "Label the rings",
                defaultValue=True,
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                "Range rings",
            )
        )

    def processAlgorithm(self, parameters, context, feedback):

        source = self.parameterAsSource(parameters, self.INPUT, context)

        if source is None:
            raise QgsProcessingException(
                self.invalidSourceError(parameters, self.INPUT)
            )

        try:
            rings = parse_rings(
                self.parameterAsString(parameters, self.RADII, context),
                self.parameterAsString(parameters, self.NAMES, context),
            )

        except ValueError as bad_input:
            raise QgsProcessingException(str(bad_input))

        colour_hex = resolve_colour(
            self.parameterAsEnum(parameters, self.COLOUR, context),
            self.parameterAsColor(parameters, self.CUSTOM_COLOUR, context),
        )

        line_style = LINE_STYLES[
            self.parameterAsEnum(parameters, self.LINE_STYLE, context)
        ][1]

        line_width = self.parameterAsDouble(
            parameters, self.LINE_WIDTH, context
        )

        merge = self.parameterAsBoolean(parameters, self.MERGE, context)

        label_on = self.parameterAsBoolean(
            parameters, self.LABEL_ON, context
        )

        fields = QgsFields()
        fields.append(QgsField("ring", QMetaType.Type.QString))
        fields.append(QgsField("radius_km", QMetaType.Type.Double))

        sink, dest_id = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            fields,
            Qgis.WkbType.Polygon,
            WGS84,
        )

        if sink is None:
            raise QgsProcessingException(
                self.invalidSinkError(parameters, self.OUTPUT)
            )

        to_wgs84 = QgsCoordinateTransform(
            source.sourceCrs(),
            WGS84,
            context.transformContext(),
        )

        points = []

        for feature in source.getFeatures():

            if feedback.isCanceled():
                return {}

            geometry = feature.geometry()

            if geometry is None or geometry.isEmpty():
                continue

            points.append(
                to_wgs84.transform(
                    QgsPointXY(geometry.centroid().asPoint())
                )
            )

        if not points:
            raise QgsProcessingException(
                "No usable points in the input layer."
            )

        total = len(points) * len(rings)
        done = 0

        for name, radius_km in rings:

            circles = []

            for point in points:

                if feedback.isCanceled():
                    return {}

                circles.append(
                    geodesic_circle(
                        point,
                        radius_km * 1000.0,
                        context.transformContext(),
                    )
                )

                done += 1
                feedback.setProgress(int(100 * done / total))

            feedback.pushInfo(
                f"{name}: {len(circles)} ring(s) at {radius_km:g} km"
            )

            # Merging is per ring TYPE, never across them - see this
            # module's own docstring.
            if merge and len(circles) > 1:
                parts = QgsGeometry.unaryUnion(
                    circles
                ).asGeometryCollection()

            else:
                parts = circles

            for part in parts:

                out = QgsFeature(fields)
                out.setGeometry(part)
                out.setAttributes([name, radius_km])

                sink.addFeature(out, QgsFeatureSink.FastInsert)

        if context.willLoadLayerOnCompletion(dest_id):

            details = context.layerToLoadOnCompletionDetails(dest_id)

            details.name = "Range rings"

            details.setPostProcessor(
                _StylePostProcessor.create(
                    colour_hex, line_style, line_width, label_on
                )
            )

        return {self.OUTPUT: dest_id}
