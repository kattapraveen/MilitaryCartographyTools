# -*- coding: utf-8 -*-

"""
Cross-layer guard for one specific defect class: a Points layer whose
`affiliation` dropdown offers, or defaults to, a value that
build_sidc() will reject.

Why this lives in its own module rather than in each layer's own tests:
the bug it guards against is not about any one table. Every
milsymbol-rendered Points layer feeds its `affiliation` field into
build_sidc(), where SIDC digit 4 has only the four real standard
identities - but the affiliation vocabulary shared across this appendix
(_control_measure_shared.AFFILIATION_LABELS) deliberately carries a
FIFTH value, "unspecified", for the hand-drawn lines and areas layers,
where affiliation only ever picks a Qt colour. The two vocabularies
look interchangeable and are not.

That mismatch shipped twice:

- H-XIX's own Points layer (2026-08-12) used the lines/areas configure
  helper outright, so it also inherited its default, "unspecified".
  Every point placed on it rendered as milsymbol's unknown icon. Caught
  by the maintainer's live smoke test, not by the suite.
- Airspace, Maritime and Target Points each built their dropdown as
  `dict(AFFILIATION_LABELS)`. Their defaults were 'friend', so they
  worked as shipped - but the attribute form offered one menu entry
  that silently broke the symbol if chosen. Found while fixing the
  first, fixed on the maintainer's instruction.

The failure is invisible to the obvious assertion. mct_build_sidc()
returns its KeyError MESSAGE as a plain string; mct_sidc_svg() hands
that to milsymbol; milsymbol falls back to its unknown icon; and the
result is still a perfectly well-formed `base64:` path. So these tests
decode the payload and look for the unknown icon's own path, and drive
each layer's OWN configured defaults rather than restating them.

Military Cartography Tools
"""

import base64

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsProject,
    QgsSymbolLayer,
)

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology._control_measure_shared import (
    AFFILIATION_LABELS,
    DEFAULT_POINT_AFFILIATION,
    POINT_AFFILIATION_LABELS,
)
from MilitaryCartographyTools.military_symbology.sidc import AFFILIATIONS

from MilitaryCartographyTools.military_symbology import (
    airspace_control_measures,
    c2_measures,
    cbrn_defense,
    mission_task_control_measures,
    defensive_control_measures,
    field_fortification,
    maritime_control_measures,
    obstacle_control_measures,
    offensive_control_measures,
    supply_points,
    sustainment_control_measures,
    target_control_measures,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")


# milsymbol's unknown-icon fallback is an inverted "?" - a stable
# fragment of the path it draws for it, present iff the SIDC it was
# handed did not resolve.
_MILSYMBOL_UNKNOWN_ICON_MARK = "94.8206,78.1372"


# Every layer in this plugin whose `affiliation` field reaches
# build_sidc(). Add a row here when a new Points layer is built - which
# is the point: a new layer that reuses the wrong vocabulary fails here
# rather than at a maintainer's smoke test.
_POINT_LAYER_FACTORIES = (
    (
        "airspace",
        airspace_control_measures.create_airspace_control_measures_points_layer,
    ),
    (
        "c2",
        c2_measures.create_c2_measures_points_layer,
    ),
    (
        "cbrn",
        cbrn_defense.create_cbrn_defense_points_layer,
    ),
    (
        "mission_task",
        mission_task_control_measures.create_mission_task_points_layer,
    ),
    (
        "defensive",
        defensive_control_measures.create_defensive_control_measures_points_layer,
    ),
    (
        "field_fortification",
        field_fortification.create_field_fortification_points_layer,
    ),
    (
        "maritime",
        maritime_control_measures.create_maritime_control_measures_points_layer,
    ),
    (
        "supply",
        supply_points.create_supply_points_layer,
    ),
    (
        "sustainment",
        sustainment_control_measures.create_sustainment_points_layer,
    ),
    (
        "obstacle",
        obstacle_control_measures.create_obstacle_control_measures_points_layer,
    ),
    (
        "offensive",
        offensive_control_measures.create_offensive_control_measures_points_layer,
    ),
    (
        "target",
        target_control_measures.create_target_control_measures_points_layer,
    ),
)


class TestSharedPointAffiliationVocabulary(QgisTestCase):

    def test_covers_exactly_the_sidc_standard_identities(self):

        # Pins the invariant that POINT_AFFILIATION_LABELS is written
        # out longhand for dropdown-ordering reasons rather than derived
        # from AFFILIATIONS: it must still be exactly AFFILIATIONS'
        # keys, no more (a value build_sidc() rejects) and no fewer (a
        # standard identity added to sidc.py and silently missed here).
        self.assertEqual(
            set(POINT_AFFILIATION_LABELS),
            set(AFFILIATIONS)
        )


    def test_default_is_a_real_standard_identity(self):

        self.assertIn(DEFAULT_POINT_AFFILIATION, AFFILIATIONS)


    def test_is_not_the_lines_and_areas_vocabulary(self):

        # The whole point of the split. If these ever become equal, one
        # of the two is wrong.
        self.assertNotEqual(
            set(POINT_AFFILIATION_LABELS),
            set(AFFILIATION_LABELS)
        )

        self.assertIn("unspecified", AFFILIATION_LABELS)

        self.assertNotIn("unspecified", POINT_AFFILIATION_LABELS)


class TestEveryPointLayerBuildsValidSidcs(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _default_attributes(self, layer):

        context = layer.createExpressionContext()

        values = {}

        for field in layer.fields():

            idx = layer.fields().indexOf(field.name())

            expression = layer.defaultValueDefinition(idx).expression()

            if expression:

                values[field.name()] = QgsExpression(expression).evaluate(context)

        return values


    def _rendered_icon_svg(self, layer, feature):

        # Found, not assumed to be symbolLayer(0): these layers do not
        # all put the milsymbol SVG first. Defensive Control Measures
        # draws a QgsSimpleMarkerSymbolLayer beneath its icon and C2
        # Measures draws one above, so the index differs per layer.
        symbol = layer.renderer().symbol()

        svg_layer = None

        for index in range(symbol.symbolLayerCount()):

            candidate = symbol.symbolLayer(index)

            if candidate.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.Name
            ):
                svg_layer = candidate
                break

        self.assertIsNotNone(
            svg_layer,
            f"{layer.name()} has no data-defined symbol name to evaluate"
        )

        context = layer.createExpressionContext()
        context.setFeature(feature)

        path, ok = svg_layer.dataDefinedProperties().valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)
        self.assertTrue(path.startswith("base64:"))

        return base64.b64decode(path[len("base64:"):]).decode("utf-8")


    def test_every_layers_affiliation_default_is_valid(self):

        for name, factory in _POINT_LAYER_FACTORIES:

            with self.subTest(layer=name):

                layer = factory()

                default = self._default_attributes(layer).get("affiliation")

                self.assertIn(default, AFFILIATIONS)


    def test_every_layers_default_entity_is_one_it_actually_offers(self):

        # The gap this sweep had: it checked that every default RENDERS,
        # which 'shelter' still did long after H17 moved Shelter off the
        # shared Control Measure Points layer into its own - because
        # 'shelter' is still perfectly real vocabulary in sidc.py. What
        # broke was narrower and invisible here: the default was no
        # longer in that layer's own dropdown, so a freshly digitized
        # point landed on an entity the form could not display.
        for name, factory in _POINT_LAYER_FACTORIES:

            with self.subTest(layer=name):

                layer = factory()

                fields = layer.fields()

                index = fields.indexOf("entity")

                if index < 0:
                    continue

                default = self._default_attributes(layer).get("entity")

                setup = layer.editorWidgetSetup(index)

                config = setup.config()

                if setup.type() == "ValueMap":

                    offered = set(config.get("map", {}).values())

                elif setup.type() == "ValueRelation":

                    lookup = QgsProject.instance().mapLayer(
                        config.get("Layer")
                    )

                    self.assertIsNotNone(lookup, name)

                    key = config.get("Key")

                    offered = {
                        feature[key] for feature in lookup.getFeatures()
                    }

                else:

                    self.fail(
                        f"{name}: unexpected entity widget "
                        f"{setup.type()!r}"
                    )

                self.assertIn(default, offered, name)


    def test_no_layer_offers_an_affiliation_build_sidc_rejects(self):

        for name, factory in _POINT_LAYER_FACTORIES:

            layer = factory()

            idx = layer.fields().indexOf("affiliation")

            offered = layer.editorWidgetSetup(idx).config().get("map", {})

            # QGIS carries a ValueMap either as a dict or as a list of
            # single-entry dicts, depending on version - the STORED
            # value is what reaches build_sidc() either way.
            if isinstance(offered, list):
                stored = [v for entry in offered for v in entry.values()]
            else:
                stored = list(offered.values())

            self.assertTrue(stored, f"{name} has no affiliation ValueMap")

            for value in stored:

                with self.subTest(layer=name, affiliation=value):

                    self.assertIn(value, AFFILIATIONS)


    def test_defaults_render_a_real_icon_on_every_layer(self):

        # The exact path a freshly digitized point takes on each layer:
        # touch no dropdown, let every field take its own default.
        for name, factory in _POINT_LAYER_FACTORIES:

            with self.subTest(layer=name):

                layer = factory()

                feature = QgsFeature(layer.fields())

                for field, value in self._default_attributes(layer).items():
                    feature.setAttribute(field, value)

                svg = self._rendered_icon_svg(layer, feature)

                self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg)


    def test_abatis_and_trip_wire_are_not_offered_as_plain_points_anywhere(self):

        # Neither Abatis (280100) nor Trip Wire (290500) is a real
        # milsymbol/2525D entity, so either one fed blindly into
        # mct_build_sidc() renders as the unknown-icon fallback whatever
        # the affiliation. Abatis once sat in the old shared Control
        # Measure Points dropdown as a stopgap so it would not vanish
        # between batches; B4 built its (since-retired) line version and
        # removed it, and this used to assert it had stayed out of
        # every points dropdown rather than drifting back in.
        #
        # **U-4 (2026-08-19) deliberately reversed that** for exactly
        # one layer: the obstacle Points layer now offers both as
        # custom-shape entities (see obstacle_control_measures.py's own
        # _CUSTOM_SHAPE_POINT_LABELS) - handled by that layer's OWN
        # renderer branch, never fed into mct_build_sidc(), so the
        # unknown-icon check below still holds for the generic case.
        # This test's job narrows to "everywhere ELSE, still never" -
        # the exact accidental-drift failure mode it was built to
        # catch, now scoped past the one deliberate exception.
        layer = mission_task_control_measures.create_mission_task_points_layer()

        for entity in ("abatis", "trip_wire"):

            feature = QgsFeature(layer.fields())

            for field, value in self._default_attributes(layer).items():
                feature.setAttribute(field, value)

            feature.setAttribute("entity", entity)

            self.assertIn(
                _MILSYMBOL_UNKNOWN_ICON_MARK,
                self._rendered_icon_svg(layer, feature),
                entity
            )

        for name, factory in _POINT_LAYER_FACTORIES:

            if name == "obstacle":
                continue

            with self.subTest(layer=name):

                offered = factory().editorWidgetSetup(
                    factory().fields().indexOf("entity")
                ).config().get("map", {})

                self.assertNotIn("abatis", set(offered.values()), name)
                self.assertNotIn("trip_wire", set(offered.values()), name)

    def test_every_offered_affiliation_renders_a_real_icon(self):

        # The regression proper: each layer's dropdown is swept against
        # its own default entity, so choosing any menu entry - including
        # the one that used to be "Unspecified (black)" - still resolves
        # to a real symbol.
        for name, factory in _POINT_LAYER_FACTORIES:

            layer = factory()

            defaults = self._default_attributes(layer)

            for affiliation in POINT_AFFILIATION_LABELS:

                with self.subTest(layer=name, affiliation=affiliation):

                    feature = QgsFeature(layer.fields())

                    for field, value in defaults.items():
                        feature.setAttribute(field, value)

                    feature.setAttribute("affiliation", affiliation)

                    # Each layer's own default entity, which
                    # test_abatis_... pins is never the unrenderable one.
                    svg = self._rendered_icon_svg(layer, feature)

                    self.assertNotIn(_MILSYMBOL_UNKNOWN_ICON_MARK, svg)
