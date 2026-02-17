import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import type { PlayerSummary } from '../../types';
import { getPositionLabel } from '../../utils';

interface PositionDistributionProps {
  players: PlayerSummary[];
}

export function PositionDistribution({ players }: PositionDistributionProps) {
  const positionData = players.reduce((acc, player) => {
    const pos = player.fantasy_position;
    if (!acc[pos]) {
      acc[pos] = { count: 0, avgPoints: 0, totalPoints: 0 };
    }
    acc[pos].count += 1;
    acc[pos].totalPoints += player.predicted_points || 0;
    return acc;
  }, {} as Record<string, { count: number; avgPoints: number; totalPoints: number }>);

  const chartData = Object.entries(positionData).map(([position, data]) => ({
    position: getPositionLabel(position),
    avgPoints: data.count > 0 ? data.totalPoints / data.count : 0,
    count: data.count,
  }));

  return (
    <div className="card">
      <h3 className="font-semibold mb-4 text-slate-800">Average Points by Position</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="position" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
            <Tooltip />
            <Bar dataKey="avgPoints" fill="#6366f1" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
