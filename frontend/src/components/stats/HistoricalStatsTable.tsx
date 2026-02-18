import { useState, useMemo, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import type { HistoricalSixNationsStat, HistoricalClubStat } from '../../types';
import { cn } from '../../utils';
import { CountryFlag } from '../common/CountryFlag';
import { Tooltip } from '../common/Tooltip';

type StatRecord = HistoricalSixNationsStat | HistoricalClubStat;

interface ColumnDef<T> {
  key: keyof T | string;
  header: string;
  tooltip?: string;
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
      { key: 'season', header: 'Szn', tooltip: 'Six Nations season year' },
      { key: 'round', header: 'Rd', tooltip: 'Tournament round number' },
      { key: 'match_date', header: 'Date', tooltip: 'Match date', format: (v) => v ? String(v).slice(5) : '-' },
      { key: 'opponent', header: 'Opp', tooltip: 'Opposing team' },
      { key: 'home_away', header: 'H/A', tooltip: 'Home or Away fixture' },
    ],
  },
  {
    id: 'participation',
    label: 'Participation',
    columns: [
      { key: 'started', header: 'Start', tooltip: 'Started in the XV', format: (v) => v ? 'Y' : 'N' },
      { key: 'minutes_played', header: 'Min', tooltip: 'Minutes played' },
    ],
  },
  {
    id: 'attacking',
    label: 'Attacking',
    columns: [
      { key: 'tries', header: 'Try', tooltip: 'Tries scored' },
      { key: 'try_assists', header: 'Ast', tooltip: 'Try assists' },
      { key: 'conversions', header: 'Con', tooltip: 'Conversions kicked' },
      { key: 'penalties_kicked', header: 'PK', tooltip: 'Penalty goals kicked' },
      { key: 'drop_goals', header: 'DG', tooltip: 'Drop goals' },
      { key: 'defenders_beaten', header: 'Def B', tooltip: 'Defenders beaten in carry' },
      { key: 'metres_carried', header: 'Mtrs', tooltip: 'Metres gained carrying the ball' },
      { key: 'clean_breaks', header: 'Brk', tooltip: 'Clean line breaks' },
      { key: 'offloads', header: 'Off', tooltip: 'Offloads in contact' },
      { key: 'fifty_22_kicks', header: '50-22', tooltip: 'Successful 50:22 kicks' },
    ],
  },
  {
    id: 'defensive',
    label: 'Defensive',
    columns: [
      { key: 'tackles_made', header: 'Tck', tooltip: 'Tackles made' },
      { key: 'tackles_missed', header: 'Miss', tooltip: 'Tackles missed' },
      { key: 'turnovers_won', header: 'TO', tooltip: 'Turnovers won at the breakdown' },
      { key: 'lineout_steals', header: 'LO St', tooltip: 'Lineout steals' },
      { key: 'scrums_won', header: 'Scr', tooltip: 'Scrums won' },
    ],
  },
  {
    id: 'discipline',
    label: 'Discipline',
    columns: [
      { key: 'penalties_conceded', header: 'Pen', tooltip: 'Penalties conceded' },
      { key: 'yellow_cards', header: 'YC', tooltip: 'Yellow cards' },
      { key: 'red_cards', header: 'RC', tooltip: 'Red cards' },
    ],
  },
  {
    id: 'awards',
    label: 'Awards',
    columns: [
      { key: 'player_of_match', header: 'POTM', tooltip: 'Player of the Match award', format: (v) => v ? 'Y' : '-' },
      { key: 'fantasy_points', header: 'FPts', tooltip: 'Fantasy points scored in this match', format: (v) => v !== null ? String(v) : '-' },
    ],
  },
];

const CLUB_COLUMN_GROUPS: ColumnGroup<HistoricalClubStat>[] = [
  {
    id: 'match',
    label: 'Match Info',
    columns: [
      { key: 'league', header: 'League', tooltip: 'Club competition name' },
      { key: 'season', header: 'Szn', tooltip: 'Season year' },
      { key: 'match_date', header: 'Date', tooltip: 'Match date', format: (v) => v ? String(v).slice(5) : '-' },
      { key: 'opponent', header: 'Opp', tooltip: 'Opposing club' },
      { key: 'home_away', header: 'H/A', tooltip: 'Home or Away fixture' },
    ],
  },
  {
    id: 'participation',
    label: 'Participation',
    columns: [
      { key: 'started', header: 'Start', tooltip: 'Started the match', format: (v) => v ? 'Y' : 'N' },
      { key: 'minutes_played', header: 'Min', tooltip: 'Minutes played' },
    ],
  },
  {
    id: 'attacking',
    label: 'Attacking',
    columns: [
      { key: 'tries', header: 'Try', tooltip: 'Tries scored' },
      { key: 'try_assists', header: 'Ast', tooltip: 'Try assists' },
      { key: 'conversions', header: 'Con', tooltip: 'Conversions kicked' },
      { key: 'penalties_kicked', header: 'PK', tooltip: 'Penalty goals kicked' },
      { key: 'drop_goals', header: 'DG', tooltip: 'Drop goals' },
      { key: 'defenders_beaten', header: 'Def B', tooltip: 'Defenders beaten in carry' },
      { key: 'metres_carried', header: 'Mtrs', tooltip: 'Metres gained carrying the ball' },
      { key: 'clean_breaks', header: 'Brk', tooltip: 'Clean line breaks' },
      { key: 'offloads', header: 'Off', tooltip: 'Offloads in contact' },
    ],
  },
  {
    id: 'defensive',
    label: 'Defensive',
    columns: [
      { key: 'tackles_made', header: 'Tck', tooltip: 'Tackles made' },
      { key: 'tackles_missed', header: 'Miss', tooltip: 'Tackles missed' },
      { key: 'turnovers_won', header: 'TO', tooltip: 'Turnovers won at the breakdown' },
      { key: 'lineout_steals', header: 'LO St', tooltip: 'Lineout steals' },
      { key: 'scrums_won', header: 'Scr', tooltip: 'Scrums won' },
    ],
  },
  {
    id: 'discipline',
    label: 'Discipline',
    columns: [
      { key: 'penalties_conceded', header: 'Pen', tooltip: 'Penalties conceded' },
      { key: 'yellow_cards', header: 'YC', tooltip: 'Yellow cards' },
      { key: 'red_cards', header: 'RC', tooltip: 'Red cards' },
    ],
  },
];

interface HistoricalStatsTableProps {
  data: StatRecord[];
  type: 'six-nations' | 'club';
}

const ROW_HEIGHT = 33;

export function HistoricalStatsTable({ data, type }: HistoricalStatsTableProps) {
  const columnGroups = type === 'six-nations'
    ? SIX_NATIONS_COLUMN_GROUPS as ColumnGroup<StatRecord>[]
    : CLUB_COLUMN_GROUPS as ColumnGroup<StatRecord>[];

  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(columnGroups.map(g => g.id))
  );
  const [sortKey, setSortKey] = useState<string | null>('match_date');
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');

  const scrollRef = useRef<HTMLDivElement>(null);

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
      const aVal = (a as unknown as Record<string, unknown>)[sortKey];
      const bVal = (b as unknown as Record<string, unknown>)[sortKey];

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

  const rowVirtualizer = useVirtualizer({
    count: sortedData.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 20,
  });

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
      <div className="text-center py-8 text-slate-400">
        No historical stats found
      </div>
    );
  }

  return (
    <div>
      <div className="text-xs text-slate-400 mb-1.5 md:hidden">Swipe to see more columns</div>
      <div
        ref={scrollRef}
        className="overflow-auto rounded-xl border border-slate-200"
        style={{ maxHeight: 'calc(100vh - 280px)' }}
      >
        <table className="divide-y divide-slate-100 text-sm w-max">
          <thead className="sticky top-0 z-20">
            <tr className="bg-slate-50">
              <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-600 sticky left-0 bg-slate-50 z-30" rowSpan={2}>
                Name
              </th>
              <th className="px-2 py-2.5 text-left text-xs font-semibold text-slate-600 bg-slate-50" rowSpan={2}>
                Country
              </th>
              <th className="px-2 py-2.5 text-left text-xs font-semibold text-slate-600 bg-slate-50" rowSpan={2}>
                Pos
              </th>

              {columnGroups.map((group) => {
                const isExpanded = expandedGroups.has(group.id);
                return (
                  <th
                    key={group.id}
                    colSpan={isExpanded ? group.columns.length : 1}
                    className={cn(
                      'px-2 py-2.5 text-center text-xs font-semibold cursor-pointer border-l border-slate-200 transition-colors',
                      isExpanded
                        ? 'bg-primary-50 text-primary-700 hover:bg-primary-100'
                        : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
                    )}
                    onClick={() => toggleGroup(group.id)}
                  >
                    <div className="flex items-center justify-center gap-1">
                      <span className="text-[10px]">{isExpanded ? '\u25BC' : '\u25B6'}</span>
                      <span>{group.label}</span>
                    </div>
                  </th>
                );
              })}
            </tr>

            <tr className="bg-white">
              {columnGroups.map((group) => {
                const isExpanded = expandedGroups.has(group.id);
                if (!isExpanded) {
                  return (
                    <th
                      key={`${group.id}-collapsed`}
                      className="px-2 py-1.5 text-center text-xs text-slate-300 border-l border-slate-200 bg-white"
                    >
                      ...
                    </th>
                  );
                }
                return group.columns.map((col, idx) => (
                  <th
                    key={String(col.key)}
                    className={cn(
                      'px-2 py-1.5 text-center text-xs font-medium text-slate-500 cursor-pointer hover:text-slate-700 bg-white',
                      idx === 0 && 'border-l border-slate-200'
                    )}
                    onClick={() => handleSort(String(col.key))}
                  >
                    <div className="flex items-center justify-center gap-0.5">
                      {col.tooltip ? (
                        <Tooltip text={col.tooltip}>{col.header}</Tooltip>
                      ) : (
                        col.header
                      )}
                      {sortKey === col.key && (
                        <span className="text-primary-500">{sortDirection === 'asc' ? '\u2191' : '\u2193'}</span>
                      )}
                    </div>
                  </th>
                ));
              })}
            </tr>
          </thead>

          <tbody>
            {/* Spacer for virtual rows above visible area */}
            {rowVirtualizer.getVirtualItems().length > 0 && (
              <tr style={{ height: rowVirtualizer.getVirtualItems()[0].start }}>
                <td colSpan={999} />
              </tr>
            )}

            {rowVirtualizer.getVirtualItems().map((virtualRow) => {
              const stat = sortedData[virtualRow.index];
              return (
                <tr
                  key={virtualRow.index}
                  className="hover:bg-primary-50/30 transition-colors border-t border-slate-100"
                  style={{ height: ROW_HEIGHT }}
                >
                  <td className="px-3 py-1.5 whitespace-nowrap font-medium text-slate-800 sticky left-0 bg-white z-10">
                    {stat.player_name}
                  </td>
                  <td className="px-2 py-1.5 whitespace-nowrap">
                    <span className="flex items-center gap-1">
                      <CountryFlag country={stat.country} size="sm" />
                      <span className="text-slate-500 text-xs">{stat.country.slice(0, 3).toUpperCase()}</span>
                    </span>
                  </td>
                  <td className="px-2 py-1.5 whitespace-nowrap text-slate-500">
                    {getPositionAbbr(stat.fantasy_position)}
                  </td>

                  {columnGroups.map((group) => {
                    const isExpanded = expandedGroups.has(group.id);
                    if (!isExpanded) {
                      return (
                        <td
                          key={`${group.id}-collapsed`}
                          className="px-2 py-2 text-center text-slate-300 border-l border-slate-100"
                        >
                          ...
                        </td>
                      );
                    }
                    return group.columns.map((col, colIdx) => (
                      <td
                        key={String(col.key)}
                        className={cn(
                          'px-2 py-1.5 text-center whitespace-nowrap tabular-nums',
                          colIdx === 0 && 'border-l border-slate-100'
                        )}
                      >
                        {formatValue((stat as unknown as Record<string, unknown>)[String(col.key)], col.format as ((v: unknown, r: StatRecord) => string) | undefined, stat)}
                      </td>
                    ));
                  })}
                </tr>
              );
            })}

            {/* Spacer for virtual rows below visible area */}
            {rowVirtualizer.getVirtualItems().length > 0 && (
              <tr style={{
                height: rowVirtualizer.getTotalSize() -
                  (rowVirtualizer.getVirtualItems().at(-1)!.start + rowVirtualizer.getVirtualItems().at(-1)!.size)
              }}>
                <td colSpan={999} />
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
