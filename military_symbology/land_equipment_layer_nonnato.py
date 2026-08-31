# -*- coding: utf-8 -*-

"""
Builds the "Land Equipment (Non-NATO)" point layer.

Its own module, same reasoning as land_unit_layer_nonnato.py: no frame
at all (vs Units' framed-but-unfilled rectangle), no echelon/status/
Combined Arms fields (none apply to Equipment - see
docs/non-nato-symbology-tracker.md's Part D), and a mine family with
its own green-not-affiliation colour rule. See
military_symbology/nonnato_symbol_engine.py for the actual rendering
logic, called via mct_nonnato_equipment_svg()
(expressions/nonnato_symbology_functions.py).

Scope, deliberately narrow (see the rules record's "Required entities"
section): 58 entities - 12 non-tiered real APP-6E entities, 13 weapon
families with real Light/Medium/Heavy siblings (39 entities, each
family's own tier renamed up one per the settled weapon-tier rule),
Machine Gun's own three tiers (repurposed from the Rifle family's
fire-mode variants, not a real weight-class family - see the rules
record's 2026-09-01 correction), and five synthetic mine icons with no
APP-6E entity at all. Not the full 189-entity NATO vocabulary.

No toolbar action yet, same as Land Unit - reachable only by calling
add_land_equipment_layer_nonnato(iface) directly.

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsField,
    QgsMarkerSymbol,
    QgsProject,
    QgsProperty,
    QgsSingleSymbolRenderer,
    QgsSvgMarkerSymbolLayer,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from qgis.PyQt.QtCore import QMetaType

from ._control_measure_shared import configure_rotation_and_scale_fields
from ._point_symbol_layer import default_insert_position
from ..core._layer_utils import add_layer_at_default_position
from .land_unit_layer_nonnato import AFFILIATION_LABELS
from .nonnato_symbol_engine import (
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY,
    BAR_MINE_ENTITY,
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY,
    INFLUENCE_MINE_ANTI_TANK_ENTITY,
    UNKNOWN_MINE_ENTITY,
)


LAYER_NAME = "Land Equipment (Non-NATO)"

DEFAULT_ENTITY = "tank"

MARKER_SIZE_MM = 8.0

# Display labels for the 58 confirmed entities - see this module's own
# docstring and docs/non-nato-symbology-tracker.md's "Required
# entities"/"Weapon light/medium/heavy tiers actually applied" notes
# for where every one of these came from. Real entity keys are
# sidc_2525e.py's own land_equipment keys, unchanged (render_nonnato_
# equipment_svg()'s own build_sidc() call resolves them directly) -
# only the label is renamed. The tier suffixes are NOT milsymbol/SIDC
# amplifiers - each tier is a genuinely separate entity key (a real
# APP-6E sibling, or one of Machine Gun's repurposed Rifle siblings),
# so there is one dropdown row per tier, not a second field.
ENTITY_LABELS = {
    # --- Non-tiered real entities (11) ---
    "antennae": "Antennae",
    "antipersonnel_land_mine": "Antipersonnel Fragmentation Mine",
    "land_mine": "Antipersonnel Mine",
    "antitank_mine": "Antitank Mine",
    "armored_protected_vehicle": "Armoured Protected Vehicle",
    "bridge": "Bridge",
    "flame_thrower": "Flame Thrower",
    "improvised_explosives_device": "Improvised Explosives Device",
    "pack_animals": "Pack Animals",
    "radar": "Radar",
    "vehicle": "Vehicle",

    # --- 13 weapon families x 3 tiers (39) ---
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

    # --- Machine Gun (3) - repurposed Rifle fire-mode family, not a
    # real weight-class family (see the rules record's correction) ---
    "single_shot_rifle": "Machine Gun (Light)",
    "semiautomatic_rifle": "Machine Gun (Medium)",
    "automatic_rifle": "Machine Gun (Heavy)",

    # --- Synthetic mine icons (5), no APP-6E entity at all ---
    UNKNOWN_MINE_ENTITY: "Unknown Mine",
    INFLUENCE_MINE_ANTI_TANK_ENTITY: "Influence Mine (Anti Tank)",
    INFLUENCE_MINE_ANTI_PERSONNEL_ENTITY: "Influence Mine (Anti Personnel)",
    ANTITANK_MINE_BOOBY_TRAPPED_ENTITY: "Antitank Mine Booby Trapped",
    BAR_MINE_ENTITY: "Bar Mine",
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

    configure_rotation_and_scale_fields(layer)


def _build_renderer():

    designation_expression = 'upper(coalesce("unique_designation", \'\'))'

    expression = (
        'mct_nonnato_equipment_svg('
        f'"affiliation","entity",{designation_expression}'
        ')'
    )

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(MARKER_SIZE_MM)

    scaled_size_expression = (
        f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(scaled_size_expression)
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
