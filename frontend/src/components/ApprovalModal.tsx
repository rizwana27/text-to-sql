import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface Props {
  sql: string
  reason: string
  onApprove: () => void
  onReject: () => void
}

const CONFIRM_WORD = 'CONFIRM'

export default function ApprovalModal({ sql, reason, onApprove, onReject }: Props) {
  const [input, setInput] = useState('')
  const confirmed = input.trim() === CONFIRM_WORD

  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      background: 'rgba(0,0,0,0.8)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: '20px',
    }}>
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--accent-yellow)',
        borderRadius: '10px',
        padding: '24px',
        maxWidth: '700px',
        width: '100%',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
        boxShadow: '0 0 40px rgba(255,184,108,0.15)',
      }}>
        {/* Title */}
        <div style={{
          fontFamily: 'var(--font-mono)',
          fontSize: '14px',
          fontWeight: 700,
          color: 'var(--accent-yellow)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}>
          <span>⚠</span>
          <span>Human Approval Required</span>
        </div>

        {/* Reason */}
        <div style={{
          background: 'rgba(255,184,108,0.08)',
          border: '1px solid rgba(255,184,108,0.3)',
          borderRadius: '6px',
          padding: '10px 12px',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
          color: 'var(--accent-yellow)',
        }}>
          {reason || 'This SQL statement requires explicit approval before execution.'}
        </div>

        {/* SQL preview */}
        <div style={{ borderRadius: '6px', overflow: 'hidden', border: '1px solid var(--border-color)' }}>
          <SyntaxHighlighter
            language="sql"
            style={vscDarkPlus}
            customStyle={{
              margin: 0,
              padding: '12px 16px',
              background: 'var(--bg-primary)',
              fontSize: '12px',
              maxHeight: '200px',
              overflowY: 'auto',
            }}
          >
            {sql}
          </SyntaxHighlighter>
        </div>

        {/* Confirm input */}
        <div>
          <div style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
            color: 'var(--text-secondary)',
            marginBottom: '8px',
          }}>
            Type <span style={{ color: 'var(--accent-yellow)', fontWeight: 700 }}>{CONFIRM_WORD}</span> to execute this statement:
          </div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={`Type ${CONFIRM_WORD} to proceed`}
            autoFocus
            style={{
              width: '100%',
              background: 'var(--bg-tertiary)',
              border: `1px solid ${confirmed ? 'var(--accent-green)' : 'var(--border-color)'}`,
              borderRadius: '6px',
              padding: '10px 12px',
              color: confirmed ? 'var(--accent-green)' : 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '14px',
              outline: 'none',
              transition: 'border-color 0.15s',
            }}
          />
        </div>

        {/* Buttons */}
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button
            onClick={onReject}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '8px 20px',
              color: 'var(--text-secondary)',
              fontSize: '13px',
              fontFamily: 'var(--font-sans)',
              transition: 'all 0.15s',
            }}
          >
            Cancel
          </button>
          <button
            onClick={onApprove}
            disabled={!confirmed}
            style={{
              background: confirmed ? 'var(--accent-yellow)' : 'var(--bg-tertiary)',
              border: 'none',
              borderRadius: '6px',
              padding: '8px 20px',
              color: confirmed ? '#0d1117' : 'var(--text-secondary)',
              fontSize: '13px',
              fontWeight: 600,
              fontFamily: 'var(--font-sans)',
              transition: 'all 0.15s',
              cursor: confirmed ? 'pointer' : 'not-allowed',
            }}
          >
            Execute Query
          </button>
        </div>
      </div>
    </div>
  )
}
