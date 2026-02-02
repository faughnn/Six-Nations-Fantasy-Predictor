import { useQuery } from '@tanstack/react-query';
import { playersApi, type GetPlayersParams } from '../api/client';

export function usePlayers(params: GetPlayersParams = {}) {
  return useQuery({
    queryKey: ['players', params],
    queryFn: () => playersApi.getAll(params),
  });
}

export function usePlayer(id: number, season = 2025, round = 1) {
  return useQuery({
    queryKey: ['player', id, season, round],
    queryFn: () => playersApi.getById(id, season, round),
    enabled: !!id,
  });
}

