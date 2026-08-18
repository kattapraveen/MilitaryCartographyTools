# -*- coding: utf-8 -*-

"""
Which MIL-STD edition new symbology layers are built against.

A single plugin-wide setting rather than a per-feature attribute, and the
reason is a QGIS constraint rather than a preference: the Entity dropdown
is a `ValueMap` editor widget, whose map is fixed when the field is
configured. It cannot re-populate itself from another field's value, so a
per-feature edition column would leave the dropdown listing one edition's
vocabulary while the SIDC was built from another's. Edition is therefore
fixed per LAYER, the way `symbol_set` already is, and this setting decides
what a newly added layer gets.

Existing layers are never touched. A layer built before this setting
existed carries no edition in its renderer expression, and
`mct_build_sidc()` treats an absent edition as 2525D - which is exactly
what those layers were built as.

Military Cartography Tools
"""

from qgis.core import QgsSettings

from .sidc import DEFAULT_EDITION, EDITIONS


SETTINGS_KEY = "MilitaryCartographyTools/symbology_edition"

# What the user sees, in the order they should be offered.
EDITION_LABELS = {
    "2525D": "MIL-STD-2525D / APP-6D",
    "2525E": "MIL-STD-2525E / APP-6E",
}


def current_edition():

    """
    The edition new layers are built against. Falls back to 2525D for a
    missing OR unrecognised stored value - a settings file written by a
    later version naming an edition this one does not have should degrade
    to the default rather than raise out of a layer-creation call.
    """

    stored = QgsSettings().value(SETTINGS_KEY, DEFAULT_EDITION)

    if stored not in EDITIONS:
        return DEFAULT_EDITION

    return stored


def set_current_edition(edition):

    """Store `edition` as the default for newly added layers."""

    if edition not in EDITIONS:

        raise KeyError(
            "Unknown edition %r - expected one of %s"
            % (edition, sorted(EDITIONS))
        )

    QgsSettings().setValue(SETTINGS_KEY, edition)


# What gets appended to a layer's name. Short on purpose - these sit in
# the Layers panel next to everything else, so "Air (2525D/6D)" reads at
# a glance where the full "MIL-STD-2525D / APP-6D" would not.
EDITION_SUFFIXES = {
    "2525D": "2525D/6D",
    "2525E": "2525E/6E",
}


def layer_name_for(name, edition):

    """
    `name` with its edition appended, e.g. "Air (2525D/6D)".

    Both editions are suffixed, not just 2525E. The name is what the
    duplicate guard matches on, so an un-suffixed 2525D layer would keep
    blocking its 2525E counterpart - which is the bug this fixes, raised
    by the maintainer 2026-08-18: inserting Air under APP-6D, switching
    the setting to 6E and adding again just reported "already exists".
    Suffixing both also means a layer says which edition it is without
    anyone opening its renderer.
    """

    return "%s (%s)" % (name, EDITION_SUFFIXES.get(edition, edition))


def edition_label(edition):

    """A user-facing name for `edition`, for menus and layer names."""

    return EDITION_LABELS.get(edition, edition)
