# -*- coding: utf-8 -*-

"""
Cross-layer guard for one specific defect class: a Points layer whose
ICON changes size when a unique designation is typed into it.

**QGIS sizes an SVG marker by its WIDTH, and milsymbol widens an
icon's declared bounding box to take in whatever amplifier text it
carries.** So at a fixed marker size, adding a designation makes the
symbol itself SHRINK - which is what the project maintainer reported
on 2026-08-13 ("now the symbol size is reducing when the Field T is
added - inconsistent from a UI point of view").

That was fixed the same day in _point_symbol_layer.py, the shared
point-layer builder. **It shipped broken anyway**, because seven
modules in this appendix build their own point renderer instead of
using that builder, and the fix lived inside it as a private
expression. The maintainer found it again on 2026-08-14, on Table
H-VI's own Checkpoint and Contact Point: "icon size changes in case of
C2 measures points... icon remained same in case of land units and
land eqpt".

So the compensation moved out to
_control_measure_shared.stabilised_point_size_expression(), every
renderer now shares it, and this file is the guard that keeps them
sharing it. It drives each layer's OWN configured defaults and
compares what actually renders, rather than asserting on expression
text - a module could pass a string-level check and still draw wrong.

The layer list is imported from test_point_layer_affiliations rather
than restated, deliberately: a new Points layer added there is covered
by both sweeps at once, and cannot be added to one and missed by the
other.

Military Cartography Tools
"""

import base64
import re

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsExpression,
    QgsFeature,
    QgsProject,
    QgsSymbolLayer,
)

from .qgis_test_case import QgisTestCase

from .test_point_layer_affiliations import _POINT_LAYER_FACTORIES

from MilitaryCartographyTools.expressions import military_symbology_functions
from MilitaryCartographyTools.military_symbology._control_measure_shared import (
    stabilised_point_size_expression,
)


WGS84 = QgsCoordinateReferenceSystem("EPSG:4326")

_VIEWBOX_WIDTH = re.compile(r'viewBox="\S+ \S+ (\S+) \S+"')

# Long enough to widen any icon's box noticeably, and upper-case so
# H.5.4's own all-caps rule doesn't change its width on the way
# through.
_DESIGNATION = "TF EAGLE 42"


class TestStabilisedSizeExpression(QgisTestCase):

    def test_the_plain_width_is_the_sidc_argument_alone(self):

        # The helper pulls mct_build_sidc(...) out of the full call by
        # counting parentheses. A regex stops at the first ')' inside a
        # nested call, which every one of these expressions has.
        stabilised = stabilised_point_size_expression(
            "8.0",
            "mct_sidc_svg(mct_build_sidc(\"affiliation\",\"entity\","
            "'control_measure','unspecified',\"status\",false),"
            "upper(coalesce(\"unique_designation\",'')),'uniqueDesignation')"
        )

        self.assertIn(
            "mct_sidc_svg_width(mct_build_sidc(\"affiliation\",\"entity\","
            "'control_measure','unspecified',\"status\",false))",
            stabilised
        )


    def test_a_null_or_zero_width_falls_back_to_no_compensation(self):

        # QGIS nulls a whole function call on any NULL argument, so one
        # unset attribute would otherwise null the size expression and
        # silently drop a per-entity multiplier back to the base size.
        stabilised = stabilised_point_size_expression(
            "8.0", "mct_sidc_svg(mct_build_sidc('a'), 'b')"
        )

        self.assertIn("coalesce(", stabilised)
        self.assertIn("nullif(", stabilised)


class TestEveryPointLayerHoldsItsIconStill(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(WGS84)

        military_symbology_functions.register()


    def tearDown(self):

        military_symbology_functions.unregister()

        super().tearDown()


    def _svg_layer(self, layer):

        # Found, not assumed to be symbolLayer(0) - these layers do not
        # all put the milsymbol SVG first.
        symbol = layer.renderer().symbol()

        for index in range(symbol.symbolLayerCount()):

            candidate = symbol.symbolLayer(index)

            if candidate.dataDefinedProperties().isActive(
                QgsSymbolLayer.Property.Name
            ):
                return candidate

        return None


    def _feature_with_defaults(self, layer, designation):

        context = layer.createExpressionContext()

        feature = QgsFeature(layer.fields())

        for field in layer.fields():

            index = layer.fields().indexOf(field.name())

            expression = layer.defaultValueDefinition(index).expression()

            if expression:

                feature.setAttribute(
                    field.name(),
                    QgsExpression(expression).evaluate(context)
                )

        feature.setAttribute("unique_designation", designation)

        return feature


    def _drawn_icon_scale(self, layer, svg_layer, designation):

        """
        Millimetres of map per icon unit - the size the ICON itself
        actually renders at, independent of how wide milsymbol declared
        the box to be.
        """

        feature = self._feature_with_defaults(layer, designation)

        context = layer.createExpressionContext()
        context.setFeature(feature)

        properties = svg_layer.dataDefinedProperties()

        size, ok = properties.valueAsDouble(
            QgsSymbolLayer.Property.Size, context, svg_layer.size()
        )

        self.assertTrue(ok)

        path, ok = properties.valueAsString(
            QgsSymbolLayer.Property.Name, context, ""
        )

        self.assertTrue(ok)

        svg = base64.b64decode(path[len("base64:"):]).decode("utf-8")

        return size / float(_VIEWBOX_WIDTH.search(svg).group(1))


    def test_a_designation_does_not_resize_the_icon(self):

        for name, factory in _POINT_LAYER_FACTORIES:

            with self.subTest(layer=name):

                layer = factory()

                if "unique_designation" not in [
                    field.name() for field in layer.fields()
                ]:
                    continue

                svg_layer = self._svg_layer(layer)

                self.assertIsNotNone(svg_layer, name)

                plain = self._drawn_icon_scale(layer, svg_layer, "")

                amplified = self._drawn_icon_scale(
                    layer, svg_layer, _DESIGNATION
                )

                self.assertAlmostEqual(plain, amplified, places=9, msg=name)


    def test_the_designation_really_does_widen_the_declared_box(self):

        # Guards the guard: if a layer's default entity happened to
        # ignore the designation entirely, the test above would pass
        # for the wrong reason - there would be nothing to compensate
        # for. Not every layer's DEFAULT entity widens (some icons put
        # their text inside the frame, some ignore the slot), so this
        # asserts a floor plus the one layer the defect was actually
        # reported on.
        widened = []

        for name, factory in _POINT_LAYER_FACTORIES:

            layer = factory()

            if "unique_designation" not in [
                field.name() for field in layer.fields()
            ]:
                continue

            svg_layer = self._svg_layer(layer)

            properties = svg_layer.dataDefinedProperties()

            widths = []

            for designation in ("", _DESIGNATION):

                feature = self._feature_with_defaults(layer, designation)

                context = layer.createExpressionContext()
                context.setFeature(feature)

                path, _ok = properties.valueAsString(
                    QgsSymbolLayer.Property.Name, context, ""
                )

                svg = base64.b64decode(
                    path[len("base64:"):]
                ).decode("utf-8")

                widths.append(float(_VIEWBOX_WIDTH.search(svg).group(1)))

            if widths[1] > widths[0]:
                widened.append(name)

        self.assertIn("c2", widened)

        self.assertGreaterEqual(len(widened), 5, widened)
