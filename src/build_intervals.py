# ============================================================
# Historical Disruption Combine Interval s
# ============================================================

# ============================================================
# This file creates:
# - Combined-interval disruption table: disruption_intervals
#
# Combines overlapping or touching disruption periods.
# Validates that no overlapping intervals remain.
#
# Uses 02_combine_disruption_intervals.sql
# ============================================================


from pathlib import Path
import duckdb

# project directory
ROOT = Path(__file__).resolve().parents[1]

database_file = ROOT /"data"/"processed"/"routeradar.duckdb"

sql = ROOT /"sql"/"02_combine_disruption_intervals.sql"

# check that files exist
if not database_file.exists():
    raise FileNotFoundError("routeradar.duckdb database not found")

if not sql.exists():
    raise FileNotFoundError("02_combine_disruption_intervals.sql not found")

# connect to database
conn = duckdb.connect(str(database_file))

try:
    # execute 02_combine_disruption_intervals.sql
    conn.execute(sql.read_text(encoding = "utf-8"))


    # count the combined intervals
    result = conn.execute("""
SELECT COUNT(*) AS interval_count
FROM disruption_intervals
""").fetchone()

    print(f"total merged intervals: {result[0]}")



    # show the first 10 rows
    show = conn.execute("""
SELECT *
FROM disruption_intervals
ORDER BY line_name, start_time
LIMIT 10
""").df()

    print(show.to_string(index = False))



# VALIDATION CHECK
# check that no overlapping or touching intervals remain
# Values should all be zero!
    remaining_overlaps = conn.execute("""
WITH ordered AS (
SELECT
line_name,
start_time,
end_time,
LAG(end_time) OVER(
PARTITION BY line_name
ORDER BY start_time, end_time
) AS previous_end

FROM disruption_intervals
)

SELECT
line_name,
COUNT(*) FILTER( 
start_time <= previous_end
) AS overlap_count

FROM ordered

GROUP BY line_name
ORDER BY overlap_count DESC, line_name
""").df()

    print(remaining_overlaps.to_string(index = False))




finally:
    conn.close()
