import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface DataPoint {
  label: string;
  value: number;
}

interface FormChartProps {
  data: DataPoint[];
  title?: string;
  color?: string;
}

export function FormChart({ data, title, color = '#6366f1' }: FormChartProps) {
  return (
    <div className="card">
      {title && <h3 className="font-semibold mb-4 text-slate-800">{title}</h3>}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: '#64748b' }} />
            <YAxis tick={{ fontSize: 12, fill: '#64748b' }} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={{ fill: color }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
