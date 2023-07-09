# fubade-ics
A Python script to generate iCal calendars from fussball.de game data.

## Usage

Run the script by passing the team id and a start date to fetch all games.

``` text
$ python3 fubade-ics.py --teamid 011MIBR3HK000000VTVG0001VTR8C1K7 --from 2023-07-01
```

The time span can be limitted by passing the `to` parameter.

``` text
$ python3 fubade-ics.py --teamid 011MIBR3HK000000VTVG0001VTR8C1K7 --from 2023-07-01 --to 2023-12-31
```

The output file can be specified using the `--output` parameter or by redirecting standard out.

``` text
$ python3 fubade-ics.py --teamid 011MIBR3HK000000VTVG0001VTR8C1K7 --from 2023-07-01 --output calendar.ics
```

``` text
$ python3 fubade-ics.py --teamid 011MIBR3HK000000VTVG0001VTR8C1K7 --from 2023-07-01 > calendar.ics
```
