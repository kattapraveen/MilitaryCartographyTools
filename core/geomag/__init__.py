# -*- coding: utf-8 -*-

"""
Vendored World Magnetic Model implementation (pyGeoMag), used for
magnetic declination. See THIRD_PARTY_NOTICES.md.
"""

from .geomag import GeoMag, GeoMagResult
from .wmm_2025 import WMM_2025


__all__ = [
    "GeoMag",
    "GeoMagResult",
    "WMM_2025",
]
