import { useState, useMemo } from 'react';
import type { PlayerStat } from '../../types';
import { cn } from '../../utils';
import { CountryFlag } from '../common/CountryFlag';

interface ColumnGroup {
  id: string;
  label: string;
  columns: {
    key: keyof PlayerStat;
    header: string;
    format?: (value: number | null) => string;
  }[];
}

const COLUMN_GROUPS: ColumnGroup[] = [
  {
    id: 'game',
    label: 'Game Stats',
    columns: [
      { key: 'minutes', header: 'Min' },
      { key: 'tackles', header: 'Tck' },
      { key: 'penalties_conceded', header: 'Pen' },
      { key: 'defenders_beaten', header: 'Def Beat' },
      { key: 'meters_carried', header: 'Meters' },
      { key: 'offloads', header: 'Off' },
    ],
  },
  {
    id: 'setpiece',
    label: 'Set Piece',
    columns: [
      { key: 'kick_50_22', header: '50-22' },
      { key: 'lineouts_won', header: 'LO Won' },
      { key: 'breakdown_steal', header: 'TO Won' },
      { key: 'att_scrum', header: 'Scrum' },
    ],
  },
  {
    id: 'scoring',
    label: 'Scoring',
    columns: [
      { key: 'try_scored', header: 'Try' },
      { key: 'assist', header: 'Ast' },
      { key: 'conversion', header: 'Con' },
      { key: 'penalty', header: 'PK' },
      { key: 'drop_goal', header: 'DG' },
    ],
  },
  {
    id: 'cards',
    label: 'Cards',
    columns: [
      { key: 'yellow_card', header: 'YC' },
      { key: 'red_card', header: 'RC' },
      { key: 'motm', header: 'MOTM' },
    ],
  },
  {
    id: 'weekly',
    label: 'Weekly Pts',
    columns: [
      { key: 'wk1', header: 'W1' },
      { key: 'wk2', header: 'W2' },
      { key: 'wk3', header: 'W3' },
      { key: 'wk4', header: 'W4' },
      { key: 'wk5', header: 'W5' },
    ],
  },
  {
    id: 'fantasy',
    label: 'Fantasy',
    columns: [
      { key: 'points', header: 'Pts' },
      { key: 'value', header: 'Price', format: (v) => v !== null ? `${v.toFixed(1)}` : '-' },
      { key: 'value_start', header: 'Start', format: (v) => v !== null ? `${v.toFixed(1)}` : '-' },
      { key: 'change', header: '+/-', format: (v) => v !== null ? (v >= 0 ? `+${v.toFixed(1)}` : v.toFixed(1)) : '-' },
    ],
  },
];

interface StatsTableProps {
  data: PlayerStat[];
}

export function StatsTable({ data }: StatsTableProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(['game', 'setpiece', 'scoring', 'cards', 'weekly', 'fantasy']) // All expanded by default
  );
  const [sortKey, setSortKey] = useState<keyof PlayerStat | null>('points');
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
      const aVal = a[sortKey];
      const bVal = b[sortKey];

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

  const handleSort = (key: keyof PlayerStat) => {
    if (sortKey === key) {
      setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDirection('desc');
    }
  };

  const formatValue = (value: unknown, format?: (v: number | null) => string): string => {
    if (value === null || value === undefined) return '-';
    if (format && typeof value === 'number') return format(value);
    if (typeof value === 'number') {
      return Number.isInteger(value) ? String(value) : value.toFixed(1);
    }
    return String(value);
  };

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        No players found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 mx-auto w-fit">
      <table className="divide-y divide-slate-100 text-sm">
        {/* Header Row 1: Group Headers */}
        <thead>
          <tr className="bg-slate-50">
            {/* Fixed columns */}
            <th className="px-3 py-2.5 text-left text-xs font-semibold text-slate-600 sticky left-0 bg-slate-50 z-10" rowSpan={2}>
              Name
            </th>
            <th className="px-2 py-2.5 text-left text-xs font-semibold text-slate-600" rowSpan={2}>
              Country
            </th>
            <th className="px-2 py-2.5 text-left text-xs font-semibold text-slate-600" rowSpan={2}>
              Pos
            </th>

            {/* Collapsible group headers */}
            {COLUMN_GROUPS.map((group) => {
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
                    <span className="text-[10px]">{isExpanded ? '▼' : '▶'}</span>
                    <span>{group.label}</span>
                  </div>
                </th>
              );
            })}
          </tr>

          {/* Header Row 2: Column Headers */}
          <tr className="bg-white">
            {COLUMN_GROUPS.map((group) => {
              const isExpanded = expandedGroups.has(group.id);
              if (!isExpanded) {
                return (
                  <th
                    key={`${group.id}-collapsed`}
                    className="px-2 py-1.5 text-center text-xs text-slate-300 border-l border-slate-200"
                  >
                    ...
                  </th>
                );
              }
              return group.columns.map((col, idx) => (
                <th
                  key={col.key}
                  className={cn(
                    'px-2 py-1.5 text-center text-xs font-medium text-slate-500 cursor-pointer hover:text-slate-700',
                    idx === 0 && 'border-l border-slate-200'
                  )}
                  onClick={() => handleSort(col.key)}
                >
                  <div className="flex items-center justify-center gap-0.5">
                    {col.header}
                    {sortKey === col.key && (
                      <span className="text-primary-500">{sortDirection === 'asc' ? '↑' : '↓'}</span>
                    )}
                  </div>
                </th>
              ));
            })}
          </tr>
        </thead>

        <tbody className="divide-y divide-slate-100">
          {sortedData.map((player, idx) => (
            <tr key={`${player.name}-${idx}`} className="hover:bg-primary-50/30 transition-colors">
              {/* Fixed columns */}
              <td className="px-3 py-1.5 whitespace-nowrap font-medium text-slate-800 sticky left-0 bg-white z-10">
                {player.name}
              </td>
              <td className="px-2 py-1.5 whitespace-nowrap">
                <span className="flex items-center gap-1">
                  <CountryFlag country={player.country} size="sm" />
                  <span className="text-slate-500 text-xs">{player.country.slice(0, 3).toUpperCase()}</span>
                </span>
              </td>
              <td className="px-2 py-1.5 whitespace-nowrap text-slate-500">
                {getPositionAbbr(player.position)}
              </td>

              {/* Collapsible group columns */}
              {COLUMN_GROUPS.map((group) => {
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
                    key={col.key}
                    className={cn(
                      'px-2 py-1.5 text-center whitespace-nowrap tabular-nums',
                      colIdx === 0 && 'border-l border-slate-100',
                      col.key === 'change' && player.change !== null && (
                        player.change > 0 ? 'text-emerald-600' : player.change < 0 ? 'text-red-500' : ''
                      )
                    )}
                  >
                    {formatValue(player[col.key], col.format)}
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

function getPositionAbbr(position: string): string {
  const abbrs: Record<string, string> = {
    'Back-row': 'BR',
    'Back Three': 'B3',
    'Second-row': 'SR',
    'Centre': 'C',
    'Scrum-half': 'SH',
    'Fly-half': 'FH',
    'Hooker': 'HK',
    'Prop': 'P',
  };
  return abbrs[position] || position;
}
