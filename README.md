# Spatial Agronomic Geo Engine

SAGE is a backend that ingests geospatial data about agricultural land, processes it into useful agricultural insights, stores the results, and exposes them via REST APIs for internal tools, dashboards, or other services.


1.Pulls satellite images from Sentinel Hub API 
2.Extracts meaningful numbers from those images (NDVI, vegetation health, etc.)
3.Stores everything in PostgreSQL
4.Provides REST API for others to query the processed data
5.Detects anomalies and sends alerts

Think of it like this: You're turning raw satellite photos into a queryable database of farm health over time.




workflow :
You have: Farm boundary (polygon coordinates)
You want: "Is this farm healthy?" (a number)

The pipeline:
1. Send polygon to Sentinel Hub → Get back pixel data
2. Process pixels → Calculate NDVI
3. Aggregate pixels → Get farm-level statistics
4. Store statistics → Database
5. Repeat over time → Time series



----------------------flow----------------------
1. Satellite flies over Rwanda
   ↓
2. Sentinel Hub stores the raw image data (you don't store this)
   ↓
3. You query Sentinel Hub API: "For Farm X polygon, compute NDVI from the Nov 15 image"
   ↓
4. Sentinel Hub returns: 100 NDVI pixel values for your farm
   ↓
5. You calculate statistics: mean=0.67, min=0.21, max=0.89, std=0.08
   ↓
6. You INSERT into raster_stats:
   - field_id: farm-001
   - acquisition_date: 2024-11-15
   - index_type: NDVI  
   - mean_value: 0.67
   - min_value: 0.21
   - max_value: 0.89
   - std_dev: 0.08
   ↓
7. You check: "Is 0.67 unusually low for this farm in November?"
   ↓
8. Yes → INSERT into alerts:
   - field_id: farm-001
   - alert_type: vegetation_decline
   - severity: high
   - message: "NDVI 20% below normal"
   ↓
9. Once a week, you aggregate raster_stats → time_series:
   - "For farm-001, for week Nov 11-17, average NDVI = 0.68"
   ↓
10. Your REST API queries these tables to answer questions



<!-- fields: "What farms are we monitoring?"
raster_stats: "What did we observe on specific dates?"
time_series: "What are the trends over time?"
alerts: "What needs attention?" -->




---

## **Why This Service Design?**

### **Clear Separation of Concerns**
```

┌─────────────────────────────────────────────────────────────┐
│                    INGESTION ENGINE                          │
│  (Background Service - Always Running)                       │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Scheduler   │    │   Workers    │    │ State Store  │
│              │    │              │    │              │
│ - Cron jobs  │───▶│ - Fetch data │───▶│ - Last run   │
│ - Triggers   │    │ - Process    │    │ - Next run   │
│ - Queue      │    │ - Store      │    │ - Status     │
└──────────────┘    └──────────────┘    └──────────────┘
        │                   │                   │
        └───────────────────┴───────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │    Database      │
                  │  raster_stats    │
                  │  time_series     │
                  │  alerts          │
                  └──────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │   REST API       │
                  │ (Read-Only Views)│
                  └──────────────────┘