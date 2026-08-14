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

    Options naming one of INJECTED_TEXT_SLOTS are NOT milsymbol's: they
    are drawn here instead, on icons milsymbol gives no text position
    at all. See _inject_text().
    """

    key = _cache_key(sidc, options)

    if key in _svg_cache:
        return _svg_cache[key]

    engine = _get_engine()

    options = options or {}

    injected = {
        slot: text for slot, text in options.items()
        if slot in INJECTED_TEXT_SLOTS
    }

    js = "new ms.Symbol({}, {}).asSVG()".format(
        json.dumps(sidc),
        json.dumps(
            {
                slot: value for slot, value in options.items()
                if slot not in INJECTED_TEXT_SLOTS
            }
        )
    )

    result = engine.evaluate(js)

    if result.isError():

        raise RuntimeError(
            f"milsymbol.js failed to render SIDC {sidc!r}: "
            + result.toString()
        )

    svg = _correct_viewbox(
        sidc,
        _apply_dominant_baseline(
            _inject_text(sidc, result.toString(), injected)
        )
    )

    _svg_cache[key] = svg

    return svg


_TEXT_PATTERN = re.compile(r"<text\b[^>]*>")

_FONT_SIZE_PATTERN = re.compile(r'font-size="([\d.]+)"')

_TEXT_Y_PATTERN = re.compile(r'\by="(-?[\d.]+)"')

# SVG's own definition of the "middle" dominant baseline: half the
# font's x-height above the alphabetic baseline. Arial's x-height is
# 0.519 em, and every <text> milsymbol emits asks for Arial, so this
# is that font's own ratio rather than a tuned constant. Qt is asked
# for the metrics at run time instead of hardcoding 0.2595 only
# because macOS substitutes Helvetica for Arial and the two differ in
# the third decimal; the fallback below is the Arial figure.
_MIDDLE_BASELINE_RATIO = None


def _middle_baseline_ratio():

    global _MIDDLE_BASELINE_RATIO

    if _MIDDLE_BASELINE_RATIO is None:

        try:

            from qgis.PyQt.QtGui import QFont, QFontMetricsF

            font = QFont("Arial", -1)
            font.setPixelSize(1000)
            font.setBold(True)

            _MIDDLE_BASELINE_RATIO = (
                QFontMetricsF(font).xHeight() / 1000.0 / 2.0
            )

        except Exception:

            _MIDDLE_BASELINE_RATIO = 0.2595

    return _MIDDLE_BASELINE_RATIO


def _apply_dominant_baseline(svg):

    """
    Bakes milsymbol's own `dominant-baseline="middle"` into an explicit
    `y`, because **Qt's SVG renderer silently ignores that attribute**.

    Probed directly: the same <text> renders pixel-for-pixel identically
    with and without it, so every label milsymbol means to CENTRE on its
    own y instead sits with its BASELINE there - roughly 0.26 em too
    high. Usually that only looks a touch off; where an icon puts a
    letter just under a centre dot it is a real collision, which is how
    this surfaced (Table H-XIV's Reference Points - Corridor Tab Point's
    "C", Data Link's "D", Marshall's "M" and the rest all sat ON the
    dot, unreadable). The attribute is left in place afterwards so the
    markup still says what it means to any renderer that does honour it;
    only `y` moves.
    """

    if 'dominant-baseline="middle"' not in svg:
        return svg

    def shift(match):

        tag = match.group(0)

        if 'dominant-baseline="middle"' not in tag:
            return tag

        font_size = _FONT_SIZE_PATTERN.search(tag)
        y = _TEXT_Y_PATTERN.search(tag)

        if not font_size or not y:
            return tag

        shifted = (
            float(y.group(1))
            + float(font_size.group(1)) * _middle_baseline_ratio()
        )

        return _TEXT_Y_PATTERN.sub(
            'y="{:g}"'.format(shifted),
            tag,
            count=1
        )

    return _TEXT_PATTERN.sub(shift, svg)


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


# --- milsymbol bbox corrections -------------------------------------
#
# milsymbol declares a bounding box per icon by hand, and a handful do
# not match what the icon actually draws. QGIS sizes an SVG marker by
# its WIDTH, so an over-generous box makes the icon render SMALLER at
# the same marker size than its own siblings - the symbol is right, the
# scale is not.
#
# Keyed by the SIDC's own entity digits (11-16). Only entries verified
# against milsymbol's own drawn geometry belong here, never a guess:
# each one below was read off the generated SVG itself, not inferred.
#
# **Sonobuoys (Table H-XIV, 213500-213515).** Every sonobuoy in the
# family is the same drawing - a circle r=40 centred at (100,100) plus
# a lead - so every one truly spans x 60..140, and milsymbol says so
# for 213500-213509 (bbox x1:60 x2:140, viewBox 88 wide). For
# 213510-213515 it declares x1:40 x2:160 instead, 128 wide, purely
# generous padding: the letter each of them adds sits INSIDE the
# circle at font-size 45 and widens nothing. The result was that
# Expired, Kingpin, LOFAR, Pattern Center, Range Only and VLAD all
# rendered ~31% smaller than the ten sonobuoys beside them, which is
# what the maintainer reported ("these symbols are smaller than others
# significantly").
#
# 213510 (Expired) is the one whose extra ink is real - its cross does
# run x 40..160. It is corrected to the family box anyway, deliberately:
# the sonobuoy's CIRCLE is what has to match its siblings, and the
# cross reads as struck THROUGH that circle exactly as the standard's
# own picture draws it. Qt does not clip an SVG to its viewBox
# (probed directly), so the overhanging arms still draw.
_SONOBUOY_FAMILY_VIEWBOX = "56 -14 88 178"

_VIEWBOX_CORRECTIONS = {
    "213510": _SONOBUOY_FAMILY_VIEWBOX,
    "213511": _SONOBUOY_FAMILY_VIEWBOX,
    "213512": _SONOBUOY_FAMILY_VIEWBOX,
    "213513": _SONOBUOY_FAMILY_VIEWBOX,
    "213514": _SONOBUOY_FAMILY_VIEWBOX,
    "213515": _SONOBUOY_FAMILY_VIEWBOX,
}

# ---------------------------------------------------------------
# Text milsymbol will not draw
# ---------------------------------------------------------------
#
# A handful of Appendix H icons have amplifier boxes in the standard's
# own template that milsymbol defines NO option for - not the one this
# project wants, not any at all. Established by probing every icon in
# the affected tables for which text options it actually accepts and
# where each one lands, not by reading milsymbol's source (its option
# NAMING lines up with neither the standard's field naming nor itself
# across icons).
#
# Two so far, both boxes the standard fills in its own EXAMPLE column:
#
# - **321706, NATO Multiple Supply Class Point.** Its milsymbol entry
#   is the bare supply-box path and nothing else. Its template asks for
#   A/A1/A2 (up to three supply class numbers, or ALL - drawn as one
#   slash-joined string, "I/III/V" in the standard's own example) plus
#   T1 below it ("ISAF").
# - **320100, Ambulance Exchange Point.** Same story, one box: T1,
#   filled with "4077" in its own example.
#
# So the text is drawn HERE, into the returned SVG, at coordinates
# LIFTED FROM A SIBLING ICON milsymbol does define rather than invented
# - 321706's two positions from 321701-321705 (the class numeral) and
# 321700 (T1), 320100's from 320200. Keyed by SIDC digits 11-16, the
# same key _VIEWBOX_CORRECTIONS uses.
#
# Each entry is (x, y, font size, bold, middle-baseline), every field
# copied from the sibling's own markup - including the last one, which
# matters: milsymbol draws the class numeral with
# dominant-baseline="middle" and its T1 designation WITHOUT it, on a
# plain alphabetic baseline. Injection happens BEFORE
# _apply_dominant_baseline() runs, so a slot that says middle gets the
# same correction milsymbol's own labels get, and one that does not is
# left alone - which is the only way both land where the sibling's do.
_FIELD_A_SLOT = "mctFieldA"
_FIELD_T1_SLOT = "mctFieldT1"

_INJECTED_TEXT = {
    "321706": {
        _FIELD_A_SLOT: (100, -18.3327, 45, True, True),
        _FIELD_T1_SLOT: (100, 20, 30, False, False),
    },
    "320100": {
        _FIELD_T1_SLOT: (100, 30, 30, False, False),
    },
}

INJECTED_TEXT_SLOTS = frozenset([_FIELD_A_SLOT, _FIELD_T1_SLOT])

# The widest the injected text may be drawn, in icon units. The supply
# box's own walls are at x=60 and x=140; this leaves a little air
# inside them. A longer string is scaled down to fit rather than
# spilling over the frame, which is what "I/III/V" at the sibling's own
# 45 would do.
_INJECTED_TEXT_MAX_WIDTH = 72.0

_PATH_STROKE_PATTERN = re.compile(r'<path\b[^>]*\bstroke="([^"]+)"')


def _injected_text_colour(svg):

    """
    The colour milsymbol drew this icon's own frame in.

    Read off the markup rather than resolved from the affiliation
    again, so injected text follows whatever the icon actually did -
    including monoColor, which recolours the whole symbol.
    """

    match = _PATH_STROKE_PATTERN.search(svg)

    return match.group(1) if match else "black"


def _fitted_font_size(text, font_size, bold):

    """
    `font_size`, or smaller if the text would otherwise overrun
    _INJECTED_TEXT_MAX_WIDTH. Measured with the same Qt font machinery
    that will draw it, like _text_extent().
    """

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)
        font.setBold(bold)

        width = (
            QFontMetricsF(font).horizontalAdvance(text)
            / 1000.0
            * font_size
        )

    except Exception:

        return font_size

    if width <= _INJECTED_TEXT_MAX_WIDTH:
        return font_size

    return font_size * _INJECTED_TEXT_MAX_WIDTH / width


def _inject_text(sidc, svg, texts):

    """
    Draws `texts` ({slot: string}) into `svg` at this icon's own
    positions - see _INJECTED_TEXT for which icons have any and where
    the numbers come from.

    A slot this icon has no position for is dropped rather than guessed
    at, the same way milsymbol itself no-ops an option an icon does not
    define.
    """

    if not texts:
        return svg

    positions = _INJECTED_TEXT.get(sidc[10:16])

    if not positions:
        return svg

    colour = _injected_text_colour(svg)

    elements = []

    for slot, text in sorted(texts.items()):

        text = str(text).strip()

        placement = positions.get(slot)

        if not text or placement is None:
            continue

        x, y, font_size, bold, middle_baseline = placement

        elements.append(
            '<text x="{:g}" y="{:g}" text-anchor="middle" '
            'font-size="{:g}" font-family="Arial"{}{} '
            'stroke="none" fill="{}" >'
            "{}</text>".format(
                x,
                y,
                _fitted_font_size(text, font_size, bold),
                ' font-weight="bold"' if bold else "",
                ' dominant-baseline="middle"' if middle_baseline else "",
                colour,
                _escape_text(text),
            )
        )

    if not elements:
        return svg

    return svg.replace("</svg>", "".join(elements) + "</svg>")


def _escape_text(text):

    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )


_VIEWBOX_PATTERN = re.compile(r'viewBox="([^"]*)"')

_SVG_WIDTH_PATTERN = re.compile(r'\bwidth="[\d.]+"')

_SVG_HEIGHT_PATTERN = re.compile(r'\bheight="[\d.]+"')

_TEXT_ELEMENT_PATTERN = re.compile(r"<text\b([^>]*)>(.*?)</text>", re.S)

_TEXT_X_PATTERN = re.compile(r'\bx="(-?[\d.]+)"')

_TEXT_ANCHOR_PATTERN = re.compile(r'text-anchor="(\w+)"')


def _text_extent(attributes, content):

    """
    (left, right) of one <text> element in the icon's own coordinates.

    Measured with the same Qt font machinery that will draw it, so the
    answer matches what actually lands on the canvas rather than an
    estimate. Returns None if the element is missing anything needed,
    in which case the caller leaves the viewBox alone rather than
    guessing narrow and clipping.
    """

    x = _TEXT_X_PATTERN.search(attributes)
    font_size = _FONT_SIZE_PATTERN.search(attributes)

    if not x or not font_size or not content:
        return None

    try:

        from qgis.PyQt.QtGui import QFont, QFontMetricsF

        font = QFont("Arial", -1)
        font.setPixelSize(1000)
        font.setBold('font-weight="bold"' in attributes)

        width = (
            QFontMetricsF(font).horizontalAdvance(content)
            / 1000.0
            * float(font_size.group(1))
        )

    except Exception:

        return None

    x = float(x.group(1))

    anchor = _TEXT_ANCHOR_PATTERN.search(attributes)
    anchor = anchor.group(1) if anchor else "start"

    if anchor == "middle":
        return x - width / 2.0, x + width / 2.0

    if anchor == "end":
        return x - width, x

    return x, x + width


def _correct_viewbox(sidc, svg):

    """
    Swaps in the corrected horizontal bounds for the icons listed in
    _VIEWBOX_CORRECTIONS - see that table for which and why - then
    widens the result back out over any amplifier text the symbol
    carries.

    That second step is not optional. The correction fixes the ICON's
    own declared box, but milsymbol's viewBox is the union of the icon
    and every amplifier on it, and Table H-XIV's own sonobuoy examples
    put the T and H fields OUTSIDE the circle ("99", "HOT", to the
    upper right). Swapping in the bare icon box alone therefore clipped
    a unique designation clean off - confirmed in a render before this
    was added. Measuring the text back in keeps the circle the same
    size as its siblings, which is the actual defect, while leaving the
    amplifiers exactly where the standard draws them.
    """

    corrected = _VIEWBOX_CORRECTIONS.get(sidc[10:16])

    if not corrected:
        return svg

    current = _VIEWBOX_PATTERN.search(svg)

    if not current:
        return svg

    left, top, width, height = (float(v) for v in corrected.split())

    right = left + width

    for attributes, content in _TEXT_ELEMENT_PATTERN.findall(svg):

        extent = _text_extent(attributes, content.strip())

        if extent is None:
            return svg

        left = min(left, extent[0])
        right = max(right, extent[1])

    width = right - left

    svg = _VIEWBOX_PATTERN.sub(
        'viewBox="{:g} {:g} {:g} {:g}"'.format(left, top, width, height),
        svg,
        count=1
    )

    svg = _SVG_WIDTH_PATTERN.sub(
        'width="{:g}"'.format(width), svg, count=1
    )

    return _SVG_HEIGHT_PATTERN.sub(
        'height="{:g}"'.format(height), svg, count=1
    )
