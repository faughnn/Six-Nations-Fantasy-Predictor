import type { PlayerSummary, Position } from '../../types';
import { getPositionLabel, getCountryFlag, formatPoints, cn } from '../../utils';

interface PositionSlotProps {
  player: PlayerSummary | null;
  position: Position;
  isBench?: boolean;
  onRemove?: () => void;
  onSetCaptain?: () => void;
  onSetSuperSub?: () => void;
  isCaptain?: boolean;
  isSuperSub?: boolean;
}

export function PositionSlot({
  player,
  position,
  isBench = false,
  onRemove,
  onSetCaptain,
  onSetSuperSub,
  isCaptain = false,
  isSuperSub = false,
}: PositionSlotProps) {
  if (!player) {
    return (
      <div
        className={cn(
          'border-2 border-dashed border-gray-300 rounded-lg p-3 text-center',
          'bg-gray-50 text-gray-400'
        )}
        data-testid={`position-${position}`}
      >
        <div className="text-sm">{isBench ? 'Bench' : getPositionLabel(position)}</div>
        <div className="text-xs">Empty</div>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'border rounded-lg p-3 bg-white shadow-sm',
        isCaptain && 'ring-2 ring-yellow-400',
        isSuperSub && 'ring-2 ring-purple-400'
      )}
    >
      <div className="flex justify-between items-start">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate">
            {getCountryFlag(player.country)} {player.name}
          </div>
          <div className="text-xs text-gray-500">
            {formatPoints(player.predicted_points)} pts
          </div>
        </div>
        <button
          onClick={onRemove}
          className="text-red-400 hover:text-red-600 ml-2"
          aria-label="Remove player"
        >
          x
        </button>
      </div>

      <div className="flex gap-1 mt-2">
        {!isBench && (
          <button
            onClick={onSetCaptain}
            className={cn(
              'text-xs px-2 py-1 rounded',
              isCaptain
                ? 'bg-yellow-100 text-yellow-800'
                : 'bg-gray-100 text-gray-600 hover:bg-yellow-50'
            )}
          >
            {isCaptain ? 'C' : 'Set C'}
          </button>
        )}
        {isBench && (
          <button
            onClick={onSetSuperSub}
            className={cn(
              'text-xs px-2 py-1 rounded',
              isSuperSub
                ? 'bg-purple-100 text-purple-800'
                : 'bg-gray-100 text-gray-600 hover:bg-purple-50'
            )}
          >
            {isSuperSub ? 'SS' : 'Set SS'}
          </button>
        )}
      </div>
    </div>
  );
}
