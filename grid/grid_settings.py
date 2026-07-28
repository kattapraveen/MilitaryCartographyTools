# -*- coding: utf-8 -*-

"""
Grid settings manager.

Military Cartography Tools
"""

from qgis.core import QgsProject


class GridSettings:
    """
    Stores grid preferences in QGIS 4 project variables.
    """

    PREFIX = "MilitaryCartographyTools/Grid"


    @classmethod
    def _variables(cls):

        return QgsProject.instance().customVariables()



    @classmethod
    def set_value(cls, key, value):

        variables = cls._variables()

        variables[f"{cls.PREFIX}/{key}"] = value

        QgsProject.instance().setCustomVariables(
            variables
        )



    @classmethod
    def value(cls, key, default=None):

        variables = cls._variables()

        return variables.get(
            f"{cls.PREFIX}/{key}",
            default
        )


    # -------------------------------------------------
    # UTM Grid
    # -------------------------------------------------

    @classmethod
    def set_utm_visible(cls, state):

        cls.set_value(
            "utm_visible",
            state
        )


    @classmethod
    def utm_visible(cls):

        return cls.value(
            "utm_visible",
            True
        )



    # -------------------------------------------------
    # MGRS 100km Grid
    # -------------------------------------------------

    @classmethod
    def set_mgrs100_visible(cls, state):

        cls.set_value(
            "mgrs100_visible",
            state
        )


    @classmethod
    def mgrs100_visible(cls):

        return cls.value(
            "mgrs100_visible",
            True
        )



    # -------------------------------------------------
    # MGRS Sub Grid
    # -------------------------------------------------

    @classmethod
    def set_mgrs_sub_visible(cls, state):

        cls.set_value(
            "mgrs_sub_visible",
            state
        )


    @classmethod
    def mgrs_sub_visible(cls):

        return cls.value(
            "mgrs_sub_visible",
            True
        )



    @classmethod
    def set_mgrs_sub_spacing(cls, spacing):

        """
        Set sub-grid spacing in metres.

        Allowed:
        10000 = 10 km
        5000  = 5 km
        1000  = 1 km
        """

        cls.set_value(
            "mgrs_sub_spacing",
            spacing
        )



    @classmethod
    def mgrs_sub_spacing(cls):

        """
        Return sub-grid spacing.
        """

        return cls.value(
            "mgrs_sub_spacing",
            10000
        )