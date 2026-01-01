import { useState } from 'react';
import { useOptimiser } from '../hooks/useOptimiser';
import { OptimiserForm } from '../components/optimiser/OptimiserForm';
import { OptimiserResult } from '../components/optimiser/OptimiserResult';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import type { OptimiseRequest, OptimisedTeam } from '../types';

export default function Optimiser() {
  const [result, setResult] = useState<OptimisedTeam | null>(null);
  const { mutate: optimise, isPending, error } = useOptimiser();

  const handleSubmit = (request: OptimiseRequest) => {
    optimise(request, {
      onSuccess: (data) => {
        setResult(data);
      },
    });
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Team Optimiser</h1>

      <OptimiserForm onSubmit={handleSubmit} isLoading={isPending} />

      {isPending && (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && (
        <div className="card bg-red-50 border border-red-200">
          <p className="text-red-600">
            Error generating team. Please try again.
          </p>
        </div>
      )}

      {result && !isPending && <OptimiserResult result={result} />}
    </div>
  );
}
