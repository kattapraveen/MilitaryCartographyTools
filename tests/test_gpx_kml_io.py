# -*- coding: utf-8 -*-

"""
Tests for waypoints/gpx_kml_io.py - the GPX/KML read/write + MGRS-
labelling logic, independent of the dialog UI that drives it (see
tests/test_gpx_kml_dialog.py for that).

Military Cartography Tools
"""

import os
import tempfile

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType

from .qgis_test_case import QgisTestCase

from MilitaryCartographyTools.waypoints.gpx_kml_io import (
    default_insert_position,
    export_waypoints,
    import_waypoints,
)


def _make_point_layer(name_value="WP001"):

    layer = QgsVectorLayer(
        "Point?crs=EPSG:4326",
        "source",
        "memory"
    )

    layer.dataProvider().addAttributes(
        [QgsField("name", QMetaType.Type.QString)]
    )

    layer.updateFields()

    feature = QgsFeature(
        layer.fields()
    )

    feature.setGeometry(
        QgsGeometry.fromPointXY(QgsPointXY(39.2083, -6.7924))
    )

    feature.setAttributes(
        [name_value]
    )

    layer.dataProvider().addFeature(
        feature
    )

    return layer


class _TempFileTestCase(QgisTestCase):

    def setUp(self):

        super().setUp()

        QgsProject.instance().setCrs(
            QgsCoordinateReferenceSystem("EPSG:4326")
        )

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


class TestExportWaypoints(_TempFileTestCase):

    def test_gpx_name_field_is_the_mgrs_string(self):

        source = _make_point_layer()

        path = self._path("out.gpx")

        success, error = export_waypoints(source, path, "GPX")

        self.assertTrue(success)
        self.assertIsNone(error)

        with open(path) as f:
            content = f.read()

        self.assertIn("<name>37M", content)
        self.assertIn("<desc>WP001</desc>", content)


    def test_kml_name_field_is_the_mgrs_string(self):

        source = _make_point_layer()

        path = self._path("out.kml")

        success, error = export_waypoints(source, path, "KML")

        self.assertTrue(success)
        self.assertIsNone(error)

        with open(path) as f:
            content = f.read()

        self.assertIn("<name>37M", content)
        self.assertIn("<description>WP001</description>", content)


    def test_source_layer_with_no_label_field_exports_an_empty_description(self):

        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "unlabelled",
            "memory"
        )

        feature = QgsFeature(
            layer.fields()
        )

        feature.setGeometry(
            QgsGeometry.fromPointXY(QgsPointXY(39.2083, -6.7924))
        )

        layer.dataProvider().addFeature(
            feature
        )

        path = self._path("unlabelled.gpx")

        success, error = export_waypoints(layer, path, "GPX")

        self.assertTrue(success)

        with open(path) as f:
            content = f.read()

        self.assertIn("<desc></desc>", content)


    def test_unsupported_format_raises(self):

        source = _make_point_layer()

        with self.assertRaises(ValueError):
            export_waypoints(source, self._path("out.gpx"), "SHP")


    def test_unwritable_destination_returns_false_and_a_message(self):

        source = _make_point_layer()

        bad_path = self._path("does/not/exist/out.gpx")

        success, error = export_waypoints(source, bad_path, "GPX")

        self.assertFalse(success)
        self.assertIsNotNone(error)


class TestImportWaypoints(_TempFileTestCase):

    def test_gpx_round_trip_adds_an_mgrs_field_and_keeps_the_original(self):

        source = _make_point_layer()

        path = self._path("roundtrip.gpx")

        export_waypoints(source, path, "GPX")

        imported = import_waypoints(
            path
        )

        self.assertIsNotNone(imported)
        self.assertEqual(imported.featureCount(), 1)

        feature = next(imported.getFeatures())

        # "name" on the re-imported layer is the MGRS string that was
        # exported (GPX's own fixed schema field), and "mgrs" is the
        # newly-added field computed independently on import - both
        # should agree, since they describe the same point.
        self.assertEqual(feature["name"], feature["mgrs"])
        self.assertEqual(feature["desc"], "WP001")


    def test_kml_round_trip_adds_an_mgrs_field_and_keeps_the_original(self):

        source = _make_point_layer()

        path = self._path("roundtrip.kml")

        export_waypoints(source, path, "KML")

        imported = import_waypoints(
            path
        )

        self.assertIsNotNone(imported)
        self.assertEqual(imported.featureCount(), 1)

        feature = next(imported.getFeatures())

        # OGR's KML reader always calls the built-in <name> element
        # "Name" (capitalised) on read-back, regardless of what field
        # name was used to write it - confirmed live.
        self.assertEqual(feature["Name"], feature["mgrs"])
        self.assertEqual(feature["description"], "WP001")


    def test_gpx_with_no_waypoints_returns_none(self):

        path = self._path("empty.gpx")

        with open(path, "w") as f:
            f.write(
                '<?xml version="1.0"?>'
                '<gpx version="1.1" '
                'xmlns="http://www.topografix.com/GPX/1/1"></gpx>'
            )

        self.assertIsNone(
            import_waypoints(path)
        )


    def test_nonexistent_file_returns_none(self):

        self.assertIsNone(
            import_waypoints(self._path("does_not_exist.gpx"))
        )


    def test_existing_mgrs_field_on_source_does_not_collide(self):

        # A source KML that already happens to have a field named
        # "mgrs" (however unlikely from a real device) shouldn't have
        # it silently overwritten - the newly-computed field should
        # get a distinct name instead.
        layer = QgsVectorLayer(
            "Point?crs=EPSG:4326",
            "already_has_mgrs",
            "memory"
        )

        layer.dataProvider().addAttributes(
            [
                QgsField("name", QMetaType.Type.QString),
                QgsField("mgrs", QMetaType.Type.QString),
            ]
        )

        layer.updateFields()

        feature = QgsFeature(
            layer.fields()
        )

        feature.setGeometry(
            QgsGeometry.fromPointXY(QgsPointXY(39.2083, -6.7924))
        )

        feature.setAttributes(
            ["WP001", "pre-existing value"]
        )

        layer.dataProvider().addFeature(
            feature
        )

        path = self._path("collision.kml")

        from qgis.core import QgsCoordinateTransformContext, QgsVectorFileWriter

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "KML"

        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            path,
            QgsCoordinateTransformContext(),
            options
        )

        imported = import_waypoints(
            path
        )

        self.assertIsNotNone(imported)

        field_names = [f.name() for f in imported.fields()]

        self.assertIn("mgrs", field_names)
        self.assertIn("mgrs_2", field_names)

        feature = next(imported.getFeatures())

        self.assertEqual(feature["mgrs"], "pre-existing value")
        self.assertNotEqual(feature["mgrs_2"], "pre-existing value")


class TestDefaultInsertPosition(QgisTestCase):

    def test_places_the_layer_at_the_top_of_the_tree(self):

        project = QgsProject.instance()

        first = QgsVectorLayer("Point?crs=EPSG:4326", "existing", "memory")

        project.addMapLayer(first)

        second = QgsVectorLayer("Point?crs=EPSG:4326", "Imported Waypoints", "memory")

        project.addMapLayer(
            second,
            False
        )

        default_insert_position(
            project,
            second
        )

        root = project.layerTreeRoot()

        names = [child.name() for child in root.children()]

        self.assertEqual(
            names[0],
            "Imported Waypoints"
        )
