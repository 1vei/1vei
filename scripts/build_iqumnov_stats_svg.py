#!/usr/bin/env python3
"""Draw profile README stats using GitHub GraphQL API."""

import base64
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone

API = "https://api.github.com/graphql"

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date weekday } }
      }
    }
  }
}
"""

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(SCRIPT_DIR, "fonts")

def face(filename, weight):
    font_path = os.path.join(FONT_DIR, filename)
    with open(font_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return (f"@font-face{{font-family:JBMono;font-style:normal;"
            f"font-weight:{weight};font-display:block;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2')}}")

def font_text():
    return face("jbmono-400.woff2", 400) + face("jbmono-600.woff2", 600)

WIDTH = 620
REVEAL = 1.30
MONO = "JBMono,ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"

LIGHT = dict(data="#6e7681", emph="#424a53", dim="#8c959f", rule="#d8dee4", surface="#ffffff")
DARK = dict(data="#c9d1d9", emph="#f0f6fc", dim="#8b949e", rule="#30363d", surface="#0d1117")

def style():
    def block(t):
        return (f".d-f{{fill:{t['data']}}}.d-s{{stroke:{t['data']}}}"
                f".e-f{{fill:{t['emph']}}}.m-f{{fill:{t['dim']}}}"
                f".u-s{{stroke:{t['rule']}}}.r{{stroke:{t['surface']}}}")
    return (f"<style>{font_text()}"
            f"{block(LIGHT)}.w{{fill:{LIGHT['data']};opacity:.13}}"
            f"@media(prefers-color-scheme:dark){{{block(DARK)}"
            f".w{{fill:{DARK['data']};opacity:.16}}}}</style>")

def head(w, h):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" fill="none" font-family="{MONO}">'
            + style())

def fade(delay, dur=0.45):
    return (f'<animate attributeName="opacity" from="0" to="1" '
            f'begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>')

def wipe(cid, x, y, w, h, delay, dur=REVEAL):
    clip = (f'<clipPath id="{cid}"><rect x="{x}" y="{y}" height="{h}" width="0">'
            f'<animate attributeName="width" from="0" to="{w}" '
            f'begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/></rect></clipPath>')
    cursor = (f'<rect y="{y}" width="2" height="{h}" class="d-f" opacity="0">'
              f'<animate attributeName="x" from="{x}" to="{x + w}" '
              f'begin="{delay:.2f}s" dur="{dur}s" fill="freeze"/>'
              f'<set attributeName="opacity" to="0.55" begin="{delay:.2f}s"/>'
              f'<set attributeName="opacity" to="0" '
              f'begin="{delay + dur:.2f}s"/></rect>')
    return clip, cursor

def label(x, y, text, size=11, cls="m-f", anchor="start", extra=""):
    a = f' text-anchor="{anchor}"' if anchor != "start" else ""
    return (f'<text x="{x}" y="{y}" class="{cls}" font-size="{size}"{a}'
            f'{extra}>{text}</text>')

def window():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=364)
    return (f"{start.isoformat()}T00:00:00Z", f"{today.isoformat()}T23:59:59Z")

def fetch_iqumnov_stats():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("ERROR: GITHUB_TOKEN not set")
        sys.exit(1)
    
    login = "Iqumnov"
    since, until = window()
    
    body = json.dumps({
        "query": QUERY,
        "variables": {"login": login, "from": since, "to": until}
    }).encode()
    
    req = urllib.request.Request(
        API, data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": f"{login}-stats"
        }
    )
    
    with urllib.request.urlopen(req, timeout=30) as r:
        payload = json.load(r)
    
    if "errors" in payload:
        print(f"GraphQL errors: {payload['errors']}")
        sys.exit(1)
    
    user = payload.get("data", {}).get("user")
    if not user:
        print(f"No such user: {login}")
        sys.exit(1)
    
    cal = user["contributionsCollection"]["contributionCalendar"]
    weeks = [w["contributionDays"] for w in cal["weeks"]]
    days = [d for w in weeks for d in w]
    weekly = [sum(d["contributionCount"] for d in w) for w in weeks]
    
    run, max_streak = 0, 0
    active_days = 0
    
    for d in days:
        c = d["contributionCount"]
        if c > 0:
            active_days += 1
            run += 1
            if run > max_streak:
                max_streak = run
        else:
            run = 0
    
    return dict(
        total=cal["totalContributions"],
        active=active_days,
        max_streak=max_streak,
        weekly=weekly
    )

def draw_stats(s):
    H = 148
    weekly = s["weekly"] or [0]
    peak = max(weekly) or 1
    p = [head(WIDTH, H)]
    
    right_margin = 24
    usable_width = WIDTH - right_margin

    p.append(f'<g opacity="0">{fade(0.10)}'
             + label(0, 42, s["total"], 36, "e-f", extra=' font-weight="600"')
             + label(0, 64, "contributions in the last year", 11) + '</g>')
    
    p.append(f'<g opacity="0">{fade(0.30)}'
             + label(usable_width, 28, f"{s['max_streak']} days", 15, "e-f", "end", ' font-weight="600"')
             + label(usable_width, 44, "max streak", 10, "m-f", "end") + '</g>')
    p.append(f'<g opacity="0">{fade(0.42)}'
             + label(usable_width, 64, s["active"], 15, "e-f", "end", ' font-weight="600"')
             + label(usable_width, 80, "active days", 10, "m-f", "end") + '</g>')

    base, top = H - 10, H - 56
    span = base - top
    step = usable_width / max(len(weekly) - 1, 1)
    pts = [(i * step, base - (v / peak) * span) for i, v in enumerate(weekly)]
    clip, cursor = wipe("rs", 0, top - 6, usable_width, span + 8, 0.50)
    p.append(clip)
    p.append('<g clip-path="url(#rs)">')
    p.append(f'<path d="M{pts[0][0]:.1f} {base:.1f}'
             + "".join(f'L{x:.1f} {y:.1f}' for x, y in pts)
             + f'L{pts[-1][0]:.1f} {base:.1f}Z" class="w"/>')
    p.append(f'<path d="M{pts[0][0]:.1f} {pts[0][1]:.1f}'
             + "".join(f'L{x:.1f} {y:.1f}' for x, y in pts[1:])
             + f'" class="d-s" stroke-width="2" stroke-linejoin="round" '
             f'stroke-linecap="round"/>')
    p.append("</g>")
    p.append(cursor)
    ex, ey = pts[-1]
    p.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" class="e-f r" '
             f'stroke-width="2" opacity="0">{fade(0.50 + REVEAL, 0.35)}</circle>')
    p.append("</svg>")
    return "".join(p)

if __name__ == "__main__":
    s = fetch_iqumnov_stats()
    svg_content = draw_stats(s)
    out_path = os.path.join(SCRIPT_DIR, "..", "stats.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Successfully generated {out_path} for Iqumnov")
    print(f"  total={s['total']}, active={s['active']}, max_streak={s['max_streak']}")