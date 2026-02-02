"""
Service for reading player stats from the Excel file.
"""
import os
from pathlib import Path

import pandas as pd


class ExcelStatsService:
    """Service to read and process player stats from Excel file."""

    COUNTRIES = ["France", "England", "Ireland", "Scotland", "Italy", "Wales"]

    # Column name mapping (Excel -> API)
    COLUMN_MAP = {
        "Name": "name",
        "Position": "position",
        "Minutes": "minutes",
        "Tackles": "tackles",
        "Penalties Conceded": "penalties_conceded",
        "DefendersBeaten": "defenders_beaten",
        "Meters Carried": "meters_carried",
        "Kick 50-22": "kick_50_22",
        "Lineouts Won": "lineouts_won",
        "Breakdown Steal": "breakdown_steal",
        "Try": "try_scored",
        "Assist": "assist",
        "Conversion ": "conversion",  # Note: Excel has trailing space
        "Conversion": "conversion",
        "Penalty": "penalty",
        "Drop Goal": "drop_goal",
        "Yellow Card": "yellow_card",
        "Red Card": "red_card",
        "MOTM": "motm",
        "Att Scrum": "att_scrum",
        "Offloads": "offloads",
        "WK 1": "wk1",
        "WK 2": "wk2",
        "WK 3": "wk3",
        "WK 4": "wk4",
        "WK 5": "wk5",
        "WK1": "wk1",
        "WK2": "wk2",
        "WK3": "wk3",
        "WK4": "wk4",
        "WK5": "wk5",
        "Points": "points",
        "Value": "value",
        "Value Start": "value_start",
        "Change": "change",
        "Country": "country",
    }

    def __init__(self, file_path: str | None = None):
        if file_path is None:
            # Default path relative to backend directory
            backend_dir = Path(__file__).parent.parent.parent
            file_path = backend_dir / "data" / "M6N 2025 Fantasy Stats.xlsx"
        self.file_path = Path(file_path)

    def get_all_players(self) -> list[dict]:
        """
        Read all country sheets from Excel and combine into single list.
        Each player dict includes their country.
        """
        if not self.file_path.exists():
            raise FileNotFoundError(f"Excel file not found: {self.file_path}")

        all_players = []

        for country in self.COUNTRIES:
            try:
                df = pd.read_excel(self.file_path, sheet_name=country)
                df["Country"] = country

                # Rename columns to API format
                df = df.rename(columns=self.COLUMN_MAP)

                # Remove duplicate columns (some sheets have both WK 1 and WK1)
                df = df.loc[:, ~df.columns.duplicated()]

                # Convert to list of dicts
                players = df.to_dict(orient="records")

                # Clean up NaN values to None for JSON serialization
                for player in players:
                    for key, value in player.items():
                        if pd.isna(value):
                            player[key] = None

                all_players.extend(players)

            except Exception as e:
                print(f"Error reading {country} sheet: {e}")
                continue

        return all_players

    def get_players_by_country(self, country: str) -> list[dict]:
        """Get players for a specific country."""
        all_players = self.get_all_players()
        return [p for p in all_players if p.get("country") == country]

    def get_players_by_position(self, position: str) -> list[dict]:
        """Get players for a specific position."""
        all_players = self.get_all_players()
        return [p for p in all_players if p.get("position") == position]
