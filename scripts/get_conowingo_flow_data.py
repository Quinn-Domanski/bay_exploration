import requests
import pandas as pd
import os


site_id = "01578310" 
param_code = "00060" 
start_date = "2017-01-01"
end_date = "2025-12-31"

url = f"https://waterservices.usgs.gov/nwis/dv/?format=json&sites={site_id}&parameterCd={param_code}&startDT={start_date}&endDT={end_date}"

print(f"Target URL constructed: {url}")
print("Fetching data from government servers... (This might take a few seconds)")


response = requests.get(url)

if response.status_code == 200:

    print("Connection Successful! Parsing JSON payload...")
    raw_data = response.json()
    
    try:

        time_series = raw_data['value']['timeSeries'][0]['values'][0]['value']
    
        clean_data = []
        for day in time_series:
            clean_data.append({
                'Date': day['dateTime'][:10],
                'Flow_cfs': float(day['value'])
            })

        conowingo_df = pd.DataFrame(clean_data)
        conowingo_df['Date'] = pd.to_datetime(conowingo_df['Date'])
        conowingo_df.set_index('Date', inplace=True)

        output_dir = "../data"
        output_file = f"{output_dir}/conowingo_flow_data.csv"

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")  
        conowingo_df.to_csv(output_file)

        print(f"\nPipeline Complete! Retrieved {len(conowingo_df)} days of flow data.")
        print(f"Data successfully saved to: {output_file}")
    
    except KeyError:
        print("Error: The USGS server returned JSON, but the structure was unexpected.")

else:
    print(f"API Connection Failed. HTTP Status Code: {response.status_code}")