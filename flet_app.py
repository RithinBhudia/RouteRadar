# This is written only for the app.
#  It should not be treated as part of the repository yet.

import os
from datetime import datetime
from pathlib import Path
import duckdb
import flet as ft
import flet_charts as fch

# project directory
ROOT = Path(__file__).resolve().parent

BUNDLED_DB = Path(os.environ.get("FLET_ASSETS_DIR", str(ROOT / "assets"))) / "data"
LOCAL_DB = ROOT/"data/processed/routeradar.duckdb"
DATABASE = BUNDLED_DB if BUNDLED_DB.exists() else LOCAL_DB

background = "#FFFCF7"
background2 = "#F0E9E0"
red = "#BE4E42"
blue = "#386898"
grey = "#606971"

def run_query(sql:str, params:list | None = None) -> list[dict]:
    conn = duckdb.connect(str(DATABASE), read_only = True)
    
    try:
        result = conn.execute(sql, params or [])
        columns = [description[0] for description in result.description]
        return [dict(zip(columns, row)) for row in result.fetchall()]
    
    finally:
        conn.close()
