# -*- coding: utf-8 -*-

"""
Builds a ready-to-use layer for MIL-STD-2525D Appendix H.5.20 (Table
H-XVIII, "Target acquisition control measure symbols") - Mini-Phase
H13/H14, the thirteenth H.5.x logical group in this appendix-by-
appendix pass.

**Areas only - 12 measure types, every one of them the identical
"freeform outline + prefix + optional name" construction already
proven throughout this appendix**, each folding a separate Irregular/
Rectangle/Circular SIDC code triple into one measure type (the same
reasoning used throughout - these render pixel-identically once only
the boundary shape differs): Artillery Target Intelligence Zone
(241101/102/103, "ATI"), Call For Fire Zone (241201/202/203, "CFF
ZONE" - the standard's own template text, not "CFFZ"), Censor Zone
(241301/302/303, "CENSOR ZONE"), Critical Friendly Zone (241401/402/
403, "CF ZONE"), Dead Space Area (241501/502/503, "DA"), Sensor Zone
(241601/602/603, "SENSOR ZONE"), Target Build-up Area (241701/702/703,
"TBA"), Target Value Area (241801/802/803, "TVAR"), Zone of
Responsibility (241901/902/903, "ZOR"), Terminally Guided Munition
Footprint (242000, "TGMF"), Blue Kill Box (242301/302/303, "BKB"),
Purple Kill Box (242304/305/306, "PKB").

**Terminally Guided Munition Footprint was missed entirely** when this
mini-phase was first built - not curated out and recorded like the two
Weapon/Sensor Range Fans below, just absent, with nothing in this
docstring acknowledging it. Added 2026-08-12 on the maintainer's own
report. It is the one measure type here with a SINGLE code rather than
an Irregular/Rectangle/Circular triple, which is probably how it fell
through a pass that was reading the table in code-triples. Its own
construction is the same freeform outline + centred prefix as every
other entry, so it needed no new technique. Its template shows no Field
T box, unlike its siblings; the optional name is still offered here for
uniformity with the rest of the layer, and simply stays unused if left
blank. The prefix text is
kept exactly as each measure type's own template/example shows it,
rather than forced onto one uniform abbreviation scheme - the standard
itself is inconsistent here (some spell the word "ZONE" out, others
don't).

**Two entries skipped outright**: **Weapon/Sensor Range Fan - Circular
(242100)** and **Weapon/Sensor Range Fan - Sector (242200)** both need
genuinely parametric/computed geometry from a single anchor point - one
or more concentric range RINGS (Circular) or a pie-shaped SECTOR with
an azimuth-defined centreline plus left/right limits and multiple range
arcs (Sector) - not a freeform polygon a user directly digitizes. The
same "doesn't fit this project's own techniques" reasoning already
applied to H4's Contain/Retain (also a computed-circle construct).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsGeometryGeneratorSymbolLayer,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsProject,
    QgsProperty,
    QgsRuleBasedLabeling,
    QgsSimpleLineSymbolLayer,
    QgsSingleSymbolRenderer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtGui import QColor

from qgis.PyQt.QtCore import QMetaType

from ._control_measure_shared import (
    AFFILIATION_LABELS,
    STATUS_LABELS,
    _PLAIN_DESIGNATION_LABEL_EXPRESSION,
    _configure_affiliation_field,
    _configure_designation_labeling,
    _configure_status_field,
    _build_pal_layer_settings,
    _build_rule_based_renderer,
    _apply_affiliation_color,
    _STATUS_LINE_STYLE_EXPRESSION,
    _status_driven_area_outline_symbol,
    _value_map,
    add_layer_if_absent,
)


AREAS_LAYER_NAME = "Target Acquisition Control Measures (Areas)"

__all__ = [
    "AREAS_LAYER_NAME",
    "AREA_MEASURE_TYPE_LABELS",
    "AFFILIATION_LABELS",
    "STATUS_LABELS",
    "create_target_acquisition_control_measures_areas_layer",
    "add_target_acquisition_control_measures_areas_layer",
]

AREA_MEASURE_TYPE_LABELS = {
    "ati": "Artillery Target Intelligence Zone (ATI)",
    "cffz": "Call For Fire Zone (CFFZ)",
    "censor_zone": "Censor Zone",
    "cfz": "Critical Friendly Zone (CFZ)",
    "dead_space_area": "Dead Space Area (DA)",
    "sensor_zone": "Sensor Zone",
    "tba": "Target Build-up Area (TBA)",
    "tvar": "Target Value Area (TVAR)",
    "zor": "Zone of Responsibility (ZOR)",
    "tgmf": "Terminally Guided Munition Footprint (TGMF)",
    "blue_kill_box": "Blue Kill Box (BKB)",
    "purple_kill_box": "Purple Kill Box (PKB)",
}

_AREA_LABEL_PREFIXES = {
    "ati": "ATI",
    "cffz": "CFF ZONE",
    "censor_zone": "CENSOR ZONE",
    "cfz": "CF ZONE",
    "dead_space_area": "DA",
    "sensor_zone": "SENSOR ZONE",
    "tba": "TBA",
    "tvar": "TVAR",
    "zor": "ZOR",
    "tgmf": "TGMF",
    "blue_kill_box": "BKB",
    "purple_kill_box": "PKB",
}

_AREA_DESIGNATION_LABEL_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"measure_type\" = '{measure_type}' THEN "
    f"'{prefix}' || CASE WHEN \"unique_designation\" IS NOT NULL"
    " AND \"unique_designation\" != '' THEN"
    f" '\\n' || {_PLAIN_DESIGNATION_LABEL_EXPRESSION} ELSE '' END"
    for measure_type, prefix in _AREA_LABEL_PREFIXES.items()
) + " ELSE '' END"

_AREA_SYMBOL_BUILDERS = {
    measure_type: _status_driven_area_outline_symbol
    for measure_type in AREA_MEASURE_TYPE_LABELS
}


# ---------------------------------------------------------------
# Weapon/Sensor Range Fans - 242100 (Circular) and 242200 (Sector)
# ---------------------------------------------------------------

RANGE_FANS_LAYER_NAME = "Weapon/Sensor Range Fans"

# **Both codes are ONE symbol here, not two.** The maintainer's own
# construction, dictated 2026-08-14: the user clicks the centre and
# fills in up to five rings, each with a left angle, a right angle, a
# range and an altitude. A ring left at the 0/360 default draws as a
# full CIRCLE - which is Circular (242100); any other pair of angles
# draws a SECTOR with straight sides back to the centre, which is
# Sector (242200). Nothing distinguishes them but the numbers typed,
# so nothing here distinguishes them either.
#
# Why these were deferred when the rest of Table H-XVIII was built:
# they need genuinely computed geometry rather than a boundary the user
# digitizes. This is the construction that unblocks them.
RANGE_FAN_MAX_RINGS = 5

# **The range is in METRES, and that is an assumption worth naming.**
# The construction says the ring is drawn "based on the map scale" -
# a real ground distance rather than a page unit, which is unique in
# this appendix - but never gives the unit. Metres is the conventional
# one for weapon and sensor ranges and for Table H-XXI's own Minimum
# Safe Distance Zone beside it. One constant if it should be otherwise.
RANGE_FAN_RANGE_UNIT = "m"

_RING_FIELDS = ("left", "right", "range", "alt")

_RANGE_FAN_LINE_WIDTH_MM = 0.4


def _ring_field(ring, name):

    return f"ring{ring}_{name}"


def _ring_geometry_expression(ring):

    return (
        "mct_range_fan_ring($geometry, \"{left}\", \"{right}\", "
        "\"{range}\")"
    ).format(
        left=_ring_field(ring, "left"),
        right=_ring_field(ring, "right"),
        range=_ring_field(ring, "range"),
    )


def _ring_layer(ring):

    """One ring, as its own geometry generator."""

    line = QgsSimpleLineSymbolLayer()

    line.setColor(QColor(0, 0, 0))

    line.setWidth(_RANGE_FAN_LINE_WIDTH_MM)

    _apply_affiliation_color(line, [QgsSymbolLayer.Property.StrokeColor])

    line.setDataDefinedProperty(
        QgsSymbolLayer.Property.StrokeStyle,
        QgsProperty.fromExpression(_STATUS_LINE_STYLE_EXPRESSION)
    )

    inner = QgsLineSymbol()

    inner.changeSymbolLayer(0, line)

    generator = QgsGeometryGeneratorSymbolLayer.create({})

    generator.setSymbolType(Qgis.SymbolType.Line)

    generator.setGeometryExpression(_ring_geometry_expression(ring))

    generator.setSubSymbol(inner)

    return generator


def _range_fan_symbol():

    """
    The whole fan: one geometry-generator layer per ring.

    Five layers rather than one expression drawing all five, so a ring
    left blank simply returns an empty geometry and draws nothing -
    and so the five stay independently inspectable.
    """

    symbol = QgsMarkerSymbol()

    symbol.changeSymbolLayer(0, _ring_layer(1))

    for ring in range(2, RANGE_FAN_MAX_RINGS + 1):

        symbol.appendSymbolLayer(_ring_layer(ring))

    return symbol


def _ring_label_expression(ring):

    """
    "RG 5000" over "ALT 300" - the two lines the construction asks for,
    each dropped when its own value is empty rather than drawn as a
    bare unit.
    """

    range_field = _ring_field(ring, "range")
    alt_field = _ring_field(ring, "alt")

    return (
        "CASE WHEN \"{range}\" IS NULL OR \"{range}\" <= 0 THEN '' ELSE "
        "'RG ' || \"{range}\" || "
        "CASE WHEN \"{alt}\" IS NULL OR \"{alt}\" = '' THEN '' "
        "ELSE '\n' || 'ALT ' || \"{alt}\" END "
        "END"
    ).format(range=range_field, alt=alt_field)


def _ring_label_point_expression(ring):

    """
    Half way between this ring's radius and the one inside it, on the
    sector's own centreline - see mct_range_fan_label_point().
    """

    inner = (
        "coalesce(\"{}\", 0)".format(_ring_field(ring - 1, "range"))
        if ring > 1 else "0"
    )

    return (
        "mct_range_fan_label_point($geometry, \"{left}\", \"{right}\", "
        "\"{range}\", {inner})"
    ).format(
        left=_ring_field(ring, "left"),
        right=_ring_field(ring, "right"),
        range=_ring_field(ring, "range"),
        inner=inner,
    )


def _configure_range_fan_labeling(layer):

    """
    One label per RING, which means one rule per ring: QGIS places a
    single label per rule, and five rings want five. Each is positioned
    on its own ring's centreline and filtered to features where that
    ring actually has a range - the same per-rule, data-defined-position
    pattern Contain and Retain already use.
    """

    root_rule = QgsRuleBasedLabeling.Rule(None)

    for ring in range(1, RANGE_FAN_MAX_RINGS + 1):

        settings = _build_pal_layer_settings(
            layer,
            Qgis.LabelPlacement.OverPoint,
            _ring_label_expression(ring),
            label_geometry_expression=_ring_label_point_expression(ring),
            quadrant=Qgis.LabelQuadrantPosition.Over,
        )

        rule = QgsRuleBasedLabeling.Rule(settings)

        rule.setFilterExpression(
            "\"{range}\" IS NOT NULL AND \"{range}\" > 0".format(
                range=_ring_field(ring, "range")
            )
        )

        rule.setDescription(f"ring{ring}")

        root_rule.appendChild(rule)

    layer.setLabeling(QgsRuleBasedLabeling(root_rule))

    layer.setLabelsEnabled(True)


def create_range_fans_layer(name=RANGE_FANS_LAYER_NAME):

    """
    Weapon/Sensor Range Fans (242100 and 242200) - one clicked centre
    and up to five rings.

    **Five is a hard cap rather than a paging problem**: the
    maintainer's own instruction is that a sixth ring means a second
    symbol placed at the same point, so nothing here tries to be
    open-ended.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(f"Point?crs={crs.authid()}", name, "memory")

    attributes = [
        QgsField("affiliation", QMetaType.Type.QString),
        QgsField("status", QMetaType.Type.QString),
        QgsField("unique_designation", QMetaType.Type.QString),
    ]

    # Grouped ring by ring rather than field by field, so the attribute
    # form reads as the table of rows the construction describes -
    # left, right, range, alt - rather than four columns of five.
    for ring in range(1, RANGE_FAN_MAX_RINGS + 1):

        attributes.extend([
            QgsField(_ring_field(ring, "left"), QMetaType.Type.Double),
            QgsField(_ring_field(ring, "right"), QMetaType.Type.Double),
            QgsField(_ring_field(ring, "range"), QMetaType.Type.Double),
            QgsField(_ring_field(ring, "alt"), QMetaType.Type.QString),
        ])

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    # Every ring starts at the full circle, which is the default the
    # construction gives and the Circular code's own shape.
    for ring in range(1, RANGE_FAN_MAX_RINGS + 1):

        layer.setDefaultValueDefinition(
            layer.fields().indexOf(_ring_field(ring, "left")),
            QgsDefaultValue("0")
        )

        layer.setDefaultValueDefinition(
            layer.fields().indexOf(_ring_field(ring, "right")),
            QgsDefaultValue("360")
        )

    layer.setRenderer(QgsSingleSymbolRenderer(_range_fan_symbol()))

    _configure_range_fan_labeling(layer)

    return layer


def add_range_fans_layer(iface):

    return add_layer_if_absent(
        iface,
        RANGE_FANS_LAYER_NAME,
        create_range_fans_layer,
    )


def create_target_acquisition_control_measures_areas_layer(name=AREAS_LAYER_NAME):

    """
    A fresh, empty polygon layer for Table H-XVIII's own 12 zone/box
    measure types - see this module's own docstring for the full list
    and for the two entries skipped (both Weapon/Sensor Range Fan
    variants).
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Polygon?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("measure_type", QMetaType.Type.QString),
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("unique_designation", QMetaType.Type.QString),
            QgsField("area_km2", QMetaType.Type.Double),
            QgsField("perimeter_km", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    measure_type_idx = layer.fields().indexOf("measure_type")

    layer.setEditorWidgetSetup(
        measure_type_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(AREA_MEASURE_TYPE_LABELS)}
        )
    )

    layer.setDefaultValueDefinition(
        measure_type_idx,
        QgsDefaultValue("'ati'")
    )

    _configure_affiliation_field(layer)
    _configure_status_field(layer)

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("area_km2"),
        QgsDefaultValue("mct_area_km2($geometry)", True)
    )

    layer.setDefaultValueDefinition(
        layer.fields().indexOf("perimeter_km"),
        QgsDefaultValue("mct_perimeter_km($geometry)", True)
    )

    layer.setRenderer(
        _build_rule_based_renderer(layer, _AREA_SYMBOL_BUILDERS)
    )

    _configure_designation_labeling(
        layer,
        Qgis.LabelPlacement.OverPoint,
        _AREA_DESIGNATION_LABEL_EXPRESSION
    )

    return layer


def add_target_acquisition_control_measures_areas_layer(iface):

    return add_layer_if_absent(
        iface,
        AREAS_LAYER_NAME,
        create_target_acquisition_control_measures_areas_layer
    )
