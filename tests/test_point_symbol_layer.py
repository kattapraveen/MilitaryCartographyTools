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
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsRenderContext,
    QgsSymbolLayer,
    QgsVectorLayer,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology._point_symbol_layer import (
    build_single_domain_point_layer,
    default_insert_position,
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


class TestDimensionField(QgisTestCase):

    # Real symbol sets (not synthetic) - sigint_air/sigint_land share the
    # exact same entity vocabulary, exercising the genuine Appendix J
    # use case this mechanism was built for.
    _DIMENSION_LABELS = {"air": "Air", "land": "Land"}
    _DIMENSION_SYMBOL_SETS = {"air": "sigint_air", "land": "sigint_land"}
    _SIGINT_ENTITY_LABELS = {"radar": "Radar"}

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _build(self):

        return build_single_domain_point_layer(
            "Test Layer",
            "sigint_air",
            self._SIGINT_ENTITY_LABELS,
            "radar",
            include_echelon=False,
            include_headquarters=False,
            dimension_labels=self._DIMENSION_LABELS,
            dimension_symbol_sets=self._DIMENSION_SYMBOL_SETS,
            default_dimension="air",
        )


    def test_excluded_by_default(self):

        layer = build_single_domain_point_layer(
            "Test Layer",
            "ground_unit",
            _ENTITY_LABELS,
            "infantry",
        )

        field_names = [field.name() for field in layer.fields()]

        self.assertNotIn("dimension", field_names)


    def test_included_and_placed_before_entity_when_given(self):

        layer = self._build()

        field_names = [field.name() for field in layer.fields()]

        self.assertIn("dimension", field_names)
        self.assertLess(
            field_names.index("dimension"),
            field_names.index("entity")
        )


    def test_dropdown_and_default_value(self):

        layer = self._build()

        idx = layer.fields().indexOf("dimension")

        self.assertEqual(
            layer.editorWidgetSetup(idx).type(),
            "ValueMap"
        )

        default_expr = layer.defaultValueDefinition(idx).expression()

        self.assertEqual(default_expr, "'air'")


    def _resolve_svg_path(self, layer, dimension):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("dimension", dimension)
        feature.setAttribute("entity", "radar")
        feature.setAttribute("status", "present")

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


    def test_each_dimension_resolves_via_its_own_symbol_set(self):

        layer = self._build()

        for dimension in ("air", "land"):

            with self.subTest(dimension=dimension):

                path, ok = self._resolve_svg_path(layer, dimension)

                self.assertTrue(ok)
                self.assertTrue(path.startswith("base64:"))


class TestRotationAndScaleFields(QgisTestCase):

    """
    U-2 (build tracker), 2026-08-19: "rotation" and "scale" are added
    unconditionally by this module - no opt-in flag, unlike echelon/
    headquarters/sector1/sector2 above - so every test here builds a
    plain layer with no extra kwargs.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _build(self):

        return build_single_domain_point_layer(
            "Test Layer",
            "ground_unit",
            _ENTITY_LABELS,
            "infantry",
        )


    def test_both_fields_present(self):

        layer = self._build()

        field_names = [field.name() for field in layer.fields()]

        self.assertIn("rotation", field_names)
        self.assertIn("scale", field_names)


    def test_both_use_a_range_spin_box_widget(self):

        layer = self._build()

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

        layer = self._build()

        rotation_idx = layer.fields().indexOf("rotation")
        scale_idx = layer.fields().indexOf("scale")

        self.assertEqual(
            layer.defaultValueDefinition(rotation_idx).expression(), "0"
        )
        self.assertEqual(
            layer.defaultValueDefinition(scale_idx).expression(), "100"
        )


    def _size_and_angle(self, layer, rotation, scale):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("affiliation", "friend")
        feature.setAttribute("entity", "infantry")
        feature.setAttribute("status", "present")

        if rotation is not None:
            feature.setAttribute("rotation", rotation)

        if scale is not None:
            feature.setAttribute("scale", scale)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        properties = layer.renderer().symbol().symbolLayer(
            0
        ).dataDefinedProperties()

        size, size_ok = properties.valueAsDouble(
            QgsSymbolLayer.Property.Size, context, 0.0
        )
        angle, angle_ok = properties.valueAsDouble(
            QgsSymbolLayer.Property.Angle, context, 0.0
        )

        self.assertTrue(size_ok)
        self.assertTrue(angle_ok)

        return size, angle


    def test_rotation_drives_the_angle_property(self):

        layer = self._build()

        _, angle = self._size_and_angle(layer, rotation=135, scale=None)

        self.assertAlmostEqual(angle, 135.0, places=6)


    def test_an_unset_rotation_draws_unrotated(self):

        layer = self._build()

        _, angle = self._size_and_angle(layer, rotation=None, scale=None)

        self.assertAlmostEqual(angle, 0.0, places=6)


    def test_scale_multiplies_the_base_size(self):

        layer = self._build()

        size_100, _ = self._size_and_angle(layer, rotation=None, scale=100)
        size_200, _ = self._size_and_angle(layer, rotation=None, scale=200)

        # Same feature otherwise (same designation, empty), so the
        # designation-compensation ratio inside
        # stabilised_point_size_expression() is identical on both sides
        # and the ratio between the two sizes should be exactly the
        # ratio between the two scale values.
        self.assertAlmostEqual(size_200 / size_100, 2.0, places=6)


    def test_an_unset_scale_draws_at_full_size(self):

        layer = self._build()

        size_unset, _ = self._size_and_angle(layer, rotation=None, scale=None)
        size_100, _ = self._size_and_angle(layer, rotation=None, scale=100)

        self.assertAlmostEqual(size_unset, size_100, places=6)


class TestValueMapWithNone(QgisTestCase):

    def test_prepends_a_none_entry_mapped_to_empty_string(self):

        result = _value_map_with_none({"low_earth_orbit": "Low Earth Orbit (LEO)"})

        self.assertEqual(result["(None)"], "")
        self.assertEqual(result["Low Earth Orbit (LEO)"], "low_earth_orbit")


class TestDefaultInsertPosition(QgisTestCase):

    def test_lands_at_top_of_tree(self):

        QgsProject.instance().setCrs(WGS84)

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        layer = build_single_domain_point_layer(
            "Test Layer", "ground_unit", _ENTITY_LABELS, "infantry"
        )

        default_insert_position(QgsProject.instance(), layer)

        root = QgsProject.instance().layerTreeRoot()

        self.assertEqual(root.children()[0].name(), "Test Layer")


    def test_inserts_collapsed(self):

        # 2026-08-18, UI request: adding a whole domain (Land, one
        # click) inserts several of these layers at once, and each
        # was previously left expanded in the Layers panel by default.
        QgsProject.instance().setCrs(WGS84)

        layer = build_single_domain_point_layer(
            "Test Layer", "ground_unit", _ENTITY_LABELS, "infantry"
        )

        default_insert_position(QgsProject.instance(), layer)

        root = QgsProject.instance().layerTreeRoot()

        node = root.findLayer(layer.id())

        self.assertFalse(node.isExpanded())
