# ============================================================
# Historical Train Service Status Data Cleaning
# ============================================================

# ============================================================
# This file creates:
# - Staging table: stg_service_status
# - Cleaned table: clean_service_status
#
# Uses 01_clean_ditorical.sql
# ============================================================


from pathlib import Path
import duckdb

# project directory of RouteRadar
ROOT = Path(__file__).resolve().parents[1]

# connect to the already existing original RouteRadar database
database_file = ROOT / "data"/"processed"/"routeradar.duckdb"

if not database_file.exists():
    raise FileNotFoundError("Database not found, run load_historical.py then try again")

conn = duckdb.connect(str(database_file))

# read and run the SQL file
sql_file = ROOT /"sql"/"01_clean_historical.sql"

sql_query = sql_file.read_text(encoding= "utf-8")

conn.execute(sql_query)



# count the number of records in the original dataset
raw_count = conn.execute(""" SELECT COUNT(*)
FROM raw_service_status
""").fetchone()[0]

# count the number of invalid entries
invalid_count = conn.execute("""SELECT COUNT(*)
FROM stg_service_status
WHERE end_time IS NULL
OR start_time IS NULL
OR end_time <= start_time
OR line_name IS NULL
OR service_status IS NULL;
""").fetchone()[0]

# count the number of cleaned records
clean_count = conn.execute(""" SELECT COUNT(*)
FROM clean_service_status
""").fetchone()[0]

# number of duplicated removed from the valid records
duplicates = raw_count - invalid_count - clean_count


print("clean_historical.py completed")
print(f"Original records: {raw_count}")
print(f"Invalid records: {invalid_count}")
print(f"Duplicate records removied: {duplicates}")
print(f"cleaned records: {clean_count}")

conn.close()