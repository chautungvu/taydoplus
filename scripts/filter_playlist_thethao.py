#!/usr/bin/env python3
"""
Fetch a remote M3U playlist and APPEND its channel entries to the bottom of
an existing output .m3u file (the output file's own existing content is
left untouched -- only new, not-yet-seen channels are added to the end).

Unlike the FPT Play version of this script, this one does NOT filter by
group-title -- every channel entry in the source playlist is considered a
candidate for appending. Re-runs skip channels that are already present in
the output file (matched by stream URL), so nothing gets duplicated.

Usage:
    python scripts/filter_playlist.py

Config via environment variables (all optional, defaults shown):
    SOURCE_URL   = https://thcoban.github.io/ththethao/ttthethao.m3u
    OUTPUT_FILE  = iptvviptdplus.m3u
"""

import os
import sys
import urllib.request

SOURCE_URL = os.environ.get(
    "SOURCE_URL",
    "https://thcoban.github.io/ththethao/ttthethao.m3u",
)
OUTPUT_FILE = os.environ.get("OUTPUT_FILE", "iptvviptdplus.m3u")


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


def entry_key(entry_lines):
    """
    A key used to detect whether an entry is already present in the output
    file, so re-runs don't keep appending duplicate copies of the same
    channel. Uses the stream URL (the last non-empty line of the entry,
    which is typically the .m3u8/.ts link) since that's the unique part.
    """
    non_empty = [ln.strip() for ln in entry_lines if ln.strip() != ""]
    return non_empty[-1] if non_empty else None


def load_existing_keys(path: str):
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        existing_text = f.read()
    existing_entries = parse_entries(existing_text)
    return {entry_key(e) for e in existing_entries if entry_key(e)}


def main():
    print(f"Fetching playlist from: {SOURCE_URL}")
    try:
        playlist_text = fetch_playlist(SOURCE_URL)
    except Exception as exc:
        print(f"ERROR: failed to fetch playlist: {exc}", file=sys.stderr)
        sys.exit(1)

    entries = parse_entries(playlist_text)

    print(f"Total entries parsed: {len(entries)}")

    os.makedirs(os.path.dirname(OUTPUT_FILE) or ".", exist_ok=True)

    file_exists = os.path.exists(OUTPUT_FILE)
    existing_keys = load_existing_keys(OUTPUT_FILE)

    # Only append channels that aren't already in the file, so repeated
    # runs don't pile up duplicate copies of the same channel.
    new_entries = [e for e in entries if entry_key(e) not in existing_keys]

    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        if not file_exists:
            f.write("#EXTM3U\n")
        for entry_lines in new_entries:
            cleaned = [ln for ln in entry_lines if ln.strip() != ""]
            f.write("\n".join(cleaned) + "\n")

    print(f"Appended {len(new_entries)} new entries to {OUTPUT_FILE} "
          f"({len(entries) - len(new_entries)} already present, skipped)")


if __name__ == "__main__":
    main()
