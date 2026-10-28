#!/usr/bin/env python3
"""Render the profile's recent GitHub contribution activity as a standalone SVG."""
import json
import math
import os
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

LOGIN = "Mohammad-AlBaker-Zaytoun"
OUTPUT = Path("profile/activity-graph.svg")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
if not TOKEN:
    raise SystemExit("GH_TOKEN or GITHUB_TOKEN is required")

query = """query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}"""
request = Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": query, "variables": {"login": LOGIN}}).encode(),
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
             "User-Agent": "profile-activity-graph"},
    method="POST",
)
with urlopen(request, timeout=30) as response:
    payload = json.load(response)
if payload.get("errors") or not payload.get("data", {}).get("user"):
    raise SystemExit(f"GitHub GraphQL failed: {payload.get('errors', payload)}")

days = {
    entry["date"]: int(entry["contributionCount"])
    for week in payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    for entry in week["contributionDays"]
}
end = date.today()
start = end - timedelta(days=59)
points = [(start + timedelta(days=i), days.get((start + timedelta(days=i)).isoformat(), 0))
          for i in range(60)]
if not any(d.isoformat() in days for d, _ in points):
    raise SystemExit("No contribution calendar data for the requested period")

W, H = 960, 310
left, right, top, bottom = 64, 930, 62, 252
max_count = max(4, max(value for _, value in points))
ceiling = max(4, math.ceil(max_count / 4) * 4)
def xy(index, value):
    return (left + (right - left) * index / (len(points) - 1),
            bottom - (bottom - top) * value / ceiling)
coords = [xy(i, value) for i, (_, value) in enumerate(points)]
poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
area = f"{left},{bottom} {poly} {right},{bottom}"
total = sum(v for _, v in points)
parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub contributions over the last 60 days">',
    '<rect width="100%" height="100%" rx="14" fill="#0d1117"/>',
    '<defs><linearGradient id="activity-fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#00d9ff" stop-opacity=".29"/><stop offset="100%" stop-color="#00d9ff" stop-opacity=".02"/></linearGradient></defs>',
    '<text x="64" y="32" fill="#00d9ff" font-family="Arial,sans-serif" font-size="19" font-weight="bold">GitHub Coding Activity</text>',
    f'<text x="930" y="32" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="13">{total} contributions · last 60 days</text>',
]
for step in range(5):
    value = ceiling * step / 4
    y = xy(0, value)[1]
    parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="#30363d" stroke-width="1"/>')
    parts.append(f'<text x="51" y="{y+4:.1f}" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{value:g}</text>')
for i in range(0, 60, 7):
    day = points[i][0]
    x = xy(i, 0)[0]
    parts.append(f'<text x="{x:.1f}" y="277" text-anchor="middle" fill="#8b949e" font-family="Arial,sans-serif" font-size="12">{day.strftime("%b %d")}</text>')
parts += [
    f'<polygon points="{area}" fill="url(#activity-fill)"/>',
    f'<polyline points="{poly}" fill="none" stroke="#00d9ff" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>',
]
for x, y in coords:
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.6" fill="#ffffff" stroke="#00d9ff" stroke-width="1.3"/>')
parts.append('<text x="930" y="301" text-anchor="end" fill="#8b949e" font-family="Arial,sans-serif" font-size="11">Source: GitHub contribution calendar · updated daily</text>')
parts.append("</svg>")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
print(f"Wrote {OUTPUT}: {len(points)} days, {total} contributions")
