# -*- coding: utf-8 -*-

"""
Builds the "Echelons (Non-NATO)" point layer.

New 2026-09-25, dictated on the Office companion and built there
first: ten entities, Detachment through Army Group, each drawing
milsymbol's own echelon marker ALONE. There is no Unspecified - it has
no marker.

**Layer, entity, affiliation and size; nothing else.** No status, no
designation, no Headquarters, no Combined Arms - a bare marker has
nowhere to put any of them.

**All ten share ONE box**, the union of the widest and the tallest -
see nonnato_symbol_engine.echelon_shared_box(). A box around each
marker's own ink would make them absurd beside each other: Company is a
single bar and Army Group is 170 units of crosses, so at one chosen
size the bar would come out as wide as the whole Army Group row.
Sharing a box means a Company inserted at 24 mm is the same bar you
would see on a 24 mm unit symbol.

Detachment's slash is stripped here exactly as it is on the unit
layers - the same echelon must not look like two different things on
two layers.

Reachable via the "Echelons" entry in the toolbar's "Non-NATO Symbols"
group (see plugin.py), or directly via
add_echelons_layer_nonnato(iface).

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

from ._control_measure_shared import add_layer_if_absent
from .land_unit_layer_nonnato import AFFILIATION_LABELS


LAYER_NAME = "Echelons (Non-NATO)"

# The same renaming the Land Unit dialog uses, minus Unspecified, which
# milsymbol draws no marker for. Kept in the engine's own
# ECHELON_MARKER_ENTITIES order, which a test holds these to.
ENTITY_LABELS = {
    "team_crew": "Detachment",
    "squad": "Squad",
    "platoon": "Platoon/Troop",
    "company": "Company/Squadron/Battery",
    "battalion": "Battalion",
    "brigade": "Brigade",
    "division": "Division",
    "corps": "Corps",
    "army": "Army",
    "army_group": "Army Group",
}

DEFAULT_ENTITY = "company"

MARKER_SIZE_MM = 8.0

# No width companion and no stabiliser: every marker is drawn in the
# same box, so nothing varies the declared width, and there is no
# designation to hold the icon steady against.
_SIZE_EXPRESSION = f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'

_NAME_EXPRESSION = (
    'mct_nonnato_echelon_svg('
    'coalesce("affiliation", \'friend\'),'
    'coalesce("entity", \'company\'))'
)


def _value_map(labels):

    return {label: value for value, label in labels.items()}


def _configure_attribute_form(layer):

    fields = layer.fields()

    layer.setEditorWidgetSetup(
        fields.indexOf("entity"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(ENTITY_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("entity"), QgsDefaultValue(f"'{DEFAULT_ENTITY}'")
    )

    # The scheme's own six, as the unit layers offer - a marker is
    # coloured, not identified, so this never reaches a SIDC.
    layer.setEditorWidgetSetup(
        fields.indexOf("affiliation"),
        QgsEditorWidgetSetup("ValueMap", {"map": _value_map(AFFILIATION_LABELS)})
    )
    layer.setDefaultValueDefinition(
        fields.indexOf("affiliation"), QgsDefaultValue("'friend'")
    )


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

    symbol.changeSymbolLayer(0, svg_layer)

    return QgsSingleSymbolRenderer(symbol)


def build_echelons_layer_nonnato():

    """A fresh, empty "Echelons (Non-NATO)" layer - never added to the project itself, see add_echelons_layer_nonnato()."""

    crs = QgsProject.instance().crs()

    layer = QgsVectorLayer(
        f"Point?crs={crs.authid()}", LAYER_NAME, "memory"
    )

    layer.dataProvider().addAttributes([
        QgsField("affiliation", QMetaType.Type.QString),
        QgsField("entity", QMetaType.Type.QString),
        QgsField("scale", QMetaType.Type.Double),
    ])

    layer.updateFields()

    _configure_attribute_form(layer)

    layer.setRenderer(_build_renderer())

    return layer


def add_echelons_layer_nonnato(iface):

    """Adds the layer to the project, unless one of the same name is already there - the same helper every other non-NATO layer uses."""

    return add_layer_if_absent(iface, LAYER_NAME, build_echelons_layer_nonnato)
