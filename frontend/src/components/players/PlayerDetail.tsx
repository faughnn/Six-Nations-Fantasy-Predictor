import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { PlayerDetail as PlayerDetailType } from '../../types';
import { CountryFlag } from '../common/CountryFlag';
import { formatPrice, formatPoints, getPositionLabel } from '../../utils';

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
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center p-4 z-50">
      <div className="bg-white rounded-2xl max-w-4xl w-full max-h-[90vh] overflow-y-auto border border-slate-200 shadow-xl">
        <div className="p-6">
          <div className="flex justify-between items-start mb-6">
            <div>
              <h2 className="text-2xl font-bold text-slate-800 flex items-center gap-2">
                <CountryFlag country={player.country} size="lg" />
                {player.name}
              </h2>
              <p className="text-slate-400 mt-0.5">
                {getPositionLabel(player.fantasy_position)} | {player.country}
                {player.club && ` | ${player.club}`}
              </p>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="w-8 h-8 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>

          <div className="grid grid-cols-4 gap-3 mb-6">
            <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
              <div className="text-2xl font-bold text-primary-600 tabular-nums">
                {formatPrice(player.price)}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">Price</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
              <div className="text-2xl font-bold text-emerald-600 tabular-nums">
                {formatPoints(player.predicted_points)}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">Predicted</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
              <div className="text-2xl font-bold text-primary-500 tabular-nums">
                {formatPoints(player.points_per_star)}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">Value</div>
            </div>
            <div className="bg-slate-50 rounded-xl p-3 text-center border border-slate-100">
              <div className="text-2xl font-bold text-slate-700">
                {player.is_kicker ? 'Yes' : 'No'}
              </div>
              <div className="text-xs text-slate-400 mt-0.5">Kicker</div>
            </div>
          </div>

          {chartData.length > 0 && (
            <div className="card mb-6" data-testid="form-chart">
              <h3 className="font-semibold mb-4 text-slate-700">Recent Form</h3>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748b' }} />
                    <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="points"
                      stroke="#6366f1"
                      strokeWidth={2}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-6">
            <div className="card">
              <h3 className="font-semibold mb-3 text-slate-700">Six Nations Stats</h3>
              {player.six_nations_stats.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-400 text-xs uppercase">
                      <th className="pb-2">vs</th>
                      <th className="pb-2">Pts</th>
                      <th className="pb-2">Tries</th>
                      <th className="pb-2">Tackles</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.six_nations_stats.slice(-5).map((stat, i) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="py-2 text-slate-700">{stat.opponent}</td>
                        <td className="tabular-nums">{formatPoints(stat.fantasy_points)}</td>
                        <td className="tabular-nums">{stat.tries}</td>
                        <td className="tabular-nums">{stat.tackles_made}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-slate-400 text-sm">No Six Nations stats available</p>
              )}
            </div>

            <div className="card">
              <h3 className="font-semibold mb-3 text-slate-700">Club Stats</h3>
              {player.club_stats.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-slate-400 text-xs uppercase">
                      <th className="pb-2">vs</th>
                      <th className="pb-2">Tries</th>
                      <th className="pb-2">Tackles</th>
                      <th className="pb-2">Metres</th>
                    </tr>
                  </thead>
                  <tbody>
                    {player.club_stats.slice(-5).map((stat, i) => (
                      <tr key={i} className="border-t border-slate-100">
                        <td className="py-2 text-slate-700">{stat.opponent}</td>
                        <td className="tabular-nums">{stat.tries}</td>
                        <td className="tabular-nums">{stat.tackles_made}</td>
                        <td className="tabular-nums">{stat.metres_carried}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-slate-400 text-sm">No club stats available</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
