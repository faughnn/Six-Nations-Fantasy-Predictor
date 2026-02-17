"""
Service for reading scraped per-round Fantasy Six Nations stats from JSON.
"""
import json
from pathlib import Path
from typing import Optional


class FantasyStatsService:
    """Service to read scraped per-round fantasy stats."""

    def __init__(self, file_path: str | None = None):
        if file_path is None:
            backend_dir = Path(__file__).parent.parent.parent
            file_path = backend_dir / "data" / "fantasy_stats_2026.json"
        self.file_path = Path(file_path)
        self._cache: dict | None = None

    def _load(self) -> dict:
        if self._cache is not None:
            return self._cache
        if not self.file_path.exists():
            raise FileNotFoundError(f"Stats file not found: {self.file_path}")
        with open(self.file_path, "r", encoding="utf-8") as f:
            self._cache = json.load(f)
        return self._cache

    def get_players(
        self,
        game_round: Optional[int] = None,
        country: Optional[str] = None,
        position: Optional[str] = None,
    ) -> list[dict]:
        data = self._load()
        players = data.get("players", [])

        if game_round is not None:
            players = [p for p in players if p.get("round") == game_round]

        if country:
            players = [p for p in players if p.get("country") == country]

        if position:
            players = [p for p in players if p.get("position") == position]

        return players

    def get_metadata(self) -> dict:
        data = self._load()
        return {
            "scraped_at": data.get("scraped_at"),
            "season": data.get("season"),
            "rounds_scraped": data.get("rounds_scraped", []),
            "total_records": data.get("total_records", 0),
            "stat_columns": data.get("stat_columns", []),
            "stat_display": data.get("stat_display", {}),
        }

    def get_countries(self) -> list[str]:
        data = self._load()
        players = data.get("players", [])
        return sorted(set(p.get("country", "") for p in players if p.get("country")))

    def get_positions(self) -> list[str]:
        data = self._load()
        players = data.get("players", [])
        return sorted(set(p.get("position", "") for p in players if p.get("position")))

    def get_rounds(self) -> list[int]:
        data = self._load()
        return sorted(data.get("rounds_scraped", []))
