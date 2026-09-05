# -*- coding: utf-8 -*-

"""
Builds the "Control Measure Points (Non-NATO)" point layer.

Structurally different from every other non-NATO layer in this branch:
Part C's own settled mechanism note - "affiliation is coded the same
way as NATO... no non-NATO-specific treatment needed for that part" -
means nine of these ten entities get NO new rendering logic at all.
They render through the exact same mct_sidc_svg()/mct_build_sidc()
pipeline every other NATO control-measure-points layer already uses
(see field_fortification.py's own points layer for the closest
precedent), with milsymbol's own real 4-value affiliation colouring
and no monoColor override - not the six-colour non-NATO palette
Land Unit/Land Equipment/SIGINT use.

Pill Box is the one exception: it still goes through milsymbol but
needs its own hollow-fill fixup (see apply_pillbox_fixup()'s own
docstring - milsymbol's own `fill: false` option does nothing for it,
confirmed live). Selected by a CASE in the renderer expression exactly
the way obstacle_control_measures.py already branches Trip Wire/Abatis
onto their own custom shapes alongside plain milsymbol entities on the
same layer.

Booby Trap (`booby_trap`) - the other custom-icon exception this layer
used to carry - moved OUT 2026-09-03 to its own "Mines and Obstacles
(Non-NATO)" layer, alongside the mine family that moved out of Land
Equipment the same day: "let's move all the mines to a different
layer - say mines and obstacles; shift booby trap also into this new
layer". See mines_and_obstacles_layer_nonnato.py -
nonnato_symbol_engine.booby_trap_control_measure_svg() itself is
unchanged, only which layer offers it changed.

Required entities and renames - see the rules record's "Control
Measure Points" section: `target_reference_point` -> Target/DF Task
(renamed again 2026-09-03, from plain "Target"), `shelter` -> Pill Box,
`observation_post_forward_observer` -> Artillery Observation Post. No
echelon/headquarters field - Appendix H's own amplifier table gives
control-measure points neither, same as every other Points layer built
from this table.

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
    stabilised_point_size_expression,
)
from .nonnato_symbol_engine import stabilised_nonnato_size_expression


LAYER_NAME = "Control Measure Points (Non-NATO)"

MARKER_SIZE_MM = 8.0

PILLBOX_ENTITY = "shelter"

# The ten required entities - see this module's own docstring and
# the rules record's "Control Measure Points" section. Keys are
# sidc.py's own ENTITIES["control_measure"] keys, unchanged (real 2525E
# entities, confirmed to exist under that edition and to render as real
# glyphs - not the unknown-icon fallback - before this module was
# written). Only three get a renamed display label. Booby Trap
# (`booby_trap`) moved out to its own layer 2026-09-03 - see this
# module's own docstring.
ENTITY_LABELS = {
    "decision_point": "Decision Point",
    "fort": "Fort",
    "impact_point": "Impact Point",
    "observation_post": "Observation Post",
    "observation_post_forward_observer": "Artillery Observation Post",
    "point_of_interest": "Point Of Interest",
    "shelter": "Pill Box",
    "shelter_above_ground": "Shelter Above Ground",
    "shelter_below_ground": "Shelter Below Ground",
    "target_reference_point": "Target/DF Task",
}

DEFAULT_ENTITY = "decision_point"

# The plain milsymbol path every entity except Booby Trap uses - the
# exact same mct_sidc_svg(mct_build_sidc(...)) shape every other
# control-measure Points layer already builds (see
# field_fortification.py's own create_field_fortification_points_layer
# for the closest precedent, via build_single_domain_point_layer()).
# No echelon/headquarters field on this layer, so both are passed as
# their literal "no amplifier" values rather than a field reference.
# Edition is pinned to '2525E' as a literal, not read from the plugin's
# current_edition() setting, matching every other non-NATO layer's own
# settled "APP-6E only" rule - unlike every OTHER caller of this
# pattern, which follows the plugin-wide edition setting instead.
_MILSYMBOL_SIDC_EXPRESSION = (
    'mct_sidc_svg(mct_build_sidc('
    '"affiliation","entity",\'control_measure\',\'unspecified\','
    '"status",false,\'\',\'\',\'2525E\'),'
    'upper(coalesce("unique_designation",\'\')),'
    "'uniqueDesignation')"
)

# Pill Box needs its own hollow-fill fixup (see nonnato_symbol_engine.
# apply_pillbox_fixup()'s own docstring) - the only other departure
# from the plain milsymbol pipeline on this layer besides Booby Trap.
_PILLBOX_DESIGNATION_EXPRESSION = 'upper(coalesce("unique_designation", \'\'))'

_PILLBOX_EXPRESSION = (
    'mct_nonnato_pillbox_svg('
    f'"affiliation","status",{_PILLBOX_DESIGNATION_EXPRESSION}'
    ')'
)

_NAME_EXPRESSION = (
    "CASE"
    f" WHEN \"entity\" = '{PILLBOX_ENTITY}' THEN {_PILLBOX_EXPRESSION}"
    f" ELSE {_MILSYMBOL_SIDC_EXPRESSION}"
    " END"
)

_SCALED_SIZE_EXPRESSION = f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'

# Pill Box gets its own width-based ratio (mct_nonnato_pillbox_svg_
# width(), since it branches off the plain pipeline below); every
# other entity keeps the existing mct_sidc_svg_width()-based one.
_SIZE_EXPRESSION = (
    "CASE"
    f" WHEN \"entity\" = '{PILLBOX_ENTITY}' THEN ("
    + stabilised_nonnato_size_expression(
        _SCALED_SIZE_EXPRESSION,
        'mct_nonnato_pillbox_svg_width('
        f'"affiliation","status",{_PILLBOX_DESIGNATION_EXPRESSION})',
        'mct_nonnato_pillbox_svg_width("affiliation","status",\'\')',
    )
    + ")"
    " ELSE ("
    + stabilised_point_size_expression(
        _SCALED_SIZE_EXPRESSION, _MILSYMBOL_SIDC_EXPRESSION
    )
    + ")"
    " END"
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
