import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { projectionsApi } from '../api/client';
import { useCurrentRound } from '../hooks/useMatches';
import { ProjectionsTable } from '../components/stats/ProjectionsTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

const COUNTRIES = ['Ireland', 'England', 'France', 'Wales', 'Scotland', 'Italy'];
const POSITIONS = [
  { value: 'prop', label: 'Prop' },
  { value: 'hooker', label: 'Hooker' },
  { value: 'second_row', label: 'Lock' },
  { value: 'back_row', label: 'Back Row' },
  { value: 'scrum_half', label: 'Scrum Half' },
  { value: 'out_half', label: 'Fly Half' },
  { value: 'centre', label: 'Centre' },
  { value: 'back_3', label: 'Back 3' },
];

const ROUNDS = [1, 2, 3, 4, 5];

interface Filters {
  country?: string;
  position?: string;
}

export default function PlayerProjections() {
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const [roundOverride, setRoundOverride] = useState<number | null>(null);
  const [filters, setFilters] = useState<Filters>({});

  const season = currentRound?.season ?? 2026;
  const round = roundOverride ?? currentRound?.round ?? 1;

  const { data: projections, isLoading, error } = useQuery({
    queryKey: ['players', 'projections', season, round, filters],
    queryFn: () => projectionsApi.getProjections({
      ...filters,
      season,
      game_round: round,
    }),
    enabled: season > 0 && round > 0,
  });

  if (error) {
    return (
      <div className="text-center py-12 text-red-500">
        Error loading projections. Make sure the backend is running.
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800">Player Projections</h1>
      <p className="text-sm text-slate-400 mt-1 mb-6">
        Predicted stats and value ratings based on 2026 per-round performance data. Rows highlighted by value tier (Pts/Star).
      </p>

      {/* Filters */}
      <div className="card mb-6">
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-4">
          <div>
            <label className="label">Round</label>
            <select
              className="input w-full"
              value={round}
              onChange={(e) => setRoundOverride(Number(e.target.value))}
              disabled={roundLoading}
            >
              {ROUNDS.map((r) => (
                <option key={r} value={r}>
                  Round {r}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Country</label>
            <select
              className="input w-full"
              value={filters.country || ''}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  country: e.target.value || undefined,
                }))
              }
            >
              <option value="">All Countries</option>
              {COUNTRIES.map((country) => (
                <option key={country} value={country}>
                  {country}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label">Position</label>
            <select
              className="input w-full"
              value={filters.position || ''}
              onChange={(e) =>
                setFilters((prev) => ({
                  ...prev,
                  position: e.target.value || undefined,
                }))
              }
            >
              <option value="">All Positions</option>
              {POSITIONS.map((pos) => (
                <option key={pos.value} value={pos.value}>
                  {pos.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              className="btn-secondary w-full"
              onClick={() => {
                setFilters({});
                setRoundOverride(null);
              }}
            >
              Clear Filters
            </button>
          </div>

          <div className="flex items-end">
            <span className="text-sm text-slate-400">
              {projections?.length || 0} players
            </span>
          </div>
        </div>
      </div>

      {/* Help text */}
      <div className="mb-4 text-sm text-slate-400">
        Click column group headers to expand/collapse. Click column headers to sort.
      </div>

      {isLoading || roundLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <ProjectionsTable data={projections || []} />
      )}
    </div>
  );
}
