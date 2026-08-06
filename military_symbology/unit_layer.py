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

DEFAULT_SYMBOL_SET = "ground_unit"

DEFAULT_MARKER_SIZE_MM = 8.0

_SIDC_EXPRESSION = (
    'mct_sidc_svg(mct_build_sidc('
    '"affiliation","entity","echelon","status","headquarters"'
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

_ENTITY_LABELS = {
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
}

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
    dropdowns, not a cascading Value Relation chain) - reasonable while
    there's only one symbol set (DEFAULT_SYMBOL_SET) with a handful of
    entities each; a cascading affiliation -> symbol set -> entity setup
    would need backing lookup layers for QgsValueRelationFieldFormatter
    and would add real complexity for no benefit until a second symbol
    set actually exists to filter between - revisit if/when the
    vocabulary grows enough for that to matter (see sidc.py's own note on
    growing ENTITIES being additive).
    """

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
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
        entity_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_ENTITY_LABELS)}
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
    # mct_build_sidc() would reject.
    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
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
    current project's own CRS - fields (affiliation/entity/echelon/
    status/headquarters/unique_designation), a friendly attribute form,
    and a renderer that draws the correct MIL-STD-2525/APP-6 symbol from
    those fields automatically. Never added to the project - see this
    module's own docstring for why callers must not treat this like
    every other generate_*() in this plugin.
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
            QgsField("entity", QMetaType.Type.QString),
            QgsField("echelon", QMetaType.Type.QString),
            QgsField("status", QMetaType.Type.QString),
            QgsField("headquarters", QMetaType.Type.Bool),
            QgsField("unique_designation", QMetaType.Type.QString),
        ]
    )

    layer.updateFields()

    _configure_attribute_form(layer)

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
