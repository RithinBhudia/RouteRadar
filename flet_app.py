# This is written only for the app. 
## A lot of this is currently being transfered over from the streamlit app.py.

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

# list of lines
def all_lines() -> list[str]:

    # copied from app.py
    lines = run_query("""
SELECT DISTINCT line_name
FROM disruption_intervals
WHERE line_name IS NOT NULL
ORDER BY line_name
""")
    return [str(line["line_name"]) for line in lines]


def latest_status(selected_line: str) -> tuple[object | None, list[dict]]:
    
    # copied from app.py
    latest = run_query("""
        SELECT MAX(extracted) AS latest_time
        FROM api_line_status
        """)

    latest_time = latest[0]["latest_time"] if latest else None
    if latest_time is None:
        return None, []

    # copied form app.py
    status = run_query("""
        SELECT line_name,
        status_description,
        reason,
        extracted
    
        FROM api_line_status
        WHERE line_name = ?
        AND extracted = (SELECT MAX(extracted)
        FROM api_line_status)
        """, [selected_line])
    return latest_time, status

def weekday_commute_window(selected_line: str) -> list[dict]:

    # copied from app.py:
    # generate weekday commute windows and intersect each window
    # with the non overlapping intervals we constructed
    commute_data = run_query("""
    WITH days AS (
    SELECT CAST(day_value AS DATE) AS commute_date

    FROM generate_series(DATE '2025-01-01', DATE '2025-12-31', 
    INTERVAL '1 day') AS t(day_value)

    WHERE EXTRACT(ISODOW FROM day_value)
    BETWEEN 1 AND 5
    ),

    windows AS(
    SELECT commute_date,
    CAST(commute_date AS TIMESTAMP) + INTERVAL '7 hours' AS window_start,
    CAST(commute_date AS TIMESTAMP) + INTERVAL '9 hours' AS window_end

    FROM days
    )


    SELECT w.commute_date,
    COALESCE(SUM(
    CASE
    WHEN d.start_time IS NOT NULL THEN
    DATE_DIFF('second', GREATEST(d.start_time, w.window_start),
    LEAST(d.end_time,w.window_end)
    ) 
    ELSE 0
    END
    ),0) AS disruption_seconds

    FROM windows w

    LEFT JOIN disruption_intervals d
    ON d.line_name = ?
    AND d.start_time < w.window_end
    AND d.end_time > w.window_start

    GROUP BY w.commute_date
    ORDER BY w.commute_date

    """,[selected_line])
    return commute_data
    # The code above is to count the duration of disruption periods between 7am and 9am.

