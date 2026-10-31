

import altair as alt
from pathlib import Path
from datetime import timezone
import duckdb
import streamlit as st
import pandas as pd

import subprocess
import sys

# for automation
import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timezone



# inital app configuration
st.set_page_config(
    page_title = "RouteRadar",
    page_icon = "👽",
    layout = "wide"
)

# directories
ROOT = Path(__file__).resolve().parent
DATABASE = ROOT /"data/processed/routeradar.duckdb"

# automatically collect TfL api snapshots
@st.cache_data(ttl = 300)
def get_tfl_api():
    url = "https://api.tfl.gov.uk/Line/Mode/tube/Status"

    params = {"detail": "true"}

    api_key = os.getenv("KEY")

    if api_key:
        # add api_key to dictionary
        params["app_key"] = api_key

    response = requests.get(url,
                            params = params,
                            timeout = 15)
    
    response.raise_for_status()

    return response.json(), datetime.now(timezone.utc)


@st.fragment(run_every = "5m")
def update_tfl_api(selected_line):

    st.subheader("Current tFl Service Status")

    try:
        data, checked_at = get_tfl_api()

    except requests.request:
        st.warning("Unable to retrieve TfL status at the moment")
        return

    matching_lines = [line for line in data
                      if line.get("name") == selected_line]

    if not matching_lines:
        st.info("No matching line found in TfL api")

    for line in matching_lines:
        for status in line.get("lineStatuses") or []:

            description = status.get("statusSeverityDescription",
                                     "Unknown Status")

            if description == "Good Service":
                st.success(description)
            else:
                st.warning(description)

            reason = status.get("reason")

            if reason:
                st.write(reason)
            
    st.caption(f"checked TfL at {checked_at:%H:%M UTC, %d %B %Y}"
               "Refreshes approximately every 5 minutes while page is open")




# cashe the result of the function below this:
@st.cache_resource(show_spinner=False)
def check_database():
    if DATABASE.exists():
        return

    scripts = ["load_historical.py",
               "clean_historical.py",
               "build_intervals.py",
               "load_api_status.py"]

    for script in scripts:
        subprocess.run([sys.executable, str(ROOT/"src" / script)],
                       cwd = ROOT,
                       check = True)
with st.spinner("running prerequisits for RouteRadar data..."):
    try:
        check_database()

    except subprocess.CalledProcessError:
        st.error("Database could not be built")
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


# instead of reading api snapshots from duckdb, get current service status directly from tfl api.
with st.container(border=True, key="lighter_colour2"):
    update_tfl_api(selected_line)



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
    CASE
    WHEN d.start_time IS NOT NULL THEN
    DATE_DIFF('second', GREATEST(d.start_time, w.window_start),
    LEAST(d.end_time,w.window_end)
    ) 
    ELSE 0
    END
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
