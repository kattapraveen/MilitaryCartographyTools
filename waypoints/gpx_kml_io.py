# -*- coding: utf-8 -*-

"""
GPX/KML waypoint import/export - reusing this plugin's own MGRS
conversion so waypoints read from a GPS unit or ATAK (which only ever
carry lat/lon) get an MGRS grid reference attached, and so waypoints
exported from QGIS carry an MGRS label a receiving device can display
immediately, without the user cross-referencing anything else.

QGIS/GDAL already read and write both formats natively (via the OGR
GPX/KML drivers) - this module doesn't reimplement that, it wraps it
and adds the MGRS-labelling step neither format has any concept of on
its own.

Military Cartography Tools
"""

from qgis.core import (
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsProject,
    QgsVectorFileWriter,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QMetaType

from ..core import MGRSConverter
from ..core.coordinate_utils import WGS84


MGRS_FIELD_NAME = "mgrs"

# Full 1m precision - matches CoordinateProbeDialog's/BearingRangeDialog's
# own MGRS precision convention.
MGRS_PRECISION = 5

def default_insert_position(project, layer):

    """
    Imported waypoints' own default placement for a brand new layer -
    top of the layer tree, the same placement Line of Sight and
    Viewshed use for their own point/polygon overlays, since an
    imported waypoint layer should stay visible above whatever base
    terrain/grid layers are underneath, not get buried by them.
    """

    project.layerTreeRoot().insertLayer(
        0,
        layer
    )


# Candidate field names (checked case-insensitively, in this order)
# that might hold a waypoint's existing human-readable label. "Name"
# is what OGR's KML reader always calls the built-in <name> element,
# regardless of what field name was used to write it (confirmed live);
# "name" is GPX's own fixed waypoint schema field for the same thing.
LABEL_FIELD_CANDIDATES = ("name", "label", "desc", "description")


def _find_label_field(fields):

    """
    The first field in LABEL_FIELD_CANDIDATES present on fields
    (case-insensitive), or None if none of them exist.
    """

    lowercase_to_actual_name = {
        field.name().lower(): field.name() for field in fields
    }

    for candidate in LABEL_FIELD_CANDIDATES:

        if candidate in lowercase_to_actual_name:
            return lowercase_to_actual_name[candidate]

    return None


def _unique_field_name(base_name, existing_fields):

    """
    base_name, or base_name with a numeric suffix if a field of that
    name (case-insensitive) already exists - defends against the rare
    case of a source file already having its own "mgrs" field.
    """

    existing_lowercase = {
        field.name().lower() for field in existing_fields
    }

    if base_name.lower() not in existing_lowercase:
        return base_name

    suffix = 2

    while f"{base_name}_{suffix}".lower() in existing_lowercase:
        suffix += 1

    return f"{base_name}_{suffix}"


def _open_source_layer(file_path):

    """
    A read-only QgsVectorLayer over file_path's point features - the
    "waypoints" sublayer for a .gpx (GDAL's GPX driver also exposes
    routes/tracks/route_points/track_points as separate sublayers,
    none of which are wanted here), or the file's own default layer
    for a .kml (a single Placemark layer, confirmed live). .kmz
    (zipped KML) isn't handled - out of scope for this first pass.
    """

    if file_path.lower().endswith(".gpx"):

        return QgsVectorLayer(
            f"{file_path}|layername=waypoints",
            "waypoints",
            "ogr"
        )

    return QgsVectorLayer(
        file_path,
        "placemarks",
        "ogr"
    )


def _transform_to_wgs84(source_crs):

    return QgsCoordinateTransform(
        source_crs,
        WGS84,
        QgsProject.instance()
    )


def import_waypoints(file_path):

    """
    Read every waypoint/placemark point feature from a GPX or KML
    file and return a new in-memory WGS84 point layer carrying all of
    the original fields plus a new "mgrs" field - the original name/
    label field, if any, is left completely untouched alongside it.

    Returns None if the file has no readable point features (wrong
    file, empty waypoint list, or a GPX with only routes/tracks and
    no standalone waypoints).
    """

    source_layer = _open_source_layer(
        file_path
    )

    if not source_layer.isValid() or source_layer.featureCount() == 0:
        return None

    transform = _transform_to_wgs84(
        source_layer.crs()
    )

    mgrs_field_name = _unique_field_name(
        MGRS_FIELD_NAME,
        source_layer.fields()
    )

    output_layer = QgsVectorLayer(
        "Point?crs=EPSG:4326",
        "Imported Waypoints",
        "memory"
    )

    output_layer.dataProvider().addAttributes(
        list(source_layer.fields())
        + [QgsField(mgrs_field_name, QMetaType.Type.QString)]
    )

    output_layer.updateFields()

    converter = MGRSConverter(
        precision=MGRS_PRECISION
    )

    output_features = []

    for feature in source_layer.getFeatures():

        geometry = QgsGeometry(
            feature.geometry()
        )

        geometry.transform(
            transform
        )

        point = geometry.asPoint()

        mgrs = converter.format(
            converter.convert(point.y(), point.x())
        )

        new_feature = QgsFeature(
            output_layer.fields()
        )

        new_feature.setGeometry(
            geometry
        )

        new_feature.setAttributes(
            feature.attributes() + [mgrs]
        )

        output_features.append(
            new_feature
        )

    output_layer.dataProvider().addFeatures(
        output_features
    )

    return output_layer


def export_waypoints(source_layer, file_path, file_format):

    """
    Write every point feature in source_layer out as a GPX or KML
    waypoint file, with each waypoint's "name" set to its MGRS grid
    reference (the field a receiving GPS unit/ATAK actually displays)
    and the source layer's own name/label field, if any, preserved
    alongside it as a separate description field.

    That description field is named "desc" for GPX and "description"
    for KML - confirmed live that those are the one field name each
    driver's fixed schema maps to its own native <desc>/<description>
    element; anything else either needs GPX_USE_EXTENSIONS (GPX) or
    ends up as free-form ExtendedData (KML), neither of which most
    consumer GPS units/ATAK render as a visible description.

    file_format must be "GPX" or "KML" (QgsVectorFileWriter's own
    driver names). Returns (True, None) on success, or
    (False, error_message) - e.g. an unwritable destination path.
    """

    if file_format not in ("GPX", "KML"):

        raise ValueError(
            f"Unsupported export format: {file_format!r}"
        )

    description_field_name = (
        "desc" if file_format == "GPX" else "description"
    )

    output_layer = QgsVectorLayer(
        "Point?crs=EPSG:4326",
        "waypoints",
        "memory"
    )

    output_layer.dataProvider().addAttributes(
        [
            QgsField("name", QMetaType.Type.QString),
            QgsField(description_field_name, QMetaType.Type.QString),
        ]
    )

    output_layer.updateFields()

    label_field_name = _find_label_field(
        source_layer.fields()
    )

    transform = _transform_to_wgs84(
        source_layer.crs()
    )

    converter = MGRSConverter(
        precision=MGRS_PRECISION
    )

    output_features = []

    for feature in source_layer.getFeatures():

        geometry = QgsGeometry(
            feature.geometry()
        )

        geometry.transform(
            transform
        )

        point = geometry.asPoint()

        mgrs = converter.format(
            converter.convert(point.y(), point.x())
        )

        original_label = (
            feature[label_field_name] if label_field_name else None
        )

        new_feature = QgsFeature(
            output_layer.fields()
        )

        new_feature.setGeometry(
            geometry
        )

        new_feature.setAttributes(
            [
                mgrs,
                "" if original_label is None else str(original_label),
            ]
        )

        output_features.append(
            new_feature
        )

    output_layer.dataProvider().addFeatures(
        output_features
    )

    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = file_format

    if file_format == "GPX":
        # Otherwise GDAL's GPX driver names the sublayer after the
        # output file's own basename instead of "waypoints", which
        # some GPS units/ATAK are stricter about recognising than
        # QGIS itself is when reading it back.
        options.layerName = "waypoints"

    write_result = QgsVectorFileWriter.writeAsVectorFormatV3(
        output_layer,
        file_path,
        QgsProject.instance().transformContext(),
        options
    )

    if write_result[0] != QgsVectorFileWriter.WriterError.NoError:
        return False, write_result[1]

    return True, None
