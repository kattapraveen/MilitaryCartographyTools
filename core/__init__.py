# -*- coding: utf-8 -*-

"""
Core functionality.
"""

from .mgrs_converter import (
    MGRSConverter,
    mgrs_square_id,
)

from .coordinate_utils import grid_convergence, magnetic_declination

__all__ = [
    "MGRSConverter",
    "mgrs_square_id",
    "grid_convergence",
    "magnetic_declination",
]