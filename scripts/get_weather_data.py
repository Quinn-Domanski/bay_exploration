import os
import sys
import time
import math
import requests
import pandas as pd
from pathlib import Path

print("=== INITIATING NOAA GEOSPATIAL WEATHER EXTRACTION ===")

NOAA_TOKEN = "PWTSQulWYzPsDvVHGWZIdpuUHQFOTVOt"

RHODE_LAT = 38.880
RHODE_LON = -76.535
SEARCH_RADIUS_KM = 40

REQUIRED_STATIONS = [
    "GHCND:USW00013752",  # Annapolis Naval Academy ASOS
    "GHCND:US1MDAA0001",  # Birdsville CoCoRaHS
]

MAX_STATIONS = 5

START_YEAR = 2017
END_YEAR = 2024

DATATYPES = ["PRCP", "AWND", "WDF2", "TMAX", "TMIN"]

SCRIPT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = SCRIPT_DIR.parent / "data"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_CSV = OUTPUT_DIR / f"Rhode_River_Weather_{START_YEAR}_{END_YEAR}.csv"

BASE = "https://www.ncei.noaa.gov/cdo-web/api/v2"
HEADERS = {"token": NOAA_TOKEN}
REQUEST_SLEEP = 0.25
MAX_RETRIES = 5

def cdo_get(endpoint: str, params: dict) -> dict:
    """GET with exponential backoff to handle fragile government servers."""
    url = f"{BASE}/{endpoint}"
    for attempt in range(1, MAX_RETRIES + 1):
        r = requests.get(url, headers=HEADERS, params=params, timeout=30)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503, 504):
            wait = 2 ** attempt
            print(f"   Server hiccup ({r.status_code}); backing off {wait}s "
                  f"(attempt {attempt}/{MAX_RETRIES})")
            time.sleep(wait)
            continue
        raise RuntimeError(f"CDO {endpoint} failed {r.status_code}: {r.text[:200]}")
    raise RuntimeError(f"CDO {endpoint} failed after {MAX_RETRIES} retries")

def haversine_km(lat1, lon1, lat2, lon2):
    """Calculates the Great Circle distance between two points on Earth."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))

def km_to_degrees(km):
    """Rough bounding box conversion."""
    return km / 111.0

def discover_prcp_stations(lat, lon, radius_km, start_year, end_year):
    """Find GHCND stations near (lat, lon) that report PRCP."""
    d = km_to_degrees(radius_km)
    extent = f"{lat - d},{lon - d},{lat + d},{lon + d}"
    found = []
    offset = 1
    while True:
        params = {
            "datasetid": "GHCND",
            "datatypeid": "PRCP",
            "extent": extent,
            "startdate": f"{start_year}-01-01",
            "enddate": f"{end_year}-12-31",
            "limit": 1000,
            "offset": offset,
        }
        js = cdo_get("stations", params)
        results = js.get("results", [])
        if not results:
            break
        found.extend(results)
        if len(results) < 1000:
            break
        offset += 1000
        time.sleep(REQUEST_SLEEP)
    return found

def select_stations(required, discovered, max_total, center_lat, center_lon):
    """Combine required + closest discovered, dedupe, cap at max_total."""
    by_id = {s["id"]: s for s in discovered}
    selected = []
    seen = set()
    
    for sid in required:
        if sid in by_id:
            s = by_id[sid]
        else:
            print(f"   Fetching metadata for required station {sid}")
            try:
                s = cdo_get(f"stations/{sid}", {})
                time.sleep(REQUEST_SLEEP)
            except Exception as e:
                print(f"   WARNING: could not fetch {sid}: {e}")
                continue
        s["_distance_km"] = haversine_km(center_lat, center_lon, s["latitude"], s["longitude"])
        selected.append(s)
        seen.add(sid)

    others = [s for s in discovered if s["id"] not in seen]
    for s in others:
        s["_distance_km"] = haversine_km(center_lat, center_lon, s["latitude"], s["longitude"])
    others.sort(key=lambda s: s["_distance_km"])

    while len(selected) < max_total and others:
        selected.append(others.pop(0))

    return selected

def fetch_year_for_station(station_id, year):
    """Paginate one year of daily data for one station."""
    out = []
    offset = 1
    limit = 1000
    while True:
        params = {
            "datasetid": "GHCND",
            "stationid": station_id,
            "startdate": f"{year}-01-01",
            "enddate": f"{year}-12-31",
            "datatypeid": DATATYPES,
            "limit": limit,
            "offset": offset,
            "includemetadata": "false",
        }
        js = cdo_get("data", params)
        results = js.get("results", [])
        if not results:
            break
        out.extend(results)
        if len(results) < limit:
            break
        offset += limit
        time.sleep(REQUEST_SLEEP)
    return out

DIVIDE_BY_10 = {"PRCP", "AWND", "TMAX", "TMIN"}

def clean_records(records):
    """Pivot long -> wide, apply units, honor QC flags."""
    if not records:
        return pd.DataFrame()
    df = pd.DataFrame(records)
    if "attributes" in df.columns:
        qflag = df["attributes"].fillna("").str.split(",").str[1]
        bad = qflag.fillna("").str.strip() != ""
        if bad.any():
            print(f"   Dropping {int(bad.sum())} records with failed QC flags")
        df = df.loc[~bad].copy()

    df["value_scaled"] = df.apply(
        lambda r: r["value"] / 10.0 if r["datatype"] in DIVIDE_BY_10 else float(r["value"]),
        axis=1,
    )

    wide = df.pivot_table(
        index=["station", "date"],
        columns="datatype",
        values="value_scaled",
        aggfunc="first",
    ).reset_index()
    wide["date"] = pd.to_datetime(wide["date"]).dt.tz_localize(None).dt.normalize()

    rename = {"PRCP": "PRCP_mm", "AWND": "AWND_mps", "WDF2": "WDF2_deg",
              "TMAX": "TMAX_C", "TMIN": "TMIN_C"}
    wide = wide.rename(columns={k: v for k, v in rename.items() if k in wide.columns})
    return wide

def main():
    if not NOAA_TOKEN or NOAA_TOKEN == "YOUR_TOKEN_HERE":
        sys.exit("ERROR: Please insert your NOAA API token into the script.")

    print(f"Center: ({RHODE_LAT}, {RHODE_LON})  radius: {SEARCH_RADIUS_KM} km")
    print(f"Years:  {START_YEAR}-{END_YEAR}")

    print("\nPhase 1: Discovering nearby stations...")
    discovered = discover_prcp_stations(RHODE_LAT, RHODE_LON, SEARCH_RADIUS_KM, START_YEAR, END_YEAR)
    selected = select_stations(REQUIRED_STATIONS, discovered, MAX_STATIONS, RHODE_LAT, RHODE_LON)
    
    if not selected:
        sys.exit("ERROR: No stations selected.")

    meta_df = pd.DataFrame([{
        "station": s["id"],
        "name": s.get("name"),
        "latitude": s.get("latitude"),
        "longitude": s.get("longitude"),
        "distance_km": round(s["_distance_km"], 2)
    } for s in selected]).sort_values("distance_km")

    print("\n   Selected stations:")
    print(meta_df.to_string(index=False))

    print("\nPhase 2: Fetching daily weather data (This will take a minute or two)...")
    all_records = []
    for sid in meta_df["station"]:
        for yr in range(START_YEAR, END_YEAR + 1):
            print(f"   Fetching {sid} for {yr}...")
            recs = fetch_year_for_station(sid, yr)
            all_records.extend(recs)

    if not all_records:
        sys.exit("ERROR: No records returned.")

    print(f"\nPhase 3: Cleaning {len(all_records)} raw records and applying unit conversions...")
    by_station = clean_records(all_records)
    by_station = by_station.merge(meta_df[["station", "name", "latitude", "longitude", "distance_km"]],
                                  on="station", how="left")

    front = ["station", "name", "distance_km", "latitude", "longitude", "date"]
    rest = [c for c in by_station.columns if c not in front]
    by_station = by_station[front + rest].sort_values(["station", "date"])
    
    by_station.to_csv(OUT_CSV, index=False)
    print(f"\n✅ SUCCESS! Data saved to: {OUT_CSV}")
    print(f"Extracted {len(by_station)} rows of cleaned data.")

if __name__ == "__main__":
    main()