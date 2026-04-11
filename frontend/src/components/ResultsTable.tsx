import { useState } from 'react'

interface Props {
  results: Record<string, unknown>[]
}

type SortDir = 'asc' | 'desc'

export default function ResultsTable({ results }: Props) {
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  if (!results || results.length === 0) return null

  const columns = Object.keys(results[0])

  const handleSort = (col: string) => {
    if (sortCol === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(col)
      setSortDir('asc')
    }
  }

  const sorted = [...results].sort((a, b) => {
    if (!sortCol) return 0
    const av = a[sortCol]
    const bv = b[sortCol]
    if (av === null || av === undefined) return 1
    if (bv === null || bv === undefined) return -1
    if (typeof av === 'number' && typeof bv === 'number') {
      return sortDir === 'asc' ? av - bv : bv - av
    }
    return sortDir === 'asc'
      ? String(av).localeCompare(String(bv))
      : String(bv).localeCompare(String(av))
  })

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* Header bar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        padding: '8px 12px',
        background: 'var(--bg-tertiary)',
        borderBottom: '1px solid var(--border-color)',
        fontFamily: 'var(--font-mono)',
        fontSize: '11px',
        color: 'var(--text-secondary)',
        gap: '8px',
      }}>
        <span style={{ color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
          Results
        </span>
        <span>·</span>
        <span>{results.length} row{results.length !== 1 ? 's' : ''}</span>
        <span>·</span>
        <span>{columns.length} column{columns.length !== 1 ? 's' : ''}</span>
      </div>

      {/* Scrollable table */}
      <div style={{ overflowX: 'auto', maxHeight: '400px', overflowY: 'auto' }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
        }}>
          <thead>
            <tr style={{ position: 'sticky', top: 0, background: 'var(--bg-tertiary)', zIndex: 1 }}>
              {columns.map((col) => (
                <th
                  key={col}
                  onClick={() => handleSort(col)}
                  style={{
                    padding: '8px 12px',
                    textAlign: 'left',
                    color: sortCol === col ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                    borderBottom: '1px solid var(--border-color)',
                    cursor: 'pointer',
                    userSelect: 'none',
                    fontSize: '11px',
                  }}
                >
                  {col}
                  {sortCol === col && (
                    <span style={{ marginLeft: '4px' }}>{sortDir === 'asc' ? '↑' : '↓'}</span>
                  )}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr
                key={i}
                style={{
                  background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
                }}
              >
                {columns.map((col) => {
                  const val = row[col]
                  const isNum = typeof val === 'number'
                  const isNull = val === null || val === undefined
                  return (
                    <td
                      key={col}
                      style={{
                        padding: '7px 12px',
                        borderBottom: '1px solid rgba(48,54,61,0.5)',
                        color: isNull
                          ? 'var(--text-secondary)'
                          : isNum
                          ? 'var(--accent-cyan)'
                          : 'var(--text-primary)',
                        fontStyle: isNull ? 'italic' : 'normal',
                        whiteSpace: 'nowrap',
                        maxWidth: '300px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                      title={isNull ? 'NULL' : String(val)}
                    >
                      {isNull ? 'NULL' : String(val)}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
