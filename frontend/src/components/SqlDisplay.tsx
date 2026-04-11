import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface Props {
  sql: string
  latencyMs: number
  requiresApproval: boolean
  approvalReason?: string
}

export default function SqlDisplay({ sql, latencyMs, requiresApproval, approvalReason }: Props) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    })
  }

  return (
    <div style={{
      background: 'var(--bg-secondary)',
      border: `1px solid ${requiresApproval ? 'var(--accent-yellow)' : 'var(--border-color)'}`,
      borderRadius: '8px',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '8px 12px',
        background: 'var(--bg-tertiary)',
        borderBottom: '1px solid var(--border-color)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--accent-green)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
          }}>
            SQL
          </span>
          {requiresApproval && (
            <span style={{
              background: 'rgba(255,184,108,0.15)',
              color: 'var(--accent-yellow)',
              border: '1px solid var(--accent-yellow)',
              borderRadius: '4px',
              padding: '1px 6px',
              fontSize: '10px',
              fontFamily: 'var(--font-mono)',
            }}>
              ⚠ APPROVAL REQUIRED
            </span>
          )}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{
            fontFamily: 'var(--font-mono)',
            fontSize: '11px',
            color: 'var(--text-secondary)',
          }}>
            {latencyMs}ms
          </span>
          <button
            onClick={handleCopy}
            style={{
              background: 'transparent',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              padding: '2px 8px',
              fontSize: '11px',
              color: copied ? 'var(--accent-green)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-mono)',
              transition: 'all 0.15s',
            }}
          >
            {copied ? '✓ copied' : 'copy'}
          </button>
        </div>
      </div>

      {/* SQL code */}
      <div style={{ fontSize: '12px', lineHeight: 1.6 }}>
        <SyntaxHighlighter
          language="sql"
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '12px 16px',
            background: 'var(--bg-secondary)',
            fontSize: '12px',
          }}
        >
          {sql}
        </SyntaxHighlighter>
      </div>

      {/* Approval reason */}
      {requiresApproval && approvalReason && (
        <div style={{
          padding: '8px 12px',
          borderTop: '1px solid var(--border-color)',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          color: 'var(--accent-yellow)',
          background: 'rgba(255,184,108,0.05)',
        }}>
          Reason: {approvalReason}
        </div>
      )}
    </div>
  )
}
