import type { PlayerSummary } from '../../types';
import { CountryFlag } from '../common/CountryFlag';
import { formatPrice, formatPoints, getPositionLabel, cn } from '../../utils';

interface PlayerCardProps {
  player: PlayerSummary;
  onClick?: () => void;
  selected?: boolean;
  showRemove?: boolean;
  onRemove?: () => void;
  isCaptain?: boolean;
  isSuperSub?: boolean;
}

export function PlayerCard({
  player,
  onClick,
  selected = false,
  showRemove = false,
  onRemove,
  isCaptain = false,
  isSuperSub = false,
}: PlayerCardProps) {
  return (
    <div
      className={cn(
        'card cursor-pointer transition-all',
        selected && 'ring-2 ring-primary-500',
        isCaptain && 'border-2 border-yellow-500',
        isSuperSub && 'border-2 border-purple-500'
      )}
      onClick={onClick}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
            <CountryFlag country={player.country} size="sm" />
            {player.name}
          </h3>
          <p className="text-sm text-gray-500">
            {getPositionLabel(player.fantasy_position)} | {player.country}
          </p>
        </div>
        {showRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove?.();
            }}
            className="text-red-500 hover:text-red-700"
          >
            X
          </button>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-gray-500">Price:</span>{' '}
          <span className="font-medium">{formatPrice(player.price)}</span>
        </div>
        <div>
          <span className="text-gray-500">Predicted:</span>{' '}
          <span className="font-medium text-primary-600">
            {formatPoints(player.predicted_points)}
          </span>
        </div>
      </div>

      {(isCaptain || isSuperSub) && (
        <div className="mt-2">
          {isCaptain && (
            <span className="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs font-medium">
              Captain (2x)
            </span>
          )}
          {isSuperSub && (
            <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-medium">
              Super Sub (3x)
            </span>
          )}
        </div>
      )}
    </div>
  );
}
