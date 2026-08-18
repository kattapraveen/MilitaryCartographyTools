# -*- coding: utf-8 -*-

"""
Tests for military_symbology/subsurface_layer.py - "Subsurface" /
"Mine Warfare" (MIL-STD-2525D Appendix F). Two separate layers (Mine Warfare's 64-entity vocabulary is
too large to fold into a companion the way Space/Air Missile's single
entity was), mirroring Land's "several layers under one action" pattern.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase, edition_layer_name

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import subsurface_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.subsurface_layer import (
    SUBSURFACE_LAYER_NAME,
    MINE_WARFARE_LAYER_NAME,
    add_subsurface_layer,
    add_mine_warfare_layer,
    add_subsurface_layers,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_subsurface_entity_labels_cover_every_entity(self):

        self.assertEqual(
            set(subsurface_layer._SUBSURFACE_ENTITY_LABELS),
            set(ENTITIES["subsurface"])
        )


    def test_mine_warfare_entity_labels_cover_every_entity(self):

        self.assertEqual(
            set(subsurface_layer._MINE_WARFARE_ENTITY_LABELS),
            set(ENTITIES["mine_warfare"])
        )


    def test_subsurface_sector_labels_cover_every_modifier(self):

        self.assertEqual(
            set(subsurface_layer._SUBSURFACE_SECTOR1_LABELS),
            set(MODIFIERS["subsurface"]["sector1"])
        )
        self.assertEqual(
            set(subsurface_layer._SUBSURFACE_SECTOR2_LABELS),
            set(MODIFIERS["subsurface"]["sector2"])
        )


class TestBuildLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _build_subsurface(self):

        return build_single_domain_point_layer(
            SUBSURFACE_LAYER_NAME,
            "subsurface",
            subsurface_layer._SUBSURFACE_ENTITY_LABELS,
            subsurface_layer.DEFAULT_SUBSURFACE_ENTITY,
            include_echelon=False,
            include_headquarters=False,
            sector1_labels=subsurface_layer._SUBSURFACE_SECTOR1_LABELS,
            sector2_labels=subsurface_layer._SUBSURFACE_SECTOR2_LABELS,
        )


    def _build_mine_warfare(self):

        return build_single_domain_point_layer(
            MINE_WARFARE_LAYER_NAME,
            "mine_warfare",
            subsurface_layer._MINE_WARFARE_ENTITY_LABELS,
            subsurface_layer.DEFAULT_MINE_WARFARE_ENTITY,
            include_echelon=False,
            include_headquarters=False,
        )


    def test_subsurface_has_the_expected_fields(self):

        # Table F-II (Appendix F's own amplifier table) lists neither
        # Field B (Echelon) nor Field S (Headquarters Staff Indicator).
        layer = self._build_subsurface()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "entity",
                "status",
                "sector1_modifier",
                "sector2_modifier",
                "unique_designation",
            ]
        )


    def test_mine_warfare_has_no_sector_modifier_fields(self):

        # milsymbol's own minewarfare.js has zero sIdm1/sIdm2 entries.
        layer = self._build_mine_warfare()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "entity",
                "status",
                "unique_designation",
            ]
        )


    def _resolve_svg_path(self, layer, entity, sector1_modifier="", sector2_modifier=""):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", entity)
        feature.setAttribute("status", "present")

        # setAttribute() by name raises KeyError if the field doesn't
        # exist on this layer (e.g. Mine Warfare has no sector modifier
        # fields at all) - only set it when present, but always set it
        # to an explicit "" when present rather than leaving it NULL,
        # since NULL resolves to a genuinely different (and wrong) SIDC
        # than an explicit empty string does.
        field_names = [f.name() for f in layer.fields()]

        if "sector1_modifier" in field_names:
            feature.setAttribute("sector1_modifier", sector1_modifier)
        if "sector2_modifier" in field_names:
            feature.setAttribute("sector2_modifier", sector2_modifier)

        expr_context = QgsExpressionContext()
        expr_context.appendScope(
            QgsExpressionContextUtils.layerScope(layer)
        )
        expr_context.setFeature(feature)

        render_context = QgsRenderContext()
        render_context.setExpressionContext(expr_context)

        symbol = layer.renderer().symbol().clone()
        symbol.startRender(render_context, layer.fields())

        svg_layer = symbol.symbolLayer(0)

        return svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            expr_context,
            ""
        )


    def test_the_originally_reported_military_generic_entity_resolves(self):

        # The user's originally-reported bug: "Subsurface - Military
        # Generic is in Air, Sea Surface [but not for Subsurface]".
        # Confirms it resolves correctly on this dedicated layer.
        layer = self._build_subsurface()

        path, ok = self._resolve_svg_path(layer, "military")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_subsurface_entity_with_sector_modifiers_resolves(self):

        layer = self._build_subsurface()

        path, ok = self._resolve_svg_path(
            layer,
            "submarine",
            sector1_modifier="antisubmarine_warfare",
            sector2_modifier="nuclear_powered",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_mine_warfare_entity_resolves(self):

        layer = self._build_mine_warfare()

        path, ok = self._resolve_svg_path(layer, "sea_mine")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_a_milco_confidence_level_variant_resolves(self):

        # Confirms the confidence-level 1-5 sub-variants (the systematic
        # axis caught by the full parse before curation, unlike Land
        # Equipment's original miss) actually resolve.
        layer = self._build_mine_warfare()

        path, ok = self._resolve_svg_path(layer, "sea_mine_milco_bottom_confidence_3")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


class TestAddSubsurfaceLayers(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_add_subsurface_layers_creates_both(self):

        result = add_subsurface_layers(self.iface)

        for name in (SUBSURFACE_LAYER_NAME, MINE_WARFARE_LAYER_NAME):

            self.assertIsNotNone(result[name])

            matching = QgsProject.instance().mapLayersByName(edition_layer_name(name))

            self.assertEqual(len(matching), 1)


    def test_each_individual_adder_guards_against_a_duplicate(self):

        for adder, name in (
            (add_subsurface_layer, SUBSURFACE_LAYER_NAME),
            (add_mine_warfare_layer, MINE_WARFARE_LAYER_NAME),
        ):

            with self.subTest(name=name):

                first = adder(self.iface)

                result = adder(self.iface)

                self.assertIsNone(result)

                matching = QgsProject.instance().mapLayersByName(edition_layer_name(name))

                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_subsurface_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], edition_layer_name(SUBSURFACE_LAYER_NAME))
