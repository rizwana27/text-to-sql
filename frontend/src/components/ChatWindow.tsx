import { useState, useRef, useEffect } from 'react'
import { postQuery, type QueryResponse } from '../api'
import SqlDisplay from './SqlDisplay'
import ResultsTable from './ResultsTable'
import type { Message } from '../App'

interface Props {
  messages: Message[]
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>
  onAnswer: (response: QueryResponse) => void
}

export default function ChatWindow({ messages, setMessages, onAnswer }: Props) {
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async () => {
    const q = question.trim()
    if (!q || loading) return

    const questionMsg: Message = {
      id: crypto.randomUUID(),
      type: 'question',
      content: q,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, questionMsg])
    setQuestion('')
    setLoading(true)

    try {
      const response = await postQuery(q)
      onAnswer(response)
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err)
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), type: 'error', content: errMsg, timestamp: new Date() },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Message history */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: '16px',
      }}>
        {messages.length === 0 && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            gap: '8px',
          }}>
            <div style={{ fontSize: '32px' }}>🔍</div>
            <div>Ask a question about your Olist data</div>
            <div style={{ fontSize: '11px', opacity: 0.6 }}>e.g. "What is the total revenue by product category?"</div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id}>
            {msg.type === 'question' && (
              <div style={{
                display: 'flex',
                justifyContent: 'flex-end',
              }}>
                <div style={{
                  background: 'var(--bg-tertiary)',
                  border: '1px solid var(--accent-cyan)',
                  borderRadius: '8px 8px 2px 8px',
                  padding: '10px 14px',
                  maxWidth: '70%',
                  fontFamily: 'var(--font-mono)',
                  fontSize: '13px',
                  color: 'var(--accent-cyan)',
                }}>
                  {msg.content as string}
                </div>
              </div>
            )}

            {msg.type === 'answer' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {(() => {
                  const r = msg.content as QueryResponse
                  return (
                    <>
                      <SqlDisplay
                        sql={r.sql}
                        latencyMs={r.latency_ms}
                        requiresApproval={r.requires_approval}
                        approvalReason={r.approval_reason}
                      />
                      {r.results.length > 0 && <ResultsTable results={r.results} />}
                      {r.results.length === 0 && !r.requires_approval && (
                        <div style={{
                          color: 'var(--text-secondary)',
                          fontFamily: 'var(--font-mono)',
                          fontSize: '12px',
                          padding: '8px 12px',
                        }}>
                          No results returned.
                        </div>
                      )}
                    </>
                  )
                })()}
              </div>
            )}

            {msg.type === 'error' && (
              <div style={{
                background: 'rgba(255,85,85,0.1)',
                border: '1px solid var(--accent-red)',
                borderRadius: '6px',
                padding: '10px 14px',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
                color: 'var(--accent-red)',
              }}>
                ⚠ {msg.content as string}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            color: 'var(--text-secondary)',
            fontFamily: 'var(--font-mono)',
            fontSize: '12px',
          }}>
            <span style={{ animation: 'pulse 1.2s infinite' }}>⬤</span>
            <span>Generating SQL...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input area */}
      <div style={{
        borderTop: '1px solid var(--border-color)',
        padding: '16px',
        background: 'var(--bg-secondary)',
      }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-end' }}>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about your data... (Enter to send, Shift+Enter for newline)"
            disabled={loading}
            style={{
              flex: 1,
              background: 'var(--bg-tertiary)',
              border: '1px solid var(--border-color)',
              borderRadius: '6px',
              padding: '10px 12px',
              color: 'var(--text-primary)',
              fontFamily: 'var(--font-mono)',
              fontSize: '13px',
              resize: 'none',
              minHeight: '44px',
              maxHeight: '120px',
              outline: 'none',
              lineHeight: 1.5,
            }}
            rows={1}
          />
          <button
            onClick={handleSubmit}
            disabled={loading || !question.trim()}
            style={{
              background: loading || !question.trim() ? 'var(--bg-tertiary)' : 'var(--accent-green)',
              color: loading || !question.trim() ? 'var(--text-secondary)' : '#0d1117',
              border: 'none',
              borderRadius: '6px',
              padding: '10px 18px',
              fontWeight: 600,
              fontSize: '13px',
              transition: 'all 0.15s',
              whiteSpace: 'nowrap',
            }}
          >
            {loading ? '...' : 'Run ↵'}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  )
}
