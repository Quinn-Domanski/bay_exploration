import requests
from bs4 import BeautifulSoup
import re
import time

base_url = 'https://eyesonthebay.dnr.maryland.gov/bay_cond/LongTermData.cfm'
response = requests.get(base_url)
# print(response.text)

soup = BeautifulSoup(response.text, 'html.parser')
# print(soup.prettify())

tag = soup.find_all('select', {'name':'station'})
print(tag)

value_num = re.findall(r'<option value="(.*?)">.*?</option>', str(tag))
print(type(value_num))
print(len(value_num))

"""
https://eyesonthebay.dnr.maryland.gov/bay_cond/GetLongTermDataHub_fromquery.cfm?station=1252&station=1253&station=1460&StartDate=1984-01-16&EndDate=2025-12-14&parameter=123&parameter=83&parameter=94&parameter=31&parameter=73&parameter=21&parameter=81&parameter=110&parameter=114
"""

"""
https://eyesonthebay.dnr.maryland.gov/bay_cond/GetLongTermDataHub_fromquery.cfm?station=1162&StartDate=1984-01-16&EndDate=2025-12-14&parameter=123&parameter=83&parameter=94&parameter=31&parameter=73&parameter=21&parameter=74&parameter=85&parameter=55&parameter=116&parameter=121&parameter=49&parameter=7&parameter=87&parameter=109&parameter=104&parameter=111&parameter=35&parameter=30&parameter=77&parameter=81&parameter=60&parameter=63&parameter=65&parameter=67&parameter=107&parameter=110&parameter=34&parameter=80&parameter=71&parameter=114&parameter=105&parameter=36&parameter=82&parameter=76&parameter=78
"""

stations = value_num
parameters = [123, 83, 94, 31, 73, 21, 74, 85, 55, 116, 121, 49, 7, 87, 109, 104, 111, 35, 30, 77, 81, 60, 63, 65, 67, 107, 110, 34, 80, 71, 114, 105, 36, 82, 76, 78] 
for i in range(0, len(stations), 3):
    cur_stations = stations[i:i+3]
    r = requests.get('https://eyesonthebay.dnr.maryland.gov/bay_cond/GetLongTermDataHub_fromquery.cfm',
                 params={'station': cur_stations,
                         'parameter': parameters,
                         'StartDate': '1984-01-16',
                         'EndDate': '2025-12-14'},
                     stream=True)
    filename = f"station_{i}_{i+len(cur_stations)}.csv"
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(8192):
            if chunk:
                f.write(chunk)
    
    print(f"Save {filename}")
    
    time.sleep(10)