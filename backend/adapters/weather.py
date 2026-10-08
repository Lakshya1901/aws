"""Hourly temperature and relative humidity: Open-Meteo historical archive, or NASA POWER (D16 fallback).

Both are free and need no key. Snapshot use:
  python backend/adapters/weather.py 2025-01-01 2025-05-31 [open-meteo|power]
writes data/snapshot/weather_<source>_kolar_<from>_<to>.json for every market in config/markets.json.
"""
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
POWER = "https://power.larc.nasa.gov/api/temporal/hourly/point"


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


def fetch_hourly_power(lat, lon, start, end):
    """Same shape as fetch_hourly, from NASA POWER (MERRA-2 based) in local solar time; fill values become None."""
    q = {"parameters": "T2M,RH2M", "community": "AG", "latitude": lat, "longitude": lon, "format": "JSON",
         "start": start.replace("-", ""), "end": end.replace("-", ""), "time-standard": "LST"}
    url = POWER + "?" + urllib.parse.urlencode(q)
    with urllib.request.urlopen(url, timeout=120) as r:
        d = json.load(r)
    fill, p = d["header"]["fill_value"], d["properties"]["parameter"]
    keys = sorted(p["T2M"])
    return {"source_url": url, "time": [f"{k[:4]}-{k[4:6]}-{k[6:8]}T{k[8:10]}:00" for k in keys],
            "temperature_c": [None if p["T2M"][k] == fill else p["T2M"][k] for k in keys],
            "relative_humidity_pct": [None if p["RH2M"][k] == fill else p["RH2M"][k] for k in keys]}


SOURCES = {"open-meteo": ("Open-Meteo historical weather archive", "Asia/Kolkata", fetch_hourly),
           "power": ("NASA POWER hourly (MERRA-2), https://power.larc.nasa.gov", "local solar time", fetch_hourly_power)}


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[2]
    start, end = sys.argv[1:3]
    src = sys.argv[3] if len(sys.argv) > 3 else "open-meteo"
    name, tz, fetch = SOURCES[src]
    markets = json.loads((root / "config/markets.json").read_text())["markets"]
    out = {"source": name, "timezone": tz,
           "units": {"temperature_c": "deg C at 2 m", "relative_humidity_pct": "% at 2 m"}, "from": start, "to": end,
           "markets": {m["market_id"]: {"lat": m["lat"], "lon": m["lon"], **fetch(m["lat"], m["lon"], start, end)}
                       for m in markets}}
    path = root / f"data/snapshot/weather_{src}_kolar_{start}_{end}.json"
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(path.relative_to(root), {k: len(v["time"]) for k, v in out["markets"].items()})
