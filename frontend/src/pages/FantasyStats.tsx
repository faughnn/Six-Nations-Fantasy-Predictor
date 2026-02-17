import { useState, useMemo, useEffect } from 'react';
import { useFantasyStats, useFantasyStatsMetadata, useFantasyStatsRounds } from '../hooks/useStats';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { CountryFlag } from '../components/common/CountryFlag';
import { Tooltip } from '../components/common/Tooltip';
import type { FantasyStatPlayer, Country, Position } from '../types';

type StatKey = keyof FantasyStatPlayer;
type SortDir = 'asc' | 'desc';

const COUNTRIES: Country[] = ['Ireland', 'England', 'France', 'Wales', 'Scotland', 'Italy'];
const POSITIONS: Position[] = ['prop', 'hooker', 'second_row', 'back_row', 'scrum_half', 'out_half', 'centre', 'back_3'];

const STAT_COLS: { key: StatKey; header: string; tooltip: string; group: string }[] = [
  { key: 'fantasy_points', header: 'Pts', tooltip: 'Fantasy points this round', group: 'pts' },
  { key: 'minutes_played', header: 'Min', tooltip: 'Minutes played', group: 'pts' },
  { key: 'player_of_match', header: 'POTM', tooltip: 'Player of the Match', group: 'pts' },
  { key: 'tries', header: 'T', tooltip: 'Tries scored', group: 'score' },
  { key: 'try_assists', header: 'As', tooltip: 'Try assists', group: 'score' },
  { key: 'conversions', header: 'C', tooltip: 'Conversions kicked', group: 'score' },
  { key: 'penalties_kicked', header: 'Pen', tooltip: 'Penalty goals kicked', group: 'score' },
  { key: 'drop_goals', header: 'DG', tooltip: 'Drop goals', group: 'score' },
  { key: 'tackles_made', header: 'Ta', tooltip: 'Tackles made', group: 'play' },
  { key: 'metres_carried', header: 'MC', tooltip: 'Metres carried', group: 'play' },
  { key: 'defenders_beaten', header: 'DB', tooltip: 'Defenders beaten', group: 'play' },
  { key: 'offloads', header: 'OF', tooltip: 'Offloads', group: 'play' },
  { key: 'fifty_22_kicks', header: '50-22', tooltip: 'Successful 50:22 kicks', group: 'set' },
  { key: 'lineout_steals', header: 'LS', tooltip: 'Lineout steals', group: 'set' },
  { key: 'breakdown_steals', header: 'BS', tooltip: 'Breakdown steals / turnovers won', group: 'set' },
  { key: 'kick_returns', header: 'KR', tooltip: 'Kick returns', group: 'set' },
  { key: 'scrums_won', header: 'SW', tooltip: 'Scrums won', group: 'set' },
  { key: 'penalties_conceded', header: 'CPen', tooltip: 'Penalties conceded', group: 'disc' },
  { key: 'yellow_cards', header: 'YC', tooltip: 'Yellow cards', group: 'disc' },
  { key: 'red_cards', header: 'RC', tooltip: 'Red cards', group: 'disc' },
];

const DESC_BY_DEFAULT: StatKey[] = ['fantasy_points', 'minutes_played', 'player_of_match', 'tries', 'try_assists', 'metres_carried', 'tackles_made', 'defenders_beaten', 'offloads'];

const STORAGE_KEY = 'fantasyStats:excludedCountries';
const STORAGE_KEY_POSITIONS = 'fantasyStats:excludedPositions';

function readStoredSet<T extends string>(key: string): Set<T> {
  try {
    const raw = sessionStorage.getItem(key);
    if (raw) return new Set(JSON.parse(raw));
  } catch {}
  return new Set();
}

export default function FantasyStats() {
  const { data: metadata } = useFantasyStatsMetadata();
  const { data: availableRounds } = useFantasyStatsRounds();

  const maxRound = availableRounds && availableRounds.length > 0
    ? Math.max(...availableRounds)
    : 0;

  const [round, setRound] = useState<number>(0);

  // Default to latest round once we know what rounds are available
  useEffect(() => {
    if (maxRound > 0 && round === 0) setRound(maxRound);
  }, [maxRound, round]);

  const { data: players, isLoading } = useFantasyStats({ game_round: round });

  const [excludedCountries, setExcludedCountries] = useState<Set<Country>>(
    () => readStoredSet<Country>(STORAGE_KEY)
  );
  const [excludedPositions, setExcludedPositions] = useState<Set<Position>>(
    () => readStoredSet<Position>(STORAGE_KEY_POSITIONS)
  );
  const [sortKey, setSortKey] = useState<StatKey>('fantasy_points');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify([...excludedCountries]));
  }, [excludedCountries]);

  useEffect(() => {
    sessionStorage.setItem(STORAGE_KEY_POSITIONS, JSON.stringify([...excludedPositions]));
  }, [excludedPositions]);

  const toggleCountry = (c: Country) => {
    setExcludedCountries(prev => {
      const next = new Set(prev);
      next.has(c) ? next.delete(c) : next.add(c);
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

  const togglePosition = (p: Position) => {
    setExcludedPositions(prev => {
      const next = new Set(prev);
      next.has(p) ? next.delete(p) : next.add(p);
      return next;
    });
  };

  const soloPosition = (p: Position) => {
    if (excludedPositions.size === POSITIONS.length - 1 && !excludedPositions.has(p)) {
      setExcludedPositions(new Set());
    } else {
      setExcludedPositions(new Set(POSITIONS.filter(x => x !== p)));
    }
  };

  const handleSort = (key: StatKey) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortKey(key);
      setSortDir(DESC_BY_DEFAULT.includes(key) ? 'desc' : 'asc');
    }
  };

  const filtered = useMemo(() => {
    if (!players) return [];
    let list = [...players];
    if (excludedCountries.size > 0) {
      list = list.filter(p => !excludedCountries.has(p.country as Country));
    }
    if (excludedPositions.size > 0) {
      list = list.filter(p => !excludedPositions.has(p.position as Position));
    }
    list.sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal == null && bVal == null) return 0;
      if (aVal == null) return 1;
      if (bVal == null) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDir === 'asc' ? aVal - bVal : bVal - aVal;
      }
      return sortDir === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });
    return list;
  }, [players, excludedCountries, excludedPositions, sortKey, sortDir]);

  const scrapedAt = metadata?.scraped_at
    ? new Date(metadata.scraped_at).toLocaleString()
    : null;

  const SortHeader = ({ label, field, tooltip: tip }: { label: string; field: StatKey; tooltip?: string }) => (
    <th
      className="pb-2 cursor-pointer select-none hover:text-slate-600 transition-colors whitespace-nowrap"
      onClick={() => handleSort(field)}
    >
      {tip ? <Tooltip text={tip}>{label}</Tooltip> : label}
      {sortKey === field && (
        <span className="ml-0.5 text-primary-500">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
      )}
    </th>
  );

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">2026 Fantasy Stats</h1>
        <p className="text-sm text-slate-400 mt-1 mb-2">
          Per-round player performance stats from the official Fantasy Six Nations game.
        </p>
        <div className="flex items-center gap-3 mt-1">
          <p className="text-slate-400">Round {round} — 2026 Six Nations</p>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setRound(Math.max(1, round - 1))}
              disabled={round <= 1}
              className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold transition-colors"
            >
              −
            </button>
            <span className="text-sm text-slate-500 w-6 text-center tabular-nums font-medium">{round}</span>
            <button
              onClick={() => setRound(Math.min(maxRound || 5, round + 1))}
              disabled={round >= (maxRound || 5)}
              className="w-7 h-7 flex items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 disabled:opacity-30 disabled:cursor-not-allowed text-sm font-bold transition-colors"
            >
              +
            </button>
          </div>
          {scrapedAt && (
            <span className="text-xs text-slate-300 ml-auto">Updated {scrapedAt}</span>
          )}
        </div>
      </div>

      {/* Filter chips */}
      <div className="space-y-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mr-1">Country</span>
          {COUNTRIES.map(c => (
            <button
              key={c}
              onClick={() => toggleCountry(c)}
              onContextMenu={(e) => { e.preventDefault(); soloCountry(c); }}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                excludedCountries.has(c)
                  ? 'bg-slate-50 text-slate-300 ring-1 ring-inset ring-slate-200 line-through'
                  : 'bg-primary-50 text-primary-700 ring-1 ring-inset ring-primary-200'
              }`}
            >
              {c}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold mr-1">Position</span>
          {POSITIONS.map(p => (
            <button
              key={p}
              onClick={() => togglePosition(p)}
              onContextMenu={(e) => { e.preventDefault(); soloPosition(p); }}
              className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                excludedPositions.has(p)
                  ? 'bg-slate-50 text-slate-300 ring-1 ring-inset ring-slate-200 line-through'
                  : 'bg-primary-50 text-primary-700 ring-1 ring-inset ring-primary-200'
              }`}
            >
              {p.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <span className="text-sm text-slate-400">
          {filtered.length} player{filtered.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : filtered.length > 0 ? (
        <div className="rounded-xl border border-slate-200 overflow-x-auto bg-white">
          <table className="w-full">
            <thead>
              <tr className="text-left text-slate-400 text-xs uppercase">
                <th className="pb-2 pl-3 pr-1 sticky left-0 bg-white z-10">#</th>
                <SortHeader label="Player" field="name" />
                <SortHeader label="Country" field="country" tooltip="National team" />
                <SortHeader label="Pos" field="position" tooltip="Fantasy position" />
                {STAT_COLS.map(col => (
                  <th
                    key={col.key}
                    className="pb-2 text-right cursor-pointer select-none hover:text-slate-600 transition-colors whitespace-nowrap px-1.5"
                    onClick={() => handleSort(col.key)}
                  >
                    <Tooltip text={col.tooltip}>{col.header}</Tooltip>
                    {sortKey === col.key && (
                      <span className="ml-0.5 text-primary-500">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
                    )}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((p, idx) => (
                <tr key={`${p.name}-${p.round}`} className="border-t border-slate-100 hover:bg-primary-50/30 transition-colors">
                  <td className="py-1.5 pl-3 pr-1 text-xs text-slate-300 tabular-nums sticky left-0 bg-white z-10">{idx + 1}</td>
                  <td className="py-1.5 pr-2">
                    <div className="flex items-center gap-1.5">
                      <CountryFlag country={p.country} size="sm" />
                      <span className="font-medium text-slate-700">{p.name}</span>
                    </div>
                  </td>
                  <td className="py-1.5 text-sm text-slate-500">{p.country}</td>
                  <td className="py-1.5 text-sm text-slate-500 whitespace-nowrap">{p.position ? p.position.replace(/_/g, ' ') : ''}</td>
                  {STAT_COLS.map(col => {
                    const val = p[col.key] as number;
                    const isPts = col.key === 'fantasy_points';
                    const isCard = col.key === 'yellow_cards' || col.key === 'red_cards';
                    return (
                      <td
                        key={col.key}
                        className={`py-1.5 text-sm text-right tabular-nums px-1.5 ${
                          isPts ? 'font-bold text-primary-600' :
                          isCard && val > 0 ? 'text-red-500 font-medium' :
                          val > 0 ? 'text-slate-700' : 'text-slate-300'
                        }`}
                      >
                        {val === 0 ? '-' : typeof val === 'number' && !Number.isInteger(val) ? val.toFixed(1) : val}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="card text-center text-slate-400 py-8">
          No stats available for Round {round}
        </div>
      )}
    </div>
  );
}
