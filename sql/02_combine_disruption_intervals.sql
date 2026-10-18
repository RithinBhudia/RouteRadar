-- =============================================================
-- Historical Train Service Status - Disruption Interval Model
-- =============================================================

-- ====================================================================================================================
-- This file creates:
-- - Table: classified_service_status
--   contains columns:   line_name, start_time, end_time, service_status, status_message
--   Source table: clean_service_status
--
-- - Table: disruption_intervals
--   contains columns:   line_name, start_time, end_time, service_status, status_message, service_type, planned_or_not
--   Source table: classified_service_status
--
-- =====================================================================================================================

-- Business question:
-- During my usual commuting hours, how much time has my Underground line 
-- had a reported service restriction?

CREATE OR REPLACE TABLE classified_service_status AS

WITH evidence AS(
    SELECT *,
    LOWER(COALESCE(status_message, '')) AS message_lower
    
    FROM clean_service_status
),

classification AS(
    SELECT *,

    -- classify the type of service condition.
    -- Do not classify whether it was planned or not yet.
    CASE
    WHEN service_status IN(
        'Minor Delays',
        'Severe Delays'
    ) THEN 'Delay'

    WHEN service_status IN(
        'Part Suspended',
        'Suspended'
    )THEN 'Closure'

    WHEN service_status IN(
        'Part Closure',
        'Planned Closure'
    )THEN 'Closure'

    WHEN service_status IN(
        'Reduced Service',
        'Special Service'
    )THEN 'Altered Service'

    WHEN service_status = 'Service Closed'
    THEN 'Service Closed'

    WHEN service_status = 'Good Service'
    THEN 'Good Service'

    ELSE 'Unknown'

    END AS service_type,


    -- Now split identifier, planned vs unplanned
    (
        message_lower LIKE '%planned engineering%'
        OR message_lower LIKE '%planned closure%'
        OR message_lower LIKE '%planned maintenance%'
    )AS planned_hint,

    (
        message_lower LIKE '%faulty train%'
        OR message_lower LIKE '%taken ill on a%'
        OR message_lower LIKE '%signal failure%'
        OR message_lower LIKE '%fire alert%'
        OR message_lower LIKE '%trespasser%'
        OR message_lower LIKE '%points failure%'
        OR message_lower LIKE '%leaf fall%'
    ) AS unplanned_hint

    FROM evidence
)

SELECT
line_name,
start_time,
end_time,
service_status,
status_message,
service_type,

-- Rate like a review system.
CASE
WHEN planned_hint AND unplanned_hint THEN 'Mixed, must review'

WHEN planned_hint THEN 'likley to be planned'

WHEN unplanned_hint THEn 'likley to be unplanned'

ELSE 'unknown'

END AS planned_or_not,

-- Which types of status enter our inital interval model
-- Planned restrictions might not be automatically excluded
CASE
WHEN service_status IN(
    -- Status where the delays happen during usual operating hours
    'Minor Delays',
    'Part Closure',
    'Severe Delays',
    'Part Suspended',
    'Suspended'
) THEN 'Include'

-- Need further investigation, are ambiguous if they happen during usual operating hours
WHEN service_status IN(
    'Planned Closure',
    'Reduced Service',
    'Special Service',
    'Service Closed'
) THEN 'Ambiguous'

-- Good service is lovely, that is great to hear
WHEN service_status = 'Good Service'
THEN 'Exclude'

ELSE 'Ambiguous'
END AS interval_decision

FROM classification;








CREATE OR REPLACE TABLE disruption_intervals AS

WITH disruption_messages AS(
    SELECT
    line_name,
    start_time,
    end_time,
    service_status,
    status_message,
    service_type,
    planned_or_not

    -- Use the 'Include' interval_decision from above
    FROM classified_service_status
    WHERE interval_decision = 'Include'
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