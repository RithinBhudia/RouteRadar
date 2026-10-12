from pathlib import Path
import duckdb

# Project directory
ROOT = Path(__file__).resolve().parents[1]

# original csv
status_file= (ROOT
            / "data"
            / "raw"
            / "historical"
            / "trains-service-status-messages.csv"
)

# location of duckdb database save
database_dir = ROOT / "data" / "processed"
database_dir.mkdir(parents = True, exist_ok = True)

database_file = database_dir / "routeradar.duckdb"


# connect to the database
conn = duckdb.connect(str(database_file))
print("database created:")
print(f"location is {database_file}")





# check that the source CSV exists
if not status_file.exists():
    raise FileNotFoundError(f"cannot find historical CSV: {status_file}")

# load the original csv into duckdb - store everything as text
conn.execute(
    """ CREATE OR REPLACE TABLE raw_service_status AS
    SELECT * 
    FROM read_csv(
    ?,
    header = true,
    all_varchar = true)
""", [str(status_file)]
)

# count the number of records that have been imported
total_records = conn.execute(
    """ SELECT COUNT(*)
    FROM raw_service_status
"""
).fetchone()[0]
print(f"successfully imported {total_records:,} records")

# inspect first 5 rows
print(conn.execute(
    """ SELECT *
    FROM raw_service_status
    LIMIT 5
""" ).df().to_string(index = False, max_colwidth = 50)
)




conn.close()