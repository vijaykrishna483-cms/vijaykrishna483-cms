"""
Builds profile.svg: animated ASCII portrait + neofetch-style info (one dark terminal card,
used for both GitHub themes; the portrait reads far more accurately light-on-dark).

Stdlib only, so the daily GitHub Action can run it. Stats come from the GitHub API
(uses GITHUB_TOKEN if set, for contributions via GraphQL).

    python generate.py
"""
import datetime as dt
import hashlib
import json
import os
import re
import urllib.request
from html import escape

USER = "vijaykrishna483-cms"
JOINED = dt.date(2024, 1, 16)

W, H = 985, 560
# portrait: 120 cols x 71 rows in a 398x525 box, pinned with textLength so any monospace font lines up
P_COLS, P_ROWS = 120, 71
P_X, P_Y, P_CHAR, P_LINE = 15, 23, 398 / 120, 525 / 71
P_FONT = round(P_LINE * 0.83, 2)
ROW_DELAY = 0.025
# info column
I_X, I_Y, I_FONT, I_LINE, I_COLS = 440, 30, 14, 19.5, 62

THEME = dict(bg="#161b22", fg="#c9d1d9", key="#ffa657", value="#a5d6ff", cc="#616e7f", scan="#58a6ff")


def api(url, body=None):
    headers = {"User-Agent": USER, "Accept": "application/vnd.github+json"}
    token = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = json.dumps(body).encode() if body else None
    with urllib.request.urlopen(urllib.request.Request(url, data, headers), timeout=20) as r:
        return json.load(r)


def stats():
    if os.environ.get("ACCESS_TOKEN"):
        # personal token: /user/repos also sees private repos
        repos = api("https://api.github.com/user/repos?per_page=100&affiliation=owner")
    else:
        repos = api(f"https://api.github.com/users/{USER}/repos?per_page=100&type=owner")
    s = {"repos": len(repos), "stars": sum(r["stargazers_count"] for r in repos)}
    try:
        q = 'query{user(login:"%s"){contributionsCollection{contributionCalendar{totalContributions} totalCommitContributions}}}' % USER
        c = api("https://api.github.com/graphql", {"query": q})["data"]["user"]["contributionsCollection"]
        s["contrib"] = c["contributionCalendar"]["totalContributions"]
        s["commits"] = c["totalCommitContributions"]
    except Exception:
        pass                                   # GraphQL needs a token; card just skips those fields
    return s


def uptime(today):
    months = (today.year - JOINED.year) * 12 + today.month - JOINED.month - (today.day < JOINED.day)
    y, m = divmod(months, 12)
    parts = [f"{y} year{'s' * (y != 1)}"] * (y > 0) + [f"{m} month{'s' * (m != 1)}"]
    return ", ".join(parts)


def info_lines(s):
    """Each line is a list of (css_class, text) spans. Keys are dot-padded like neofetch."""
    def kv(key, value):
        dots = max(1, I_COLS - len(key) - len(value) - 4)
        return [("cc", ". "), ("key", key), ("cc", ":" + " " + "." * dots + " "), ("value", value)]

    def header(title):
        return [("fg", title + " "), ("cc", "-" * (I_COLS - len(title) - 1))]

    stat_line = f"{s['repos']} repos | {s['stars']} stars"
    lines = [
        header("vijay@krishna"),
        kv("Role", "Software Engineer"),
        kv("Org", "IIT Madras"),
        kv("Currently", "Building AI agents, esp. Voice Agents"),
        kv("Uptime", uptime(dt.date.today())),
        [],
        kv("AI.Agents", "LiveKit Agents, MCP, Tool Calling, RAG"),
        kv("AI.Voice", "Realtime STT -> LLM -> TTS, VAD, WebRTC"),
        kv("AI.Ops", "Agent Evals, Observability, Guardrails"),
        [],
        kv("Languages.Programming", "C, C++, Java, Python, JS, TS"),
        kv("Languages.Web", "HTML, CSS, GraphQL"),
        kv("Frameworks", "React, Next.js, React Native, Node"),
        kv("Backend", "Express, FastAPI, Flask, Socket.io"),
        kv("Cloud", "AWS, Firebase, DigitalOcean, Vercel"),
        kv("Databases", "PostgreSQL, MySQL, MongoDB, Redis"),
        kv("Tools", "Git, Nginx, Figma, Postman, Notion"),
        [],
        header("- Contact"),
        kv("Email", "vijay762005@gmail.com"),
        kv("LinkedIn", "vijay-krishna-s-b68916283"),
        kv("GitHub", USER),
        [],
        header("- GitHub Stats"),
        kv("Repos", stat_line),
    ]
    if "contrib" in s:
        lines.append(kv("Contributions (past year)", f"{s['contrib']} | commits {s['commits']}"))
    return lines


def svg(portrait, lines):
    t = THEME
    out = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Consolas,'SF Mono',Menlo,'DejaVu Sans Mono',monospace">
<style>
text, tspan {{ white-space: pre; }}
.fg {{ fill: {t['fg']}; }} .key {{ fill: {t['key']}; }} .value {{ fill: {t['value']}; }} .cc {{ fill: {t['cc']}; }}
.ascii {{ fill: {t['fg']}; font-size: {P_FONT}px; font-weight: bold; }}
.info {{ font-size: {I_FONT}px; }}
/* 1. face draws in top-to-bottom, then info lines slide in */
.row {{ opacity: 0; animation: reveal .35s ease-out forwards; }}
.line {{ opacity: 0; animation: slide .4s ease-out forwards; }}
@keyframes reveal {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
@keyframes slide {{ from {{ opacity: 0; transform: translateX(-8px); }} to {{ opacity: 1; transform: none; }} }}
/* 2. scanner beam sweeping over the face, forever */
.beam {{ animation: scan 4.5s linear 2.4s infinite; opacity: 0; }}
@keyframes scan {{ 0% {{ transform: translateY(0); opacity: 0; }} 8% {{ opacity: 1; }} 92% {{ opacity: 1; }} 100% {{ transform: translateY({P_ROWS * P_LINE + 50:.0f}px); opacity: 0; }} }}
/* 3. tiny glitch every few seconds */
.face {{ animation: glitch 6s steps(1) 3s infinite; }}
@keyframes glitch {{ 0%, 90%, 94%, 100% {{ transform: none; }} 91% {{ transform: translateX(3px); }} 92% {{ transform: translateX(-2px); }} 93% {{ transform: translateX(1px); }} }}
/* 4. blinking terminal cursor */
.cursor {{ animation: blink 1s steps(1) infinite backwards; }}
@keyframes blink {{ 0% {{ opacity: 0; }} 50% {{ opacity: 1; }} }}
</style>
<defs>
<linearGradient id="beam" x1="0" y1="0" x2="0" y2="1">
<stop offset="0" stop-color="{t['scan']}" stop-opacity="0"/>
<stop offset=".85" stop-color="{t['scan']}" stop-opacity=".22"/>
<stop offset="1" stop-color="{t['scan']}" stop-opacity=".6"/>
</linearGradient>
</defs>
<rect width="{W}" height="{H}" fill="{t['bg']}" rx="15"/>
<g class="face">''']
    for i, row in enumerate(portrait):
        if not row.strip():
            continue
        y = P_Y + i * P_LINE
        out.append(f'<text class="ascii row" x="{P_X}" y="{y:.1f}" textLength="{len(row) * P_CHAR:.1f}" '
                   f'lengthAdjust="spacingAndGlyphs" style="animation-delay:{i * ROW_DELAY:.2f}s">{escape(row)}</text>')
    out.append('</g>')
    out.append(f'<rect class="beam" x="{P_X}" y="{P_Y - 50}" width="{P_COLS * P_CHAR:.0f}" height="50" fill="url(#beam)"/>')

    start = P_ROWS * ROW_DELAY
    for i, spans in enumerate(lines):
        if not spans:
            continue
        y = I_Y + i * I_LINE
        body = "".join(f'<tspan class="{c}">{escape(txt)}</tspan>' for c, txt in spans)
        out.append(f'<text class="info line" x="{I_X}" y="{y}" style="animation-delay:{start + i * 0.07:.2f}s">{body}</text>')
    cy = I_Y + len(lines) * I_LINE
    out.append(f'<text class="info line" x="{I_X}" y="{cy}" style="animation-delay:{start + len(lines) * 0.07:.2f}s">'
               f'<tspan class="key">vijay@krishna</tspan><tspan class="fg">:~$ </tspan></text>')
    # cursor is its own element: opacity animations aren't reliable on a tspan
    out.append(f'<rect class="cursor" x="{I_X + 18 * I_FONT * 0.55:.0f}" y="{cy - I_FONT + 3}" '
               f'width="{I_FONT * 0.55:.1f}" height="{I_FONT}" fill="{t["fg"]}" '
               f'style="animation-delay:{start + len(lines) * 0.07:.2f}s"/>')
    out.append('</svg>\n')
    return "\n".join(out)


if __name__ == "__main__":
    s = stats()
    lines = info_lines(s)
    portrait = open("assets/ascii.txt", encoding="utf-8").read().splitlines()
    card = svg(portrait, lines)
    with open("profile.svg", "w", encoding="utf-8") as f:
        f.write(card)
    # version the image URL so GitHub's image cache picks up every change
    version = hashlib.sha1(card.encode()).hexdigest()[:8]
    readme = open("README.md", encoding="utf-8").read()
    readme = re.sub(r'src="\./profile\.svg(\?v=\w+)?"', f'src="./profile.svg?v={version}"', readme)
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("stats:", s)
