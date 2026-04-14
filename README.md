# Investigating Bidirectional Dynamics in Chesapeake Bay Tributaries 🌊

**Author:** Quinn Domanski  
**Institution:** Anne Arundel Community College Environmental Center  

## Project Overview
Long-term monitoring across the Chesapeake Bay watershed has documented overall declines in nitrogen loading to the tidal Bay, yet nutrient dynamics within tidal tributaries remain complex. This repository contains the data pipeline, exploratory data analysis, and machine learning models developed to investigate bidirectional nutrient exchange (specifically elevated nitrate and nitrite concentrations) near the mouth of tributaries. 

By integrating long-term monitoring data with predictive modeling, this project aims to predict conditions associated with these elevated nutrient levels using seasonal, hydrologic, and weather variables.

## Data Sources
* **Maryland Department of Natural Resources (Eyes on the Bay):** 40 years of high-quality nutrient data from the Chesapeake Bay and its tributaries.
* *(Planned) USGS National Water Information System:* Conowingo Dam discharge rates.
* *(Planned) NOAA NCEI:* Historical precipitation and weather data for the watershed.

---

## Local Environment Setup (Linux)

To run this project locally, you will need Python 3 installed on your machine. This project strictly isolates dependencies using a Python virtual environment (`venv`).

### 1. Clone the Repository
Clone this repository to your local machine and navigate into the project directory:
```bash
git clone https://github.com/Quinn-Domanski/bay_exploration.git
cd bay_exploration
```

### 2. Create and Activate the Virtual Environment
Create a clean virtual environment named `venv` to avoid package conflicts:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
Install all required scientific computing and machine learning libraries:
```bash
pip install -r requirements.txt
```

### 4. Configure the Jupyter Notebook Kernel
To ensure Jupyter Notebook uses the packages from your isolated virtual environment instead of your global system Python, install the virtual environment as a specific Jupyter kernel:
```bash
# Ensure ipykernel is installed in your virtual environment
pip install ipykernel

# Register the virtual environment as a kernel
python -m ipykernel install --user --name=bay_venv --display-name "Python (Bay Project venv)"
```

### 5. Launch the Project
Start the Jupyter Notebook server:
```bash
jupyter notebook
```
*Note: When you open `bay_data_exploration.ipynb` or any other notebook, ensure that the kernel selected in the top right corner is set to **"Python (Bay Project venv)"**.*
