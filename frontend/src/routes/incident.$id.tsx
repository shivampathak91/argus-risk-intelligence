import { createFileRoute, useNavigate, useParams, useSearch } from '@tanstack/react-router'
import { useEffect, useState, useRef } from 'react'
import { 
  Shield, 
  Terminal, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Download, 
  MessageSquare, 
  TrendingUp, 
  Briefcase, 
  FileText, 
  ArrowLeft,
  Loader2,
  AlertTriangle,
  Play
} from 'lucide-react'
import { api, getAuthToken } from '../lib/api'
import type { Incident, Workflow, Report } from '../lib/api'

export const Route = createFileRoute('/incident/$id')({
  component: IncidentDetails,
})

function IncidentDetails() {
  const { id: incidentId } = useParams({ from: '/incident/$id' })
  const navigate = useNavigate()
  
  // States
  const [incident, setIncident] = useState<Incident | null>(null)
  const [workflow, setWorkflow] = useState<Workflow | null>(null)
  const [report, setReport] = useState<Report | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'timeline' | 'risk' | 'recommendations' | 'report'>('timeline')
  const [liveLog, setLiveLog] = useState<string[]>([])
  const [pipelineLoading, setPipelineLoading] = useState(false)
  
  // WebSocket Reference
  const wsRef = useRef<WebSocket | null>(null)

  const loadData = async () => {
    try {
      const inc = await api.incidents.get(incidentId)
      setIncident(inc)
      
      // Get report if exists
      const reports = await api.reports.getForIncident(incidentId)
      let matchedReport: Report | null = null
      if (reports.length > 0) {
        matchedReport = reports[0]
        setReport(matchedReport)
      }

      // Get workflows independently of report
      const workflows = await api.workflows.listForIncident(incidentId)
      if (workflows.length > 0) {
        const matchedWf = matchedReport?.workflow_id
          ? workflows.find(w => w.id === matchedReport.workflow_id)
          : null
        setWorkflow(matchedWf || workflows[0])
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load incident details.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const token = getAuthToken()
    if (!token) {
      navigate({ to: '/login' })
      return
    }

    loadData()

    return () => {
      if (wsRef.current) {
        wsRef.current.close()
      }
    }
  }, [incidentId, navigate])

  // Setup WebSocket when workflow ID is known
  useEffect(() => {
    if (!workflow?.id) return

    // Connect to WebSocket if running or pending
    if (workflow.status === 'running' || workflow.status === 'pending') {
      const wsUrl = `ws://127.0.0.1:8000/ws/workflow/${workflow.id}`
      const ws = new WebSocket(wsUrl)
      wsRef.current = ws

      setLiveLog(prev => [...prev, `[SYSTEM] Connecting to tactical telemetry for workflow ${workflow.id}...`])

      ws.onmessage = (event) => {
        const payload = JSON.parse(event.data)
        const { event_type, data } = payload

        if (event_type === 'connection_established') {
          setLiveLog(prev => [...prev, '[SYSTEM] Security tunnel established. Pipeline listening.'])
        } else if (event_type === 'agent_started') {
          setLiveLog(prev => [...prev, `[PIPELINE] ${data.agent.toUpperCase()} agent initialized.`])
          // Update step state
          setWorkflow(prev => {
            if (!prev) return null
            const updatedSteps = prev.agent_steps.map(s => 
              s.agent === data.agent ? { ...s, status: 'running' as const } : s
            )
            return { ...prev, agent_steps: updatedSteps }
          })
        } else if (event_type === 'agent_completed') {
          const riskDetails = data.risk_level ? ` - Result: ${data.risk_level.toUpperCase()} (score: ${data.risk_score})` : ''
          setLiveLog(prev => [...prev, `[PIPELINE] ${data.agent.toUpperCase()} agent execution complete${riskDetails}.`])
          
          // Force update workflow stats
          setWorkflow(prev => {
            if (!prev) return null
            const updatedSteps = prev.agent_steps.map(s => 
              s.agent === data.agent ? { ...s, status: 'completed' as const, output_summary: data.summary } : s
            )
            return { ...prev, agent_steps: updatedSteps }
          })
        } else if (event_type === 'agent_failed') {
          setLiveLog(prev => [...prev, `[ALERT] ${data.agent.toUpperCase()} agent failed: ${data.error}`])
          setWorkflow(prev => {
            if (!prev) return null
            const updatedSteps = prev.agent_steps.map(s => 
              s.agent === data.agent ? { ...s, status: 'failed' as const, error: data.error } : s
            )
            return { ...prev, agent_steps: updatedSteps }
          })
        } else if (event_type === 'agent_skipped') {
          setLiveLog(prev => [...prev, `[WARNING] ${data.agent.toUpperCase()} agent skipped: ${data.error}`])
          setWorkflow(prev => {
            if (!prev) return null
            const updatedSteps = prev.agent_steps.map(s => 
              s.agent === data.agent ? { ...s, status: 'skipped' as const, error: data.error } : s
            )
            return { ...prev, agent_steps: updatedSteps }
          })
        } else if (event_type === 'debate_resolved') {
          setLiveLog(prev => [...prev, `[COMMANDER] Structured debate resolved. Risk escalated to ${data.final_risk_level.toUpperCase()}.`])
        } else if (event_type === 'report_ready') {
          setLiveLog(prev => [...prev, `[SYSTEM] Risk report compiled & verified. PDF artifact created.`])
          loadData() // Reload to fetch report ORM record
        } else if (event_type === 'workflow_completed') {
          setLiveLog(prev => [...prev, `[SYSTEM] Pipeline run complete in ${data.duration_seconds}s. Shutting down connection.`])
          setWorkflow(prev => prev ? { ...prev, status: 'completed' as const } : null)
          ws.close()
        }
      }

      ws.onerror = () => {
        setLiveLog(prev => [...prev, '[ERROR] Telemetry interface error.'])
      }

      ws.onclose = () => {
        setLiveLog(prev => [...prev, '[SYSTEM] Telemetry link terminated.'])
      }
    }
  }, [workflow?.id])

  const handleTriggerAnalysis = async () => {
    setPipelineLoading(true)
    try {
      const wf = await api.workflows.trigger(incidentId)
      setWorkflow(wf)
      setLiveLog([`[SYSTEM] Multi-Agent Orchestrator triggered for incident: ${incidentId}`])
    } catch (err: any) {
      setError(err.message || 'Failed to start analysis pipeline.')
    } finally {
      setPipelineLoading(false)
    }
  }

  const handleDownloadPdf = async () => {
    if (!report) return
    try {
      await api.reports.downloadPdf(report.id)
    } catch (err: any) {
      setError(err.message || 'Failed to download PDF.')
    }
  }

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-dark-deep">
        <Loader2 className="w-10 h-10 text-brand-blue animate-spin mb-4" />
        <span className="text-sm text-slate-400 font-mono tracking-wider">RETRIEVING MISSION DATA...</span>
      </div>
    )
  }

  if (!incident) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-dark-deep text-center p-6">
        <AlertCircle className="w-12 h-12 text-red-500 mb-4" />
        <h2 className="text-xl font-bold">Incident Not Found</h2>
        <button onClick={() => navigate({ to: '/' })} className="mt-4 text-brand-blue hover:underline font-mono">
          RETURN TO DASHBOARD
        </button>
      </div>
    )
  }

  // Parse structured data from report JSON if complete
  const reportData = report?.full_report_json || {}
  const commanderDecision = workflow?.agent_steps?.find(s => s.agent === 'commander')?.output_summary

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto max-w-7xl mx-auto w-full">
      {/* Header breadcrumb */}
      <div className="flex items-center gap-3">
        <button 
          onClick={() => navigate({ to: '/' })}
          className="flex items-center gap-2 text-xs font-mono text-slate-400 hover:text-slate-200 transition-colors uppercase tracking-wider"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Control Dashboard</span>
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-500/20 text-red-400 text-xs font-mono flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{error}</span>
          </div>
          <button onClick={() => setError(null)} className="text-red-400/60 hover:text-red-400 text-xs cursor-pointer">✕</button>
        </div>
      )}

      {/* Incident Summary Card */}
      <div className="glass-panel p-6 rounded-xl border border-glass-border flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold border ${
              incident.risk_level === 'critical' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
              incident.risk_level === 'high' ? 'bg-orange-500/10 text-orange-400 border-orange-500/20' :
              incident.risk_level === 'medium' ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20' :
              incident.risk_level === 'low' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
              'bg-slate-900 text-slate-400 border-slate-800'
            }`}>
              {incident.risk_level || 'ANALYSIS PENDING'}
            </span>
            <span className="text-xs text-slate-500 font-mono">ID: {incident.id.slice(0, 8)}</span>
            <span className="text-xs text-slate-500 font-mono">Type: {incident.incident_type}</span>
          </div>
          <h1 className="font-display font-bold text-2xl tracking-wide text-slate-100">{incident.title}</h1>
          {incident.description && (
            <p className="text-sm text-slate-400 max-w-3xl leading-relaxed">{incident.description}</p>
          )}
          {incident.location_name && (
            <p className="text-xs text-slate-500 font-mono">LOCATION: {incident.location_name} {incident.latitude && `(${incident.latitude.toFixed(4)}, ${incident.longitude?.toFixed(4)})`}</p>
          )}
        </div>

        <div className="flex flex-col gap-2 min-w-[200px]">
          {report ? (
            <button 
              onClick={handleDownloadPdf}
              className="py-3 px-4 rounded-lg bg-brand-blue hover:bg-brand-blue/90 font-semibold text-xs uppercase tracking-wider text-white flex items-center justify-center gap-2 border border-brand-blue/30 shadow-[0_0_20px_rgba(59,130,246,0.15)] transition-all cursor-pointer text-center"
            >
              <Download className="w-4 h-4" />
              <span>Download Intelligence PDF</span>
            </button>
          ) : (
            !workflow && (
              <button 
                onClick={handleTriggerAnalysis}
                disabled={pipelineLoading}
                className="py-3 px-4 rounded-lg bg-emerald-600 hover:bg-emerald-500 font-semibold text-xs uppercase tracking-wider text-white flex items-center justify-center gap-2 border border-emerald-500/30 transition-all cursor-pointer disabled:opacity-50"
              >
                {pipelineLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                <span>{pipelineLoading ? 'Initializing...' : 'Initialize Pipeline'}</span>
              </button>
            )
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-glass-border">
        {[
          { id: 'timeline', label: 'Telemetry & Timeline', icon: Terminal },
          { id: 'risk', label: 'Threat & What-If Scenarios', icon: TrendingUp },
          { id: 'recommendations', label: 'Action Plan & Debates', icon: Briefcase },
          { id: 'report', label: 'Synthesized Intelligence', icon: FileText }
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-5 py-3 border-b-2 font-display text-sm font-semibold tracking-wide transition-all flex items-center gap-2 cursor-pointer ${
              activeTab === tab.id 
                ? 'border-brand-blue text-brand-blue bg-brand-blue/5' 
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab Panels */}
      <div className="space-y-6">
        
        {/* PANEL 1: Telemetry Timeline */}
        {activeTab === 'timeline' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Pipeline progress steps */}
            <div className="lg:col-span-7 glass-panel p-6 rounded-xl border border-glass-border space-y-6">
              <h2 className="font-display font-semibold text-lg">Agent Execution Status</h2>
              
              {!workflow ? (
                <div className="text-center py-12 text-slate-500 font-mono text-xs">
                  NO AGENT ACTIVE. CLICK "INITIALIZE PIPELINE" TO BEGIN.
                </div>
              ) : (
                <div className="relative border-l border-glass-border pl-6 ml-3 space-y-8">
                  {workflow.agent_steps.map((step, idx) => (
                    <div key={idx} className="relative group">
                      {/* Step Indicator Dot */}
                      <span className={`absolute -left-[31px] top-1 w-4 h-4 rounded-full border-2 flex items-center justify-center bg-dark-deep ${
                        step.status === 'completed' ? 'border-emerald-500 bg-emerald-500/10' :
                        step.status === 'running' ? 'border-brand-blue bg-brand-blue/10 animate-pulse' :
                        step.status === 'failed' ? 'border-red-500 bg-red-500/10' :
                        step.status === 'skipped' ? 'border-yellow-500 bg-yellow-500/10' :
                        'border-slate-800'
                      }`}>
                        {step.status === 'completed' && <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />}
                        {step.status === 'running' && <div className="w-1.5 h-1.5 rounded-full bg-brand-blue" />}
                        {step.status === 'skipped' && <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />}
                      </span>

                      {/* Header details */}
                      <div className="space-y-1">
                        <div className="flex items-center justify-between">
                          <h3 className="text-xs uppercase font-mono tracking-widest font-bold text-slate-200">
                            {step.agent.toUpperCase()} AGENT
                          </h3>
                          <span className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded ${
                            step.status === 'completed' ? 'text-emerald-400 bg-emerald-950/20' :
                            step.status === 'running' ? 'text-brand-blue bg-brand-blue/10 animate-pulse' :
                            step.status === 'failed' ? 'text-red-400 bg-red-950/20' :
                            step.status === 'skipped' ? 'text-yellow-400 bg-yellow-950/20' :
                            'text-slate-500'
                          }`}>
                            {step.status}
                          </span>
                        </div>
                        
                        {step.duration_seconds && (
                          <span className="text-[10px] font-mono text-slate-500 block">TIME ELAPSED: {step.duration_seconds}s</span>
                        )}

                        {step.output_summary && (
                          <div className="mt-2 p-3.5 rounded bg-slate-950/40 border border-slate-900 text-xs text-slate-300 leading-relaxed font-mono">
                            {step.output_summary}
                          </div>
                        )}

                        {step.error && (
                          <div className="mt-2 p-3.5 rounded bg-red-950/20 border border-red-500/10 text-xs text-red-400 font-mono leading-relaxed">
                            {step.error}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Live Telemetry console */}
            <div className="lg:col-span-5 glass-panel p-5 rounded-xl border border-glass-border bg-slate-950/60 font-mono text-[10px] flex flex-col h-[500px]">
              <div className="flex items-center justify-between mb-4 border-b border-glass-border pb-3">
                <span className="font-semibold text-slate-400 flex items-center gap-1.5">
                  <Terminal className="w-3.5 h-3.5 text-brand-blue" />
                  PIPELINE CONSOLE LOGS
                </span>
                <span className="text-slate-600">baud: 9600 / secure</span>
              </div>
              <div className="flex-1 overflow-y-auto space-y-2 text-slate-400 pr-2">
                {liveLog.length === 0 ? (
                  <span className="text-slate-600 block text-center mt-12">Telemetry console idle...</span>
                ) : (
                  liveLog.map((log, i) => (
                    <div key={i} className="leading-relaxed border-l-2 border-brand-blue/30 pl-2">
                      <span className="text-slate-600">[{new Date().toLocaleTimeString()}]</span> {log}
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}

        {/* PANEL 2: Threat & Simulation */}
        {activeTab === 'risk' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Risk Assessment details */}
            <div className="lg:col-span-7 glass-panel p-6 rounded-xl border border-glass-border space-y-6">
              <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <Shield className="w-5 h-5 text-brand-blue" />
                Comprehensive Threat Evaluation
              </h2>
              
              {commanderDecision ? (
                <div className="p-4 rounded-xl bg-brand-blue/5 border border-brand-blue/20 text-sm leading-relaxed text-slate-300 font-mono">
                  <div className="text-[10px] uppercase text-brand-blue tracking-wider font-bold mb-1">COMMANDER DECISION BASIS</div>
                  {commanderDecision}
                </div>
              ) : (
                <p className="text-xs text-slate-400">Analysis pending. Wait for the commander agent to render final decision.</p>
              )}

              {/* Risk details */}
              {reportData.risk_analysis && (
                <div className="space-y-4 pt-4 border-t border-glass-border/30">
                  <h3 className="font-display font-semibold text-sm text-slate-300">Detailed Risk Synthesis</h3>
                  <p className="text-xs text-slate-400 leading-relaxed font-mono">{reportData.risk_analysis}</p>
                </div>
              )}
            </div>

            {/* Simulation Outcomes */}
            <div className="lg:col-span-5 glass-panel p-5 rounded-xl border border-glass-border space-y-5">
              <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-brand-indigo" />
                Simulation Scenarios
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                What-If probabilistic outcomes model structural behavior and cascades under varied intervention parameters.
              </p>

              {reportData.simulation_findings ? (
                <div className="space-y-3">
                  <div className="p-4 rounded-lg bg-slate-900/60 border border-glass-border text-xs leading-relaxed font-mono text-slate-300">
                    {reportData.simulation_findings}
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 font-mono text-xs">
                  Scenario simulations not compiled. Run pipeline.
                </div>
              )}
            </div>
          </div>
        )}

        {/* PANEL 3: Recommendations & Debates */}
        {activeTab === 'recommendations' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            {/* Recommendations List */}
            <div className="lg:col-span-8 glass-panel p-6 rounded-xl border border-glass-border space-y-6">
              <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <Briefcase className="w-5 h-5 text-brand-emerald" />
                Prioritized Action Plan
              </h2>
              
              {reportData.recommendations_text ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-xl bg-slate-900/40 border border-glass-border text-xs leading-relaxed font-mono text-slate-300">
                    {reportData.recommendations_text}
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-500 font-mono text-xs">
                  NO ACTION PLANS COMPILED. PIPELINE MUST BE EXECUTED TO PRODUCE PLAN.
                </div>
              )}
            </div>

            {/* Debates & Historical Precedent context */}
            <div className="lg:col-span-4 glass-panel p-5 rounded-xl border border-glass-border space-y-5">
              <h2 className="font-display font-semibold text-lg flex items-center gap-2">
                <MessageSquare className="w-5 h-5 text-brand-blue" />
                Historical Context &amp; Debates
              </h2>
              
              {reportData.historical_context ? (
                <div className="p-4 rounded-lg bg-slate-900/60 border border-glass-border text-xs font-mono text-slate-300 leading-relaxed">
                  <div className="text-[10px] uppercase text-brand-indigo tracking-wider font-bold mb-1">HISTORICAL SYNOPSIS</div>
                  {reportData.historical_context}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 font-mono text-xs">
                  No historical matches queried.
                </div>
              )}
            </div>
          </div>
        )}

        {/* PANEL 4: Synthesized Report */}
        {activeTab === 'report' && (
          <div className="glass-panel p-8 rounded-xl border border-glass-border max-w-4xl mx-auto space-y-8 shadow-[0_12px_48px_rgba(0,0,0,0.4)] relative">
            
            {/* Header */}
            <div className="flex flex-col items-center text-center space-y-4 border-b border-glass-border pb-8">
              <div className="bg-brand-blue/10 p-4 rounded-full border border-brand-blue/20">
                <Shield className="w-10 h-10 text-brand-blue animate-pulse-glow" />
              </div>
              <div>
                <span className="text-[10px] text-brand-blue font-mono tracking-widest uppercase font-bold block">ARGUS RISK INTELLIGENCE PLATFORM</span>
                <h1 className="font-display font-bold text-3xl tracking-wide text-slate-100 mt-1">Tactical Analysis Dossier</h1>
              </div>
            </div>

            {report ? (
              <div className="space-y-8 font-sans text-slate-200">
                {/* Meta details */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 p-4 rounded-lg bg-slate-900/60 border border-slate-800 text-xs font-mono">
                  <div>
                    <span className="text-slate-500 block">Dossier ID:</span>
                    <span>{report.id.slice(0, 8).toUpperCase()}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Risk Evaluation:</span>
                    <span className="text-red-400 font-bold uppercase">{report.risk_level}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">AI Confidence:</span>
                    <span>{(report.confidence_score * 100).toFixed(0)}%</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">Compiled:</span>
                    <span>{new Date(report.created_at).toLocaleDateString()}</span>
                  </div>
                </div>

                {/* Dossier sections */}
                <div className="space-y-6">
                  <div>
                    <h3 className="font-display font-bold text-base text-brand-blue border-b border-slate-800 pb-2 mb-3">I. Executive Summary</h3>
                    <p className="text-sm leading-relaxed text-slate-300">{report.executive_summary}</p>
                  </div>

                  <div>
                    <h3 className="font-display font-bold text-base text-brand-blue border-b border-slate-800 pb-2 mb-3">II. Comprehensive Threat Assessment</h3>
                    <p className="text-sm leading-relaxed text-slate-300">{report.risk_analysis}</p>
                  </div>

                  {reportData.recommendations_text && (
                    <div>
                      <h3 className="font-display font-bold text-base text-brand-blue border-b border-slate-800 pb-2 mb-3">III. Prioritized Actions &amp; Mitigation</h3>
                      <p className="text-sm leading-relaxed text-slate-300">{reportData.recommendations_text}</p>
                    </div>
                  )}

                  {report.data_sources && (
                    <div>
                      <h3 className="font-display font-bold text-sm text-slate-400 mb-2">Sources &amp; Audit</h3>
                      <ul className="list-disc list-inside text-xs text-slate-500 space-y-1 font-mono">
                        {report.data_sources.map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="text-center py-20 text-slate-500 font-mono text-xs flex flex-col items-center gap-3">
                <FileText className="w-8 h-8 text-slate-600" />
                <span>INTELLIGENCE DOSSIER ANALYSIS INCOMPLETE. PIPELINE PROCESSING REQUIRED.</span>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  )
}
