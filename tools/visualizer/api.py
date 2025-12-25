import pathlib
import sys

import httpx
import streamlit as st

root_path = pathlib.Path(__file__).parent.parent.parent.resolve()
sys.path.insert(0, str(root_path))
from app.core.config import config  # noqa: E402

API_BASE_URL = config.API_BASE_URL


def fetch_parcels():
    try:
        with httpx.Client(base_url=API_BASE_URL) as client:
            response = client.get("/parcels", params={"limit": 100})
            response.raise_for_status()
            data = response.json()
            return data.get("parcels", [])
    except Exception as e:
        st.error(f"Failed to fetch parcels: {e}")
        return []


def fetch_parcel_details(parcel_id: str):
    try:
        with httpx.Client(base_url=API_BASE_URL) as client:
            response = client.get(f"/{parcel_id}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch parcel details: {e}")
        return None


def fetch_raw_stats(parcel_id: str):
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
            response = client.get(f"/{parcel_id}/raw-stats")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch stats: {e}")
        return []


def fetch_time_series(parcel_id: str, period: str = "weekly"):
    """Fetch time series data for a parcel"""
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
            response = client.get(f"/{parcel_id}/stats?period={period}")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to fetch time series: {e}")
        return []


def create_parcel(parcel_data: dict):
    """Create a new parcel"""
    try:
        with httpx.Client(base_url=API_BASE_URL, timeout=60.0) as client:
            response = client.post("/parcels", json=parcel_data)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        st.error(f"Failed to create parcel: {e}")
        return None
