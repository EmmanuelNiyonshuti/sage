"""Sentinel Hub API client for making HTTP requests."""

from datetime import date
from typing import Any

import httpx

from app.services.sentinel_hub_auth import sentinel_auth


class SentinelHubClient:
    """
    Low-level client for Sentinel Hub API.

    Handles HTTP requests to Sentinel Hub services.
    Does NOT contain business logic or database operations.
    """

    def __init__(self, base_url: str = "https://services.sentinel-hub.com"):
        """
        Initialize Sentinel Hub client.

        Args:
            base_url: Sentinel Hub API base URL
        """
        self.base_url = base_url

    def get_statistics(
        self,
        geometry: dict[str, Any],
        start_date: date,
        end_date: date,
        evalscript: str,
        max_cloud_coverage: int = 30,
    ) -> dict[str, Any]:
        """
        Request statistics from Sentinel Hub Statistical API.

        Args:
            geometry: GeoJSON geometry (Polygon)
            start_date: Start of time range
            end_date: End of time range
            evalscript: JavaScript evalscript for processing
            max_cloud_coverage: Maximum acceptable cloud coverage percentage

        Returns:
            Raw JSON response from Statistical API

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        # Build request payload
        payload = self._build_statistics_payload(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            evalscript=evalscript,
            max_cloud_coverage=max_cloud_coverage,
        )
        token = sentinel_auth.get_token()

        with httpx.Client(base_url=self.base_url, timeout=60.0) as client:
            response = client.post(
                "/api/v1/statistics",
                json=payload,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        return response.json()

    def _build_statistics_payload(
        self,
        geometry: dict[str, Any],
        start_date: date,
        end_date: date,
        evalscript: str,
        max_cloud_coverage: int,
    ) -> dict[str, Any]:
        """
        Build the JSON payload for Statistical API request.

        Args:
            geometry: GeoJSON geometry
            start_date: Start date
            end_date: End date
            evalscript: Processing script
            max_cloud_coverage: Max cloud coverage

        Returns:
            Complete request payload
        """
        # Format dates as ISO 8601 with time
        start_datetime = f"{start_date.isoformat()}T00:00:00Z"
        end_datetime = f"{end_date.isoformat()}T23:59:59Z"

        return {
            "input": {
                "bounds": {"geometry": geometry},
                "data": [
                    {
                        "type": "sentinel-2-l2a",
                        "dataFilter": {
                            "timeRange": {
                                "from": start_datetime,
                                "to": end_datetime,
                            },
                            "maxCloudCoverage": max_cloud_coverage,
                        },
                    }
                ],
            },
            "aggregation": {
                "timeRange": {
                    "from": start_datetime,
                    "to": end_datetime,
                },
                "aggregationInterval": {
                    "of": "P1D"  # Process per day
                },
                "evalscript": evalscript,
            },
            "calculations": {
                # The output id must match what's defined in evalscript
                "default": {
                    "statistics": {
                        "default": {}  # Request all default statistics
                    }
                }
            },
        }


sentinel_client = SentinelHubClient()
