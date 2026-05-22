# %%
import gspread
import requests
import os
import time
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# %%
# --- 1. SETUP & ENVIRONMENT ---
# Load environment variables from .env file
load_dotenv()
api_key = os.getenv("API_KEY")

# %%
# Configuration for Google Sheets
GOOGLE_JSON = 'service_account.json' 
SHEET_NAME = 'nd_map_coverage'  # Google Sheet name
TABS_TO_UPDATE = ['map_regions', 'map_points'] # List of tabs to update

# %%
# --- 2. GOOGLE SHEETS AUTHENTICATION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_JSON, scope)
client = gspread.authorize(creds)

try:
    sh = client.open(SHEET_NAME)
except Exception as e:
    print(f"Error: Could not open spreadsheet: {e}")
    exit()

# %%
# --- 3. PROCESSING LOOP FOR EACH TAB ---
for tab_name in TABS_TO_UPDATE:
    print(f"\n--- Processing Tab: {tab_name} ---")
    
    try:
        ws = sh.worksheet(tab_name)
    except Exception as e:
        print(f"Skipping {tab_name}: Worksheet not found.")
        continue

    # Get headers to find column positions dynamically for THIS specific tab
    headers_row = ws.row_values(1)
    
    try:
        # We use case-insensitive matching or exact matching
        iso_col_idx = headers_row.index("ISO_Code") + 1
        comp_col_idx = headers_row.index("Companies") + 1
        print(f"  Mapping found: ISO_Code (Col {iso_col_idx}), Companies (Col {comp_col_idx})")
    except ValueError:
        print(f"  Error: Headers 'ISO_Code' or 'Companies' not found in {tab_name}. Skipping...")
        continue

    # Get all data from the sheet
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):
        iso = row.get("ISO_Code")
        country = row.get("Country", "Unknown") # 'Country' is just for the log output
        
        if not iso:
            continue
        
        api_url = f"https://www.northdata.de/_api/search/v1/power?countries={iso}"
        api_headers = {
            "X-Api-Key": api_key,
            "Accept": "application/json"
        }
        
        try:
            response = requests.get(api_url, headers=api_headers)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                
                # Write back to the correct column in the current tab
                ws.update_cell(i, comp_col_idx, total)
                print(f"  ✅ {country} ({iso}): {total}")
            else:
                print(f"  ❌ {country} ({iso}): API Error {response.status_code}")
                
            # Rate limiting to stay safe
            time.sleep(1)
            
        except Exception as e:
            print(f"  ⚠️ Error processing {country} in {tab_name}: {e}")

print("\n--- ALL UPDATES COMPLETED ---")


