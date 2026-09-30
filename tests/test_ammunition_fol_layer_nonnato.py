# -*- coding: utf-8 -*-

"""
Tests for military_symbology/ammunition_fol_layer_nonnato.py - the
"Ammunition and FOL (Non-NATO)" layer, added 2026-09-18. It shares Land
Unit's builder the way Aviation does; these pin that, and the three
entities' glyphs.

Military Cartography Tools
"""

import base64
import re

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpressionContext,
    QgsExpressionContextUtils,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsSymbolLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.expressions import nonnato_symbology_functions
from MilitaryCartographyTools.military_symbology.ammunition_fol_layer_nonnato import (
    ENTITY_LABELS,
    LAYER_NAME,
    add_ammunition_fol_layer_nonnato,
    build_ammunition_fol_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology.land_unit_layer_nonnato import (
    ENTITY_LABELS as LAND_UNIT_ENTITY_LABELS,
    build_land_unit_layer_nonnato,
)
from MilitaryCartographyTools.military_symbology import (
    nonnato_symbol_engine as nse,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

_FRAME_D = "M25,50 l150,0 0,100 -150,0 z"


_GLYPH_PATTERN = re.compile(
    r'<path transform="translate\(([-\d.]+),([-\d.]+)\) scale\(([\d.]+)\)" '
    r'd="([^"]+)" stroke-width="([\d.]+)"'
)


def _glyphs(svg):

    """(d, (translate x, y), scale, stroke width) for every glyph inside the circle."""

    return [
        (d, (float(x), float(y)), float(scale), float(width))
        for x, y, scale, d, width in _GLYPH_PATTERN.findall(svg)
    ]


def _glyph_ds(svg):

    return [glyph[0] for glyph in _glyphs(svg)]


def _placed_centre(glyph, own_centre):

    _, (x, y), scale, _ = glyph

    return (x + scale * own_centre[0], y + scale * own_centre[1])


class TestAmmunitionEntityList(QgisTestCase):

    def test_the_agreed_entities(self):

        # "add Ammunition to the title otherwise user may get confused
        # with FOL".
        self.assertEqual(
            ENTITY_LABELS,
            {
                nse.AMMUNITION_ALL_TYPES_ENTITY: "Ammunition (All Types)",
                nse.AMMUNITION_AIR_FORCE_ENTITY: "Ammunition (Air Force)",
                nse.AMMUNITION_ARMOUR_ENTITY: "Ammunition (Armour)",
                nse.AMMUNITION_ARTILLERY_ENTITY: "Ammunition (Artillery)",
                nse.AMMUNITION_ROCKET_MISSILE_ENTITY: "Ammunition (Rocket or Missile)",
                nse.AMMUNITION_SMALL_ARMS_ENTITY: "Ammunition (Small Arms)",
                nse.FOL_AVIATION_ENTITY: "Aviation FOL",
                nse.FOL_NON_AVIATION_ENTITY: "Non-Aviation FOL",
                nse.WATER_ENTITY: "Water",
                nse.CHEMICALS_ENTITY: "Chemicals",
            },
        )
        self.assertEqual(set(ENTITY_LABELS), set(nse.AMMUNITION_FOL_ENTITIES))


    def test_nothing_is_offered_on_land_unit_too(self):

        self.assertEqual(set(ENTITY_LABELS) & set(LAND_UNIT_ENTITY_LABELS), set())


class TestAmmunitionGlyphs(QgisTestCase):

    def test_the_glyphs_are_milsymbols_own(self):

        # Copied as constants; a milsymbol update that moves one must
        # fail here rather than drift.
        self.assertIn(
            f'd="{nse._AMMUNITION_GLYPH_D}"',
            nse.render_nonnato_unit_svg("friend", "ammunition"),
        )
        self.assertIn(
            f'd="{nse._ARMOUR_OVAL_D}"',
            nse.render_nonnato_unit_svg("friend", "armor_mechanized"),
        )
        self.assertIn(
            f'd="{nse._ARMY_AVIATION_PROPELLER_SOLID_D}"',
            nse.render_nonnato_unit_svg("friend", "aviation_fixed_wing"),
        )


    def test_all_types_is_the_logistics_circle_with_the_ammunition_glyph(self):

        svg = nse.render_nonnato_unit_svg("friend", nse.AMMUNITION_ALL_TYPES_ENTITY)

        # "the circle of same diameter as the height of the standard
        # rectangle" - no rectangle, a circle 100 across on its centre.
        self.assertNotIn(_FRAME_D, svg)
        self.assertIn('<circle cx="100" cy="100" r="50"', svg)
        self.assertNotIn(">MP<", svg)
        self.assertEqual(_glyph_ds(svg), [nse._AMMUNITION_GLYPH_D])


    def test_air_force_adds_the_propeller_hollow(self):

        svg = nse.render_nonnato_unit_svg("friend", nse.AMMUNITION_AIR_FORCE_ENTITY)

        self.assertEqual(
            _glyph_ds(svg),
            [nse._AMMUNITION_GLYPH_D, nse._ARMY_AVIATION_PROPELLER_SOLID_D],
        )
        self.assertNotIn('fill="#3060c0"', svg)


    def test_armour_adds_the_oval(self):

        svg = nse.render_nonnato_unit_svg("friend", nse.AMMUNITION_ARMOUR_ENTITY)

        self.assertEqual(
            _glyph_ds(svg), [nse._AMMUNITION_GLYPH_D, nse._ARMOUR_OVAL_D]
        )


    def test_the_sizes_asked_for(self):

        # "increase the size of the main glyph ... by 40%; reduce the
        # size of propeller by 50%; reduce the size of the oval to match
        # the propeller size", then both 15% larger (2026-09-18).
        air_force = _glyphs(nse.render_nonnato_unit_svg(
            "friend", nse.AMMUNITION_AIR_FORCE_ENTITY
        ))
        armour = _glyphs(nse.render_nonnato_unit_svg(
            "friend", nse.AMMUNITION_ARMOUR_ENTITY
        ))

        self.assertEqual(air_force[0][2], 1.4)

        # Half, then 15% larger: "increase the size of propeller and
        # oval by 15%".
        self.assertAlmostEqual(air_force[1][2], 0.5 * 1.15, places=6)
        self.assertAlmostEqual(
            nse._ARMOUR_OVAL_WIDTH * armour[1][2],
            nse._PROPELLER_WIDTH * air_force[1][2],
            places=3,
        )


    def test_everything_is_centred_on_the_ammunition_glyph(self):

        # The glyph grows about its own centre, so that centre does not
        # move; the propeller and the oval sit on it.
        air_force = _glyphs(nse.render_nonnato_unit_svg(
            "friend", nse.AMMUNITION_AIR_FORCE_ENTITY
        ))
        armour = _glyphs(nse.render_nonnato_unit_svg(
            "friend", nse.AMMUNITION_ARMOUR_ENTITY
        ))

        centre = nse._AMMUNITION_GLYPH_CENTRE

        for placed in (
            _placed_centre(air_force[0], nse._AMMUNITION_GLYPH_CENTRE),
            _placed_centre(air_force[1], nse._PROPELLER_CENTRE),
            _placed_centre(armour[1], nse._ARMOUR_OVAL_CENTRE),
        ):
            self.assertAlmostEqual(placed[0], centre[0], places=3)
            self.assertAlmostEqual(placed[1], centre[1], places=3)


    def test_every_glyph_keeps_the_same_line_weight(self):

        # Stroke width divided by the scale, so each draws at 3.9 once
        # its transform and the final stroke scale are applied.
        for entity in nse.AMMUNITION_ENTITIES:
            for d, _, scale, width in _glyphs(
                nse.render_nonnato_unit_svg("friend", entity)
            ):
                with self.subTest(entity=entity, d=d):
                    self.assertAlmostEqual(width * scale, 3.9, places=3)


    def test_every_glyph_takes_the_affiliation_colour(self):

        for affiliation, colour in nse.AFFILIATION_COLOURS.items():
            for entity in nse.AMMUNITION_FOL_ENTITIES:

                with self.subTest(affiliation=affiliation, entity=entity):

                    svg = nse.render_nonnato_unit_svg(affiliation, entity)

                    self.assertEqual(
                        set(re.findall(r'stroke="([^"]+)"', svg)) - {"none"},
                        {colour},
                    )


    def test_the_unit_amplifiers_still_apply(self):

        for entity in nse.AMMUNITION_FOL_ENTITIES:

            with self.subTest(entity=entity):

                self.assertIn(
                    "stroke-dasharray",
                    nse.render_nonnato_unit_svg("friend", entity, status="planned"),
                )
                self.assertIn(
                    "A1",
                    nse.render_nonnato_unit_svg(
                        "friend", entity, designation_left="a1"
                    ),
                )


    def test_there_is_no_echelon_headquarters_or_combined_arms(self):

        # "Ammunition and FOL do not need echelons", then "headquarters
        # and combined arms also not required" - and nothing else moves
        # either, since milsymbol never draws them to make room for. The
        # FOL half of the layer follows the same rule.
        for entity in nse.AMMUNITION_FOL_ENTITIES:

            plain = nse.render_nonnato_unit_svg("friend", entity)

            for options in (
                {"echelon": "team_crew"}, {"echelon": "squad"},
                {"echelon": "company"}, {"echelon": "brigade"},
                {"echelon": "army_group"}, {"headquarters": True},
                {"combined_arms": True},
                {"echelon": "battalion", "headquarters": True, "combined_arms": True},
            ):
                with self.subTest(entity=entity, **options):

                    self.assertEqual(
                        nse.render_nonnato_unit_svg("friend", entity, **options),
                        plain,
                    )


    def test_the_ammunition_marks_sit_inside_the_glyph(self):

        # Artillery's dot on the glyph's centre; Rocket or Missile's line
        # and Small Arms' X "in the middle of the center glyph", the line
        # "not touching the top or the bottom of the glyph".
        centre_x, centre_y = nse._AMMUNITION_GLYPH_CENTRE

        artillery = nse.render_nonnato_unit_svg("friend", nse.AMMUNITION_ARTILLERY_ENTITY)
        # Half Artillery's own r=15: "reduce the artillery dot by 50%".
        self.assertIn(
            f'<circle cx="{centre_x:g}" cy="{centre_y:g}" r="7.5"', artillery
        )
        self.assertIn('fill="#3060c0"></circle>', artillery)

        rocket = nse.render_nonnato_unit_svg("friend", nse.AMMUNITION_ROCKET_MISSILE_ENTITY)
        top, bottom = (
            float(value) for value in re.search(
                r'<path d="M100,([\d.]+) L100,([\d.]+)"', rocket
            ).groups()
        )
        self.assertGreater(top, nse._AMMUNITION_INNER_TOP + 3.9 / 2)
        self.assertLess(bottom, nse._AMMUNITION_INNER_BOTTOM - 3.9 / 2)
        self.assertAlmostEqual((top + bottom) / 2, centre_y, places=3)

        small_arms = nse.render_nonnato_unit_svg("friend", nse.AMMUNITION_SMALL_ARMS_ENTITY)
        half = nse._SMALL_ARMS_X_HALF
        self.assertIn(
            f'd="M{centre_x - half:g},{centre_y - half:g} '
            f'L{centre_x + half:g},{centre_y + half:g} '
            f'M{centre_x + half:g},{centre_y - half:g} '
            f'L{centre_x - half:g},{centre_y + half:g}"',
            small_arms,
        )
        # Clear of the legs, ink to ink.
        self.assertLess(
            half + 3.9 / 2 / 2 ** 0.5 + 3.9 / 2, nse._AMMUNITION_INNER_HALF_WIDTH
        )


class TestFol(QgisTestCase):

    CIRCLE_INNER_INK = 50 - 5.2 / 2


    def _ink_reach(self, x, y):

        return ((x - 100) ** 2 + (y - 100) ** 2) ** 0.5 + 3.9 / 2


    def test_aviation_fol_triangle_and_stem_clear_the_circle(self):

        # "the triangle and line dont touch the circle".
        half = nse._FOL_TRIANGLE_HALF_BASE
        top = nse._FOL_TRIANGLE_TOP

        for x, y in ((100 - half, top), (100 + half, top), (100, nse._FOL_STEM_BOTTOM)):
            with self.subTest(point=(x, y)):
                self.assertLess(self._ink_reach(x, y), self.CIRCLE_INNER_INK)

        svg = nse.render_nonnato_unit_svg("friend", nse.FOL_AVIATION_ENTITY)

        self.assertIn(
            f'<path d="M100,{nse._FOL_TRIANGLE_APEX_Y:g} L100,{nse._FOL_STEM_BOTTOM:g}"',
            svg,
        )


    def test_aviation_fol_propeller_is_as_wide_as_the_triangles_base(self):

        svg = nse.render_nonnato_unit_svg("friend", nse.FOL_AVIATION_ENTITY)

        scale = float(re.search(
            r'scale\(([\d.]+)\)" d="' + re.escape(nse._ARMY_AVIATION_PROPELLER_SOLID_D),
            svg,
        ).group(1))

        self.assertAlmostEqual(
            nse._PROPELLER_WIDTH * scale, 2 * nse._FOL_TRIANGLE_HALF_BASE, places=3
        )


    def test_aviation_fol_propeller_is_centred_on_the_stem(self):

        # "shift the propeller to vertically center align with the
        # vertical line only".
        svg = nse.render_nonnato_unit_svg("friend", nse.FOL_AVIATION_ENTITY)

        x, y, scale = (float(value) for value in re.search(
            r'translate\(([-\d.]+),([-\d.]+)\) scale\(([\d.]+)\)" d="'
            + re.escape(nse._ARMY_AVIATION_PROPELLER_SOLID_D),
            svg,
        ).groups())

        self.assertAlmostEqual(x + scale * 100, 100, places=3)
        self.assertAlmostEqual(
            y + scale * 100,
            (nse._FOL_TRIANGLE_APEX_Y + nse._FOL_STEM_BOTTOM) / 2,
            places=3,
        )


    def test_non_aviation_fol_keeps_the_triangle_and_adds_a_solid_one_tip_to_tip(self):

        aviation = nse.render_nonnato_unit_svg("friend", nse.FOL_AVIATION_ENTITY)
        svg = nse.render_nonnato_unit_svg("friend", nse.FOL_NON_AVIATION_ENTITY)

        triangle = re.search(r'<path d="(M\d+,68 [^"]+)"', aviation).group(1)

        self.assertIn(f'd="{triangle}"', svg)
        self.assertNotIn(nse._ARMY_AVIATION_PROPELLER_SOLID_D, svg)
        self.assertNotIn(f"L100,{nse._FOL_STEM_BOTTOM:g}", svg)

        # Right side up, 60% of the original, its tip on the original's.
        solid = re.search(
            r'<path d="M100,([\d.]+) L([\d.]+),([\d.]+) L([\d.]+),([\d.]+) Z"[^>]*fill="#3060c0"',
            svg,
        )
        tip, right, base, left, _ = (float(value) for value in solid.groups())

        self.assertAlmostEqual(tip, nse._FOL_TRIANGLE_APEX_Y, places=3)
        self.assertAlmostEqual(right - left, 0.6 * 2 * nse._FOL_TRIANGLE_HALF_BASE, places=3)
        self.assertAlmostEqual(base - tip, 0.6 * nse._FOL_TRIANGLE_HEIGHT, places=3)
        self.assertGreater(base, tip)


    def test_water_and_chemicals_are_lettered_circles(self):

        for entity, letter in ((nse.WATER_ENTITY, "W"), (nse.CHEMICALS_ENTITY, "C")):

            with self.subTest(entity=entity):

                svg = nse.render_nonnato_unit_svg("friend", entity)

                self.assertIn('<circle cx="100" cy="100" r="50"', svg)
                self.assertIn(f">{letter}</text>", svg)
                self.assertNotIn(">MP<", svg)
                self.assertNotIn(_FRAME_D, svg)


class TestAmmunitionLayerMatchesLandUnit(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_the_fields_are_identical(self):

        self.assertEqual(
            [(f.name(), f.type()) for f in build_ammunition_fol_layer_nonnato().fields()],
            [(f.name(), f.type()) for f in build_land_unit_layer_nonnato().fields()],
        )


    def test_the_entity_dropdown_lists_this_layers_own_entities(self):

        layer = build_ammunition_fol_layer_nonnato()

        setup = layer.editorWidgetSetup(layer.fields().indexOf("entity"))

        self.assertEqual(set(setup.config()["map"]), set(ENTITY_LABELS.values()))


    def test_every_entity_renders_through_the_real_expression(self):

        layer = build_ammunition_fol_layer_nonnato()

        for entity in ENTITY_LABELS:

            with self.subTest(entity=entity):

                feature = QgsFeature(layer.fields())
                feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(0, 0)))
                feature.setAttribute("affiliation", "friend")
                feature.setAttribute("entity", entity)

                context = QgsExpressionContext()
                context.appendScope(QgsExpressionContextUtils.layerScope(layer))
                context.setFeature(feature)

                path, ok = layer.renderer().symbol().symbolLayer(
                    0
                ).dataDefinedProperties().valueAsString(
                    QgsSymbolLayer.Property.Name, context, ""
                )

                self.assertTrue(ok, "expression failed to evaluate")

                svg = base64.b64decode(path[len("base64:"):]).decode("utf-8")

                self.assertEqual(
                    svg, nse.render_nonnato_unit_svg("friend", entity)
                )


class TestAddAmmunitionFolLayerNonnato(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        nonnato_symbology_functions.register()

        self.iface = FakeIface()


    def tearDown(self):

        nonnato_symbology_functions.unregister()

        super().tearDown()


    def test_adds_the_layer_once(self):

        first = add_ammunition_fol_layer_nonnato(self.iface)

        self.assertIsNotNone(first)
        self.assertIsNone(add_ammunition_fol_layer_nonnato(self.iface))
        self.assertEqual(len(QgsProject.instance().mapLayersByName(LAYER_NAME)), 1)
