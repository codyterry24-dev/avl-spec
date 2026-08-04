import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL!
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

export type Database = {
  public: {
    Tables: {
      ai_audit_events: {
        Row: AuditEvent
        Insert: Omit<AuditEvent, 'id' | 'created_at'>
        Update: Partial<AuditEvent>
      }
      ai_flagged_incidents: {
        Row: FlaggedIncident
        Insert: Omit<FlaggedIncident, 'id' | 'created_at'>
        Update: Partial<FlaggedIncident>
      }
    }
  }
}

export interface AuditEvent {
  id: string
  event_id: string
  timestamp: string
  event_type: string
  system_id: string
  environment: string
  model_provider: string
  model_id: string
  model_version: string | null
  temperature: number | null
  user_id: string | null
  session_id: string | null
  user_prompt: string | null
  response: string | null
  tokens_prompt: number | null
  tokens_completion: number | null
  latency_ms: number | null
  guardrail_event: string | null
  guardrail_action: string | null
  pii_detected: boolean
  content_filtered: boolean
  policy_violations: string[] | null
  drift_score: number | null
  hallucination_risk: number | null
  toxicity_score: number | null
  jailbreak_confidence: number | null
  control_ids: string[] | null
  entry_hash: string | null
  prev_entry_hash: string | null
  schema_version: string
  inference_cost_usd: number | null
  raw_payload: Record<string, unknown>
  created_at: string
}

export interface FlaggedIncident {
  id: string
  event_id: string
  timestamp: string
  severity: 'critical' | 'warning'
  reason: string
  field_missing: string | null
  threshold_violated: string | null
  threshold_value: number | null
  actual_value: number | null
  resolved: boolean
  resolved_at: string | null
  notes: string | null
  created_at: string
}
