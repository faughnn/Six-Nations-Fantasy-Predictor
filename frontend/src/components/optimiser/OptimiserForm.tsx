import { useState } from 'react';
import type { OptimiseRequest } from '../../types';

interface OptimiserFormProps {
  onSubmit: (request: OptimiseRequest) => void;
  isLoading?: boolean;
}

export function OptimiserForm({ onSubmit, isLoading = false }: OptimiserFormProps) {
  const [round, setRound] = useState(1);
  const [budget, setBudget] = useState(230);
  const [maxPerCountry, setMaxPerCountry] = useState(4);
  const [includeBench, setIncludeBench] = useState(true);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit({
      round,
      budget,
      max_per_country: maxPerCountry,
      include_bench: includeBench,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="card">
      <h2 className="text-xl font-bold mb-4">Optimiser Settings</h2>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
        <div>
          <label htmlFor="round" className="label">
            Round
          </label>
          <select
            id="round"
            className="input"
            value={round}
            onChange={(e) => setRound(parseInt(e.target.value))}
          >
            {[1, 2, 3, 4, 5].map((r) => (
              <option key={r} value={r}>
                Round {r}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="budget" className="label">
            Budget
          </label>
          <input
            id="budget"
            type="number"
            className="input"
            value={budget}
            onChange={(e) => setBudget(parseFloat(e.target.value))}
            min={0}
            max={300}
            step={0.5}
          />
        </div>

        <div>
          <label htmlFor="maxPerCountry" className="label">
            Max per Country
          </label>
          <input
            id="maxPerCountry"
            type="number"
            className="input"
            value={maxPerCountry}
            onChange={(e) => setMaxPerCountry(parseInt(e.target.value))}
            min={1}
            max={15}
          />
        </div>

        <div className="flex items-end">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includeBench}
              onChange={(e) => setIncludeBench(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm">Include Bench</span>
          </label>
        </div>
      </div>

      <button
        type="submit"
        className="btn-primary w-full"
        disabled={isLoading}
      >
        {isLoading ? 'Generating...' : 'Generate Optimal Team'}
      </button>
    </form>
  );
}
