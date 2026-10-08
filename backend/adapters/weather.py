"""Hourly temperature and relative humidity from the Open-Meteo historical archive (free, no key).

Snapshot use: python backend/adapters/weather.py 2025-01-01 2025-05-31
writes data/snapshot/weather_kolar_<from>_<to>.json for every market in config/markets.json.
"""
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"


def archive_url(lat, lon, start, end):
    q = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
         "hourly": "temperature_2m,relative_humidity_2m", "timezone": "Asia/Kolkata"}
    return ARCHIVE + "?" + urllib.parse.urlencode(q)


def fetch_hourly(lat, lon, start, end):
    """{source_url, time[], temperature_c[], relative_humidity_pct[]}; hours Open-Meteo lacks stay None."""
    url = archive_url(lat, lon, start, end)
    with urllib.request.urlopen(url, timeout=60) as r:
        h = json.load(r)["hourly"]
    return {"source_url": url, "time": h["time"], "temperature_c": h["temperature_2m"],
            "relative_humidity_pct": h["relative_humidity_2m"]}


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[2]
    start, end = sys.argv[1:3]
    markets = json.loads((root / "config/markets.json").read_text())["markets"]
    out = {"source": "Open-Meteo historical weather archive", "timezone": "Asia/Kolkata",
           "units": {"temperature_c": "deg C at 2 m", "relative_humidity_pct": "% at 2 m"}, "from": start, "to": end,
           "markets": {m["market_id"]: {"lat": m["lat"], "lon": m["lon"], **fetch_hourly(m["lat"], m["lon"], start, end)}
                       for m in markets}}
    path = root / f"data/snapshot/weather_kolar_{start}_{end}.json"
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(path.relative_to(root), {k: len(v["time"]) for k, v in out["markets"].items()})
