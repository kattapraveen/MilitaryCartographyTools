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
APP-6E entity at all - plus Jammer and Radar (Land-scoped SIGINT),
merged in here 2026-09-02 once a two-entity layer stopped justifying
its own module ("merge sigint glyphs (since there are only two) with
land equipment"). Not the full 189-entity NATO vocabulary.

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
    SIGINT_RADAR_ENTITY,
    UNKNOWN_MINE_ENTITY,
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
    # --- Non-tiered real entities (10) - Land Equipment's own separate
    # "radar" entry (a physical radar system, distinct from SIGINT's
    # own Radar platform below) was removed 2026-09-02, at the
    # maintainer's own request, once the two read as visually the same
    # thing in practice: "remove radar and keep only radar (sigint)
    # since both are same; rename radar (sigint) as radar only". ---
    "antennae": "Antennae",
    "antipersonnel_land_mine": "Antipersonnel Fragmentation Mine",
    "land_mine": "Antipersonnel Mine",
    "antitank_mine": "Antitank Mine",
    "armored_protected_vehicle": "Armoured Protected Vehicle",
    "bridge": "Bridge",
    "flame_thrower": "Flame Thrower",
    "improvised_explosives_device": "Improvised Explosives Device",
    "pack_animals": "Pack Animals",
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

    configure_rotation_and_scale_fields(layer)


# Jammer/Radar (SIGINT, merged in 2026-09-02) read visibly smaller
# than every other Land Equipment icon at the same declared marker
# size, confirmed by measuring rendered pixel extents directly: both
# are a compact/bare glyph (a single letter, a small hooked line) that
# occupies a much smaller fraction of its own declared viewBox than a
# typical Equipment icon's own path does, even though every icon here
# shares the same declared width QGIS scales against. Reported live:
# "Jammer and radar (sigint) are still smaller than other land
# equipment, adjust them same as others". 1.8x brings their own
# measured bounding-box height roughly in line with the other
# entities' own average - a real measurement, not a guess, though
# still an approximation given how much bounding-box size already
# varies entity to entity even among icons nobody complained about.
_SIGINT_SIZE_MULTIPLIER = 1.8

_ENTITY_SIZE_MULTIPLIERS = {
    "jammer": _SIGINT_SIZE_MULTIPLIER,
    SIGINT_RADAR_ENTITY: _SIGINT_SIZE_MULTIPLIER,
}

_ENTITY_SIZE_MULTIPLIER_EXPRESSION = "CASE " + " ".join(
    f"WHEN \"entity\" = '{entity}' THEN {multiplier:g}"
    for entity, multiplier in _ENTITY_SIZE_MULTIPLIERS.items()
) + " ELSE 1 END"


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
        f' * ({_ENTITY_SIZE_MULTIPLIER_EXPRESSION})'
    )

    # Holds the icon still when a designation is typed in - see
    # stabilised_nonnato_size_expression()'s own docstring for the
    # 2026-09-02 fix this is (reported against Land Unit, applied
    # "across the board" per the maintainer's own instruction).
    amplified_width_expression = (
        'mct_nonnato_equipment_svg_width('
        f'"affiliation","entity",{designation_expression}'
        ')'
    )

    plain_width_expression = (
        "mct_nonnato_equipment_svg_width(\"affiliation\",\"entity\",'')"
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
