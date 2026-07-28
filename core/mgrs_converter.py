# -*- coding: utf-8 -*-

"""
Military Cartography Tools

MGRS conversion interface.

Provides a clean wrapper around the MGRS engine.

Military Cartography Tools
"""


from . import mgrs_engine


_INV_ALPHABET = {
    code: letter
    for letter, code in mgrs_engine.ALPHABET.items()
}


def mgrs_square_id(zone, easting, northing, band=None):
    """
    Return the two-letter MGRS 100km square identifier
    for a UTM coordinate (standard false easting/northing
    included), given the zone it belongs to.

    Works directly from UTM zone/easting/northing, so no
    latitude/longitude round-trip (and no risk of resolving
    to the wrong zone for points near a zone boundary).
    """

    ltr2_low, ltr2_high, pattern_offset = mgrs_engine._gridValues(
        zone
    )

    if (
        band == "V"
        and zone == 31
        and easting == 500000.0
    ):
        easting -= 1.0

    northing = float(northing)

    while northing >= mgrs_engine.TWOMIL:
        northing -= mgrs_engine.TWOMIL

    northing += pattern_offset

    if northing >= mgrs_engine.TWOMIL:
        northing -= mgrs_engine.TWOMIL

    row = int(northing / mgrs_engine.ONEHT)

    if row > mgrs_engine.ALPHABET['H']:
        row += 1

    if row > mgrs_engine.ALPHABET['N']:
        row += 1

    col = ltr2_low + int((easting / mgrs_engine.ONEHT) - 1)

    if (
        ltr2_low == mgrs_engine.ALPHABET['J']
        and col > mgrs_engine.ALPHABET['N']
    ):
        col += 1

    # Out of the valid A-Z (minus I/O) range: the coordinate
    # is not actually inside this zone (e.g. an extent that
    # spans more than one UTM zone reprojected into a single
    # zone). Not a real 100km square, so no label rather than
    # a wrong or crashing one.
    if not (0 <= row <= 25) or not (0 <= col <= 25):
        return None

    return _INV_ALPHABET[col] + _INV_ALPHABET[row]


class MGRSConverter:
    """
    High level MGRS conversion interface.

    The conversion algorithm is provided by mgrs_engine.
    """


    def __init__(self, precision=5):

        """
        Parameters
        ----------
        precision : int
            MGRS precision.

            0 = 100 km
            1 = 10 km
            2 = 1 km
            3 = 100 m
            4 = 10 m
            5 = 1 m
        """

        if precision < 0 or precision > 5:
            raise ValueError(
                "MGRS precision must be between 0 and 5"
            )

        self.precision = precision



    # ---------------------------------------------------------
    # Coordinate conversion
    # ---------------------------------------------------------

    def convert(
        self,
        latitude,
        longitude
    ):

        """
        Convert latitude/longitude to MGRS.

        Returns
        -------
        str
            Raw MGRS string.
        """

        return mgrs_engine.toMgrs(
            float(latitude),
            float(longitude),
            self.precision
        )



    # ---------------------------------------------------------
    # Reverse conversion
    # ---------------------------------------------------------

    def to_latlon(
        self,
        mgrs_string
    ):

        """
        Convert an MGRS string back to (latitude, longitude)
        in WGS84.
        """

        return mgrs_engine.toWgs(
            mgrs_string
        )



    # ---------------------------------------------------------
    # Formatting
    # ---------------------------------------------------------

    def format(
        self,
        mgrs_string,
        spaces=True
    ):

        """
        Format MGRS string.

        Example:

        37MDQ7513515087

        becomes

        37M DQ 75135 15087
        """

        if not mgrs_string:

            return ""


        mgrs_string = (
            mgrs_string
            .replace(" ", "")
            .upper()
        )


        if len(mgrs_string) < 5:

            return mgrs_string


        if spaces:

            return (
                mgrs_string[0:3]
                + " "
                + mgrs_string[3:5]
                + " "
                + mgrs_string[5:10]
                + " "
                + mgrs_string[10:]
            )


        return mgrs_string



    # ---------------------------------------------------------
    # MGRS components
    # ---------------------------------------------------------

    def zone(self, mgrs_string):

        """
        Extract UTM zone.

        Example:

        37MDQ7513515087

        returns:

        37
        """

        mgrs_string = (
            mgrs_string
            .replace(" ", "")
        )

        return mgrs_string[:2]



    def gzd(self, mgrs_string):

        """
        Extract Grid Zone Designator.

        Example:

        37MDQ7513515087

        returns:

        37M
        """

        mgrs_string = (
            mgrs_string
            .replace(" ", "")
        )

        return mgrs_string[:3]



    def square(self, mgrs_string):

        """
        Extract 100 km square letters.

        Example:

        37MDQ7513515087

        returns:

        DQ
        """

        mgrs_string = (
            mgrs_string
            .replace(" ", "")
        )

        return mgrs_string[3:5]



    def one_km_label(self, mgrs_string):

        """
        Extract 1 km label.

        Example:

        37MDQ7513515087

        returns:

        75 15

        """

        mgrs_string = (
            mgrs_string
            .replace(" ", "")
        )

        return (
            mgrs_string[5:7],
            mgrs_string[10:12]
        )



    def easting(self, mgrs_string):

        """
        Extract the full-precision easting digits.

        Example:

        37MDQ7513515087

        returns:

        75135
        """

        mgrs_string = (
            mgrs_string
            .replace(" ", "")
        )

        digits = mgrs_string[5:]

        half = len(digits) // 2

        return digits[:half]



    def northing(self, mgrs_string):

        """
        Extract the full-precision northing digits.

        Example:

        37MDQ7513515087

        returns:

        15087
        """

        mgrs_string = (
            mgrs_string
            .replace(" ", "")
        )

        digits = mgrs_string[5:]

        half = len(digits) // 2

        return digits[half:]