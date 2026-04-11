import { useState, useEffect } from 'react'
import ChatWindow from './components/ChatWindow'
import SchemaExplorer from './components/SchemaExplorer'
import ApprovalModal from './components/ApprovalModal'
import { getSchema, postApprove, type SchemaTable, type QueryResponse } from './api'

export interface Message {
  id: string
  type: 'question' | 'answer' | 'error'
  content: QueryResponse | string
  timestamp: Date
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [schema, setSchema] = useState<SchemaTable[]>([])
  const [activeTables, setActiveTables] = useState<string[]>([])
  const [pendingApproval, setPendingApproval] = useState<QueryResponse | null>(null)

  useEffect(() => {
    getSchema()
      .then(setSchema)
      .catch((err) => console.error('Failed to load schema:', err))
  }, [])

  const handleAnswer = (response: QueryResponse) => {
    if (response.requires_approval) {
      setPendingApproval(response)
    }
    setActiveTables(response.tables_used)
    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        type: 'answer',
        content: response,
        timestamp: new Date(),
      },
    ])
  }

  const handleApprove = async (approved: boolean) => {
    if (!pendingApproval) return
    try {
      const result = await postApprove(pendingApproval.sql, approved)
      const updatedResponse: QueryResponse = {
        ...pendingApproval,
        results: result.results,
        requires_approval: false,
      }
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          type: 'answer',
          content: updatedResponse,
          timestamp: new Date(),
        },
      ])
    } catch (err) {
      console.error('Approval failed:', err)
    } finally {
      setPendingApproval(null)
    }
  }

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      overflow: 'hidden',
      background: 'var(--bg-primary)',
    }}>
      {/* Sidebar */}
      <div style={{
        width: '280px',
        minWidth: '280px',
        borderRight: '1px solid var(--border-color)',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
      }}>
        <div style={{
          padding: '16px',
          borderBottom: '1px solid var(--border-color)',
          fontFamily: 'var(--font-mono)',
          color: 'var(--accent-green)',
          fontSize: '14px',
          fontWeight: 700,
          letterSpacing: '0.05em',
        }}>
          ⚡ TEXT-TO-SQL
        </div>
        <SchemaExplorer schema={schema} activeTables={activeTables} />
      </div>

      {/* Main area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        <ChatWindow
          messages={messages}
          setMessages={setMessages}
          onAnswer={handleAnswer}
        />
      </div>

      {/* Approval modal */}
      {pendingApproval && (
        <ApprovalModal
          sql={pendingApproval.sql}
          reason={pendingApproval.approval_reason || ''}
          onApprove={() => handleApprove(true)}
          onReject={() => {
            setPendingApproval(null)
          }}
        />
      )}
    </div>
  )
}
