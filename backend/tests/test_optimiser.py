import pytest
from app.services.optimiser import optimise_team, OptimiserPlayer
from app.schemas.player import Position


def create_test_players():
    """Create a set of test players for optimisation"""
    players = [
        # Props
        OptimiserPlayer(id=1, name="Prop 1", country="Ireland", fantasy_position="prop", price=10, predicted_points=12, is_available=True, is_starting=True),
        OptimiserPlayer(id=2, name="Prop 2", country="England", fantasy_position="prop", price=9, predicted_points=10, is_available=True, is_starting=True),
        OptimiserPlayer(id=3, name="Prop 3", country="France", fantasy_position="prop", price=8, predicted_points=9, is_available=True, is_starting=True),

        # Hookers
        OptimiserPlayer(id=4, name="Hooker 1", country="Ireland", fantasy_position="hooker", price=12, predicted_points=15, is_available=True, is_starting=True),
        OptimiserPlayer(id=5, name="Hooker 2", country="Wales", fantasy_position="hooker", price=10, predicted_points=12, is_available=True, is_starting=True),

        # Second Row
        OptimiserPlayer(id=6, name="Lock 1", country="Ireland", fantasy_position="second_row", price=11, predicted_points=13, is_available=True, is_starting=True),
        OptimiserPlayer(id=7, name="Lock 2", country="England", fantasy_position="second_row", price=10, predicted_points=11, is_available=True, is_starting=True),
        OptimiserPlayer(id=8, name="Lock 3", country="Scotland", fantasy_position="second_row", price=9, predicted_points=10, is_available=True, is_starting=True),

        # Back Row
        OptimiserPlayer(id=9, name="Flanker 1", country="France", fantasy_position="back_row", price=13, predicted_points=18, is_available=True, is_starting=True),
        OptimiserPlayer(id=10, name="Flanker 2", country="Ireland", fantasy_position="back_row", price=12, predicted_points=16, is_available=True, is_starting=True),
        OptimiserPlayer(id=11, name="Number 8", country="England", fantasy_position="back_row", price=14, predicted_points=17, is_available=True, is_starting=True),
        OptimiserPlayer(id=12, name="Flanker 3", country="Italy", fantasy_position="back_row", price=8, predicted_points=9, is_available=True, is_starting=True),

        # Scrum Half
        OptimiserPlayer(id=13, name="SH 1", country="France", fantasy_position="scrum_half", price=15, predicted_points=20, is_available=True, is_starting=True),
        OptimiserPlayer(id=14, name="SH 2", country="Wales", fantasy_position="scrum_half", price=12, predicted_points=15, is_available=True, is_starting=True),

        # Out Half
        OptimiserPlayer(id=15, name="OH 1", country="Ireland", fantasy_position="out_half", price=16, predicted_points=22, is_available=True, is_starting=True),
        OptimiserPlayer(id=16, name="OH 2", country="England", fantasy_position="out_half", price=14, predicted_points=18, is_available=True, is_starting=True),

        # Centres
        OptimiserPlayer(id=17, name="Centre 1", country="France", fantasy_position="centre", price=13, predicted_points=16, is_available=True, is_starting=True),
        OptimiserPlayer(id=18, name="Centre 2", country="Scotland", fantasy_position="centre", price=11, predicted_points=13, is_available=True, is_starting=True),
        OptimiserPlayer(id=19, name="Centre 3", country="Wales", fantasy_position="centre", price=10, predicted_points=12, is_available=True, is_starting=True),

        # Back 3
        OptimiserPlayer(id=20, name="Wing 1", country="France", fantasy_position="back_3", price=14, predicted_points=19, is_available=True, is_starting=True),
        OptimiserPlayer(id=21, name="Wing 2", country="Ireland", fantasy_position="back_3", price=13, predicted_points=17, is_available=True, is_starting=True),
        OptimiserPlayer(id=22, name="Fullback 1", country="England", fantasy_position="back_3", price=15, predicted_points=21, is_available=True, is_starting=True),
        OptimiserPlayer(id=23, name="Wing 3", country="Italy", fantasy_position="back_3", price=9, predicted_points=11, is_available=True, is_starting=True),

        # Bench players
        OptimiserPlayer(id=24, name="Bench Prop", country="Scotland", fantasy_position="prop", price=7, predicted_points=6, is_available=True, is_starting=False),
        OptimiserPlayer(id=25, name="Bench Hooker", country="Italy", fantasy_position="hooker", price=6, predicted_points=5, is_available=True, is_starting=False),
        OptimiserPlayer(id=26, name="Bench SH", country="Wales", fantasy_position="scrum_half", price=8, predicted_points=8, is_available=True, is_starting=False),
    ]
    return players


class TestOptimiser:
    def test_optimiser_respects_budget(self):
        players = create_test_players()
        result = optimise_team(players, budget=230)
        assert result.total_cost <= 230

    def test_optimiser_respects_country_limit(self):
        players = create_test_players()
        result = optimise_team(players, max_per_country=4)

        # Count players per country
        all_players = []

        # Starting XV
        all_players.extend(result.starting_xv.props)
        if result.starting_xv.hooker:
            all_players.append(result.starting_xv.hooker)
        all_players.extend(result.starting_xv.second_row)
        all_players.extend(result.starting_xv.back_row)
        if result.starting_xv.scrum_half:
            all_players.append(result.starting_xv.scrum_half)
        if result.starting_xv.out_half:
            all_players.append(result.starting_xv.out_half)
        all_players.extend(result.starting_xv.centres)
        all_players.extend(result.starting_xv.back_3)

        # Bench
        all_players.extend(result.bench)

        countries = {}
        for p in all_players:
            country = p.country.value
            countries[country] = countries.get(country, 0) + 1

        for country, count in countries.items():
            assert count <= 4, f"Too many players from {country}: {count}"

    def test_optimiser_super_sub_on_bench(self):
        players = create_test_players()
        result = optimise_team(players)

        if result.super_sub:
            assert result.super_sub in result.bench

    def test_optimiser_captain_in_team(self):
        players = create_test_players()
        result = optimise_team(players)

        if result.captain:
            all_players = []
            all_players.extend(result.starting_xv.props)
            if result.starting_xv.hooker:
                all_players.append(result.starting_xv.hooker)
            all_players.extend(result.starting_xv.second_row)
            all_players.extend(result.starting_xv.back_row)
            if result.starting_xv.scrum_half:
                all_players.append(result.starting_xv.scrum_half)
            if result.starting_xv.out_half:
                all_players.append(result.starting_xv.out_half)
            all_players.extend(result.starting_xv.centres)
            all_players.extend(result.starting_xv.back_3)
            all_players.extend(result.bench)

            assert result.captain in all_players

    def test_optimiser_locked_players(self):
        players = create_test_players()
        locked_player_id = 1  # Prop 1

        result = optimise_team(players, locked_players=[locked_player_id])

        all_player_ids = []
        all_player_ids.extend([p.id for p in result.starting_xv.props])
        if result.starting_xv.hooker:
            all_player_ids.append(result.starting_xv.hooker.id)
        all_player_ids.extend([p.id for p in result.starting_xv.second_row])
        all_player_ids.extend([p.id for p in result.starting_xv.back_row])
        if result.starting_xv.scrum_half:
            all_player_ids.append(result.starting_xv.scrum_half.id)
        if result.starting_xv.out_half:
            all_player_ids.append(result.starting_xv.out_half.id)
        all_player_ids.extend([p.id for p in result.starting_xv.centres])
        all_player_ids.extend([p.id for p in result.starting_xv.back_3])
        all_player_ids.extend([p.id for p in result.bench])

        assert locked_player_id in all_player_ids

    def test_optimiser_excluded_players(self):
        players = create_test_players()
        excluded_player_id = 15  # OH 1 (best out half)

        result = optimise_team(players, excluded_players=[excluded_player_id])

        all_player_ids = []
        all_player_ids.extend([p.id for p in result.starting_xv.props])
        if result.starting_xv.hooker:
            all_player_ids.append(result.starting_xv.hooker.id)
        all_player_ids.extend([p.id for p in result.starting_xv.second_row])
        all_player_ids.extend([p.id for p in result.starting_xv.back_row])
        if result.starting_xv.scrum_half:
            all_player_ids.append(result.starting_xv.scrum_half.id)
        if result.starting_xv.out_half:
            all_player_ids.append(result.starting_xv.out_half.id)
        all_player_ids.extend([p.id for p in result.starting_xv.centres])
        all_player_ids.extend([p.id for p in result.starting_xv.back_3])
        all_player_ids.extend([p.id for p in result.bench])

        assert excluded_player_id not in all_player_ids

    def test_optimiser_empty_players(self):
        result = optimise_team([])
        assert result.total_cost == 0
        assert result.total_predicted_points == 0

    def test_optimiser_no_bench(self):
        players = create_test_players()
        result = optimise_team(players, include_bench=False)

        assert len(result.bench) == 0

    def test_optimiser_position_limits(self):
        players = create_test_players()
        result = optimise_team(players)

        assert len(result.starting_xv.props) <= 2
        assert len(result.starting_xv.second_row) <= 2
        assert len(result.starting_xv.back_row) <= 3
        assert len(result.starting_xv.centres) <= 2
        assert len(result.starting_xv.back_3) <= 3
