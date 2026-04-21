import {
  BarChart, Bar, LineChart, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import type { ChartInfo } from '../api'

interface Props {
  results: Record<string, unknown>[]
  chart: ChartInfo
}

export default function ChartDisplay({ results, chart }: Props) {
  if (chart.type === 'none' || !chart.x_col || !chart.y_col) return null

  const data = results.slice(0, 50).map((row) => ({
    x: String(row[chart.x_col!] ?? ''),
    y: Number(row[chart.y_col!] ?? 0),
  }))

  const axisStyle = { fill: 'var(--text-secondary)', fontSize: 11, fontFamily: 'var(--font-mono)' }
  const common = {
    data,
    margin: { top: 8, right: 16, left: 0, bottom: 40 },
  }

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      padding: '16px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: 'var(--text-secondary)',
        marginBottom: '12px',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
      }}>
        {chart.type} chart · {chart.x_col} vs {chart.y_col}
      </div>
      <ResponsiveContainer width="100%" height={240}>
        {chart.type === 'line' ? (
          <LineChart {...common}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis dataKey="x" tick={axisStyle} angle={-35} textAnchor="end" interval="preserveStartEnd" />
            <YAxis tick={axisStyle} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}
              labelStyle={{ color: 'var(--text-secondary)' }}
              itemStyle={{ color: 'var(--accent-cyan)' }}
            />
            <Line type="monotone" dataKey="y" stroke="var(--accent-cyan)" strokeWidth={2} dot={false} />
          </LineChart>
        ) : (
          <BarChart {...common}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis dataKey="x" tick={axisStyle} angle={-35} textAnchor="end" interval={0} />
            <YAxis tick={axisStyle} />
            <Tooltip
              contentStyle={{ background: 'var(--bg-tertiary)', border: '1px solid var(--border-color)', borderRadius: 6, fontFamily: 'var(--font-mono)', fontSize: 12 }}
              labelStyle={{ color: 'var(--text-secondary)' }}
              itemStyle={{ color: 'var(--accent-green)' }}
            />
            <Bar dataKey="y" fill="var(--accent-green)" radius={[3, 3, 0, 0]} />
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  )
}
