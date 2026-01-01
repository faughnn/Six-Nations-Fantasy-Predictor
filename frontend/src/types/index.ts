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

export interface StartingXV {
  props: PlayerSummary[];
  hooker: PlayerSummary | null;
  second_row: PlayerSummary[];
  back_row: PlayerSummary[];
  scrum_half: PlayerSummary | null;
  out_half: PlayerSummary | null;
  centres: PlayerSummary[];
  back_3: PlayerSummary[];
}

export interface OptimisedTeam {
  starting_xv: StartingXV;
  bench: PlayerSummary[];
  captain: PlayerSummary | null;
  super_sub: PlayerSummary | null;
  total_cost: number;
  total_predicted_points: number;
  remaining_budget: number;
  empty_slots: Position[];
}

export interface OptimiseRequest {
  round: number;
  budget?: number;
  max_per_country?: number;
  locked_players?: number[];
  excluded_players?: number[];
  min_players?: number;
  include_bench?: boolean;
}
