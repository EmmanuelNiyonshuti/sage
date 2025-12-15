import pytest
from httpx import AsyncClient

api_url_prefix = "/api/v1"


async def create_parcel(payload: dict, async_client: AsyncClient) -> dict:
    response = await async_client.post(f"{api_url_prefix}/parcels", json=payload)
    return response.json()


@pytest.fixture()
async def created_parcel(async_client: AsyncClient):
    return await create_parcel(
        {
            "name": "Kigali Trial Parcel",
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [30.058, -1.949],
                        [30.060, -1.949],
                        [30.060, -1.947],
                        [30.058, -1.947],
                        [30.058, -1.949],
                    ]
                ],
            },
            "crop_type": "maize",
            "soil_type": "clay",
            "irrigation_type": "rainfed",
        },
        async_client,
    )


@pytest.mark.anyio
async def test_create_parcel(async_client: AsyncClient):
    payload = {
        "name": "Nyamata Block A",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [30.3291, -2.1824],
                    [30.3305, -2.1827],
                    [30.3307, -2.1812],
                    [30.3294, -2.1809],
                    [30.3291, -2.1824],
                ]
            ],
        },
        "crop_type": "bean",
        "soil_type": "sandy loam",
        "irrigation_type": "mixed",
    }
    response = await async_client.post(f"{api_url_prefix}/parcels", json=payload)
    assert response.status_code == 201
    assert {
        "name": "Nyamata Block A",
        "crop_type": "bean",
    }.items() <= response.json().items()


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
    response = await async_client.get(f"{api_url_prefix}/12344")
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
