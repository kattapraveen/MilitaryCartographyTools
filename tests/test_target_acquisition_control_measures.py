# -*- coding: utf-8 -*-

"""
Tests for military_symbology/target_acquisition_control_measures.py -
the Target Acquisition Control Measures Areas layer (Table H-XVIII,
Mini-Phase H13/H14), styled via a QgsRuleBasedRenderer keyed on
"measure_type". See that module's own docstring for what's skipped
(nothing now - both Weapon/Sensor Range Fan variants were built
2026-08-14 and are covered by TestRangeFans at the foot of this file).

Military Cartography Tools
"""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsPointXY,
    QgsProject,
    QgsSymbolLayer,
    QgsVectorLayer,
)
from qgis.PyQt.QtGui import QColor

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions

from MilitaryCartographyTools.expressions.military_symbology_functions import (
    _distance_area,
)
from MilitaryCartographyTools.military_symbology.target_acquisition_control_measures import (
    RANGE_FANS_LAYER_NAME,
    RANGE_FAN_MAX_RINGS,
    add_range_fans_layer,
    create_range_fans_layer,
    AREAS_LAYER_NAME,
    AREA_MEASURE_TYPE_LABELS,
    add_target_acquisition_control_measures_areas_layer,
    create_target_acquisition_control_measures_areas_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


def _rule_symbol_for(layer, measure_type):

    root = layer.renderer().rootRule()

    rule = next(
        rule for rule in root.children()
        if rule.filterExpression() == f'"measure_type" = \'{measure_type}\''
    )

    return rule.symbol()


def _resolve_stroke_color(symbol_layer, layer, affiliation):

    feature = QgsFeature(layer.fields())
    feature.setAttribute("affiliation", affiliation)

    context = layer.createExpressionContext()
    context.setFeature(feature)

    color, ok = symbol_layer.dataDefinedProperties().valueAsColor(
        QgsSymbolLayer.Property.StrokeColor,
        context,
        QColor(1, 2, 3)
    )

    return color, ok


class TestCreateTargetAcquisitionControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def _evaluate_label(self, layer, measure_type, **attrs):

        feature = QgsFeature(layer.fields())
        feature.setAttribute("measure_type", measure_type)

        for key, value in attrs.items():

            feature.setAttribute(key, value)

        settings = layer.labeling().settings()

        expression = QgsExpression(settings.fieldName)
        context = layer.createExpressionContext()
        context.setFeature(feature)

        result = expression.evaluate(context)
        self.assertFalse(expression.hasEvalError(), expression.evalErrorString())
        return result


    def test_has_the_expected_fields(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        field_names = [field.name() for field in layer.fields()]

        self.assertEqual(
            field_names,
            [
                "measure_type", "affiliation", "status",
                "unique_designation", "area_km2", "perimeter_km",
            ]
        )


    def test_is_a_polygon_layer(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        self.assertEqual(
            layer.geometryType().name,
            "Polygon"
        )


    def test_covers_every_measure_type_the_table_lists(self):

        # Was a bare `len(...) == 11` count until 2026-08-12, which is
        # exactly the check that let Terminally Guided Munition
        # Footprint (242000) go missing: it was never added, so the
        # count agreed with itself and stayed green. Pinned against the
        # standard's OWN code list now, so an absent measure type fails
        # by name rather than passing quietly.
        #
        # Codes are given as the table gives them - most entries are an
        # Irregular/Rectangle/Circular TRIPLE folded into one measure
        # type here, TGMF is a lone code, and the two Kill Boxes share
        # one 2423xx run between them. That mixture is very likely why a
        # pass reading the table in triples skipped the one entry that
        # isn't one.
        self.assertEqual(
            set(AREA_MEASURE_TYPE_LABELS),
            {
                "ati",            # 241101/102/103
                "cffz",           # 241201/202/203
                "censor_zone",    # 241301/302/303
                "cfz",            # 241401/402/403
                "dead_space_area",  # 241501/502/503
                "sensor_zone",    # 241601/602/603
                "tba",            # 241701/702/703
                "tvar",           # 241801/802/803
                "zor",            # 241901/902/903
                "tgmf",           # 242000 - single code, no triple
                "blue_kill_box",  # 242301/302/303
                "purple_kill_box",  # 242304/305/306
            }
        )

        # Weapon/Sensor Range Fan (242100 Circular, 242200 Sector) are
        # deliberately still absent - genuinely computed geometry from
        # one anchor point, not a digitized boundary. Tracked to build
        # rather than curated out.
        self.assertNotIn("weapon_sensor_range_fan_circular", AREA_MEASURE_TYPE_LABELS)
        self.assertNotIn("weapon_sensor_range_fan_sector", AREA_MEASURE_TYPE_LABELS)


    def test_terminally_guided_munition_footprint_labels_tgmf(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        self.assertEqual(self._evaluate_label(layer, "tgmf"), "TGMF")

        self.assertEqual(
            self._evaluate_label(
                layer, "tgmf", unique_designation="alpha"
            ),
            "TGMF\nALPHA"
        )


    def test_rule_tree_has_one_rule_per_measure_type(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        root = layer.renderer().rootRule()

        filters = {rule.filterExpression() for rule in root.children()}

        self.assertEqual(
            filters,
            {
                f'"measure_type" = \'{measure_type}\''
                for measure_type in AREA_MEASURE_TYPE_LABELS
            }
        )


    def test_labels_prefix_the_type_abbreviation(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        cases = {
            "ati": ("ATI", "mnd(n)", "ATI\nMND(N)"),
            "cffz": ("CFF ZONE", "3bde 4id", "CFF ZONE\n3BDE 4ID"),
            "censor_zone": ("CENSOR ZONE", "school", "CENSOR ZONE\nSCHOOL"),
            "cfz": ("CF ZONE", "green", "CF ZONE\nGREEN"),
            "dead_space_area": ("DA", "1/7 fa", "DA\n1/7 FA"),
            "sensor_zone": ("SENSOR ZONE", "q37", "SENSOR ZONE\nQ37"),
            "tba": ("TBA", "tank", "TBA\nTANK"),
            "tvar": ("TVAR", "scud", "TVAR\nSCUD"),
            "zor": ("ZOR", "3bde 4id", "ZOR\n3BDE 4ID"),
            "blue_kill_box": ("BKB", "x corps", "BKB\nX CORPS"),
            "purple_kill_box": ("PKB", "x corps", "PKB\nX CORPS"),
        }

        for measure_type, (prefix, name, expected) in cases.items():

            with self.subTest(measure_type=measure_type):

                self.assertEqual(
                    self._evaluate_label(
                        layer, measure_type, unique_designation=name
                    ),
                    expected
                )

                self.assertEqual(
                    self._evaluate_label(layer, measure_type),
                    prefix
                )


    def test_every_area_is_a_plain_unfilled_outline(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            with self.subTest(measure_type=measure_type):

                symbol = _rule_symbol_for(layer, measure_type)

                self.assertEqual(symbol.symbolLayerCount(), 1)


    def test_area_outline_colours_follow_affiliation_per_ms_std_2525d_h_5_1_1_1(self):

        layer = create_target_acquisition_control_measures_areas_layer()

        expected = {
            "friend": "#0000ff",
            "hostile": "#ff0000",
            "neutral": "#00ff00",
            "unknown": "#ffff00",
            "unspecified": "#000000",
        }

        for measure_type in AREA_MEASURE_TYPE_LABELS:

            symbol = _rule_symbol_for(layer, measure_type)
            outline_layer = symbol.symbolLayer(0)

            for affiliation, hex_color in expected.items():

                with self.subTest(measure_type=measure_type, affiliation=affiliation):

                    color, ok = _resolve_stroke_color(outline_layer, layer, affiliation)

                    self.assertTrue(ok)
                    self.assertEqual(color.name(), hex_color)


    def test_area_and_perimeter_default_values_recalculate_on_update(self):

        military_symbology_functions.register()

        try:

            layer = create_target_acquisition_control_measures_areas_layer()

            self.assertTrue(
                layer.defaultValueDefinition(
                    layer.fields().indexOf("area_km2")
                ).applyOnUpdate()
            )

            self.assertTrue(
                layer.defaultValueDefinition(
                    layer.fields().indexOf("perimeter_km")
                ).applyOnUpdate()
            )

        finally:

            military_symbology_functions.unregister()


class TestAddTargetAcquisitionControlMeasuresAreasLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_areas_layer_is_created_and_added(self):

        layer = add_target_acquisition_control_measures_areas_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_areas_layer_is_never_replaced_if_it_already_exists(self):

        first = add_target_acquisition_control_measures_areas_layer(self.iface)

        result = add_target_acquisition_control_measures_areas_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(AREAS_LAYER_NAME)

        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].id(), first.id())


    def test_default_insert_position_lands_at_top_of_tree(self):

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_target_acquisition_control_measures_areas_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], AREAS_LAYER_NAME)


class TestRangeFans(QgisTestCase):

    """
    Weapon/Sensor Range Fans - 242100 (Circular) and 242200 (Sector),
    built 2026-08-14 to the maintainer's own dictated construction.

    **Two codes, one symbol.** Circular is Sector with the 0/360
    default, so nothing here distinguishes them but the numbers typed.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _ring(self, left, right, range_m, wkt="Point(0 0)"):

        return QgsExpression(
            "mct_range_fan_ring(geom_from_wkt('{}'), {}, {}, {})".format(
                wkt, left, right, range_m
            )
        ).evaluate()


    def test_the_default_angles_draw_a_closed_circle(self):

        # 0/360 is the default every ring starts at, and it is also
        # what makes this symbol the Circular code.
        ring = self._ring(0, 360, 5000).asPolyline()

        self.assertGreater(len(ring), 100)

        # Closed, and never returning to the centre - a circle has no
        # radial sides.
        self.assertAlmostEqual(ring[0].x(), ring[-1].x(), places=6)
        self.assertAlmostEqual(ring[0].y(), ring[-1].y(), places=6)

        for point in ring:
            self.assertGreater(abs(point.y()) + abs(point.x()), 0.001)


    def test_a_sector_closes_back_to_the_centre(self):

        # "connect the arc end to pt1 using line segments" - without
        # them a sector is a floating arc.
        ring = self._ring(30, 120, 5000).asPolyline()

        centre = QgsPointXY(0, 0)

        self.assertAlmostEqual(ring[0].x(), centre.x(), places=9)
        self.assertAlmostEqual(ring[0].y(), centre.y(), places=9)
        self.assertAlmostEqual(ring[-1].x(), centre.x(), places=9)
        self.assertAlmostEqual(ring[-1].y(), centre.y(), places=9)


    def test_angles_are_compass_bearings_from_north(self):

        # "the centerline is always north". A sector from 0 to 90 must
        # occupy the NORTH-EAST quadrant - x and y both positive - which
        # is the opposite of a maths convention measuring anticlockwise
        # from east.
        ring = self._ring(0, 90, 5000).asPolyline()

        arc = ring[1:-1]

        for point in arc:

            self.assertGreaterEqual(point.x(), -1e-9)
            self.assertGreaterEqual(point.y(), -1e-9)


    def test_a_sector_may_cross_north(self):

        # 300 to 60 is a 120-degree sector straddling north, not a
        # 240-degree one going the other way round.
        wide = self._ring(300, 60, 5000).asPolyline()
        narrow = self._ring(0, 120, 5000).asPolyline()

        self.assertEqual(len(wide), len(narrow))


    def test_the_range_is_a_real_ground_distance(self):

        # Unlike every glyph in this appendix, which is millimetres on
        # the page. A ring of 10 km must measure 10 km on the ellipsoid,
        # not 10 km of coordinate.
        ring = self._ring(0, 360, 10000).asPolyline()

        measured = _distance_area().measureLine(
            QgsPointXY(0, 0), ring[0]
        )

        self.assertAlmostEqual(measured, 10000.0, delta=1.0)


    def test_a_ring_with_no_range_draws_nothing(self):

        # Which is how one symbol carrying five ring layers draws only
        # the rings actually filled in.
        for range_m in (0, -100):

            with self.subTest(range_m=range_m):

                self.assertTrue(self._ring(0, 360, range_m).isEmpty())

        # An UNFILLED ring is a different path and worth pinning
        # separately: QGIS short-circuits a whole function call to NULL
        # the moment any argument is NULL, so the function never runs
        # at all. A NULL geometry generator draws nothing either, so
        # the outcome matches - but it is QGIS's doing, not this
        # function's, and a guard here would be dead code.
        self.assertIsNone(self._ring(0, 360, "NULL"))


    def test_the_layer_has_four_fields_per_ring_and_five_rings(self):

        layer = create_range_fans_layer()

        names = [field.name() for field in layer.fields()]

        for ring in range(1, RANGE_FAN_MAX_RINGS + 1):

            for suffix in ("left", "right", "range", "alt"):

                self.assertIn(f"ring{ring}_{suffix}", names)

        self.assertNotIn("ring6_range", names)

        # Every ring starts as a full circle.
        for ring in range(1, RANGE_FAN_MAX_RINGS + 1):

            self.assertEqual(
                layer.defaultValueDefinition(
                    layer.fields().indexOf(f"ring{ring}_left")
                ).expression(),
                "0"
            )

            self.assertEqual(
                layer.defaultValueDefinition(
                    layer.fields().indexOf(f"ring{ring}_right")
                ).expression(),
                "360"
            )


    def test_one_symbol_layer_and_one_label_rule_per_ring(self):

        layer = create_range_fans_layer()

        # Five rings plus the north axis.
        self.assertEqual(
            layer.renderer().symbol().symbolLayerCount(),
            RANGE_FAN_MAX_RINGS + 1
        )

        # QGIS places one label per RULE, and five rings want five.
        self.assertEqual(
            len(layer.labeling().rootRule().children()),
            RANGE_FAN_MAX_RINGS
        )


    def test_each_rings_label_is_rg_over_alt(self):

        layer = create_range_fans_layer()

        settings = layer.labeling().rootRule().children()[0].settings()

        expression = QgsExpression(settings.fieldName)

        feature = QgsFeature(layer.fields())
        feature.setAttribute("ring1_range", 5000)
        feature.setAttribute("ring1_alt", "300")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        self.assertEqual(expression.evaluate(context), "RG 5000\nALT 300")

        # No altitude, no second line - rather than a bare "ALT".
        feature.setAttribute("ring1_alt", None)
        context.setFeature(feature)

        self.assertEqual(expression.evaluate(context), "RG 5000")


    def test_an_outer_rings_sides_stop_at_the_inner_rings_range(self):

        # The first build ran every ring's sides to the centre, so the
        # outer rings drew straight through the inner ones. Reported
        # against the standard's own picture, where each ring's sides
        # span only its own band.
        ring = QgsExpression(
            "mct_range_fan_ring(geom_from_wkt('Point(0 0)'), "
            "290, 30, 2500, 1500)"
        ).evaluate().asPolyline()

        centre = QgsPointXY(0, 0)

        for end in (ring[0], ring[-1]):

            self.assertAlmostEqual(
                _distance_area().measureLine(centre, end),
                1500.0,
                delta=1.0
            )

        # ...and only ring 1, whose inner range is 0, reaches the vertex.
        first = QgsExpression(
            "mct_range_fan_ring(geom_from_wkt('Point(0 0)'), "
            "290, 30, 1500, 0)"
        ).evaluate().asPolyline()

        self.assertAlmostEqual(first[0].x(), 0.0, places=9)
        self.assertAlmostEqual(first[0].y(), 0.0, places=9)


    def test_a_full_circle_has_no_sides_to_restrict(self):

        ring = QgsExpression(
            "mct_range_fan_ring(geom_from_wkt('Point(0 0)'), "
            "0, 360, 4000, 2000)"
        ).evaluate().asPolyline()

        centre = QgsPointXY(0, 0)

        for point in ring:

            self.assertAlmostEqual(
                _distance_area().measureLine(centre, point),
                4000.0,
                delta=1.0
            )


    def test_the_axis_runs_north_past_the_outermost_ring(self):

        axis = QgsExpression(
            "mct_range_fan_axis(geom_from_wkt('Point(0 0)'), 5250)"
        ).evaluate().asPolyline()

        self.assertEqual(len(axis), 2)

        self.assertAlmostEqual(axis[0].x(), 0.0, places=9)

        # Due north, and the overshoot clear of the 5000 m arc.
        self.assertAlmostEqual(axis[1].x(), 0.0, places=6)
        self.assertGreater(axis[1].y(), 0.0)

        self.assertAlmostEqual(
            _distance_area().measureLine(QgsPointXY(0, 0), axis[1]),
            5250.0,
            delta=1.0
        )


    def test_the_symbol_carries_an_axis_beyond_its_five_rings(self):

        layer = create_range_fans_layer()

        symbol = layer.renderer().symbol()

        self.assertEqual(
            symbol.symbolLayerCount(), RANGE_FAN_MAX_RINGS + 1
        )

        axis = symbol.symbolLayer(RANGE_FAN_MAX_RINGS)

        expression = axis.geometryExpression()

        self.assertIn("mct_range_fan_axis(", expression)

        # Sized off the LARGEST ring, plus the overshoot.
        self.assertIn("array_max(", expression)
        self.assertIn("250", expression)


    def test_the_altitude_is_upper_cased_per_h_5_4(self):

        # Reported from the smoke test: a lower-case "gl" stayed lower
        # case, against the appendix's own all-caps rule.
        layer = create_range_fans_layer()

        settings = layer.labeling().rootRule().children()[0].settings()

        feature = QgsFeature(layer.fields())
        feature.setAttribute("ring1_range", 1500)
        feature.setAttribute("ring1_alt", "gl")

        context = layer.createExpressionContext()
        context.setFeature(feature)

        self.assertEqual(
            QgsExpression(settings.fieldName).evaluate(context),
            "RG 1500\nALT GL"
        )


    def test_adding_the_layer_inserts_exactly_one(self):

        self.assertIsNotNone(add_range_fans_layer(self.iface))

        self.assertIsNone(add_range_fans_layer(self.iface))

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(
                RANGE_FANS_LAYER_NAME
            )),
            1
        )
