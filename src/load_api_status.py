from pathlib import Path
from datetime import datetime, timezone

import duckdb
import json


ROOT = Path(__file__).resolve().parents[1]

raw_dir = ROOT /"data/raw/api"

database_file = ROOT / "data/processed/routeradar.duckdb"

files = sorted(raw_dir.glob("tube_status_*.json"))
if not files:
    raise FileNotFoundError("No API JSON files found. Run extract_tfl.py")

"""
--- The first few api response definitions ---
Line (Tfl-19):
id
name
modeName
disruptions
created
modified
lineStatuses
routeSections
serviceTypes
crowding

LineStatus (Tfl-16):
id
lineId
statusSeverity
statusSeverityDescription
reason
created
modified
validityPeriods
disruption

LineServiceTypeInfo:
name
uri
...
"""

records = []

for file in files:
    # get the extraction time from the filename
    timestamp = file.stem.removeprefix("tube_status_")
    extracted = datetime.strptime(timestamp, "%Y%m%dT%H%M%S%fZ").replace(tzinfo = timezone.utc)

    # read the original JSON 
    data = json.loads(file.read_bytes())

    # checks file has expected structure
    if not isinstance(data, list):
        raise ValueError(f"data is not a list in {file.name}")

    for line in data:
        # one line could have more than one status
        for index, status in enumerate(
            line.get("lineStatuses") or []
        ):
            records.append((
                # fields may not be required in the api so use .get to retrun none if not exist
                file.name,
                extracted,
                line.get("id"),
                line.get("name"),
                index,
                status.get("statusSeverity"),
                status.get("statusSeverityDescription"),
                status.get("reason"),
                line.get("modeName"),
                (status.get("disruption") or {}).get("category")
            ))

# build a table from the original snapshots
with duckdb.connect(str(database_file)) as conn:

    conn.execute("""
CREATE OR REPLACE TABLE api_line_status AS(
SELECT 
CAST(NULL AS VARCHAR) AS source_file,
CAST(NULL AS TIMESTAMPTZ) AS extracted,
CAST(NULL AS VARCHAR) AS line_id,
CAST(NULL AS VARCHAR) AS line_name,
CAST(NULL AS INTEGER) AS status_index,
CAST(NULL AS INTEGER) AS severity_score,
CAST(NULL AS VARCHAR) AS status_description,
CAST(NULL AS VARCHAR) AS reason,
CAST(NULL AS VARCHAR) AS mode_name,
CAST(NULL AS VARCHAR) AS disruption_category
WHERE FALSE
)
""")

    if records:
        conn.executemany("""
    INSERT INTO api_line_status
    VALUES(?,?,?,?,?,?,?,?,?,?)
    """, records)

    count = conn.execute("""
    SELECT COUNT(*) FROM api_line_status
    """).fetchone()[0]

    print(f"API data transformed with {len(files)} source snapshots and {count} status records")