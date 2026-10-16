# Validation file


from pathlib import Path
import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
RAW_CSV_FILE = ROOT / "data/raw/historical/trains-service-status-messages.csv"

# 01_clean_historical.sql
CLEAN_SQL = ROOT / "sql/01_clean_historical.sql"

# sql/02_combine_disruption_intervals.sql
COMBINE_SQL = ROOT / "sql/02_combine_disruption_intervals.sql"

@pytest.fixture(scope = "module")

def db():
    # check that all the files exist
    for path in (RAW_CSV_FILE, CLEAN_SQL, COMBINE_SQL):
        if not path.is_file():
            pytest.fail(f"file {path} not found")

    # rebuild the historical tables from raw CSV in a temporary database stored in ram
    conn = duckdb.connect(":memory:")

    try:
        # loads the historical CSV into raw_service_status
        conn.execute("""
CREATE TABLE raw_service_status AS
SELECT *
FROM read_csv(?, header = true, all_varchar = true)""",[str(RAW_CSV_FILE)],
        )

        # executes 01_clean_historical.sql
        conn.execute(CLEAN_SQL.read_text(encoding = "utf-8"))

        #does the cleaned table have column names?
        column_names = {row[0] for row in conn.execute("DESCRIBE clean_service_status").fetchall()}

        # checks that start and end times exist - these are needed for 02_combine_disruption_intervals.sql
        if not {"start_time", "end_time"}.issubset(column_names):
            pytest.fail("clean_service_status needs a start and end_time columns"
                        f"current columns are: {(column_names)}")

        # runs 02_combine_disruption_intervals.sql
        conn.execute(COMBINE_SQL.read_text(encoding = "utf-8"))

        # test it
        yield conn
    finally:
        conn.close()

# check the historical data row counts
def test_raw_and_clean_counts(db):

    raw_count = db.execute("""
SELECT COUNT(*)
FROM raw_service_status
    """).fetchone()[0]

    clean_count = db.execute("""
SELECT COUNT(*)
FROM clean_service_status
""").fetchone()[0]

    assert raw_count == 118_595
    assert clean_count == 104_544

    