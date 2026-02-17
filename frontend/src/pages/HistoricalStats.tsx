import { useState } from 'react';
import {
  useHistoricalSixNationsStats,
  useHistoricalClubStats,
  useHistoricalLeagues,
  useHistoricalSeasons,
  useHistoricalPositions,
  useStatsCountries,
} from '../hooks/useStats';
import { HistoricalStatsTable } from '../components/stats/HistoricalStatsTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';

type StatsType = 'six-nations' | 'club';

const POSITION_LABELS: Record<string, string> = {
  back_row: 'Back Row',
  back_3: 'Back Three',
  second_row: 'Second Row',
  centre: 'Centre',
  scrum_half: 'Scrum Half',
  out_half: 'Fly Half',
  hooker: 'Hooker',
  prop: 'Prop',
};

interface Filters {
  country?: string;
  position?: string;
  season?: number;
  league?: string;
}

export default function HistoricalStats() {
  const [statsType, setStatsType] = useState<StatsType>('six-nations');
  const [filters, setFilters] = useState<Filters>({});

  const { data: countries } = useStatsCountries();
  const { data: positions } = useHistoricalPositions();
  const { data: leagues } = useHistoricalLeagues();
  const { data: seasons } = useHistoricalSeasons();

  const sixNationsParams = {
    country: filters.country,
    position: filters.position,
    season: filters.season,
  };

  const clubParams = {
    country: filters.country,
    position: filters.position,
    league: filters.league,
  };

  const {
    data: sixNationsStats,
    isLoading: sixNationsLoading,
    error: sixNationsError,
  } = useHistoricalSixNationsStats(statsType === 'six-nations' ? sixNationsParams : {});

  const {
    data: clubStats,
    isLoading: clubLoading,
    error: clubError,
  } = useHistoricalClubStats(statsType === 'club' ? clubParams : {});

  const isLoading = statsType === 'six-nations' ? sixNationsLoading : clubLoading;
  const error = statsType === 'six-nations' ? sixNationsError : clubError;
  const stats = statsType === 'six-nations' ? sixNationsStats : clubStats;

  if (error) {
    return (
      <div className="text-center py-12 text-red-500">
        Error loading historical stats. Make sure the database has been populated.
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800 mb-6">Historical Stats</h1>

      {/* Stats Type Toggle */}
      <div className="card mb-6">
        <div className="flex flex-wrap gap-4 items-center">
          <div className="flex gap-0.5 bg-slate-100 rounded-lg p-0.5">
            <button
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                statsType === 'six-nations'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
              onClick={() => {
                setStatsType('six-nations');
                setFilters((prev) => ({ ...prev, league: undefined }));
              }}
            >
              Six Nations
            </button>
            <button
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
                statsType === 'club'
                  ? 'bg-white text-primary-700 shadow-sm'
                  : 'text-slate-500 hover:text-slate-700'
              }`}
              onClick={() => {
                setStatsType('club');
                setFilters((prev) => ({ ...prev, season: undefined }));
              }}
            >
              Club
            </button>
          </div>

          <div className="h-6 w-px bg-slate-200" />

          {/* Filters */}
          <div className="flex flex-wrap gap-4 items-end">
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
                    {POSITION_LABELS[position] || position}
                  </option>
                ))}
              </select>
            </div>

            {statsType === 'six-nations' && (
              <div>
                <label className="label">Season</label>
                <select
                  className="input w-full"
                  value={filters.season || ''}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      season: e.target.value ? parseInt(e.target.value) : undefined,
                    }))
                  }
                >
                  <option value="">All Seasons</option>
                  {seasons?.map((season) => (
                    <option key={season} value={season}>
                      {season}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {statsType === 'club' && (
              <div>
                <label className="label">League</label>
                <select
                  className="input w-full"
                  value={filters.league || ''}
                  onChange={(e) =>
                    setFilters((prev) => ({
                      ...prev,
                      league: e.target.value || undefined,
                    }))
                  }
                >
                  <option value="">All Leagues</option>
                  {leagues?.map((league) => (
                    <option key={league} value={league}>
                      {league}
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              className="btn-secondary"
              onClick={() => setFilters({})}
            >
              Clear Filters
            </button>

            <span className="text-sm text-slate-400">
              {stats?.length || 0} records
            </span>
          </div>
        </div>
      </div>

      {/* Help text */}
      <div className="mb-4 text-sm text-slate-400">
        Click column group headers to expand/collapse. Click column headers to sort.
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <HistoricalStatsTable data={stats || []} type={statsType} />
      )}
    </div>
  );
}
