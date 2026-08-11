# -*- coding: utf-8 -*-

"""
Tests for military_symbology/control_measure_points.py - the "Tactical
Graphics - Control Measure Points" point layer: MIL-STD-2525D Appendix
H's own point-type control measures (checkpoints, decision points,
supply points, and similar), rendered through the same milsymbol.js
pipeline as unit_layer.py.

Military Cartography Tools
"""

import re

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
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology import control_measure_points
from MilitaryCartographyTools.military_symbology.airspace_control_measures import (
    POINT_ENTITY_LABELS as _AIRSPACE_POINT_ENTITY_LABELS,
)
from MilitaryCartographyTools.military_symbology.c2_measures import (
    POINT_ENTITY_LABELS as _C2_POINT_ENTITY_LABELS,
)
from MilitaryCartographyTools.military_symbology.defensive_control_measures import (
    POINT_ENTITY_LABELS as _DEFENSIVE_POINT_ENTITY_LABELS,
)
from MilitaryCartographyTools.military_symbology.offensive_control_measures import (
    POINT_ENTITY_LABELS as _OFFENSIVE_POINT_ENTITY_LABELS,
)
from MilitaryCartographyTools.military_symbology.sidc import (
    AFFILIATIONS,
    build_sidc,
    ENTITIES,
    STATUS,
)
from MilitaryCartographyTools.military_symbology.symbol_engine import (
    render_symbol_svg,
)
from MilitaryCartographyTools.military_symbology.control_measure_points import (
    OUTPUT_LAYER_NAME,
    add_control_measure_points_layer,
    create_control_measure_points_layer,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


class TestVocabularyLabelsMatchSidc(QgisTestCase):

    """
    Regression guard: control_measure_points.py's own display-label
    dicts are kept separate from sidc.py's vocabulary (same
    presentation-vs-data-model split as unit_layer.py) - asserting the
    key sets match exactly turns a silently-missing dropdown entry into
    a loud test failure instead.
    """

    def test_affiliation_labels_cover_every_sidc_affiliation(self):

        self.assertEqual(
            set(control_measure_points._AFFILIATION_LABELS),
            set(AFFILIATIONS)
        )


    def test_status_labels_cover_every_sidc_status(self):

        self.assertEqual(
            set(control_measure_points._STATUS_LABELS),
            set(STATUS)
        )


    def test_entity_labels_cover_every_control_measure_entity(self):

        # Not a full match against ENTITIES["control_measure"] on its
        # own any more: Table H-VI (Command and control points), Table
        # H-IX (Observation Post family), Table H-XI's own Point of
        # Departure (all 2026-08-10) and Table H-XIII's own 26-entry
        # airspace family (2026-08-12) have all moved out to their own
        # dedicated Points layers - see control_measure_points.py's own
        # _ENTITY_LABELS comment for why. The real invariant this
        # guards is that every control_measure entity is offered by SOME
        # dropdown, not necessarily this one - as more H.5.x groups get
        # their own dedicated Points layer, their own entity sets join
        # this union too.
        self.assertEqual(
            set(control_measure_points._ENTITY_LABELS)
            | set(_AIRSPACE_POINT_ENTITY_LABELS)
            | set(_C2_POINT_ENTITY_LABELS)
            | set(_DEFENSIVE_POINT_ENTITY_LABELS)
            | set(_OFFENSIVE_POINT_ENTITY_LABELS),
            set(ENTITIES["control_measure"])
        )


class TestCreateControlMeasurePointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_has_the_expected_fields(self):

        layer = create_control_measure_points_layer()

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


    def test_uses_the_projects_own_crs(self):

        layer = create_control_measure_points_layer()

        self.assertEqual(layer.crs().authid(), WGS84.authid())


    def test_dropdown_fields_use_value_map_widgets(self):

        # Unlike unit_layer.py's "Entity" field, this layer's "Entity"
        # IS a plain ValueMap - there's only one symbol set here, so
        # there's nothing to cascade against (see module docstring).
        layer = create_control_measure_points_layer()

        for field_name in ("affiliation", "entity", "status"):

            idx = layer.fields().indexOf(field_name)

            self.assertEqual(
                layer.editorWidgetSetup(idx).type(),
                "ValueMap"
            )


    def test_renderers_svg_layer_has_a_data_defined_name(self):

        layer = create_control_measure_points_layer()

        symbol = layer.renderer().symbol()
        svg_layer = symbol.symbolLayer(0)

        self.assertTrue(
            svg_layer.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.Name
            )
        )


    def test_a_real_feature_resolves_to_a_valid_symbol_path(self):

        # Integration-level, same shape as unit_layer.py's own
        # equivalent test: a real feature run through the actual
        # renderer resolves to a valid base64: SVG path.
        layer = create_control_measure_points_layer()

        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
        feature.setAttribute("affiliation", "hostile")
        feature.setAttribute("entity", "checkpoint")
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

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name,
            expr_context,
            ""
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))


class TestControlMeasurePointColouring(QgisTestCase):

    """
    Confirms, through the real milsymbol.js rendering pipeline (not a
    mock), that this symbol set's own colouring already matches
    MIL-STD-2525D Appendix H.5.3 (friendly/neutral/unknown -> black,
    hostile -> red) with no extra code on our side - see
    control_measure_points.py's own module docstring for how this was
    first confirmed live. This test is the permanent regression guard
    for that finding.
    """

    def setUp(self):

        super().setUp()

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _stroke_colours(self, affiliation):

        sidc = build_sidc(
            affiliation=affiliation,
            entity="checkpoint",
            symbol_set="control_measure"
        )

        svg = render_symbol_svg(sidc, {"size": 35})

        return set(re.findall(r'stroke="([^"]+)"', svg))


    def test_friend_neutral_unknown_render_black(self):

        for affiliation in ("friend", "neutral", "unknown"):

            self.assertIn(
                "black",
                self._stroke_colours(affiliation),
                affiliation
            )


    def test_hostile_renders_red(self):

        self.assertIn(
            "rgb(255, 0, 0)",
            self._stroke_colours("hostile")
        )


class TestAddControlMeasurePointsLayer(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def test_creates_and_adds_the_layer(self):

        layer = add_control_measure_points_layer(self.iface)

        self.assertIsNotNone(layer)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)


    def test_does_nothing_and_warns_if_one_already_exists(self):

        first = add_control_measure_points_layer(self.iface)

        result = add_control_measure_points_layer(self.iface)

        self.assertIsNone(result)

        matching = QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)

        self.assertEqual(len(matching), 1)

        self.assertEqual(matching[0].id(), first.id())

        self.assertEqual(
            len(self.iface.messageBar().calls),
            1
        )


    def test_default_insert_position_lands_at_top_of_tree(self):

        from qgis.core import QgsVectorLayer

        dummy = QgsVectorLayer("Point?crs=EPSG:4326", "dummy_below", "memory")
        QgsProject.instance().addMapLayer(dummy)

        add_control_measure_points_layer(self.iface)

        root = QgsProject.instance().layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(names[0], OUTPUT_LAYER_NAME)
