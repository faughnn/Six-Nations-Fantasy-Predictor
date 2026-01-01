import { Link } from 'react-router-dom';
import { usePlayers } from '../hooks/usePlayers';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { PositionDistribution } from '../components/charts/PositionDistribution';

export default function Dashboard() {
  const { data: players, isLoading, error } = usePlayers({ is_available: true });

  if (isLoading) {
    return (
      <div className="flex justify-center py-12">
        <LoadingSpinner size="lg" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-12 text-red-600">
        Error loading dashboard data
      </div>
    );
  }

  const availablePlayers = players || [];
  const topPlayers = [...availablePlayers]
    .sort((a, b) => (b.predicted_points || 0) - (a.predicted_points || 0))
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Dashboard</h1>
        <p className="text-gray-500">Round 1 Overview</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card text-center">
          <div className="text-3xl font-bold text-primary-600">
            {availablePlayers.length}
          </div>
          <div className="text-sm text-gray-500">Available Players</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-green-600">230</div>
          <div className="text-sm text-gray-500">Budget</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-yellow-600">4</div>
          <div className="text-sm text-gray-500">Max per Country</div>
        </div>
        <div className="card text-center">
          <div className="text-3xl font-bold text-purple-600">18</div>
          <div className="text-sm text-gray-500">Squad Size (15+3)</div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Top Predicted Players</h2>
            <Link to="/players" className="text-primary-600 text-sm hover:underline">
              View All
            </Link>
          </div>
          {topPlayers.length > 0 ? (
            <table className="w-full">
              <thead>
                <tr className="text-left text-gray-500 text-sm">
                  <th className="pb-2">Player</th>
                  <th className="pb-2">Position</th>
                  <th className="pb-2">Predicted</th>
                </tr>
              </thead>
              <tbody>
                {topPlayers.map((player) => (
                  <tr key={player.id} className="border-t">
                    <td className="py-2 font-medium">{player.name}</td>
                    <td className="py-2 text-gray-500">{player.fantasy_position}</td>
                    <td className="py-2 font-semibold text-primary-600">
                      {player.predicted_points?.toFixed(1) || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-gray-500">No players available yet</p>
          )}
        </div>

        {availablePlayers.length > 0 && (
          <PositionDistribution players={availablePlayers} />
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link
          to="/players"
          className="card hover:shadow-lg transition-shadow group"
        >
          <h3 className="font-semibold group-hover:text-primary-600">
            Browse Players
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            View all available players and their stats
          </p>
        </Link>
        <Link
          to="/optimiser"
          className="card hover:shadow-lg transition-shadow group"
        >
          <h3 className="font-semibold group-hover:text-primary-600">
            Run Optimiser
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Generate optimal team within budget
          </p>
        </Link>
        <Link
          to="/team-builder"
          className="card hover:shadow-lg transition-shadow group"
        >
          <h3 className="font-semibold group-hover:text-primary-600">
            Build Team
          </h3>
          <p className="text-sm text-gray-500 mt-1">
            Manually select your fantasy team
          </p>
        </Link>
      </div>
    </div>
  );
}
