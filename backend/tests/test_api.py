import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_get_players_empty(client: AsyncClient):
    response = await client.get("/api/players")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_create_player(client: AsyncClient):
    player_data = {
        "name": "Johnny Sexton",
        "country": "Ireland",
        "fantasy_position": "out_half",
        "is_kicker": True
    }
    response = await client.post("/api/players", json=player_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Johnny Sexton"
    assert data["country"] == "Ireland"
    assert data["fantasy_position"] == "out_half"
    assert data["is_kicker"] is True


@pytest.mark.asyncio
async def test_get_player_not_found(client: AsyncClient):
    response = await client.get("/api/players/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_optimise_endpoint(client: AsyncClient):
    response = await client.post("/api/optimise", json={"round": 1})
    assert response.status_code == 200
    data = response.json()
    assert "starting_xv" in data
    assert "captain" in data
    assert "total_cost" in data


@pytest.mark.asyncio
async def test_scrape_status(client: AsyncClient):
    response = await client.get("/api/scrape/status")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_predictions_endpoint(client: AsyncClient):
    response = await client.get("/api/predictions", params={"round": 1})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
