import { useState, useEffect } from 'react'
import { getHistory, type HistoryItem } from '../api'

interface Props {
  onSelect: (question: string) => void
}

export default function QueryHistory({ onSelect }: Props) {
  const [items, setItems] = useState<HistoryItem[]>([])
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    getHistory().then(setItems).catch(() => {})
  }, [])

  return (
    <div style={{
      width: collapsed ? '36px' : '240px',
      minWidth: collapsed ? '36px' : '240px',
      borderRight: '1px solid var(--border-color)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      transition: 'width 0.2s, min-width 0.2s',
      background: 'var(--bg-secondary)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        padding: collapsed ? '12px 0' : '10px 12px',
        borderBottom: '1px solid var(--border-color)',
        flexShrink: 0,
      }}>
        {!collapsed && (
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
          }}>
            History
          </span>
        )}
        <button
          onClick={() => setCollapsed((c) => !c)}
          title={collapsed ? 'Expand history' : 'Collapse history'}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--text-secondary)',
            fontSize: '14px',
            padding: '2px 4px',
            lineHeight: 1,
          }}
        >
          {collapsed ? '›' : '‹'}
        </button>
      </div>

      {/* Items */}
      {!collapsed && (
        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {items.length === 0 && (
            <div style={{
              padding: '16px 12px',
              color: 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              textAlign: 'center',
            }}>
              No history yet
            </div>
          )}
          {items.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelect(item.question)}
              title={item.question}
              style={{
                display: 'block',
                width: '100%',
                textAlign: 'left',
                background: 'none',
                border: 'none',
                borderBottom: '1px solid var(--border-color)',
                padding: '8px 12px',
                cursor: 'pointer',
                color: 'var(--text-primary)',
                fontFamily: 'var(--font-mono)',
                fontSize: '11px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-tertiary)')}
              onMouseLeave={(e) => (e.currentTarget.style.background = 'none')}
            >
              <div style={{
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
                color: 'var(--text-primary)',
                marginBottom: '2px',
              }}>
                {item.question}
              </div>
              <div style={{ color: 'var(--text-secondary)', fontSize: '10px' }}>
                {item.latency_ms != null ? `${item.latency_ms}ms` : ''} · {item.created_at.slice(0, 10)}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
