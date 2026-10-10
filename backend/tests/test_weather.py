"""NOAA GHCN-Daily parsing and the live weather branch (D29); no network: S3 and HTTP are stubbed."""
from backend.adapters import weather

CSV = """ID,DATE,ELEMENT,DATA_VALUE,M_FLAG,Q_FLAG,S_FLAG,OBS_TIME
IN022021900,20230928,TMAX,352,,,S,
IN022021900,20230928,TMIN,214,,,S,
IN022021900,20230929,TMAX,352,,,S,
IN022021900,20230929,TMIN,214,,,S,
IN022021900,20230929,TAVG,278,H,,S,
IN022021900,20230930,TAVG,999,,X,S,
IN022021900,20230930,PRCP,5,,,S,
"""
STATIONS = ("IN022021900  28.5830   77.2000  216.0    NEW DELHI/SAFDARJUN            GSN     42182\n"
            "IN001030601  13.2000   78.7500  684.0    PALAMNER                                    \n")


def _stub(monkeypatch):
    monkeypatch.setattr(weather, "_stations", None)
    monkeypatch.setattr(weather, "_noaa_text", lambda key: STATIONS if key == "ghcnd-stations.txt" else CSV)


def test_ghcn_daily_mean(monkeypatch):
    _stub(monkeypatch)
    d = weather.fetch_ghcn_daily("IN022021900", "2023-09-28", "2023-09-30")
    # TAVG wins; else mean of TMAX and TMIN; a quality-flagged value is dropped (no 2023-09-30)
    assert d["time"] == ["2023-09-28", "2023-09-29"] and d["temperature_c"] == [28.3, 27.8]
    assert d["source_url"] == "s3://noaa-ghcn-pds/csv/by_station/IN022021900.csv"


def test_live_temperature_branches(monkeypatch):
    _stub(monkeypatch)
    monkeypatch.setattr(weather, "forecast_mean_c", lambda lat, lon, day: 31.0)
    assert weather.live_temperature_c(28.72, 77.16, "2026-10-10", today="2026-10-10") == 31.0  # forecast
    assert weather.live_temperature_c(28.72, 77.16, "2023-09-29", today="2026-10-10") == 27.8  # nearest station
    assert weather.live_temperature_c(19.07, 72.88, "2023-09-29", today="2026-10-10") is None  # no station in 50 km


def test_live_temperature_skips_stations_without_data(monkeypatch):
    """Mumbai: the three nearest stations stopped reporting; the 4th (Santacruz) has the day."""
    stations = "".join(f"IN01207{i:04d}  {18.94 + i * 0.01:.4f}   72.8350   10.0    TEST STATION {i}\n" for i in range(4))
    rows = "ID,DATE,ELEMENT,DATA_VALUE,M_FLAG,Q_FLAG,S_FLAG,OBS_TIME\nIN012070003,20230929,TAVG,287,,,S,\n"
    monkeypatch.setattr(weather, "_stations", None)
    monkeypatch.setattr(weather, "_noaa_text", lambda key: stations if key == "ghcnd-stations.txt" else (
        rows if key.endswith("IN012070003.csv") else "ID,DATE,ELEMENT,DATA_VALUE,M_FLAG,Q_FLAG,S_FLAG,OBS_TIME\n"))
    assert weather.live_temperature_c(18.94, 72.835, "2023-09-29", today="2026-10-10") == 28.7
