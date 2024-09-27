import argparse
import logging
import re
from datetime import datetime, date, timedelta
import sys
from typing import IO

import bs4
import requests

DATA_URL = "https://www.fussball.de/ajax.team.matchplan.loadmore/-/datum-von/{date_from}/match-type/-1/mime-type/JSON/mode/PAGE/show-venues/true/team-id/{team_id}/max/{per_page}/offset/{offset}"
GAMES_PER_PAGE = 200

logging.basicConfig(
    format="[%(asctime)s] %(levelname)s (%(module)s): %(message)s",
    level=logging.INFO,
)


def parse_games(content: str) -> list[dict]:
    """Parses game data and returns a list of games"""
    soup = bs4.BeautifulSoup(content, features="html.parser")
    rows = soup.select("tr")

    games = []
    current_game = {}
    skip_game = False

    for row in rows:
        classes = row.get("class", [])
        assert isinstance(classes, list)

        if not "row-headline" in classes and skip_game:
            continue

        if "row-headline" in classes:
            if current_game:
                if not skip_game:
                    games.append(current_game)
                current_game = {}
                skip_game = False
            headline = row.text.strip()
            m = re.search(r", (\d{2}.\d{2}.\d{4} - \d{2}:\d{2} Uhr) \| (.+)", headline)
            if not m:
                logging.debug("headline does not match pattern: %s", headline)
                skip_game = True
                continue
            current_game["datetime"] = datetime.strptime(
                m.group(1), "%d.%m.%Y - %H:%M Uhr"
            )
            current_game["competition"] = m.group(2).strip()
        elif classes == [] or classes == ["odd"]:
            club_name_divs = row.select("td.column-club>a.club-wrapper>div.club-name")
            current_game["team1"] = club_name_divs[0].text.strip()
            current_game["team2"] = club_name_divs[1].text.strip()
            details = row.select("td.column-detail>a")
            if details:
                current_game["details"] = details[0]["href"]
        elif "row-venue" in classes:
            venue = row.select('td[colspan="3"]')[0].text.strip()
            current_game["venue"] = venue

    if current_game:
        games.append(current_game)

    return games


def fetch_teamname(team_id: str) -> str:
    """Fetches the team name by its team id"""
    resp = requests.get(
        f"https://www.fussball.de/mannschaft/-/saison/2425/team-id/{team_id}/",
        allow_redirects=True,
    )
    assert resp.status_code == 200
    soup = bs4.BeautifulSoup(resp.text, features="html.parser")
    title = soup.find("title")
    assert title is not None
    return title.text


def fetch_games(
    team_id: str, date_from: date, date_to: date | None = None
) -> list[dict]:
    """Fetches game data of a given team in the timespan between date_from and date_to"""
    params = {
        "team_id": team_id,
        "per_page": GAMES_PER_PAGE,
        "offset": 0,
        "date_from": date.strftime(date_from, "%Y-%m-%d"),
    }

    date_to_param = ""
    if date_to:
        date_to_param = f"/datum-bis/{date.strftime(date_to, '%Y-%m-%d')}"

    done = False
    games = []

    while not done:
        page_url = DATA_URL.format(**params) + date_to_param
        logging.debug("fetchting %s", page_url)
        resp = requests.get(page_url)
        assert (
            resp.status_code == 200
        ), f"status code for {page_url} was {resp.status_code}"
        body = resp.json()
        assert body != {}, f"body of {page_url} was empty"
        params["offset"] += params["per_page"]
        done = body["final"]
        content = body["html"]
        games += parse_games(content)

    return games


def write_ical(team_name: str, games: list[dict], fp: IO[str]) -> None:
    """Writes a list of games to fp"""
    calendar = "BEGIN:VCALENDAR\n"
    calendar += f"X-WR-CALNAME:{team_name} Spielplan\n"

    for game in games:
        summary = f"{game['team1']} - {game['team2']}"
        description = game["competition"].replace(",", "\\,")
        dtstart = game["datetime"].strftime("%Y%m%dT%H%M%S")
        dtend = (game["datetime"] + timedelta(minutes=90 + 15)).strftime(
            "%Y%m%dT%H%M%S"
        )
        location = game["venue"].replace(",", "\\,") if "venue" in game else ""
        calendar += f"""BEGIN:VEVENT
DTSTART:{dtstart}
DTEND:{dtend}
SUMMARY:{summary}
LOCATION:{location}
DESCRIPTION:{description}
URL:{game['details'] if 'details' in game else ""}
END:VEVENT
"""

    calendar += "END:VCALENDAR\n"
    fp.write(calendar)


def main():
    arg_parser = argparse.ArgumentParser(
        description="A script for creating iCal calendars from fussball.de team game plans"
    )
    arg_parser.add_argument(
        "--teamid",
        dest="team_id",
        required=True,
        help="the team's fussball.de id",
    )
    arg_parser.add_argument(
        "--from",
        dest="date_from",
        required=True,
        help="yyyy-mm-dd",
    )
    arg_parser.add_argument(
        "--to",
        dest="date_to",
        required=False,
        help="yyyy-mm-dd",
    )
    arg_parser.add_argument(
        "--output",
        dest="output_file",
    )
    arg_parser.add_argument(
        "--debug",
        dest="debug",
        action="store_const",
        const=True,
        help="Enable debug logging",
    )

    args = arg_parser.parse_args()
    date_from = datetime.strptime(args.date_from, "%Y-%m-%d").date()
    date_to = (
        datetime.strptime(args.date_to, "%Y-%m-%d").date() if args.date_to else None
    )

    if args.debug:
        logging.root.setLevel(logging.DEBUG)

    logging.debug("fetching team name")
    team_name = fetch_teamname(args.team_id)
    logging.debug("fetching games")
    games = fetch_games(args.team_id, date_from, date_to)

    if args.output_file:
        logging.debug("writing calendar to %s", args.output_file)
        with open(args.output_file, "w") as f:
            write_ical(team_name, games, f)
    else:
        write_ical(team_name, games, sys.stdout)

    logging.debug("done")


if __name__ == "__main__":
    main()
