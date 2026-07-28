# -*- coding: utf-8 -*-

"""
MGRS 100 km Grid generator.

Creates MGRS 100km squares
from UTM Grid Zone Designator polygons.

Military Cartography Tools
"""


from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsProject,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsMessageLog,
    Qgis
)

from qgis.PyQt.QtCore import QMetaType

from ..core import mgrs_square_id
from ..core.coordinate_utils import WGS84, get_utm_crs_from_zone_band
from ._style_utils import apply_simple_fill_style

PLUGIN_LOG = "Military Cartography Tools"



class MGRS100KGenerator:


    def __init__(self):

        self.layer = None



    def create_layer(self):

        project_crs = QgsProject.instance().crs()

        self.layer = QgsVectorLayer(
            f"Polygon?crs={project_crs.authid()}",
            "MGRS 100km Grid",
            "memory"
        )


        provider = self.layer.dataProvider()


        provider.addAttributes(
            [

                QgsField(
                    "GZD",
                    QMetaType.Type.QString
                ),

                QgsField(
                    "100K",
                    QMetaType.Type.QString
                ),

                QgsField(
                    "ZONE",
                    QMetaType.Type.Int
                ),

                QgsField(
                    "EASTING",
                    QMetaType.Type.Int
                ),

                QgsField(
                    "NORTHING",
                    QMetaType.Type.Int
                )

            ]
        )


        self.layer.updateFields()

        return self.layer



    def apply_style(self):

        apply_simple_fill_style(
            self.layer,
            outline_width="0.7"
        )



    def generate(self, utm_layer):


        if self.layer is None:

            self.create_layer()


        provider = self.layer.dataProvider()

        provider.truncate()


        features = []


        project = QgsProject.instance()

        project_crs = project.crs()


        if utm_layer is None:

            return self.layer



        #
        # Process every GZD
        #

        for gzd in utm_layer.getFeatures():


            gzd_name = gzd["GZD"]

            zone = int(
                gzd["ZONE"]
            )

            band = gzd["BAND"]



            utm_crs = get_utm_crs_from_zone_band(
                zone,
                band
            )



            #
            # Transform GZD polygon into UTM
            #

            to_utm = QgsCoordinateTransform(
                WGS84,
                utm_crs,
                project
            )


            from_utm = QgsCoordinateTransform(
                utm_crs,
                project_crs,
                project
            )


            gzd_geom = QgsGeometry(
                gzd.geometry()
            )


            gzd_geom.transform(
                to_utm
            )


            bbox = gzd_geom.boundingBox()


            # A straight edge in UTM isn't straight once
            # reprojected back to the project CRS - it's a
            # gentle curve. Transforming only the 4 corners
            # draws a straight chord instead, and adjacent
            # squares' un-densified edges can visibly bow apart
            # then rejoin at shared corners (the "splitting and
            # joining like longitudes" look). Densify each edge
            # with intermediate points before the final
            # transform so it actually follows the curve.
            DENSIFY_SEGMENTS = 16

            def densified_square(sx, sy):

                corners = [
                    (sx, sy),
                    (sx + 100000, sy),
                    (sx + 100000, sy + 100000),
                    (sx, sy + 100000),
                    (sx, sy),
                ]

                ring = []

                for (cx1, cy1), (cx2, cy2) in zip(
                    corners, corners[1:]
                ):

                    for i in range(DENSIFY_SEGMENTS):

                        t = i / DENSIFY_SEGMENTS

                        ring.append(
                            QgsPointXY(
                                cx1 + (cx2 - cx1) * t,
                                cy1 + (cy2 - cy1) * t
                            )
                        )

                ring.append(
                    QgsPointXY(sx, sy)
                )

                return QgsGeometry.fromPolygonXY(
                    [ring]
                )


            #
            # Expand to complete 100km squares
            #

            xmin = (
                int(bbox.xMinimum() // 100000)
                * 100000
            )


            ymin = (
                int(bbox.yMinimum() // 100000)
                * 100000
            )


            xmax = (
                int(bbox.xMaximum() // 100000)
                * 100000
            )


            ymax = (
                int(bbox.yMaximum() // 100000)
                * 100000
            )



            #
            # Generate squares
            #

            x = xmin


            while x <= xmax:


                y = ymin


                while y <= ymax:


                    square = densified_square(
                        x, y
                    )


                    #
                    # Keep full squares or clipped edges
                    #

                    if gzd_geom.contains(square):

                        geom = square

                    else:

                        geom = square.intersection(
                            gzd_geom
                        )


                    # A square that only touches the GZD boundary
                    # (a shared edge/corner rather than a shared
                    # area) intersects to a LineString/Point, which
                    # is "valid" and "not empty" but has no area and
                    # is the wrong geometry type for this (Polygon)
                    # layer - skip those, or a single bad geometry
                    # in the batch fails the whole addFeatures() call.
                    if (
                        not geom.isEmpty()
                        and geom.isGeosValid()
                        and geom.area() > 0
                    ):

                        geom.transform(
                            from_utm
                        )


                        feature = QgsFeature(
                            self.layer.fields()
                        )


                        feature.setGeometry(
                            geom
                        )


                        square_id = mgrs_square_id(
                            zone,
                            x,
                            y,
                            band
                        ) or ""


                        feature.setAttributes(
                            [

                                gzd_name,

                                square_id,

                                zone,

                                int(x),

                                int(y)

                            ]
                        )


                        features.append(
                            feature
                        )


                    y += 100000


                x += 100000


        add_ok, _ = provider.addFeatures(
            features
        )

        if not add_ok:

            QgsMessageLog.logMessage(
                "Some MGRS 100km squares failed to add "
                "to the layer.",
                PLUGIN_LOG,
                Qgis.MessageLevel.Warning
            )


        self.layer.updateExtents()


        self.apply_style()


        return self.layer