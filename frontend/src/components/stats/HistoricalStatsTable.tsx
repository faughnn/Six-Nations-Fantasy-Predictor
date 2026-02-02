import { useState, useMemo } from 'react';
import type { HistoricalSixNationsStat, HistoricalClubStat } from '../../types';
import { cn } from '../../utils';
import { CountryFlag } from '../common/CountryFlag';

type StatRecord = HistoricalSixNationsStat | HistoricalClubStat;

interface ColumnDef<T> {
  key: keyof T | string;
  header: string;
  format?: (value: unknown, record: T) => string;
}

interface ColumnGroup<T> {
  id: string;
  label: string;
  columns: ColumnDef<T>[];
}

const SIX_NATIONS_COLUMN_GROUPS: ColumnGroup<HistoricalSixNationsStat>[] = [
  {
    id: 'match',
    label: 'Match Info',
    columns: [
      { key: 'season', header: 'Szn' },
      { key: 'round', header: 'Rd' },
      { key: 'match_date', header: 'Date', format: (v) => v ? String(v).slice(5) : '-' },
      { key: 'opponent', header: 'Opp' },
      { key: 'home_away', header: 'H/A' },
    ],
  },
  {
    id: 'participation',
    label: 'Participation',
    columns: [
      { key: 'started', header: 'Start', format: (v) => v ? 'Y' : 'N' },
      { key: 'minutes_played', header: 'Min' },
    ],
  },
  {
    id: 'attacking',
    label: 'Attacking',
    columns: [
      { key: 'tries', header: 'Try' },
      { key: 'try_assists', header: 'Ast' },
      { key: 'conversions', header: 'Con' },
      { key: 'penalties_kicked', header: 'PK' },
      { key: 'drop_goals', header: 'DG' },
      { key: 'defenders_beaten', header: 'Def B' },
      { key: 'metres_carried', header: 'Mtrs' },
      { key: 'clean_breaks', header: 'Brk' },
      { key: 'offloads', header: 'Off' },
      { key: 'fifty_22_kicks', header: '50-22' },
    ],
  },
  {
    id: 'defensive',
    label: 'Defensive',
    columns: [
      { key: 'tackles_made', header: 'Tck' },
      { key: 'tackles_missed', header: 'Miss' },
      { key: 'turnovers_won', header: 'TO' },
      { key: 'lineout_steals', header: 'LO St' },
      { key: 'scrums_won', header: 'Scr' },
    ],
  },
  {
    id: 'discipline',
    label: 'Discipline',
    columns: [
      { key: 'penalties_conceded', header: 'Pen' },
      { key: 'yellow_cards', header: 'YC' },
      { key: 'red_cards', header: 'RC' },
    ],
  },
  {
    id: 'awards',
    label: 'Awards',
    columns: [
      { key: 'player_of_match', header: 'POTM', format: (v) => v ? 'Y' : '-' },
      { key: 'fantasy_points', header: 'FPts', format: (v) => v !== null ? String(v) : '-' },
    ],
  },
];

const CLUB_COLUMN_GROUPS: ColumnGroup<HistoricalClubStat>[] = [
  {
    id: 'match',
    label: 'Match Info',
    columns: [
      { key: 'league', header: 'League' },
      { key: 'season', header: 'Szn' },
      { key: 'match_date', header: 'Date', format: (v) => v ? String(v).slice(5) : '-' },
      { key: 'opponent', header: 'Opp' },
      { key: 'home_away', header: 'H/A' },
    ],
  },
  {
    id: 'participation',
    label: 'Participation',
    columns: [
      { key: 'started', header: 'Start', format: (v) => v ? 'Y' : 'N' },
      { key: 'minutes_played', header: 'Min' },
    ],
  },
  {
    id: 'attacking',
    label: 'Attacking',
    columns: [
      { key: 'tries', header: 'Try' },
      { key: 'try_assists', header: 'Ast' },
      { key: 'conversions', header: 'Con' },
      { key: 'penalties_kicked', header: 'PK' },
      { key: 'drop_goals', header: 'DG' },
      { key: 'defenders_beaten', header: 'Def B' },
      { key: 'metres_carried', header: 'Mtrs' },
      { key: 'clean_breaks', header: 'Brk' },
      { key: 'offloads', header: 'Off' },
    ],
  },
  {
    id: 'defensive',
    label: 'Defensive',
    columns: [
      { key: 'tackles_made', header: 'Tck' },
      { key: 'tackles_missed', header: 'Miss' },
      { key: 'turnovers_won', header: 'TO' },
      { key: 'lineout_steals', header: 'LO St' },
      { key: 'scrums_won', header: 'Scr' },
    ],
  },
  {
    id: 'discipline',
    label: 'Discipline',
    columns: [
      { key: 'penalties_conceded', header: 'Pen' },
      { key: 'yellow_cards', header: 'YC' },
      { key: 'red_cards', header: 'RC' },
    ],
  },
];

interface HistoricalStatsTableProps {
  data: StatRecord[];
  type: 'six-nations' | 'club';
}

export function HistoricalStatsTable({ data, type }: HistoricalStatsTableProps) {
  const columnGroups = type === 'six-nations'
    ? SIX_NATIONS_COLUMN_GROUPS as ColumnGroup<StatRecord>[]
    : CLUB_COLUMN_GROUPS as ColumnGroup<StatRecord>[];

  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(columnGroups.map(g => g.id))
  );
  const [sortKey, setSortKey] = useState<string | null>('match_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      return next;
    });
  };

  const sortedData = useMemo(() => {
    if (!sortKey) return data;

    return [...data].sort((a, b) => {
      const aVal = (a as Record<string, unknown>)[sortKey];
      const bVal = (b as Record<string, unknown>)[sortKey];

      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      const aStr = String(aVal);
      const bStr = String(bVal);
      return sortDirection === 'asc'
        ? aStr.localeCompare(bStr)
        : bStr.localeCompare(aStr);
    });
  }, [data, sortKey, sortDirection]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDirection('desc');
    }
  };

  const formatValue = (value: unknown, format?: (v: unknown, r: StatRecord) => string, record?: StatRecord): string => {
    if (value === null || value === undefined) return '-';
    if (format && record) return format(value, record);
    if (typeof value === 'number') {
      return Number.isInteger(value) ? String(value) : value.toFixed(1);
    }
    if (typeof value === 'boolean') return value ? 'Y' : 'N';
    return String(value);
  };

  const getPositionAbbr = (position: string): string => {
    const abbrs: Record<string, string> = {
      'back_row': 'BR',
      'back_3': 'B3',
      'second_row': 'SR',
      'centre': 'C',
      'scrum_half': 'SH',
      'out_half': 'OH',
      'hooker': 'HK',
      'prop': 'P',
    };
    return abbrs[position] || position;
  };

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No historical stats found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto border rounded-lg mx-auto w-fit">
      <table className="divide-y divide-gray-200 text-sm">
        <thead className="bg-gray-100">
          <tr>
            <th className="px-2 py-2 text-left text-xs font-semibold text-gray-700 sticky left-0 bg-gray-100 z-10" rowSpan={2}>
              Name
            </th>
            <th className="px-2 py-2 text-left text-xs font-semibold text-gray-700" rowSpan={2}>
              Country
            </th>
            <th className="px-2 py-2 text-left text-xs font-semibold text-gray-700" rowSpan={2}>
              Pos
            </th>

            {columnGroups.map((group) => {
              const isExpanded = expandedGroups.has(group.id);
              return (
                <th
                  key={group.id}
                  colSpan={isExpanded ? group.columns.length : 1}
                  className={cn(
                    'px-2 py-2 text-center text-xs font-semibold cursor-pointer hover:bg-gray-200 border-l border-gray-300',
                    isExpanded ? 'bg-primary-100 text-primary-800' : 'bg-gray-200 text-gray-600'
                  )}
                  onClick={() => toggleGroup(group.id)}
                >
                  <div className="flex items-center justify-center gap-1">
                    <span>{isExpanded ? '\u25BC' : '\u25B6'}</span>
                    <span>{group.label}</span>
                  </div>
                </th>
              );
            })}
          </tr>

          <tr className="bg-gray-50">
            {columnGroups.map((group) => {
              const isExpanded = expandedGroups.has(group.id);
              if (!isExpanded) {
                return (
                  <th
                    key={`${group.id}-collapsed`}
                    className="px-2 py-1 text-center text-xs text-gray-400 border-l border-gray-300"
                  >
                    ...
                  </th>
                );
              }
              return group.columns.map((col, idx) => (
                <th
                  key={String(col.key)}
                  className={cn(
                    'px-2 py-1 text-center text-xs font-medium text-gray-600 cursor-pointer hover:bg-gray-100',
                    idx === 0 && 'border-l border-gray-300'
                  )}
                  onClick={() => handleSort(String(col.key))}
                >
                  <div className="flex items-center justify-center gap-0.5">
                    {col.header}
                    {sortKey === col.key && (
                      <span className="text-primary-600">{sortDirection === 'asc' ? '\u2191' : '\u2193'}</span>
                    )}
                  </div>
                </th>
              ));
            })}
          </tr>
        </thead>

        <tbody className="bg-white divide-y divide-gray-200">
          {sortedData.map((stat, idx) => (
            <tr key={`${stat.player_id}-${stat.match_date}-${idx}`} className="hover:bg-gray-50">
              <td className="px-2 py-1 whitespace-nowrap font-medium text-gray-900 sticky left-0 bg-white z-10">
                {stat.player_name}
              </td>
              <td className="px-2 py-1 whitespace-nowrap">
                <span className="flex items-center gap-1">
                  <CountryFlag country={stat.country} size="sm" />
                  <span className="text-gray-600 text-xs">{stat.country.slice(0, 3).toUpperCase()}</span>
                </span>
              </td>
              <td className="px-2 py-1 whitespace-nowrap text-gray-600">
                {getPositionAbbr(stat.fantasy_position)}
              </td>

              {columnGroups.map((group) => {
                const isExpanded = expandedGroups.has(group.id);
                if (!isExpanded) {
                  return (
                    <td
                      key={`${group.id}-collapsed`}
                      className="px-2 py-2 text-center text-gray-400 border-l border-gray-200"
                    >
                      ...
                    </td>
                  );
                }
                return group.columns.map((col, colIdx) => (
                  <td
                    key={String(col.key)}
                    className={cn(
                      'px-2 py-1 text-center whitespace-nowrap',
                      colIdx === 0 && 'border-l border-gray-200'
                    )}
                  >
                    {formatValue((stat as Record<string, unknown>)[String(col.key)], col.format as ((v: unknown, r: StatRecord) => string) | undefined, stat)}
                  </td>
                ));
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
