# sage

SAGE is a backend application that uses the Sentinel Hub API to periodically fetch NDVI
(Normalized Difference Vegetation Index) data for farm boundaries (called **parcels** in the application).

The data is stored in a relational database, aggregated into time series, and used to generate
basic alerts such as vegetation decline, sustained low NDVI, or drought_risk.

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

