# -*- coding: utf-8 -*-

"""
Tests for military_symbology/sigint_layer.py - "SIGINT" (MIL-STD-2525D
Appendix J). A single layer spanning FIVE symbol
sets (sigint_space/air/land/sea_surface/subsurface) via the "Dimension"
field mechanism in _point_symbol_layer.py - see that module's own tests
(test_point_symbol_layer.py's TestDimensionField) for the mechanism
itself; these tests cover SIGINT's own real vocabulary and wiring.

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

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import sigint_layer
from MilitaryCartographyTools.military_symbology.sidc import ENTITIES, MODIFIERS
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
)
from MilitaryCartographyTools.military_symbology.sigint_layer import (
    OUTPUT_LAYER_NAME,
    add_sigint_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    def test_entity_labels_cover_every_sigint_entity(self):

        # Same 4-entity dict is aliased under all five sigint_* keys in
        # sidc.py - checking against one of them checks all of them.
        self.assertEqual(
            set(sigint_layer._ENTITY_LABELS),
            set(ENTITIES["sigint_air"])
        )


    def test_sector1_labels_cover_every_sigint_modifier(self):

        self.assertEqual(
            set(sigint_layer._SECTOR1_LABELS),
            set(MODIFIERS["sigint_air"]["sector1"])
        )


    def test_dimension_labels_and_symbol_sets_have_matching_keys(self):

        self.assertEqual(
            set(sigint_layer._DIMENSION_LABELS),
            set(sigint_layer._DIMENSION_SYMBOL_SETS)
        )


    def test_every_dimension_symbol_set_exists_in_sidc(self):

        for dimension, symbol_set in sigint_layer._DIMENSION_SYMBOL_SETS.items():

            with self.subTest(dimension=dimension):

                self.assertIn(symbol_set, ENTITIES)
                self.assertIn(symbol_set, MODIFIERS)


class TestBuildSigintLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _build(self):

        return build_single_domain_point_layer(
            OUTPUT_LAYER_NAME,
            "sigint_air",
            sigint_layer._ENTITY_LABELS,
            sigint_layer.DEFAULT_ENTITY,
            include_echelon=False,
            include_headquarters=False,
            sector1_labels=sigint_layer._SECTOR1_LABELS,
            dimension_labels=sigint_layer._DIMENSION_LABELS,
            dimension_symbol_sets=sigint_layer._DIMENSION_SYMBOL_SETS,
            default_dimension=sigint_layer.DEFAULT_DIMENSION,
        )


    def test_has_the_expected_fields_no_echelon_no_headquarters_no_sector2(self):

        # Table J-II lists no Field B (Echelon)/Field S (Headquarters) -
        # see sigint_layer.py's own docstring on why this plugin doesn't
        # attempt a per-dimension conditional field set instead.
        # J.5.3.2's own text: no sector 2 modifiers in SIGINT.
        layer = self._build()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "affiliation",
                "dimension",
                "entity",
                "status",
                "sector1_modifier",
                "unique_designation",
            ]
        )


    def _resolve_svg_path(self, layer, entity, dimension, sector1_modifier=""):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("dimension", dimension)
        feature.setAttribute("entity", entity)
        feature.setAttribute("status", "present")
        feature.setAttribute("sector1_modifier", sector1_modifier)

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


    def test_the_same_entity_resolves_across_every_dimension(self):

        # The whole point of Appendix J's own construction - Table
        # J-II's SymbolSetCode column lists the same four entity codes
        # against all five symbol sets at once.
        layer = self._build()

        for dimension in sigint_layer._DIMENSION_SYMBOL_SETS:

            with self.subTest(dimension=dimension):

                path, ok = self._resolve_svg_path(layer, "radar", dimension)

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


    def test_the_hierarchy_only_generic_entity_resolves(self):

        # "signal_intercept" (110000) has no icon in milsymbol's own
        # source - frame-only, per Table J-II's own remarks column.
        layer = self._build()

        path, ok = self._resolve_svg_path(layer, "signal_intercept", "space")

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


    def test_an_entity_with_a_sector1_modifier_resolves(self):

        layer = self._build()

        path, ok = self._resolve_svg_path(
            layer,
            "jammer",
            "air",
            sector1_modifier="noise_jammer",
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


class TestAddSigintLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_sigint_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_sigint_layer(self.iface)

        result = add_sigint_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_sigint_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], OUTPUT_LAYER_NAME)
