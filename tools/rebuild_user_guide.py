# -*- coding: utf-8 -*-

"""
Rebuilds docs/user-guide-offline.html from docs/user-guide.dc.html.

NOT shipped with the plugin and NOT imported by it - a developer tool, run
by hand after editing the guide's source. See docs/roadmap.md's 1.4.0 entry.

The offline file is a bundle: a small loader, the guide's own runtime and
React inlined as gzip+base64 in a manifest, and the page itself as a JSON
string. Editing the guide's text changes only that page, so this swaps the
page in and keeps everything else - which reproduces Claude Design's own
bundler output exactly (proved against the 1.4.0 build: identical rendered
text and DOM).

It also marks the manifest line for detect-secrets, which the QGIS Plugin
Repository runs on every upload. The three inlined libraries are long
base64 strings and read as "Base64 High Entropy String" otherwise. The
marker has to share the flagged line - a "nextline" marker must sit alone
on the line above, which here is inside the <script> and would break its
JSON. Run this again after any rebuild in Claude Design to restore it.

Usage:
    python3 tools/rebuild_user_guide.py
"""

import json
import os
import re


DOCS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
)
SOURCE = os.path.join(DOCS_DIR, "user-guide.dc.html")
BUNDLE = os.path.join(DOCS_DIR, "user-guide-offline.html")

ALLOWLIST = "<!-- pragma: allowlist secret -->"


def main():

    with open(SOURCE, encoding="utf-8") as f:
        page = f.read()

    with open(BUNDLE, encoding="utf-8") as f:
        bundle = f.read()

    template = re.search(
        r'(<script type="__bundler/template">\n)(.*?)(\n\s*</script>)',
        bundle,
        re.S,
    )

    if template is None:
        raise SystemExit(f"No page template found in {BUNDLE}")

    # The source loads its runtime from ./support.js; the bundle carries it
    # inline under a UUID, which the current page template already names.
    support_uuid = re.search(
        r'<script src=\\"([0-9a-f-]{36})\\">',
        template.group(2),
    ).group(1)

    page, count = re.subn(
        r'<script src="\./support\.js">',
        f'<script src="{support_uuid}">',
        page,
        count=1,
    )

    if count != 1:
        raise SystemExit(f"No ./support.js reference found in {SOURCE}")

    # The bundler lifts the thumbnail into the loader shell, which already
    # has it, and drops it from the page.
    page = re.sub(
        r'<template id="__bundler_thumbnail">.*?</template>',
        "",
        page,
        count=1,
        flags=re.S,
    )

    encoded = json.dumps(page, ensure_ascii=False).replace("</", "<\\u002F")

    bundle = (
        bundle[:template.start(2)] + encoded + bundle[template.end(2):]
    )

    if ALLOWLIST not in bundle:

        manifest = re.search(
            r'(<script type="__bundler/manifest">\n)([^\n]*)(\n\s*</script>)',
            bundle,
        )

        if manifest is None:
            raise SystemExit(f"No manifest found in {BUNDLE}")

        bundle = (
            bundle[:manifest.start(3)]
            + "</script>" + ALLOWLIST
            + bundle[manifest.end(3):]
        )

    with open(BUNDLE, "w", encoding="utf-8") as f:
        f.write(bundle)

    print(f"Rebuilt {BUNDLE}")


if __name__ == "__main__":
    main()
