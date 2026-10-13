-- DISRUPTION INTERVAL MODEL

-- Purpose:
-- Calculate continuous periods where at least one disruption status was reported.


CREATE OR REPLACE TABLE disruption_intervals AS

WITH disruption_messages AS(
    SELECT
    line_name,
    start_time,
    end_time,
    service_status,
    status_message

    FROM clean_service_status

    WHERE service_status IN(
        -- THIS HAS NOT BEEN SORTED OUT YET, THESE ARE ROUGH NOTES FOR NOW!
        'Minor Delays', -- Clear disruption unless planned
        'Part Closure', -- Clear disruption unless planned
        'Part Suspended', -- Clear disruption unless planned

        'Planned Closure', -- Could represent ordinary non operating periods, must distinguish.
        -- Include planned disruptions in the service availibility analysis.
        
        
        'Reduced Service', -- With only 5 records in the dataset
        -- and 3 distinct message descriptions, inspect each of them.
        -- Dont automatically classify every reduced service as a disruption

        'Service Closed', -- Keep these records for potential timetable analysis, but
        -- exclude routine closures from disruption duration metrics since it would 
        -- make a line seem to have hours of disruption every night.

        'Severe Delays', -- Clear disruption unless planned
        'Special Service', -- Clear disruption unless planned
        'Suspended' -- Clear disruption unless planned
    )
),

-- Find the latest end time of all the earlier disruption messages on the same line.
-- This helps identify overlapping intervals.
ordered AS(
    SELECT *,
    MAX(end_time) OVER(
        PARTITION BY line_name
        ORDER BY start_time, end_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS previous_max_end
    FROM disruption_messages
),

-- Flag the beginning of each new disruption period.
-- Start a new number if there is no message or if 
-- there is a time gap after the previous disruption.
flagged AS(
    SELECT *,
    CASE WHEN previous_max_end IS NULL
    OR start_time > previous_max_end
    THEN 1
    ELSE 0
    END AS new_interval
    FROM ordered
),


-- Group the overlapping disruptions into one period.
-- number the disruptions starting with 1.
-- The number increases whenever a new interval begins.
-- Overlapping or touching interval disruptions have the same group number.
grouped AS(
    SELECT *,
    SUM(new_interval) OVER(
        PARTITION BY line_name
        ORDER BY start_time, end_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS interval_group
    FROM flagged
)


-- Combine by calculating the earliest start, latest end, number of disturbance messages
-- and total duration. 
-- This is done without dounting overlapping times twice.
SELECT line_name,
MIN(start_time) AS start_time,
MAX(end_time) AS end_time,
COUNT(*) AS source_message_count,
DATE_DIFF(
    'second',
    MIN(start_time),
    MAX(end_time)
) AS duration_in_seconds

FROM grouped

GROUP BY line_name, interval_group