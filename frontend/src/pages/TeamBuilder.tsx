import { useState } from 'react';
import { usePlayers } from '../hooks/usePlayers';
import { useTeam } from '../hooks/useTeam';
import { TeamBuilder as TeamBuilderComponent } from '../components/team/TeamBuilder';
import { PlayerTable } from '../components/players/PlayerTable';
import { PlayerFilters } from '../components/players/PlayerFilters';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import type { Country, Position, PlayerSummary } from '../types';

interface Filters {
  country?: Country;
  position?: Position;
  minPrice?: number;
  maxPrice?: number;
  isAvailable?: boolean;
}

export default function TeamBuilder() {
  const [filters, setFilters] = useState<Filters>({ isAvailable: true });

  const { data: players, isLoading } = usePlayers({
    country: filters.country,
    position: filters.position,
    min_price: filters.minPrice,
    max_price: filters.maxPrice,
    is_available: filters.isAvailable,
  });

  const {
    team,
    totalCost,
    remainingBudget,
    totalPredictedPoints,
    countryCount,
    addPlayer,
    removePlayer,
    setCaptain,
    setSuperSub,
    clearTeam,
  } = useTeam();

  const handleAddPlayer = (player: PlayerSummary, toBench = false) => {
    const result = addPlayer(player, toBench);
    if (!result.valid) {
      alert(result.reason);
    }
  };

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">Team Builder</h1>

      <TeamBuilderComponent
        team={team}
        totalCost={totalCost}
        remainingBudget={remainingBudget}
        totalPredictedPoints={totalPredictedPoints}
        countryCount={countryCount}
        onRemovePlayer={removePlayer}
        onSetCaptain={setCaptain}
        onSetSuperSub={setSuperSub}
        onClear={clearTeam}
      />

      <div>
        <h2 className="text-xl font-bold mb-4">Available Players</h2>
        <PlayerFilters filters={filters} onChange={setFilters} />

        {isLoading ? (
          <div className="flex justify-center py-8">
            <LoadingSpinner />
          </div>
        ) : (
          <div className="card">
            <PlayerTable
              players={players || []}
              showAddButton
              onAddPlayer={(player) => handleAddPlayer(player)}
            />
          </div>
        )}
      </div>
    </div>
  );
}
