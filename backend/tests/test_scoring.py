import pytest
from app.services.scoring import calculate_fantasy_points, PlayerStats, is_forward


class TestIsForward:
    def test_prop_is_forward(self):
        assert is_forward("prop") is True

    def test_hooker_is_forward(self):
        assert is_forward("hooker") is True

    def test_second_row_is_forward(self):
        assert is_forward("second_row") is True

    def test_back_row_is_forward(self):
        assert is_forward("back_row") is True

    def test_scrum_half_is_not_forward(self):
        assert is_forward("scrum_half") is False

    def test_out_half_is_not_forward(self):
        assert is_forward("out_half") is False

    def test_centre_is_not_forward(self):
        assert is_forward("centre") is False

    def test_back_3_is_not_forward(self):
        assert is_forward("back_3") is False


class TestCalculateFantasyPoints:
    def test_forward_try_scoring(self):
        stats = PlayerStats(tries=2, is_forward=True)
        points = calculate_fantasy_points(stats)
        assert points >= 30  # 2 * 15

    def test_back_try_scoring(self):
        stats = PlayerStats(tries=2, is_forward=False)
        points = calculate_fantasy_points(stats)
        assert points >= 20  # 2 * 10

    def test_tackle_points(self):
        stats = PlayerStats(tackles_made=15)
        points = calculate_fantasy_points(stats)
        assert points >= 15

    def test_try_assist_points(self):
        stats = PlayerStats(try_assists=2)
        points = calculate_fantasy_points(stats)
        assert points >= 8  # 2 * 4

    def test_conversion_points(self):
        stats = PlayerStats(conversions=5)
        points = calculate_fantasy_points(stats)
        assert points >= 10  # 5 * 2

    def test_penalty_kick_points(self):
        stats = PlayerStats(penalties_kicked=4)
        points = calculate_fantasy_points(stats)
        assert points >= 12  # 4 * 3

    def test_drop_goal_points(self):
        stats = PlayerStats(drop_goals=1)
        points = calculate_fantasy_points(stats)
        assert points >= 5

    def test_defenders_beaten_points(self):
        stats = PlayerStats(defenders_beaten=5)
        points = calculate_fantasy_points(stats)
        assert points >= 10  # 5 * 2

    def test_metres_carried_points(self):
        stats = PlayerStats(metres_carried=50)
        points = calculate_fantasy_points(stats)
        assert points >= 5  # 50 // 10

    def test_offload_points(self):
        stats = PlayerStats(offloads=3)
        points = calculate_fantasy_points(stats)
        assert points >= 6  # 3 * 2

    def test_fifty_22_kick_points(self):
        stats = PlayerStats(fifty_22_kicks=1)
        points = calculate_fantasy_points(stats)
        assert points >= 7

    def test_scrum_won_points_forward(self):
        stats = PlayerStats(scrums_won=8, is_forward=True)
        points = calculate_fantasy_points(stats)
        assert points >= 8

    def test_scrum_won_no_points_for_back(self):
        stats = PlayerStats(scrums_won=8, is_forward=False)
        points = calculate_fantasy_points(stats)
        assert points == 0  # Backs don't get scrum points

    def test_turnover_points(self):
        stats = PlayerStats(turnovers_won=2)
        points = calculate_fantasy_points(stats)
        assert points >= 10  # 2 * 5

    def test_lineout_steal_points(self):
        stats = PlayerStats(lineout_steals=1)
        points = calculate_fantasy_points(stats)
        assert points >= 7

    def test_player_of_match_points(self):
        stats = PlayerStats(player_of_match=True)
        points = calculate_fantasy_points(stats)
        assert points >= 15

    def test_penalty_conceded_negative(self):
        stats = PlayerStats(penalties_conceded=3)
        points = calculate_fantasy_points(stats)
        assert points == -3

    def test_yellow_card_negative(self):
        stats = PlayerStats(yellow_cards=1)
        points = calculate_fantasy_points(stats)
        assert points == -5

    def test_red_card_negative(self):
        stats = PlayerStats(red_cards=1)
        points = calculate_fantasy_points(stats)
        assert points == -8

    def test_complete_forward_game(self):
        """Test a complete forward performance"""
        stats = PlayerStats(
            tries=1,
            try_assists=1,
            tackles_made=12,
            metres_carried=35,
            turnovers_won=1,
            scrums_won=6,
            penalties_conceded=2,
            is_forward=True
        )
        points = calculate_fantasy_points(stats)
        expected = 15 + 4 + 12 + 3 + 5 + 6 - 2  # 43
        assert points == expected

    def test_complete_back_game(self):
        """Test a complete back performance"""
        stats = PlayerStats(
            tries=2,
            try_assists=1,
            conversions=3,
            penalties_kicked=2,
            defenders_beaten=4,
            metres_carried=65,
            tackles_made=5,
            is_forward=False
        )
        points = calculate_fantasy_points(stats)
        expected = 20 + 4 + 6 + 6 + 8 + 6 + 5  # 55
        assert points == expected

    def test_dict_input(self):
        """Test that dict input works"""
        stats = {"tries": 1, "is_forward": True}
        points = calculate_fantasy_points(stats)
        assert points >= 15
