import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { HistoricalTelemetry } from '../types/history'

export function TemperatureChart({ telemetry }: { telemetry: HistoricalTelemetry[] }) {
  const data = telemetry.map((item) => ({
    ...item,
    time: new Date(item.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
  }))

  if (data.length === 0) return <div className="history-empty">No telemetry recorded for this trip.</div>

  return (
    <div className="temperature-chart">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 18, left: -12, bottom: 8 }}>
          <CartesianGrid stroke="#d8e1dc" strokeDasharray="3 3" />
          <XAxis dataKey="time" minTickGap={32} tick={{ fill: '#708080', fontSize: 11 }} />
          <YAxis unit="°" tick={{ fill: '#708080', fontSize: 11 }} />
          <Tooltip
            labelFormatter={(label) => `Recorded ${label}`}
            formatter={(value: unknown) => [`${typeof value === 'number' ? value : '—'}°`, 'Temperature']}
          />
          <Line type="monotone" dataKey="temperature" stroke="#0f6c68" strokeWidth={2.5} dot={false} activeDot={{ r: 4 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}