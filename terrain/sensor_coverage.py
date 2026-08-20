# -*- coding: utf-8 -*-

"""
Multi-sensor coverage: three persistent, hand-digitized "Sensor Points"
layers (Low/Medium/High level), each driving its own merged "Sensor
Coverage" polygon.

Unlike the single-observer Viewshed tool (viewshed_tool.py), where every
click is a complete standalone analysis that replaces the last one, a
sensor laydown is several sensors deployed together whose coverage is
read as one picture: overlapping footprints should fuse into a single
perimeter, and only genuinely separated ones should draw as separate
shapes. That is exactly what a unary union of every sensor's own
visible-area polygon produces - see generate_sensor_coverage().

**The bands are measured ABOVE THE ANTENNA, not above sea level.** This
is the single most counter-intuitive thing in this module and it was
established by the maintainer directly, 2026-08-20, with two worked
cases:

  - A radar on a boat, 5 m mast, so 5 m AMSL. An aircraft at 300 m AMSL
    is 295 m above it - inside a 3,300 m capability. An aircraft at
    3,500 m AMSL is 3,495 m above it - OUTSIDE that capability.
  - The same radar on a 2,000 m plateau, still 5 m of mast, so 2,005 m
    AMSL. The 3,500 m aircraft is now only 1,495 m above it - INSIDE
    the same capability.

So a level is a statement about the SENSOR's vertical reach, not about
a fixed slice of airspace: siting a set higher lifts its whole band
with it, and the same aircraft can be a low-level target to one radar
and out of reach of an identical one elsewhere. Getting this backwards
(treating the bands as absolute AMSL altitudes) is the obvious mistake,
and was in fact the first implementation here before the maintainer
corrected it.

**Why three layers rather than one with a "level" field.** A real
laydown is planned one band at a time - the low-level picture and the
high-level picture are different products, drawn and read separately.
Splitting them into their own layers also lets each layer's own
detection-height field be range-limited to its own band by the
attribute form (see _configure_attribute_form()), which a single shared
field could not be, and lets a user show/hide one band's whole picture
with one Layers-panel checkbox. Because each band is drawn at its own
TOP (the maintainer's choice, 2026-08-20 - the best case rather than
the guaranteed-throughout-the-band case), coverage for identically
sited sensors nests: High contains Medium contains Low.

**Per-point sensor characteristics, not per-level presets.** Confirmed
with the maintainer 2026-08-20 against a concrete case: three radars
that all belong on the LOW level layer but differ by an order of
magnitude in range (a man-portable set at ~5-6 m and 30 km, a
vehicle-mounted one at ~10-12 m and 150 km, a semi-mobile ground set at
~10-15 m and 180 km). So sensor height, detection height and maximum
range are all per-FEATURE fields; the level only constrains which
detection heights are valid on that layer. The DEM, by contrast, is
global - one terrain source covers the whole laydown - and is
remembered on the points layer itself (see set_dem_layer()).

**Deliberately NOT modelled: antenna tilt limits and beam width.** Both
were raised and both were ruled out by the maintainer, 2026-08-20, as
too sensor-specific to express usefully without real figures. Nor is
any RF path-loss model used (Longley-Rice, ITU-R P.1812 and friends
were surveyed): every one of them needs frequency, transmit power,
antenna gain, receiver sensitivity and ground constants, none of which
this tool's users can supply, and inventing them would dress made-up
inputs up as a dB contour. The geometric model here claims exactly what
it knows - terrain, curvature, and an operator-stated maximum range -
and nothing more.

Deliberately NOT a generate_*()/replace_named_layer() feature on the
POINTS side, same reasoning as military_symbology/_point_symbol_layer.py:
the sensor points are hand-placed operational data a user digitizes and
then drags around with QGIS's own native point-editing tools, never
something safe to silently regenerate. The COVERAGE layers are the
opposite - pure derived output, regenerated in place from the points
every time.

Military Cartography Tools
"""

from collections import namedtuple

from qgis.core import (
    QgsCoordinateTransform,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsMarkerSymbol,
    QgsProject,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from ..core.coordinate_utils import WGS84
from .viewshed import (
    _apply_polygon_style,
    DEFAULT_OPACITY,
    DEFAULT_OUTLINE_ONLY,
    visible_area_at_altitude,
)


# Radar propagation bends more than light does. The rest of this plugin
# uses 0.13, the standard OPTICAL refraction coefficient, because Line
# of Sight and Viewshed are both about what an eye can see; radar
# convention is the 4/3-earth model, k = 0.25, which pushes the horizon
# out by roughly 15%. On a 180 km set that is tens of kilometres, so it
# is not a rounding choice. Confirmed with the maintainer 2026-08-20:
# use the radar figure here and leave the other two features optical.
RADAR_REFRACTION_COEFFICIENT = 0.25


# Which DEM this layer's coverage is computed against, remembered on
# the points layer itself rather than re-asked per regeneration. A
# layer custom property (not a field) because it belongs to the whole
# laydown, not to any one sensor, and because QGIS serializes custom
# properties into the project file - so a saved project reopens still
# knowing its own DEM.
DEM_LAYER_PROPERTY = "mct/sensor_coverage_dem_layer_id"

POINTS_LAYER_NAME_TEMPLATE = "Sensor Points - {label}"
COVERAGE_LAYER_NAME_TEMPLATE = "Sensor Coverage - {label}"


# The three bands, as agreed with the maintainer 2026-08-20. Each is a
# height ABOVE THE SENSOR'S OWN ANTENNA (see this module's docstring),
# not an absolute altitude. The boundaries are the familiar flight-level
# ones - 10,000 ft and 25,000 ft - converted to round metric figures
# rather than their exact conversions (3,048 m and 7,620 m), because
# these are planning band edges, not measurements: a sensor is not
# assigned to the low-level picture by three metres.
#
# `ceiling` on the top band is a form limit, not a physical one - the
# band itself is open-ended ("above 25,000 ft"), and 30,000 m is simply
# well past anything an air-defence sensor is asked about while still
# keeping the spin box's own range finite.
LOW_CEILING_M = 3300.0
MEDIUM_CEILING_M = 7000.0
HIGH_CEILING_M = 30000.0

SensorLevel = namedtuple(
    "SensorLevel",
    ("key", "label", "floor_m", "ceiling_m", "color")
)

# Each band gets its own colour: all three coverage layers are meant to
# be read together over the same ground, and three greens would be
# indistinguishable. Low keeps viewshed.py's own green (the established
# "this is visible" colour in this plugin), with amber and blue climbing
# from it.
SENSOR_LEVELS = (
    SensorLevel("low", "Low Level", 0.0, LOW_CEILING_M, (60, 160, 60)),
    SensorLevel("medium", "Medium Level", LOW_CEILING_M, MEDIUM_CEILING_M, (220, 150, 40)),
    SensorLevel("high", "High Level", MEDIUM_CEILING_M, HIGH_CEILING_M, (60, 110, 200)),
)


# A light, mobile set sits a few metres up; a mast-mounted one tens of
# metres. The range is deliberately wide rather than tuned to any one
# sensor type - see this module's own docstring.
DEFAULT_SENSOR_HEIGHT_M = 5.0
MAX_SENSOR_HEIGHT_M = 500.0

# 30 km is the low end of the maintainer's own worked example (a
# man-portable set), so it is a defensible starting value that is
# obviously wrong for a longer-ranged sensor rather than plausibly
# wrong for all of them.
DEFAULT_MAX_DISTANCE_M = 30000.0
MIN_MAX_DISTANCE_M = 50.0

# Past this, curvature alone stops the sightline regardless of what the
# sensor claims: even a target at 15,000 m is over the horizon from a
# 5 m observer beyond roughly 477 km (see docs/roadmap.md's own
# 2026-08-20 entry for the working). Left generous rather than enforced
# per-feature, since the real limit depends on both heights.
MAX_MAX_DISTANCE_M = 500000.0

MARKER_SIZE_MM = 3.0


def level_by_key(key):

    for level in SENSOR_LEVELS:

        if level.key == key:
            return level

    return None


def points_layer_name(level):

    return POINTS_LAYER_NAME_TEMPLATE.format(label=level.label)


def coverage_layer_name(level):

    return COVERAGE_LAYER_NAME_TEMPLATE.format(label=level.label)


def set_dem_layer(points_layer, dem_layer):

    points_layer.setCustomProperty(
        DEM_LAYER_PROPERTY,
        dem_layer.id()
    )


def dem_layer_for(points_layer):

    """
    The DEM remembered on points_layer, resolved against the current
    project - or None if none was ever set, or if the layer it named
    has since been removed from the project (a real case: a user can
    delete the DEM and leave the sensor points behind).
    """

    layer_id = points_layer.customProperty(
        DEM_LAYER_PROPERTY
    )

    if not layer_id:
        return None

    return QgsProject.instance().mapLayer(
        layer_id
    )


def _configure_attribute_form(layer, level):

    """
    Range spin boxes, defaults and unit-naming aliases for the three
    per-sensor fields - the same widget convention every hand-digitized
    layer in this plugin uses (see military_symbology/
    _control_measure_shared.py's configure_rotation_and_scale_fields()).

    Detection height is the one field whose range is level-specific: it
    is clamped to this layer's own band, which is what makes a point
    placed on the Low Level layer a low-level sensor rather than
    something the user has to remember to keep in band by hand. It
    defaults to the band's CEILING, because each band is drawn at its
    own top - see this module's docstring.
    """

    fields = layer.fields()

    observer_idx = fields.indexOf("sensor_height")

    layer.setEditorWidgetSetup(
        observer_idx,
        QgsEditorWidgetSetup(
            "Range",
            {
                "Min": 0.0,
                "Max": MAX_SENSOR_HEIGHT_M,
                "Step": 0.5,
                "Precision": 1,
                "Style": "SpinBox",
                "AllowNull": False,
            }
        )
    )

    layer.setDefaultValueDefinition(
        observer_idx,
        QgsDefaultValue(f"{DEFAULT_SENSOR_HEIGHT_M:g}")
    )

    layer.setFieldAlias(
        observer_idx,
        "Sensor height (m above ground)"
    )


    detection_idx = fields.indexOf("detection_height")

    layer.setEditorWidgetSetup(
        detection_idx,
        QgsEditorWidgetSetup(
            "Range",
            {
                "Min": level.floor_m,
                "Max": level.ceiling_m,
                "Step": 100.0,
                "Precision": 0,
                "Style": "SpinBox",
                "AllowNull": False,
            }
        )
    )

    layer.setDefaultValueDefinition(
        detection_idx,
        QgsDefaultValue(f"{level.ceiling_m:g}")
    )

    layer.setFieldAlias(
        detection_idx,
        f"Max detection height above sensor (m, {level.label.lower()})"
    )

    distance_idx = fields.indexOf("max_distance")

    layer.setEditorWidgetSetup(
        distance_idx,
        QgsEditorWidgetSetup(
            "Range",
            {
                "Min": MIN_MAX_DISTANCE_M,
                "Max": MAX_MAX_DISTANCE_M,
                "Step": 1000.0,
                "Precision": 0,
                "Style": "SpinBox",
                "AllowNull": False,
            }
        )
    )

    layer.setDefaultValueDefinition(
        distance_idx,
        QgsDefaultValue(f"{DEFAULT_MAX_DISTANCE_M:g}")
    )

    layer.setFieldAlias(
        distance_idx,
        "Maximum range (m)"
    )


def build_sensor_points_layer(level):

    """
    A fresh, empty sensor points layer for one level - hand-digitized
    with QGIS's own Add Point tool, then moved/deleted with its own
    vertex tools. Never added to the project here; see
    core/_layer_utils.py's module docstring.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        points_layer_name(level),
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("sensor_height", QMetaType.Type.Double),
            QgsField("detection_height", QMetaType.Type.Double),
            QgsField("max_distance", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    _configure_attribute_form(
        layer,
        level
    )

    red, green, blue = level.color

    layer.renderer().setSymbol(
        QgsMarkerSymbol.createSimple(
            {
                "name": "triangle",
                "color": f"{red},{green},{blue}",
                "outline_color": "0,0,0",
                "outline_width": "0.3",
                "size": str(MARKER_SIZE_MM),
            }
        )
    )

    return layer


def _sensor_observations(points_layer, level):

    """
    Every sensor on points_layer as a (WGS84 QgsPointXY, sensor_height,
    detection_height, max_distance) tuple, skipping any feature with no
    geometry. Field values fall back to sensible defaults rather than
    being trusted to exist: a feature created before a field did, or
    one whose value was cleared by hand, should still contribute its
    coverage instead of silently dropping out of the picture. The
    detection-height fallback is this LEVEL's own ceiling, matching the
    field default - see _configure_attribute_form().
    """

    to_wgs84 = QgsCoordinateTransform(
        points_layer.crs(),
        WGS84,
        QgsProject.instance()
    )

    for feature in points_layer.getFeatures():

        geometry = feature.geometry()

        if geometry.isEmpty():
            continue

        point = to_wgs84.transform(
            geometry.asPoint()
        )

        def value(name, fallback):

            raw = feature[name]

            return fallback if raw is None else float(raw)

        yield (
            point,
            value("sensor_height", DEFAULT_SENSOR_HEIGHT_M),
            value("detection_height", level.ceiling_m),
            value("max_distance", DEFAULT_MAX_DISTANCE_M),
        )


def _merged_visible_geometry(dem_layer, points_layer, level):

    """
    One QgsGeometry (in WGS84) covering everything from which a target
    at any sensor's own detection ceiling would be visible, or None if
    no sensor produced any coverage at all.

    Every per-sensor result is reprojected to WGS84 BEFORE being
    unioned. That is not incidental tidying: visible_area_at_altitude()
    returns its polygon in whatever local UTM zone the DEM clip around
    THAT sensor resolved to, and two sensors far enough apart genuinely
    land in different zones - unioning those raw would silently place
    one of them thousands of kilometres from where it belongs.

    The union itself is what the whole feature is for: overlapping
    footprints fuse into a single outer perimeter, while sensors too far
    apart to overlap simply stay separate parts of the same multipolygon
    and keep drawing their own outlines.
    """

    project = QgsProject.instance()

    geometries = []

    for point, sensor_height, detection_height, max_distance in _sensor_observations(points_layer, level):

        visible = visible_area_at_altitude(
            dem_layer,
            point,
            sensor_height,
            detection_height,
            max_distance,
            refraction_coefficient=RADAR_REFRACTION_COEFFICIENT
        )

        if visible is None:
            # This sensor sits outside the DEM's own coverage - the
            # rest of the laydown is still perfectly valid, so it is
            # skipped rather than failing the whole regeneration.
            continue

        to_wgs84 = QgsCoordinateTransform(
            visible.crs(),
            WGS84,
            project
        )

        for feature in visible.getFeatures():

            geometry = QgsGeometry(
                feature.geometry()
            )

            geometry.transform(
                to_wgs84
            )

            geometries.append(
                geometry
            )

    if not geometries:
        return None

    return QgsGeometry.unaryUnion(
        geometries
    )


def generate_sensor_coverage(
    dem_layer,
    points_layer,
    level,
    opacity=DEFAULT_OPACITY,
    outline_only=DEFAULT_OUTLINE_ONLY
):

    """
    Build this level's merged "Sensor Coverage" polygon layer from every
    sensor on points_layer, against the one shared dem_layer. Returns
    None when nothing is visible from anywhere - an empty points layer,
    or every sensor outside the DEM - so a caller can leave whatever is
    already drawn alone instead of replacing it with an empty layer.

    Deliberately does NOT add the layer to the project; see
    core/_layer_utils.py's module docstring.
    """

    merged = _merged_visible_geometry(
        dem_layer,
        points_layer,
        level
    )

    if merged is None or merged.isEmpty():
        return None

    layer = QgsVectorLayer(
        f"Polygon?crs={WGS84.authid()}",
        coverage_layer_name(level),
        "memory"
    )

    feature = QgsFeature()

    feature.setGeometry(
        merged
    )

    layer.dataProvider().addFeature(
        feature
    )

    layer.updateExtents()

    _apply_polygon_style(
        layer,
        opacity,
        level.color,
        outline_only
    )

    return layer


def default_insert_position(project, layer):

    """
    Top of the layer tree - the same placement Viewshed's own output
    uses, and for the same reason: this is an analysis overlay meant to
    sit above whatever terrain rendering is underneath, not a base
    layer.
    """

    project.layerTreeRoot().insertLayer(
        0,
        layer
    )
