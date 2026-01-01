import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface DataPoint {
  label: string;
  value: number;
}

interface FormChartProps {
  data: DataPoint[];
  title?: string;
  color?: string;
}

export function FormChart({ data, title, color = '#0ea5e9' }: FormChartProps) {
  return (
    <div className="card">
      {title && <h3 className="font-semibold mb-4">{title}</h3>}
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="label" />
            <YAxis />
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
