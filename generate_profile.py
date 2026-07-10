#!/usr/bin/env python3
"""Generate profile.svg — neofetch-style GitHub profile card for pendakwahteknologi.

Left column:  procedurally drawn synthwave scene (retro sun, starfield,
              perspective grid) matching the Pendakwah Teknologi logo motif.
Right column: dotted-leader system-info lines with live GitHub stats.
Wrapped in a macOS-terminal-window frame. Pure stdlib — no dependencies.

Run locally:   GH_TOKEN=$(gh auth token) python3 generate_profile.py
In Actions:    GH_TOKEN=${{ secrets.GITHUB_TOKEN }} python3 generate_profile.py
"""

import json
import os
import sys
import urllib.request
from datetime import date
from xml.sax.saxutils import escape

USER = "pendakwahteknologi"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "profile.svg")
GITHUB_JOINED = date(2021, 5, 13)

# ---- theme -----------------------------------------------------------------
BG = "#0d1117"
BORDER = "#2d1b4e"
TITLE = "#8b949e"
KEY = "#ff4fd8"       # brand magenta
HEADER = "#53e0ff"    # brand cyan
VALUE = "#e6edf3"
DIM = "#484f58"
BULLET = "#9d5cff"    # brand purple

STAR = "#8b79c7"
GRID_V = "#37c8f0"    # radiating grid lines
GRID_H = "#9d5cff"    # horizontal grid lines
# retrowave sun gradient, top -> bottom
SUN_STOPS = [(255, 211, 25), (255, 144, 31), (255, 41, 117), (242, 34, 255)]

FONT = "'SFMono-Regular',Consolas,'Liberation Mono',Menlo,monospace"
FONT_SIZE = 13
CHAR_W = 7.85         # advance width of 13px monospace
LINE_H = 19
CHAR_ASPECT = CHAR_W / LINE_H

ART_COLS = 54
INFO_W = 52           # info column width in chars (for dot leaders)


# ---- github data -----------------------------------------------------------
def gh(path):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": USER},
    )
    tok = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if tok:
        req.add_header("Authorization", f"Bearer {tok}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_stats():
    user = gh(f"/users/{USER}")
    repos, page = [], 1
    while True:
        batch = gh(f"/users/{USER}/repos?per_page=100&page={page}")
        repos += batch
        if len(batch) < 100:
            break
        page += 1
    langs = {}
    for r in repos:
        if r.get("language"):
            langs[r["language"]] = langs.get(r["language"], 0) + 1
    try:
        commits = gh(f"/search/commits?q=author:{USER}")["total_count"]
    except Exception:
        commits = None
    return {
        "followers": user["followers"],
        "repos": user["public_repos"],
        "stars": sum(r["stargazers_count"] for r in repos),
        "forks": sum(r["forks_count"] for r in repos),
        "commits": commits,
        "top_langs": [k for k, _ in sorted(langs.items(), key=lambda kv: -kv[1])[:3]],
    }


def uptime():
    today = date.today()
    months = (today.year - GITHUB_JOINED.year) * 12 + today.month - GITHUB_JOINED.month
    if today.day < GITHUB_JOINED.day:
        months -= 1
    y, m = divmod(months, 12)
    return f"{y} years, {m} month{'s' if m != 1 else ''}"


# ---- synthwave scene -------------------------------------------------------
def lerp_color(stops, t):
    t = min(max(t, 0.0), 1.0) * (len(stops) - 1)
    i = min(int(t), len(stops) - 2)
    f = t - i
    (r1, g1, b1), (r2, g2, b2) = stops[i], stops[i + 1]
    return "#{:02x}{:02x}{:02x}".format(
        round(r1 + (r2 - r1) * f), round(g1 + (g2 - g1) * f), round(b1 + (b2 - b1) * f)
    )


def synthwave_art(cols=ART_COLS, rows=26):
    """Retro sun rising over a perspective grid, as rows of (char, color)."""
    grid = [[(" ", None) for _ in range(cols)] for _ in range(rows)]
    hz = round(rows * 0.62)               # horizon row
    cx = (cols - 1) / 2
    r = 10.0                              # sun radius, in row units (visual)
    gaps = {1, 3, 5}                      # slat gaps: rows above horizon

    # starfield (deterministic hash sprinkle)
    for y in range(hz):
        for x in range(cols):
            h = ((x * 73856093) ^ (y * 19349663)) % 883
            if h < 30:
                grid[y][x] = (".", STAR)
            elif h < 38:
                grid[y][x] = ("*", STAR)

    # sun: semicircle centered on the horizon; slat rows dim to keep silhouette
    for y in range(hz):
        dy = hz - y                       # rows above horizon (>= 1)
        if dy > r:
            continue
        t = 1 - dy / r                    # 0 at top -> 1 at horizon
        color = lerp_color(SUN_STOPS, t)
        slat = dy in gaps
        if slat:                          # dimmed band: silhouette stays whole
            color = "#{:02x}{:02x}{:02x}".format(
                *(round(int(color[i:i + 2], 16) * 0.55) for i in (1, 3, 5)))
        for x in range(cols):
            dxu = (x - cx) * CHAR_ASPECT  # visual x-distance in row units
            d = (dxu * dxu + dy * dy) ** 0.5
            if d <= r:
                ch = "=" if slat else ("@" if d <= r - 1.0 else "%")
                grid[y][x] = (ch, color)

    # perspective grid below horizon
    spacing = 5.4
    h_rows = {2, 5, 9}                    # horizontal lines: offsets below horizon
    last = rows - 1
    for y in range(hz + 1, rows):
        s = (y - hz) / (last - hz)
        is_h = (y - hz) in h_rows or y == last
        for x in range(cols):
            slope = None
            for k in range(-8, 9):
                pos = cx + k * spacing * (0.30 + 0.70 * s)
                if abs(x - pos) < 0.5:
                    slope = k
                    break
            if slope is not None:
                ch = "+" if is_h else ("|" if slope == 0 else ("\\" if slope > 0 else "/"))
                grid[y][x] = (ch, GRID_V)
            elif is_h:
                grid[y][x] = ("=", GRID_H)

    # horizon line
    grid[hz] = [("=", GRID_H) for _ in range(cols)]
    return grid


# ---- info column -----------------------------------------------------------
def kv(key, value):
    """'. Key: ...dots... value'  right-aligned to INFO_W chars."""
    left = f" {key}: "
    dots = INFO_W - 1 - len(left) - len(value) - 1
    return [
        (".", BULLET), (left, KEY),
        ("." * max(dots, 2) + " ", DIM), (value, VALUE),
    ]


def header(title):
    bar = "─" * (INFO_W - len(title) - 4)
    return [("── ", DIM), (title + " ", HEADER), (bar, DIM)]


def blank():
    return []


def info_lines(s):
    commits = f"{s['commits']}+" if s["commits"] else "a lot"
    return [
        [(f"adil@{USER}", HEADER),
         (" " + "─" * (INFO_W - len(USER) - 6), DIM)],
        kv("OS", "macOS, Android, Linux"),
        kv("Host", "Pendakwah Teknologi"),
        kv("Locale", "Malaysia (ms_MY.UTF-8)"),
        kv("Shell", "zsh + Claude Code"),
        kv("Uptime", uptime() + " on GitHub"),
        blank(),
        kv("Lang.Programming", "Python, Kotlin, Swift"),
        kv("Lang.GitHub", ", ".join(s["top_langs"])),
        kv("Lang.Real", "Bahasa Melayu, English"),
        blank(),
        kv("Focus.AI", "agents, on-device LLMs"),
        kv("Focus.Mobile", "Android Compose, iOS"),
        kv("Focus.Infra", "homelab, NAS, LoRa mesh"),
        blank(),
        header("Contact"),
        kv("Web", "pendakwah.tech"),
        kv("YouTube", "@pendakwahteknologi"),
        kv("X", "@PendakwahTekno"),
        kv("Facebook", "pendakwahteknologi"),
        kv("TikTok", "@pendakwahteknologi"),
        blank(),
        header("GitHub Stats"),
        kv("Repos", f"{s['repos']} public"),
        kv("Stars", f"{s['stars']} | Forks: {s['forks']}"),
        kv("Commits", f"{commits} | Followers: {s['followers']}"),
    ]


# ---- svg -------------------------------------------------------------------
def tspan(text, color=None):
    fill = f' fill="{color}"' if color else ""
    return f"<tspan{fill}>{escape(text)}</tspan>"


def render(art, info):
    pad_x, top = 34, 74
    art_w = ART_COLS * CHAR_W
    info_x = pad_x + art_w + 34
    width = round(info_x + INFO_W * CHAR_W + pad_x)
    n_lines = max(len(art), len(info))
    height = round(top + n_lines * LINE_H + 30)
    art_top = top + max(0, (len(info) - len(art)) // 2) * LINE_H

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Pendakwah Teknologi — terminal profile card">',
        # Blink dropped xml:space support; CSS pre keeps run-length spaces intact
        "<style>text{white-space:pre}</style>",
        f'<rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="14" '
        f'fill="{BG}" stroke="{BORDER}" stroke-width="2"/>',
        # traffic lights + title bar
        '<circle cx="30" cy="28" r="7" fill="#ff5f57"/>',
        '<circle cx="54" cy="28" r="7" fill="#febc2e"/>',
        '<circle cx="78" cy="28" r="7" fill="#28c840"/>',
        f'<text x="{width / 2}" y="33" text-anchor="middle" font-family={FONT!r} '
        f'font-size="12" fill="{TITLE}">adil@{USER} — -zsh</text>',
        f'<line x1="1" y1="48" x2="{width - 1}" y2="48" stroke="{BORDER}" stroke-width="1"/>',
        f'<g font-family={FONT!r} font-size="{FONT_SIZE}" xml:space="preserve">',
    ]

    # ascii art: merge same-color runs into tspans
    for i, row in enumerate(art):
        y = art_top + i * LINE_H
        runs, cur_c, cur_t = [], None, ""
        for ch, c in row:
            c = None if ch == " " else c
            if c == cur_c:
                cur_t += ch
            else:
                if cur_t:
                    runs.append(tspan(cur_t, cur_c))
                cur_c, cur_t = c, ch
        if cur_t:
            runs.append(tspan(cur_t, cur_c))
        out.append(f'<text x="{pad_x}" y="{y}">{"".join(runs)}</text>')

    for i, segs in enumerate(info):
        if not segs:
            continue
        y = top + i * LINE_H
        spans = "".join(tspan(t, c) for t, c in segs)
        out.append(f'<text x="{info_x}" y="{y}">{spans}</text>')

    out += ["</g>", "</svg>"]
    return "\n".join(out)


def main():
    stats = fetch_stats()
    print(f"stats: {stats}", file=sys.stderr)
    svg = render(synthwave_art(), info_lines(stats))
    with open(OUT, "w") as f:
        f.write(svg)
    print(f"wrote {OUT} ({len(svg) / 1024:.0f} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
