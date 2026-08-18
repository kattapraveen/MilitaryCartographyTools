# -*- coding: utf-8 -*-

"""
Generates military_symbology/sidc_2525e.py from the MIL-STD-2525E tables.

NOT shipped with the plugin and NOT imported by it - a developer tool, run
by hand when the source tables change. See docs/roadmap.md's Phase 12 entry.

Source: reference/milstandard-e/tsv-tables/, a copy of
https://github.com/spatialillusions/milstandard-e (MIT), which transcribes
the standard's own tables - Entity / Entity Type / Entity Subtype / Code /
Remarks, exactly the columns the printed tables use. reference/ is
gitignored, so this script is the reproducible part, not its input.

Usage:
    python3 tools/extract_2525e_vocabulary.py > military_symbology/sidc_2525e.py
"""

import csv
import glob
import os
import re
import sys


TSV_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reference", "milstandard-e", "tsv-tables",
)

# Table basename -> the plugin's own symbol_set key (sidc.py's SYMBOL_SETS).
# Control Measures is deliberately absent: Appendix H is built as hand-drawn
# geometry in this plugin, not from an entity vocabulary, so its 561 rows
# have no dict to land in. Dismounted Individual has no layer yet either.
SYMBOL_SETS = {
    "Activities": "activities",
    "Air": "air",
    "Air missile": "air_missile",
    "Cyberspace": "cyberspace",
    "Land civilian": "land_civilian",
    "Land equipment": "land_equipment",
    "Land installation": "land_installation",
    "Land unit": "ground_unit",
    "Mine warfare": "mine_warfare",
    "Sea subsurface": "subsurface",
    "Sea surface": "sea_surface",
    "Space": "space",
    "Space missile": "space_missile",
}

# SIGINT is one vocabulary shared across five symbol sets - the standard
# gives the same entity/modifier tables to Space/Air/Land/Sea Surface/
# Subsurface SIGINT, and sidc.py already models that with five keys
# pointing at one dict. The source has a single "Signals intelligence"
# table, so it is fanned out here the same way.
#
# Leaving these out is what broke every SIGINT symbol under 2525E: the
# layer fell back to 2525D labels for its dropdowns, but build_sidc()
# looked the chosen entity up in a 2525E vocabulary that had no SIGINT
# entry at all, raised KeyError, and mct_build_sidc() returned the error
# text as a string - which milsymbol then drew as garbage rather than
# failing visibly. Found by the maintainer's smoke test, 2026-08-18.
SHARED_TABLES = {
    "Signals intelligence": (
        "sigint_space",
        "sigint_air",
        "sigint_land",
        "sigint_sea_surface",
        "sigint_subsurface",
    ),
}

# Rows the standard prints as placeholders rather than symbols. {Disused}
# marks a code 2525E retired from 2525D - it must NOT be offered to a user,
# which is the whole reason this generator reads Remarks at all.
PLACEHOLDER = re.compile(r"\{\s*(disused|reserved)", re.I)


def slug(text):

    text = text.replace("&", " and ")
    text = re.sub(r"\(.*?\)", " ", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)

    return text.strip("_").lower()


def read_table(path):

    """[(path_parts, code, remarks)] for one TSV, placeholders dropped."""

    with open(path, encoding="utf-8", errors="replace") as handle:
        rows = list(csv.reader(handle, delimiter="\t"))

    header = rows[0]

    if "Code" not in header:
        return []

    code_at = header.index("Code")
    out = []

    for row in rows[1:]:

        if len(row) <= code_at or not row[code_at].strip():
            continue

        parts = [cell.strip() for cell in row[:code_at] if cell.strip()]

        if not parts or any(PLACEHOLDER.search(cell) for cell in parts):
            continue

        remarks = row[code_at + 1].strip() if len(row) > code_at + 1 else ""

        if PLACEHOLDER.search(remarks):
            continue

        out.append((parts, row[code_at].strip(), remarks))

    return out


def unique_keys(entries, specific_first=False):

    """
    A key per entry: the most specific name alone where that is unambiguous
    inside this symbol set, otherwise widened through the hierarchy
    ("light" -> "machine_gun_light"). Matches how sidc.py's hand-written
    2525D dicts already read, so the two are comparable by eye.

    `specific_first` because the two kinds of table are laid out in
    OPPOSITE directions. Entity tables run general to specific across the
    columns (Entity, Entity Type, Entity Subtype), so the last column is
    the name. Modifier tables run the other way (First Modifier, Category),
    so the FIRST column is the name and the second is its grouping. Reading
    both the same way produced keys like "mobility" and "robotic_mobility"
    where "robotic" was meant - caught by a test, not by inspection.
    """

    keys = {}
    taken = set()

    for parts, code, _ in entries:

        ordered = list(reversed(parts)) if specific_first else parts

        for depth in range(1, len(ordered) + 1):

            candidate = slug("_".join(ordered[-depth:][::-1] if specific_first
                                      else ordered[-depth:]))

            if candidate and candidate not in taken:
                break

        else:
            candidate = "%s_%s" % (candidate, code)

        taken.add(candidate)
        keys[code] = candidate

    return keys


def label_for(parts, specific_first, hierarchical=False):

    """
    The text a user reads in a dropdown. Entity tables run general to
    specific, so the last column is the name and any earlier ones are its
    group; modifier tables run the other way. Either way the NAME is what
    is shown, with its group appended in parentheses only when the name
    alone would be ambiguous out of context ("Light", "Other").
    """

    name = parts[0] if specific_first else parts[-1]
    rest = parts[1:] if specific_first else parts[:-1]

    # A row the standard marks "Reserved for hierarchical purposes" is a
    # GROUP HEADER, and its printed name is often the bare noun its own
    # children qualify - Land Installation prints 121400 "Water Supply"
    # above 121410 "Water" and 121411 "Water Treatment". Faithful, but
    # three near-identical rows in one dropdown. "(Generic)" is the
    # convention the hand-written 2525D labels already use for exactly
    # this, so the two editions read the same way.
    # Raised by the maintainer on the 1.0.4 smoke test, 2026-08-18.
    if hierarchical:
        return "%s (Generic)" % name

    if len(name) > 3 or not rest:
        return name

    return "%s (%s)" % (name, rest[0])


def emit_labels(title, tables, specific_first=False):

    print("%s = {" % title)

    for label in sorted(tables):

        entries = tables[label]

        if not entries:
            continue

        print('    "%s": {' % label)

        keys = unique_keys(entries, specific_first)

        for parts, code, remarks in entries:

            key = keys[code]
            hierarchical = "hierarchical" in remarks.lower()
            text = label_for(
                parts, specific_first, hierarchical
            ).replace('"', "'")
            suppress = (
                "  # nosec B105 # pragma: allowlist secret"
                if "secret" in key else ""
            )

            print('        "%s": "%s",%s' % (key, text, suppress))

        print("    },")

    print("}")
    print()


def emit(title, tables, specific_first=False):

    print("%s = {" % title)

    for label in sorted(tables):

        entries = tables[label]

        if not entries:
            continue

        print('    "%s": {' % label)

        keys = unique_keys(entries, specific_first)

        for parts, code, remarks in entries:

            key = keys[code]

            # "Secret" here is the US Secret Service, a real entity name in
            # both editions - Bandit's B105 and detect-secrets read the key
            # as a credential. Emitted by the generator rather than added by
            # hand afterwards, because this file is regenerated: a manual
            # fix would vanish on the next run and the finding would come
            # back on upload, which is exactly how 1.0.2 was burned.
            if "secret" in key:
                suppress = "  # nosec B105 # pragma: allowlist secret"
            else:
                suppress = ""

            comment = "  # %s" % remarks if remarks and not suppress else ""
            print('        "%s": "%s",%s%s' % (key, code, comment, suppress))

        print("    },")

    print("}")
    print()


def main():

    entities = {}
    sector1 = {}
    sector2 = {}

    for path in sorted(glob.glob(os.path.join(TSV_DIR, "*.tsv"))):

        name = os.path.basename(path)[:-4]

        if name.endswith(" sector 1"):
            base, bucket = name[:-9], sector1
        elif name.endswith(" sector 2"):
            base, bucket = name[:-9], sector2
        else:
            base, bucket = name, entities

        if base == "Common Modifiers":
            bucket["common"] = read_table(path)
            continue

        shared = SHARED_TABLES.get(base)

        if shared is not None:

            entries = read_table(path)

            for key in shared:
                bucket[key] = entries

            continue

        key = SYMBOL_SETS.get(base)

        if key is None:
            continue

        bucket[key] = read_table(path)

    print("# -*- coding: utf-8 -*-")
    print()
    print('"""')
    print("MIL-STD-2525E entity and sector-modifier vocabularies.")
    print()
    print("GENERATED by tools/extract_2525e_vocabulary.py - do not hand-edit;")
    print("re-run the generator instead. Source tables are described there.")
    print()
    print("Separate from sidc.py's 2525D vocabularies on purpose: the two")
    print("editions disagree on more than spelling. 2525E retires codes")
    print("outright ({Disused} in the source tables, dropped here), and")
    print("renames others in place - 121301 is Airport/Air Base in 2525D and")
    print("Aerial Port of Debarkation/Embarkation in 2525E, same code.")
    print()
    print("COMMON modifiers are a parallel namespace, not a fallback: SIDC")
    print("digit 21 selects the common sector-1 table over the symbol set's")
    print("own, and digit 22 does the same for sector 2. That is why the")
    print('sector dicts below carry a "common" entry alongside the per-set')
    print("ones, and why its codes are THREE digits (100-166) where every")
    print("other code here is two: the standard prints the selecting flag")
    print("as part of the code. Do not strip it to two digits.")
    print()
    print("Military Cartography Tools")
    print('"""')
    print()

    emit("ENTITIES_2525E", entities)
    emit("MODIFIERS_SECTOR1_2525E", sector1, specific_first=True)
    emit("MODIFIERS_SECTOR2_2525E", sector2, specific_first=True)

    # Labels are generated alongside the codes rather than hand-written
    # per layer the way the 2525D ones are: 989 entities is well past
    # what is sensible to transcribe, and the source tables already hold
    # the standard's own wording.
    emit_labels("ENTITY_LABELS_2525E", entities)
    emit_labels("SECTOR1_LABELS_2525E", sector1, specific_first=True)
    emit_labels("SECTOR2_LABELS_2525E", sector2, specific_first=True)


if __name__ == "__main__":
    main()
