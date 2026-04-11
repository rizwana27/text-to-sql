import { useState } from 'react'
import type { SchemaTable } from '../api'

interface Props {
  schema: SchemaTable[]
  activeTables: string[]
}

export default function SchemaExplorer({ schema, activeTables }: Props) {
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const toggle = (tableName: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(tableName)) next.delete(tableName)
      else next.add(tableName)
      return next
    })
  }

  return (
    <div style={{
      flex: 1,
      overflowY: 'auto',
      padding: '12px 8px',
    }}>
      <div style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        color: 'var(--text-secondary)',
        textTransform: 'uppercase',
        letterSpacing: '0.1em',
        padding: '0 4px',
        marginBottom: '8px',
      }}>
        Schema Explorer
      </div>

      {schema.length === 0 && (
        <div style={{
          color: 'var(--text-secondary)',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          padding: '8px 4px',
        }}>
          Loading schema...
        </div>
      )}

      {schema.map((table) => {
        const isActive = activeTables.includes(table.table_name)
        const isOpen = expanded.has(table.table_name)

        return (
          <div key={table.table_name} style={{ marginBottom: '4px' }}>
            {/* Table header */}
            <button
              onClick={() => toggle(table.table_name)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: isActive ? 'rgba(0,255,136,0.08)' : 'transparent',
                border: isActive ? '1px solid rgba(0,255,136,0.2)' : '1px solid transparent',
                borderRadius: '5px',
                padding: '6px 8px',
                color: isActive ? 'var(--accent-green)' : 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                textAlign: 'left',
                transition: 'all 0.1s',
              }}
            >
              <span style={{ fontSize: '9px', opacity: 0.6 }}>{isOpen ? '▼' : '▶'}</span>
              <span style={{ fontSize: '14px' }}>
                {table.table_name.startsWith('fact') ? '📊' : '📋'}
              </span>
              <span style={{ flex: 1 }}>{table.table_name}</span>
              {isActive && (
                <span style={{
                  width: '6px',
                  height: '6px',
                  background: 'var(--accent-green)',
                  borderRadius: '50%',
                  flexShrink: 0,
                }} />
              )}
            </button>

            {/* Columns list */}
            {isOpen && (
              <div style={{
                marginLeft: '16px',
                marginTop: '2px',
                borderLeft: '1px solid var(--border-color)',
                paddingLeft: '8px',
              }}>
                {table.columns.map((col) => (
                  <div
                    key={col.name}
                    style={{
                      padding: '3px 4px',
                      fontFamily: 'var(--font-mono)',
                      fontSize: '11px',
                    }}
                    title={col.description}
                  >
                    <span style={{ color: 'var(--accent-cyan)' }}>{col.name}</span>
                    <div style={{
                      color: 'var(--text-secondary)',
                      fontSize: '10px',
                      marginTop: '1px',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      maxWidth: '210px',
                    }}>
                      {col.description}
                    </div>
                  </div>
                ))}

                {/* Table description */}
                <div style={{
                  padding: '4px 4px 4px',
                  fontFamily: 'var(--font-sans)',
                  fontSize: '10px',
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                  borderTop: '1px solid var(--border-color)',
                  marginTop: '4px',
                }}>
                  {table.description}
                </div>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
