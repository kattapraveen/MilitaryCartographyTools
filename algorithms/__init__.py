# -*- coding: utf-8 -*-

"""
Processing algorithms, and the provider that registers them.

Named `algorithms/` rather than `processing/` on purpose: a package
called `processing` inside the plugin would shadow QGIS's own
`processing` module and break every tool that calls processing.run().

Military Cartography Tools
"""

from .provider import MilitaryCartographyProvider, PROVIDER_ID
from .range_rings import RangeRingsAlgorithm, parse_rings


__all__ = [
    "MilitaryCartographyProvider",
    "PROVIDER_ID",
    "RangeRingsAlgorithm",
    "parse_rings",
]
