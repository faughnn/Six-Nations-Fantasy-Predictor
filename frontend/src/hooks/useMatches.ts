import { useQuery } from '@tanstack/react-query';
import { matchesApi } from '../api/client';

export function useMatches(season: number, gameRound: number) {
  return useQuery({
    queryKey: ['matches', season, gameRound],
    queryFn: () => matchesApi.getAll(season, gameRound),
    enabled: season > 0 && gameRound > 0,
  });
}

export function useCurrentRound() {
  return useQuery({
    queryKey: ['currentRound'],
    queryFn: () => matchesApi.getCurrentRound(),
  });
}

export function useRoundScrapeStatus(season: number, gameRound: number) {
  return useQuery({
    queryKey: ['roundScrapeStatus', season, gameRound],
    queryFn: () => matchesApi.getScrapeStatus(season, gameRound),
    enabled: season > 0 && gameRound > 0,
    refetchInterval: 30000, // refresh every 30s
  });
}
