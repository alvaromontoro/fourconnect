#!/usr/bin/env python3

import argparse
import html as html_utils
import json
import re
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from typing import Optional


ROOT = Path(__file__).resolve().parents[1]
GAMES_DIR = ROOT / "games"
INDEX_FILE = ROOT / "index.html"
ARCHIVE_FILE = ROOT / "archive.html"
SITEMAP_XML_FILE = ROOT / "sitemap.xml"
SITEMAP_HTML_FILE = ROOT / "sitemap.html"
RSS_XML_FILE = ROOT / "rss.xml"
RSS_DIR = ROOT / "rss"
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

STATIC_PAGE_FILES = {
    "/": ROOT / "index.html",
    "/archive.html": ROOT / "archive.html",
    "/how-to-play.html": ROOT / "how-to-play.html",
    "/faq.html": ROOT / "faq.html",
    "/about.html": ROOT / "about.html",
    "/contact.html": ROOT / "contact.html",
    "/privacy.html": ROOT / "privacy.html",
    "/terms.html": ROOT / "terms.html",
    "/stats.html": ROOT / "stats.html",
}


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_long_date(value: date) -> str:
    # Avoid platform-specific day formatting flags.
    return value.strftime("%B %d, %Y").replace(" 0", " ")


def format_short_date(value: date) -> str:
    """Format date as 'Mon DD' (e.g., 'May 11')."""
    return value.strftime("%b %d").replace(" 0", " ")


def format_category_label(value: str) -> str:
    return re.sub(r"[\s_-]+", " ", value.strip()).title()


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
    entries = []
    for path, _label in STATIC_PAGES:
        location = f"{BASE_URL}{path}"
        file_path = STATIC_PAGE_FILES.get(path)
        if file_path and file_path.exists():
            lastmod = date.fromtimestamp(file_path.stat().st_mtime).isoformat()
        else:
            lastmod = date.today().isoformat()
        entries.append(
            "  <url>\n"
            f"    <loc>{html_utils.escape(location)}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            "  </url>"
        )

    for game_date, _data in games_with_data:
        path = f"/games/{game_date:%Y/%m/%d}"
        location = f"{BASE_URL}{path}"
        entries.append(
            "  <url>\n"
            f"    <loc>{html_utils.escape(location)}</loc>\n"
            f"    <lastmod>{game_date.isoformat()}</lastmod>\n"
            "  </url>"
        )

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


def format_rss_pub_date(value: date) -> str:
    return format_datetime(datetime.combine(value, datetime.min.time(), tzinfo=timezone.utc))


def build_rss_items(games_with_data: list[tuple[date, dict]]) -> list[str]:
    items = []
    for game_date, data in games_with_data:
        title = str(data.get("title", "Daily Puzzle")).strip() or "Daily Puzzle"
        game_url = f"{BASE_URL}/games/{game_date:%Y/%m/%d}"
        description = f"4Connect puzzle for {format_long_date(game_date)}"

        categories = data.get("categories") or []
        if categories:
            category_text = ", ".join(str(item).strip() for item in categories if str(item).strip())
            if category_text:
                description += f". Categories: {category_text}."

        items.append(
            "  <item>\n"
            f"    <title>{html_utils.escape(title)}</title>\n"
            f"    <link>{html_utils.escape(game_url)}</link>\n"
            f"    <guid>{html_utils.escape(game_url)}</guid>\n"
            f"    <pubDate>{html_utils.escape(format_rss_pub_date(game_date))}</pubDate>\n"
            f"    <description>{html_utils.escape(description)}</description>\n"
            "  </item>"
        )

    return items


def build_rss_content(title: str, link: str, description: str, items: list[str], latest_date: date) -> str:
    latest_pub_date = format_rss_pub_date(latest_date)
    return (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<rss version=\"2.0\">\n"
        "<channel>\n"
        f"  <title>{html_utils.escape(title)}</title>\n"
        f"  <link>{html_utils.escape(link)}</link>\n"
        f"  <description>{html_utils.escape(description)}</description>\n"
        "  <language>en-us</language>\n"
        f"  <lastBuildDate>{html_utils.escape(latest_pub_date)}</lastBuildDate>\n"
        + "\n".join(items)
        + "\n</channel>\n"
        "</rss>\n"
    )


def update_rss_file(file_path: Path, title: str, link: str, description: str, games_with_data: list[tuple[date, dict]]) -> bool:
    items = build_rss_items(games_with_data)
    latest_date = games_with_data[0][0] if games_with_data else date.today()
    content = build_rss_content(title, link, description, items, latest_date)

    existing = file_path.read_text(encoding="utf-8") if file_path.exists() else ""
    if existing == content:
        return False

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return True


def update_rss_xml(games_with_data: list[tuple[date, dict]]) -> bool:
    return update_rss_file(
        RSS_XML_FILE,
        title="4Connect",
        link=f"{BASE_URL}/",
        description="Daily 4Connect puzzle updates.",
        games_with_data=games_with_data,
    )


def update_category_rss_xml(games_with_data: list[tuple[date, dict]]) -> bool:
    category_games = defaultdict(list)
    for game_date, data in games_with_data:
        for category in data.get("categories") or []:
            category_slug = str(category).strip()
            if category_slug:
                category_games[category_slug].append((game_date, data))

    changed = False
    for category_file in sorted((ROOT / "categories").glob("*.json")):
        category_slug = category_file.stem
        category_label = format_category_label(category_slug)
        changed |= update_rss_file(
            RSS_DIR / f"{category_slug}.xml",
            title=f"4Connect - {category_label}",
            link=f"{BASE_URL}/rss/{category_slug}.xml",
            description=f"Daily 4Connect puzzle updates for {category_label}.",
            games_with_data=category_games.get(category_slug, []),
        )

    return changed


def update_all_rss_files(games_with_data: list[tuple[date, dict]]) -> bool:
    rss_xml_changed = update_rss_xml(games_with_data)
    category_rss_changed = update_category_rss_xml(games_with_data)
    return rss_xml_changed or category_rss_changed


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
        <link rel="alternate" type="application/rss+xml" title="4Connect RSS Feed" href="/rss.xml">

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
                    <img aria-hidden="true" alt="" src="/media/logo.webp" width="32" height="32">
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
                        <img aria-hidden="true" alt="" src="/media/logo.webp" width="24" height="24">
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
                                <li><a href="/rss.xml">RSS</a></li>
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


def update_archive_html(
    current_date: date,
    current_data: dict,
    max_items: int = 35,
    available_game_dates: Optional[list[date]] = None,
    date_themes: Optional[dict[date, str]] = None,
) -> bool:
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

    if available_game_dates:
        available_dates = sorted({game_date.isoformat() for game_date in available_game_dates})
    else:
        available_dates = []
        for item in updated_items:
            match = re.search(r'datetime="([^"]+)"', item)
            if match:
                available_dates.append(match.group(1))
        available_dates = sorted(set(available_dates))

    if date_themes is None:
        date_themes = {}

    if available_dates:
        payload = {
            "minDate": available_dates[0],
            "maxDate": available_dates[-1],
            "availableDates": available_dates,
            "dateThemes": {
                game_date.isoformat(): theme
                for game_date, theme in sorted(date_themes.items(), key=lambda item: item[0])
                if theme
            },
        }
        data_island = (
            '      <script id="archive-data" type="application/json">'
            + json.dumps(payload, separators=(",", ":"))
            + "</script>"
        )

        if re.search(r'<script id="archive-data" type="application/json">.*?</script>', updated, flags=re.DOTALL):
            updated = re.sub(
                r'<script id="archive-data" type="application/json">.*?</script>',
                data_island,
                updated,
                count=1,
                flags=re.DOTALL,
            )
        else:
            updated = re.sub(
                r'(<section class="more-games">.*?</section>)',
                r"\1\n\n" + data_island,
                updated,
                count=1,
                flags=re.DOTALL,
            )

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
            r'(<h2 class="game-title">\s*)(.*?)(\s*</h2>)',
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
    parser = argparse.ArgumentParser()
    parser.add_argument("--rss-only", action="store_true", help="Only update RSS feeds")
    args = parser.parse_args()

    published_game_files = find_latest_game_data_files(limit=None)

    published_games_with_data = []
    for game_date, data_file in published_game_files:
        data = json.loads(data_file.read_text(encoding="utf-8"))
        published_games_with_data.append((game_date, data))

    if args.rss_only:
        rss_changed = update_all_rss_files(published_games_with_data)
        if rss_changed:
            print(f"Updated {RSS_XML_FILE} and category feeds in {RSS_DIR}")
        else:
            print("No RSS changes needed")
        return

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

    archive_changed = update_archive_html(
        current_date,
        current_data,
        max_items=35,
        available_game_dates=[game_date for game_date, _data in published_games_with_data],
        date_themes={
            game_date: normalize_css_class(str((game_data.get("categories") or [""])[0]))
            for game_date, game_data in published_games_with_data
            if (game_data.get("categories") or [""])[0]
        },
    )
    sitemap_xml_changed = update_sitemap_xml(games_with_data=published_games_with_data)
    sitemap_html_changed = update_sitemap_html(games_with_data=published_games_with_data)
    rss_xml_changed = update_all_rss_files(games_with_data=published_games_with_data)

    changed = index_changed or archive_changed or sitemap_xml_changed or sitemap_html_changed or rss_xml_changed

    if changed:
        print(f"Updated {INDEX_FILE}, {ARCHIVE_FILE}, {SITEMAP_XML_FILE}, {SITEMAP_HTML_FILE}, {RSS_XML_FILE}, and {RSS_DIR}")
    else:
        print("No changes needed")


if __name__ == "__main__":
    main()
