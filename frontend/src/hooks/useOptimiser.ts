import { useMutation } from '@tanstack/react-query';
import { optimiserApi } from '../api/client';
import type { OptimiseRequest } from '../types';

export function useOptimiser() {
  return useMutation({
    mutationFn: (request: OptimiseRequest) => optimiserApi.optimise(request),
  });
}
