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
        'card cursor-pointer transition-all hover:shadow-card-hover',
        selected && 'ring-2 ring-primary-500',
        isCaptain && 'border-2 border-yellow-400',
        isSuperSub && 'border-2 border-purple-400'
      )}
      onClick={onClick}
    >
      <div className="flex justify-between items-start">
        <div>
          <h3 className="font-semibold text-slate-800 flex items-center gap-2">
            <CountryFlag country={player.country} size="sm" />
            {player.name}
          </h3>
          <p className="text-sm text-slate-400">
            {getPositionLabel(player.fantasy_position)} | {player.country}
          </p>
        </div>
        {showRemove && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRemove?.();
            }}
            className="text-red-400 hover:text-red-600 transition-colors"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-slate-400">Price:</span>{' '}
          <span className="font-medium tabular-nums">{formatPrice(player.price)}</span>
        </div>
        <div>
          <span className="text-slate-400">Predicted:</span>{' '}
          <span className="font-medium text-primary-600 tabular-nums">
            {formatPoints(player.predicted_points)}
          </span>
        </div>
      </div>

      {(isCaptain || isSuperSub) && (
        <div className="mt-2">
          {isCaptain && (
            <span className="badge-yellow">
              Captain (2x)
            </span>
          )}
          {isSuperSub && (
            <span className="badge-purple">
              Super Sub (3x)
            </span>
          )}
        </div>
      )}
    </div>
  );
}
