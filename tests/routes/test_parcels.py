import pytest
from httpx import AsyncClient

api_url_prefix = "/api/v1"


@pytest.mark.anyio
async def test_add_parcel(async_client: AsyncClient):
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
    response = await async_client.post(f"{api_url_prefix}/parcels/", json=payload)
    print(response.json())
    assert response.status_code == 201
    assert {
        "name": "Nyamata Block A",
        "crop_type": "bean",
    }.items() <= response.json().items()
