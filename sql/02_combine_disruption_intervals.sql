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

ordered AS(
    SELECT *,
    MAX(end_time) OVER(
        PARTITION BY line_name
        ORDER BY start_time, end_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING
    ) AS previous_max_end
    FROM disruption_messages
),

flagged AS(
    SELECT *,
    CASE WHEN previous_max_end IS NULL
    OR start_time > previous_max_end
    THEN 1
    ELSE 0
    END AS new_interval
    FROM ordered
),

grouped AS(
    SELECT *,
    SUM(new_interval) OVER(
        PARTITION BY line_name
        ORDER BY start_time, end_time
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS interval_group
    FROM flagged
)

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