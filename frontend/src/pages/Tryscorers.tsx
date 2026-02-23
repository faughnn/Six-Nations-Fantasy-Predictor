import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { matchesApi } from '../api/client';
import { useCurrentRound, useRoundScrapeStatus } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CountryFlag } from '../components/common/CountryFlag';
import { Tooltip } from '../components/common/Tooltip';
import type { Country, Position } from '../types';

type SortKey = 'name' | 'country' | 'fantasy_position' | 'match' | 'anytime_try_odds' | 'implied_prob' | 'expected_try_points' | 'price' | 'ownership_pct' | 'exp_pts_per_star';
type SortDir = 'asc' | 'desc';

type Availability = 'starting' | 'substitute' | 'not_playing';

const AVAILABILITY_INDICATOR: Record<Availability, { dot: string; label: string }> = {
  starting: { dot: 'bg-green-700', label: 'XV' },
  substitute: { dot: 'bg-amber-600', label: 'SUB' },
  not_playing: { dot: 'bg-stone-300', label: 'Out' },
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

function timeAgo(iso: string | null): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  const month = d.toLocaleString('en-GB', { month: 'short' });
  const day = d.getDate();
  const hours = d.getHours().toString().padStart(2, '0');
  const minutes = d.getMinutes().toString().padStart(2, '0');
  return `${month} ${day}, ${hours}:${minutes}`;
}

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

  const { data: scrapeStatus } = useRoundScrapeStatus(season, round);

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

  const DESC_BY_DEFAULT: SortKey[] = ['expected_try_points', 'implied_prob', 'exp_pts_per_star', 'ownership_pct'];

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
    if (excludedCountries.size > 0) list = list.filter(p => !excludedCountries.has(p.country as Country));
    if (excludedPositions.size > 0) list = list.filter(p => !excludedPositions.has(p.fantasy_position as Position));
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

  const SortHeader = ({ label, field, tooltip }: { label: string; field: SortKey; tooltip?: string }) => (
    <th
      className="pb-2 cursor-pointer select-none hover:text-stone-700 transition-colors"
      onClick={() => handleSort(field)}
    >
      {tooltip ? <Tooltip text={tooltip}>{label}</Tooltip> : label}
      {sortKey === field && (
        <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>
      )}
    </th>
  );

  return (
    <div className="space-y-4">
      <div>
        <div className="masthead">
          <h1 className="masthead-title">Player <span className="italic" style={{ color: '#b91c1c' }}>Analysis</span></h1>
          <p className="masthead-subtitle">Odds, Value & Ownership</p>
        </div>
        <div className="edition-bar">
          <span>Round {round} — {season} Six Nations</span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setRoundOverride(Math.max(1, round - 1))}
              disabled={round <= 1}
              className="w-6 h-6 flex items-center justify-center border border-stone-300 text-stone-400 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed text-xs font-bold transition-colors"
            >
              −
            </button>
            <span className="font-mono text-sm text-stone-800 w-6 text-center tabular-nums">{round}</span>
            <button
              onClick={() => setRoundOverride(Math.min(5, round + 1))}
              disabled={round >= 5}
              className="w-6 h-6 flex items-center justify-center border border-stone-300 text-stone-400 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed text-xs font-bold transition-colors"
            >
              +
            </button>
          </div>
        </div>
      </div>

      {/* Freshness & warnings */}
      {scrapeStatus && (() => {
        const enriched = scrapeStatus.enriched_matches ?? [];
        const tsScrapedAts = enriched
          .map(m => m.try_scorer.scraped_at)
          .filter((v): v is string => v != null);
        const latest = tsScrapedAts.length > 0
          ? tsScrapedAts.reduce((a, b) => (a > b ? a : b))
          : null;
        const hasPreSquadWarning = enriched.some(m => m.try_scorer.status === 'warning');
        return (
          <div className="space-y-1.5">
            {latest && (
              <p className="text-xs text-stone-400">
                Odds retrieved: {formatDate(latest)} ({timeAgo(latest)})
              </p>
            )}
            {hasPreSquadWarning && (
              <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs px-3 py-2">
                Some odds were scraped before squad announcements. Players may have changed.
              </div>
            )}
          </div>
        );
      })()}

      {/* Filters */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mr-1">Country</span>
          {COUNTRIES.map(c => (
            <button
              key={c}
              onClick={() => toggleCountry(c)}
              onContextMenu={(e) => { e.preventDefault(); soloCountry(c); }}
              className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                excludedCountries.has(c)
                  ? 'bg-transparent text-stone-400 border border-stone-300 line-through'
                  : 'bg-stone-900 text-white border border-stone-900'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mr-1">Position</span>
          {POSITIONS.map(p => (
            <button
              key={p}
              onClick={() => togglePosition(p)}
              onContextMenu={(e) => { e.preventDefault(); soloPosition(p); }}
              className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                excludedPositions.has(p)
                  ? 'bg-transparent text-stone-400 border border-stone-300 line-through'
                  : 'bg-stone-900 text-white border border-stone-900'
              }`}
            >
              {p.replace('_', ' ')}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mr-1">Status</span>
          {AVAILABILITY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setAvailFilter(opt.value)}
              className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                availFilter === opt.value
                  ? 'bg-stone-900 text-white border border-stone-900'
                  : 'bg-transparent text-stone-400 border border-stone-300'
              }`}
            >
              {opt.value !== 'all' && (
                <span className={`inline-block w-2 h-2 rounded-full mr-1 ${AVAILABILITY_INDICATOR[opt.value].dot}`} />
              )}
              {opt.label}
            </button>
          ))}
        </div>
        <span className="text-sm text-stone-400">
          {filtered.length} player{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      {filtered.length > 0 ? (
        <div className="border-t-2 border-stone-900 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-stone-400 text-[10px] uppercase tracking-[1.2px] font-bold">
                <SortHeader label="Player" field="name" />
                <SortHeader label="Country" field="country" tooltip="National team" />
                <SortHeader label="Position" field="fantasy_position" tooltip="Fantasy position category" />
                <SortHeader label="Match" field="match" tooltip="Upcoming fixture" />
                <th className="pb-2 text-right cursor-pointer select-none hover:text-stone-700" onClick={() => handleSort('anytime_try_odds')}>
                  <Tooltip text="Bookmaker anytime try scorer decimal odds">Odds</Tooltip>{sortKey === 'anytime_try_odds' && <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-stone-700" onClick={() => handleSort('implied_prob')}>
                  <Tooltip text="Implied probability of scoring a try (100 / odds)">Implied %</Tooltip>{sortKey === 'implied_prob' && <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-stone-700" onClick={() => handleSort('expected_try_points')}>
                  <Tooltip text="Expected fantasy points from try scoring alone">Exp Pts</Tooltip>{sortKey === 'expected_try_points' && <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-stone-700" onClick={() => handleSort('price')}>
                  <Tooltip text="Fantasy cost in stars">Price</Tooltip>{sortKey === 'price' && <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-stone-700" onClick={() => handleSort('ownership_pct')}>
                  <Tooltip text="% of fantasy players who own this player">Own%</Tooltip>{sortKey === 'ownership_pct' && <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
                <th className="pb-2 text-right cursor-pointer select-none hover:text-stone-700" onClick={() => handleSort('exp_pts_per_star')}>
                  <Tooltip text="Expected try points divided by price — higher is better value">Exp/Star</Tooltip>{sortKey === 'exp_pts_per_star' && <span className="ml-1 text-[#b91c1c]">{sortDir === 'asc' ? '↑' : '↓'}</span>}
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <tr key={p.player_id} className="border-b border-dotted border-stone-300 hover:bg-[#f5f0e8] transition-colors">
                  <td className="py-1.5">
                    <div className="flex items-center gap-1.5">
                      <CountryFlag country={p.country} size="sm" />
                      {p.availability && AVAILABILITY_INDICATOR[p.availability] && (
                        <span
                          className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${AVAILABILITY_INDICATOR[p.availability].dot}`}
                          title={AVAILABILITY_INDICATOR[p.availability].label}
                        />
                      )}
                      <span className="font-medium text-stone-800">
                        {p.name}
                      </span>
                    </div>
                  </td>
                  <td className="py-1.5 text-sm text-stone-500">{p.country}</td>
                  <td className="py-1.5 text-sm text-stone-500">{p.fantasy_position.replace('_', ' ')}</td>
                  <td className="py-1.5 text-sm text-stone-500">{p.match}</td>
                  <td className="py-1.5 text-sm text-right font-medium font-mono tabular-nums">{p.anytime_try_odds?.toFixed(2) ?? '-'}</td>
                  <td className="py-1.5 text-sm text-right font-semibold text-green-800 font-mono tabular-nums">
                    {p.implied_prob != null ? `${(p.implied_prob * 100).toFixed(0)}%` : '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right font-bold text-[#b91c1c] font-mono tabular-nums">
                    {p.expected_try_points?.toFixed(1) ?? '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right text-stone-500 font-mono tabular-nums">
                    {p.price?.toFixed(1) ?? '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right text-stone-500 font-mono tabular-nums">
                    {p.ownership_pct != null ? `${p.ownership_pct.toFixed(0)}%` : '-'}
                  </td>
                  <td className="py-1.5 text-sm text-right font-bold text-green-800 font-mono tabular-nums">
                    {p.exp_pts_per_star?.toFixed(2) ?? '-'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center text-stone-400 py-8 border-t-2 border-stone-900">
          No tryscorer odds available for this round yet
        </div>
      )}
    </div>
  );
}
