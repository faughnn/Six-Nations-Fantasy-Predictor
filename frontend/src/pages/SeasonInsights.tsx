import { useState, useMemo, useEffect } from 'react';
import { useSeasonSummary } from '../hooks/useStats';
import { useCurrentRound } from '../hooks/useMatches';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CountryFlag } from '../components/common/CountryFlag';
import { Tooltip } from '../components/common/Tooltip';
import type { Country, Position } from '../types';
import type { SeasonSummaryPlayer } from '../api/client';

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

type SortKey = keyof SeasonSummaryPlayer | 'name' | 'country' | 'position';
type SortDir = 'asc' | 'desc';

const COUNTRIES: Country[] = ['Ireland', 'England', 'France', 'Wales', 'Scotland', 'Italy'];
const POSITIONS: Position[] = ['prop', 'hooker', 'second_row', 'back_row', 'scrum_half', 'out_half', 'centre', 'back_3'];

const STAT_COLS: { key: SortKey; header: string; tooltip: string; format?: (v: number) => string }[] = [
  { key: 'games_played', header: 'GP', tooltip: 'Games played' },
  { key: 'price', header: 'Price', tooltip: 'Current price (stars)', format: (v) => v.toFixed(1) },
  { key: 'avg_points', header: 'Avg Pts', tooltip: 'Average fantasy points per game' },
  { key: 'total_points', header: 'Tot Pts', tooltip: 'Total fantasy points across all rounds' },
  { key: 'avg_minutes', header: 'Avg Min', tooltip: 'Average minutes per game' },
  { key: 'points_per_minute', header: 'Pts/Min', tooltip: 'Fantasy points per minute played', format: (v) => v.toFixed(2) },
  { key: 'avg_tries', header: 'Avg T', tooltip: 'Average tries per game' },
  { key: 'avg_tackles', header: 'Avg Ta', tooltip: 'Average tackles per game' },
  { key: 'avg_metres', header: 'Avg MC', tooltip: 'Average metres carried per game' },
  { key: 'avg_defenders_beaten', header: 'Avg DB', tooltip: 'Average defenders beaten per game' },
  { key: 'avg_offloads', header: 'Avg OF', tooltip: 'Average offloads per game' },
  { key: 'total_tries', header: 'Tries', tooltip: 'Total tries scored' },
  { key: 'total_conversions', header: 'Cons', tooltip: 'Total conversions' },
  { key: 'total_penalties_kicked', header: 'Pens', tooltip: 'Total penalties kicked' },
  { key: 'potm_count', header: 'POTM', tooltip: 'Player of the Match awards' },
  { key: 'total_penalties_conceded', header: 'CPen', tooltip: 'Total penalties conceded' },
];

const DESC_BY_DEFAULT = new Set([
  'price', 'avg_points', 'total_points', 'avg_minutes', 'points_per_minute', 'avg_tries',
  'avg_tackles', 'avg_metres', 'avg_defenders_beaten', 'avg_offloads',
  'total_tries', 'total_conversions', 'total_penalties_kicked', 'potm_count', 'games_played',
]);

const STORAGE_KEY = 'seasonInsights:excludedCountries';
const STORAGE_KEY_POS = 'seasonInsights:excludedPositions';
const STORAGE_KEY_GAMES = 'seasonInsights:excludedGames';

function readStoredSet<T extends string>(key: string): Set<T> {
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) return new Set(JSON.parse(raw));
  } catch {}
  return new Set();
}

const GAME_COUNTS = [1, 2, 3, 4] as const;

export default function SeasonInsights() {
  const { data: currentRound } = useCurrentRound();
  const nextRound = currentRound?.round ?? 5;
  const { data, isLoading } = useSeasonSummary({ next_round: nextRound });

  const [excludedCountries, setExcludedCountries] = useState<Set<Country>>(() => readStoredSet<Country>(STORAGE_KEY));
  const [excludedPositions, setExcludedPositions] = useState<Set<Position>>(() => readStoredSet<Position>(STORAGE_KEY_POS));
  const [availabilityFilter, setAvailabilityFilter] = useState<Availability | 'all'>('all');
  const [sortKey, setSortKey] = useState<SortKey>('avg_points');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [excludedGames, setExcludedGames] = useState<Set<number>>(() => readStoredSet<string>(STORAGE_KEY_GAMES).size > 0 ? new Set([...readStoredSet<string>(STORAGE_KEY_GAMES)].map(Number)) : new Set());

  useEffect(() => { sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...excludedCountries])); }, [excludedCountries]);
  useEffect(() => { sessionStorage.setItem(STORAGE_KEY_POS, JSON.stringify([...excludedPositions])); }, [excludedPositions]);
  useEffect(() => { sessionStorage.setItem(STORAGE_KEY_GAMES, JSON.stringify([...excludedGames])); }, [excludedGames]);

  const toggleCountry = (c: Country) => {
    setExcludedCountries(prev => { const n = new Set(prev); n.has(c) ? n.delete(c) : n.add(c); return n; });
  };
  const soloCountry = (c: Country) => {
    if (excludedCountries.size === COUNTRIES.length - 1 && !excludedCountries.has(c)) setExcludedCountries(new Set());
    else setExcludedCountries(new Set(COUNTRIES.filter(x => x !== c)));
  };
  const togglePosition = (p: Position) => {
    setExcludedPositions(prev => { const n = new Set(prev); n.has(p) ? n.delete(p) : n.add(p); return n; });
  };
  const soloPosition = (p: Position) => {
    if (excludedPositions.size === POSITIONS.length - 1 && !excludedPositions.has(p)) setExcludedPositions(new Set());
    else setExcludedPositions(new Set(POSITIONS.filter(x => x !== p)));
  };
  const toggleGames = (g: number) => {
    setExcludedGames(prev => { const n = new Set(prev); n.has(g) ? n.delete(g) : n.add(g); return n; });
  };
  const soloGames = (g: number) => {
    if (excludedGames.size === GAME_COUNTS.length - 1 && !excludedGames.has(g)) setExcludedGames(new Set());
    else setExcludedGames(new Set(GAME_COUNTS.filter(x => x !== g)));
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortKey(key); setSortDir(DESC_BY_DEFAULT.has(key) ? 'desc' : 'asc'); }
  };

  const filtered = useMemo(() => {
    if (!data) return [];
    let list = [...data.players];
    if (excludedCountries.size > 0) list = list.filter(p => !excludedCountries.has(p.country as Country));
    if (excludedPositions.size > 0) list = list.filter(p => !excludedPositions.has(p.position as Position));
    if (excludedGames.size > 0) list = list.filter(p => !excludedGames.has(p.games_played));
    if (availabilityFilter !== 'all') list = list.filter(p => p.availability === availabilityFilter);

    list.sort((a, b) => {
      const aVal = a[sortKey as keyof SeasonSummaryPlayer];
      const bVal = b[sortKey as keyof SeasonSummaryPlayer];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      return sortDir === 'asc' ? String(aVal).localeCompare(String(bVal)) : String(bVal).localeCompare(String(aVal));
    });
    return list;
  }, [data, excludedCountries, excludedPositions, sortKey, sortDir, excludedGames, availabilityFilter]);

  // Position averages computed from the filtered player list (respects country, position, min games filters)
  const positionAverages = useMemo(() => {
    if (!filtered.length) return [];
    const byPos: Record<string, number[]> = {};
    for (const p of filtered) {
      if (!p.position || p.avg_minutes === 0) continue; // skip players with 0 minutes
      if (!byPos[p.position]) byPos[p.position] = [];
      byPos[p.position].push(p.avg_points);
    }
    return Object.entries(byPos)
      .map(([position, avgs]) => ({
        position,
        player_count: avgs.length,
        avg_points: Math.round(avgs.reduce((a, b) => a + b, 0) / avgs.length * 10) / 10,
        max_avg_points: Math.round(Math.max(...avgs) * 10) / 10,
        min_avg_points: Math.round(Math.min(...avgs) * 10) / 10,
      }))
      .sort((a, b) => b.avg_points - a.avg_points);
  }, [filtered]);

  const SortHeader = ({ label, field, tooltip: tip }: { label: string; field: SortKey; tooltip?: string }) => (
    <th
      className="pb-2 cursor-pointer select-none hover:text-stone-700 transition-colors whitespace-nowrap"
      onClick={() => handleSort(field)}
    >
      {tip ? <Tooltip text={tip}>{label}</Tooltip> : label}
      {sortKey === field && (
        <span className="ml-0.5 text-[#b91c1c]">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
      )}
    </th>
  );

  return (
    <div className="space-y-4">
      <div>
        <div className="masthead">
          <h1 className="masthead-title">Season <span className="italic" style={{ color: '#b91c1c' }}>Insights</span></h1>
          <p className="masthead-subtitle">Aggregated Performance Across All Rounds</p>
        </div>
        <div className="edition-bar">
          <span>
            Rounds {data?.rounds_included?.join(', ') || '...'} — 2026 Six Nations
          </span>
        </div>
      </div>

      {/* Position averages cards */}
      {positionAverages.length > 0 && (
        <div>
          <h2 className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mb-2">Average Points by Position</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {positionAverages
              .sort((a, b) => b.avg_points - a.avg_points)
              .map(pa => (
                <div
                  key={pa.position}
                  className="border border-stone-300 p-3 bg-white/50"
                >
                  <div className="text-[10px] text-stone-400 uppercase tracking-wider font-bold">
                    {pa.position.replace(/_/g, ' ')}
                  </div>
                  <div className="text-xl font-bold text-[#b91c1c] font-mono tabular-nums mt-0.5">
                    {pa.avg_points}
                  </div>
                  <div className="text-[10px] text-stone-400 mt-0.5">
                    {pa.player_count} players · {pa.min_avg_points}–{pa.max_avg_points}
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

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
              {p.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mr-1">Games</span>
          {GAME_COUNTS.map(g => (
            <button
              key={g}
              onClick={() => toggleGames(g)}
              onContextMenu={(e) => { e.preventDefault(); soloGames(g); }}
              className={`px-2.5 py-1 text-xs font-medium transition-colors ${
                excludedGames.has(g)
                  ? 'bg-transparent text-stone-400 border border-stone-300 line-through'
                  : 'bg-stone-900 text-white border border-stone-900'
              }`}
            >
              {g} {g === 1 ? 'game' : 'games'}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-stone-400 uppercase tracking-[2px] font-bold mr-1">Rd {nextRound} Status</span>
          {AVAILABILITY_OPTIONS.map(opt => (
            <button
              key={opt.value}
              onClick={() => setAvailabilityFilter(opt.value)}
              className={`px-2.5 py-1 text-xs font-medium transition-colors flex items-center gap-1 ${
                availabilityFilter === opt.value
                  ? 'bg-stone-900 text-white border border-stone-900'
                  : 'bg-transparent text-stone-400 border border-stone-300 hover:text-stone-700'
              }`}
            >
              {opt.value !== 'all' && (
                <span className={`inline-block w-2 h-2 rounded-full ${AVAILABILITY_INDICATOR[opt.value].dot}`} />
              )}
              {opt.label}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm text-stone-400">
            {filtered.length} player{filtered.length !== 1 ? 's' : ''}
          </span>
          <span className="text-[10px] text-stone-300 italic">Click to exclude · Right-click to solo</span>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : filtered.length > 0 ? (
        <div className="border-t-2 border-stone-900 overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="text-left text-stone-400 text-[10px] uppercase tracking-[1.2px] font-bold">
                <th className="pb-2 pl-3 pr-1 sticky left-0 bg-[#faf8f4] z-10">#</th>
                <SortHeader label="Player" field="name" />
                <SortHeader label="Country" field="country" tooltip="National team" />
                <SortHeader label="Pos" field="position" tooltip="Fantasy position" />
                {STAT_COLS.map(col => (
                  <th
                    key={col.key}
                    className="pb-2 text-right cursor-pointer select-none hover:text-stone-700 transition-colors whitespace-nowrap px-1.5"
                    onClick={() => handleSort(col.key)}
                  >
                    <Tooltip text={col.tooltip}>{col.header}</Tooltip>
                    {sortKey === col.key && (
                      <span className="ml-0.5 text-[#b91c1c]">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
                    )}
                  </th>
                ))}
                <th className="pb-2 text-right whitespace-nowrap px-1.5">
                  <Tooltip text="Rounds played (which rounds)">Rnds</Tooltip>
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, idx) => (
                <tr key={p.player_id} className="border-b border-dotted border-stone-300 hover:bg-[#f5f0e8] transition-colors">
                  <td className="py-1.5 pl-3 pr-1 text-xs text-stone-300 tabular-nums font-mono sticky left-0 bg-[#faf8f4] z-10">{idx + 1}</td>
                  <td className="py-1.5 pr-2">
                    <div className="flex items-center gap-1.5">
                      <CountryFlag country={p.country} size="sm" />
                      {p.availability && AVAILABILITY_INDICATOR[p.availability] && (
                        <span
                          className={`inline-block w-2 h-2 rounded-full flex-shrink-0 ${AVAILABILITY_INDICATOR[p.availability].dot}`}
                          title={AVAILABILITY_INDICATOR[p.availability].label}
                        />
                      )}
                      <span className="font-medium text-stone-800">{p.name}</span>
                    </div>
                  </td>
                  <td className="py-1.5 text-sm text-stone-500">{p.country}</td>
                  <td className="py-1.5 text-sm text-stone-500 whitespace-nowrap">{p.position ? p.position.replace(/_/g, ' ') : ''}</td>
                  {STAT_COLS.map(col => {
                    const val = p[col.key as keyof SeasonSummaryPlayer] as number | null;
                    const isAvgPts = col.key === 'avg_points';
                    const isTotPts = col.key === 'total_points';
                    const isGP = col.key === 'games_played';
                    const isPotm = col.key === 'potm_count';
                    const isPrice = col.key === 'price';
                    const formatted = val == null ? '-' : col.format ? col.format(val) : (typeof val === 'number' && !Number.isInteger(val) ? val.toFixed(1) : val);
                    return (
                      <td
                        key={col.key}
                        className={`py-1.5 text-sm text-right tabular-nums font-mono px-1.5 ${
                          isAvgPts ? 'font-bold text-[#b91c1c]' :
                          isTotPts ? 'font-semibold text-stone-800' :
                          isGP ? 'font-semibold text-stone-600' :
                          isPrice && val ? 'text-stone-600' :
                          isPotm && val && val > 0 ? 'text-amber-700 font-medium' :
                          val && val > 0 ? 'text-stone-700' : 'text-stone-300'
                        }`}
                      >
                        {val == null || val === 0 ? '-' : formatted}
                      </td>
                    );
                  })}
                  <td className="py-1.5 text-xs text-right text-stone-400 font-mono px-1.5">
                    {p.rounds_played.join(',')}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-center text-stone-400 py-8 border-t-2 border-stone-900">
          No data available
        </div>
      )}
    </div>
  );
}
