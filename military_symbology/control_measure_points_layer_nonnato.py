# -*- coding: utf-8 -*-

"""
Builds the "Control Measure Points (Non-NATO)" point layer.

The affiliation here is one of the four real standard identities and
goes into the SIDC, as on NATO's own control-measure points - Part C's
"affiliation is coded the same way as NATO". Every entity renders
through one function, nonnato_symbol_engine.render_nonnato_control_
measure_svg(), whose docstring says what each gets:

- Decision Point, Impact Point, Observation Post, Artillery Observation
  Post, Point Of Interest and Target/DF Task: milsymbol's render in the
  scheme's affiliation palette (since 2026-09-17 - decided on the Office
  companion 2026-09-15/16), where they used to be milsymbol's black and
  red.
- Fort, Shelter Above Ground and Shelter Below Ground: milsymbol's
  render, its own colours.
- Pill Box: the same, forced hollow (apply_pillbox_fixup()).
- Added 2026-09-17: Command Post (Military Police relettered "CP"), NBC
  Shelter (Shelter Below Ground, hollow, "NBC" to its right unless a
  designation is typed) and Fire Trench/Weapon Pit/Weapon Emplacement
  (a rectangle open at the bottom, drawn by the engine).

Until 2026-09-17 nine entities went through the NATO layers' own
mct_sidc_svg()/mct_build_sidc() expression and Pill Box through its own
function. That split could not carry three new drawings and a palette,
so it became one function; the entities it did not change render
byte-for-byte as before (tested).

Booby Trap (`booby_trap`) moved OUT 2026-09-03 to "Mines and Obstacles
(Non-NATO)", alongside the mine family - see
mines_and_obstacles_layer_nonnato.py.

Required entities and renames - see the rules record's "Control
Measure Points" section: `target_reference_point` -> Target/DF Task
(renamed again 2026-09-03, from plain "Target"), `shelter` -> Pill Box,
`observation_post_forward_observer` -> Artillery Observation Post. No
echelon/headquarters field - Appendix H's own amplifier table gives
control-measure points neither, and Command Post's frame takes none
either.

Reachable via its own "Control Measure Points" entry in the toolbar's
"Non-NATO Symbols" group (see plugin.py), or directly via
add_control_measure_points_layer_nonnato(iface).

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

from ._control_measure_shared import (
    _configure_point_affiliation_field,
    _configure_status_field,
    _value_map,
    add_layer_if_absent,
    configure_rotation_and_scale_fields,
)
from .nonnato_symbol_engine import (
    AREA_NAI_ENTITY,
    AREA_TAI_ENTITY,
    DF_SOS_ENTITY,
    POINT_NAI_ENTITY,
    POINT_TAI_ENTITY,
    AIR_DEFENCE_OP_ENTITY,
    AIR_FORCE_OP_ENTITY,
    AIR_HEAD_ENTITY,
    LISTENING_POST_ENTITY,
    MOBILE_OP_ENTITY,
    BEACH_HEAD_ENTITY,
    BRIDGE_HEAD_ENTITY,
    VITAL_AREA_ENTITY,
    VITAL_POINT_ENTITY,
    COMMAND_POST_ENTITY,
    FIRE_TRENCH_ENTITY,
    NBC_SHELTER_ENTITY,
    stabilised_nonnato_size_expression,
)


LAYER_NAME = "Control Measure Points (Non-NATO)"

MARKER_SIZE_MM = 8.0

PILLBOX_ENTITY = "shelter"

# The thirteen entities. Real keys are sidc.py's own
# ENTITIES["control_measure"] keys, unchanged; the three added
# 2026-09-17 are the engine's own synthetic keys (see this module's
# docstring). Booby Trap (`booby_trap`) moved out to its own layer
# 2026-09-03.
ENTITY_LABELS = {
    AIR_DEFENCE_OP_ENTITY: "Air Defence Observation Post",
    AIR_FORCE_OP_ENTITY: "Air Force Observation Post",
    AIR_HEAD_ENTITY: "Air Head",
    AREA_NAI_ENTITY: "Area NAI",
    AREA_TAI_ENTITY: "Area TAI",
    BEACH_HEAD_ENTITY: "Beach Head",
    BRIDGE_HEAD_ENTITY: "Bridge Head",
    COMMAND_POST_ENTITY: "Command Post",
    "decision_point": "Decision Point",
    DF_SOS_ENTITY: "DF (SOS)",
    FIRE_TRENCH_ENTITY: "Fire Trench/Weapon Pit/Weapon Emplacement",
    "fort": "Fort",
    "impact_point": "Impact Point",
    LISTENING_POST_ENTITY: "Listening Post/Infantry Observation Post",
    MOBILE_OP_ENTITY: "Mobile Observation Post",
    NBC_SHELTER_ENTITY: "NBC Shelter",
    "observation_post": "Observation Post",
    "observation_post_forward_observer": "Artillery Observation Post",
    POINT_NAI_ENTITY: "Point NAI",
    "point_of_interest": "Point Of Interest",
    POINT_TAI_ENTITY: "Point TAI",
    "shelter": "Pill Box",
    "shelter_above_ground": "Shelter Above Ground",
    "shelter_below_ground": "Shelter Below Ground",
    "target_reference_point": "Target/DF Task",
    VITAL_AREA_ENTITY: "Vital Area",
    VITAL_POINT_ENTITY: "Vital Point",
}

SYNTHETIC_ENTITIES = frozenset({
    COMMAND_POST_ENTITY, FIRE_TRENCH_ENTITY, NBC_SHELTER_ENTITY,
    # Added 2026-09-23, all five drawn in the engine - three on Forces
    # in Defence's own ellipse turned over, and two of their own.
    AIR_HEAD_ENTITY, BEACH_HEAD_ENTITY, BRIDGE_HEAD_ENTITY,
    VITAL_AREA_ENTITY, VITAL_POINT_ENTITY,
    # Added 2026-09-24 - all four built on Artillery Observation
    # Post's own triangle.
    LISTENING_POST_ENTITY, AIR_FORCE_OP_ENTITY, AIR_DEFENCE_OP_ENTITY,
    MOBILE_OP_ENTITY,
    # And the NAI/TAI four plus DF (SOS), all built on a donor
    # entity's own render - Point of Interest and the Target cross.
    POINT_NAI_ENTITY, POINT_TAI_ENTITY, AREA_NAI_ENTITY, AREA_TAI_ENTITY,
    DF_SOS_ENTITY,
})

DEFAULT_ENTITY = "decision_point"

# coalesce() on every field, since QGIS nulls a whole function call when
# any argument is NULL and a feature pasted in or made outside the form
# arrives without defaults. Edition is fixed inside the engine (APP-6E,
# like every other non-NATO layer), not read from the plugin's setting.
_DESIGNATION_EXPRESSION = 'upper(coalesce("unique_designation", \'\'))'

_ARGUMENTS = (
    'coalesce("affiliation", \'friend\'),"entity",'
    'coalesce("status", \'present\')'
)

_NAME_EXPRESSION = (
    f"mct_nonnato_control_measure_svg({_ARGUMENTS},{_DESIGNATION_EXPRESSION})"
)

_SCALED_SIZE_EXPRESSION = f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'

# The icon holds its size when a designation is typed - the width with
# it over the width without. "Without" also leaves out NBC Shelter's
# default "NBC" (the trailing false), so that text hangs outside the
# glyph like any typed one instead of shrinking it.
_SIZE_EXPRESSION = stabilised_nonnato_size_expression(
    _SCALED_SIZE_EXPRESSION,
    f"mct_nonnato_control_measure_svg_width({_ARGUMENTS},"
    f"{_DESIGNATION_EXPRESSION})",
    f"mct_nonnato_control_measure_svg_width({_ARGUMENTS},'',false)",
)


def _configure_attribute_form(layer):

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("entity"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(ENTITY_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("entity"), QgsDefaultValue(f"'{DEFAULT_ENTITY}'")
    )

    # The four real SIDC standard identities (not the six-colour
    # non-NATO palette) - see _configure_point_affiliation_field()'s
    # own docstring for why a milsymbol-rendered Points layer must use
    # this one, not the plain lines/areas affiliation field.
    _configure_point_affiliation_field(layer)

    _configure_status_field(layer)

    configure_rotation_and_scale_fields(layer)


def _build_renderer():

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(MARKER_SIZE_MM)

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Size,
        QgsProperty.fromExpression(_SIZE_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Name,
        QgsProperty.fromExpression(_NAME_EXPRESSION)
    )

    svg_layer.setDataDefinedProperty(
        QgsSymbolLayer.Property.Angle,
        QgsProperty.fromExpression('coalesce("rotation", 0)')
    )

    symbol.changeSymbolLayer(0, svg_layer)

    return QgsSingleSymbolRenderer(symbol)


def build_control_measure_points_layer_nonnato():

    """A fresh, empty "Control Measure Points (Non-NATO)" layer - never added to the project itself, see add_control_measure_points_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}",
        LAYER_NAME,
        "memory"
    )

    attributes = [
        QgsField("affiliation", QMetaType.Type.QString),
        QgsField("entity", QMetaType.Type.QString),
        QgsField("status", QMetaType.Type.QString),
        QgsField("unique_designation", QMetaType.Type.QString),
        QgsField("rotation", QMetaType.Type.Double),
        QgsField("scale", QMetaType.Type.Double),
    ]

    layer.dataProvider().addAttributes(attributes)

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_control_measure_points_layer_nonnato(iface):

    return add_layer_if_absent(
        iface,
        LAYER_NAME,
        build_control_measure_points_layer_nonnato,
    )
