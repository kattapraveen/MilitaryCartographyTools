# -*- coding: utf-8 -*-

"""
Tests for military_symbology/mines_and_obstacles_lines_layer_nonnato.py
- the "Mines and Obstacles Lines (Non-NATO)" layer, the branch's only
LINE layer and its only symbol built from QGIS primitives rather than
from an SVG.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsMarkerLineSymbolLayer,
    QgsPointXY,
    QgsProject,
    QgsSimpleLineSymbolLayer,
    QgsSymbolLayer,
    QgsWkbTypes,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.military_symbology.mines_and_obstacles_lines_layer_nonnato import (
    ENTITY_LABELS,
    TRENCH_SYSTEM_ENTITY,
    LAYER_NAME,
    add_mines_and_obstacles_lines_layer_nonnato,
    build_mines_and_obstacles_lines_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.nonnato_symbol_engine import (
    MINE_GREEN,
    MINE_TYPE_ANTIPERSONNEL,
    MINE_TYPE_ANTITANK,
    MINE_TYPE_BOTH,
    MINE_TYPE_NONE,
    MINEFIELD_GENERAL_ENTITY,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


def _sub_symbol_expressions(symbol):

    """
    Every data-defined expression on a symbol and on its sub-symbols.

    The rampart's own colour is set on the SUB-symbol's marker, not on
    the marker-line layer that carries it - the same place a
    QgsLinePatternFillSymbolLayer hides its colour, and for the same
    reason: what paints is the sub-symbol.
    """

    found = []

    for index in range(symbol.symbolLayerCount()):

        layer = symbol.symbolLayer(index)

        for key in layer.dataDefinedProperties().propertyKeys():

            found.append(
                layer.dataDefinedProperties().property(key).expressionString()
            )

        sub = layer.subSymbol()

        if sub is not None:
            found.extend(_sub_symbol_expressions(sub))

    return found


def _symbol_for(layer, entity):

    """
    That entity's own rule's symbol. The layer rendered through a
    single symbol while Minefield (General) was alone on it; since
    Trench System joined, each entity has a rule of its own.
    """

    for rule in layer.renderer().rootRule().children():

        if f"'{entity}'" in rule.filterExpression():
            return rule.symbol()

    raise AssertionError(f"no rule for {entity}")


class TestBuildMinesAndObstaclesLinesLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_it_is_a_line_layer(self):

        # The whole reason it is a layer of its own: a QGIS vector layer
        # carries one geometry type, and its point sibling is points.
        layer = build_mines_and_obstacles_lines_layer_nonnato()

        self.assertEqual(
            layer.geometryType(), QgsWkbTypes.GeometryType.LineGeometry
        )


    def test_it_offers_minefield_general_and_trench_system(self):

        # Trench System joined 2026-09-25 - the one symbol on the
        # branch taken from the NATO side unchanged.
        self.assertEqual(
            list(ENTITY_LABELS),
            [MINEFIELD_GENERAL_ENTITY, TRENCH_SYSTEM_ENTITY],
        )


    def test_every_field_exists(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        # `affiliation` arrived with Trench System, which is coloured
        # like the NATO symbol it is rather than obstacle green.
        self.assertEqual(
            [field.name() for field in layer.fields()],
            ["entity", "mine_type", "affiliation"],
        )


    def test_the_mine_type_dropdown_offers_all_four(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        setup = layer.editorWidgetSetup(layer.fields().indexOf("mine_type"))

        self.assertEqual(setup.type(), "ValueMap")
        self.assertEqual(
            set(setup.config()["map"]),
            {"None", "Antitank", "Antipersonnel", "Both (alternating)"},
        )


    def test_the_symbol_is_two_parallel_lines_plus_a_run_per_mine_type(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        symbol = _symbol_for(layer, MINEFIELD_GENERAL_ENTITY)

        kinds = [
            type(symbol.symbolLayer(index))
            for index in range(symbol.symbolLayerCount())
        ]

        self.assertEqual(kinds.count(QgsSimpleLineSymbolLayer), 2)
        self.assertEqual(kinds.count(QgsMarkerLineSymbolLayer), 2)


    def test_the_two_lines_sit_either_side_of_the_digitised_one(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        symbol = _symbol_for(layer, MINEFIELD_GENERAL_ENTITY)

        offsets = sorted(
            symbol.symbolLayer(index).offset()
            for index in range(symbol.symbolLayerCount())
            if isinstance(symbol.symbolLayer(index), QgsSimpleLineSymbolLayer)
        )

        self.assertEqual(len(offsets), 2)
        self.assertAlmostEqual(offsets[0], -offsets[1])
        self.assertGreater(offsets[1], 0)


    def _run_placements(self, layer, mine_type):

        """
        Each run's own (interval, offset along the line) as actually
        evaluated for a feature of this mine_type - both are
        data-defined, so the plain values on the layer say nothing
        about what gets drawn.
        """

        feature = QgsFeature(layer.fields())
        feature.setGeometry(
            QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(1, 0)])
        )
        feature.setAttribute("entity", MINEFIELD_GENERAL_ENTITY)
        feature.setAttribute("mine_type", mine_type)

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        context.setFeature(feature)

        symbol = _symbol_for(layer, MINEFIELD_GENERAL_ENTITY)

        placements = []

        for index in range(symbol.symbolLayerCount()):

            run = symbol.symbolLayer(index)

            if not isinstance(run, QgsMarkerLineSymbolLayer):
                continue

            values = []

            for prop in (
                QgsSymbolLayer.Property.Interval,
                QgsSymbolLayer.Property.OffsetAlongLine,
            ):

                value, ok = run.dataDefinedProperties().valueAsDouble(
                    prop, context, -1.0
                )

                self.assertTrue(ok, f"{prop} expression failed to evaluate")

                values.append(value)

            placements.append(tuple(values))

        return placements


    def test_the_two_runs_interleave_rather_than_coincide(self):

        # "populate the mines as per selection", alternating when both
        # types are chosen - which works by offsetting one run half an
        # interval along the line.
        layer = build_mines_and_obstacles_lines_layer_nonnato()

        placements = self._run_placements(layer, MINE_TYPE_BOTH)

        intervals = {interval for interval, _ in placements}

        self.assertEqual(len(intervals), 1)

        alongs = sorted(along for _, along in placements)

        self.assertAlmostEqual(alongs[0], 0.0)
        self.assertAlmostEqual(alongs[1], intervals.pop() / 2)


    def test_the_gap_between_mines_is_the_same_on_every_setting(self):

        # "the gap between the mines - when selected single is more as
        # compared to alternating where they are much closer - can't we
        # have a consistent gap?" (2026-09-12). Two interleaved runs at
        # one run's own interval halve what the reader sees, so under
        # "both" each run's interval doubles. What matters is the gap
        # between one drawn mine and the next, whichever run drew it:
        # one run's interval when a single type is selected, half of
        # the (doubled) interval when both are.
        layer = build_mines_and_obstacles_lines_layer_nonnato()

        spacings = {}

        for mine_type in (
            MINE_TYPE_ANTITANK, MINE_TYPE_ANTIPERSONNEL, MINE_TYPE_BOTH
        ):

            placements = self._run_placements(layer, mine_type)

            intervals = {interval for interval, _ in placements}

            self.assertEqual(
                len(intervals), 1, "the two runs must share one interval"
            )

            interval = intervals.pop()

            spacings[mine_type] = (
                interval / 2 if mine_type == MINE_TYPE_BOTH else interval
            )

        self.assertEqual(len(set(spacings.values())), 1, spacings)

        # A run on its own starts at the line's own beginning - no
        # leading gap left for a run that is not drawn.
        for mine_type in (MINE_TYPE_ANTITANK, MINE_TYPE_ANTIPERSONNEL):

            with self.subTest(mine_type=mine_type):

                self.assertEqual(
                    {along for _, along in self._run_placements(
                        layer, mine_type
                    )},
                    {0.0}
                )


    def _run_sizes(self, layer, mine_type):

        feature = QgsFeature(layer.fields())
        feature.setGeometry(
            QgsGeometry.fromPolylineXY([QgsPointXY(0, 0), QgsPointXY(1, 0)])
        )
        feature.setAttribute("entity", MINEFIELD_GENERAL_ENTITY)
        feature.setAttribute("mine_type", mine_type)

        context = QgsExpressionContext()
        context.appendScope(QgsExpressionContextUtils.layerScope(layer))
        context.setFeature(feature)

        symbol = _symbol_for(layer, MINEFIELD_GENERAL_ENTITY)

        sizes = []

        for index in range(symbol.symbolLayerCount()):

            run = symbol.symbolLayer(index)

            if not isinstance(run, QgsMarkerLineSymbolLayer):
                continue

            marker = run.subSymbol().symbolLayer(0)

            value, ok = marker.dataDefinedProperties().valueAsDouble(
                QgsSymbolLayer.Property.Size, context, 0.0
            )

            self.assertTrue(ok, "size expression failed to evaluate")

            sizes.append(value)

        return sizes


    def test_each_run_is_drawn_only_when_its_own_type_is_selected(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        antipersonnel, antitank = self._run_sizes(
            layer, MINE_TYPE_ANTIPERSONNEL
        )

        self.assertGreater(antipersonnel, 0)
        self.assertEqual(antitank, 0)

        antipersonnel, antitank = self._run_sizes(layer, MINE_TYPE_ANTITANK)

        self.assertEqual(antipersonnel, 0)
        self.assertGreater(antitank, 0)


    def test_both_draws_both_runs_and_none_draws_neither(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        self.assertTrue(all(s > 0 for s in self._run_sizes(layer, MINE_TYPE_BOTH)))
        self.assertTrue(all(s == 0 for s in self._run_sizes(layer, MINE_TYPE_NONE)))


    def test_a_null_mine_type_draws_no_mines_rather_than_blanking(self):

        # coalesce() in the expression - a feature whose dropdown has
        # never been touched must still render its two lines.
        layer = build_mines_and_obstacles_lines_layer_nonnato()

        self.assertTrue(all(s == 0 for s in self._run_sizes(layer, None)))


    def test_everything_is_mine_green(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        symbol = _symbol_for(layer, MINEFIELD_GENERAL_ENTITY)

        for index in range(symbol.symbolLayerCount()):

            layer_at = symbol.symbolLayer(index)

            if isinstance(layer_at, QgsSimpleLineSymbolLayer):
                self.assertEqual(layer_at.color().name(), MINE_GREEN)
            else:
                self.assertEqual(
                    layer_at.subSymbol().symbolLayer(0).strokeColor().name(),
                    MINE_GREEN,
                )


class TestAddMinesAndObstaclesLinesLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        self.iface = FakeIface()


    def test_it_adds_a_layer_with_the_expected_name(self):

        layer = add_mines_and_obstacles_lines_layer_nonnato(self.iface)

        self.assertIsNotNone(layer)
        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(LAYER_NAME)), 1
        )


    def test_it_guards_against_a_duplicate(self):

        add_mines_and_obstacles_lines_layer_nonnato(self.iface)

        self.assertIsNone(
            add_mines_and_obstacles_lines_layer_nonnato(self.iface)
        )


class TestTrenchSystem(QgisTestCase):

    """
    "Use the Fortified Line of NATO symbology for it, no change"
    (2026-09-24), confirmed 2026-09-25. The one symbol on this branch
    that is a NATO symbol taken whole.
    """

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)


    def test_it_is_the_nato_fortified_line_itself(self):

        from MilitaryCartographyTools.military_symbology.field_fortification import (
            fortified_line_symbol,
        )

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        ours = _symbol_for(layer, TRENCH_SYSTEM_ENTITY)
        theirs = fortified_line_symbol()

        self.assertEqual(ours.symbolLayerCount(), theirs.symbolLayerCount())

        for index in range(theirs.symbolLayerCount()):

            with self.subTest(layer=index):

                self.assertEqual(
                    type(ours.symbolLayer(index)),
                    type(theirs.symbolLayer(index)),
                )
                self.assertEqual(
                    ours.symbolLayer(index).properties(),
                    theirs.symbolLayer(index).properties(),
                )


    def test_it_is_affiliation_coloured_not_obstacle_green(self):

        # H.5.22.1 makes none of the exception H.5.21.1 makes for
        # obstacles - see field_fortification's own docstring.
        layer = build_mines_and_obstacles_lines_layer_nonnato()

        expressions = _sub_symbol_expressions(
            _symbol_for(layer, TRENCH_SYSTEM_ENTITY)
        )

        self.assertTrue(expressions)
        self.assertTrue(any("affiliation" in e for e in expressions))
        self.assertFalse(any(MINE_GREEN in e for e in expressions))


    def test_the_affiliation_dropdown_is_the_lines_and_areas_one(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        setup = layer.editorWidgetSetup(
            layer.fields().indexOf("affiliation")
        )

        self.assertEqual(setup.type(), "ValueMap")

        # Five values, not the four SIDC identities: this one only
        # ever picks a Qt colour.
        self.assertEqual(len(setup.config()["map"]), 5)


    def test_minefield_general_is_still_green_and_unaffiliated(self):

        layer = build_mines_and_obstacles_lines_layer_nonnato()

        expressions = _sub_symbol_expressions(
            _symbol_for(layer, MINEFIELD_GENERAL_ENTITY)
        )

        self.assertFalse(any("affiliation" in e for e in expressions))
