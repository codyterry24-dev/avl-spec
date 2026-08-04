'use client'
import { useEffect, useState, useCallback } from 'react'
import { supabase } from '@/lib/supabase'
import type { AuditEvent, FlaggedIncident } from '@/lib/supabase'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { AlertTriangle, CheckCircle, Shield, Activity, Eye, Download, RefreshCw, ChevronRight, X, Zap } from 'lucide-react'
import { format, subDays } from 'date-fns'

// ---- AXT Policy Thresholds (AVL-3) ----
const REQUIRED_FIELDS = ['model_version','guardrail_event','schema_version','control_ids','entry_hash','drift_score']
const THRESHOLDS = {
  drift_score: { max: 0.4, label: 'Drift Score', unit: '' },
  hallucination_risk: { max: 0.35, label: 'Hallucination Risk', unit: '' },
  toxicity_score: { max: 0.2, label: 'Toxicity Score', unit: '' },
  jailbreak_confidence: { max: 0.15, label: 'Jailbreak Confidence', unit: '' },
  latency_ms: { max: 3000, label: 'Latency', unit: 'ms' },
  inference_cost_usd: { max: 0.05, label: 'Inference Cost', unit: '$' },
}

const TABS = ['Overview','Coverage','Flagged Events','Policy Thresholds','Auditor Export'] as const
type Tab = typeof TABS[number]

function severityColor(s: string) {
  return s === 'critical' ? 'text-red-400 bg-red-400/10 border-red-400/30'
    : 'text-amber-400 bg-amber-400/10 border-amber-400/30'
}

function scoreFlag(events: AuditEvent[]): FlaggedIncident[] {
  const flags: FlaggedIncident[] = []
  events.forEach(ev => {
    REQUIRED_FIELDS.forEach(f => {
      const val = (ev as Record<string,unknown>)[f]
      if (val === null || val === undefined || val === '') {
        flags.push({
          id: `${ev.event_id}-${f}`,
          event_id: ev.event_id,
          timestamp: ev.timestamp,
          severity: 'critical',
          reason: `Required field missing: ${f}`,
          field_missing: f,
          threshold_violated: null,
          threshold_value: null,
          actual_value: null,
          resolved: false,
          resolved_at: null,
          notes: null,
          created_at: ev.created_at,
        })
      }
    });
    Object.entries(THRESHOLDS).forEach(([k, cfg]) => {
      const val = (ev as Record<string,unknown>)[k] as number | null
      if (val !== null && val !== undefined && val > cfg.max) {
        flags.push({
          id: `${ev.event_id}-${k}-thresh`,
          event_id: ev.event_id,
          timestamp: ev.timestamp,
          severity: k === 'jailbreak_confidence' || k === 'toxicity_score' ? 'critical' : 'warning',
          reason: `${cfg.label} exceeds threshold: ${val.toFixed(3)} > ${cfg.max}${cfg.unit}`,
          field_missing: null,
          threshold_violated: k,
          threshold_value: cfg.max,
          actual_value: val,
          resolved: false,
          resolved_at: null,
          notes: null,
          created_at: ev.created_at,
        })
      }
    })
  })
  return flags
}

export default function ComplianceMonitor() {
  const [tab, setTab] = useState<Tab>('Overview')
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [flags, setFlags] = useState<FlaggedIncident[]>([])
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null)
  const [filterSeverity, setFilterSeverity] = useState<'all'|'critical'|'warning'>('all')
  const [search, setSearch] = useState('')
  const [useSeed, setUseSeed] = useState(false)

  const seedData = useCallback((): AuditEvent[] => {
    const models = ['gpt-4.1','gpt-4.1-mini','claude-3-5-sonnet','gemini-1.5-pro']
    const guardEvents = ['none','pii_detected','toxicity_block','jailbreak_attempt',null]
    const now = new Date()
    return Array.from({length: 40}, (_,i) => ({
      id: `seed-${i}`,
      event_id: `evt-${String(i).padStart(4,'0')}`,
      timestamp: new Date(now.getTime() - i * 90000).toISOString(),
      event_type: 'ai_inference',
      system_id: 'axt-gateway-prod',
      environment: 'production',
      model_provider: 'openai',
      model_id: models[i % models.length],
      model_version: i % 7 === 0 ? null : `v${(i%3)+1}.0.${i%10}`,
      temperature: 0.2,
      user_id: `user_${(i%8)+1}`,
      session_id: `sess_${i}`,
      user_prompt: 'Sample prompt text for AXT inference call',
      response: 'Model response text',
      tokens_prompt: 200 + i * 10,
      tokens_completion: 150 + i * 8,
      latency_ms: 400 + i * 60,
      guardrail_event: i % 5 === 0 ? null : guardEvents[i % guardEvents.length],
      guardrail_action: i % 9 === 0 ? null : 'allow',
      pii_detected: i % 11 === 0,
      content_filtered: i % 15 === 0,
      policy_violations: i % 6 === 0 ? null : [],
      drift_score: i % 8 === 0 ? null : parseFloat((Math.random() * 0.6).toFixed(3)),
      hallucination_risk: parseFloat((Math.random() * 0.5).toFixed(3)),
      toxicity_score: parseFloat((Math.random() * 0.3).toFixed(3)),
      jailbreak_confidence: parseFloat((Math.random() * 0.25).toFixed(3)),
      control_ids: i % 4 === 0 ? null : ['AI-CTRL-12','AI-CTRL-17'],
      entry_hash: i % 10 === 0 ? null : `0x${Math.random().toString(16).slice(2,18)}`,
      prev_entry_hash: `0x${Math.random().toString(16).slice(2,18)}`,
      schema_version: i % 12 === 0 ? '' : '1.2.0',
      inference_cost_usd: parseFloat((Math.random() * 0.08).toFixed(5)),
      raw_payload: { note: 'seed record', index: i },
      created_at: new Date(now.getTime() - i * 90000).toISOString(),
    }))
  }, [])
