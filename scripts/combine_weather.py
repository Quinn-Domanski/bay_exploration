"""
Wunderground PWS JSON → Single CSV Combiner
============================================
Walks all KMDEDGEW11_YYYY-MM.json files in ../data/, flattens them into one
tidy CSV, and (optionally) removes the per-month JSON files afterward.
 
Layout:
  ./scripts/combine_wu.py   <-- this file
  ./data/KMDEDGEW11_*.json  <-- input (from get_wu.py)
  ./data/KMDEDGEW11_history.csv  <-- output
 
Usage:
  python combine_wu.py              # combine into CSV, keep JSONs
  python combine_wu.py --cleanup    # combine into CSV, then delete JSONs
"""
 
import argparse
import csv
import json
import sys
from pathlib import Path
 
# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
STATION_ID = "KMDEDGEW11"
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR   = SCRIPT_DIR.parent / "data"
OUT_CSV    = DATA_DIR / f"{STATION_ID}_history.csv"
 
# Column order in the output CSV. Defined explicitly so the schema is stable
# even if the API ever changes its key ordering.
COLUMNS = [
    "date",              # YYYY-MM-DD (local time)
    "stationID",
    "obsTimeUtc",
    "obsTimeLocal",
    "epoch",
    "lat",
    "lon",
    "qcStatus",
    "solarRadiationHigh",
    "uvHigh",
    "winddirAvg",
    "humidityHigh",
    "humidityLow",
    "humidityAvg",
    # imperial.* fields
    "tempHigh",
    "tempLow",
    "tempAvg",
    "windspeedHigh",
    "windspeedLow",
    "windspeedAvg",
    "windgustHigh",
    "windgustLow",
    "windgustAvg",
    "dewptHigh",
    "dewptLow",
    "dewptAvg",
    "windchillHigh",
    "windchillLow",
    "windchillAvg",
    "heatindexHigh",
    "heatindexLow",
    "heatindexAvg",
    "pressureMax",
    "pressureMin",
    "pressureTrend",
    "precipRate",
    "precipTotal",
]
 
TOP_LEVEL_FIELDS = [
    "stationID", "obsTimeUtc", "obsTimeLocal", "epoch", "lat", "lon",
    "qcStatus", "solarRadiationHigh", "uvHigh", "winddirAvg",
    "humidityHigh", "humidityLow", "humidityAvg",
]
IMPERIAL_FIELDS = [
    "tempHigh", "tempLow", "tempAvg",
    "windspeedHigh", "windspeedLow", "windspeedAvg",
    "windgustHigh", "windgustLow", "windgustAvg",
    "dewptHigh", "dewptLow", "dewptAvg",
    "windchillHigh", "windchillLow", "windchillAvg",
    "heatindexHigh", "heatindexLow", "heatindexAvg",
    "pressureMax", "pressureMin", "pressureTrend",
    "precipRate", "precipTotal",
]
 
 
def flatten_observation(obs: dict) -> dict:
    """Flatten one observation dict into a single flat row."""
    row = {field: obs.get(field) for field in TOP_LEVEL_FIELDS}
    imperial = obs.get("imperial") or {}
    for field in IMPERIAL_FIELDS:
        row[field] = imperial.get(field)
    # Derive a clean date column from obsTimeLocal ("YYYY-MM-DD HH:MM:SS")
    local = obs.get("obsTimeLocal") or ""
    row["date"] = local[:10] if local else None
    return row
 
 
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Delete per-month JSON files after writing the CSV.",
    )
    args = parser.parse_args()
 
    if not DATA_DIR.exists():
        print(f"Data directory not found: {DATA_DIR}")
        return 1
 
    json_files = sorted(DATA_DIR.glob(f"{STATION_ID}_*.json"))
    if not json_files:
        print(f"No {STATION_ID}_*.json files found in {DATA_DIR}")
        return 1
 
    print(f"Found {len(json_files)} JSON files in {DATA_DIR}")
 
    rows = []
    empty_months = 0
    bad_files = 0
 
    for fpath in json_files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ✗ {fpath.name}: failed to read ({e})")
            bad_files += 1
            continue
 
        obs_list = data.get("observations") or []
        if not obs_list:
            empty_months += 1
            continue
 
        for obs in obs_list:
            rows.append(flatten_observation(obs))
 
    if not rows:
        print("No observations found across any files. Nothing to write.")
        return 1
 
    # Sort by date so the CSV is chronological regardless of file order
    rows.sort(key=lambda r: (r.get("date") or "", r.get("obsTimeLocal") or ""))
 
    # Write the CSV
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
 
    print()
    print(f"✔ Wrote {len(rows)} rows to {OUT_CSV}")
    print(f"  Date range: {rows[0]['date']} → {rows[-1]['date']}")
    print(f"  Files processed: {len(json_files)}")
    print(f"  Empty months:    {empty_months}")
    print(f"  Bad files:       {bad_files}")
 
    if args.cleanup:
        if bad_files > 0:
            print()
            print(f"⚠ Skipping --cleanup because {bad_files} file(s) failed to parse.")
            print(f"  Investigate those before deleting anything.")
            return 0
        print()
        print(f"Removing {len(json_files)} JSON files...")
        for fpath in json_files:
            fpath.unlink()
        print(f"✔ Removed. Only {OUT_CSV.name} remains in {DATA_DIR}.")
 
    return 0
 
 
if __name__ == "__main__":
    sys.exit(main())