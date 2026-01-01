import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { PlayerDetail as PlayerDetailType } from '../../types';
import { formatPrice, formatPoints, getPositionLabel, getCountryFlag } from '../../utils';

interface PlayerDetailProps {
  player: PlayerDetailType;
  onClose?: () => void;
}

export function PlayerDetail({ player, onClose }: PlayerDetailProps) {
  const allStats = [...player.six_nations_stats, ...player.club_stats]
    .sort((a, b) => new Date(a.match_date).getTime() - new Date(b.match_date).getTime())
    .slice(-10);

  const chartData = allStats.map((stat) => ({
    date: new Date(stat.match_date).toLocaleDateString(),
    points: stat.fantasy_points || 0,
    tries: stat.tries,
    tackles: stat.tackles_made,
  }));

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold">
                {getCountryFlag(player.country)} {player.name}
              </h2>
              <p className="text-gray-500">
                {getPositionLabel(player.fantasy_position)} | {player.country}
                {player.club && ` | ${player.club}`}
              </p>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="text-gray-400 hover:text-gray-600"
              >
                Close
              </button>
            )}
          </div>

          <div className="grid grid-cols-4 gap-4 mb-6">
            <div className="card text-center">
              <div className="text-2xl font-bold text-primary-600">
                {formatPrice(player.price)}
              </div>
              <div className="text-sm text-gray-500">Price</div>
            </div>
            <div className="card text-center">
              <div className="text-2xl font-bold text-green-600">
                {formatPoints(player.predicted_points)}
              </div>
              <div className="text-sm text-gray-500">Predicted</div>
            </div>
            <div className="card text-center">
              <div className="text-2xl font-bold text-blue-600">
                {formatPoints(player.points_per_star)}
              </div>
              <div className="text-sm text-gray-500">Value</div>
            </div>
            <div className="card text-center">
              <div className="text-2xl font-bold">
                {player.is_kicker ? 'Yes' : 'No'}
              </div>
              <div className="text-sm text-gray-500">Kicker</div>
            </div>
          </div>

          {chartData.length > 0 && (
            <div className="card mb-6" data-testid="form-chart">
              <h3 className="font-semibold mb-4">Recent Form</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="points"
                      stroke="#0ea5e9"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold mb-3">Six Nations Stats</h3>
              {player.six_nations_stats.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500">
                      <th className="pb-2">vs</th>
                      <th className="pb-2">Pts</th>
                      <th className="pb-2">Tries</th>
                      <th className="pb-2">Tackles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.six_nations_stats.slice(-5).map((stat, i) => (
                      <tr key={i} className="border-t">
                        <td className="py-2">{stat.opponent}</td>
                        <td>{formatPoints(stat.fantasy_points)}</td>
                        <td>{stat.tries}</td>
                        <td>{stat.tackles_made}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-gray-500 text-sm">No Six Nations stats available</p>
              )}
            </div>

            <div className="card">
              <h3 className="font-semibold mb-3">Club Stats</h3>
              {player.club_stats.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-gray-500">
                      <th className="pb-2">vs</th>
                      <th className="pb-2">Tries</th>
                      <th className="pb-2">Tackles</th>
                      <th className="pb-2">Metres</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.club_stats.slice(-5).map((stat, i) => (
                      <tr key={i} className="border-t">
                        <td className="py-2">{stat.opponent}</td>
                        <td>{stat.tries}</td>
                        <td>{stat.tackles_made}</td>
                        <td>{stat.metres_carried}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-gray-500 text-sm">No club stats available</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
