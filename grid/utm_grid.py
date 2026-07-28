# -*- coding: utf-8 -*-

"""
UTM Grid generator.

Creates MGRS Grid Zone Designator polygons
for the current map extent.

Military Cartography Tools
"""


from qgis.core import (
    QgsVectorLayer,
    QgsFeature,
    QgsGeometry,
    QgsField,
    QgsCoordinateTransform,
    QgsProject
)

from qgis.PyQt.QtCore import QVariant

from ..core.coordinate_utils import WGS84
from ._style_utils import apply_simple_fill_style



class UTMGridGenerator:
    """
    Generates extent-based UTM GZD polygons.
    """


    def __init__(self):

        self.layer = None



    def apply_style(self):

        apply_simple_fill_style(
            self.layer,
            outline_width="1.2"
        )



    def create_layer(self):

        """
        Create UTM grid layer.
        """

        self.layer = QgsVectorLayer(
            "Polygon?crs=EPSG:4326",
            "UTM Grid",
            "memory"
        )


        provider = self.layer.dataProvider()


        provider.addAttributes(
            [

                QgsField(
                    "GZD",
                    QVariant.String
                ),

                QgsField(
                    "ZONE",
                    QVariant.Int
                ),

                QgsField(
                    "BAND",
                    QVariant.String
                )

            ]
        )


        self.layer.updateFields()


        return self.layer



    def required_zones(self, extent):

        """
        Determine required UTM zones
        from WGS84 extent.
        """

        zones = set()


        xmin = extent.xMinimum()
        xmax = extent.xMaximum()


        start_zone = int(
            (xmin + 180) / 6
        ) + 1


        end_zone = int(
            (xmax + 180) / 6
        ) + 1


        for zone in range(
            max(1, start_zone),
            min(60, end_zone) + 1
        ):

            zones.add(
                zone
            )


        return zones



    def required_bands(self, extent):

        """
        Determine required latitude bands
        from WGS84 extent.
        """

        bands = "CDEFGHJKLMNPQRSTUVWXX"


        required = set()


        ymin = max(
            -80,
            extent.yMinimum()
        )


        ymax = min(
            84,
            extent.yMaximum()
        )


        start = int(
            (ymin + 80) / 8
        )


        end = int(
            (ymax + 80) / 8
        )


        for index in range(
            start,
            end + 1
        ):

            required.add(
                bands[index]
            )


        return required



    def extent_to_wgs84(self, extent):

        """
        Convert current project extent
        to longitude/latitude.
        """

        transform = QgsCoordinateTransform(
            QgsProject.instance().crs(),
            WGS84,
            QgsProject.instance()
        )


        return transform.transformBoundingBox(
            extent
        )



    def generate(self, extent):

        """
        Generate GZD polygons
        intersecting extent.
        """


        extent = self.extent_to_wgs84(
            extent
        )


        if self.layer is None:

            self.create_layer()


        provider = self.layer.dataProvider()


        provider.truncate()


        features = []


        zones = self.required_zones(
            extent
        )


        bands = self.required_bands(
            extent
        )



        for zone in zones:


            west = -180 + (
                (zone - 1) * 6
            )


            east = west + 6



            for band in bands:


                index = (
                    "CDEFGHJKLMNPQRSTUVWXX"
                    .index(band)
                )


                south = -80 + (
                    index * 8
                )


                north = south + 8


                if band == "X":

                    north = 84



                geom = QgsGeometry.fromWkt(
                    f"""
                    POLYGON(
                    (
                    {west} {south},
                    {east} {south},
                    {east} {north},
                    {west} {north},
                    {west} {south}
                    )
                    )
                    """
                )


                feature = QgsFeature(
                    self.layer.fields()
                )


                feature.setGeometry(
                    geom
                )


                feature.setAttributes(
                    [

                        f"{zone}{band}",
                        zone,
                        band

                    ]
                )


                features.append(
                    feature
                )



        provider.addFeatures(
            features
        )


        self.layer.updateExtents()


        self.apply_style()


        return self.layer