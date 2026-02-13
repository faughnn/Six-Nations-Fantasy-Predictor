import axios from 'axios';
import type { PlayerSummary, PlayerDetail, PredictionDetail, PlayerStat, HistoricalSixNationsStat, HistoricalClubStat, MatchData, PlayerProjection, TryScorerDetail } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface GetPlayersParams {
  country?: string;
  position?: string;
  min_price?: number;
  max_price?: number;
  is_available?: boolean;
  season?: number;
  round?: number;
}

export const playersApi = {
  getAll: async (params: GetPlayersParams = {}): Promise<PlayerSummary[]> => {
    const response = await api.get('/api/players', { params });
    return response.data;
  },

  getById: async (id: number, season = 2025, round = 1): Promise<PlayerDetail> => {
    const response = await api.get(`/api/players/${id}`, { params: { season, round } });
    return response.data;
  },

};

export const predictionsApi = {
  getAll: async (round: number, position?: string, minPredicted?: number): Promise<PredictionDetail[]> => {
    const response = await api.get('/api/predictions', {
      params: { round, position, min_predicted: minPredicted },
    });
    return response.data;
  },

  getById: async (playerId: number, round = 1, season = 2025): Promise<PredictionDetail> => {
    const response = await api.get(`/api/predictions/${playerId}`, { params: { round, season } });
    return response.data;
  },

  generate: async (round: number, season = 2025): Promise<{ status: string; predictions_generated: number }> => {
    const response = await api.post('/api/predictions/generate', null, { params: { round, season } });
    return response.data;
  },
};

export interface GetStatsParams {
  country?: string;
  position?: string;
}

export const statsApi = {
  getAll: async (params: GetStatsParams = {}): Promise<PlayerStat[]> => {
    const response = await api.get('/api/stats/all', { params });
    return response.data;
  },

  getCountries: async (): Promise<string[]> => {
    const response = await api.get('/api/stats/countries');
    return response.data;
  },

  getPositions: async (): Promise<string[]> => {
    const response = await api.get('/api/stats/positions');
    return response.data;
  },
};

export interface GetHistoricalSixNationsParams {
  country?: string;
  position?: string;
  season?: number;
}

export interface GetHistoricalClubParams {
  country?: string;
  position?: string;
  league?: string;
}

export const historicalStatsApi = {
  getSixNations: async (params: GetHistoricalSixNationsParams = {}): Promise<HistoricalSixNationsStat[]> => {
    const response = await api.get('/api/stats/historical/six-nations', { params });
    return response.data;
  },

  getClub: async (params: GetHistoricalClubParams = {}): Promise<HistoricalClubStat[]> => {
    const response = await api.get('/api/stats/historical/club', { params });
    return response.data;
  },

  getLeagues: async (): Promise<string[]> => {
    const response = await api.get('/api/stats/historical/leagues');
    return response.data;
  },

  getSeasons: async (): Promise<number[]> => {
    const response = await api.get('/api/stats/historical/seasons');
    return response.data;
  },

  getPositions: async (): Promise<string[]> => {
    const response = await api.get('/api/stats/historical/positions');
    return response.data;
  },
};

export interface GetProjectionsParams {
  country?: string;
  position?: string;
  sort_by?: string;
  season?: number;
  game_round?: number;
}

export const projectionsApi = {
  getProjections: async (params: GetProjectionsParams = {}): Promise<PlayerProjection[]> => {
    const response = await api.get('/api/players/projections', { params });
    return response.data;
  },
};

export interface CurrentRound {
  season: number;
  round: number;
}

export interface MatchScrapeStatus {
  home_team: string;
  away_team: string;
  match_date: string;
  has_handicap: boolean;
  has_totals: boolean;
  has_try_scorer: boolean;
  try_scorer_count: number;
}

export interface RoundScrapeStatus {
  season: number;
  round: number;
  matches: MatchScrapeStatus[];
  missing_markets: string[];
  has_prices: boolean;
  price_count: number;
}

export const matchesApi = {
  getAll: async (season: number, gameRound: number): Promise<MatchData[]> => {
    const response = await api.get('/api/matches', {
      params: { season, game_round: gameRound },
    });
    return response.data;
  },

  getCurrentRound: async (): Promise<CurrentRound> => {
    const response = await api.get('/api/matches/current-round');
    return response.data;
  },

  getScrapeStatus: async (season: number, gameRound: number): Promise<RoundScrapeStatus> => {
    const response = await api.get('/api/matches/status', {
      params: { season, game_round: gameRound },
    });
    return response.data;
  },

  getTryScorers: async (season: number, gameRound: number): Promise<TryScorerDetail[]> => {
    const response = await api.get('/api/matches/tryscorers', {
      params: { season, game_round: gameRound },
    });
    return response.data;
  },
};

export interface ScrapeJobStatus {
  status: string;
  message?: string;
  matches_found?: number;
  matches_completed?: number;
  current_match?: string;
}

export type ScrapeResponse = { status: string; job_id: string; message?: string };

export const scrapeApi = {
  scrapeAllMatchOdds: async (season: number, round: number): Promise<ScrapeResponse> => {
    const response = await api.post('/api/scrape/all-match-odds', { season, round });
    return response.data;
  },

  scrapeMarket: async (season: number, round: number, market: string): Promise<ScrapeResponse> => {
    const response = await api.post('/api/scrape/market', { season, round, market });
    return response.data;
  },

  scrapeMissing: async (season: number, round: number): Promise<ScrapeResponse> => {
    const response = await api.post('/api/scrape/missing', { season, round });
    return response.data;
  },

  importPrices: async (season: number, round: number): Promise<ScrapeResponse> => {
    const response = await api.post('/api/scrape/import-prices', { season, round });
    return response.data;
  },

  getJobStatus: async (jobId: string): Promise<ScrapeJobStatus> => {
    const response = await api.get(`/api/scrape/status/${jobId}`);
    return response.data;
  },
};

export default api;
