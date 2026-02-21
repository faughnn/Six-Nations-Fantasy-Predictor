import { useState } from 'react';
import { useAllStats, useStatsCountries, useStatsPositions } from '../hooks/useStats';
import { StatsTable } from '../components/stats/StatsTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

interface Filters {
  country?: string;
  position?: string;
}

export default function PlayersAllStats() {
  const [filters, setFilters] = useState<Filters>({});

  const { data: stats, isLoading, error } = useAllStats(filters);
  const { data: countries } = useStatsCountries();
  const { data: positions } = useStatsPositions();

  if (error) {
    return (
      <div className="text-center py-12 text-red-800">
        Error loading stats. Make sure the Excel file is in place.
      </div>
    );
  }

  return (
    <div>
      <div className="masthead">
        <h1 className="masthead-title">Player <span className="italic" style={{ color: '#b91c1c' }}>Archive</span></h1>
        <p className="masthead-subtitle">2025 Fantasy Six Nations</p>
      </div>

      {/* Filters */}
      <div className="border-t-2 border-stone-900 border-b border-stone-300 py-3 px-4 mb-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
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
              {countries?.map((country) => (
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
              {positions?.map((position) => (
                <option key={position} value={position}>
                  {position}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <button
              className="btn-secondary w-full"
              onClick={() => setFilters({})}
            >
              Clear Filters
            </button>
          </div>

          <div className="flex items-end">
            <span className="text-sm text-stone-400">
              {stats?.length || 0} players
            </span>
          </div>
        </div>
      </div>

      {/* Help text */}
      <div className="mb-4 text-xs text-stone-400 uppercase tracking-wider font-semibold">
        Click column group headers to expand/collapse. Click column headers to sort.
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <StatsTable data={stats || []} />
      )}
    </div>
  );
}
