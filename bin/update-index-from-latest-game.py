#!/usr/bin/env python3

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


def find_latest_game_data_file() -> Path:
    latest = None
    latest_date = None

    for data_file in GAMES_DIR.glob("*/*/*/data.json"):
        try:
            year = int(data_file.parts[-4])
            month = int(data_file.parts[-3])
            day = int(data_file.parts[-2])
            current_date = date(year, month, day)
        except (ValueError, IndexError):
            continue

        if latest_date is None or current_date > latest_date:
            latest_date = current_date
            latest = data_file

    if latest is None:
        raise RuntimeError("No game data files found in games/YYYY/MM/DD/data.json")

    return latest


def update_index_html(game_date: date, date_long: str, game_payload: str, previous_link: str) -> bool:
    html = INDEX_FILE.read_text(encoding="utf-8")

    updated = re.sub(
        r'<time datetime="[^"]+" class="game-date pill">[^<]+</time>',
        f'<time datetime="{game_date.isoformat()}" class="game-date pill">{date_long}</time>',
        html,
        count=1,
    )

    updated = re.sub(
        r"<four-connect data='[^']*'></four-connect>",
        f"<four-connect data='{game_payload}'></four-connect>",
        updated,
        count=1,
    )

    updated = re.sub(
        r'<a href="[^"]+" class="play-now-link">',
        f'<a href="{previous_link}" class="play-now-link">',
        updated,
        count=1,
    )

    if updated == html:
        return False

    INDEX_FILE.write_text(updated, encoding="utf-8")
    return True


def main() -> None:
    data_file = find_latest_game_data_file()
    data = json.loads(data_file.read_text(encoding="utf-8"))

    date_from_path = date(int(data_file.parts[-4]), int(data_file.parts[-3]), int(data_file.parts[-2]))
    date_str = data.get("date", date_from_path.isoformat())
    game_date = parse_iso_date(date_str)

    date_long = data.get("dateLong", format_long_date(game_date))
    game_payload = json.dumps(data["game"], separators=(",", ":"))

    previous_date = game_date - timedelta(days=1)
    previous_link = f"/games/{previous_date:%Y/%m/%d}/"

    changed = update_index_html(game_date, date_long, game_payload, previous_link)

    if changed:
        print(f"Updated {INDEX_FILE} using {data_file}")
    else:
        print("No changes needed")


if __name__ == "__main__":
    main()