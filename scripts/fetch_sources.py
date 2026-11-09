"""Download Wikipedia articles as plain text into data/sources/<topic>/.

Usage: python scripts/fetch_sources.py
"""

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

TOPICS = {
    "tea-and-coffee": ["Green tea", "Coffee", "Caffeine", "Theanine", "Catechin"],
    "renewable-energy": ["Solar power", "Wind power", "Heat pump", "Lithium-ion battery", "Grid energy storage"],
    "sleep": ["Sleep", "Circadian rhythm", "Melatonin", "Insomnia", "Sleep deprivation"],
    "space-exploration": ["James Webb Space Telescope", "Exoplanet", "Mars rover", "Artemis program", "SpaceX Starship"],
}

API = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "DigitalScribe/0.1 (https://github.com/aashish177/Digital-Scribe)"
OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "sources"


def fetch(title: str) -> dict:
    params = {
        "action": "query",
        "prop": "extracts|info|revisions",
        "explaintext": 1,
        "inprop": "url",
        "rvprop": "ids",
        "redirects": 1,
        "titles": title,
        "format": "json",
        "formatversion": 2,
    }
    req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        page = json.load(resp)["query"]["pages"][0]
    if "missing" in page:
        raise ValueError(f"Wikipedia page not found: {title}")
    return page


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def main():
    for topic, titles in TOPICS.items():
        topic_dir = OUT_DIR / topic
        topic_dir.mkdir(parents=True, exist_ok=True)
        for title in titles:
            page = fetch(title)
            body = re.split(r"\n== (?:See also|Notes|References|Further reading|External links) ==", page["extract"])[0].strip()
            header = {
                "title": page["title"],
                "url": page["fullurl"],
                "revision": page["revisions"][0]["revid"],
                "license": "CC BY-SA 4.0",
            }
            path = topic_dir / f"{slugify(page['title'])}.md"
            path.write_text(f"---\n{json.dumps(header)}\n---\n{body}\n", encoding="utf-8")
            print(f"{topic}: {page['title']} ({len(body)} chars)")


if __name__ == "__main__":
    main()
