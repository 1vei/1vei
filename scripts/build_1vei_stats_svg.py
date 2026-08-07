#!/usr/bin/env python3
import urllib.request
import re
import os
import base64

# Font loading helper
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
LEFT = 34
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

def fetch_1vei_stats():
    url = "https://github.com/users/1vei/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')

    td_matches = re.findall(r'data-date="([^"]+)".*?id="(contribution-day-component-[^"]+)"', html)
    id_to_date = {tid: d for d, tid in td_matches}
    tt_matches = re.findall(r'for="(contribution-day-component-[^"]+)".*?>(.*?)<\/tool-tip>', html, re.DOTALL)

    date_counts = {}
    for tid, text in tt_matches:
        d = id_to_date.get(tid)
        if d:
            m = re.search(r'(\d+)\s+contribution', text)
            c = int(m.group(1)) if m else 0
            date_counts[d] = c

    sorted_dates = sorted(date_counts.keys())
    total_contribs = sum(date_counts.values())

    run, max_streak = 0, 0
    active_days = 0
    weekly_counts = []
    current_week = 0

    for idx, d in enumerate(sorted_dates):
        c = date_counts[d]
        current_week += c
        if (idx + 1) % 7 == 0 or idx == len(sorted_dates) - 1:
            weekly_counts.append(current_week)
            current_week = 0

        if c > 0:
            active_days += 1
            run += 1
            if run > max_streak:
                max_streak = run
        else:
            run = 0

    return dict(
        total=total_contribs,
        active=active_days,
        max_streak=max_streak,
        weekly=weekly_counts
    )

def draw_stats(s):
    H = 148
    weekly = s["weekly"] or [0]
    peak = max(weekly) or 1
    p = [head(WIDTH, H)]
    p.append(f'<g opacity="0">{fade(0.10)}'
             + label(0, 50, s["total"], 52, "e-f", extra=' font-weight="600"')
             + label(0, 72, "contributions in the last year", 12) + '</g>')
    
    for i, (val, lab) in enumerate([(f"{s['max_streak']} days", "max streak"),
                                    (s["active"], "active days")]):
        p.append(f'<g opacity="0">{fade(0.30 + i * 0.12)}'
                 + label(WIDTH, 30 + i * 40, val, 19, "e-f", "end",
                         ' font-weight="600"')
                 + label(WIDTH, 47 + i * 40, lab, 11, "m-f", "end") + '</g>')

    base, top = H - 10, H - 58
    span = base - top
    step = WIDTH / max(len(weekly) - 1, 1)
    pts = [(i * step, base - (v / peak) * span) for i, v in enumerate(weekly)]
    clip, cursor = wipe("rs", 0, top - 6, WIDTH, span + 8, 0.50)
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
    p.append(f'<circle cx="{ex - 2:.1f}" cy="{ey:.1f}" r="4.5" class="e-f r" '
             f'stroke-width="2" opacity="0">{fade(0.50 + REVEAL, 0.35)}</circle>')
    p.append("</svg>")
    return "".join(p)

if __name__ == "__main__":
    s = fetch_1vei_stats()
    svg_content = draw_stats(s)
    out_path = os.path.join(SCRIPT_DIR, "..", "stats.svg")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Successfully generated {out_path} with total={s['total']}, active={s['active']}, max_streak={s['max_streak']}")
