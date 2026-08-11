# -*- coding: utf-8 -*-

"""
Builds a ready-to-use "Control Measure Points" point
layer - MIL-STD-2525D Appendix H's own point-type control measures
(command/control points, observation posts, target points, sustainment/
supply points, and similar - sidc.py's ENTITIES["control_measure"], symbol
set "25"), rendered through the same milsymbol.js pipeline as
unit_layer.py (mct_build_sidc()/mct_sidc_svg()) - NOT control_measures.py's
hand-built QGIS line/fill symbology, which covers Appendix H's LINE/AREA
control measures instead (a different rendering mechanism entirely, since
milsymbol.js has no line/polygon support - see that module's own
docstring). Appendix H's point-type control measures are ordinary point
icons as far as milsymbol.js is concerned, so they get the exact same
data-defined-SVG-marker treatment as any unit symbol.

Confirmed live (2026-08-07) that milsymbol.js already renders this symbol
set's affiliation coloring correctly per the standard's own H.5.3 rule
(friendly/neutral/unknown -> black, hostile -> red) with no extra code on
our side - rendering a real checkpoint/decision-point/contact-point SIDC
through the actual QJSEngine pipeline for all four affiliations showed
`stroke="black"` for unknown/friend/neutral and `stroke="rgb(255, 0, 0)"`
for hostile, every time. Unlike control_measures.py's hand-built lines/
areas, which had to implement H.5.3 themselves via a data-defined colour
expression, this symbol set's colouring comes for free from milsymbol.js's
own rendering logic for symbolSet "25" - no _apply_affiliation_color()
equivalent needed here.

Deliberately simpler than unit_layer.py's own attribute form:

- No "Symbol Set" field - this layer only ever draws from the
  "control_measure" symbol set, so there's nothing to cascade against,
  which means "Entity" is a plain ValueMap dropdown here, not a cascading
  ValueRelation - sidesteps that mechanism's own crash-risk caveat (see
  unit_layer.py's _configure_entity_field() docstring) entirely, since it
  isn't needed.
- No "Echelon" or "Headquarters" fields - MIL-STD-2525D's own H.5.1.1
  list of control-measure amplifiers doesn't include a headquarters
  amplifier, and while H.5.1.1.6 does describe an echelon indicator for
  control measures generally, it's primarily used on boundaries (see
  control_measures.py) rather than the point types curated here, so it's
  left out of this first pass rather than exposed as an always-
  "Unspecified" field with no real use. "Status" (H.5.1.1.3) IS kept,
  since present/planned genuinely applies to a point control measure
  (e.g. a proposed vs. an active checkpoint).

Same "never touches the project" / no generate_*() contract as
unit_layer.py, for the same reason (hand-placed operational data) - see
that module's own docstring for the full rationale.

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


OUTPUT_LAYER_NAME = "Control Measure Points"

SYMBOL_SET = "control_measure"

DEFAULT_MARKER_SIZE_MM = 8.0

# Literal 'control_measure'/'unspecified'/false for the symbol_set/
# echelon/headquarters positions mct_build_sidc() still requires - this
# layer has no fields for them (see module docstring), so the expression
# supplies fixed values directly rather than reading absent fields. The
# "unique_designation" field IS passed through - as mct_sidc_svg()'s own
# second, optional argument (its own `uniqueDesignation` slot), upper-
# cased per H.5.4 Labeling - see that function's own docstring for the
# 2026-08-10 fixes this was missing entirely before (the field existed
# on this layer's own schema, but nothing ever read it; then, once
# wired up, wasn't upper-cased either), and for why coalesce(...,'')
# matters (a bare NULL field reference silently breaks the whole
# rendered icon, not just the missing text).
#
# **Known limitation, not yet resolved**: c2_measures.py's own Points
# layer found (2026-08-10) that several icons actually need the text in
# milsymbol.js's OTHER slot, `uniqueDesignation1`, to land where the
# standard's own template shows it - see that module's own
# _POINT_SIDC_EXPRESSION comment for the full finding. This layer's own
# ~88 entities haven't been individually checked against that same
# per-icon distinction yet (Table H-VI's 22 were, since that's what
# prompted the finding) - every entity here still only ever uses
# `uniqueDesignation`, which will be in the wrong position for whichever
# of these entities turns out to work the same way Amnesty Point/
# Checkpoint/Distress Call did. Revisit if reported.
_SIDC_EXPRESSION = (
    "mct_sidc_svg(mct_build_sidc("
    "\"affiliation\",\"entity\",'control_measure','unspecified',"
    "\"status\",false"
    "),upper(coalesce(\"unique_designation\",'')))"
)

# Display labels for this plugin's own UI - kept separate from sidc.py's
# own vocabulary dicts, which are the data model (real SIDC component
# codes), not presentation text. Mirrors unit_layer.py's own separation.
_AFFILIATION_LABELS = {
    "friend": "Friend",
    "hostile": "Hostile",
    "neutral": "Neutral",
    "unknown": "Unknown",
}

_STATUS_LABELS = {
    "present": "Present",
    "planned": "Planned",
}

# Mirrors sidc.py's ENTITIES["control_measure"] exactly - see that
# dict's own comment for what was curated out and why.
_ENTITY_LABELS = {
    # Table H-VI (Command and control points), Table H-IX (Observation
    # post), Table H-XI's own single Point of Departure entry, and Table
    # H-XIII's own 26-entry airspace point family have all moved to
    # their own dedicated layers - c2_measures.py's own
    # POINT_ENTITY_LABELS, defensive_control_measures.py's own
    # POINT_ENTITY_LABELS, offensive_control_measures.py's own
    # POINT_ENTITY_LABELS, and airspace_control_measures.py's own
    # POINT_ENTITY_LABELS respectively - at the project maintainer's own
    # request (2026-08-10, and again 2026-08-12 for the airspace family:
    # "all symbols related to points, I think they are in control
    # measure points, need to be relocated"): a flat ~90-entry dropdown
    # made these groups hard to find, and the same "own layer(s)"
    # convention c2_measures.py's own Lines/Areas already follow extends
    # naturally to their own point-type entities too. Not duplicated
    # here - the underlying sidc.py entities are untouched, so any
    # already-digitized feature keeps rendering fine regardless of which
    # layer's dropdown offers them.
    # Maritime hazards / reference points
    "distressed_vessel": "Distressed Vessel",
    "downed_aircraft": "Downed/Ditched Aircraft",
    "iceberg": "Iceberg",
    "oil_rig": "Oil Rig",
    "sea_mine_like_contact": "Sea Mine-Like Contact",
    # Fires
    "point_target": "Point/Single Target",
    "nuclear_target": "Nuclear Target",
    "target_recorded": "Target - Recorded",
    "fire_support_station": "Fire Support Station",
    "firing_point": "Firing Point",
    "hide_point": "Hide Point",
    "launch_point": "Launch Point",
    "reload_point": "Reload Point",
    "survey_control_point": "Survey Control Point",
    # Protection (obstacles, mines, shelters, CBRN events)
    "abatis": "Abatis",
    "antipersonnel_mine": "Antipersonnel Mine",
    "antitank_mine": "Antitank Mine",
    "unspecified_mine": "Unspecified Mine",
    "booby_trap": "Booby Trap",
    "engineer_regulating_point": "Engineer Regulating Point",
    "shelter": "Shelter",
    "shelter_above_ground": "Shelter, Above Ground",
    "shelter_below_ground": "Shelter, Below Ground",
    "fort": "Fort",
    "chemical_event": "Chemical Event",
    "biological_event": "Biological Event",
    "nuclear_event": "Nuclear Event",
    "radiological_event": "Radiological Event",
    # Sustainment, supply, casualty & personnel handling
    "ambulance_exchange_point": "Ambulance Exchange Point",
    "ammunition_supply_point": "Ammunition Supply Point",
    "ammunition_transfer_point": "Ammunition Transfer and Holding Point",
    "cannibalization_point": "Cannibalization Point",
    "casualty_collection_point": "Casualty Collection Point",
    "civilian_collection_point": "Civilian Collection Point",
    "detainee_collection_point": "Detainee Collection Point",
    "enemy_prisoner_of_war_collection_point": "Enemy Prisoner of War Collection Point",
    "logistics_release_point": "Logistics Release Point",
    "maintenance_collection_point": "Maintenance Collection Point (MCP)",
    "medevac_pickup_point": "Medical Evacuation (MEDEVAC) Pick-Up Point",
    "rearm_refuel_resupply_point": "Rearm, Refuel and Resupply Point (R3P)",
    "refuel_on_the_move_point": "Refuel on the Move (ROM) Point",
    "traffic_control_post": "Traffic Control Post (TCP)",
    "trailer_transfer_point": "Trailer Transfer Point (TTP)",
    "unit_maintenance_collection_point": "Unit Maintenance Collection Point (UMCP)",
    "general_supply_point": "General Supply Point",
    "medical_supply_point": "Medical Supply Point",
    # Mission tasks (point form)
    "destroy_point": "Destroy (Point)",
    "interdict_point": "Interdict (Point)",
    "neutralize_point": "Neutralize (Point)",
    # Maritime control points (Table H-XIV, Mini-Phase H8/H9) - see
    # maritime_control_measures.py's own docstring for what's built
    # there instead (the Bearing Line family) and the much larger
    # AEGIS-specific/ASW-sonar/sonobuoy family deliberately left out.
    "plan_ship": "Plan Ship",
    "aim_point": "Aim Point",
    "defended_asset": "Defended Asset",
    "drop_point": "Drop Point",
    "entry_point": "Entry Point",
    "air_detonation": "Air Detonation",
    "ground_zero": "Ground Zero",
    "impact_point": "Impact Point",
    "predicted_impact_point": "Predicted Impact Point",
    "missile_detection_point": "Missile Detection Point",
    "brief_contact": "Brief Contact",
    "datum_lost_contact": "Datum Lost Contact",
    "navigational_reference_point": "Navigational Reference Point",
}


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _configure_attribute_form(layer):

    """
    A ValueMap dropdown per vocabulary field - no cascading widget
    needed here, unlike unit_layer.py's "Entity" field, since this
    layer only ever draws from the one "control_measure" symbol set
    (see module docstring).
    """

    fields = layer.fields()

    affiliation_idx = fields.indexOf("affiliation")
    entity_idx = fields.indexOf("entity")
    status_idx = fields.indexOf("status")

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
        status_idx,
        QgsEditorWidgetSetup(
            "ValueMap",
            {"map": _value_map(_STATUS_LABELS)}
        )
    )

    # Sensible defaults so a feature added and saved without touching
    # every field still resolves to a valid SIDC rather than an
    # empty-string one mct_build_sidc() would reject. Default entity was
    # "checkpoint" until 2026-08-10, when Table H-VI (which owned it)
    # moved out to its own layer - see _ENTITY_LABELS' own comment.
    layer.setDefaultValueDefinition(affiliation_idx, QgsDefaultValue("'friend'"))
    layer.setDefaultValueDefinition(entity_idx, QgsDefaultValue("'distressed_vessel'"))
    layer.setDefaultValueDefinition(status_idx, QgsDefaultValue("'present'"))


def _build_renderer():

    """
    One symbol, one QgsSvgMarkerSymbolLayer, whose own path is
    data-defined per feature via _SIDC_EXPRESSION - same mechanism as
    unit_layer.py's _build_renderer(), already confirmed live to work.
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


def create_control_measure_points_layer(name=OUTPUT_LAYER_NAME):

    """
    A fresh, empty "Control Measure Points" point
    layer, in the current project's own CRS - fields (affiliation/
    entity/status/unique_designation), a friendly attribute form, and a
    renderer that draws the correct MIL-STD-2525/APP-6 symbol from
    those fields automatically. Never added to the project by this
    function itself - same hand-placed-operational-data contract as
    unit_layer.py's create_unit_layer(), see that module's own
    docstring for why.
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
            QgsField("status", QMetaType.Type.QString),
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
    Top of the layer tree - matches unit_layer.py's own convention for
    an operational overlay meant to sit above whatever base terrain
    rendering is underneath.
    """

    root = project.layerTreeRoot()

    root.insertLayer(
        0,
        layer
    )


def add_control_measure_points_layer(iface):

    """
    The toolbar action's own callback (bundled into the same "Tactical
    Graphics - Control Measures" action as the lines/areas layers - see
    plugin.py's create_control_measures()). If a layer named
    OUTPUT_LAYER_NAME already exists, does nothing but warn - same
    data-loss guard as add_unit_layer(). Returns the new layer, or None
    if one already existed.
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

    layer = create_control_measure_points_layer()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
