import type { PlayerSummary, Position } from '../../types';
import type { TeamState } from '../../hooks/useTeam';
import { PositionSlot } from './PositionSlot';
import { BudgetTracker } from './BudgetTracker';
import { TeamSummary } from './TeamSummary';
import { getPositionLabel } from '../../utils';

interface TeamBuilderProps {
  team: TeamState;
  totalCost: number;
  remainingBudget: number;
  totalPredictedPoints: number;
  countryCount: Record<string, number>;
  onRemovePlayer: (playerId: number) => void;
  onSetCaptain: (player: PlayerSummary) => void;
  onSetSuperSub: (player: PlayerSummary) => void;
  onClear: () => void;
}

const POSITION_ORDER: { key: keyof Omit<TeamState, 'bench' | 'captain' | 'super_sub'>; position: Position; limit: number }[] = [
  { key: 'props', position: 'prop', limit: 2 },
  { key: 'hooker', position: 'hooker', limit: 1 },
  { key: 'second_row', position: 'second_row', limit: 2 },
  { key: 'back_row', position: 'back_row', limit: 3 },
  { key: 'scrum_half', position: 'scrum_half', limit: 1 },
  { key: 'out_half', position: 'out_half', limit: 1 },
  { key: 'centres', position: 'centre', limit: 2 },
  { key: 'back_3', position: 'back_3', limit: 3 },
];

export function TeamBuilder({
  team,
  totalCost,
  remainingBudget,
  totalPredictedPoints,
  countryCount,
  onRemovePlayer,
  onSetCaptain,
  onSetSuperSub,
  onClear,
}: TeamBuilderProps) {
  const getPlayersForPosition = (key: keyof typeof team) => {
    const value = team[key];
    if (Array.isArray(value)) return value;
    if (value && typeof value === 'object' && 'id' in value) return [value as PlayerSummary];
    return [];
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6" data-testid="team-builder">
      <div className="lg:col-span-2">
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Starting XV</h2>
            <button onClick={onClear} className="btn-secondary text-sm">
              Clear Team
            </button>
          </div>

          <div className="space-y-4">
            {POSITION_ORDER.map(({ key, position, limit }) => (
              <div key={key} className="border-b pb-4">
                <h3 className="font-medium text-gray-700 mb-2">
                  {getPositionLabel(position)} ({getPlayersForPosition(key).length}/{limit})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                  {getPlayersForPosition(key).map((player) => (
                    <PositionSlot
                      key={player.id}
                      player={player}
                      position={position}
                      onRemove={() => onRemovePlayer(player.id)}
                      onSetCaptain={() => onSetCaptain(player)}
                      isCaptain={team.captain?.id === player.id}
                    />
                  ))}
                  {Array.from({ length: limit - getPlayersForPosition(key).length }).map((_, i) => (
                    <PositionSlot
                      key={`empty-${key}-${i}`}
                      player={null}
                      position={position}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <h3 className="font-medium text-gray-700 mb-2">
              Bench ({team.bench.length}/3)
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
              {team.bench.map((player) => (
                <PositionSlot
                  key={player.id}
                  player={player}
                  position={player.fantasy_position}
                  isBench
                  onRemove={() => onRemovePlayer(player.id)}
                  onSetSuperSub={() => onSetSuperSub(player)}
                  isSuperSub={team.super_sub?.id === player.id}
                />
              ))}
              {Array.from({ length: 3 - team.bench.length }).map((_, i) => (
                <PositionSlot
                  key={`empty-bench-${i}`}
                  player={null}
                  position="prop"
                  isBench
                />
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <BudgetTracker
          totalCost={totalCost}
          remainingBudget={remainingBudget}
          data-testid="remaining-budget"
        />
        <TeamSummary
          totalPredictedPoints={totalPredictedPoints}
          countryCount={countryCount}
          playerCount={
            Object.values(team).flat().filter((p): p is PlayerSummary =>
              p !== null && typeof p === 'object' && 'id' in p
            ).length
          }
        />
      </div>
    </div>
  );
}
