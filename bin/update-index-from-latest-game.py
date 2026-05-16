#!/usr/bin/env python3

import html as html_utils
import json
import re
from datetime import date, datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GAMES_DIR = ROOT / "games"
INDEX_FILE = ROOT / "index.html"


def parse_iso_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def format_long_date(value: date) -> str:
    # Avoid platform-specific day formatting flags.
    return value.strftime("%B %d, %Y").replace(" 0", " ")


def format_short_date(value: date) -> str:
    """Format date as 'Mon DD' (e.g., 'May 11')."""
    return value.strftime("%b %d").replace(" 0", " ")


def find_latest_game_data_files(limit: int = 7) -> list[tuple[date, Path]]:
    """Find latest N game data files, sorted by date descending."""
    games = []

    for data_file in GAMES_DIR.glob("*/*/*/data.json"):
        try:
            year = int(data_file.parts[-4])
            month = int(data_file.parts[-3])
            day = int(data_file.parts[-2])
            current_date = date(year, month, day)
        except (ValueError, IndexError):
            continue

        games.append((current_date, data_file))

    if not games:
        raise RuntimeError("No game data files found in games/YYYY/MM/DD/data.json")

    games.sort(key=lambda x: x[0], reverse=True)
    return games[:limit]


def build_previous_games_html(games_with_data: list[tuple[date, dict]]) -> str:
    """Build previous games list (skip first/current game, take next 6)."""
    items = []
    for game_date, data in games_with_data[1:7]:
        date_str = game_date.isoformat()
        display = format_short_date(game_date)
        items.append(f'            <li><a href="/archive.html#{date_str}">{display}</a></li>')
    
    # Add "View All" link
    items.append('            <li><a href="/archive.html">View All <span class="a11y-hidden">previous games</span></a></li>')
    return "\n".join(items)


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
            r'(<p class="game-title">\s*)(.*?)(\s*</p>)',
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
    game_files = find_latest_game_data_files(limit=7)

    # Load all game data
    games_with_data = []
    for game_date, data_file in game_files:
        data = json.loads(data_file.read_text(encoding="utf-8"))
        games_with_data.append((game_date, data))

    # Current game (first/latest)
    current_date, current_data = games_with_data[0]
    date_long = current_data.get("dateLong", format_long_date(current_date))
    game_title = current_data.get("title", "")
    game_payload = json.dumps(current_data["game"], separators=(",", ":"))

    previous_date = current_date - timedelta(days=1)
    previous_link = f"/games/{previous_date:%Y/%m/%d}/"

    # Build previous games section
    previous_games_html = build_previous_games_html(games_with_data)

    changed = update_index_html(
        current_date,
        date_long,
        game_title,
        game_payload,
        previous_link,
        previous_games_html,
    )

    if changed:
        print(f"Updated {INDEX_FILE} with latest game and previous games")
    else:
        print("No changes needed")


if __name__ == "__main__":
    main()
