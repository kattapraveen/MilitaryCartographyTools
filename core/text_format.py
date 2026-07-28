# -*- coding: utf-8 -*-

"""
Shared QFont/QgsTextFormat construction.

Every module that draws label text - the print-layout marginalia
(layout/) and the grid tick/square labels (grid/) - built its own
QFont (and, for PAL labelling/map-grid annotations, QgsTextFormat)
from scratch. This collects that into one place so the handful of
font properties actually used across the plugin (family, size,
bold, italic, underline, colour, opacity, HTML formatting) stay
consistent rather than each caller re-deriving the same few lines.

Military Cartography Tools
"""

from qgis.core import QgsTextFormat
from qgis.PyQt.QtGui import QFont


DEFAULT_FONT_FAMILY = "Arial"


def build_font(size, family=DEFAULT_FONT_FAMILY, bold=False, italic=False, underline=False):

    """
    A QFont with the given properties - used directly by
    QgsLayoutItemLabel.setFont()/QgsLayoutItemScaleBar.setFont()
    (the print-layout marginalia modules), and as the basis for
    build_text_format() below (the grid modules, which need a
    QgsTextFormat rather than a plain QFont).
    """

    font = QFont(family)

    font.setPointSize(size)

    if bold:
        font.setBold(True)

    if italic:
        font.setItalic(True)

    if underline:
        font.setUnderline(True)

    return font


def build_text_format(
    size,
    family=DEFAULT_FONT_FAMILY,
    bold=False,
    italic=False,
    underline=False,
    color=None,
    opacity=None,
    allow_html=False
):

    """
    A QgsTextFormat wrapping build_font() - used where the API
    needs a QgsTextFormat rather than a plain QFont (PAL labelling
    settings, QgsLayoutItemMapGrid annotation text, and the
    QgsLayoutItemLabel/QgsLayoutItemScaleBar marginalia items now
    that their setFont() is deprecated in favour of setTextFormat()).
    """

    text_format = QgsTextFormat()

    text_format.setFont(
        build_font(
            size,
            family=family,
            bold=bold,
            italic=italic,
            underline=underline
        )
    )

    text_format.setSize(
        size
    )

    if color is not None:
        text_format.setColor(color)

    if opacity is not None:
        text_format.setOpacity(opacity)

    if allow_html:
        text_format.setAllowHtmlFormatting(True)

    return text_format
