# -*- coding: utf-8 -*-

"""
Processing algorithms, and the provider that registers them.

Named `algorithms/` rather than `processing/` on purpose: a package
called `processing` inside the plugin would shadow QGIS's own
`processing` module and break every tool that calls processing.run().

Military Cartography Tools
"""

from .contours import ContoursAlgorithm
from .hillshade_combination import HillshadeCombinationAlgorithm
from .hypsometric_tint import HypsometricTintAlgorithm
from .provider import MilitaryCartographyProvider, PROVIDER_ID
from .range_rings import RangeRingsAlgorithm, parse_rings
from .tanaka_contours import TanakaContoursAlgorithm


__all__ = [
    "ContoursAlgorithm",
    "HillshadeCombinationAlgorithm",
    "HypsometricTintAlgorithm",
    "MilitaryCartographyProvider",
    "PROVIDER_ID",
    "RangeRingsAlgorithm",
    "TanakaContoursAlgorithm",
    "parse_rings",
]
