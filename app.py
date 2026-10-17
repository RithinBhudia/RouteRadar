from pathlib import Path
from datetime import timezone
import duckdb
import streamlit as st
import pandas as pd

st.set_page_config(
    page_title = "RouteRadar",
    page_icon = "👽",
    layout = "wide"
)

ROOT = Path(__file__).resolve().parent
DATABASE = ROOT /"data/processed/routeradar.duckdb"



# connect to duckdb

if not DATABASE.exists():
    st.error("database not found.")

def run_query(sql, params = None):
    conn = duckdb.connect(str(DATABASE), read_only = True)

    try:
        return conn.execute(sql, params or []).df()
    finally:
        conn.close()


# page heading
st.title("ЯR: RouteRadar")
st.write(
    "Explore London Underground and historical distribution patterns."
)

st.divider()


## Select option for London Undergroumd Line

# options for lines
lines = run_query("""
SELECT DiSTINCT line_name
FROM disruption_intervals
WHERE line_name IS NOT NULL
ORDER BY line_name
""")

# make drop down menu
selected_line = st.selectbox(
    "Choose your Underground line", lines["line_name"].tolist()
)

## get the last collected service status

st.header("Latest Collected Service Status")

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
        for _, row in status.iterrows():
            st.subheader(row["status_description"])

            # if reason is not NULL and not empty string ""
            if pd.notna(row["reason"]) and row["reason"]:
                st.write(row["reason"])

            st.caption(f"Latest snapshot collected at {latest_time}")

st.info("This section shows the latest SAVED API snapshot."
        " It may not necessarily be the current live service status.")


