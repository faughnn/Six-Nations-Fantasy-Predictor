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
        <div className="font-medium text-gray-900 flex items-center gap-2">
          <CountryFlag country={player.country} size="sm" />
          {player.name}
        </div>
      ),
    },
    {
      key: 'fantasy_position',
      header: 'Position',
      sortable: true,
      render: (player: PlayerSummary) => getPositionLabel(player.fantasy_position),
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
      render: (player: PlayerSummary) => formatPrice(player.price),
    },
    {
      key: 'predicted_points',
      header: 'Predicted',
      sortable: true,
      render: (player: PlayerSummary) => (
        <span className="font-semibold text-primary-600">
          {formatPoints(player.predicted_points)}
        </span>
      ),
    },
    {
      key: 'points_per_star',
      header: 'Value',
      sortable: true,
      render: (player: PlayerSummary) => formatPoints(player.points_per_star),
    },
    {
      key: 'is_available',
      header: 'Status',
      render: (player: PlayerSummary) => (
        <span
          className={`px-2 py-1 rounded-full text-xs ${
            player.is_available
              ? 'bg-green-100 text-green-800'
              : 'bg-gray-100 text-gray-600'
          }`}
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
