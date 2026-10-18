

import altair as alt
from pathlib import Path
from datetime import timezone
import duckdb
import streamlit as st
import pandas as pd


# inital app configuration
st.set_page_config(
    page_title = "RouteRadar",
    page_icon = "👽",
    layout = "wide"
)

# directories
ROOT = Path(__file__).resolve().parent
DATABASE = ROOT /"data/processed/routeradar.duckdb"



# connect to duckdb
if not DATABASE.exists():
    st.error("database not found.")
    st.stop()

# create a function to run sql query
def run_query(sql, params = None):
    conn = duckdb.connect(str(DATABASE), read_only = True)

    try:
        return conn.execute(sql, params or []).df()
    finally:
        conn.close()


# page heading
st.title(":red[Route]:blue[Radar] :grey[| Tube Insights]")
st.write(
    "Explore service statuses and historical disruption patterns across London's Underground."
)

st.divider()


## Select option for London Undergroumd Line

# options for lines
lines = run_query("""
SELECT DISTINCT line_name
FROM disruption_intervals
WHERE line_name IS NOT NULL
ORDER BY line_name
""")

# make the box lighter than the background: key - lighter_colour
st.markdown("""
<style>
.st-key-lighter_colour {
    background-color: #FFFCF7;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)



# make drop down menu
with st.container(border = True, key = "lighter_colour"):
    selected_line = st.selectbox(
        "Choose your Underground line", lines["line_name"].tolist()
    )

## get the last collected service status


# make the box lighter than the background: key - lighter_colour

st.markdown("""
<style>
.st-key-lighter_colour2 {
    background-color: #FFFCF7;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)



with st.container(border = True, key = "lighter_colour2"):

    st.subheader("Latest Service Status")

    # latest extracted timd
    latest = run_query("""
    SELECT MAX(extracted) AS latest_time
    FROM api_line_status
    """)

    latest_time =latest.iloc[0]["latest_time"]

    if pd.isna(latest_time):
        st.warning("No API snapshots available")
    else:
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

        if status.empty:
            st.info(
                "No matching status in the latest snapshot"
            )

        else:
            # for each row where the line matches what the user put in the drop down is
            # from the latest snapshot, write the status_description along with its respective reason.
            for _, row in status.iterrows():

                # display the status for each row
                if row["status_description"] == "Good Service":
                    st.success("Good Service")
                else:
                    st.markdown(
                        f"#### {row['status_description']}"
                    )

                # if reason is not NULL and not empty string ""
                if pd.notna(row["reason"]) and row["reason"]:
                    st.write(row["reason"])

            st.caption(f"Latest snapshot collected at {pd.to_datetime(latest_time).strftime("%H:%M  %d %B %Y ")}")

    st.caption("TfL's saved API snapshot"
            " - May not reflect live service status.")



## Historical morning commute analysis

st.divider()

st.markdown("""
<style>
.st-key-lighter_colour3 {
    background-color: #F0E9E0;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<style>
.st-key-darker_colour1,
.st-key-darker_colour2 {
    background-color: #FFFCF7;
    border-radius: 12px;
    padding: 16px;
}
</style>
""", unsafe_allow_html=True)


with st.container(border = True, key = "lighter_colour3"):
    st.subheader("Historical Morning Commute Analysis")

    st.caption("Reported service restrictions during weekday" 
    " mornings between 07:00 and 09:00 in 2025")

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
    DATE_DIFF('second', GREATEST(d.start_time, w.window_start),
    LEAST(d.end_time,w.window_end))
    ),0) AS disruption_seconds

    FROM windows w

    LEFT JOIN disruption_intervals d
    ON d.line_name = ?
    AND d.start_time < w.window_end
    AND d.end_time > w.window_start

    GROUP BY w.commute_date
    ORDER BY w.commute_date

    """,[selected_line])
    # The code above is to count the duration of disruption periods between 7am and 9am.


    ## calculate the summary metrics

    # number of mornings with some disruption
    affected_mornings = int(
        (commute_data["disruption_seconds"] > 0).sum()
    )

    # total number of mornings
    total_mornings = len(commute_data)

    # total number of hours
    total_hours = (
        commute_data["disruption_seconds"].sum() / 3600
    )

    # split page into two for results
    column1, column2 = st.columns(2)

    # proportion of restricted mornings
    with column1:
        with st.container(key = "darker_colour1"):
            st.metric(
                "Mornings with reported restrictions",
                f"{affected_mornings} / {total_mornings}"
            )

    # total duration in hours of disruptions in commuting hours
    with column2:
        with st.container(key = "darker_colour2"):
            st.metric(
                "Total reported restriction hours",
                f"{total_hours:.1f}"
            )

    ## visualise monthly patterns - bar graph
    # add month column to commute_data
    commute_data["month"] = pd.to_datetime(
        commute_data["commute_date"]
    ).dt.strftime("%Y-%m")

    month = (
        commute_data.groupby("month", sort = True)["disruption_seconds"]
        .sum().div(3600)
        .reset_index(name = "reported_hours")
    )

    st.subheader("Restricted hours by month")

    month["month"] = pd.to_datetime(month["month"]).dt.strftime("%b")

    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    month["month"] = pd.Categorical(month["month"],
                                    categories = month_order,
                                    ordered = True)

    st.bar_chart(month,
                 x = "month",
                 y = "reported_hours",
                 color = "#BF6258",
                 height = 300,
                 x_label="",
                 y_label="Restriction hours")
