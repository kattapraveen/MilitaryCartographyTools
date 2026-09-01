# -*- coding: utf-8 -*-

"""
Builds the "SIGINT (Non-NATO)" point layer.

Land-scoped only, per the rules record's Part B: "Land SIGINT: only
Jammer and Radar are required, following the same rules as Land
Equipment (no frame, bare glyph, affiliation by the glyph's own
outline colour)." Structurally this is land_equipment_layer_nonnato
.py's own shape (no echelon/status/combined_arms), just a two-entry
vocabulary and no mine-family colour exception - and no Dimension
field either, unlike the NATO SIGINT layer (sigint_layer.py), since
non-NATO scope never needed Space/Air/Sea Surface/Subsurface. See
military_symbology/nonnato_symbol_engine.py's render_nonnato_sigint_
svg() for the actual rendering logic, called via mct_nonnato_sigint_svg()
(expressions/nonnato_symbology_functions.py).

No toolbar action yet, same as Land Unit/Land Equipment - reachable
only by calling add_land_sigint_layer_nonnato(iface) directly.

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
from .nonnato_symbol_engine import stabilised_nonnato_size_expression


LAYER_NAME = "SIGINT (Non-NATO)"

DEFAULT_ENTITY = "radar"

MARKER_SIZE_MM = 8.0

# Land SIGINT's own entire required vocabulary - see this module's own
# docstring and the rules record's Part B. No renaming (unlike Land
# Unit/Land Equipment): Jammer/Radar keep their NATO labels unchanged.
ENTITY_LABELS = {
    "jammer": "Jammer",
    "radar": "Radar",
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
        'mct_nonnato_sigint_svg('
        f'"affiliation","entity",{designation_expression}'
        ')'
    )

    symbol = QgsMarkerSymbol()

    svg_layer = QgsSvgMarkerSymbolLayer("")

    svg_layer.setSize(MARKER_SIZE_MM)

    scaled_size_expression = (
        f'{MARKER_SIZE_MM:g} * coalesce("scale", 100) / 100.0'
    )

    # Holds the icon still when a designation is typed in - see
    # stabilised_nonnato_size_expression()'s own docstring for the
    # 2026-09-02 fix this is (reported against Land Unit, applied
    # "across the board" per the maintainer's own instruction).
    amplified_width_expression = (
        'mct_nonnato_sigint_svg_width('
        f'"affiliation","entity",{designation_expression}'
        ')'
    )

    plain_width_expression = (
        "mct_nonnato_sigint_svg_width(\"affiliation\",\"entity\",'')"
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


def build_land_sigint_layer_nonnato():

    """A fresh, empty "SIGINT (Non-NATO)" layer - never added to the project itself, see add_land_sigint_layer_nonnato()."""

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


def add_land_sigint_layer_nonnato(iface):

    """
    Guard-and-insert: if "SIGINT (Non-NATO)" already exists, warns and
    does nothing; otherwise builds and inserts a fresh one. Returns the
    new layer, or None if one already existed.
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

    layer = build_land_sigint_layer_nonnato()

    return add_layer_at_default_position(
        project,
        layer,
        default_insert_position
    )
