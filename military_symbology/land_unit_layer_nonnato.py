# -*- coding: utf-8 -*-

"""
Builds the "Land Unit (Non-NATO)" point layer.

Deliberately its OWN module, not built through _point_symbol_layer.py's
shared NATO builder - the two schemes diverge too much to share that
code cleanly: six affiliations here, not milsymbol's four; a rectangle
frame with no fill rather than an affiliation-shaped, affiliation-
filled icon; renamed echelons; a Solid/Dashed status rather than
Present/Planned; and a Combined Arms checkbox with no NATO equivalent
at all. See docs/non-nato-symbology-tracker.md for the full rules
record every choice below is drawn from, and
military_symbology/nonnato_symbol_engine.py for the actual rendering
logic this layer's renderer calls into via mct_nonnato_unit_svg()
(expressions/nonnato_symbology_functions.py).

Scope for this first pass, deliberately narrow (see the rules record's
"Required entities" section): the 20 APP-6E ground_unit entities the
maintainer's reviewed check sheet confirmed, plus Enemy (Info
Unknown), a standalone frame variant with no APP-6E entity at all.
Every other Land Unit entity is out of scope until the maintainer adds
it - this is not the full 187-entity vocabulary the NATO Land Unit
layer offers.

Not yet built (deliberately deferred, not an oversight): headquarters/
sector1/sector2 modifiers - worth adding once this layer is otherwise
proven out, not before. Icon-size stabilisation for a typed
designation WAS missing at first ("No icon-size stabilisation for a
typed designation yet" in an earlier version of this file), then fixed
2026-09-02 once the maintainer actually hit it live - see
nonnato_symbol_engine.stabilised_nonnato_size_expression()'s own
docstring.

No toolbar action yet either - reachable only by calling
add_land_unit_layer_nonnato(iface) directly (e.g. from QGIS's own
Python console), by the maintainer's own request, until this branch's
non-NATO work is further along.

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
from .nonnato_symbol_engine import (
    ENEMY_INFO_UNKNOWN_ENTITY,
    stabilised_nonnato_size_expression,
)


LAYER_NAME = "Land Unit (Non-NATO)"

DEFAULT_ENTITY = "infantry"

MARKER_SIZE_MM = 8.0

# Display labels for the 20 real APP-6E entities the reviewed check
# sheet confirmed, plus Enemy (Info Unknown). Entity KEYS are the real
# ground_unit keys sidc_2525e.py already defines (unchanged, so
# render_nonnato_unit_svg()'s own build_sidc() call resolves them
# directly) - only the LABEL a user reads in the dropdown is renamed,
# same convention as every other vocabulary dict in this project. See
# the rules record's "Required entities"/"Renamed"/"Icon modifications"
# notes for where each one of these came from.
ENTITY_LABELS = {
    "air_defense": "Air Defence",
    "ammunition": "Ammunition",
    "amphibious": "Amphibious",
    "armor_mechanized": "Armour",
    "armored_mechanized_tracked": "Mechanised Infantry",
    "aviation_fixed_wing": "Army Aviation",
    "counterintelligence": "Counterintelligence",
    "electronic_warfare": "Electronic Warfare",
    "engineer": "Engineer",
    "field_artillery": "Artillery",
    "infantry": "Infantry",
    "maintenance": "EME",
    "mechanized": "Armoured/Assault Engineers",
    "medical": "Medical",
    "military_intelligence": "Military Intelligence",
    "military_police": "Military Police",
    "parachute_rigger": "Parachute Rigger",
    "reconnaissance_cavalry_scout": "Light Armour/Recce & Support (Tracked)",
    "signal": "Signal",
    "special_operations_forces": "Special Operations Forces",
    ENEMY_INFO_UNKNOWN_ENTITY: "Enemy (Info Unknown)",
}

# Six affiliations, not milsymbol's own four - see
# nonnato_symbol_engine.AFFILIATION_COLOURS for the colour each maps
# to. Stored keys match that dict's own, so the renderer expression
# can pass the field value straight through with no translation.
AFFILIATION_LABELS = {
    "friend": "Friendly",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
    "friendly_paramilitary": "Friendly Paramilitary",
    "nonstate_hostile": "Non-state Hostile",
}

# Renamed from NATO's own list - stored keys are unchanged (the same
# ones sidc.py's ECHELONS/build_sidc() use), only the label differs.
# NATO's own Section/Regiment/Theater/Command are dropped (their names
# were reused above), so they simply don't appear here at all.
ECHELON_LABELS = {
    "unspecified": "Unspecified",
    "team_crew": "Detachment",
    "squad": "Section",
    "platoon": "Platoon/Troop",
    "company": "Company/Battery/Flight/Squadron",
    "battalion": "Battalion/Regiment/Avn Squadron",
    "brigade": "Brigade",
    "division": "Division",
    "corps": "Corps",
    "army": "Command",
    "army_group": "Army Group",
}

# Present/Planned, renamed after the line style itself rather than the
# unit's own status - same stored keys as sidc.py's STATUS.
STATUS_LABELS = {
    "present": "Solid",
    "planned": "Dashed",
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

    layer.setEditorWidgetSetup(
        fields.indexOf("echelon"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(ECHELON_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("echelon"), QgsDefaultValue("'unspecified'")
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("status"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(STATUS_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("status"), QgsDefaultValue("'present'")
    )

    layer.setEditorWidgetSetup(
        fields.indexOf("combined_arms"),
        QgsEditorWidgetSetup("CheckBox", {})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("combined_arms"), QgsDefaultValue("false")
    )

    configure_rotation_and_scale_fields(layer)


def _build_renderer():

    # Field values are passed straight through - affiliation/entity/
    # echelon/status all use the same stored keys render_nonnato_unit_
    # svg() itself expects, per the label dicts above.
    designation_expression = 'upper(coalesce("unique_designation", \'\'))'

    expression = (
        'mct_nonnato_unit_svg('
        '"affiliation","entity","echelon","status",'
        f'{designation_expression},"combined_arms"'
        ')'
    )

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(MARKER_SIZE_MM)

    # U-2's own "scale" field (percent, 100 = unchanged) - same
    # convention as every other point-symbol layer in this plugin.
    scaled_size_expression = (
        f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'
    )

    # Holds the icon still when a designation is typed in - see
    # stabilised_nonnato_size_expression()'s own docstring for the
    # 2026-09-02 fix this is. The "plain" call below passes '' for
    # designation (not "combined_arms"'s own field - Combined Arms
    # widens the icon too, but by drawing a rectangle around it, not by
    # milsymbol's own text-box widening, so it is correctly left as a
    # live field reference on both sides and cancels out of the ratio).
    amplified_width_expression = (
        'mct_nonnato_unit_svg_width('
        '"affiliation","entity","echelon","status",'
        f'{designation_expression},"combined_arms"'
        ')'
    )

    plain_width_expression = (
        'mct_nonnato_unit_svg_width('
        '"affiliation","entity","echelon","status",'
        '\'\',"combined_arms"'
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

    return QgsSingleSymbolRenderer(symbol)


def build_land_unit_layer_nonnato():

    """A fresh, empty "Land Unit (Non-NATO)" layer - never added to the project itself, see add_land_unit_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        LAYER_NAME,
        "memory"
    )

    attributes = [
        QgsField("affiliation", QMetaType.Type.QString),
        QgsField("entity", QMetaType.Type.QString),
        QgsField("echelon", QMetaType.Type.QString),
        QgsField("status", QMetaType.Type.QString),
        QgsField("combined_arms", QMetaType.Type.Bool),
        QgsField("unique_designation", QMetaType.Type.QString),
        QgsField("rotation", QMetaType.Type.Double),
        QgsField("scale", QMetaType.Type.Double),
    ]

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_land_unit_layer_nonnato(iface):

    """
    Guard-and-insert: if "Land Unit (Non-NATO)" already exists, warns
    and does nothing (same reasoning as add_single_domain_point_layer()
    - this is hand-placed operational data, not safe to silently
    replace); otherwise builds and inserts a fresh one. Returns the new
    layer, or None if one already existed.
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

    layer = build_land_unit_layer_nonnato()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
