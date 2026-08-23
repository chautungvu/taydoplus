#!/usr/bin/env python3
"""
Fetch a remote M3U playlist and sync its channel entries into an existing
output .m3u file.

Behavior: for every group-title found in the freshly fetched playlist, any
existing entries in the output file that belong to that same group are
removed first, then the freshly fetched entries for that group are written
in. This means channels get fully refreshed (URLs, names, etc. always match
the latest source) instead of being skipped forever once a URL has been
seen once. Entries belonging to groups NOT present in the source (e.g.
channels you added manually, or from a different script/source sharing the
same output file) are left untouched.

Usage:
    python scripts/filter_playlist.py

Config via environment variables (all optional, defaults shown):
    SOURCE_URL   = https://thcoban.github.io/ththethao/ttthethao.m3u
    OUTPUT_FILE  = iptvviptdplus.m3u
"""

import os
import re
import sys
import urllib.request

SOURCE_URL = os.environ.get(
    "SOURCE_URL",
    "https://thcoban.github.io/ththethao/ttthethao.m3u",
)
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "iptvviptdplus.m3u")

GROUP_TITLE_RE = re.compile(r'group-title="([^"]*)"')


def fetch_playlist(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_entries(playlist_text: str):
    """
    Yield each channel entry as a list of raw lines: the #EXTINF line plus
    every following line (EXTVLCOPT / KODIPROP / the stream URL) up to the
    next #EXTINF or end of file. This preserves user-agent headers, DRM
    keys, etc. that belong to a channel.
    """
    lines = playlist_text.splitlines()
    entries = []
    current = None

    for line in lines:
        if line.startswith("#EXTINF"):
            if current is not None:
                entries.append(current)
            current = [line]
        elif current is not None:
            current.append(line)

    if current is not None:
        entries.append(current)

    return entries


def entry_group(entry_lines):
    """The group-title of an entry, or None if it doesn't have one."""
    match = GROUP_TITLE_RE.search(entry_lines[0])
    return match.group(1) if match else None


def entry_key(entry_lines):
    """
    A key used to de-duplicate entries within a single fetch (in case the
    source itself lists the same channel twice). Uses the stream URL (the
    last non-empty line of the entry).
    """
    non_empty = [ln.strip() for ln in entry_lines if ln.strip() != ""]
    return non_empty[-1] if non_empty else None


def load_existing_entries(path: str):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        existing_text = f.read()
    return parse_entries(existing_text)


def main():
    print(f"Fetching playlist from: {SOURCE_URL}")
    try:
        playlist_text = fetch_playlist(SOURCE_URL)
    except Exception as exc:
        print(f"ERROR: failed to fetch playlist: {exc}", file=sys.stderr)
        sys.exit(1)

    fetched_entries = parse_entries(playlist_text)
    print(f"Total entries parsed from source: {len(fetched_entries)}")

    # De-duplicate fetched entries by stream URL, in case the source
    # repeats a channel.
    seen_keys = set()
    deduped_fetched = []
    for e in fetched_entries:
        key = entry_key(e)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_fetched.append(e)

    fetched_groups = {entry_group(e) for e in deduped_fetched}
    print(f"Groups in fetched playlist: {sorted(g for g in fetched_groups if g)}")

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)

    existing_entries = load_existing_entries(OUTPUT_FILE)

    # Keep only existing entries whose group is NOT being refreshed by this
    # fetch (e.g. manually added channels, or channels from a different
    # group/source sharing the same output file).
    kept_entries = [e for e in existing_entries if entry_group(e) not in fetched_groups]

    removed_count = len(existing_entries) - len(kept_entries)
    print(f"Removed {removed_count} existing entries whose group is being refreshed")

    final_entries = kept_entries + deduped_fetched

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for entry_lines in final_entries:
            cleaned = [ln for ln in entry_lines if ln.strip() != ""]
            f.write("\n".join(cleaned) + "\n")

    print(f"Wrote {len(final_entries)} total entries to {OUTPUT_FILE} "
          f"({len(kept_entries)} kept unchanged, {len(deduped_fetched)} refreshed from source)")


if __name__ == "__main__":
    main()
