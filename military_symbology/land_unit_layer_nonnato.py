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

Scope, deliberately narrow (see the rules record's "Required entities"
section): 39 entities - the 20 APP-6E ground_unit entities the
maintainer's reviewed check sheet confirmed, plus nineteen with no
matching real ground_unit key of their own: the four Enemy entities
(Info Unknown, and Echelon / Designation / Type Unknown added
2026-09-06 - standalone frame variants with no APP-6E entity at all,
differing only in where a "?" sits), Air Defence Artillery, Air Force,
Motorised Infantry, Mountain Infantry, Recce & Support (Wheeled),
Administration or Logistics Unit, Static Formation Headquarters, Self
Propelled Artillery, Parachute Field Artillery, and six built on
Military Police's own framed glyph - Information Warfare, Postal Unit,
Intelligence, Supplies and Transport, Ordnance, and Remount and
Veterinary Corps (the last thirteen all 2026-09-06). Every other Land Unit entity is out of scope
until the maintainer adds it - this is not the full 187-entity
vocabulary the NATO Land Unit layer offers.

Not yet built (deliberately deferred, not an oversight): the
sector1/sector2 modifiers - worth adding once this layer is otherwise
proven out, not before. Headquarters WAS deferred here and is now
built (2026-09-06): a Bool field feeding build_sidc()'s own Field S,
same convention the NATO layers use. Icon-size stabilisation for a typed
designation WAS missing at first ("No icon-size stabilisation for a
typed designation yet" in an earlier version of this file), then fixed
2026-09-02 once the maintainer actually hit it live - see
nonnato_symbol_engine.stabilised_nonnato_size_expression()'s own
docstring.

A single "unique_designation" field (milsymbol's own side-anchored
uniqueDesignation slot) was replaced the same day with the two fields
below - "i want two unique designators - unique designator (left) and
unique designator (right)... both left and right designators should be
vertically middle aligned to the left or right of the glyph, the
present unique designator can be removed or ignored" - see
nonnato_symbol_engine.inject_side_designations().

Reachable via the "Land" entry in the toolbar's "Non-NATO Symbols"
group, which adds this layer and Land Equipment (Non-NATO) together
(see nonnato_layers.py and plugin.py), or directly via
add_land_unit_layer_nonnato(iface).

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
    AIR_DEFENSE_ARTILLERY_ENTITY,
    ENEMY_DESIGNATION_UNKNOWN_ENTITY,
    ENEMY_ECHELON_UNKNOWN_ENTITY,
    ENEMY_INFO_UNKNOWN_ENTITY,
    ENEMY_TYPE_UNKNOWN_ENTITY,
    ADMIN_LOGISTICS_ENTITY,
    MOTORISED_INFANTRY_ENTITY,
    MOUNTAIN_INFANTRY_ENTITY,
    INFORMATION_WARFARE_ENTITY,
    INTELLIGENCE_ENTITY,
    ORDNANCE_ENTITY,
    POSTAL_UNIT_ENTITY,
    REMOUNT_VETERINARY_ENTITY,
    SUPPLIES_TRANSPORT_ENTITY,
    PARACHUTE_FIELD_ARTILLERY_ENTITY,
    RECCE_SUPPORT_WHEELED_ENTITY,
    SELF_PROPELLED_ARTILLERY_ENTITY,
    STATIC_FORMATION_HQ_ENTITY,
    stabilised_nonnato_size_expression,
)


LAYER_NAME = "Land Unit (Non-NATO)"

DEFAULT_ENTITY = "infantry"

MARKER_SIZE_MM = 8.0

# Display labels for the 20 real APP-6E entities the reviewed check
# sheet confirmed, plus nineteen entries with no matching real
# ground_unit key of their own - see this module's own docstring for
# the list. Every other entry's KEY is a real ground_unit key
# sidc_2525e.py already defines (unchanged, so render_nonnato_unit_
# svg()'s own build_sidc() call resolves them directly) - only the
# LABEL a user reads in the dropdown is renamed, same convention as
# every other vocabulary dict in this project. See the rules record's
# "Required entities"/"Renamed"/"Icon modifications" notes for where
# each one of these came from, and nonnato_symbol_engine.py's own
# comments for the Enemy family (no SIDC at all), Air Defence
# Artillery (Air Defence's real SIDC, plus Artillery's own dot fixed up
# on top - requested live 2026-09-02), and Air Force (Army Aviation's
# real SIDC, with its own hollow figure-of-8 opened on the right -
# requested live 2026-09-03).
ENTITY_LABELS = {
    "air_defense": "Air Defence",
    AIR_DEFENSE_ARTILLERY_ENTITY: "Air Defence Artillery",
    "ammunition": "Ammunition",
    "amphibious": "Amphibious",
    "armor_mechanized": "Armour",
    "armored_mechanized_tracked": "Mechanised Infantry",
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
    "parachute_rigger": "Parachute",
    "reconnaissance_cavalry_scout": "Light Armour/Recce & Support (Tracked)",
    "signal": "Signal",
    "special_operations_forces": "Special Operations Forces",
    ENEMY_INFO_UNKNOWN_ENTITY: "Enemy (Info Unknown)",
    ENEMY_ECHELON_UNKNOWN_ENTITY: "Enemy (Echelon Unknown)",
    ENEMY_DESIGNATION_UNKNOWN_ENTITY: "Enemy (Designation Unknown)",
    ENEMY_TYPE_UNKNOWN_ENTITY: "Enemy (Type Unknown)",

    # Synthetic, 2026-09-06: Infantry's own glyph with the Vehicle
    # family's own two wheels under it - see nonnato_symbol_engine.
    # inject_motorised_wheels().
    MOTORISED_INFANTRY_ENTITY: "Motorised Infantry",

    # Synthetic, 2026-09-06: Infantry's own glyph with a "^" in
    # its lower half - see nonnato_symbol_engine._mountain_chevron().
    MOUNTAIN_INFANTRY_ENTITY: "Mountain Infantry",

    # Synthetic, 2026-09-06: Mechanised Infantry's own glyph with
    # Motorised Infantry's own wheels under it - the wheeled
    # counterpart to "Light Armour/Recce & Support (Tracked)".
    RECCE_SUPPORT_WHEELED_ENTITY: "Recce & Support (Wheeled)",

    # Synthetic, 2026-09-06: Artillery's own glyph with three
    # wheels, and with the Parachute unit's own canopy - see
    # nonnato_symbol_engine._self_propelled_wheels() and
    # _parachute_over_artillery().
    SELF_PROPELLED_ARTILLERY_ENTITY: "Self Propelled Artillery",
    PARACHUTE_FIELD_ARTILLERY_ENTITY: "Parachute Field Artillery",

    # Synthetic, 2026-09-06: all six built on Military Police's own
    # framed glyph - the first three swap its "MP" for other
    # letters, the last three swap it for a shape. Built on a real
    # render, not standalone, so echelon/status/headquarters keep
    # working - see nonnato_symbol_engine's own comment.
    INFORMATION_WARFARE_ENTITY: "Information Warfare",
    POSTAL_UNIT_ENTITY: "Postal Unit",
    INTELLIGENCE_ENTITY: "Intelligence",
    SUPPLIES_TRANSPORT_ENTITY: "Supplies and Transport",
    ORDNANCE_ENTITY: "Ordnance",
    REMOUNT_VETERINARY_ENTITY: "Remount and Veterinary Corps",

    # Synthetic, 2026-09-06: a bare circle at the frame's own height,
    # no APP-6E entity and no glyph inside - see
    # nonnato_symbol_engine.admin_logistics_svg().
    ADMIN_LOGISTICS_ENTITY: "Administration or Logistics Unit",

    # Synthetic, 2026-09-06: a pennant-shaped frame (the rectangle's own
    # right side replaced by a "<") carrying the Headquarters mast -
    # see nonnato_symbol_engine.static_formation_hq_svg().
    STATIC_FORMATION_HQ_ENTITY: "Static Formation Headquarters",
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


def configure_unit_attribute_form(layer, entity_labels, default_entity):

    """
    The Land Unit dialog - affiliation, entity, echelon, status,
    Combined Arms, Headquarters, plus rotation and scale.

    Parameterised on the entity list 2026-09-06 so the "Aviation
    (Non-NATO)" layer can present exactly the same dialog over its own
    entities: "same rules as land unit i.e. same dialog box
    replicated". Nothing but the entity dropdown differs between the
    two.
    """

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
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(entity_labels)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("entity"), QgsDefaultValue(f"'{default_entity}'")
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

    # milsymbol's own flag-mast amplifier (SIDC Field S), added
    # 2026-09-06 - "there is a choice for Headquarters in the NATO
    # symbology wherein a flag mast is added to the glyph - implement
    # the same in non-nato also". Same widget and default the NATO
    # layers use for it (_point_symbol_layer.include_headquarters).
    layer.setEditorWidgetSetup(
        fields.indexOf("headquarters"),
        QgsEditorWidgetSetup("CheckBox", {})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("headquarters"), QgsDefaultValue("false")
    )

    configure_rotation_and_scale_fields(layer)


def build_unit_renderer():

    # Field values are passed straight through - affiliation/entity/
    # echelon/status all use the same stored keys render_nonnato_unit_
    # svg() itself expects, per the label dicts above. Two independent
    # designation fields, left and right - see nonnato_symbol_engine.
    # inject_side_designations()'s own docstring for the 2026-09-02
    # request this replaces the older single "unique_designation" field
    # for ("i want two unique designators - unique designator (left)
    # and unique designator (right)... the present unique designator
    # can be removed or ignored").
    designation_left_expression = (
        'upper(coalesce("unique_designation_left", \'\'))'
    )
    designation_right_expression = (
        'upper(coalesce("unique_designation_right", \'\'))'
    )

    # Every field reference feeding the render functions is coalesced to
    # its own default, for the same reason the booleans below are: QGIS
    # returns NULL from an expression function the moment ANY argument
    # is NULL. echelon/status were still bare references until
    # 2026-09-06, when building the Aviation layer's own tests surfaced
    # it - a feature with no echelon set rendered nothing at all.
    echelon_expression = 'coalesce("echelon", \'unspecified\')'
    status_expression = 'coalesce("status", \'present\')'

    # coalesce() around BOTH booleans, not just a tidy-up: QGIS returns
    # NULL from an expression function the moment ANY argument is NULL,
    # so a feature whose checkbox has never been set renders NOTHING at
    # all. The field defaults only apply to features created through the
    # attribute form - a pasted feature, a provider-level insert or a
    # project predating the field all arrive NULL. Confirmed by direct
    # evaluation 2026-09-06; "combined_arms" had carried this latent
    # blank-icon bug since it was added, and adding "headquarters"
    # beside it is what surfaced it.
    combined_arms_expression = 'coalesce("combined_arms", false)'
    headquarters_expression = 'coalesce("headquarters", false)'

    expression = (
        'mct_nonnato_unit_svg('
        '"affiliation","entity",'
        f'{echelon_expression},{status_expression},'
        f'{designation_left_expression},{designation_right_expression},'
        f'{combined_arms_expression},{headquarters_expression}'
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
    # 2026-09-02 fix this is. The "plain" call below passes '' for both
    # designation sides (not "combined_arms"'s own field - Combined Arms
    # widens the icon too, but by drawing a rectangle around it, not by
    # the side-designation text-box widening, so it is correctly left as
    # a live field reference on both sides and cancels out of the
    # ratio).
    amplified_width_expression = (
        'mct_nonnato_unit_svg_width('
        '"affiliation","entity",'
        f'{echelon_expression},{status_expression},'
        f'{designation_left_expression},{designation_right_expression},'
        f'{combined_arms_expression},{headquarters_expression}'
        ')'
    )

    plain_width_expression = (
        'mct_nonnato_unit_svg_width('
        '"affiliation","entity",'
        f'{echelon_expression},{status_expression},'
        f'\'\',\'\',{combined_arms_expression},{headquarters_expression}'
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


def build_unit_style_layer(layer_name, entity_labels, default_entity):

    """
    A fresh, empty layer carrying the full Land Unit dialog and
    renderer - shared with "Aviation (Non-NATO)" since 2026-09-06, which
    differs only in its name and its own entity list.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        layer_name,
        "memory"
    )

    attributes = [
        QgsField("affiliation", QMetaType.Type.QString),
        QgsField("entity", QMetaType.Type.QString),
        QgsField("echelon", QMetaType.Type.QString),
        QgsField("status", QMetaType.Type.QString),
        QgsField("combined_arms", QMetaType.Type.Bool),
        QgsField("headquarters", QMetaType.Type.Bool),
        QgsField("unique_designation_left", QMetaType.Type.QString),
        QgsField("unique_designation_right", QMetaType.Type.QString),
        QgsField("rotation", QMetaType.Type.Double),
        QgsField("scale", QMetaType.Type.Double),
    ]

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    configure_unit_attribute_form(layer, entity_labels, default_entity)

    layer.setRenderer(build_unit_renderer())

    return layer


def build_land_unit_layer_nonnato():

    """A fresh, empty "Land Unit (Non-NATO)" layer - never added to the project itself, see add_land_unit_layer_nonnato()."""

    return build_unit_style_layer(LAYER_NAME, ENTITY_LABELS, DEFAULT_ENTITY)


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
