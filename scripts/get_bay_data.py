import requests
from bs4 import BeautifulSoup
import re
import time
from tqdm import tqdm

BASE_URL = 'https://eyesonthebay.dnr.maryland.gov/bay_cond/LongTermData.cfm'
DATA_URL = "https://eyesonthebay.dnr.maryland.gov/bay_cond/GetLongTermDataHub_fromquery.cfm"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": BASE_URL
}

PARAMETERS = [
    123, 83, 94, 31, 73, 21, 74, 85, 55, 116, 121, 49, 7, 87, 109,
    104, 111, 35, 30, 77, 81, 60, 63, 65, 67, 107, 110, 34, 80,
    71, 114, 105, 36, 82, 76, 78
]

OUTFILE = "eyes_on_the_bay_all_stations.csv"

#Get Stations List
response = requests.get(BASE_URL, headers=HEADERS)
soup = BeautifulSoup(response.text, "html.parser")

stations = []

for opt in soup.select('select[name="station"] option'):
    value = opt.get("value")
    if value:
        stations.append(value)

print(f"found {len(stations)} stations")

# Download Data 3 per request with a break
first_write  = True

with open(OUTFILE, "wb") as f:
    pass #Create file to truncate

for i in tqdm(range(0, len(stations), 3), desc="Downloading Station Batches..."):
    cur_stations = stations[i:i+3]
    
    params = {
        "station" : cur_stations,
        "parameter": PARAMETERS,
        "StartDate": "1984-01-16",
        "EndDate": "2025-12-23"
    }
    
    r = requests.get(DATA_URL, params = params, headers = HEADERS)
    
    content_type = r.headers.get("Content-Type", "")
    if "text/csv" not in content_type:
        print(f"\nHTML returned for stations {cur_stations}, skipping...")
        continue
    
    lines = re.content.splitlines()
    
    with open(OUTFILE, "ab") as f:
        if first_write:
            f.write(b"\n".join(lines) + b"\n")
            first_write = False
        else:
            f.write(b"\n".join(lines[1:])+ b"\n")
    
    time.sleep(2)
