import { useState } from 'react';
import { usePlayers, usePlayer } from '../hooks/usePlayers';
import { PlayerTable } from '../components/players/PlayerTable';
import { PlayerFilters } from '../components/players/PlayerFilters';
import { PlayerDetail } from '../components/players/PlayerDetail';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import type { Country, Position, PlayerSummary } from '../types';

interface Filters {
  country?: Country;
  position?: Position;
  minPrice?: number;
  maxPrice?: number;
  isAvailable?: boolean;
}

export default function Players() {
  const [filters, setFilters] = useState<Filters>({});
  const [selectedPlayerId, setSelectedPlayerId] = useState<number | null>(null);

  const { data: players, isLoading, error } = usePlayers({
    country: filters.country,
    position: filters.position,
    min_price: filters.minPrice,
    max_price: filters.maxPrice,
    is_available: filters.isAvailable,
  });

  const { data: selectedPlayer } = usePlayer(selectedPlayerId || 0);

  const handlePlayerClick = (player: PlayerSummary) => {
    setSelectedPlayerId(player.id);
  };

  if (error) {
    return (
      <div className="text-center py-12 text-red-500">
        Error loading players
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-800">Players</h1>
      <p className="text-sm text-slate-400 mt-1 mb-6">
        Browse all Six Nations players with their fantasy prices, predicted points, and value ratings. Click a player for a detailed breakdown.
      </p>

      <PlayerFilters filters={filters} onChange={setFilters} />

      {isLoading ? (
        <div className="flex justify-center py-12">
          <LoadingSpinner size="lg" />
        </div>
      ) : (
        <div className="card">
          <PlayerTable
            players={players || []}
            onPlayerClick={handlePlayerClick}
          />
        </div>
      )}

      {selectedPlayer && (
        <PlayerDetail
          player={selectedPlayer}
          onClose={() => setSelectedPlayerId(null)}
        />
      )}
    </div>
  );
}
