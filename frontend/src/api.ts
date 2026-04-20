import axios from 'axios'

const api = axios.create({ baseURL: '/' })

export interface QueryResponse {
  sql: string
  results: Record<string, unknown>[]
  tables_used: string[]
  requires_approval: boolean
  approval_reason?: string
  latency_ms: number
}

export interface ApproveResponse {
  executed: boolean
  results: Record<string, unknown>[]
  message: string
}

export interface SchemaColumn {
  name: string
  description: string
}

export interface SchemaTable {
  table_name: string
  description: string
  columns: SchemaColumn[]
}

export async function postQuery(question: string): Promise<QueryResponse> {
  const { data } = await api.post<QueryResponse>('/api/query', { question })
  return data
}

export async function postApprove(sql: string, approved: boolean): Promise<ApproveResponse> {
  const { data } = await api.post<ApproveResponse>('/api/approve', { sql, approved })
  return data
}

export async function getSchema(): Promise<SchemaTable[]> {
  const { data } = await api.get<SchemaTable[]>('/api/schema')
  return data
}

export async function getHealth(): Promise<Record<string, unknown>> {
  const { data } = await api.get<Record<string, unknown>>('/api/health')
  return data
}

export interface EvalResult {
  question_id: number
  question: string
  expected_sql: string
  generated_sql: string
  passed: boolean
  latency_ms: number
  error: string | null
}

export interface EvalSummary {
  run_id: string
  total_questions: number
  passed: number
  failed: number
  accuracy_pct: number
  avg_latency_ms: number
  results: EvalResult[]
}

export async function postEval(): Promise<EvalSummary> {
  const { data } = await api.post<EvalSummary>('/api/eval')
  return data
}

export async function getEvalMeta(): Promise<{ total_questions: number }> {
  const { data } = await api.get<{ total_questions: number }>('/api/eval/meta')
  return data
}
