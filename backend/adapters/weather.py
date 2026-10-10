"""Temperature for the spoilage model (CLAUDE.md Section 8.1, D16, D29).

Snapshots (replay days, read by backend/adapters/store.py):
  python backend/adapters/weather.py 2025-01-01 2025-05-31 [open-meteo|power]
    hourly Open-Meteo archive or NASA POWER at every market in config/markets.json -> weather_<source>_kolar_*.json
  python backend/adapters/weather.py 2023-09-01 2023-09-30 ghcn <station_id>[,<station_id>...] <region>
    daily mean temperature from NOAA GHCN-Daily on the AWS Registry of Open Data (public S3 bucket noaa-ghcn-pds,
    no account needed): TAVG, else the mean of TMAX and TMIN; quality-flagged values dropped
    -> weather_ghcn_<region>_<from>_<to>.json (one entry per day; store.temperature_c averages a day's entries).
Live (no snapshot covers the day, WEATHER_LIVE=1 on the Lambda): live_temperature_c.
"""
import csv
import io
import json
import pathlib
import sys
import urllib.parse
import urllib.request

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
NOAA_BUCKET = "noaa-ghcn-pds"  # AWS Registry of Open Data: https://registry.opendata.aws/noaa-ghcn/
GHCN_MAX_KM = 50
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


def _noaa_s3():
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
    return boto3.client("s3", region_name="us-east-1", config=Config(signature_version=UNSIGNED))


def _noaa_text(key):
    return _noaa_s3().get_object(Bucket=NOAA_BUCKET, Key=key)["Body"].read().decode("utf-8")


_stations = None


def ghcn_stations():
    """India stations from ghcnd-stations.txt: [(id, lat, lon, name)] (fixed-width format, see the bucket's readme)."""
    global _stations
    if _stations is None:
        _stations = [(ln[:11], float(ln[12:20]), float(ln[21:30]), ln[41:71].strip())
                     for ln in _noaa_text("ghcnd-stations.txt").splitlines() if ln.startswith("IN")]
    return _stations


def fetch_ghcn_daily(station, start, end):
    """{source_url, time[YYYY-MM-DD], temperature_c[]}: TAVG, else (TMAX + TMIN) / 2; values with a quality flag
    are dropped; days without a value are left out."""
    key = f"csv/by_station/{station}.csv"
    lo, hi = start.replace("-", ""), end.replace("-", "")
    day = {}
    for r in csv.DictReader(io.StringIO(_noaa_text(key))):
        if lo <= r["DATE"] <= hi and r["ELEMENT"] in ("TAVG", "TMAX", "TMIN") and not r["Q_FLAG"]:
            day.setdefault(r["DATE"], {})[r["ELEMENT"]] = int(r["DATA_VALUE"]) / 10  # tenths of deg C
    time, temps = [], []
    for d, v in sorted(day.items()):
        t = v.get("TAVG")
        if t is None and "TMAX" in v and "TMIN" in v:
            t = (v["TMAX"] + v["TMIN"]) / 2
        if t is not None:
            time.append(f"{d[:4]}-{d[4:6]}-{d[6:]}")
            temps.append(round(t, 1))
    return {"source_url": f"s3://{NOAA_BUCKET}/{key}", "time": time, "temperature_c": temps}


def forecast_mean_c(lat, lon, day):
    """Mean hourly forecast temperature for `day` (Asia/Kolkata) from Open-Meteo, or None."""
    q = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m", "timezone": "Asia/Kolkata",
         "start_date": day, "end_date": day}
    with urllib.request.urlopen(FORECAST + "?" + urllib.parse.urlencode(q), timeout=3) as r:
        temps = [t for t in json.load(r)["hourly"]["temperature_2m"] if t is not None]
    return sum(temps) / len(temps) if temps else None


def live_temperature_c(lat, lon, day, today):
    """Today or later: Open-Meteo forecast. Earlier days: the nearest NOAA GHCN-Daily station within GHCN_MAX_KM."""
    if day >= today:
        return forecast_mean_c(lat, lon, day)
    from backend.core.netvalue import haversine_km
    near = sorted((haversine_km(lat, lon, s_lat, s_lon), sid) for sid, s_lat, s_lon, _ in ghcn_stations())
    for km, sid in near[:3]:
        if km > GHCN_MAX_KM:
            break
        temps = fetch_ghcn_daily(sid, day, day)["temperature_c"]
        if temps:
            return temps[0]
    return None


SOURCES = {"open-meteo": ("Open-Meteo historical weather archive", "Asia/Kolkata", fetch_hourly),
           "power": ("NASA POWER hourly (MERRA-2), https://power.larc.nasa.gov", "local solar time", fetch_hourly_power)}


def ghcn_snapshot(root, start, end, station_ids, region):
    stations = {sid: (lat, lon, name) for sid, lat, lon, name in ghcn_stations()}
    out = {"source": "NOAA GHCN-Daily via the AWS Registry of Open Data (s3://noaa-ghcn-pds)", "timezone": "local day",
           "units": {"temperature_c": "daily mean deg C (TAVG, else (TMAX + TMIN) / 2)"}, "from": start, "to": end,
           "markets": {f"ghcn_{sid}": {"lat": stations[sid][0], "lon": stations[sid][1], "name": stations[sid][2],
                                       **fetch_ghcn_daily(sid, start, end)} for sid in station_ids}}
    path = root / f"data/snapshot/weather_ghcn_{region}_{start}_{end}.json"
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(path.relative_to(root), {k: len(v["time"]) for k, v in out["markets"].items()})


if __name__ == "__main__":
    root = pathlib.Path(__file__).resolve().parents[2]
    start, end = sys.argv[1:3]
    src = sys.argv[3] if len(sys.argv) > 3 else "open-meteo"
    if src == "ghcn":
        ghcn_snapshot(root, start, end, sys.argv[4].split(","), sys.argv[5])
        sys.exit(0)
    name, tz, fetch = SOURCES[src]
    markets = json.loads((root / "config/markets.json").read_text())["markets"]
    out = {"source": name, "timezone": tz,
           "units": {"temperature_c": "deg C at 2 m", "relative_humidity_pct": "% at 2 m"}, "from": start, "to": end,
           "markets": {m["market_id"]: {"lat": m["lat"], "lon": m["lon"], **fetch(m["lat"], m["lon"], start, end)}
                       for m in markets}}
    path = root / f"data/snapshot/weather_{src}_kolar_{start}_{end}.json"
    path.write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(path.relative_to(root), {k: len(v["time"]) for k, v in out["markets"].items()})
