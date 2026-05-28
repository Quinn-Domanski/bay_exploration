
"""
Wunderground PWS History Fetcher
=================================
Station: KMDEDGEW11 (Tandem Point, Edgewater, MD)
Range:   2017-01 through 2025-12 (108 months)
 
Pure data retrieval — no processing. Saves one JSON file per month to ../data/.
 
Layout:
  ./scripts/wu_fetch.py   <-- this file
  ./data/                  <-- output goes here
 
Rate limiting:
  - Base delay of 2 seconds between successful requests
  - Exponential backoff on 429 (rate limit) or 5xx errors: 5s, 10s, 20s, 40s, 80s
  - Hard stop on 403 (IP blocked) with a clear message
  - Skips months that already have a saved file (resumable)
"""
 
import json
import time
import sys
from pathlib import Path
from calendar import monthrange
 
import requests
 
# ---------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------
STATION_ID = "KMDEDGEW11"
API_KEY    = "e1f10a1e78da46f5b10a1e78da96f525"  # public key used by wunderground.com
BASE_URL   = "https://api.weather.com/v2/pws/history/daily"
 
START_YEAR = 2017
END_YEAR   = 2025
 
# Output directory: ../data relative to this script
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR   = SCRIPT_DIR.parent / "data"
 
# Rate limiting
BASE_DELAY_SEC      = 2.0       # delay between successful requests
BACKOFF_INITIAL_SEC = 5.0       # first retry wait
BACKOFF_MAX_SEC     = 80.0      # cap on retry wait
MAX_RETRIES         = 5         # per month before giving up
REQUEST_TIMEOUT     = 30        # seconds
 
 
# ---------------------------------------------------------------------
# FETCH ONE MONTH (with retry/backoff)
# ---------------------------------------------------------------------
def fetch_month(year: int, month: int) -> dict | None:
    """
    Fetch raw JSON for one month. Returns the parsed JSON dict, or None on
    permanent failure for that month. Raises SystemExit on 403 (IP banned).
    """
    last_day = monthrange(year, month)[1]
    params = {
        "stationId": STATION_ID,
        "format": "json",
        "units": "e",
        "startDate": f"{year:04d}{month:02d}01",
        "endDate":   f"{year:04d}{month:02d}{last_day:02d}",
        "numericPrecision": "decimal",
        "apiKey": API_KEY,
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin":  "https://www.wunderground.com",
        "Referer": "https://www.wunderground.com/",
    }
 
    wait = BACKOFF_INITIAL_SEC
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(BASE_URL, params=params, headers=headers,
                             timeout=REQUEST_TIMEOUT)
        except requests.RequestException as e:
            print(f"    network error (attempt {attempt}/{MAX_RETRIES}): {e}")
            time.sleep(wait)
            wait = min(wait * 2, BACKOFF_MAX_SEC)
            continue
 
        # Success
        if r.status_code == 200:
            try:
                return r.json()
            except ValueError:
                print(f"    200 but invalid JSON — body starts: {r.text[:120]!r}")
                return None
 
        # No content for that month (station offline / not yet installed)
        if r.status_code == 204:
            return {"observations": []}
 
        # IP banned / blocked entirely — bail out hard
        if r.status_code == 403:
            print()
            print(f"  ❌ 403 Forbidden from api.weather.com")
            print(f"     Your IP is being blocked. Possible causes:")
            print(f"       1. Datacenter / VPN IP — try a residential connection")
            print(f"       2. API key rotated — get a fresh one from DevTools:")
            print(f"          open the Wunderground dashboard in a browser,")
            print(f"          Network tab → look for a 'history/daily' request,")
            print(f"          copy the apiKey param into this script.")
            print(f"       3. You ran too many requests too fast and got blacklisted.")
            print(f"          Wait an hour and try again.")
            raise SystemExit(1)
 
        # Rate limited or server hiccup — back off and retry
        if r.status_code in (429, 500, 502, 503, 504):
            print(f"    HTTP {r.status_code} (attempt {attempt}/{MAX_RETRIES}) "
                  f"— sleeping {wait:.0f}s")
            time.sleep(wait)
            wait = min(wait * 2, BACKOFF_MAX_SEC)
            continue
 
        # Anything else: log and give up on this month
        print(f"    unexpected HTTP {r.status_code}: {r.text[:120]!r}")
        return None
 
    print(f"    gave up after {MAX_RETRIES} retries")
    return None
 
 
# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Output directory: {DATA_DIR}")
    print(f"Station: {STATION_ID}")
    print(f"Range:   {START_YEAR}-01 through {END_YEAR}-12")
    total_months = (END_YEAR - START_YEAR + 1) * 12
    print(f"Total months to fetch: {total_months}")
    print(f"Base delay: {BASE_DELAY_SEC}s  |  Backoff: up to {BACKOFF_MAX_SEC}s")
    print()
 
    fetched = skipped = failed = 0
 
    for year in range(START_YEAR, END_YEAR + 1):
        for month in range(1, 13):
            fname = f"{STATION_ID}_{year:04d}-{month:02d}.json"
            fpath = DATA_DIR / fname
 
            # Resume: skip months already on disk
            if fpath.exists():
                skipped += 1
                continue
 
            print(f"  {year}-{month:02d} ... ", end="", flush=True)
            data = fetch_month(year, month)
 
            if data is None:
                print("FAILED")
                failed += 1
                # Still sleep so we don't hammer on consecutive failures
                time.sleep(BASE_DELAY_SEC)
                continue
 
            # Save raw JSON exactly as returned
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            n_obs = len(data.get("observations") or [])
            print(f"saved ({n_obs} days)")
            fetched += 1
 
            # Polite delay before the next request
            time.sleep(BASE_DELAY_SEC)
 
    print()
    print(f"Done. Fetched: {fetched}  |  Already on disk: {skipped}  |  Failed: {failed}")
    print(f"Files in {DATA_DIR}")
    return 0 if failed == 0 else 2
 
 
if __name__ == "__main__":
    sys.exit(main())