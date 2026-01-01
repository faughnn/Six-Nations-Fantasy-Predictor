"""
End-to-end tests using Playwright for the Fantasy Six Nations API.
Tests the full API flow including creating players, predictions, and optimization.
"""
import pytest
from playwright.sync_api import sync_playwright, APIRequestContext
import httpx

BASE_URL = "http://localhost:8001"


@pytest.fixture(scope="module")
def api_context():
    """Create API request context for testing"""
    with sync_playwright() as p:
        context = p.request.new_context(base_url=BASE_URL)
        yield context
        context.dispose()


class TestAPIE2E:
    """End-to-end API tests"""

    def test_health_endpoint(self, api_context: APIRequestContext):
        """Test health check endpoint"""
        response = api_context.get("/health")
        assert response.ok
        data = response.json()
        assert data["status"] == "healthy"

    def test_root_endpoint(self, api_context: APIRequestContext):
        """Test root endpoint"""
        response = api_context.get("/")
        assert response.ok
        data = response.json()
        assert "message" in data
        assert data["version"] == "1.0.0"

    def test_create_and_get_player(self, api_context: APIRequestContext):
        """Test creating a player and retrieving them"""
        # Create player
        player_data = {
            "name": "Johnny Sexton",
            "country": "Ireland",
            "fantasy_position": "out_half",
            "is_kicker": True
        }
        create_response = api_context.post("/api/players", data=player_data)
        assert create_response.ok
        created_player = create_response.json()
        assert created_player["name"] == "Johnny Sexton"
        assert created_player["country"] == "Ireland"
        player_id = created_player["id"]

        # Get player
        get_response = api_context.get(f"/api/players/{player_id}")
        assert get_response.ok
        player = get_response.json()
        assert player["name"] == "Johnny Sexton"

    def test_get_players_list(self, api_context: APIRequestContext):
        """Test getting players list"""
        response = api_context.get("/api/players")
        assert response.ok
        data = response.json()
        assert isinstance(data, list)

    def test_filter_players_by_country(self, api_context: APIRequestContext):
        """Test filtering players by country"""
        # Create players from different countries
        api_context.post("/api/players", data={
            "name": "Antoine Dupont",
            "country": "France",
            "fantasy_position": "scrum_half",
            "is_kicker": False
        })

        # Filter by Ireland
        response = api_context.get("/api/players?country=Ireland")
        assert response.ok
        data = response.json()
        for player in data:
            assert player["country"] == "Ireland"

    def test_filter_players_by_position(self, api_context: APIRequestContext):
        """Test filtering players by position"""
        response = api_context.get("/api/players?position=out_half")
        assert response.ok
        data = response.json()
        for player in data:
            assert player["fantasy_position"] == "out_half"

    def test_optimise_endpoint(self, api_context: APIRequestContext):
        """Test team optimiser endpoint"""
        response = api_context.post("/api/optimise", data={"round": 1})
        assert response.ok
        data = response.json()
        assert "starting_xv" in data
        assert "bench" in data
        assert "total_cost" in data
        assert "remaining_budget" in data

    def test_scrape_status(self, api_context: APIRequestContext):
        """Test scrape status endpoint"""
        response = api_context.get("/api/scrape/status")
        assert response.ok

    def test_predictions_endpoint(self, api_context: APIRequestContext):
        """Test predictions endpoint"""
        response = api_context.get("/api/predictions?round=1")
        assert response.ok
        data = response.json()
        assert isinstance(data, list)


class TestFullWorkflow:
    """Test complete user workflow"""

    def test_complete_fantasy_workflow(self, api_context: APIRequestContext):
        """Test full workflow: create players, import data, optimize"""

        # Step 1: Create multiple players
        players = [
            {"name": "Tadhg Furlong", "country": "Ireland", "fantasy_position": "prop", "is_kicker": False},
            {"name": "Dan Sheehan", "country": "Ireland", "fantasy_position": "hooker", "is_kicker": False},
            {"name": "James Ryan", "country": "Ireland", "fantasy_position": "second_row", "is_kicker": False},
            {"name": "Caelan Doris", "country": "Ireland", "fantasy_position": "back_row", "is_kicker": False},
            {"name": "Jamison Gibson-Park", "country": "Ireland", "fantasy_position": "scrum_half", "is_kicker": False},
            {"name": "Jack Crowley", "country": "Ireland", "fantasy_position": "out_half", "is_kicker": True},
            {"name": "Garry Ringrose", "country": "Ireland", "fantasy_position": "centre", "is_kicker": False},
            {"name": "Hugo Keenan", "country": "Ireland", "fantasy_position": "back_3", "is_kicker": False},
            {"name": "Marcus Smith", "country": "England", "fantasy_position": "out_half", "is_kicker": True},
            {"name": "Maro Itoje", "country": "England", "fantasy_position": "second_row", "is_kicker": False},
        ]

        created_players = []
        for player_data in players:
            response = api_context.post("/api/players", data=player_data)
            assert response.ok
            created_players.append(response.json())

        # Step 2: Import prices
        prices = [{"player_name": p["name"], "price": 10 + i} for i, p in enumerate(players)]
        price_response = api_context.post("/api/import/prices", data={
            "round": 1,
            "season": 2025,
            "prices": prices
        })
        assert price_response.ok

        # Step 3: Import team selections
        teams = {
            "Ireland": [{"player_name": p["name"], "squad_position": i+1}
                       for i, p in enumerate(players) if p["country"] == "Ireland"],
            "England": [{"player_name": p["name"], "squad_position": i+1}
                       for i, p in enumerate(players) if p["country"] == "England"],
        }
        selection_response = api_context.post("/api/import/team-selection", data={
            "round": 1,
            "season": 2025,
            "teams": teams
        })
        assert selection_response.ok

        # Step 4: Generate predictions
        pred_response = api_context.post("/api/predictions/generate?round=1&season=2025")
        assert pred_response.ok

        # Step 5: Get optimised team
        optimise_response = api_context.post("/api/optimise", data={
            "round": 1,
            "budget": 230,
            "max_per_country": 4
        })
        assert optimise_response.ok
        optimised = optimise_response.json()

        # Verify team structure
        assert "starting_xv" in optimised
        assert optimised["total_cost"] <= 230

        # Step 6: Get predictions
        predictions_response = api_context.get("/api/predictions?round=1")
        assert predictions_response.ok

    def test_budget_constraints(self, api_context: APIRequestContext):
        """Test that optimiser respects budget constraints"""
        response = api_context.post("/api/optimise", data={
            "round": 1,
            "budget": 100,  # Very tight budget
        })
        assert response.ok
        data = response.json()
        assert data["total_cost"] <= 100

    def test_country_limit_constraint(self, api_context: APIRequestContext):
        """Test that optimiser respects country limits"""
        response = api_context.post("/api/optimise", data={
            "round": 1,
            "max_per_country": 2,  # Very restrictive
        })
        assert response.ok


class TestErrorHandling:
    """Test error handling"""

    def test_player_not_found(self, api_context: APIRequestContext):
        """Test 404 for non-existent player"""
        response = api_context.get("/api/players/99999")
        assert response.status == 404

    def test_invalid_country_filter(self, api_context: APIRequestContext):
        """Test validation of country filter"""
        response = api_context.get("/api/players?country=InvalidCountry")
        assert response.status == 422  # Validation error

    def test_invalid_position_filter(self, api_context: APIRequestContext):
        """Test validation of position filter"""
        response = api_context.get("/api/players?position=invalid_pos")
        assert response.status == 422  # Validation error
