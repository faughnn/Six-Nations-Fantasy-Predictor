import { useState } from 'react';
import { useComparePlayers } from '../hooks/usePlayers';
import { DataTable } from '../components/common/DataTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { formatPrice, formatPoints, getPositionLabel, getCountryFlag } from '../utils';
import type { Position, PlayerSummary } from '../types';

const POSITIONS: Position[] = [
  'prop',
  'hooker',
  'second_row',
  'back_row',
  'scrum_half',
  'out_half',
  'centre',
  'back_3',
];

export default function Compare() {
  const [round, setRound] = useState(1);
  const [position, setPosition] = useState<Position | ''>('');

  const { data: players, isLoading } = useComparePlayers(
    round,
    position || undefined
  );

  const columns = [
    {
      key: 'name',
      header: 'Player',
      sortable: true,
      render: (player: PlayerSummary) => (
        <div className="font-medium">
          {getCountryFlag(player.country)} {player.name}
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
        <span className="font-bold text-primary-600">
          {formatPoints(player.predicted_points)}
        </span>
      ),
    },
    {
      key: 'points_per_star',
      header: 'Pts/Star',
      sortable: true,
      render: (player: PlayerSummary) => formatPoints(player.points_per_star),
    },
    {
      key: 'value_score',
      header: 'Value',
      sortable: true,
      render: (player: PlayerSummary) => {
        const value = player.value_score;
        if (!value) return '-';
        const color =
          value > 1.5
            ? 'text-green-600'
            : value > 1
            ? 'text-yellow-600'
            : 'text-red-600';
        return <span className={`font-medium ${color}`}>{value.toFixed(2)}</span>;
      },
    },
    {
      key: 'anytime_try_odds',
      header: 'Try Odds',
      sortable: true,
      render: (player: PlayerSummary) =>
        player.anytime_try_odds ? player.anytime_try_odds.toFixed(2) : '-',
    },
  ];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Compare Players</h1>

      <div className="card">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="round-select" className="label">
              Round
            </label>
            <select
              id="round-select"
              className="input"
              value={round}
              onChange={(e) => setRound(parseInt(e.target.value))}
            >
              {[1, 2, 3, 4, 5].map((r) => (
                <option key={r} value={r}>
                  Round {r}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="position-select" className="label">
              Position
            </label>
            <select
              id="position-select"
              className="input"
              value={position}
              onChange={(e) => setPosition(e.target.value as Position | '')}
            >
              <option value="">All Positions</option>
              {POSITIONS.map((pos) => (
                <option key={pos} value={pos}>
                  {getPositionLabel(pos)}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="card" data-testid="comparison-table">
          <DataTable
            data={players || []}
            columns={columns}
            keyExtractor={(player) => player.id}
            emptyMessage="No players available for comparison"
          />
        </div>
      )}
    </div>
  );
}
