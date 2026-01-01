import { Link } from 'react-router-dom';
import type { OptimisedTeam } from '../../types';
import { PlayerCard } from '../players/PlayerCard';
import { getPositionLabel, formatPoints } from '../../utils';

interface OptimiserResultProps {
  result: OptimisedTeam;
}

export function OptimiserResult({ result }: OptimiserResultProps) {
  const { starting_xv, bench, captain, super_sub, total_cost, total_predicted_points, remaining_budget } = result;

  const startingPlayers = [
    ...starting_xv.props,
    starting_xv.hooker,
    ...starting_xv.second_row,
    ...starting_xv.back_row,
    starting_xv.scrum_half,
    starting_xv.out_half,
    ...starting_xv.centres,
    ...starting_xv.back_3,
  ].filter(Boolean);

  return (
    <div className="space-y-6" data-testid="optimal-team">
      <div className="grid grid-cols-3 gap-4">
        <div className="card text-center" data-testid="total-cost">
          <div className="text-2xl font-bold text-gray-900">
            {total_cost.toFixed(1)}
          </div>
          <div className="text-sm text-gray-500">Total Cost</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-primary-600">
            {formatPoints(total_predicted_points)}
          </div>
          <div className="text-sm text-gray-500">Predicted Points</div>
        </div>
        <div className="card text-center">
          <div className="text-2xl font-bold text-green-600">
            {remaining_budget.toFixed(1)}
          </div>
          <div className="text-sm text-gray-500">Remaining Budget</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {captain && (
          <div className="card" data-testid="captain-pick">
            <h3 className="font-semibold mb-2">Captain (2x points)</h3>
            <PlayerCard player={captain} isCaptain />
          </div>
        )}
        {super_sub && (
          <div className="card" data-testid="super-sub-pick">
            <h3 className="font-semibold mb-2">Super Sub (3x points)</h3>
            <PlayerCard player={super_sub} isSuperSub />
          </div>
        )}
      </div>

      <div className="card">
        <h3 className="font-semibold mb-4">Starting XV</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {startingPlayers.map((player) => (
            <PlayerCard
              key={player!.id}
              player={player!}
              isCaptain={captain?.id === player!.id}
            />
          ))}
        </div>
      </div>

      {bench.length > 0 && (
        <div className="card">
          <h3 className="font-semibold mb-4">Bench</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {bench.map((player) => (
              <PlayerCard
                key={player.id}
                player={player}
                isSuperSub={super_sub?.id === player.id}
              />
            ))}
          </div>
        </div>
      )}

      <div className="flex justify-center">
        <Link to="/team-builder" className="btn-primary">
          Edit in Team Builder
        </Link>
      </div>
    </div>
  );
}
