export type Country = 'Ireland' | 'England' | 'France' | 'Wales' | 'Scotland' | 'Italy';

export type Position = 'prop' | 'hooker' | 'second_row' | 'back_row' | 'scrum_half' | 'out_half' | 'centre' | 'back_3';

export type League = 'urc' | 'premiership' | 'top_14';

export interface PlayerSummary {
  id: number;
  name: string;
  country: Country;
  fantasy_position: Position;
  club: string | null;
  league: League | null;
  price: number | null;
  is_available: boolean;
  is_starting: boolean | null;
  predicted_points: number | null;
  points_per_star: number | null;
  value_score: number | null;
  recent_form: number | null;
  anytime_try_odds: number | null;
}

export interface StatsHistory {
  match_date: string;
  opponent: string;
  fantasy_points: number | null;
  tries: number;
  tackles_made: number;
  metres_carried: number;
}

export interface PlayerDetail extends PlayerSummary {
  is_kicker: boolean;
  six_nations_stats: StatsHistory[];
  club_stats: StatsHistory[];
  prediction_breakdown: Record<string, unknown> | null;
}

export interface PredictionBreakdown {
  predicted_tries: number;
  predicted_try_prob: number;
  predicted_tackles: number;
  predicted_metres: number;
  predicted_turnovers: number;
  predicted_conversions: number;
  predicted_penalties: number;
}

export interface PredictionDetail {
  player_id: number;
  player_name: string;
  predicted_points: number;
  confidence_interval: [number, number];
  breakdown: PredictionBreakdown;
  key_factors: string[];
}

// Excel stats data types
export type ExcelPosition = 'Back-row' | 'Prop' | 'Back Three' | 'Second-row' | 'Centre' | 'Scrum-half' | 'Fly-half' | 'Hooker';

export interface PlayerStat {
  name: string;
  country: string;
  position: ExcelPosition;
  minutes: number;
  tackles: number;
  penalties_conceded: number | null;
  defenders_beaten: number | null;
  meters_carried: number | null;
  kick_50_22: number | null;
  lineouts_won: number | null;
  breakdown_steal: number | null;
  try_scored: number | null;
  assist: number | null;
  conversion: number | null;
  penalty: number | null;
  drop_goal: number | null;
  yellow_card: number | null;
  red_card: number | null;
  motm: number | null;
  att_scrum: number | null;
  offloads: number | null;
  wk1: number | null;
  wk2: number | null;
  wk3: number | null;
  wk4: number | null;
  wk5: number | null;
  points: number;
  value: number;
  value_start: number;
  change: number;
}

// Historical stats from database (rugbypy)
export interface HistoricalSixNationsStat {
  player_id: number;
  player_name: string;
  country: string;
  fantasy_position: string;
  season: number;
  round: number;
  match_date: string;
  opponent: string;
  home_away: string;
  actual_position: string | null;
  started: boolean;
  minutes_played: number | null;
  tries: number;
  try_assists: number;
  conversions: number;
  penalties_kicked: number;
  drop_goals: number;
  defenders_beaten: number;
  metres_carried: number;
  clean_breaks: number;
  offloads: number;
  fifty_22_kicks: number;
  tackles_made: number;
  tackles_missed: number;
  turnovers_won: number;
  lineout_steals: number;
  scrums_won: number;
  penalties_conceded: number;
  yellow_cards: number;
  red_cards: number;
  player_of_match: boolean;
  fantasy_points: number | null;
}

export interface MatchTryScorer {
  player_id: number;
  name: string;
  country: string;
  odds: number;
  implied_prob: number;
}

export interface TryScorerDetail {
  player_id: number;
  name: string;
  country: string;
  fantasy_position: string;
  match: string;
  anytime_try_odds: number | null;
  implied_prob: number | null;
  expected_try_points: number | null;
  price: number | null;
  ownership_pct?: number | null;
  exp_pts_per_star: number | null;
  availability?: 'starting' | 'substitute' | 'not_playing';
}

export interface MatchData {
  home_team: string;
  away_team: string;
  match_date: string;
  home_win: number | null;
  away_win: number | null;
  draw: number | null;
  handicap_line: number | null;
  home_handicap_odds: number | null;
  away_handicap_odds: number | null;
  over_under_line: number | null;
  over_odds: number | null;
  under_odds: number | null;
  top_try_scorers: MatchTryScorer[];
}

export interface PlayerProjection {
  id: number;
  name: string;
  country: string;
  fantasy_position: string;
  price: number | null;
  predicted_points: number | null;
  points_per_star: number | null;
  avg_tries: number | null;
  avg_tackles: number | null;
  avg_metres: number | null;
  avg_turnovers: number | null;
  avg_defenders_beaten: number | null;
  avg_offloads: number | null;
  expected_minutes: number | null;
  start_rate: number | null;
  points_per_minute: number | null;
  anytime_try_odds: number | null;
  opponent: string | null;
  home_away: string | null;
  total_games: number;
}

// Fantasy stats scraped from fantasy.sixnationsrugby.com (per-round)
export interface FantasyStatPlayer {
  name: string;
  country: string;
  position: Position | '';
  round: number;
  minutes_played: number;
  player_of_match: number;
  tries: number;
  try_assists: number;
  conversions: number;
  penalties_kicked: number;
  drop_goals: number;
  tackles_made: number;
  metres_carried: number;
  defenders_beaten: number;
  offloads: number;
  fifty_22_kicks: number;
  lineout_steals: number;
  breakdown_steals: number;
  kick_returns: number;
  scrums_won: number;
  penalties_conceded: number;
  yellow_cards: number;
  red_cards: number;
  fantasy_points: number;
}

export interface FantasyStatsMetadata {
  scraped_at: string;
  season: number;
  rounds_scraped: number[];
  total_records: number;
  stat_columns: string[];
  stat_display: Record<string, string>;
}

export interface HistoricalClubStat {
  player_id: number;
  player_name: string;
  country: string;
  fantasy_position: string;
  league: string;
  season: string;
  match_date: string;
  opponent: string;
  home_away: string;
  started: boolean;
  minutes_played: number | null;
  tries: number;
  try_assists: number;
  conversions: number;
  penalties_kicked: number;
  drop_goals: number;
  defenders_beaten: number;
  metres_carried: number;
  clean_breaks: number;
  offloads: number;
  tackles_made: number;
  tackles_missed: number;
  turnovers_won: number;
  lineout_steals: number;
  scrums_won: number;
  penalties_conceded: number;
  yellow_cards: number;
  red_cards: number;
}
