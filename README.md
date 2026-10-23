# RouteRadar | Tube Insights

**London Underground service status insights for everyday commmuters.**

RouteRadar is a Streamlit dashboard supported by a Pyhon, SQL, DuckDB data pipeline. It combines the latest Transport for London (TfL) *API status snapshots* with *historical service status records* to help people explore when their Underground line has been reported to have service restrictions.

> *Project status:* First draft. Historical figures currently cover the selected TfL status categories and weekday morning commute windows in 2025. *They should not be interpreted as measured passenger delays.*

## What I built and who is it for

I built RouteRadar for London Underground commuters who want more context about the lines they use regulary. A live status message is only useful for todays journey, but it does not show what has happened during past commuting periods. RouteRadar brings a saved current status snapshot and historical analysis into one place.

Users can select an Underground line to:

- View the **l*atest collected TfL service status**, including when the snapshot was taken.
- See **how many mornings has a reported service restrictriction between 7am and 9am** in 2025.
- See **how many hours those restrictions covered**.
- Compare **monthly patters** in recorded restriction coverage.*

The question I wanted my app to answer are: *How frequently was my line reporting a restriction during my morning commuting hours?* *How long did these reports cover?* *Did certain months have more reported restriction time than others?* *What did TfL report in their latest API?*

## The data

### TfL Unified API:

- **Provider:** Transport for London (TfL).
- **Documentation:** [TfL Unified API documentation](https://api.tfl.gov.uk/swagger/ui/index.html) and [TfL's Unified API overview](https://tfl.gov.uk/info-for/open-data-users/unified-api).
- **Endpoint:** [`GET /Line/Mode/tube/Status?detail=true`](https://api.tfl.gov.uk/Line/Mode/tube/Status?detail=true).
- **What I extracted:** Underground line identifiers/names and nested status information, including status descriptions, severity and explanatory reasons when provided.
- **Raw format:** Timestamped JSON responses saved in `data/raw/api/` without modifying the response body.
- **Processed format:** The `api_line_status` table in DuckDB, with line/status fields flattened into rows and linked to their extraction timestamp/source file.

The API returns a snapshot of status at the time it is queried. The app uses the latest saved snapshot so it doesnt auto refresh the page when somebody opens the page.


### Historical Underground records

Historial London Underground service-status data published by Transport for London. This dataset is seperate to the API.

- **Source:** https://tfl.gov.uk/corporate/publications-and-reports/underground-services-performance
- **Raw file:** `data/raw/historical/trains-service-status-messages.csv`.
- **Fields:** Line, start date/time, end date/time, service status and status-message details.

The original CSV is retained seperately from the cleaned and modelled data. Keeping the raw inputs makes it possible to inspect source records and rebuild the transformations.

## How it works and repository structure

```text
RouteRadar/
│
├── README.md
├── requirements.txt
├── .gitignore
├── app.py
│
├── data/
│   ├── raw/
│   │   ├── historical/
│   │   │   └── trains-service-status-messages.csv
│   │   │
│   │   └── api/
│   │       └── tube_status_*.json
│   │
│   └── processed/
│       └── routeradar.duckdb
│
├── notebooks/
│   └── 01_profiling_historical.ipynb
│
├── sql/
│   ├── 01_clean_historical.sql
│   └── 02_combine_disruption_intervals.sql
│
├── src/
│   ├── load_historical.py
│   ├── clean_historical.py
│   ├── build_intervals.py
│   ├── extract_tfl.py
│   └── load_api_status.py
│
└── test/
    └── validation_pipeline.py
```

My pipeline separates ingestion, cleaning, classification, interval modelling and dashboard.
```text
Historical TfL CSV
    -> raw_service_status
    -> stg_service_status / clean_service_status
    -> classified_service_status
    -> disruption_intervals ----------------------\
                                                   \
TfL Unified API                                     |-> Streamlit app dashboard
    -> original timestamped JSON snapshots         /
    -> api_line_status ---------------------------/
```

### 1. Preserve raw inputs
- `src/load_historical.py` loads the historical CSV nito DuckDB.
- `src/extract_tfl.py` requests the TfL endpoint and saves its original response as a timestamped JSON file.
- API credentials are loaded from a `.env` file which is stored locally.

### 2. Clean historical records
- `src/clean_historical.py` executes `sql/01_clean_historical.sql`.
- This standardises names and timestamps, removes exact duplicates and excludes records with missing or invalid time ranges.

### 3. classify service messages
- `sql/02_combine_disruption_intervals.sql` creates `classified_service_status`.
- It groups together labels into types such as delay, suspension and closure. It looks as hints about whether a restriction was planned or unplanned.
- These are based on keywords and are not to be treated as definitive evidence.

### 4. Combine overlapping time intervals
- `sql/02_combine_disruption_intervals.sql` also creates `disruption_intervals`.
- For each line, window functions compare a records start time with the latest previous end time.
- Overlapping and touching records are then grouped and reduced into one interval.
- This avoids double counting the time when TfL records overlap.
- A combined interval is not necessarily one distinct incident.

### 5. calculate the commute window coverage
- `app.py` creates a weekday morning window from 7am to 9am for 2025, it intersects them with the combined historical intervals, then sums the total overlapping seconds.
- It displays the number of affected mornings, total restriction hours and a monthly chart.
- The dashboard queries `api_line_status` for the most recent saved status of the selected line.

--

### What the metrics mean
- **mornings with reported restrictions:** the number of weekday morning windows containing at least some time covered by an included TfL status record.
- **Reported restriction hours:** the total time within the windows covered by status records  with overlapping intervals counted once.

These metrics **do not** mean that every train/ passenger was delayed for that duration. Some status reports describe only part of a line.


### Data quality decisions and limitations
The cleaning and modelling uses `CREATE OR REPLACE` tables so rerunning them rebuilds their outputs instead of messing with old ones.

- The current historical interval calculation includes **Minor Delays, Severe Delays, Part Closure, Part Suspended and Suspended**. These indicate reported service restrictions whether or not they were planned.
- **Planned Closure, Reduced Service, Special Servuce and Service Closed** are retained in the classified data for further investigstion. Including `Service Closed` might have incorrectly counted normal overnight non operating time as a disruption.
- **Good Serivce** is excluded from the restricted duration calculations.
- A weekday with no matching included record is counted as **zero matching restriction time** - this should not be counted as a good service.
- The analysis uses calendar weekdays, **bank holidays are not currently excluded**
- The calculation refers to the entire line rather than station or journey specific. The monthly chart shows **reported coverage** and does not represent a full reliability ranking.

### How to run it
The commands below assume **Python3** and a terminal opened in the project folder. This is for macOS.

**1. clone the repository.** Replace the placeholder with this projects GitHub URL:

```bash
git clone https://github.com/RithinBhudia/RouteRadar.git
cd RouteRadar
```

**2. Create a virtual environment and install dependancies**

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install duckdb pandas streamlit altair requests python-dotenv pytest
```

**3. Rebuild duckDB from the committed files.** The duckDB database is stored locally.

```bash
mkdir -p data/processed
python3 src/load_historical.py
python3 src/clean_historical.py
python3 src/build_intervals.py
python3 src/load_api_status.py
```

The API loading script reads the raw JSON files in `data/raw/api/`. I have left an API snapshot in the repository so reviewers can run it without an API key.

**4. Run the automated tests**

```bash
python3 -m pytest -v test/validation_pipeline.py
```

**5. launch the app**

```bash
python3 -m streamlit run app.py
```

Streamlit will show a local URL looking something likeL `http://localhost:8501`. Select an Underground line to explore its layest API status and its historical 2025 morning commute metrics.

## What I will do next:
1. **Resolve ambiguous statuses**
2. **Personalise the analysis**
3. **Improve geographical analysis**


Powered by TFL Open Data. RouteRadar is an independent educational/portfolio project, not an official TfL application.