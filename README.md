# sage

SAGE is a backend that utilize sentinel hub api to fetch agronomic data through scheduled jobs for a particular farm boundary(drawn on a map) referred to in the application as **parcels**, stores the data in relational database , builds time series and alerts over those data and expose them via a REST API for internal tools, dashboards, or other services.

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

