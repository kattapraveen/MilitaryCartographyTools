# -*- coding: utf-8 -*-

"""
Tests for military_symbology/_control_measure_shared.py's
configure_rotation_and_scale_fields() - the U-2 (build tracker) widget/
default/alias contract every point-symbol layer wanting rotation and
scale shares, first extracted here 2026-08-19 (obstacle_control_
measures.py's own Trip Wire/Abatis rebuild) and reused since by every
module in that build's own rollout to the ~15 modules that build their
own point renderer rather than going through _point_symbol_layer.py.

Exercised here directly, against a bare synthetic layer, rather than
only indirectly through each caller's own field-list test - those tests
confirm the FIELDS exist, not that this shared function configures them
correctly; a mistake here would otherwise only show up per-caller.

Military Cartography Tools
"""

from qgis.core import QgsField, QgsVectorLayer

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.military_symbology._control_measure_shared import (
    configure_rotation_and_scale_fields,
)

from qgis.PyQt.QtCore import QMetaType


def _layer_with_rotation_and_scale_fields():

    layer = QgsVectorLayer("Point?crs=EPSG:4326", "probe", "memory")

    layer.dataProvider().addAttributes(
        [
            QgsField("rotation", QMetaType.Type.Double),
            QgsField("scale", QMetaType.Type.Double),
        ]
    )

    layer.updateFields()

    return layer


class TestConfigureRotationAndScaleFields(QgisTestCase):

    def test_both_use_a_range_spin_box_widget(self):

        layer = _layer_with_rotation_and_scale_fields()

        configure_rotation_and_scale_fields(layer)

        for name, expected_min, expected_max in (
            ("rotation", 0.0, 360.0), ("scale", 10.0, 400.0)
        ):

            with self.subTest(field=name):

                idx = layer.fields().indexOf(name)
                setup = layer.editorWidgetSetup(idx)

                self.assertEqual(setup.type(), "Range")

                config = setup.config()

                self.assertEqual(config["Min"], expected_min)
                self.assertEqual(config["Max"], expected_max)
                self.assertEqual(config["Style"], "SpinBox")
                self.assertFalse(config["AllowNull"])


    def test_default_values(self):

        layer = _layer_with_rotation_and_scale_fields()

        configure_rotation_and_scale_fields(layer)

        rotation_idx = layer.fields().indexOf("rotation")
        scale_idx = layer.fields().indexOf("scale")

        self.assertEqual(
            layer.defaultValueDefinition(rotation_idx).expression(), "0"
        )
        self.assertEqual(
            layer.defaultValueDefinition(scale_idx).expression(), "100"
        )


    def test_field_aliases_name_the_unit(self):

        layer = _layer_with_rotation_and_scale_fields()

        configure_rotation_and_scale_fields(layer)

        rotation_idx = layer.fields().indexOf("rotation")
        scale_idx = layer.fields().indexOf("scale")

        self.assertIn("°", layer.attributeAlias(rotation_idx))
        self.assertIn("%", layer.attributeAlias(scale_idx))
