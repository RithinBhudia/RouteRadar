-- ============================================================
-- Historical Train Service Status Data Cleaning
-- ============================================================

-- ============================================================
-- This file creates:
-- - table: stg_service_status
--   contains columns:   line_name, start_time, end_time, service_status, status_message
--   Source table: raw_service_status
--
-- - table: clean_service_status
--   contains columns:   line_name, start_time, end_time, service_status, status_message
--   Source table: stg_service_status
--
-- ============================================================


-- standardise the source fields and datatypes
CREATE OR REPLACE TABLE stg_service_status AS
SELECT
NULLIF(TRIM("Line"), '') AS line_name,

TRY_STRPTIME(
    "Start Date/Time",
    '%d/%m/%Y %H:%M:%S'
) AS start_time,

TRY_STRPTIME(
    "End Date/Time",
    '%d/%m/%Y %H:%M:%S'
) AS end_time,

NULLIF(TRIM("Service Status"), '') AS service_status,

NULLIF(TRIM("Status Message Details"), '') AS status_message

FROM raw_service_status; -- created in load_historical.py




-- keep unique records with valid values
-- raw tables will remain unchanged
-- rebuild the raw table on each run

CREATE OR REPLACE TABLE clean_service_status AS
SELECT DISTINCT
line_name,
start_time,
end_time,
service_status,
status_message

FROM stg_service_status 

WHERE end_time IS NOT NULL
AND start_time  IS NOT NULL
AND end_time > start_time
AND line_name IS NOT NULL
AND service_status IS NOT NULL;