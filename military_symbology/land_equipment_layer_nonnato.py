# -*- coding: utf-8 -*-

"""
Builds the "Land Equipment (Non-NATO)" point layer.

Its own module, same reasoning as land_unit_layer_nonnato.py: no frame
at all (vs Units' framed-but-unfilled rectangle), no echelon/status/
Combined Arms fields (none apply to Equipment - see
docs/non-nato-symbology-tracker.md's Part D). See
military_symbology/nonnato_symbol_engine.py for the actual rendering
logic, called via mct_nonnato_equipment_svg()
(expressions/nonnato_symbology_functions.py).

The mine family (three real APP-6E entities plus six synthetic icons,
all fixed MINE_GREEN regardless of affiliation) moved OUT to its own
"Mines and Obstacles (Non-NATO)" layer 2026-09-03 - see
mines_and_obstacles_layer_nonnato.py - along with Control Measure
Points' own Booby Trap, consolidating every fixed-green custom-icon
entity onto one layer regardless of which real symbol_set it used to
sit in. nonnato_symbol_engine.py's own rendering functions for all of
them are unchanged (layer-agnostic); only which QGIS layer offers them
changed.

Scope, deliberately narrow (see the rules record's "Required entities"
section): 56 entities - 6 non-tiered real APP-6E entities, 14 weapon
families with real Light/Medium/Heavy siblings (42 entities, each
family's own tier renamed up one per the settled weapon-tier rule -
Machine Gun included, its own tiers oddly bare-keyed ("light"/
"medium"/"heavy", not "machine_gun_light" etc.) in the 2525E table but
real siblings all the same - see the rules record's 2026-09-02
correction of an earlier, wrong "not one of the tiered families" call),
three synthetic entities built from Armoured Protected Vehicle's own
oval glyph (Bridge Layer Tank, Armoured Recce Vehicle, Armoured
Protection Vehicle (Wheeled), added 2026-09-03), three FULLY synthetic
Vehicle-family entities that replaced APP-6E's own real "vehicle"
entity ('B' Vehicle, 'C' Vehicle, Light Recce Vehicle, 2026-09-05) -
plus Jammer and
Radar (Land-scoped SIGINT), merged
in here 2026-09-02 once a two-entity layer stopped justifying its own
module ("merge sigint glyphs (since there are only two) with land
equipment"). Not the full 189-entity NATO vocabulary.

Reachable via the "Land" entry in the toolbar's "Non-NATO Symbols"
group (see plugin.py), or directly via
add_land_equipment_layer_nonnato(iface).

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSimpleMarkerSymbolLayer,
    QgsSimpleMarkerSymbolLayerBase,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsUnitTypes,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType, QPointF
from qgis.PyQt.QtGui import QColor

from ._control_measure_shared import configure_rotation_and_scale_fields
from ._point_symbol_layer import default_insert_position
from ..core._layer_utils import add_layer_at_default_position
from .land_unit_layer_nonnato import AFFILIATION_LABELS
from .nonnato_symbol_engine import (
    AFFILIATION_COLOURS,
    APV_WHEEL_CENTRE_XS,
    APV_WHEEL_CENTRE_Y,
    APV_WHEEL_DIAMETER,
    APV_WHEEL_STROKE_WIDTH,
    APV_WHEELED_ENTITY,
    ARMOURED_RECCE_VEHICLE_ENTITY,
    B_VEHICLE_ENTITY,
    BRIDGE_LAYER_TANK_ENTITY,
    C_VEHICLE_ENTITY,
    LIGHT_RECCE_VEHICLE_ENTITY,
    MOBILITY_LABELS,
    SIGINT_RADAR_ENTITY,
    nonnato_entity_size_multiplier_expression,
    stabilised_nonnato_size_expression,
)


LAYER_NAME = "Land Equipment (Non-NATO)"

DEFAULT_ENTITY = "tank"

# 20% bigger than every other non-NATO point layer's own 8.0mm default
# (Land Unit, SIGINT before its merge, Control Measure Points all still
# use 8.0) - requested live, 2026-09-02, specifically for this layer:
# "in land equipment, i want all the glyphs to be 20% bigger by
# default". The "scale" field (configure_rotation_and_scale_fields())
# still works exactly as before - 100% now means THIS size, not 8.0mm.
MARKER_SIZE_MM = 8.0 * 1.2

# Display labels for the 56 confirmed entities (54 Land Equipment's
# own, plus Jammer/Radar) - see this module's own docstring and
# docs/non-nato-symbology-tracker.md's "Required entities"/"Weapon
# light/medium/heavy tiers actually applied" notes for where every one
# of these came from. Real entity keys are sidc_2525e.py's own
# land_equipment keys, unchanged (render_nonnato_equipment_svg()'s own
# build_sidc() call resolves them directly) - only the label is
# renamed. The tier suffixes are NOT milsymbol/SIDC amplifiers - each
# tier is a genuinely separate real APP-6E entity key, so there is one
# dropdown row per tier, not a second field.
ENTITY_LABELS = {
    # --- Non-tiered real entities (6) - Land Equipment's own separate
    # "radar" entry (a physical radar system, distinct from SIGINT's
    # own Radar platform below) was removed 2026-09-02, at the
    # maintainer's own request, once the two read as visually the same
    # thing in practice: "remove radar and keep only radar (sigint)
    # since both are same; rename radar (sigint) as radar only". The
    # three real mine entities ("antipersonnel_land_mine", "land_mine",
    # "antitank_mine") moved out entirely 2026-09-03, along with the six
    # synthetic mine icons that used to sit below - see
    # mines_and_obstacles_layer_nonnato.py. The real "vehicle" entity
    # (a stadium hull on two small wheels) was dropped 2026-09-05 -
    # "remove the existing vehicle glyph, we will replace with 'B'
    # Vehicle and 'C' Vehicle" - see the Vehicle-family block below. ---
    "antennae": "Antennae",
    "armored_protected_vehicle": "Armoured Protected Vehicle",
    "bridge": "Bridge",
    "flame_thrower": "Flame Thrower",
    "improvised_explosives_device": "Improvised Explosives Device",
    "pack_animals": "Pack Animals",

    # --- 13 properly-prefixed weapon families x 3 tiers (39) - Machine
    # Gun is a 14th real tiered family, kept in its own block below
    # since its 2525E keys are oddly unprefixed, not grouped in here ---
    "air_defense_gun": "Air Defence Gun (Light)",
    "air_defense_gun_light": "Air Defence Gun (Medium)",
    "air_defense_gun_medium": "Air Defence Gun (Heavy)",
    "air_defense_missile_launcher": "Air Defence Missile Launcher (Light)",
    "air_defense_missile_launcher_light": "Air Defence Missile Launcher (Medium)",
    "air_defense_missile_launcher_medium": "Air Defence Missile Launcher (Heavy)",
    "antitank_gun": "Antitank Gun (Light)",
    "antitank_gun_light": "Antitank Gun (Medium)",
    "antitank_gun_medium": "Antitank Gun (Heavy)",
    "antitank_missile_launcher": "Antitank Missile Launcher (Light)",
    "antitank_missile_launcher_light": "Antitank Missile Launcher (Medium)",
    "antitank_missile_launcher_medium": "Antitank Missile Launcher (Heavy)",
    "antitank_rocket_launcher": "Antitank Rocket Launcher (Light)",
    "antitank_rocket_launcher_light": "Antitank Rocket Launcher (Medium)",
    "antitank_rocket_launcher_medium": "Antitank Rocket Launcher (Heavy)",
    "direct_fire_gun": "Field Gun (Light)",
    "direct_fire_gun_light": "Field Gun (Medium)",
    "direct_fire_gun_medium": "Field Gun (Heavy)",
    "grenade_launcher": "Grenade Launcher (Light)",
    "grenade_launcher_light": "Grenade Launcher (Medium)",
    "grenade_launcher_medium": "Grenade Launcher (Heavy)",
    "howitzer": "Howitzer (Light)",
    "howitzer_light": "Howitzer (Medium)",
    "howitzer_medium": "Howitzer (Heavy)",
    "missile_launcher": "Missile Launcher (Light)",
    "missile_launcher_light": "Missile Launcher (Medium)",
    "missile_launcher_medium": "Missile Launcher (Heavy)",
    "mortar": "Mortar (Light)",
    "mortar_light": "Mortar (Medium)",
    "mortar_medium": "Mortar (Heavy)",
    "recoilless_gun": "Recoilless Gun (Light)",
    "recoilless_gun_light": "Recoilless Gun (Medium)",
    "recoilless_gun_medium": "Recoilless Gun (Heavy)",
    "single_rocket_launcher": "Single Rocket Launcher (Light)",
    "single_rocket_launcher_light": "Single Rocket Launcher (Medium)",
    "single_rocket_launcher_medium": "Single Rocket Launcher (Heavy)",
    "tank": "Tank (Light)",
    "tank_light": "Tank (Medium)",
    "tank_medium": "Tank (Heavy)",

    # --- Machine Gun (3) - a real weight-class family after all (see
    # the rules record's 2026-09-02 correction of the correction):
    # sidc_2525e.py's own 2525E table keys its Light/Medium/Heavy
    # siblings as bare "light"/"medium"/"heavy", not the expected
    # "machine_gun_light" pattern every other family uses (sidc.py's
    # own 2525D table has them correctly prefixed as "machine_gun_
    # light" etc., same codes - 2525E's own extraction just dropped the
    # prefix for this one family). Same base -> Light, real-Light ->
    # Medium, real-Medium -> Heavy shift as the 13 properly-prefixed
    # families above; real Heavy ("heavy", 3 lines) dropped, same as
    # every other family's own real Heavy tier. ---
    "machine_gun": "Machine Gun (Light)",
    "light": "Machine Gun (Medium)",
    "medium": "Machine Gun (Heavy)",

    # --- Synthetic entities built from Armoured Protected Vehicle's
    # own "oval" glyph (3), requested live 2026-09-03 - see
    # nonnato_symbol_engine.py's own comment for the exact geometry of
    # each mark. ---
    BRIDGE_LAYER_TANK_ENTITY: "Bridge Layer Tank",
    ARMOURED_RECCE_VEHICLE_ENTITY: "Armoured Recce Vehicle",
    APV_WHEELED_ENTITY: "Armoured Protection Vehicle (Wheeled)",

    # --- The Vehicle family (3), requested live 2026-09-05, replacing
    # APP-6E's own real "vehicle" entity above. Unlike the three APV
    # variants, these are FULLY synthetic - no SIDC, no milsymbol call
    # at all, a complete SVG authored in nonnato_symbol_engine.py (see
    # its own _SYNTHETIC_VEHICLE_SVG) the same way the synthetic mine
    # family is. Rectangle at the Land Unit frame's own dimensions, two
    # wheels on APV Wheeled's own rule minus its middle wheel, and a
    # centred letter ('B'/'C') or - for Light Recce Vehicle - Armoured
    # Recce Vehicle's own "/" above the rectangle instead. ---
    B_VEHICLE_ENTITY: "'B' Vehicle",
    C_VEHICLE_ENTITY: "'C' Vehicle",
    LIGHT_RECCE_VEHICLE_ENTITY: "Light Recce Vehicle",

    # --- SIGINT, Land-scoped (2), merged in 2026-09-02 - real APP-6E
    # entities, but under symbol_set "sigint_land" rather than
    # "land_equipment" (see nonnato_symbol_engine.
    # _EQUIPMENT_SYMBOL_SET_OVERRIDES). SIGINT_RADAR_ENTITY's own STORED
    # key stays "sigint_radar" (not the literal "radar") purely to
    # match nonnato_symbol_engine._EQUIPMENT_ENTITY_KEY_ALIASES, which
    # resolves it to the real APP-6E entity "radar" at SIDC-build time -
    # its own DISPLAY LABEL is plain "Radar" now that Land Equipment's
    # own separate radar entry is gone (see this dict's own note above).
    "jammer": "Jammer",
    SIGINT_RADAR_ENTITY: "Radar",
}


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _configure_attribute_form(layer):

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("affiliation"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(AFFILIATION_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("affiliation"), QgsDefaultValue("'friend'")
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("entity"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(ENTITY_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("entity"), QgsDefaultValue(f"'{DEFAULT_ENTITY}'")
    )

    # Tracked / Self-Propelled, added 2026-09-06 - "they need to appear
    # as choice - maybe from a dropdown in the dialog box". Not entities
    # (any entity can carry one), so this is its own field rather than
    # more rows in the entity list. The empty string is the default and
    # means no mark at all.
    layer.setEditorWidgetSetup(
        fields.indexOf("mobility"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(MOBILITY_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("mobility"), QgsDefaultValue("''")
    )

    configure_rotation_and_scale_fields(layer)


# Per-entity size multipliers - Jammer/Radar up 1.8x, the Vehicle
# family down to 0.8x. Both the table and the CASE expression live in
# nonnato_symbol_engine now (2026-09-05): that module has to divide the
# same multiplier back out of the Vehicle family's own stroke width AND
# of every icon's own designation text, and keeping a second copy here
# is exactly how the designation text came to be wrong for that family.
# See NONNATO_ENTITY_SIZE_MULTIPLIERS for the reasoning behind each
# value. Only this layer's own entities get a branch.
_ENTITY_SIZE_MULTIPLIER_EXPRESSION = nonnato_entity_size_multiplier_expression(
    ENTITY_LABELS
)


# Armoured Protection Vehicle (Wheeled)'s own three wheels are their
# own QGIS simple-marker symbol layers, NOT circles drawn into the
# icon's own SVG - the same multi-layer composition this plugin's own
# NATO side already uses whenever an element has to be added to a
# milsymbol icon (c2_measures.py's own crossed runway lines are the
# closest precedent). **This is not a style preference, it is the only
# thing that works**: an SVG-internal circle drawn below milsymbol's
# own declared draw area is clipped by QGIS's own marker rendering no
# matter what the SVG's viewBox says - a real bug, caught by a smoke
# test ("the circles below the ellipse are not visible - the full
# circle is not being drawn, circles are being cropped"), then chased
# through six SVG-side workarounds (growing the viewBox, leaving
# width/height unchanged, dropping them entirely, circles-as-path-arcs,
# a second SVG marker layer, text glyphs) that all failed the same way,
# before the maintainer pointed at the NATO side's own established
# answer. Confirmed against a real render.
#
# Geometry comes from nonnato_symbol_engine.py's own APV_WHEEL_*
# constants, in milsymbol's own icon units, converted to millimetres
# here against this layer's own MARKER_SIZE_MM. Everything scales with
# the "scale" field exactly as the icon itself does; the wheels sit at
# size 0 for every other entity, which is how one shared symbol serves
# a whole layer's worth of different icons.
_ICON_VIEWBOX_WIDTH = 108.0

_MM_PER_ICON_UNIT = MARKER_SIZE_MM / _ICON_VIEWBOX_WIDTH

# The same six-colour palette render_nonnato_equipment_svg() itself
# resolves internally, restated as an expression so a plain QGIS marker
# layer can follow it too - the wheels have to match whatever colour
# the icon they hang off was drawn in.
_AFFILIATION_COLOUR_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"affiliation\" = '{affiliation}' THEN '{colour}'"
    for affiliation, colour in AFFILIATION_COLOURS.items()
) + f" ELSE '{AFFILIATION_COLOURS['friend']}' END"

# The SVG marker's own anchor is the CENTRE of its own viewBox, which
# is what a wheel's own offset is measured from. Horizontally that is
# fixed (the viewBox never grows sideways), but VERTICALLY it moves:
# inject_centered_designation_below() grows the viewBox downward to fit
# a typed designation, pushing the centre down and so shifting the icon
# itself UP on the map. A wheel at a fixed offset would stay put and
# end up over the text - reported live, 2026-09-03: "when i add the
# unique designator in APV wheeled, the wheels shift and overlap on the
# text of unique designation instead of staying where they are". So the
# vertical offset is computed per feature from the icon's own RENDERED
# height (mct_nonnato_equipment_svg_height()), not from a constant.
_ICON_ANCHOR_X = 100.0

# The viewBox's own y origin, which _expand_viewbox_for_rect() never
# moves for a below-the-icon addition (it only ever extends the height).
_ICON_VIEWBOX_Y = 46.0

_SCALE_FACTOR_EXPRESSION = 'coalesce("scale", 100) / 100.0'


def _wheel_symbol_layers():

    """
    One hollow circle marker layer per wheel - see this section's own
    comment above. Each is sized/offset in millimetres from the icon's
    own anchor, and data-defined so it collapses to nothing for every
    entity except Armoured Protection Vehicle (Wheeled).

    The vertical offset tracks the icon's own RENDERED height rather
    than a constant, so the wheels stay locked to the hull when a typed
    designation grows the viewBox and moves the anchor - see this
    section's own comment on _ICON_VIEWBOX_Y.
    """

    designation_expression = 'upper(coalesce("unique_designation", \'\'))'

    # Mobility is in here too: a Tracked/Self-Propelled mark grows the
    # viewBox downward exactly the way a designation does, moving the
    # marker's own anchor and so the hull the wheels have to stay with.
    rendered_height_expression = (
        'mct_nonnato_equipment_svg_height('
        f'"affiliation","entity",{designation_expression},'
        'coalesce("mobility", \'\')'
        ')'
    )

    # The anchor's own y, in icon units: the middle of whatever viewBox
    # this feature actually rendered with.
    anchor_y_expression = (
        f"({_ICON_VIEWBOX_Y:g} + ({rendered_height_expression}) / 2.0)"
    )

    offset_y_expression = (
        f"({APV_WHEEL_CENTRE_Y:g} - {anchor_y_expression}) "
        f"* {_MM_PER_ICON_UNIT:g} * ({_SCALE_FACTOR_EXPRESSION})"
    )

    layers = []

    for centre_x in APV_WHEEL_CENTRE_XS:

        wheel = QgsSimpleMarkerSymbolLayer(
            QgsSimpleMarkerSymbolLayerBase.Shape.Circle
        )

        wheel.setSize(APV_WHEEL_DIAMETER * _MM_PER_ICON_UNIT)
        wheel.setSizeUnit(QgsUnitTypes.RenderUnit.RenderMillimeters)

        wheel.setFillColor(QColor(0, 0, 0, 0))
        wheel.setStrokeWidth(APV_WHEEL_STROKE_WIDTH * _MM_PER_ICON_UNIT)
        wheel.setStrokeWidthUnit(QgsUnitTypes.RenderUnit.RenderMillimeters)

        offset_x = (centre_x - _ICON_ANCHOR_X) * _MM_PER_ICON_UNIT

        # A static fallback for the undrawn case (a symbol inspected
        # outside any feature context) - the data-defined pair below is
        # what actually renders.
        wheel.setOffset(QPointF(offset_x, 0.0))
        wheel.setOffsetUnit(QgsUnitTypes.RenderUnit.RenderMillimeters)

        wheel.setDataDefinedProperty(
            QgsSymbolLayer.Property.Size,
            QgsProperty.fromExpression(
                f"CASE WHEN \"entity\" = '{APV_WHEELED_ENTITY}' THEN "
                f"{APV_WHEEL_DIAMETER * _MM_PER_ICON_UNIT:g} * "
                f"({_SCALE_FACTOR_EXPRESSION}) ELSE 0 END"
            )
        )

        wheel.setDataDefinedProperty(
            QgsSymbolLayer.Property.Offset,
            QgsProperty.fromExpression(
                f"format('%1,%2', {offset_x:g} * ({_SCALE_FACTOR_EXPRESSION}), "
                f"{offset_y_expression})"
            )
        )

        wheel.setDataDefinedProperty(
            QgsSymbolLayer.Property.StrokeColor,
            QgsProperty.fromExpression(_AFFILIATION_COLOUR_EXPRESSION)
        )

        layers.append(wheel)

    return layers


def _build_renderer():

    designation_expression = 'upper(coalesce("unique_designation", \'\'))'

    # The Tracked/Self-Propelled mark, added 2026-09-06 - a fourth,
    # optional argument to the same three render functions (see
    # nonnato_symbol_engine.inject_mobility_indicator()).
    mobility_expression = 'coalesce("mobility", \'\')'

    expression = (
        'mct_nonnato_equipment_svg('
        f'"affiliation","entity",{designation_expression},'
        f'{mobility_expression}'
        ')'
    )

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(MARKER_SIZE_MM)

    scaled_size_expression = (
        f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'
        f' * ({_ENTITY_SIZE_MULTIPLIER_EXPRESSION})'
    )

    # Holds the icon still when a designation is typed in - see
    # stabilised_nonnato_size_expression()'s own docstring for the
    # 2026-09-02 fix this is (reported against Land Unit, applied
    # "across the board" per the maintainer's own instruction).
    amplified_width_expression = (
        'mct_nonnato_equipment_svg_width('
        f'"affiliation","entity",{designation_expression},'
        f'{mobility_expression}'
        ')'
    )

    # The designation-less counterpart still carries the mobility mark:
    # the ratio has to isolate what the DESIGNATION does to the icon's
    # width, and a mark the feature really has belongs on both sides of
    # it. (Neither mark widens the viewBox in practice - both are
    # narrower than the glyphs they hang off - but that is a property
    # of today's two marks, not something to bake in.)
    plain_width_expression = (
        'mct_nonnato_equipment_svg_width('
        f'"affiliation","entity",\'\',{mobility_expression}'
        ')'
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(
            stabilised_nonnato_size_expression(
                scaled_size_expression,
                amplified_width_expression,
                plain_width_expression,
            )
        )
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(expression)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Angle,
        QgsProperty.fromExpression('coalesce("rotation", 0)')
    )

    symbol.changeSymbolLayer(0, svg_layer)

    for wheel in _wheel_symbol_layers():
        symbol.appendSymbolLayer(wheel)

    return QgsSingleSymbolRenderer(symbol)


def build_land_equipment_layer_nonnato():

    """A fresh, empty "Land Equipment (Non-NATO)" layer - never added to the project itself, see add_land_equipment_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        LAYER_NAME,
        "memory"
    )

    attributes = [
        QgsField("affiliation", QMetaType.Type.QString),
        QgsField("entity", QMetaType.Type.QString),
        QgsField("unique_designation", QMetaType.Type.QString),
        QgsField("mobility", QMetaType.Type.QString),
        QgsField("rotation", QMetaType.Type.Double),
        QgsField("scale", QMetaType.Type.Double),
    ]

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_land_equipment_layer_nonnato(iface):

    """
    Guard-and-insert: if "Land Equipment (Non-NATO)" already exists,
    warns and does nothing; otherwise builds and inserts a fresh one.
    Returns the new layer, or None if one already existed.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(LAYER_NAME):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'A "{LAYER_NAME}" layer already exists - use the Layers '
            "panel to work with it, or rename it first if you want a "
            "second one."
        )

        return None

    layer = build_land_equipment_layer_nonnato()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
