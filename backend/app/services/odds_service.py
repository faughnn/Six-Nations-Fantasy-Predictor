"""
Service for managing odds data in the database.
Handles fuzzy player name matching and saving/updating odds records.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import date, datetime
from decimal import Decimal
import logging
import re

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from rapidfuzz import fuzz, process

from app.models import Player, Odds, MatchOdds

logger = logging.getLogger(__name__)

# Minimum fuzzy match score (0-100)
FUZZY_MATCH_THRESHOLD = 80
LOW_CONFIDENCE_THRESHOLD = 90  # Matches below this are logged as low confidence


class OddsService:
    """Service for managing odds data in the database."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._player_cache: Optional[Dict[str, Player]] = None

    async def _get_all_players(self) -> List[Player]:
        """Fetch all players from database."""
        query = select(Player)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _build_player_cache(self) -> Dict[str, Player]:
        """Build a cache of player names to Player objects."""
        if self._player_cache is not None:
            return self._player_cache

        players = await self._get_all_players()
        self._player_cache = {}

        for player in players:
            # Store by normalized name
            normalized = self._normalize_name(player.name)
            self._player_cache[normalized] = player

            # Also store original name
            self._player_cache[player.name.lower()] = player

        return self._player_cache

    def _normalize_name(self, name: str) -> str:
        """Normalize a player name for matching."""
        if not name:
            return ""

        # Convert to lowercase
        name = name.lower().strip()

        # Remove team/country suffix in parentheses
        name = re.sub(r'\s*\([^)]+\)\s*$', '', name)

        # Remove common prefixes/suffixes
        name = re.sub(r'^(mr|dr|sir)\s+', '', name)

        # Expand common abbreviations
        # "M. Smith" -> keep as is for now, fuzzy will handle

        # Remove extra whitespace
        name = ' '.join(name.split())

        return name

    def _expand_abbreviated_name(self, name: str) -> str:
        """Try to expand abbreviated first names."""
        # Pattern: "J. Smith" or "J Smith"
        match = re.match(r'^([A-Z])\.\s*(.+)$', name)
        if match:
            initial = match.group(1)
            surname = match.group(2)
            return f"{initial} {surname}"
        return name

    async def find_player_by_name(
        self, scraped_name: str, countries: Optional[List[str]] = None
    ) -> Tuple[Optional[Player], float]:
        """
        Find a player by name using fuzzy matching.

        Args:
            scraped_name: The player name scraped from odds source.
            countries: Optional list of countries to restrict matching to
                (e.g. the two teams in a match). Prevents cross-match mismatches.

        Returns:
            Tuple of (Player or None, confidence score 0-100)
        """
        cache = await self._build_player_cache()
        normalized_scraped = self._normalize_name(scraped_name)

        # Build filtered cache if countries provided
        if countries:
            country_set = {c.lower() for c in countries}
            filtered_cache = {
                k: v for k, v in cache.items()
                if v.country and v.country.lower() in country_set
            }
        else:
            filtered_cache = cache

        # Try exact match first (in filtered set)
        if normalized_scraped in filtered_cache:
            return filtered_cache[normalized_scraped], 100.0

        # Try fuzzy matching
        player_names = list(filtered_cache.keys())
        if not player_names:
            return None, 0.0

        # Use token_sort_ratio for better handling of name order differences
        matches = process.extract(
            normalized_scraped,
            player_names,
            scorer=fuzz.token_sort_ratio,
            limit=3
        )

        if matches and matches[0][1] >= FUZZY_MATCH_THRESHOLD:
            best_match_name = matches[0][0]
            confidence = matches[0][1]
            return filtered_cache[best_match_name], confidence

        # Try with partial ratio for abbreviated names
        matches = process.extract(
            normalized_scraped,
            player_names,
            scorer=fuzz.partial_ratio,
            limit=3
        )

        if matches and matches[0][1] >= FUZZY_MATCH_THRESHOLD:
            best_match_name = matches[0][0]
            confidence = matches[0][1]
            return filtered_cache[best_match_name], confidence

        return None, 0.0

    async def save_anytime_try_scorer_odds(
        self,
        odds_data: List[Dict[str, Any]],
        season: int,
        round_num: int,
        match_date: date,
        home_team: Optional[str] = None,
        away_team: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Save scraped try scorer odds to database, matching players by name.

        Args:
            odds_data: List of dicts with player_name, average_odds, etc.
            season: Season year (e.g., 2025)
            round_num: Round number
            match_date: Date of the match
            home_team: Home team country name (constrains fuzzy matching)
            away_team: Away team country name (constrains fuzzy matching)

        Returns:
            Dict with counts: saved, updated, not_found, low_confidence_matches
        """
        saved = 0
        updated = 0
        not_found = []
        low_confidence_matches = []

        # Build country filter from match teams
        countries = [home_team, away_team] if home_team and away_team else None

        for item in odds_data:
            player_name = item["player_name"]
            average_odds = Decimal(str(item["average_odds"]))

            # Find player by name, constrained to match countries when available
            player, confidence = await self.find_player_by_name(
                player_name, countries=countries
            )

            if not player:
                not_found.append(player_name)
                logger.info(f"Player not found: {player_name}")
                continue

            # Log low confidence matches
            if confidence < LOW_CONFIDENCE_THRESHOLD:
                low_confidence_matches.append({
                    "scraped_name": player_name,
                    "matched_name": player.name,
                    "confidence": confidence,
                })
                logger.warning(
                    f"Low confidence match: '{player_name}' -> '{player.name}' ({confidence}%)"
                )

            # Check if odds record exists for this player/round
            existing = await self._get_existing_odds(
                player.id, season, round_num, match_date
            )

            if existing:
                existing.anytime_try_scorer = average_odds
                existing.match_date = match_date
                existing.scraped_at = datetime.utcnow()
                updated += 1
                logger.debug(f"Updated odds for {player.name}: {average_odds}")
            else:
                new_odds = Odds(
                    player_id=player.id,
                    season=season,
                    round=round_num,
                    match_date=match_date,
                    anytime_try_scorer=average_odds,
                    source="oddschecker",
                )
                self.db.add(new_odds)
                saved += 1
                logger.debug(f"Saved odds for {player.name}: {average_odds}")

        await self.db.commit()

        logger.info(
            f"Odds save complete: {saved} saved, {updated} updated, "
            f"{len(not_found)} not found, {len(low_confidence_matches)} low confidence"
        )

        return {
            "saved": saved,
            "updated": updated,
            "not_found": not_found,
            "low_confidence_matches": low_confidence_matches,
        }

    async def _get_existing_odds(
        self, player_id: int, season: int, round_num: int, match_date: date
    ) -> Optional[Odds]:
        """Check for existing odds record."""
        query = select(Odds).where(
            Odds.player_id == player_id,
            Odds.season == season,
            Odds.round == round_num,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def save_match_totals_odds(
        self,
        totals_data: List[Dict[str, Any]],
        season: int,
        round_num: int,
        match_date: date,
        home_team: str,
        away_team: str,
    ) -> Dict[str, Any]:
        """
        Save scraped match totals odds to database.

        Args:
            totals_data: List of dicts with line, over_odds, under_odds
            season: Season year
            round_num: Round number
            match_date: Date of the match
            home_team: Home team name
            away_team: Away team name

        Returns:
            Dict with save status and data
        """
        # We typically want to save the main line (most common is around 40-50 points)
        # For now, save all lines or the primary one
        if not totals_data:
            return {
                "saved": False,
                "error": "No totals data provided",
            }

        # Find the existing match odds record or create new
        existing = await self._get_existing_match_odds(
            season, round_num, match_date, home_team, away_team
        )

        # Use the first/primary line, but reject if too few bookmakers
        MIN_BOOKMAKERS = 3
        primary_line = totals_data[0]
        num_bookmakers = primary_line.get("num_bookmakers", 0)
        if num_bookmakers < MIN_BOOKMAKERS:
            logger.warning(
                f"Totals for {home_team} vs {away_team} has only {num_bookmakers} "
                f"bookmaker(s) (min {MIN_BOOKMAKERS}) — skipping unreliable line {primary_line.get('line')}"
            )
            return {
                "saved": False,
                "skipped": True,
                "reason": f"Only {num_bookmakers} bookmaker(s) — need at least {MIN_BOOKMAKERS}",
                "line": primary_line.get("line"),
            }

        line_value = Decimal(str(primary_line["line"]))
        over_odds = Decimal(str(primary_line.get("over_odds", 0))) if primary_line.get("over_odds") else None
        under_odds = Decimal(str(primary_line.get("under_odds", 0))) if primary_line.get("under_odds") else None

        if existing:
            existing.over_under_line = line_value
            existing.over_odds = over_odds
            existing.under_odds = under_odds
            existing.match_date = match_date
            existing.scraped_at = datetime.utcnow()
            status = "updated"
        else:
            new_match_odds = MatchOdds(
                season=season,
                round=round_num,
                match_date=match_date,
                home_team=home_team,
                away_team=away_team,
                over_under_line=line_value,
                over_odds=over_odds,
                under_odds=under_odds,
                scraped_at=datetime.utcnow(),
            )
            self.db.add(new_match_odds)
            status = "saved"

        await self.db.commit()

        logger.info(
            f"Match totals odds {status}: {home_team} vs {away_team}, "
            f"line={line_value}, over={over_odds}, under={under_odds}"
        )

        return {
            "saved": status == "saved",
            "updated": status == "updated",
            "line": float(line_value),
            "over_odds": float(over_odds) if over_odds else None,
            "under_odds": float(under_odds) if under_odds else None,
            "all_lines": totals_data,
        }

    async def _get_existing_match_odds(
        self,
        season: int,
        round_num: int,
        match_date: date,
        home_team: str,
        away_team: str,
    ) -> Optional[MatchOdds]:
        """Check for existing match odds record."""
        query = select(MatchOdds).where(
            MatchOdds.season == season,
            MatchOdds.round == round_num,
            MatchOdds.home_team == home_team,
            MatchOdds.away_team == away_team,
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def save_handicap_odds(
        self,
        handicap_data: List[Dict[str, Any]],
        season: int,
        round_num: int,
        match_date: date,
        home_team: str,
        away_team: str,
    ) -> Dict[str, Any]:
        """
        Save scraped handicap odds to database.

        Args:
            handicap_data: List of dicts with line, home_odds, away_odds
            season: Season year
            round_num: Round number
            match_date: Date of the match
            home_team: Home team name
            away_team: Away team name

        Returns:
            Dict with save status and data
        """
        if not handicap_data:
            return {
                "saved": False,
                "error": "No handicap data provided",
            }

        # Find existing match odds record or create new
        existing = await self._get_existing_match_odds(
            season, round_num, match_date, home_team, away_team
        )

        # Use the first/primary line, but reject if too few bookmakers
        MIN_BOOKMAKERS = 3
        primary_line = handicap_data[0]
        num_bookmakers = primary_line.get("num_bookmakers", 0)
        if num_bookmakers < MIN_BOOKMAKERS:
            logger.warning(
                f"Handicap for {home_team} vs {away_team} has only {num_bookmakers} "
                f"bookmaker(s) (min {MIN_BOOKMAKERS}) — skipping unreliable line {primary_line.get('line')}"
            )
            return {
                "saved": False,
                "skipped": True,
                "reason": f"Only {num_bookmakers} bookmaker(s) — need at least {MIN_BOOKMAKERS}",
                "line": primary_line.get("line"),
            }

        line_value = Decimal(str(primary_line["line"]))
        home_odds = Decimal(str(primary_line.get("home_odds", 0))) if primary_line.get("home_odds") else None
        away_odds = Decimal(str(primary_line.get("away_odds", 0))) if primary_line.get("away_odds") else None

        if existing:
            existing.handicap_line = line_value
            existing.home_handicap_odds = home_odds
            existing.away_handicap_odds = away_odds
            existing.match_date = match_date
            existing.scraped_at = datetime.utcnow()
            status = "updated"
        else:
            new_match_odds = MatchOdds(
                season=season,
                round=round_num,
                match_date=match_date,
                home_team=home_team,
                away_team=away_team,
                handicap_line=line_value,
                home_handicap_odds=home_odds,
                away_handicap_odds=away_odds,
                scraped_at=datetime.utcnow(),
            )
            self.db.add(new_match_odds)
            status = "saved"

        await self.db.commit()

        logger.info(
            f"Handicap odds {status}: {home_team} vs {away_team}, "
            f"line={line_value}, home={home_odds}, away={away_odds}"
        )

        return {
            "saved": status == "saved",
            "updated": status == "updated",
            "line": float(line_value),
            "home_handicap_odds": float(home_odds) if home_odds else None,
            "away_handicap_odds": float(away_odds) if away_odds else None,
            "all_lines": handicap_data,
        }

    async def get_player_odds_for_round(
        self, season: int, round_num: int
    ) -> List[Dict[str, Any]]:
        """Get all player odds for a specific round."""
        query = (
            select(Odds, Player)
            .join(Player, Odds.player_id == Player.id)
            .where(Odds.season == season, Odds.round == round_num)
            .order_by(Odds.anytime_try_scorer)
        )
        result = await self.db.execute(query)

        odds_list = []
        for odds, player in result.all():
            odds_list.append({
                "player_id": player.id,
                "player_name": player.name,
                "country": player.country,
                "anytime_try_scorer": float(odds.anytime_try_scorer) if odds.anytime_try_scorer else None,
                "first_try_scorer": float(odds.first_try_scorer) if odds.first_try_scorer else None,
                "scraped_at": odds.scraped_at.isoformat() if odds.scraped_at else None,
            })

        return odds_list
