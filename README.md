# sage

SAGE is a backend application that uses the Sentinel Hub API to periodically fetch NDVI
(Normalized Difference Vegetation Index) data for farm boundaries (called **parcels** in the application).

The data is stored in a relational database, aggregated into time series, and used to generate
basic alerts such as vegetation decline, sustained low NDVI, or drought_risk.

The Sentinel Hub API uses OAuth2 Authentication and requires that you have an access token. to get your credentials you can:
1.  **Register:** Create an account at [Sentinel Hub / Planet](https://login.planet.com).
2.  **OAuth Client:** Navigate to the User Settings to create a new OAuth Client.
3.  **Credentials:** Obtain your `CLIENT_ID` and `CLIENT_SECRET`. 
4.  **Documentation:** For more details you can visit [Sentinel Hub Auth Guide](https://docs.sentinel-hub.com/api/latest/api/overview/authentication/).

These credentials should be placed in your `.env` file (you can check `.env.template`)

The API is meant to be used by things like:
- Simple dashboards (maps, charts, alert lists)
- Internal tools that need parcel-level vegetation trends
- Experiments or analysis built on top of cleaned, structured NDVI data

SAGE exposes everything through a REST API and focuses mainly on backend concerns:
data ingestion, scheduling, processing, and alerting.

There is also a small Streamlit-based dashboard for basic interaction and visualization.

## NOTE

There are a few fixed defaults used in the code when aggregating data and generating alerts.
These values are practical heuristics meant for general monitoring. They are not agronomic ground truth.

Examples include:
- Grouping daily raster stats into weekly and monthly averages
- Using a 30-day history window for anomaly detection
- Flagging anomalies with a ±2 standard deviation rule
- Triggering vegetation alerts based on recent percentage changes
- Treating sustained low NDVI as a signal worth flagging

There is no single “correct” NDVI threshold or time duration that defines vegetation or drought stress.
What makes sense is highly context-dependent and varies by crop type, growth stage, location, and even the data itself.

These values are used as reasonable starting points in code and are meant to be tunable, not definitive.

## Running It Locally

```bash
# Clone the repository
git clone git@github.com:EmmanuelNiyonshuti/sage.git
cd sage

# Configure environment variables
cp .env.template .env
```

Edit `.env` and add your Sentinel Hub credentials:
```
SENTINEL_HUB_CLIENT_ID=your_client_id_here
SENTINEL_HUB_CLIENT_SECRET=your_client_secret_here
```

### Option A: Using Docker

```bash
docker compose up
```

it will start all services including the database (PostgreSQL with PostGIS), API server. you will have to start the dashboard if you want because its optional service by running ```docker compose up dashboard```.

### Option B: Using uv

```bash
# Install dependencies
uv sync

# Run the API server
uv run fastapi dev

# Run the dashboard (in a separate terminal)
python3 -m tools.visualizer.streamlit_app
```

**Note:** You'll need to set up a PostgreSQL database with the PostGIS extension separately if not using Docker.

### Accessing the Application

- **API Documentation:** http://localhost:8000/docs
- **Dashboard:** http://localhost:8501