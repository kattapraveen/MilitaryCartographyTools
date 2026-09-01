# -*- coding: utf-8 -*-

"""
Tests for military_symbology/nonnato_layers.py - add_nonnato_land_layers(),
the non-NATO counterpart to land_layer.py's own add_land_layers().

Military Cartography Tools
"""

from qgis.core import QgsCoordinateReferenceSystem, QgsProject

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import nonnato_symbology_functions
from MilitaryCartographyTools.military_symbology.land_equipment_layer_nonnato import (
    LAYER_NAME as EQUIPMENT_LAYER_NAME,
    add_land_equipment_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.land_unit_layer_nonnato import (
    LAYER_NAME as UNIT_LAYER_NAME,
    add_land_unit_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_layers import (
    add_nonnato_land_layers,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestAddNonnatoLandLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_creates_both_layers(self):

        result = add_nonnato_land_layers(self.iface)

        for name in (UNIT_LAYER_NAME, EQUIPMENT_LAYER_NAME):

            self.assertIsNotNone(result[name])

            matching = QgsProject.instance().mapLayersByName(name)

            self.assertEqual(len(matching), 1)


    def test_calling_twice_only_fills_in_whats_missing(self):

        add_land_unit_layer_nonnato(self.iface)

        result = add_nonnato_land_layers(self.iface)

        # Unit was already there (None, warned) - Equipment is new.
        self.assertIsNone(result[UNIT_LAYER_NAME])
        self.assertIsNotNone(result[EQUIPMENT_LAYER_NAME])

        for name in (UNIT_LAYER_NAME, EQUIPMENT_LAYER_NAME):

            matching = QgsProject.instance().mapLayersByName(name)

            self.assertEqual(len(matching), 1)
