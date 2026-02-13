import { useState, useMemo, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { matchesApi } from '../api/client';
import { useCurrentRound } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CountryFlag } from '../components/common/CountryFlag';
import type { TryScorerDetail, Country, Position } from '../types';

type SortKey = 'name' | 'country' | 'fantasy_position' | 'match' | 'anytime_try_odds' | 'implied_prob' | 'expected_try_points' | 'price' | 'exp_pts_per_star';
type SortDir = 'asc' | 'desc';

type Availability = 'starting' | 'substitute' | 'not_playing';

const AVAILABILITY_INDICATOR: Record<Availability, { dot: string; label: string }> = {
  starting: { dot: 'bg-green-500', label: 'XV' },
  substitute: { dot: 'bg-amber-400', label: 'SUB' },
  not_playing: { dot: 'bg-gray-300', label: 'Out' },
};

const AVAILABILITY_OPTIONS: { value: Availability | 'all'; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'starting', label: 'Starting XV' },
  { value: 'substitute', label: 'Subs' },
  { value: 'not_playing', label: 'Not playing' },
];

const COUNTRIES: Country[] = ['Ireland', 'England', 'France', 'Wales', 'Scotland', 'Italy'];
const POSITIONS: Position[] = ['prop', 'hooker', 'second_row', 'back_row', 'scrum_half', 'out_half', 'centre', 'back_3'];

const STORAGE_KEY_COUNTRIES = 'tryscorers:excludedCountries';
const STORAGE_KEY_POSITIONS = 'tryscorers:excludedPositions';

function readStoredSet<T extends string>(key: string): Set<T> {
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) return new Set(JSON.parse(raw));
  } catch {}
  return new Set();
}

export default function Tryscorers() {
  const { data: currentRound, isLoading: roundLoading } = useCurrentRound();
  const [roundOverride, setRoundOverride] = useState<number | null>(null);
  const season = currentRound?.season ?? 0;
  const round = roundOverride ?? currentRound?.round ?? 0;

  const { data: tryscorers, isLoading: dataLoading } = useQuery({
    queryKey: ['tryscorers', season, round],
    queryFn: () => matchesApi.getTryScorers(season, round),
    enabled: season > 0 && round > 0,
  });

  const [excludedCountries, setExcludedCountries] = useState<Set<Country>>(
    () => readStoredSet<Country>(STORAGE_KEY_COUNTRIES)
  );
  const [excludedPositions, setExcludedPositions] = useState<Set<Position>>(
    () => readStoredSet<Position>(STORAGE_KEY_POSITIONS)
  );

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY_COUNTRIES, JSON.stringify([...excludedCountries]));
  }, [excludedCountries]);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY_POSITIONS, JSON.stringify([...excludedPositions]));
  }, [excludedPositions]);
  const [sortKey, setSortKey] = useState<SortKey>('exp_pts_per_star');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [availFilter, setAvailFilter] = useState<Availability | 'all'>('all');

  const toggleCountry = (c: Country) => {
    setExcludedCountries(prev => {
      const next = new Set(prev);
      next.has(c) ? next.delete(c) : next.add(c);
      return next;
    });
  };

  const togglePosition = (p: Position) => {
    setExcludedPositions(prev => {
      const next = new Set(prev);
      next.has(p) ? next.delete(p) : next.add(p);
      return next;
    });
  };

  const soloCountry = (c: Country) => {
    if (excludedCountries.size === COUNTRIES.length - 1 && !excludedCountries.has(c)) {
      setExcludedCountries(new Set());
    } else {
      setExcludedCountries(new Set(COUNTRIES.filter(x => x !== c)));
    }
  };

  const soloPosition = (p: Position) => {
    if (excludedPositions.size === POSITIONS.length - 1 && !excludedPositions.has(p)) {
      setExcludedPositions(new Set());
    } else {
      setExcludedPositions(new Set(POSITIONS.filter(x => x !== p)));
    }
  };

  const DESC_BY_DEFAULT: SortKey[] = ['expected_try_points', 'implied_prob', 'exp_pts_per_star'];

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(DESC_BY_DEFAULT.includes(key) ? 'desc' : 'asc');
    }
  };

  const filtered = useMemo(() => {
    if (!tryscorers) return [];
    let list = [...tryscorers];
    if (excludedCountries.size > 0) list = list.filter(p => !excludedCountries.has(p.country));
    if (excludedPositions.size > 0) list = list.filter(p => !excludedPositions.has(p.fantasy_position));
    if (availFilter !== 'all') list = list.filter(p => (p.availability ?? 'not_playing') === availFilter);

    list.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      // Push nulls to the bottom regardless of sort direction
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortDir === 'asc' ? aStr.localeCompare(bStr) : bStr.localeCompare(aStr);
    });

    return list;
  }, [tryscorers, excludedCountries, excludedPositions, availFilter, sortKey, sortDir]);

  if (roundLoading || dataLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  const SortHeader = ({ label, field }: { label: string; field: SortKey }) => (
    <th
      className="pb-2 cursor-pointer select-none hover:text-gray-700"
      onClick={() => handleSort(field)}
    >
      {label}
      {sortKey === field && (
        <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>
      )}
    </th>
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Anytime Try Scorers</h1>
        <div className="flex items-center gap-3 mt-1">
          <p className="text-gray-500">Round {round} — {season} Six Nations</p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setRoundOverride(Math.max(1, round - 1))}
              disabled={round <= 1}
              className="w-6 h-6 flex items-center justify-center rounded border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold"
            >
              −
            </button>
            <span className="text-sm text-gray-500 w-6 text-center">{round}</span>
            <button
              onClick={() => setRoundOverride(Math.min(5, round + 1))}
              disabled={round >= 5}
              className="w-6 h-6 flex items-center justify-center rounded border border-gray-300 text-gray-600 hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold"
            >
              +
            </button>
            {roundOverride !== null && (
              <button
                onClick={() => setRoundOverride(null)}
                className="ml-1 text-xs text-primary-600 hover:underline"
              >
                reset
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 uppercase font-medium mr-1">Country</span>
          {COUNTRIES.map(c => (
            <button
              key={c}
              onClick={() => toggleCountry(c)}
              onContextMenu={(e) => { e.preventDefault(); soloCountry(c); }}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                excludedCountries.has(c)
                  ? 'bg-gray-100 text-gray-400 border-gray-200 line-through'
                  : 'bg-primary-100 text-primary-700 border-primary-300'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 uppercase font-medium mr-1">Position</span>
          {POSITIONS.map(p => (
            <button
              key={p}
              onClick={() => togglePosition(p)}
              onContextMenu={(e) => { e.preventDefault(); soloPosition(p); }}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                excludedPositions.has(p)
                  ? 'bg-gray-100 text-gray-400 border-gray-200 line-through'
                  : 'bg-primary-100 text-primary-700 border-primary-300'
              }`}
            >
              {p.replace('_', ' ')}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 uppercase font-medium mr-1">Status</span>
          {AVAILABILITY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setAvailFilter(opt.value)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium border transition-colors ${
                availFilter === opt.value
                  ? 'bg-primary-100 text-primary-700 border-primary-300'
                  : 'bg-gray-100 text-gray-400 border-gray-200'
              }`}
            >
              {opt.value !== 'all' && (
                <span className={`inline-block w-2 h-2 rounded-full mr-1 ${AVAILABILITY_INDICATOR[opt.value].dot}`} />
              )}
              {opt.label}
            </button>
          ))}
        </div>
        <span className="text-sm text-gray-500">
          {filtered.length} player{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
        <div className="card overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-gray-500 text-xs uppercase">
                <SortHeader label="Player" field="name" />
                <SortHeader label="Country" field="country" />
                <SortHeader label="Position" field="fantasy_position" />
                <SortHeader label="Match" field="match" />
                <th className="pb-2 text-right cursor-pointer select-none hover:text-gray-700" onClick={() => handleSort('anytime_try_odds')}>
                  Odds{sortKey === 'anytime_try_odds' && <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-gray-700" onClick={() => handleSort('implied_prob')}>
                  Implied %{sortKey === 'implied_prob' && <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-gray-700" onClick={() => handleSort('expected_try_points')}>
                  Exp Pts{sortKey === 'expected_try_points' && <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-gray-700" onClick={() => handleSort('price')}>
                  Price{sortKey === 'price' && <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-gray-700" onClick={() => handleSort('exp_pts_per_star')}>
                  Exp/Star{sortKey === 'exp_pts_per_star' && <span className="ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.player_id} className="border-t hover:bg-gray-50">
                  <td className="py-1.5">
                    <div className="flex items-center gap-1.5">
                      <CountryFlag country={p.country} size="sm" />
                      {p.availability && AVAILABILITY_INDICATOR[p.availability] && (
                        <span
                          className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${AVAILABILITY_INDICATOR[p.availability].dot}`}
                          title={AVAILABILITY_INDICATOR[p.availability].label}
                        />
                      )}
                      <Link to={`/players/${p.player_id}`} className="font-medium hover:text-primary-600">
                        {p.name}
                      </Link>
                    </div>
                  </td>
                  <td className="py-1.5 text-sm text-gray-600">{p.country}</td>
                  <td className="py-1.5 text-sm text-gray-600">{p.fantasy_position.replace('_', ' ')}</td>
                  <td className="py-1.5 text-sm text-gray-600">{p.match}</td>
                  <td className="py-1.5 text-sm text-right font-medium">{p.anytime_try_odds?.toFixed(2) ?? '-'}</td>
                  <td className="py-1.5 text-sm text-right font-semibold text-green-600">
                    {p.implied_prob != null ? `${(p.implied_prob * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right font-bold text-primary-600">
                    {p.expected_try_points?.toFixed(1) ?? '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right text-gray-600">
                    {p.price?.toFixed(1) ?? '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right font-bold text-green-600">
                    {p.exp_pts_per_star?.toFixed(2) ?? '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card text-center text-gray-500 py-8">
          No tryscorer odds available for this round yet
        </div>
      )}
    </div>
  );
}
