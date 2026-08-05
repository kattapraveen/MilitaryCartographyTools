# -*- coding: utf-8 -*-

"""
Tests for waypoints/gpx_kml_dialog.py's import_from_dialog_values()/
export_from_dialog_values() - the accept-flow logic split out of
show_import_waypoints_dialog()/show_export_waypoints_dialog() so it's
testable without driving an actual modal QDialog, mirroring the rest
of this plugin's dialog test modules (e.g.
tests/test_hypsometric_tint_dialog.py).

Military Cartography Tools
"""

import os
import tempfile

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)

from .qgis_test_case import FakeIface, QgisTestCase

from MilitaryCartographyTools.waypoints.gpx_kml_dialog import (
    export_from_dialog_values,
    import_from_dialog_values,
)
from MilitaryCartographyTools.waypoints.gpx_kml_io import export_waypoints


class _TempFileTestCase(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

        self.iface = FakeIface()

        self._temp_dir = tempfile.mkdtemp()


    def tearDown(self):

        for entry in os.listdir(self._temp_dir):

            try:
                os.remove(os.path.join(self._temp_dir, entry))
            except OSError:
                pass

        try:
            os.rmdir(self._temp_dir)
        except OSError:
            pass


    def _path(self, filename):

        return os.path.join(self._temp_dir, filename)


class TestImportFromDialogValues(_TempFileTestCase):

    def test_no_file_path_warns_and_returns_none(self):

        result = import_from_dialog_values(
            self.iface,
            {"file_path": ""}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_unreadable_file_warns_and_returns_none(self):

        result = import_from_dialog_values(
            self.iface,
            {"file_path": self._path("does_not_exist.gpx")}
        )

        self.assertIsNone(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_valid_file_is_added_to_the_project_named_after_the_file(self):

        source = QgsVectorLayer("Point?crs=EPSG:4326", "source", "memory")

        feature = QgsFeature(source.fields())

        feature.setGeometry(
            QgsGeometry.fromPointXY(QgsPointXY(39.2083, -6.7924))
        )

        source.dataProvider().addFeature(feature)

        path = self._path("my_waypoints.gpx")

        export_waypoints(source, path, "GPX")

        result = import_from_dialog_values(
            self.iface,
            {"file_path": path}
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.name(), "my_waypoints")

        self.assertIsNotNone(
            QgsProject.instance().mapLayer(result.id())
        )


class TestExportFromDialogValues(_TempFileTestCase):

    def _source_layer(self):

        layer = QgsVectorLayer("Point?crs=EPSG:4326", "source", "memory")

        feature = QgsFeature(layer.fields())

        feature.setGeometry(
            QgsGeometry.fromPointXY(QgsPointXY(39.2083, -6.7924))
        )

        layer.dataProvider().addFeature(feature)

        return layer


    def test_no_source_layer_warns_and_returns_false(self):

        result = export_from_dialog_values(
            self.iface,
            {
                "source_layer": None,
                "file_format": "GPX",
                "file_path": self._path("out.gpx"),
            }
        )

        self.assertFalse(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_no_file_path_warns_and_returns_false(self):

        result = export_from_dialog_values(
            self.iface,
            {
                "source_layer": self._source_layer(),
                "file_format": "GPX",
                "file_path": "",
            }
        )

        self.assertFalse(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)


    def test_successful_export_pushes_info_and_returns_true(self):

        path = self._path("out.gpx")

        result = export_from_dialog_values(
            self.iface,
            {
                "source_layer": self._source_layer(),
                "file_format": "GPX",
                "file_path": path,
            }
        )

        self.assertTrue(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)
        self.assertTrue(os.path.exists(path))


    def test_failed_export_warns_and_returns_false(self):

        result = export_from_dialog_values(
            self.iface,
            {
                "source_layer": self._source_layer(),
                "file_format": "GPX",
                "file_path": self._path("does/not/exist/out.gpx"),
            }
        )

        self.assertFalse(result)
        self.assertEqual(len(self.iface.messageBar().calls), 1)
