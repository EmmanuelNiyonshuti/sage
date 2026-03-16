"""Sentinel Hub API client for making HTTP requests."""

from datetime import date
from typing import Any

import httpx

from .sentinel_hub_auth import sentinel_auth


class SentinelHubClient:
    """
    client for Sentinel Hub API. serve as external api interface
    """

    def __init__(self, base_url: str = "https://services.sentinel-hub.com"):
        """
        Initialize Sentinel Hub client.

        Args:
            base_url: Sentinel Hub API base URL
        """
        self.base_url = base_url

    async def get_statistics(
        self,
        geometry: dict[str, Any],
        start_date: date,
        end_date: date,
        evalscript: str,
        max_cloud_coverage: int = 30,
    ) -> dict[str, Any]:
        """
        Request statistics from Sentinel Hub Statistical API.
        `Sentinel Hub statistical api` allows us to obtain statistical data from satellite imagery without downloading the images.

        We provide area of interest(a parcel boundary), time period(start and end date),
        evalscript(a javascript snippet that tells sentinel hub which bands to use and how to compute the output index)


        Args:
            geometry: GeoJSON geometry (Polygon), The farm boundary
            start_date: Start of  the time window
            end_date: End of of  the time window
            evalscript: JavaScript evalscript snippet for processing
            max_cloud_coverage: Maximum acceptable cloud coverage percentage default: 30 skip images where >30% of sky is cloudy

        Returns:
            Raw JSON response from Statistical API

        Raises:
            httpx.HTTPStatusError: If API request fails
        """
        payload = self._build_statistics_payload(
            geometry=geometry,
            start_date=start_date,
            end_date=end_date,
            evalscript=evalscript,
            max_cloud_coverage=max_cloud_coverage,
        )
        token = await sentinel_auth.get_token()

        async with httpx.AsyncClient(base_url=self.base_url, timeout=60.0) as client:
            response = await client.post(
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
        Build the JSON payload for Statistical API request to get data from `sentinel-2-l2a`.

        Sentinel-2 is a family of satellites(currently S2A && S2B) that orbits earth and photograph land surfaces every ~5 days.
        These sattelites are capable of capturing  `near-infrared (NIR)` and `shortwave infrared (SWIR)` light and we need those for finding ndvi.

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
                "default": {
                    "statistics": {
                        "default": {}  # Request all default statistics
                    }
                }
            },
        }


sentinel_client = SentinelHubClient()
