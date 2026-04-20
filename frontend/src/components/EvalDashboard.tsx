import { useState, useEffect, Fragment } from 'react'
import { postEval, getEvalMeta, type EvalSummary } from '../api'

export default function EvalDashboard() {
  const [loading, setLoading] = useState(false)
  const [summary, setSummary] = useState<EvalSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [expandedSql, setExpandedSql] = useState<number | null>(null)
  const [totalQuestions, setTotalQuestions] = useState<number | null>(null)

  useEffect(() => {
    getEvalMeta().then((m) => setTotalQuestions(m.total_questions)).catch(() => {})
  }, [])

  const handleRunEval = async () => {
    setLoading(true)
    setError(null)
    setSummary(null)
    try {
      const result = await postEval()
      setSummary(result)
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Evaluation failed'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      overflow: 'auto',
      padding: '24px',
      gap: '20px',
      fontFamily: 'var(--font-sans)',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{
            margin: 0,
            fontSize: '18px',
            fontWeight: 700,
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-mono)',
          }}>
            SQL Evaluation Dashboard
          </h2>
          <p style={{ margin: '4px 0 0', fontSize: '13px', color: 'var(--text-secondary)' }}>
            Runs the golden test set through the LLM pipeline and compares execution results.
          </p>
        </div>
        <button
          onClick={handleRunEval}
          disabled={loading}
          style={{
            padding: '10px 20px',
            background: loading ? 'var(--bg-tertiary)' : 'var(--accent-green)',
            color: loading ? 'var(--text-secondary)' : '#0d1117',
            border: 'none',
            borderRadius: '6px',
            fontFamily: 'var(--font-mono)',
            fontSize: '13px',
            fontWeight: 700,
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'opacity 0.15s',
            whiteSpace: 'nowrap',
          }}
        >
          {loading ? '⏳ Running…' : '▶ Run Evaluation'}
        </button>
      </div>

      {/* Error state */}
      {error && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(255,85,85,0.1)',
          border: '1px solid var(--accent-red)',
          borderRadius: '8px',
          color: 'var(--accent-red)',
          fontFamily: 'var(--font-mono)',
          fontSize: '13px',
        }}>
          {error}
        </div>
      )}

      {/* Loading spinner */}
      {loading && (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
          padding: '40px',
          color: 'var(--text-secondary)',
          fontSize: '14px',
        }}>
          <div style={{
            width: '32px',
            height: '32px',
            border: '3px solid var(--border-color)',
            borderTopColor: 'var(--accent-green)',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
          }} />
          Running {totalQuestions ?? '…'} questions through the LLM pipeline…
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* Summary cards */}
      {summary && (
        <>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            <SummaryCard
              label="Accuracy"
              value={`${summary.accuracy_pct}%`}
              color={summary.accuracy_pct >= 80 ? 'var(--accent-green)' : summary.accuracy_pct >= 50 ? 'var(--accent-yellow)' : 'var(--accent-red)'}
            />
            <SummaryCard label="Passed" value={String(summary.passed)} color="var(--accent-green)" />
            <SummaryCard label="Failed" value={String(summary.failed)} color="var(--accent-red)" />
            <SummaryCard label="Avg Latency" value={`${summary.avg_latency_ms} ms`} color="var(--accent-cyan)" />
            <SummaryCard label="Run ID" value={summary.run_id.slice(0, 8) + '…'} color="var(--text-secondary)" />
          </div>

          {/* Per-question table */}
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border-color)',
            borderRadius: '8px',
            overflow: 'hidden',
          }}>
            {/* Table header bar */}
            <div style={{
              padding: '8px 16px',
              background: 'var(--bg-tertiary)',
              borderBottom: '1px solid var(--border-color)',
              fontFamily: 'var(--font-mono)',
              fontSize: '11px',
              color: 'var(--text-secondary)',
              display: 'flex',
              gap: '8px',
              alignItems: 'center',
            }}>
              <span style={{ color: 'var(--accent-cyan)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                Results
              </span>
              <span>·</span>
              <span>{summary.total_questions} questions</span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table style={{
                width: '100%',
                borderCollapse: 'collapse',
                fontFamily: 'var(--font-mono)',
                fontSize: '12px',
              }}>
                <thead>
                  <tr style={{ background: 'var(--bg-tertiary)' }}>
                    {['#', 'Question', 'Generated SQL', 'Pass/Fail', 'Latency'].map((col) => (
                      <th key={col} style={{
                        padding: '8px 12px',
                        textAlign: 'left',
                        color: 'var(--text-secondary)',
                        fontWeight: 600,
                        fontSize: '11px',
                        borderBottom: '1px solid var(--border-color)',
                        whiteSpace: 'nowrap',
                      }}>
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {summary.results.map((r, i) => (
                    <Fragment key={r.question_id}>
                      <tr style={{ background: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)' }}>
                        <td style={{ padding: '8px 12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                          {r.question_id}
                        </td>
                        <td style={{ padding: '8px 12px', color: 'var(--text-primary)', maxWidth: '320px' }}>
                          {r.question}
                        </td>
                        <td style={{ padding: '8px 12px', maxWidth: '260px' }}>
                          {r.generated_sql ? (
                            <code style={{
                              display: 'block',
                              color: 'var(--accent-cyan)',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: expandedSql === r.question_id ? 'pre-wrap' : 'nowrap',
                              maxWidth: '260px',
                              fontSize: '11px',
                              cursor: 'pointer',
                            }}
                              onClick={() => setExpandedSql(expandedSql === r.question_id ? null : r.question_id)}
                              title="Click to expand"
                            >
                              {r.generated_sql}
                            </code>
                          ) : (
                            <span style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>—</span>
                          )}
                        </td>
                        <td style={{ padding: '8px 12px', whiteSpace: 'nowrap' }}>
                          <span style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            fontSize: '11px',
                            fontWeight: 700,
                            background: r.passed ? 'rgba(0,255,136,0.12)' : 'rgba(255,85,85,0.12)',
                            color: r.passed ? 'var(--accent-green)' : 'var(--accent-red)',
                            border: `1px solid ${r.passed ? 'rgba(0,255,136,0.3)' : 'rgba(255,85,85,0.3)'}`,
                          }}>
                            {r.passed ? '✓ PASS' : '✗ FAIL'}
                          </span>
                        </td>
                        <td style={{ padding: '8px 12px', color: 'var(--accent-cyan)', whiteSpace: 'nowrap' }}>
                          {r.latency_ms > 0 ? `${r.latency_ms} ms` : '—'}
                        </td>
                      </tr>
                      {r.error && (
                        <tr style={{ background: 'rgba(255,85,85,0.04)' }}>
                          <td colSpan={5} style={{
                            padding: '4px 12px 8px 36px',
                            color: 'var(--accent-red)',
                            fontSize: '11px',
                            fontFamily: 'var(--font-mono)',
                          }}>
                            ⚠ {r.error}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* Empty state */}
      {!loading && !summary && !error && (
        <div style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          color: 'var(--text-secondary)',
          fontSize: '14px',
        }}>
          <span style={{ fontSize: '40px' }}>📊</span>
          <p style={{ margin: 0 }}>Click <strong style={{ color: 'var(--accent-green)' }}>Run Evaluation</strong> to test the pipeline against the golden set.</p>
          <p style={{ margin: 0, fontSize: '12px' }}>{totalQuestions ?? '…'} questions · execution accuracy · latency tracking</p>
        </div>
      )}
    </div>
  )
}

function SummaryCard({
  label,
  value,
  color,
}: {
  label: string
  value: string
  color: string
}) {
  return (
    <div style={{
      padding: '14px 20px',
      background: 'var(--bg-secondary)',
      border: '1px solid var(--border-color)',
      borderRadius: '8px',
      minWidth: '120px',
    }}>
      <div style={{ fontSize: '11px', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.06em' }}>
        {label}
      </div>
      <div style={{ fontSize: '22px', fontWeight: 700, color, fontFamily: 'var(--font-mono)' }}>
        {value}
      </div>
    </div>
  )
}
