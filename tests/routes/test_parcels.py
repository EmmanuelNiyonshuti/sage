from unittest.mock import patch

import pytest
from httpx import AsyncClient

api_url_prefix = "/api/v1"


def get_parcel_payload(
    name: str = "Test Parcel",
    lat: float = -1.949,
    lon: float = 30.058,
    crop_type: str = "maize",
    **overrides,
) -> dict:
    payload = {
        "name": name,
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [lon, lat],
                    [lon + 0.002, lat],
                    [lon + 0.002, lat + 0.002],
                    [lon, lat + 0.002],
                    [lon, lat],
                ]
            ],
        },
        "crop_type": crop_type,
        "soil_type": "clay",
        "irrigation_type": "rainfed",
    }
    payload.update(overrides)
    return payload


async def create_parcel(
    async_client: AsyncClient, trigger_backfill: bool = False, **payload_overrides
) -> dict:
    payload = get_parcel_payload(**payload_overrides)
    response = await async_client.post(
        f"{api_url_prefix}/parcels",
        json=payload,
        params={"trigger_backfill": trigger_backfill},
    )
    return response.json()


@pytest.fixture()
async def created_parcel(async_client: AsyncClient):
    return await create_parcel(async_client, name="Kigali Trial Parcel")


@pytest.mark.anyio
async def test_create_parcel(async_client: AsyncClient):
    payload = get_parcel_payload(
        name="Nyamata Block A",
        lat=-2.1824,
        lon=30.3291,
        crop_type="bean",
        soil_type="sandy loam",
        irrigation_type="mixed",
    )
    response = await async_client.post(
        f"{api_url_prefix}/parcels", json=payload, params={"trigger_backfill": False}
    )
    assert response.status_code == 201
    assert {
        "name": "Nyamata Block A",
        "crop_type": "bean",
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_create_parcel_triggers_backfill(async_client: AsyncClient):
    with patch("app.api.routes.parcels.trigger_backfill_for_parcel") as mocked_backfill:
        payload = get_parcel_payload(name="Test Block A", crop_type="wheat")
        response = await async_client.post(f"{api_url_prefix}/parcels", json=payload)

        assert response.status_code == 201
        parcel_id = response.json()["uid"]
        mocked_backfill.assert_called_once_with(parcel_id, lookback_days=90)


@pytest.mark.anyio
async def test_get_raw_parcel_stats(
    async_client: AsyncClient, created_parcel: created_parcel
):
    response = await async_client.get(
        f"{api_url_prefix}/{created_parcel['uid']}/raw-stats"
    )
    assert response.status_code == 200
    assert {
        "parcel_id": created_parcel["uid"],
        "stats": [],
    }.items() <= response.json().items()


@pytest.mark.anyio
async def test_get_parcel(async_client: AsyncClient, created_parcel: created_parcel):
    response = await async_client.get(f"{api_url_prefix}/{created_parcel['uid']}")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_get_parcel_not_exists(async_client: AsyncClient):
    response = await async_client.get(f"{api_url_prefix}/parcels/12344")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_timeseries_parcel_stats(
    async_client: AsyncClient, created_parcel: created_parcel
):
    response = await async_client.get(f"{api_url_prefix}/{created_parcel['uid']}/stats")
    assert response.status_code == 200
    assert {
        "parcel_id": created_parcel["uid"],
        "stats": [],
    }.items() <= response.json().items()
