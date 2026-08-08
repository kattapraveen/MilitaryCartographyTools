# -*- coding: utf-8 -*-

"""
Tests for military_symbology/_point_symbol_layer.py - the shared
single-domain point layer factory every appendix-specific layer
(space_layer.py, and future ones) is built on. Exercised here with a
synthetic ground_unit-style vocabulary, decoupled from any one
appendix's own data.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
    _value_map_with_none,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

_ENTITY_LABELS = {"infantry": "Infantry"}

_SECTOR1_LABELS = {"low_earth_orbit": "Low Earth Orbit (LEO)"}
_SECTOR2_LABELS = {"optical": "Optical"}


class TestIncludeEchelonAndHeadquarters(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_both_included_by_default(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "ground_unit",
            _ENTITY_LABELS,
            "infantry",
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertIn("echelon", field_names)
        self.assertIn("headquarters", field_names)

        self.assertEqual(
            layer.editorWidgetSetup(
                layer.fields().indexOf("echelon")
            ).type(),
            "ValueMap"
        )
        self.assertEqual(
            layer.editorWidgetSetup(
                layer.fields().indexOf("headquarters")
            ).type(),
            "CheckBox"
        )


    def test_both_excluded_when_opted_out(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "ground_unit",
            _ENTITY_LABELS,
            "infantry",
            include_echelon=False,
            include_headquarters=False,
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertNotIn("echelon", field_names)
        self.assertNotIn("headquarters", field_names)


    def test_excluding_echelon_alone_still_keeps_headquarters(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "ground_unit",
            _ENTITY_LABELS,
            "infantry",
            include_echelon=False,
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertNotIn("echelon", field_names)
        self.assertIn("headquarters", field_names)


class TestSector1AndSector2Modifiers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_excluded_by_default(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "ground_unit",
            _ENTITY_LABELS,
            "infantry",
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertNotIn("sector1_modifier", field_names)
        self.assertNotIn("sector2_modifier", field_names)


    def test_included_when_labels_given(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "space",
            _ENTITY_LABELS,
            "infantry",
            sector1_labels=_SECTOR1_LABELS,
            sector2_labels=_SECTOR2_LABELS,
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertIn("sector1_modifier", field_names)
        self.assertIn("sector2_modifier", field_names)


    def test_sector1_alone_does_not_include_sector2(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "space",
            _ENTITY_LABELS,
            "infantry",
            sector1_labels=_SECTOR1_LABELS,
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertIn("sector1_modifier", field_names)
        self.assertNotIn("sector2_modifier", field_names)


    def test_dropdown_has_a_none_option_and_defaults_to_it(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "space",
            _ENTITY_LABELS,
            "infantry",
            sector1_labels=_SECTOR1_LABELS,
        )

        idx = layer.fields().indexOf("sector1_modifier")

        config = layer.editorWidgetSetup(idx).config()

        self.assertEqual(config["map"]["(None)"], "")

        default_expr = layer.defaultValueDefinition(idx).expression()

        self.assertEqual(default_expr, "''")


class TestValueMapWithNone(QgisTestCase):

    def test_prepends_a_none_entry_mapped_to_empty_string(self):

        result = _value_map_with_none({"low_earth_orbit": "Low Earth Orbit (LEO)"})

        self.assertEqual(result["(None)"], "")
        self.assertEqual(result["Low Earth Orbit (LEO)"], "low_earth_orbit")
