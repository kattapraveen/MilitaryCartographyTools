# -*- coding: utf-8 -*-

"""
Renders a MIL-STD-2525/APP-6 symbol from a SIDC by running the vendored
milsymbol.js (see military_symbology/vendor/, THIRD_PARTY_NOTICES.md)
through Qt's own QJSEngine - no Node.js, no browser, no network access,
confirmed live to work identically on both QGIS 3.44 (PyQt5) and QGIS 4.2
(PyQt6).

qgis.PyQt doesn't provide a QtQml shim (confirmed - only the commonly-used
submodules like QtCore/QtGui/QtWidgets are aliased there), so this is the
one module in this plugin that imports directly from whichever PyQt binding
is actually active, mirroring exactly what QGIS's own qgis.PyQt.QtCore shim
does internally (a plain hardcoded `from PyQt5/6.QtCore import *` depending
on the QGIS build) - confirmed live that both QGIS 3.44 and 4.2 only ever
have ONE of these importable, so the try/except below deterministically
picks the one already loaded in-process rather than risking two separate
Qt binding instances running side by side.

Military Cartography Tools
"""

import base64
import json
import os
import re

try:
    from PyQt5.QtQml import QJSEngine
except ImportError:
    from PyQt6.QtQml import QJSEngine


_VENDOR_JS_PATH = os.path.join(
    os.path.dirname(__file__),
    "vendor",
    "milsymbol.js"
)

# Lazily constructed - QJSEngine() requires a QCoreApplication to already
# exist, which is only guaranteed once QGIS itself (or a test harness) has
# started, not at plugin import time.
_engine = None

# Keyed by (sidc, sorted-options-tuple) - QGIS may re-evaluate a feature's
# style expression on every repaint/pan/zoom, and re-invoking the JS engine
# for a SIDC it's already rendered would be wasted work. Only scalar option
# values are supported (a sorted tuple of the options dict's own items is
# used as the cache key), which covers every option milsymbol itself takes
# (size, fill, frame, and similar).
_svg_cache = {}


def _get_engine():

    global _engine

    if _engine is None:

        engine = QJSEngine()

        with open(_VENDOR_JS_PATH, "r", encoding="utf-8") as handle:
            source = handle.read()

        load_result = engine.evaluate(source)

        if load_result.isError():

            raise RuntimeError(
                "Failed to load vendored milsymbol.js: "
                + load_result.toString()
            )

        _engine = engine

    return _engine


def _cache_key(sidc, options):

    return (sidc, tuple(sorted((options or {}).items())))


def render_symbol_svg(sidc, options=None):

    """
    SVG markup (a string) for sidc, via milsymbol.js's own
    `new ms.Symbol(sidc, options).asSVG()` - options is milsymbol's own
    options object (e.g. {"size": 35}), passed through as-is. Cached per
    (sidc, options) combination - see _svg_cache's own comment.
    """

    key = _cache_key(sidc, options)

    if key in _svg_cache:
        return _svg_cache[key]

    engine = _get_engine()

    js = "new ms.Symbol({}, {}).asSVG()".format(
        json.dumps(sidc),
        json.dumps(options or {})
    )

    result = engine.evaluate(js)

    if result.isError():

        raise RuntimeError(
            f"milsymbol.js failed to render SIDC {sidc!r}: "
            + result.toString()
        )

    svg = result.toString()

    _svg_cache[key] = svg

    return svg


_STROKE_WIDTH_PATTERN = re.compile(r'stroke-width="([\d.]+)"')


def scale_svg_stroke_width(svg, factor):

    """
    Multiplies every stroke-width in `svg` by `factor`.

    Done here rather than through milsymbol's own `strokeWidth` option,
    which does NOT do this: probed directly, that option only widens
    the generated viewBox (108 -> 110.8) while every path keeps its
    original stroke-width="3". Passing it would therefore make an icon
    render SMALLER at a fixed marker size, and no thicker - the opposite
    of what it looks like it does.
    """

    if not factor or factor == 1:
        return svg

    return _STROKE_WIDTH_PATTERN.sub(
        lambda match: 'stroke-width="{:g}"'.format(
            float(match.group(1)) * factor
        ),
        svg
    )


def render_symbol_base64_path(sidc, options=None, stroke_scale=None):

    """
    "base64:<...>" for sidc - the exact path string format
    QgsSvgMarkerSymbolLayer/QgsSvgCache accept directly for inline SVG
    content (confirmed live: QgsSvgCache.svgAsImage() returns a valid
    non-null image for this format), so a rendered symbol never needs to
    touch disk as a temp file.

    `stroke_scale` thickens (or thins) every stroke in the rendered
    symbol - see scale_svg_stroke_width() for why this cannot be left
    to milsymbol.
    """

    svg = scale_svg_stroke_width(
        render_symbol_svg(sidc, options),
        stroke_scale
    )

    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")

    return "base64:" + encoded
