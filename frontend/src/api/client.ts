import axios from 'axios';
import type { PlayerSummary, PlayerDetail, OptimisedTeam, OptimiseRequest, PredictionDetail } from '../types';

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

  compare: async (round: number, position?: string): Promise<PlayerSummary[]> => {
    const response = await api.get('/api/players/compare', { params: { round, position } });
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

export const optimiserApi = {
  optimise: async (request: OptimiseRequest): Promise<OptimisedTeam> => {
    const response = await api.post('/api/optimise', request);
    return response.data;
  },
};

export const scrapeApi = {
  scrapeOdds: async (round: number): Promise<{ status: string; job_id: string }> => {
    const response = await api.post('/api/scrape/odds', { round });
    return response.data;
  },

  scrapePrices: async (round: number): Promise<{ status: string; job_id: string }> => {
    const response = await api.post('/api/scrape/fantasy-prices', { round });
    return response.data;
  },

  getStatus: async (): Promise<Record<string, { status: string; message?: string }>> => {
    const response = await api.get('/api/scrape/status');
    return response.data;
  },
};

export const importApi = {
  importPrices: async (
    round: number,
    prices: { player_name: string; price: number }[],
    season = 2025
  ): Promise<{ status: string; imported: number; errors: string[] }> => {
    const response = await api.post('/api/import/prices', { round, season, prices });
    return response.data;
  },

  importTeamSelection: async (
    round: number,
    teams: Record<string, { player_name: string; squad_position: number }[]>,
    season = 2025
  ): Promise<{ status: string; imported: number; errors: string[] }> => {
    const response = await api.post('/api/import/team-selection', { round, season, teams });
    return response.data;
  },
};

export default api;
