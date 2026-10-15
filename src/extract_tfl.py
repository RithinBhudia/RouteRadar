# ============================================================
# TfL Tube Line Status API Extraction
# ===========================================================

# ===========================================================
# This file creates:
# - Folder: data/raw/api
# - JSON file: tube_status_{timestamp}.json
#
# Each API request creates a new timestamped JSON file.
# ===========================================================


import os
from pathlib import Path
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

# Load API key from .env
load_dotenv()

api_key = os.getenv("KEY")

if not api_key:
    raise ValueError("TfL API key not found in .env")

# TfL line status
url = "https://api.tfl.gov.uk/Line/Mode/tube/Status"

response = requests.get(url,
                        params={"detail": "true", "app_key": api_key},
                        timeout=30
)

response.raise_for_status()

# Save original API response unchanged
folder = Path("data/raw/api")
folder.mkdir(parents=True, exist_ok=True)

timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")

filename = folder / f"tube_status_{timestamp}.json"
filename.write_bytes(response.content)

print("Success! TfL API connected.")
print(f"Saved data to: {filename}")
