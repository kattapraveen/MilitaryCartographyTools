# -*- coding: utf-8 -*-

"""
Shared hypsometric ("layer tint") colour ramp for the terrain/
generators (Tanaka contours' per-segment colour, hypsometric tint's
per-pixel colour) - both need the same blue-below-sea-level,
green-through-white-above-it convention, normalised the same way.

Military Cartography Tools
"""


# Standard hypsometric ("layer tint") colour convention used on
# topographic/military maps: shades of blue below sea level, then
# green -> yellow -> brown -> red -> white with increasing elevation
# above it (white standing in for permanent snow/ice at the highest
# bands). Defined as (fraction 0-1, colour) rather than fixed
# absolute elevations - a single generation typically only spans a
# few hundred metres of local relief, so a fixed global scale (e.g.
# 0-5500m) would leave any one run stuck inside one narrow slice of
# it and read as basically monochrome (confirmed live: a real DEM
# clip came out entirely brown against the first, fixed-elevation
# version of this ramp). Stretched per-generation instead, against
# that output's own min/max elevation - see hypsometric_color() - so
# every run shows the full ramp regardless of the area's absolute
# elevation.
SEA_RAMP = (
    (0.0, (168, 218, 250)),
    (0.35, (39, 106, 165)),
    (0.7, (13, 55, 117)),
    (1.0, (7, 21, 59)),
)

LAND_RAMP = (
    (0.0, (57, 130, 69)),
    (0.1, (104, 164, 79)),
    (0.2, (166, 190, 101)),
    (0.3, (216, 194, 111)),
    (0.4, (177, 132, 87)),
    (0.55, (150, 100, 80)),
    (0.7, (186, 129, 116)),
    (0.85, (222, 190, 176)),
    (1.0, (255, 255, 255)),
)


def _interpolate_stops(elevation, stops):

    """
    Linear-interpolate an (r, g, b) colour between the two stops
    bracketing elevation, clamping to the nearest end colour beyond
    either edge rather than extrapolating.
    """

    if elevation <= stops[0][0]:
        return stops[0][1]

    if elevation >= stops[-1][0]:
        return stops[-1][1]

    for (elev_a, color_a), (elev_b, color_b) in zip(stops, stops[1:]):

        if elev_a <= elevation <= elev_b:

            ratio = (elevation - elev_a) / (elev_b - elev_a)

            return tuple(
                round(a + (b - a) * ratio)
                for a, b in zip(color_a, color_b)
            )

    return stops[-1][1]


def _clamp01(value):

    return max(0.0, min(1.0, value))


def hypsometric_color(elevation, min_elevation, max_elevation):

    """
    (r, g, b) for a given elevation, normalised against
    min_elevation/max_elevation - the actual range present in this
    generation's own output, not a fixed global scale (see the
    SEA_RAMP/LAND_RAMP comment above for why).

    A real coastline (min_elevation < 0, i.e. this generation's own
    output actually dips below sea level) still anchors land and sea
    exactly at 0, each normalised over its own side independently
    (0..max_elevation for land, min_elevation..0 for sea) - elevation
    relative to sea level still means something concrete whenever sea
    level is actually present in the data. Otherwise (the common
    case: an inland area with no negative elevations at all) the
    whole output is land, so the full LAND_RAMP is stretched across
    min_elevation..max_elevation instead of forcing it to start at 0,
    guaranteeing the full ramp is visible regardless of how high up
    that elevation range happens to sit.
    """

    if min_elevation < 0:

        if elevation < 0:

            depth_span = max(-min_elevation, 1e-6)

            fraction = _clamp01(-elevation / depth_span)

            return _interpolate_stops(fraction, SEA_RAMP)

        height_span = max(max_elevation, 1e-6)

        fraction = _clamp01(elevation / height_span)

        return _interpolate_stops(fraction, LAND_RAMP)

    span = max(max_elevation - min_elevation, 1e-6)

    fraction = _clamp01(
        (elevation - min_elevation) / span
    )

    return _interpolate_stops(fraction, LAND_RAMP)
