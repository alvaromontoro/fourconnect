#!/usr/bin/env python3

import html as html_utils
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
GAMES_DIR = ROOT / "games"
INDEX_FILE = ROOT / "index.html"
ARCHIVE_FILE = ROOT / "archive.html"
SITEMAP_XML_FILE = ROOT / "sitemap.xml"
SITEMAP_HTML_FILE = ROOT / "sitemap.html"
BASE_URL = "https://fourconnect.net"

STATIC_PAGES = [
    ("/", "Home"),
    ("/archive.html", "Archive"),
    ("/how-to-play.html", "How to Play"),
    ("/faq.html", "FAQ"),
    ("/about.html", "About"),
    ("/contact.html", "Contact"),
    ("/privacy.html", "Privacy"),
    ("/terms.html", "Terms of Use"),
    ("/stats.html", "Stats"),
]


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_long_date(value: date) -> str:
    # Avoid platform-specific day formatting flags.
    return value.strftime("%B %d, %Y").replace(" 0", " ")


def format_short_date(value: date) -> str:
    """Format date as 'Mon DD' (e.g., 'May 11')."""
    return value.strftime("%b %d").replace(" 0", " ")


def find_latest_game_data_files(limit: Optional[int] = 10, include_future: bool = False) -> list[tuple[date, Path]]:
    """Find game data files sorted by date descending."""
    games = []
    today = date.today()

    for data_file in GAMES_DIR.glob("*/*/*/data.json"):
        try:
            year = int(data_file.parts[-4])
            month = int(data_file.parts[-3])
            day = int(data_file.parts[-2])
            current_date = date(year, month, day)

            # Keep homepage/archive behavior unchanged by default.
            if not include_future and current_date > today:
                continue
        except (ValueError, IndexError):
            continue

        games.append((current_date, data_file))

    if not games:
        raise RuntimeError("No game data files found in games/YYYY/MM/DD/data.json")

    games.sort(key=lambda x: x[0], reverse=True)
    if limit is None:
        return games
    return games[:limit]


def build_sitemap_urls(games_with_data: list[tuple[date, dict]]) -> list[str]:
    static_urls = [path for path, _label in STATIC_PAGES]
    game_urls = [f"/games/{game_date:%Y/%m/%d}" for game_date, _data in games_with_data]
    return static_urls + game_urls


def update_sitemap_xml(games_with_data: list[tuple[date, dict]]) -> bool:
    urls = build_sitemap_urls(games_with_data)

    entries = []
    for path in urls:
        location = f"{BASE_URL}{path}"
        entries.append(f"  <url>\n    <loc>{html_utils.escape(location)}</loc>\n  </url>")

    content = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">\n"
        + "\n".join(entries)
        + "\n</urlset>\n"
    )

    existing = SITEMAP_XML_FILE.read_text(encoding="utf-8") if SITEMAP_XML_FILE.exists() else ""
    if existing == content:
        return False

    SITEMAP_XML_FILE.write_text(content, encoding="utf-8")
    return True


def build_sitemap_html(games_with_data: list[tuple[date, dict]]) -> str:
    static_items = []
    for path, label in STATIC_PAGES:
        static_items.append(f'                <li><a href="{path}">{html_utils.escape(label)}</a></li>')

    game_items = []
    for game_date, data in games_with_data:
        path = f"/games/{game_date:%Y/%m/%d}"
        title = data.get("title", "")
        label = format_long_date(game_date)
        if title:
            label = f"{label} - {title}"
        game_items.append(f'                <li><a href="{path}">{html_utils.escape(label)}</a></li>')

    return """<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <meta name="author" content="Alvaro Montoro (alvaromontoro@gmail.com)" />
        <meta name="keywords" content="fourconnect,4connect,game,puzzle,daily puzzle,sitemap" />
        <meta name="description" content="Browse all FourConnect pages and daily games." />
        <meta name="theme-color" content="#7d44db" />
        <meta property="og:title" content="4Connect" />
        <meta property="og:type" content="website" />
        <meta property="og:url" content="https://fourconnect.net/sitemap.html" />
        <meta property="og:image" content="https://fourconnect.net/media/thumb.png" />
        <meta property="og:description" content="Browse all FourConnect pages and daily games." />
        <link rel="monetization" href="https://fynbos.me/alvaro">

        <title>4Connect - Sitemap</title>

        <link rel="stylesheet" href="/css/styles.css">
        <link rel="stylesheet" href="/css/section.css">
        <script src="/js/code.js" defer></script>
        <script src="/js/fourconnect.js" defer></script>
        <script async src="https://www.googletagmanager.com/gtag/js?id=G-438W7TCDDG"></script>
        <script>
            window.dataLayer = window.dataLayer || [];
            function gtag(){{dataLayer.push(arguments);}}
            gtag('js', new Date());

            gtag('config', 'G-438W7TCDDG');
        </script>
    </head>
    <body class="sitemap section">
        <a href="#main" class="skip-to-main">Skip to main</a>
        <header>
            <div class="container">
                <h1>
                    <img aria-hidden alt="" src="/media/logo.webp" width="32" height="32">
                    4Connect
                </h1>
                <nav aria-label="Main navigation">
                    <button id="menu-toggle" aria-controls="main-menu" aria-expanded="false" aria-label="Toggle menu" hidden>
                        <span class="a11y-hidden">Toggle menu</span>
                    </button>
                    <ul id="main-menu">
                        <li><a href="/index.html" data-url="home">Home</a></li>
                        <li><a href="/archive.html" data-url="archive">Archive</a></li>
                        <li><a href="/how-to-play.html" data-url="how-to-play">How to Play</a></li>
                        <li><a href="/faq.html" data-url="faq">FAQ</a></li>
                        <li><a href="/about.html" data-url="about">About</a></li>
                    </ul>
                </nav>
            </div>
        </header>

        <main id="main" class="container">
            <section class="hero">
                <div class="heading">
                    <hgroup>
                        <p>Discover all pages</p>
                        <h2>Sitemap</h2>
                    </hgroup>
                    <span class="pill">Everything in one place</span>
                </div>
            </section>

            <section aria-labelledby="core-pages-title">
                <h3 id="core-pages-title">Core Pages</h3>
                <p><a href="/sitemap.xml">Machine-readable sitemap (XML)</a></p>
                <ul>
{static_items}
                </ul>
            </section>

            <section aria-labelledby="daily-games-title">
                <h3 id="daily-games-title">Daily Games</h3>
                <ul>
{game_items}
                </ul>
            </section>
        </main>

        <footer>
            <div class="container footer-content">
                <div>
                    <h2>
                        <img aria-hidden alt="" src="/media/logo.webp" width="24" height="24">
                        4Connect
                    </h2>
                    <small>&copy; 2026 <a href="https://studiokah.com">Studio Kah</a>. All rights reserved.</small>
                </div>
                <div class="footer-links">
                    <details>
                        <summary><h3>Game</h3></summary>
                        <nav>
                            <ul>
                                <li><a href="/how-to-play.html" data-url="how-to-play">How to Play</a></li>
                                <li><a href="/archive.html" data-url="archive">Archive</a></li>
                                <li><a href="/faq.html" data-url="faq">FAQ</a></li>
                                <li><a href="/stats.html" data-url="stats">Stats</a></li>
                            </ul>
                        </nav>
                    </details>

                    <details>
                        <summary><h3>About Us</h3></summary>
                        <nav>
                            <ul>
                                <li><a href="/about.html" data-url="about">About</a></li>
                                <li><a href="/contact.html" data-url="contact">Contact</a></li>
                                <li><a href="/privacy.html" data-url="privacy">Privacy</a></li>
                                <li><a href="/terms.html" data-url="terms">Terms of Use</a></li>
                                <li><a href="/sitemap.html" data-url="sitemap">Sitemap</a></li>
                            </ul>
                        </nav>
                    </details>

                    <details>
                        <summary><h3>Follow Us</h3></summary>
                        <nav>
                            <ul>
                                <li><a href="https://bsky.app/profile/fourconnect.net" target="_blank" rel="noopener noreferrer">Bluesky</a></li>
                                <li><a href="https://www.instagram.com/4connect_game/" target="_blank" rel="noopener noreferrer">Instagram</a></li>
                            </ul>
                        </nav>
                    </details>
                </div>
            </div>
        </footer>
    </body>
</html>
""".format(static_items="\n".join(static_items), game_items="\n".join(game_items))


def update_sitemap_html(games_with_data: list[tuple[date, dict]]) -> bool:
    content = build_sitemap_html(games_with_data)
    content = re.sub(
        r"(?m)^(?: {4})+",
        lambda match: "  " * (len(match.group(0)) // 4),
        content,
    )
    existing = SITEMAP_HTML_FILE.read_text(encoding="utf-8") if SITEMAP_HTML_FILE.exists() else ""
    if existing == content:
        return False

    SITEMAP_HTML_FILE.write_text(content, encoding="utf-8")
    return True


def build_previous_games_html(games_with_data: list[tuple[date, dict]]) -> str:
    """Build previous games list (skip first/current game, take next 9)."""
    items = []
    for game_date, data in games_with_data[1:10]:
        date_str = game_date.isoformat()
        display = format_short_date(game_date)
        items.append(f'            <li><a href="/games/{game_date:%Y/%m/%d}">{display}</a></li>')

    # Add "View All" link
    items.append('            <li><a href="/archive.html">View All <span class="a11y-hidden">previous games</span></a></li>')
    return "\n".join(items)


def normalize_css_class(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.strip().lower()).strip("-")


def build_archive_item_html(game_date: date, game_data: dict) -> str:
    href = f"/games/{game_date:%Y/%m/%d}"
    date_str = game_date.isoformat()
    display = format_short_date(game_date)

    categories = game_data.get("categories") or []
    css_class = ""
    if categories:
        css_class = normalize_css_class(str(categories[0]))

    class_attr = f' class="{css_class}"' if css_class else ""
    return f'          <li><a href="{href}"{class_attr}><time datetime="{date_str}">{display}</time></a></li>'


def update_archive_html(current_date: date, current_data: dict, max_items: int = 35) -> bool:
    html = ARCHIVE_FILE.read_text(encoding="utf-8")

    section_match = re.search(
        r"(<section class=\"more-games\">\s*<ul>)(.*?)(</ul>\s*</section>)",
        html,
        flags=re.DOTALL,
    )
    if not section_match:
        return False

    list_html = section_match.group(2)
    existing_items = re.findall(r"<li>.*?</li>", list_html, flags=re.DOTALL)

    date_str = current_date.isoformat()
    href_fragment = f"/games/{current_date:%Y/%m/%d}"

    filtered_items = []
    for item in existing_items:
        if f'datetime="{date_str}"' in item:
            continue
        if href_fragment in item:
            continue
        filtered_items.append(item.strip())

    new_item = build_archive_item_html(current_date, current_data).strip()
    updated_items = [new_item] + filtered_items
    updated_items = [f"          {item}" for item in updated_items[:max_items]]

    new_section = section_match.group(1) + "\n" + "\n".join(updated_items) + "\n        " + section_match.group(3)
    updated = html[:section_match.start()] + new_section + html[section_match.end():]

    if updated == html:
        return False

    ARCHIVE_FILE.write_text(updated, encoding="utf-8")
    return True


def update_index_html(
    game_date: date,
    date_long: str,
    game_title: str,
    game_payload: str,
    previous_link: str,
    previous_games_html: str,
) -> bool:
    html = INDEX_FILE.read_text(encoding="utf-8")

    # Update game date
    updated = re.sub(
        r'<time datetime="[^"]+" class="game-date pill">[^<]+</time>',
        f'<time datetime="{game_date.isoformat()}" class="game-date pill">{date_long}</time>',
        html,
        count=1,
    )

    # Update game title
    if game_title:
        escaped_title = html_utils.escape(game_title)
        updated = re.sub(
            r'(<h3 class="game-title">\s*)(.*?)(\s*</h3>)',
            lambda m: f"{m.group(1)}{escaped_title}{m.group(3)}",
            updated,
            flags=re.DOTALL,
            count=1,
        )

    # Update game data
    updated = re.sub(
        r"<four-connect data='[^']*'></four-connect>",
        lambda _m: f"<four-connect data='{game_payload}'></four-connect>",
        updated,
        count=1,
    )

    # Update "Play Yesterday's Game" link
    updated = re.sub(
        r'<a href="[^"]+" class="play-now-link">',
        f'<a href="{previous_link}" class="play-now-link">',
        updated,
        count=1,
    )

    # Update previous games list
    updated = re.sub(
        r"(<section class=\"previous\">.*?<ul>)(.*?)(</ul>\s*</section>)",
        r"\1\n" + previous_games_html + "\n          " + r"\3",
        updated,
        flags=re.DOTALL,
        count=1,
    )

    if updated == html:
        return False

    INDEX_FILE.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    published_game_files = find_latest_game_data_files(limit=None)

    published_games_with_data = []
    for game_date, data_file in published_game_files:
        data = json.loads(data_file.read_text(encoding="utf-8"))
        published_games_with_data.append((game_date, data))

    games_with_data = published_games_with_data[:10]

    # Current game (first/latest)
    current_date, current_data = games_with_data[0]
    date_long = current_data.get("dateLong", format_long_date(current_date))
    game_title = current_data.get("title", "")
    game_payload = json.dumps(current_data["game"], separators=(",", ":"))

    previous_date = current_date - timedelta(days=1)
    previous_link = f"/games/{previous_date:%Y/%m/%d}/"

    # Build previous games section
    previous_games_html = build_previous_games_html(games_with_data)

    index_changed = update_index_html(
        current_date,
        date_long,
        game_title,
        game_payload,
        previous_link,
        previous_games_html,
    )

    archive_changed = update_archive_html(current_date, current_data, max_items=35)
    sitemap_xml_changed = update_sitemap_xml(games_with_data=published_games_with_data)
    sitemap_html_changed = update_sitemap_html(games_with_data=published_games_with_data)

    changed = index_changed or archive_changed or sitemap_xml_changed or sitemap_html_changed

    if changed:
        print(f"Updated {INDEX_FILE}, {ARCHIVE_FILE}, {SITEMAP_XML_FILE}, and {SITEMAP_HTML_FILE}")
    else:
        print("No changes needed")


if __name__ == "__main__":
    main()
