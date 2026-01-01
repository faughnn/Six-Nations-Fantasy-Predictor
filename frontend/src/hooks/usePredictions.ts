import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { predictionsApi } from '../api/client';

export function usePredictions(round: number, position?: string, minPredicted?: number) {
  return useQuery({
    queryKey: ['predictions', round, position, minPredicted],
    queryFn: () => predictionsApi.getAll(round, position, minPredicted),
  });
}

export function usePrediction(playerId: number, round = 1, season = 2025) {
  return useQuery({
    queryKey: ['prediction', playerId, round, season],
    queryFn: () => predictionsApi.getById(playerId, round, season),
    enabled: !!playerId,
  });
}

export function useGeneratePredictions() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ round, season }: { round: number; season?: number }) =>
      predictionsApi.generate(round, season),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['predictions'] });
    },
  });
}
