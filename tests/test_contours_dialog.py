# -*- coding: utf-8 -*-

"""
Tests for terrain/contours_dialog.py - the accept-flow logic split
out of show_contours_dialog() so it can be exercised without driving
an actual modal QDialog, plus the dialog's own defaults.

The interval default is the point of this dialog: asking for 20 m
contours on a 1:1,000,000 sheet should be a deliberate choice rather
than an accident.

Military Cartography Tools
"""

import os

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
)

from .qgis_test_case import (
    build_synthetic_cone_dem,
    FakeIface,
    make_canvas,
    QgisTestCase,
)

from MilitaryCartographyTools.terrain.contours import (
    DEFAULT_COLOUR,
    DEFAULT_INTERVAL,
    OUTPUT_LAYER_NAME,
)
from MilitaryCartographyTools.terrain.contours_dialog import (
    ContoursDialog,
    generate_from_dialog_values,
)


class _ContoursDialogTestCase(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        self._dem_path = build_synthetic_cone_dem(
            width=80,
            height=80,
            pixel_size=0.00035
        )

        self.dem_layer = QgsRasterLayer(self._dem_path, "test_dem")

        QgsProject.instance().addMapLayer(self.dem_layer)

        self.iface = FakeIface(canvas=make_canvas())


    def tearDown(self):

        try:
            os.remove(self._dem_path)
        except OSError:
            pass

        super().tearDown()


    def _values(self, **overrides):

        values = {
            "dem_layer": self.dem_layer,
            "extent": self.dem_layer.extent(),
            "extent_crs": self.dem_layer.crs(),
            "interval": 50.0,
            "index_every": 5,
            "colour": DEFAULT_COLOUR,
            "add_as_new_layer": False,
        }

        values.update(overrides)

        return values


class TestDialogDefaults(_ContoursDialogTestCase):

    def test_without_a_canvas_it_opens_at_the_plain_default(self):

        """
        The tests build this without a canvas, and so would any
        caller with no map to reason from. There is no scale to
        derive an interval from, so it must not guess.
        """

        dialog = ContoursDialog()

        self.assertEqual(dialog.interval_spin.value(), DEFAULT_INTERVAL)
        self.assertEqual(dialog.scale_label.text(), "")


    def test_with_a_canvas_it_opens_at_the_interval_for_that_scale(self):

        canvas = make_canvas()
        canvas.setExtent(QgsRectangle(0, 0, 1, 1))

        dialog = ContoursDialog(canvas=canvas)

        self.assertGreater(dialog.interval_spin.value(), 0)
        self.assertIn("would normally use", dialog.scale_label.text())


    def test_the_from_scale_button_re_derives_after_a_zoom(self):

        canvas = make_canvas()
        canvas.setExtent(QgsRectangle(0, 0, 1, 1))

        dialog = ContoursDialog(canvas=canvas)

        dialog.interval_spin.setValue(999.0)

        dialog.apply_suggested_interval()

        self.assertNotEqual(dialog.interval_spin.value(), 999.0)


    def test_the_extent_defaults_to_the_selected_dems_own(self):

        dialog = ContoursDialog()

        dialog.dem_combo.setLayer(self.dem_layer)

        self.assertEqual(
            dialog.extent_group.outputExtent().toString(3),
            self.dem_layer.extent().toString(3)
        )


    def test_choosing_a_different_dem_resets_the_extent(self):

        other_path = build_synthetic_cone_dem(width=20, height=20)

        try:

            other = QgsRasterLayer(other_path, "other_dem")

            QgsProject.instance().addMapLayer(other)

            dialog = ContoursDialog()

            dialog.dem_combo.setLayer(self.dem_layer)
            dialog.dem_combo.setLayer(other)

            self.assertEqual(
                dialog.extent_group.outputExtent().toString(3),
                other.extent().toString(3)
            )

        finally:

            try:
                os.remove(other_path)
            except OSError:
                pass


    def test_values_carries_everything_the_generator_needs(self):

        dialog = ContoursDialog()

        dialog.dem_combo.setLayer(self.dem_layer)

        values = dialog.values()

        self.assertEqual(
            set(values),
            {
                "dem_layer",
                "extent",
                "extent_crs",
                "interval",
                "index_every",
                "colour",
                "add_as_new_layer",
            }
        )

        self.assertEqual(values["colour"], DEFAULT_COLOUR)


class TestGenerateFromDialogValues(_ContoursDialogTestCase):

    def test_no_dem_layer_warns_and_returns_none(self):

        result = generate_from_dialog_values(
            self.iface,
            self._values(dem_layer=None)
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_it_generates_a_named_layer_into_the_project(self):

        layer = generate_from_dialog_values(
            self.iface,
            self._values()
        )

        self.assertIsNotNone(layer)
        self.assertEqual(layer.name(), OUTPUT_LAYER_NAME)
        self.assertGreater(layer.featureCount(), 0)

        self.assertIn(
            layer.id(),
            QgsProject.instance().mapLayers()
        )


    def test_rerunning_replaces_rather_than_piling_layers_up(self):

        first = generate_from_dialog_values(self.iface, self._values())
        second = generate_from_dialog_values(self.iface, self._values())

        self.assertIsNotNone(first)
        self.assertIsNotNone(second)

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)),
            1
        )


    def test_the_checkbox_keeps_the_previous_layer_alongside(self):

        generate_from_dialog_values(self.iface, self._values())

        generate_from_dialog_values(
            self.iface,
            self._values(add_as_new_layer=True)
        )

        self.assertEqual(
            len(QgsProject.instance().mapLayersByName(OUTPUT_LAYER_NAME)),
            2
        )


    def test_a_narrowed_extent_produces_less_than_the_whole_dem(self):

        full = generate_from_dialog_values(
            self.iface,
            self._values(add_as_new_layer=True)
        )

        extent = self.dem_layer.extent()

        quarter = QgsRectangle(
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMinimum() + extent.width() / 2.0,
            extent.yMinimum() + extent.height() / 2.0
        )

        narrowed = generate_from_dialog_values(
            self.iface,
            self._values(
                extent=quarter,
                extent_crs=self.dem_layer.crs(),
                add_as_new_layer=True
            )
        )

        self.assertGreater(full.featureCount(), 0)
        self.assertLess(narrowed.featureCount(), full.featureCount())


    def test_omitting_the_extent_falls_back_to_the_whole_dem(self):

        values = self._values(add_as_new_layer=True)

        del values["extent"]
        del values["extent_crs"]

        without = generate_from_dialog_values(self.iface, values)

        with_extent = generate_from_dialog_values(
            self.iface,
            self._values(add_as_new_layer=True)
        )

        self.assertEqual(
            without.featureCount(),
            with_extent.featureCount()
        )


    def test_the_chosen_colour_reaches_the_drawn_layer(self):

        layer = generate_from_dialog_values(
            self.iface,
            self._values(colour="#112233")
        )

        rules = layer.renderer().rootRule().children()

        self.assertEqual(rules[0].symbol().color().name(), "#112233")
