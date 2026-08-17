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

from qgis.PyQt.QtCore import QMetaType

import math

from ..core.coordinate_utils import (
    WGS84,
    utm_candidate_zones,
    utm_zone_bounds,
)
from ._style_utils import apply_simple_fill_style



# A degree of latitude is very nearly constant; a degree of longitude
# is not, shrinking with the cosine of latitude to nothing at the pole.
METERS_PER_DEGREE_LATITUDE = 111320.0


def _minimum_half_extent_m(west, east, south, north):

    """
    The smaller of a GZD cell's two half-dimensions, in metres:
    half its width and half its height, measured at the latitude
    where the cell is narrowest.

    This is the distance a label anchored at the centroid can be
    nudged before it leaves the cell, and it is what grid_labels.py
    compares a fixed page offset against. Width is measured at the
    poleward edge rather than at the centroid, deliberately - a cell
    narrows towards the pole, so the centroid's own width would
    overstate the room available on the side the label is nudged
    towards.

    Height is included even though width is the binding constraint
    almost everywhere, because near the equator a 6-degree cell is
    wider than an 8-degree band is tall, and the label is nudged up
    as well as left.
    """

    poleward = max(abs(south), abs(north))

    cos_latitude = max(
        math.cos(math.radians(poleward)),
        0.0
    )

    width_m = (east - west) * METERS_PER_DEGREE_LATITUDE * cos_latitude
    height_m = (north - south) * METERS_PER_DEGREE_LATITUDE

    return min(width_m, height_m) / 2.0


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
                    QMetaType.Type.QString
                ),

                QgsField(
                    "ZONE",
                    QMetaType.Type.Int
                ),

                QgsField(
                    "BAND",
                    QMetaType.Type.QString
                ),

                # The cell's own smaller half-dimension on the ground,
                # in metres - see _minimum_half_extent_m(). Carried on
                # the feature so the label rules can decide per cell
                # whether a fixed page offset still fits inside it,
                # instead of one global scale threshold standing in for
                # cells that range from 3 to 12 degrees wide and vary
                # tenfold in ground width between the equator and band
                # X. See grid/grid_labels.py.
                QgsField(
                    "HALF_MIN_M",
                    QMetaType.Type.Double
                )

            ]
        )


        self.layer.updateFields()


        return self.layer



    def required_zones(self, extent):

        """
        Determine required UTM zones from a WGS84 extent.

        Deliberately ONE ZONE WIDER on each side than the longitude
        arithmetic alone implies - see utm_candidate_zones(). The
        extras are filtered back out in generate(), which drops any
        cell whose real bounds miss the extent, so a widened exception
        cell (32V reaching down to 3E, 33X down to 9E) is still found
        without drawing spurious neighbours.
        """

        return set(
            utm_candidate_zones(
                extent.xMinimum(),
                extent.xMaximum()
            )
        )



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



        for zone in sorted(zones):


            for band in sorted(bands):


                bounds = utm_zone_bounds(
                    zone,
                    band
                )


                # 32X, 34X and 36X do not exist - their ground belongs
                # to the widened 31X/33X/35X/37X either side.
                if bounds is None:

                    continue


                west, east = bounds


                # required_zones() casts one zone wider than the
                # arithmetic needs, so a widened cell is never missed;
                # this is where the extras come back out again.
                if east <= extent.xMinimum() or west >= extent.xMaximum():

                    continue


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
                        band,
                        _minimum_half_extent_m(west, east, south, north)

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