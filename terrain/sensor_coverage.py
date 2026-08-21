# -*- coding: utf-8 -*-

"""
Multi-sensor coverage: three persistent, hand-digitized "Sensor Points"
layers (Low/Medium/High level), each driving its own merged "Sensor
Coverage" perimeter.

Unlike the single-observer Viewshed tool (viewshed_tool.py), where every
click is a complete standalone analysis that replaces the last one, a
sensor laydown is several sensors deployed together whose coverage is
read as one picture: overlapping footprints should fuse into a single
perimeter, and only genuinely separated ones should draw as separate
shapes. The merged perimeter is then partitioned back out, each
stretch attributed to the sensor that contributed it, so the result
reads as one outline while each sensor still labels the part of it that
is its own. See _perimeter_segments() and generate_sensor_coverage().

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
    Qgis,
    QgsCoordinateTransform,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsSymbolLayer,
    QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)

from qgis.PyQt.QtCore import QMetaType
from qgis.PyQt.QtGui import QColor

from ..core.coordinate_utils import WGS84
from ..core.text_format import build_text_format
from .viewshed import visible_area_at_altitude


# Radar propagation bends more than light does. The rest of this plugin
# uses 0.13, the standard OPTICAL refraction coefficient, because Line
# of Sight and Viewshed are both about what an eye can see; radar
# convention is the 4/3-earth model, k = 0.25, which pushes the horizon
# out by roughly 15%. On a 180 km set that is tens of kilometres, so it
# is not a rounding choice. Confirmed with the maintainer 2026-08-20:
# use the radar figure here and leave the other two features optical.
RADAR_REFRACTION_COEFFICIENT = 0.25

# Coverage is a PERIMETER, never a filled shape - the maintainer's own
# call 2026-08-20, on cartographic grounds: "they fill up the entire
# space without clarity". A laydown is several large overlapping shapes
# stacked over the very terrain being judged against them (contours,
# hillshade, unit symbology), and even at 65% a fill washes all of that
# out. Since 2026-08-20 the layer is a LINE layer, so this is now
# structural rather than a styling choice; a user wanting a filled
# product uses the Viewshed tool instead.
#
# Full opacity follows: an outline obscures almost nothing, and holding
# it translucent only greys the line out and undoes the clarity this is
# for.
COVERAGE_OPACITY = 1.0


# Which DEM this layer's coverage is computed against, remembered on
# the points layer itself rather than re-asked per regeneration. A
# layer custom property (not a field) because it belongs to the whole
# laydown, not to any one sensor, and because QGIS serializes custom
# properties into the project file - so a saved project reopens still
# knowing its own DEM.
DEM_LAYER_PROPERTY = "mct/sensor_coverage_dem_layer_id"

# Colour follows AFFILIATION rather than being a free RGB pick, at the
# maintainer's own request 2026-08-20 ("inline with the affiliation that
# we used in the mil-std 2525"). These are the same four standard
# identities and the same four colours every control measure in this
# plugin already draws with - see military_symbology/
# _control_measure_shared.py's POINT_AFFILIATION_LABELS and
# _AFFILIATION_COLOR_EXPRESSION. Deliberately duplicated here rather
# than imported across a package boundary into that module's private
# namespace; test_sensor_coverage.py pins both against it so neither can
# drift, the same way Viewshed's own default green is pinned against
# Line of Sight's.
#
# Note this is the FOUR-value vocabulary, not the five-value one the
# lines/areas helper uses: there is no "unspecified" here. That fifth
# value caused a real bug on 2026-08-12 (every obstacle point rendering
# as unknown) and nothing on this layer feeds a SIDC anyway.
AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

AFFILIATION_COLORS = {
    "friend": (0, 0, 255),
    "hostile": (255, 0, 0),
    "neutral": (0, 255, 0),
    "unknown": (255, 255, 0),
}

DEFAULT_AFFILIATION = "friend"

# Affiliation is PER SENSOR, not per level - the maintainer's own call
# 2026-08-20, on the grounds that there are no separate friendly and
# hostile layers to put them on. **Merging happens strictly within one
# affiliation**: friendly coverage fuses with friendly, hostile with
# hostile, and the two never combine into a shape that would claim a
# single side owns ground it does not. So one level's coverage layer
# holds up to four features, one per affiliation actually present, and
# is styled from the "affiliation" field rather than a fixed colour.

POINTS_LAYER_NAME_TEMPLATE = "Sensor Points - {label}"
COVERAGE_LAYER_NAME_TEMPLATE = "Sensor Coverage - {label}"

# How far above the perimeter the designation sits, in millimetres.
# "Just above the sensor perimeter" - the maintainer's own words,
# 2026-08-20.
DESIGNATION_LABEL_DISTANCE_MM = 1.2
DESIGNATION_LABEL_FONT_SIZE = 8.0

# A perimeter arc can be shorter than its own label - a sensor barely
# breaking the surface of a much larger one's footprint - and PAL will
# not place a label on a line shorter than the text unless allowed to
# overrun its ends.
DESIGNATION_LABEL_OVERRUN_MM = 12.0

# Wide enough to bridge inter-letter spacing, not just outline each
# glyph - a narrower buffer lets the terrain underneath show through
# between letters.
DESIGNATION_LABEL_BUFFER_MM = 1.0


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
    ("key", "label", "floor_m", "ceiling_m", "width_mm", "dash_mm")
)

# Affiliation owns the HUE (see AFFILIATION_COLORS); the level owns how
# far that hue is washed toward white. Without this the three bands of
# one friendly laydown would all be the same blue, and since they nest
# by design - High contains Medium contains Low - stacked bands would be
# unreadable. Tinting instead keeps both signals legible at once: which
# side it is, and which band.
#
# Blending toward white rather than using QColor.lighter(): the
# affiliation colours are fully saturated primaries, whose HSV value is
# already maxed, so lighter() is a no-op on every one of them.
# Width and dash pattern per level. Colour is NOT one of the signals -
# every level draws in its affiliation's own full-strength colour, so a
# hostile perimeter is the same red whichever band it belongs to.
#
# There was briefly a per-level tint as well, lightening each band in
# turn. The maintainer removed it 2026-08-21: "keep all three with same
# colour; since we are using dash and solid, it is self explanatory".
# The tint also had the awkward consequence that the MIDDLE band came
# out palest once High was asked to match Low.
#
# Widths are the maintainer's own figures (0.3 / 0.5, high left at its
# original 0.6). Note this is the OPPOSITE ordering to the one their
# reference text suggested (thickest at low level); raised explicitly
# and left as they specified.
#
# Dash patterns follow that reference: short dash low, long dash medium,
# solid high. Expressed as [on, off] millimetre runs rather than Qt's
# own dash styles, which offer no long/short distinction of their own.
SENSOR_LEVELS = (
    SensorLevel("low", "Low Level", 0.0, LOW_CEILING_M, 0.3, (2.0, 1.5)),
    SensorLevel("medium", "Medium Level", LOW_CEILING_M, MEDIUM_CEILING_M, 0.5, (6.0, 2.0)),
    SensorLevel("high", "High Level", MEDIUM_CEILING_M, HIGH_CEILING_M, 0.6, None),
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


def color_for(affiliation):

    """
    The colour one affiliation's coverage is drawn in - the same at
    every level, see SENSOR_LEVELS.
    """

    return AFFILIATION_COLORS.get(
        affiliation,
        AFFILIATION_COLORS[DEFAULT_AFFILIATION]
    )


def affiliation_color_expression():

    """
    A QGIS expression mapping the "affiliation" field to its own
    colour, for data-defining a symbol's fill/stroke or a label's text
    colour.

    Data-defined rather than a categorized renderer with four classes:
    the coverage layer is rebuilt from scratch on every edit, so the
    renderer is rebuilt with it, and one symbol carrying an expression
    is far less to reconstruct (and to get wrong) than four categories
    whose ordering and fallback would have to be maintained.
    """

    clauses = " ".join(
        "WHEN \"affiliation\" = '{key}' THEN color_rgb({r}, {g}, {b})".format(
            key=key,
            **dict(zip(("r", "g", "b"), color_for(key)))
        )
        for key in AFFILIATION_COLORS
    )

    fallback = color_for(DEFAULT_AFFILIATION)

    return (
        f"CASE {clauses} "
        f"ELSE color_rgb({fallback[0]}, {fallback[1]}, {fallback[2]}) END"
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

    affiliation_idx = fields.indexOf("affiliation")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": {label: key for key, label in AFFILIATION_LABELS.items()}}
        )
    )

    layer.setDefaultValueDefinition(
        affiliation_idx,
        QgsDefaultValue(f"'{DEFAULT_AFFILIATION}'")
    )

    layer.setFieldAlias(
        affiliation_idx,
        "Affiliation"
    )

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

    # Field T, the same free-text designation every symbology layer in
    # this plugin carries, and drawn upper-case per H.5.4's own
    # all-caps rule for text labelling. Left with no default: an unnamed
    # sensor is the normal case and should not invent a name.
    designation_idx = fields.indexOf("unique_designation")

    layer.setFieldAlias(
        designation_idx,
        "Unique designation"
    )

    _configure_location_fields(layer)


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
            # Affiliation first, matching every other layer in this
            # plugin - the standard's own symbol-building order picks a
            # standard identity before anything else.
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("sensor_height", QMetaType.Type.Double),
            QgsField("detection_height", QMetaType.Type.Double),
            QgsField("max_distance", QMetaType.Type.Double),
            QgsField("unique_designation", QMetaType.Type.QString),
            # Derived from the sensor's own position, filled in and kept
            # up to date by QGIS itself - see _configure_location_fields().
            QgsField("latitude", QMetaType.Type.Double),
            QgsField("longitude", QMetaType.Type.Double),
            QgsField("mgrs", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    _configure_attribute_form(
        layer,
        level
    )

    apply_points_style(layer)

    return layer


def apply_points_style(points_layer, level=None):

    """
    The sensor marker, in the same colour as the coverage it generates -
    so a sensor and its footprint read as one thing - and data-defined
    from the feature's own affiliation, so a laydown with friendly and
    hostile sets on one layer shows each marker in its own side's
    colour rather than one colour for the layer.
    """

    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": "triangle",
            "outline_color": "0,0,0",
            "outline_width": "0.3",
            "size": str(MARKER_SIZE_MM),
        }
    )

    symbol.symbolLayer(0).setDataDefinedProperty(
        QgsSymbolLayer.Property.FillColor,
        QgsProperty.fromExpression(
            affiliation_color_expression()
        )
    )

    points_layer.renderer().setSymbol(symbol)

    points_layer.triggerRepaint()


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

        designation = feature["unique_designation"]

        affiliation = feature["affiliation"]

        yield (
            point,
            (
                affiliation
                if affiliation in AFFILIATION_COLORS
                else DEFAULT_AFFILIATION
            ),
            "" if designation is None else str(designation).strip(),
            value("sensor_height", DEFAULT_SENSOR_HEIGHT_M),
            value("detection_height", level.ceiling_m),
            value("max_distance", DEFAULT_MAX_DISTANCE_M),
        )


def _sensor_footprints(dem_layer, points_layer, level):

    """
    [(affiliation, designation, footprint)] - one entry per sensor that
    produced any coverage at all, each footprint a single QgsGeometry in
    WGS84.

    Kept PER SENSOR rather than unioned on the spot for two reasons:
    merging is confined to one affiliation (see this module's own
    constants), and each sensor labels its own stretch of the perimeter
    (see _perimeter_segments()) - neither of which can be recovered once
    everything has been fused into one shape.

    Every per-sensor result is reprojected to WGS84 here, before
    anything is combined. That is not incidental tidying:
    visible_area_at_altitude() returns its polygon in whatever local UTM
    zone the DEM clip around THAT sensor resolved to, and two sensors
    far enough apart genuinely land in different zones - combining those
    raw would silently place one of them thousands of kilometres from
    where it belongs.
    """

    project = QgsProject.instance()

    footprints = []

    for point, affiliation, designation, sensor_height, detection_height, max_distance in _sensor_observations(points_layer, level):

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

        parts = []

        for feature in visible.getFeatures():

            geometry = QgsGeometry(
                feature.geometry()
            )

            geometry.transform(
                to_wgs84
            )

            parts.append(geometry)

        if not parts:
            continue

        combined = QgsGeometry.unaryUnion(parts)

        if combined is None or combined.isEmpty():
            continue

        footprints.append((affiliation, designation, combined))

    return footprints


def _perimeter_segments(footprints):

    """
    [(affiliation, designation, line geometry)] - each named sensor
    paired with the stretch of the MERGED perimeter that is its own, so
    it can label it.

    A sensor's contribution is the part of its OWN boundary that lies on
    the merged perimeter of everything on its side: wherever two
    same-side coverages overlap, the swallowed arc is interior to their
    merged shape and no longer part of any perimeter, so it must not be
    drawn or labelled. That is the maintainer's own specification -
    "each sensor label is on its respective perimeter, in case of
    overlap in the respective segment of the perimeter".

    **Computed by PARTITIONING the merged boundary, not by subtracting
    or intersecting.** Both of the obvious formulations were tried and
    both were wrong:

      - `own boundary MINUS the other footprints` looks right and
        silently deletes coverage. Two same-side sensors in the same
        place with the same range have identical footprints, so each
        one's boundary lies exactly ON the other's polygon, and GEOS
        counts boundary points as inside - each erased the other and
        coverage vanished outright. Reported by the maintainer
        2026-08-21 and reproduced: `generate_sensor_coverage()` returned
        None for two coincident sensors. It has the same failure
        wherever two footprints share any stretch of boundary at all,
        which two sensors clipped against the same DEM edge do.
      - `own boundary INTERSECTED with the merged boundary` is immune to
        that, but GEOS returns each collinear run as its own tiny
        two-point piece - 83 fragments per sensor on a two-sensor test -
        and quietly drops slivers where the two boundaries are only
        almost coincident, losing ~0.2% of the perimeter. Fragments are
        not cosmetic either: PAL would have 83 candidate places to put
        one sensor's label.

    So the merged boundary is walked once and each of its vertices
    attributed to whichever sensor contributed it - a union preserves
    its inputs' vertices, so a lookup from coordinate to sensor settles
    almost every one, and the handful of new vertices GEOS creates where
    two boundaries cross simply continue the previous run. Consecutive
    vertices with the same owner become that sensor's arc.

    That makes the shares a true PARTITION: they reconstruct the merged
    perimeter exactly, with nothing lost and nothing duplicated, and
    coverage cannot vanish however the footprints overlap. Two
    coincident sensors give one of them the whole ring and the other
    nothing - the perimeter is still drawn in full, which is the part
    that matters.

    Other affiliations are deliberately NOT merged in. A hostile
    footprint lying over a friendly one does not erase the friendly
    perimeter - the two are separate overlays, and the friendly
    boundary is still drawn there, so it still deserves its label.

    Together these segments ARE the merged perimeter, cut per sensor -
    which is why coverage needs no polygon layer of its own. Their union
    is exactly the boundary a unioned polygon would have had (pinned by
    test: for sensors that are not coincident, the segment lengths sum
    to the merged boundary's own length), and since coverage is drawn
    outline-only, drawing them as lines is indistinguishable from
    drawing that polygon's outline. Collapsing the two into one layer is
    the maintainer's own request 2026-08-20 - "that's too many layers".

    A sensor whose footprint is wholly inside a same-side neighbour's
    contributes nothing and is skipped. An UNNAMED sensor is kept,
    because its stretch of the perimeter still has to be drawn - it
    simply labels as nothing.
    """

    segments = []

    # AFFILIATION_COLORS' own order, so the output is stable rather than
    # following whatever order the sensors happen to be digitized in.
    for affiliation in AFFILIATION_COLORS:

        same_side = [
            (designation, geometry)
            for own, designation, geometry in footprints
            if own == affiliation
        ]

        if not same_side:
            continue

        merged = QgsGeometry.unaryUnion(
            [geometry for _, geometry in same_side]
        )

        if merged is None or merged.isEmpty():
            continue

        merged_boundary = _outward_boundary(merged)

        if merged_boundary is None or merged_boundary.isEmpty():
            continue

        owners = _vertex_owners(same_side)

        for ring in merged_boundary.asGeometryCollection():

            for owner, points in _runs_by_owner(ring.asPolyline(), owners):

                segments.append(
                    (
                        affiliation,
                        same_side[owner][0],
                        QgsGeometry.fromPolylineXY(points),
                    )
                )

    return segments


def _outward_boundary(polygon):

    """
    `polygon` as a line, with every exterior ring running clockwise.

    forceRHR() first because label side is decided by the direction of
    travel along the line - "above" means to the LEFT of it - so without
    a consistent ring orientation some sensors' labels land outside the
    coverage and others inside it. Confirmed by render 2026-08-20: three
    sensors, two labelled outside and one sitting in the middle of the
    fill.
    """

    oriented = QgsGeometry(polygon)

    oriented = oriented.forceRHR()

    # destMultipart=True is not optional here. Converting a MULTI-polygon
    # with it left False returns an empty geometry rather than failing,
    # and two sensors far enough apart not to overlap merge into exactly
    # that - so their coverage silently came out as nothing at all.
    return oriented.convertToType(
        Qgis.GeometryType.Line,
        True
    )


# The sensor's own position, in the two forms this plugin's users read
# coordinates in. Requested by the maintainer 2026-08-21.
#
# Done with QGIS's own default-value expressions rather than in Python,
# and crucially with applyOnUpdate=True: that makes QGIS recompute them
# whenever the feature changes, so they FOLLOW the sensor when it is
# dragged instead of recording where it was first dropped. No signal
# handling of ours is involved, and they survive a project reload the
# same way any other field configuration does.
#
# transform() to WGS84 explicitly rather than reading $x/$y: the points
# layer takes the project's CRS, which is very often not WGS84, and
# $x/$y would then be metres in some projection rather than degrees.
_LONGITUDE_EXPRESSION = (
    "x(transform($geometry, layer_property(@layer, 'crs'), 'EPSG:4326'))"
)

_LATITUDE_EXPRESSION = (
    "y(transform($geometry, layer_property(@layer, 'crs'), 'EPSG:4326'))"
)

_MGRS_EXPRESSION = (
    f"mct_mgrs({_LATITUDE_EXPRESSION}, {_LONGITUDE_EXPRESSION})"
)

_LOCATION_FIELDS = (
    ("latitude", _LATITUDE_EXPRESSION, "Latitude (°)"),
    ("longitude", _LONGITUDE_EXPRESSION, "Longitude (°)"),
    ("mgrs", _MGRS_EXPRESSION, "MGRS"),
)


def _configure_location_fields(layer):

    """
    Latitude, longitude and MGRS, derived from the sensor's own position
    and marked read-only in the form - they describe where the sensor
    is, so the way to change them is to move the sensor.
    """

    fields = layer.fields()

    form_config = layer.editFormConfig()

    for name, expression, alias in _LOCATION_FIELDS:

        index = fields.indexOf(name)

        layer.setDefaultValueDefinition(
            index,
            QgsDefaultValue(expression, True)
        )

        layer.setFieldAlias(index, alias)

        form_config.setReadOnly(index, True)

    layer.setEditFormConfig(form_config)


def _vertex_key(point):

    # Rounded, because the merged boundary's coordinates come back
    # through GEOS and need not be bit-identical to the inputs that
    # produced them. Nine places is far finer than any DEM pixel and far
    # coarser than the noise.
    return (round(point.x(), 9), round(point.y(), 9))


def _vertex_owners(same_side):

    """
    {vertex key: index into same_side} for every vertex of every
    footprint's boundary - the lookup that attributes each stretch of
    the merged perimeter to the sensor it came from.

    First writer wins, so two sensors that contributed the same vertex
    (coincident footprints) resolve to the earlier one rather than
    flickering between them.
    """

    owners = {}

    for index, (_, geometry) in enumerate(same_side):

        boundary = _outward_boundary(geometry)

        if boundary is None or boundary.isEmpty():
            continue

        for ring in boundary.asGeometryCollection():

            for point in ring.asPolyline():

                owners.setdefault(_vertex_key(point), index)

    return owners


def _runs_by_owner(points, owners):

    """
    [(owner index, [points])] - `points` cut into consecutive runs
    belonging to one sensor each.

    A vertex GEOS invented (where two boundaries cross, so it is in no
    input) continues the run it is in rather than starting one; that
    keeps a crossing from splitting an arc in two over a single point.
    Each run carries the vertex that starts the next one, so the arcs
    meet instead of leaving a pixel-wide gap between them.
    """

    runs = []

    current = None

    for point in points:

        owner = owners.get(_vertex_key(point), current)

        if owner is None:
            # Nothing has been attributed yet and this vertex is not in
            # any input - wait for one that is.
            continue

        if owner != current:

            if runs:
                # Close the previous run ON this vertex, so consecutive
                # arcs share an endpoint.
                runs[-1][1].append(point)

            runs.append((owner, [point]))

            current = owner

        else:

            runs[-1][1].append(point)

    # A ring's first and last runs are the same stretch of perimeter
    # when they share an owner; joining them avoids splitting one arc
    # across the ring's arbitrary start point.
    if len(runs) > 1 and runs[0][0] == runs[-1][0]:

        runs[0] = (runs[0][0], runs[-1][1] + runs[0][1])

        runs.pop()

    return [
        (owner, points)
        for owner, points in runs
        if len(points) > 1
    ]


def _build_coverage_layer(segments, level, opacity):

    """
    One LINE layer holding every sensor's own stretch of the merged
    perimeter - the whole of this level's coverage, and its labels, in
    a single layer.

    It used to be two: a polygon carrying the merged shape, plus a line
    layer carrying per-sensor arcs purely so each sensor could label its
    own. The polygon stopped earning its place the moment coverage went
    outline-only, since these arcs already draw exactly the outline it
    had (see _perimeter_segments()). Dropping it means no fill is
    possible here any more - accepted by the maintainer 2026-08-20, who
    noted the Viewshed tool remains available for a filled product.
    """

    if not segments:
        return None

    layer = QgsVectorLayer(
        f"LineString?crs={WGS84.authid()}",
        coverage_layer_name(level),
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    features = []

    for affiliation, designation, geometry in segments:

        feature = QgsFeature(layer.fields())

        feature.setGeometry(geometry)

        feature["affiliation"] = affiliation
        feature["unique_designation"] = designation

        features.append(feature)

    layer.dataProvider().addFeatures(features)

    layer.updateExtents()

    _apply_coverage_style(layer, level, opacity)

    _apply_designation_labels(layer)

    return layer


def _apply_coverage_style(layer, level, opacity):

    """
    The perimeter itself: this level's own width and dash pattern (see
    SENSOR_LEVELS), coloured per feature from its own affiliation.
    """

    symbol = QgsLineSymbol.createSimple(
        {
            "line_width": str(level.width_mm),
            "line_width_unit": "MM",
        }
    )

    line_layer = symbol.symbolLayer(0)

    line_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeColor,
        QgsProperty.fromExpression(
            affiliation_color_expression()
        )
    )

    if level.dash_mm is not None:

        # Qt's own pen styles have no long/short dash distinction, so
        # the pattern is given explicitly as [on, off] millimetre runs.
        line_layer.setUseCustomDashPattern(True)

        line_layer.setCustomDashPatternUnit(
            Qgis.RenderUnit.Millimeters
        )

        line_layer.setCustomDashVector(
            list(level.dash_mm)
        )

    layer.renderer().setSymbol(symbol)

    layer.setOpacity(opacity)

    layer.triggerRepaint()


def _apply_designation_labels(layer):

    """
    Curved labels riding just above the perimeter, in each segment's own
    affiliation colour with a white buffer so they stay readable over
    any terrain rendering underneath. A segment whose sensor has no
    designation simply labels as nothing.

    `displayAll` is the important one: PAL's default collision handling
    silently DROPS labels it cannot place, and these arcs are exactly
    the case that provokes it - several of them share endpoints and run
    close together wherever coverages meet. The same setting rescued the
    nested dose-rate contours (see docs/roadmap.md); the maintainer
    asked for it here by name.
    """

    settings = QgsPalLayerSettings()

    settings.fieldName = 'upper("unique_designation")'
    settings.isExpression = True

    settings.placement = Qgis.LabelPlacement.Line

    line_settings = settings.lineSettings()

    # AboveLine keeps the whole label clear of the perimeter rather than
    # straddling it. MapOrientation is deliberately NOT set: it makes
    # "above" mean north-of-the-line instead of left-of-the-direction-of-
    # travel, which on a closed ring puts roughly half the labels inside
    # the coverage. _perimeter_segments() orients every ring clockwise
    # instead, which makes left-of-travel consistently OUTSIDE.
    line_settings.setPlacementFlags(
        Qgis.LabelLinePlacementFlag.AboveLine
    )

    # A perimeter arc can be short - a sensor barely breaking the
    # surface of a much larger one's footprint - and PAL will not place
    # a label on a line shorter than the text unless allowed to overrun
    # its ends.
    line_settings.setOverrunDistance(DESIGNATION_LABEL_OVERRUN_MM)
    line_settings.setOverrunDistanceUnit(Qgis.RenderUnit.Millimeters)

    settings.setLineSettings(line_settings)

    settings.dist = DESIGNATION_LABEL_DISTANCE_MM
    settings.distUnits = Qgis.RenderUnit.Millimeters

    settings.displayAll = True

    text_format = build_text_format(
        DESIGNATION_LABEL_FONT_SIZE,
        bold=True
    )

    buffer_settings = text_format.buffer()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(DESIGNATION_LABEL_BUFFER_MM)
    buffer_settings.setSizeUnit(Qgis.RenderUnit.Millimeters)
    buffer_settings.setColor(QColor(255, 255, 255))
    text_format.setBuffer(buffer_settings)

    settings.setFormat(text_format)

    # Text colour follows each segment's own affiliation, the same way
    # the perimeter does - a hostile sensor's name has to read as
    # hostile even where its arc runs alongside a friendly one.
    settings.dataDefinedProperties().setProperty(
        QgsPalLayerSettings.Property.Color,
        QgsProperty.fromExpression(
            affiliation_color_expression()
        )
    )

    layer.setLabeling(
        QgsVectorLayerSimpleLabeling(settings)
    )

    layer.setLabelsEnabled(True)


def generate_sensor_coverage(
    dem_layer,
    points_layer,
    level,
    opacity=COVERAGE_OPACITY
):

    """
    Build this level's "Sensor Coverage" line layer from every sensor on
    points_layer, against the one shared dem_layer: each sensor's own
    stretch of the merged perimeter, coloured by its affiliation and
    labelled with its designation.

    Returns None when nothing is visible from anywhere - an empty points
    layer, or every sensor outside the DEM - so a caller can leave
    whatever is already drawn alone instead of replacing it with an
    empty layer.

    Deliberately does NOT add the layer to the project; see
    core/_layer_utils.py's module docstring.
    """

    footprints = _sensor_footprints(
        dem_layer,
        points_layer,
        level
    )

    return _build_coverage_layer(
        _perimeter_segments(footprints),
        level,
        opacity
    )


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
