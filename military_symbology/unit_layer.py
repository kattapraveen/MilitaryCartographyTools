# -*- coding: utf-8 -*-

"""
Builds a ready-to-use "Tactical Graphics - Units" point layer: the right
fields, a friendly attribute form, and a renderer that computes each
feature's own MIL-STD-2525/APP-6 symbol live from its own attributes -
via mct_build_sidc()/mct_sidc_svg() (expressions/
military_symbology_functions.py) - so placing a unit is just filling in a
plain attribute form, not picking a symbol from a separate picker.

Deliberately NOT a generate_*()/replace_named_layer() feature like every
other layer this plugin builds - those are safe to recreate because their
content is algorithmically derived from a DEM/AO/grid and can be thrown
away and rebuilt at will. This layer's content is hand-placed operational
data (real unit positions a user digitizes with QGIS's own native "Add
Point Feature" tool, deliberately - see docs/roadmap.md's Phase 10 entry
for why no custom placement tool exists) - regenerating "in place" would
mean silently destroying real, irreplaceable data the moment a second
click happened, so create_unit_layer() only ever builds a fresh layer;
callers are responsible for not calling it if a layer with the same name
already exists (see unit_layer_dialog.py's own guard).

Military Cartography Tools
"""

from qgis.core import (
    QgsDefaultValue,
    QgsEditorWidgetSetup,
    QgsFeature,
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

from ..core._layer_utils import add_layer_at_default_position


OUTPUT_LAYER_NAME = "Tactical Graphics - Units"

ENTITY_LOOKUP_LAYER_NAME = "Tactical Graphics - Units (Entity Reference)"

DEFAULT_SYMBOL_SET = "ground_unit"

DEFAULT_MARKER_SIZE_MM = 8.0

_SIDC_EXPRESSION = (
    'mct_sidc_svg(mct_build_sidc('
    '"affiliation","entity","symbol_set","echelon","status","headquarters"'
    '))'
)

# Display labels for this plugin's own UI - kept separate from sidc.py's
# own vocabulary dicts, which are the data model (real SIDC component
# codes), not presentation text.
_AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

# Domain display names, used both for the "Symbol Set" field's own
# ValueMap and to prefix each entity's label in the combined "Entity"
# dropdown below (e.g. "Air - Fighter") - added 2026-08-07 alongside the
# air/sea_surface/subsurface symbol sets, so entities from different
# domains stay visually distinguishable in one flat dropdown even though
# their underlying stored value (the entity key) is domain-agnostic.
_SYMBOL_SET_LABELS = {
    "ground_unit": "Ground Unit",
    "air": "Air",
    "sea_surface": "Sea Surface",
    "subsurface": "Subsurface",
}

# Entity labels, keyed by symbol set - mirrors sidc.py's own ENTITIES
# structure exactly (see that module's docstring for where each symbol
# set's codes come from). Entity key names are unique across all four
# symbol sets, with two deliberate exceptions: "military" is shared by
# air/sea_surface/subsurface (all three map to the identical generic
# code "110000", so no ambiguity - selecting any of the three
# domain-prefixed labels stores the same value and is correct paired
# with any of those three symbol_set values), and two real collisions
# were avoided by renaming in sidc.py itself - ground_unit's own
# "reconnaissance"/"electronic_warfare" vs. unrelated air entities, now
# "air_reconnaissance"/"airborne_electronic_warfare". A plain entity key
# is enough to look up the right code once paired with its own
# symbol_set value; the domain prefix in _combined_entity_labels() below
# exists purely for the user's own clarity when scanning one long
# dropdown, not to disambiguate the stored value itself.
_ENTITY_LABELS_BY_SYMBOL_SET = {
    "ground_unit": {
        # Command & signal
        "command_and_control": "Command and Control",
        "signal": "Signal",
        "liaison": "Liaison",
        # Maneuver
        "infantry": "Infantry",
        "motorized_infantry": "Motorized Infantry",
        "mechanized_infantry": "Mechanized Infantry",
        "armor": "Armor",
        "reconnaissance": "Reconnaissance",
        "antitank": "Antitank/Antiarmor",
        "combined_arms": "Combined Arms",
        "aviation_rotary_wing": "Aviation (Rotary Wing)",
        "aviation_fixed_wing": "Aviation (Fixed Wing)",
        "air_assault": "Air Assault",
        "amphibious": "Amphibious",
        "special_forces": "Special Forces",
        "ranger": "Ranger",
        "sniper": "Sniper",
        "surveillance": "Surveillance",
        "unmanned_systems": "Unmanned Systems",
        # Fires
        "field_artillery": "Field Artillery",
        "field_artillery_self_propelled": "Field Artillery, Self-Propelled",
        "field_artillery_observer": "Field Artillery Observer",
        "mortar": "Mortar",
        "missile": "Missile",
        "joint_fire_support": "Joint Fire Support",
        # Air defense
        "air_defense": "Air Defense",
        "air_defense_gun": "Air Defense Gun",
        "air_defense_missile": "Air Defense Missile",
        "air_and_missile_defense": "Air and Missile Defense",
        # Combat support
        "engineer": "Engineer",
        "engineer_mechanized": "Engineer, Mechanized",
        "cbrn": "CBRN (Chemical, Biological, Radiological, Nuclear)",
        "explosive_ordnance_disposal": "Explosive Ordnance Disposal (EOD)",
        "military_police": "Military Police",
        "mine_clearing": "Mine Clearing",
        "search_and_rescue": "Search and Rescue",
        "security": "Security",
        # Intelligence & electronic warfare
        "military_intelligence": "Military Intelligence",
        "electronic_warfare": "Electronic Warfare",
        "counter_intelligence": "Counter-Intelligence",
        "sensor": "Sensor",
        # Combat service support
        "sustainment": "Sustainment",
        "maintenance": "Maintenance",
        "medical": "Medical",
        "supply": "Supply",
        "transportation": "Transportation",
        "quartermaster": "Quartermaster",
        "ordnance": "Ordnance",
        "ammunition": "Ammunition",
        "petroleum_oil_lubricants": "Petroleum, Oil, and Lubricants (POL)",
    },
    "air": {
        "military": "Military (Generic)",
        "fixed_wing": "Fixed-Wing",
        "attack": "Attack/Strike",
        "bomber": "Bomber",
        "fighter": "Fighter",
        "fighter_bomber": "Fighter/Bomber",
        "cargo": "Cargo/Transport",
        "airborne_electronic_warfare": "Electronic Warfare (Jammer/ECM)",
        "tanker": "Tanker",
        "patrol": "Patrol",
        "air_reconnaissance": "Reconnaissance",
        "trainer": "Trainer",
        "utility": "Utility",
        "airborne_early_warning": "Airborne Early Warning",
        "antisubmarine_warfare": "Antisubmarine Warfare",
        "medical_evacuation": "Medical Evacuation",
        "combat_search_and_rescue": "Combat Search and Rescue",
        "special_operations_forces": "Special Operations Forces",
        "rotary_wing": "Rotary Wing (Helicopter)",
        "unmanned_aerial_vehicle": "Unmanned Aerial Vehicle (UAV)",
    },
    "sea_surface": {
        "military": "Military (Generic)",
        "carrier": "Carrier",
        "cruiser": "Cruiser",
        "destroyer": "Destroyer",
        "frigate": "Frigate",
        "corvette": "Corvette",
        "littoral_combat_ship": "Littoral Combat Ship",
        "amphibious_assault_ship": "Amphibious Assault Ship",
        "landing_ship": "Landing Ship",
        "landing_craft": "Landing Craft",
        "minelayer": "Minelayer",
        "minesweeper": "Minesweeper",
        "mine_countermeasures_ship": "Mine Countermeasures Ship",
        "patrol_craft": "Patrol Craft",
        "unmanned_surface_vehicle": "Unmanned Surface Vehicle (USV)",
        "auxiliary_ship": "Auxiliary Ship",
        "hospital_ship": "Hospital Ship",
        "cargo_ship": "Cargo Ship",
        "oiler": "Oiler (Replenishment)",
        "submarine_tender": "Submarine Tender",
        "tug": "Tug (Ocean Going)",
    },
    "subsurface": {
        "military": "Military (Generic)",
        "submarine": "Submarine",
        "submarine_surfaced": "Submarine, Surfaced",
        "submarine_snorkeling": "Submarine, Snorkeling",
        "other_submersible": "Other Submersible",
        "autonomous_underwater_vehicle": "Autonomous Underwater Vehicle (AUV/UUV)",
        "diver_military": "Diver, Military",
        "torpedo": "Torpedo",
    },
}


def _combined_entity_labels():

    """
    Every entity's own {value: "Domain - Label"} string, flattened
    across all four symbol sets - the source data for
    _build_entity_lookup_layer()'s rows below. Domain-prefixed so the
    lookup layer's own "label" column reads clearly on its own (e.g. if
    the cascading ValueRelation this backs ever needs falling back to
    an unfiltered flat list - see _configure_entity_field()'s own
    docstring).
    """

    labels = {}

    for symbol_set, entities in _ENTITY_LABELS_BY_SYMBOL_SET.items():

        domain = _SYMBOL_SET_LABELS[symbol_set]

        for entity, label in entities.items():

            labels[entity] = f"{domain} - {label}"

    return labels


def _build_entity_lookup_layer(name=ENTITY_LOOKUP_LAYER_NAME):

    """
    A small reference layer backing the "Entity" field's cascading
    ValueRelation dropdown (_configure_entity_field(), below) - one row
    per (symbol_set, entity) pair, sourced from _combined_entity_labels().
    Not user data - safe to always (re)build, unlike every other layer
    this module or control_measures.py creates.
    """

    layer = QgsVectorLayer(
        "NoGeometry?field=symbol_set:string&field=entity:string&field=label:string",
        name,
        "memory"
    )

    labels = _combined_entity_labels()

    features = []

    for symbol_set, entities in _ENTITY_LABELS_BY_SYMBOL_SET.items():

        for entity in entities:

            feature = QgsFeature(layer.fields())

            feature.setAttribute("symbol_set", symbol_set)
            feature.setAttribute("entity", entity)
            feature.setAttribute("label", labels[entity])

            features.append(feature)

    layer.dataProvider().addFeatures(features)

    return layer


def _configure_entity_field(layer):

    """
    Wires the "Entity" field to a cascading ValueRelation dropdown,
    filtered to only the entities belonging to whichever "Symbol Set"
    value is currently selected on the same feature - via
    QgsValueRelationFieldFormatter's FilterExpression and QGIS's own
    current_value('symbol_set') expression function, the standard
    mechanism for a dropdown whose options depend on a sibling field.

    Flagged here plainly, not hidden: during development,
    current_value() inside a ValueRelation FilterExpression caused a
    native crash every time it was exercised directly through
    QgsValueRelationFieldFormatter.createCache() - reproduced repeatedly,
    including with a real layer-backed feature, not just a synthetic
    one. This is nonetheless the standard, documented way to build a
    cascading dropdown in QGIS, and is expected to work correctly
    through the real interactive attribute form (which sets up
    expression-context scope this direct low-level API call may not) -
    but that could not be verified without a live QGIS session, since
    this plugin's own test harness can only drive the API layer, not a
    real form UI. If this proves unstable in practice, the fallback is
    a field constraint expression instead (validates the "entity"/
    "symbol_set" combination on save rather than filtering the dropdown
    live - an ordinary per-feature expression with no current_value()
    dependency, so it doesn't share this risk).
    """

    lookup_layer = _build_entity_lookup_layer()

    QgsProject.instance().addMapLayer(
        lookup_layer,
        False
    )

    entity_idx = layer.fields().indexOf("entity")

    layer.setEditorWidgetSetup(
        entity_idx,
        QgsEditorWidgetSetup(
            "ValueRelation",
            {
                "Layer": lookup_layer.id(),
                "Key": "entity",
                "Value": "label",
                "FilterExpression": "\"symbol_set\" = current_value('symbol_set')",
                "AllowMulti": False,
                "AllowNull": False,
                "OrderByValue": False,
                "NofColumns": 1,
                "UseCompleter": False,
            }
        )
    )


_ECHELON_LABELS = {
    "unspecified": "Unspecified",
    "team_crew": "Team/Crew",
    "squad": "Squad",
    "section": "Section",
    "platoon": "Platoon",
    "company": "Company",
    "battalion": "Battalion",
    "regiment": "Regiment",
    "brigade": "Brigade",
    "division": "Division",
    "corps": "Corps",
    "army": "Army",
}

_STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned",
}


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _configure_attribute_form(layer):

    """
    A ValueMap dropdown per vocabulary field (plain, independent
    dropdowns) for everything except "Entity", which is configured
    separately by _configure_entity_field() as a cascading
    ValueRelation filtered by this layer's own "Symbol Set" field - see
    that function's own docstring for the mechanism and its caveats.
    """

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    symbol_set_idx = fields.indexOf("symbol_set")
    entity_idx = fields.indexOf("entity")
    echelon_idx = fields.indexOf("echelon")
    status_idx = fields.indexOf("status")
    headquarters_idx = fields.indexOf("headquarters")

    layer.setEditorWidgetSetup(
        affiliation_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_AFFILIATION_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        symbol_set_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_SYMBOL_SET_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        echelon_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_ECHELON_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_STATUS_LABELS)}
        )
    )

    layer.setEditorWidgetSetup(
        headquarters_idx,
        QgsEditorWidgetSetup("CheckBox", {})
    )

    # Sensible defaults so a feature added and saved without touching
    # every field (or a feature added programmatically, e.g. by a test)
    # still resolves to a valid SIDC rather than an empty-string one
    # mct_build_sidc() would reject. symbol_set/entity default to a
    # matching pair (ground_unit/infantry), not independently arbitrary
    # values, since an unpaired default would render as a visible error
    # string instead of a symbol.
    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(symbol_set_idx, QgsDefaultValue(f"'{DEFAULT_SYMBOL_SET}'"))
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue("'infantry'"))
    layer.setDefaultValueDefinition(echelon_idx, QgsDefaultValue("'unspecified'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))
    layer.setDefaultValueDefinition(headquarters_idx, QgsDefaultValue("false"))


def _build_renderer():

    """
    One symbol, one QgsSvgMarkerSymbolLayer, whose own path is
    data-defined per feature via _SIDC_EXPRESSION - confirmed live that
    QGIS re-evaluates this per feature at render time, so every point's
    own attributes drive its own symbol automatically with no per-point
    Python code needed.
    """

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(DEFAULT_MARKER_SIZE_MM)

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_SIDC_EXPRESSION)
    )

    symbol.changeSymbolLayer(0, svg_layer)

    return QgsSingleSymbolRenderer(symbol)


def create_unit_layer(name=OUTPUT_LAYER_NAME):

    """
    A fresh, empty "Tactical Graphics - Units" point layer, in the
    current project's own CRS - fields (affiliation/symbol_set/entity/
    echelon/status/headquarters/unique_designation), a friendly
    attribute form, and a renderer that draws the correct MIL-STD-2525/
    APP-6 symbol from those fields automatically. The Units layer
    itself is never added to the project - see this module's own
    docstring for why callers must not treat this like every other
    generate_*() in this plugin. One narrow exception: this also
    registers a small ENTITY_LOOKUP_LAYER_NAME reference layer into the
    project (hidden from the Layers panel) backing the "Entity" field's
    cascading dropdown - see _configure_entity_field()'s own docstring.
    That lookup layer holds no user data, so registering it here doesn't
    carry the same "never touch the project" risk the Units layer itself
    does.
    """

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        name,
        "memory"
    )

    layer.dataProvider().addAttributes(
        [
            QgsField("affiliation", QMetaType.Type.QString),
            QgsField("symbol_set", QMetaType.Type.QString),
            QgsField("entity", QMetaType.Type.QString),
            QgsField("echelon", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("headquarters", QMetaType.Type.Bool),
            QgsField("unique_designation", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    _configure_attribute_form(layer)

    _configure_entity_field(layer)

    layer.setRenderer(
        _build_renderer()
    )

    return layer


def default_insert_position(project, layer):

    """
    Top of the layer tree - matches Line of Sight/Viewshed's own
    convention for an analysis/operational overlay meant to sit above
    whatever base terrain rendering is underneath.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


def add_unit_layer(iface):

    """
    The toolbar action's own callback - no dialog, since there's nothing
    to configure at creation time (fields/styling are fixed; per-feature
    values are filled in via the attribute form after placing each
    point, which isn't a creation-time choice either). If a layer named
    OUTPUT_LAYER_NAME already exists, does nothing but warn - see this
    module's own docstring for why silently replacing it, the way every
    other generate_*() in this plugin does, would be a real data-loss
    bug here. Returns the new layer, or None if one already existed.
    """

    project = QgsProject.instance()

    if project.mapLayersByName(OUTPUT_LAYER_NAME):

        iface.messageBar().pushWarning(
            "Military Cartography Tools",
            f'A "{OUTPUT_LAYER_NAME}" layer already exists - use the '
            "Layers panel to work with it, or rename it first if you "
            "want a second one."
        )

        return None

    layer = create_unit_layer()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
