import { useState, useMemo } from 'react';
import type { PlayerProjection } from '../../types';
import { cn } from '../../utils';
import { CountryFlag } from '../common/CountryFlag';
import { Tooltip } from '../common/Tooltip';

interface Column {
  key: keyof PlayerProjection;
  header: string;
  tooltip?: string;
  format?: (value: number | null) => string;
}

interface ColumnGroup {
  id: string;
  label: string;
  columns: Column[];
}

const COLUMN_GROUPS: ColumnGroup[] = [
  {
    id: 'cost',
    label: 'Cost / Value',
    columns: [
      { key: 'price', header: 'Price', tooltip: 'Current fantasy price in stars', format: (v) => v !== null ? v.toFixed(1) : '-' },
      { key: 'predicted_points', header: 'Pred Pts', tooltip: 'ML-predicted fantasy points for this round', format: (v) => v !== null ? v.toFixed(1) : '-' },
      { key: 'points_per_star', header: 'Pts/Star', tooltip: 'Predicted points divided by price — higher is better value', format: (v) => v !== null ? v.toFixed(2) : '-' },
    ],
  },
  {
    id: 'predicted',
    label: 'Predicted Stats',
    columns: [
      { key: 'avg_tries', header: 'Tries/G', tooltip: 'Average tries per game', format: (v) => v !== null ? v.toFixed(2) : '-' },
      { key: 'avg_tackles', header: 'Tck/G', tooltip: 'Average tackles per game', format: (v) => v !== null ? v.toFixed(1) : '-' },
      { key: 'avg_metres', header: 'Mtrs/G', tooltip: 'Average metres carried per game', format: (v) => v !== null ? v.toFixed(0) : '-' },
      { key: 'avg_turnovers', header: 'TO/G', tooltip: 'Average turnovers won per game', format: (v) => v !== null ? v.toFixed(2) : '-' },
      { key: 'avg_defenders_beaten', header: 'DB/G', tooltip: 'Average defenders beaten per game', format: (v) => v !== null ? v.toFixed(1) : '-' },
      { key: 'avg_offloads', header: 'Off/G', tooltip: 'Average offloads per game', format: (v) => v !== null ? v.toFixed(2) : '-' },
    ],
  },
  {
    id: 'efficiency',
    label: 'Efficiency',
    columns: [
      { key: 'expected_minutes', header: 'Exp Min', tooltip: 'Expected minutes on the pitch', format: (v) => v !== null ? v.toFixed(0) : '-' },
      { key: 'start_rate', header: 'Start %', tooltip: 'Historical starting XV selection rate', format: (v) => v !== null ? `${v.toFixed(0)}%` : '-' },
      { key: 'points_per_minute', header: 'Pts/Min', tooltip: 'Fantasy points generated per minute played', format: (v) => v !== null ? v.toFixed(3) : '-' },
    ],
  },
  {
    id: 'odds',
    label: 'Odds / Fixture',
    columns: [
      { key: 'anytime_try_odds', header: 'Try Odds', tooltip: 'Bookmaker anytime try scorer odds', format: (v) => v !== null ? v.toFixed(2) : '-' },
      { key: 'opponent', header: 'Opp', tooltip: 'Upcoming opponent' },
      { key: 'home_away', header: 'H/A', tooltip: 'Home or Away fixture' },
      { key: 'total_games', header: 'Games', tooltip: 'Total games in historical sample' },
    ],
  },
];

const POSITION_ABBRS: Record<string, string> = {
  prop: 'P',
  hooker: 'HK',
  second_row: 'SR',
  back_row: 'BR',
  scrum_half: 'SH',
  out_half: 'FH',
  centre: 'C',
  back_3: 'B3',
};

function getValueTierClass(pointsPerStar: number | null): string {
  if (pointsPerStar === null) return '';
  if (pointsPerStar >= 15) return 'bg-emerald-50/60';
  if (pointsPerStar >= 10) return 'bg-emerald-50/40';
  if (pointsPerStar >= 7) return 'bg-yellow-50/50';
  return '';
}

interface ProjectionsTableProps {
  data: PlayerProjection[];
}

export function ProjectionsTable({ data }: ProjectionsTableProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(
    new Set(['cost', 'predicted', 'efficiency', 'odds'])
  );
  const [sortKey, setSortKey] = useState<keyof PlayerProjection | null>('predicted_points');
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

  const handleSort = (key: keyof PlayerProjection) => {
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
                    {col.tooltip ? (
                      <Tooltip text={col.tooltip}>{col.header}</Tooltip>
                    ) : (
                      col.header
                    )}
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
          {sortedData.map((player) => (
            <tr
              key={player.id}
              className={cn(
                'hover:bg-primary-50/30 transition-colors',
                getValueTierClass(player.points_per_star)
              )}
            >
              {/* Fixed columns */}
              <td className={cn(
                'px-3 py-1.5 whitespace-nowrap font-medium text-slate-800 sticky left-0 z-10',
                getValueTierClass(player.points_per_star) || 'bg-white'
              )}>
                {player.name}
              </td>
              <td className="px-2 py-1.5 whitespace-nowrap">
                <span className="flex items-center gap-1">
                  <CountryFlag country={player.country} size="sm" />
                  <span className="text-slate-500 text-xs">{player.country.slice(0, 3).toUpperCase()}</span>
                </span>
              </td>
              <td className="px-2 py-1.5 whitespace-nowrap text-slate-500">
                {POSITION_ABBRS[player.fantasy_position] || player.fantasy_position}
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
                      colIdx === 0 && 'border-l border-slate-100'
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
