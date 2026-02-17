import type { PlayerSummary } from '../../types';
import { DataTable } from '../common/DataTable';
import { CountryFlag } from '../common/CountryFlag';
import { formatPrice, formatPoints, getPositionLabel } from '../../utils';

interface PlayerTableProps {
  players: PlayerSummary[];
  onPlayerClick?: (player: PlayerSummary) => void;
  onAddPlayer?: (player: PlayerSummary) => void;
  showAddButton?: boolean;
}

export function PlayerTable({
  players,
  onPlayerClick,
  onAddPlayer,
  showAddButton = false,
}: PlayerTableProps) {
  const columns = [
    {
      key: 'name',
      header: 'Name',
      sortable: true,
      render: (player: PlayerSummary) => (
        <div className="font-medium text-slate-800 flex items-center gap-2">
          <CountryFlag country={player.country} size="sm" />
          {player.name}
        </div>
      ),
    },
    {
      key: 'fantasy_position',
      header: 'Position',
      sortable: true,
      render: (player: PlayerSummary) => (
        <span className="text-slate-500">{getPositionLabel(player.fantasy_position)}</span>
      ),
    },
    {
      key: 'country',
      header: 'Country',
      sortable: true,
    },
    {
      key: 'price',
      header: 'Price',
      sortable: true,
      render: (player: PlayerSummary) => (
        <span className="tabular-nums">{formatPrice(player.price)}</span>
      ),
    },
    {
      key: 'predicted_points',
      header: 'Predicted',
      sortable: true,
      render: (player: PlayerSummary) => (
        <span className="font-semibold text-primary-600 tabular-nums">
          {formatPoints(player.predicted_points)}
        </span>
      ),
    },
    {
      key: 'points_per_star',
      header: 'Value',
      sortable: true,
      render: (player: PlayerSummary) => (
        <span className="tabular-nums">{formatPoints(player.points_per_star)}</span>
      ),
    },
    {
      key: 'is_available',
      header: 'Status',
      render: (player: PlayerSummary) => (
        <span
          className={
            player.is_available
              ? 'badge-green'
              : 'badge-gray'
          }
        >
          {player.is_available ? (player.is_starting ? 'Starting' : 'Bench') : 'N/A'}
        </span>
      ),
    },
    ...(showAddButton
      ? [
          {
            key: 'actions',
            header: '',
            render: (player: PlayerSummary) => (
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onAddPlayer?.(player);
                }}
                className="btn-primary text-xs"
                data-testid={`add-player-${player.id}`}
              >
                Add
              </button>
            ),
          },
        ]
      : []),
  ];

  return (
    <DataTable
      data={players}
      columns={columns}
      keyExtractor={(player) => player.id}
      onRowClick={onPlayerClick}
      emptyMessage="No players found"
    />
  );
}
