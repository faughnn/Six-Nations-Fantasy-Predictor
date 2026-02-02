import { useQuery } from '@tanstack/react-query';
import { statsApi, historicalStatsApi, projectionsApi, type GetStatsParams, type GetHistoricalSixNationsParams, type GetHistoricalClubParams, type GetProjectionsParams } from '../api/client';

export function useAllStats(params: GetStatsParams = {}) {
  return useQuery({
    queryKey: ['stats', 'all', params],
    queryFn: () => statsApi.getAll(params),
  });
}

export function useStatsCountries() {
  return useQuery({
    queryKey: ['stats', 'countries'],
    queryFn: () => statsApi.getCountries(),
  });
}

export function useStatsPositions() {
  return useQuery({
    queryKey: ['stats', 'positions'],
    queryFn: () => statsApi.getPositions(),
  });
}

export function useHistoricalSixNationsStats(params: GetHistoricalSixNationsParams = {}) {
  return useQuery({
    queryKey: ['stats', 'historical', 'six-nations', params],
    queryFn: () => historicalStatsApi.getSixNations(params),
  });
}

export function useHistoricalClubStats(params: GetHistoricalClubParams = {}) {
  return useQuery({
    queryKey: ['stats', 'historical', 'club', params],
    queryFn: () => historicalStatsApi.getClub(params),
  });
}

export function useHistoricalLeagues() {
  return useQuery({
    queryKey: ['stats', 'historical', 'leagues'],
    queryFn: () => historicalStatsApi.getLeagues(),
  });
}

export function useHistoricalSeasons() {
  return useQuery({
    queryKey: ['stats', 'historical', 'seasons'],
    queryFn: () => historicalStatsApi.getSeasons(),
  });
}

export function useHistoricalPositions() {
  return useQuery({
    queryKey: ['stats', 'historical', 'positions'],
    queryFn: () => historicalStatsApi.getPositions(),
  });
}

export function usePlayerProjections(params: GetProjectionsParams = {}) {
  return useQuery({
    queryKey: ['players', 'projections', params],
    queryFn: () => projectionsApi.getProjections(params),
  });
}
