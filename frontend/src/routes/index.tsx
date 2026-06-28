import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  Shield,
  Plus,
  Upload,
  Play,
  Info,
  AlertTriangle,
  FileText,
  CheckCircle2,
  Loader2,
  Sparkles,
  MapPin,
  Trash2,
} from "lucide-react";
import { api, getAuthToken, removeAuthToken } from "../lib/api";
import type { Incident } from "../lib/api";
import IncidentMap from "../components/IncidentMap";

export const Route = createFileRoute("/")({
  component: Dashboard,
});

function Dashboard() {
  const navigate = useNavigate();
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [title, setTitle] = useState("");
  const [incidentType, setIncidentType] = useState("bridge_failure");
  const [description, setDescription] = useState("");
  const [locationName, setLocationName] = useState("");
  const [latitude, setLatitude] = useState("");
  const [longitude, setLongitude] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [demoLoading, setDemoLoading] = useState<string | null>(null);

  useEffect(() => {
    const token = getAuthToken();
    if (!token) {
      setLoading(false);
      navigate({ to: "/login" });
      return;
    }

    async function loadDashboard() {
      try {
        const list = await api.incidents.list();
        setIncidents(list);
      } catch (err: any) {
        setError(err.message || "Failed to load dashboard data.");
        if (err.message === "Not authenticated") {
          removeAuthToken();
          navigate({ to: "/login" });
        }
      } finally {
        setLoading(false);
      }
    }
    loadDashboard();
  }, [navigate]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(Array.from(e.target.files));
    }
  };

  const handleCreateIncident = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      // 1. Create Incident
      const newInc = await api.incidents.create({
        title,
        description: description || undefined,
        location_name: locationName || undefined,
        latitude: latitude ? parseFloat(latitude) : undefined,
        longitude: longitude ? parseFloat(longitude) : undefined,
      });

      // 2. Upload Files (if any)
      if (files.length > 0) {
        await api.uploads.upload(newInc.id, files);
      }

      // 3. Add to local list immediately so it appears in the table
      setIncidents((prev) => [newInc, ...prev]);

      // 4. Trigger Workflow only if files were uploaded (backend requires uploads)
      if (files.length > 0) {
        const wf = await api.workflows.trigger(newInc.id);
        navigate({ to: `/incident/${newInc.id}`, search: { workflowId: wf.id } });
      } else {
        // Navigate to incident page (user can upload files and trigger pipeline there)
        navigate({ to: `/incident/${newInc.id}` });
      }
    } catch (err: any) {
      setError(
        err.message || "Failed to initialize incident analysis pipeline.",
      );
      setSubmitting(false);
    }
  };

  const handleLaunchDemo = async (scenario: string) => {
    setDemoLoading(scenario);
    setError(null);
    try {
      const res = await api.demo.launch(scenario);
      navigate({
        to: `/incident/${res.incident_id}`,
        search: { workflowId: res.workflow_id },
      });
    } catch (err: any) {
      setError(err.message || `Failed to launch ${scenario} demo.`);
      setDemoLoading(null);
    }
  };

  const handleDeleteIncident = async (id: string) => {
    if (!confirm("Are you sure you want to delete this incident? This action cannot be undone.")) {
      return;
    }
    // Optimistic: remove from list immediately
    const previousIncidents = incidents;
    setIncidents(incidents.filter((inc) => inc.id !== id));
    try {
      await api.incidents.delete(id);
    } catch (err: any) {
      // Restore on failure
      setIncidents(previousIncidents);
      setError(err.message || "Failed to delete incident.");
    }
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-dark-deep">
        <Loader2 className="w-10 h-10 text-brand-blue animate-spin mb-4" />
        <span className="text-sm text-slate-400 font-mono tracking-wider">
          LOADING CORE SERVICES...
        </span>
      </div>
    );
  }

  // Calculate statistics
  const total = incidents.length;
  const critical = incidents.filter((i) => i.risk_level === "critical").length;
  const high = incidents.filter((i) => i.risk_level === "high").length;
  const pending = incidents.filter((i) => !i.risk_level).length;

  return (
    <div className="flex-1 p-6 space-y-6 overflow-y-auto max-w-7xl mx-auto w-full">
      {/* Welcome Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-glass-border pb-6">
        <div>
          <h1 className="font-display font-bold text-3xl tracking-wider">
            Mission Control Dashboard
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Autonomous multi-agent early warning intelligence and risk
            assessment platform.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-emerald-400 flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>ALL CORE SYSTEMS OPERATIONAL</span>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <div className="p-4 rounded-xl bg-red-950/30 border border-red-500/20 text-red-400 text-xs font-mono">
          {error}
        </div>
      )}

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[
          {
            label: "Total Incidents",
            val: total,
            color: "text-brand-blue",
            bg: "bg-brand-blue/5",
          },
          {
            label: "Critical Threat",
            val: critical,
            color: "text-red-500",
            bg: "bg-red-500/5",
            border: "border-red-500/20",
          },
          {
            label: "High Threat",
            val: high,
            color: "text-orange-500",
            bg: "bg-orange-500/5",
            border: "border-orange-500/20",
          },
          {
            label: "Pending Processing",
            val: pending,
            color: "text-slate-400",
            bg: "bg-slate-900/40",
          },
        ].map((stat, i) => (
          <div
            key={i}
            className={`glass-card p-5 rounded-xl border border-glass-border flex flex-col justify-between min-h-[110px] ${stat.border || ""} relative overflow-hidden`}
          >
            <div
              className={`absolute top-0 right-0 w-16 h-16 rounded-full ${stat.bg} filter blur-xl`}
            />
            <span className="text-[10px] uppercase font-mono tracking-widest text-slate-400 block">
              {stat.label}
            </span>
            <span
              className={`text-3xl font-display font-bold mt-2 ${stat.color}`}
            >
              {stat.val}
            </span>
          </div>
        ))}
      </div>

      {/* Main Panel Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Side: Create & Demo launchers (40%) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Launch Demo Scenario Panel */}
          <div className="glass-panel p-6 rounded-xl border border-glass-border shadow-[0_4px_24px_rgba(0,0,0,0.2)]">
            <div className="flex items-center gap-2 mb-4">
              <Sparkles className="w-5 h-5 text-brand-blue" />
              <h2 className="font-display font-semibold text-lg">
                Launch Simulation Scenarios
              </h2>
            </div>
            <p className="text-xs text-slate-400 mb-4 leading-relaxed">
              Instantly deploy pre-configured intelligence packages (visual
              analysis assets, structural sensor readings, local blueprints) to
              demonstrate the multi-agent AI pipeline.
            </p>
            <div className="grid grid-cols-1 gap-2.5">
              {[
                {
                  name: "bridge_structural_failure",
                  label: "Bridge Failure Scenario",
                  desc: "Analyzes visual structural cracks & maintenance blueprints",
                },
                {
                  name: "urban_flood",
                  label: "Urban Flood Scenario",
                  desc: "Synthesizes hydrology data sheets & flood damage visuals",
                },
                {
                  name: "wildfire",
                  label: "Wildfire Scenario",
                  desc: "Processes evacuation maps & vegetation moisture specs",
                },
                {
                  name: "power_grid_failure",
                  label: "Power Grid Failure Scenario",
                  desc: "Computes transformer loading reports & thermal pictures",
                },
              ].map((scenario) => (
                <button
                  key={scenario.name}
                  onClick={() => handleLaunchDemo(scenario.name)}
                  disabled={demoLoading !== null}
                  className="flex items-center justify-between p-3.5 rounded-xl border border-glass-border bg-slate-900/30 hover:bg-slate-900/60 hover:border-brand-blue/30 text-left transition-all duration-300 group disabled:opacity-50 cursor-pointer"
                >
                  <div className="flex-1 pr-4">
                    <span className="text-xs font-semibold block text-slate-200 group-hover:text-brand-blue transition-colors">
                      {scenario.label}
                    </span>
                    <span className="text-[10px] font-mono text-slate-500 mt-1 block leading-normal">
                      {scenario.desc}
                    </span>
                  </div>
                  {demoLoading === scenario.name ? (
                    <Loader2 className="w-4 h-4 text-brand-blue animate-spin" />
                  ) : (
                    <Play className="w-3.5 h-3.5 text-slate-400 group-hover:text-brand-blue group-hover:translate-x-0.5 transition-all" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Create New Incident Form */}
          <div className="glass-panel p-6 rounded-xl border border-glass-border shadow-[0_4px_24px_rgba(0,0,0,0.2)]">
            <div className="flex items-center gap-2 mb-4">
              <Plus className="w-5 h-5 text-brand-blue" />
              <h2 className="font-display font-semibold text-lg">
                Initialize Custom Incident
              </h2>
            </div>
            <form onSubmit={handleCreateIncident} className="space-y-4">
              <div className="space-y-1">
                <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                  Incident Title
                </label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. San Francisco Pier 3 Crack Investigation"
                  className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 glass-input"
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                    Incident Type
                  </label>
                  <select
                    value={incidentType}
                    onChange={(e) => setIncidentType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 glass-input"
                  >
                    <option value="bridge_failure">Bridge Failure</option>
                    <option value="urban_flood">Urban Flood</option>
                    <option value="wildfire">Wildfire</option>
                    <option value="power_grid_failure">Power Grid</option>
                    <option value="earthquake">Earthquake</option>
                    <option value="landslide">Landslide</option>
                    <option value="unknown">Other/General</option>
                  </select>
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                    Location Name
                  </label>
                  <input
                    type="text"
                    value={locationName}
                    onChange={(e) => setLocationName(e.target.value)}
                    placeholder="e.g. Pier 3, SF"
                    className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 glass-input"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                    Latitude
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    value={latitude}
                    onChange={(e) => setLatitude(e.target.value)}
                    placeholder="37.7749"
                    className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 glass-input"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                    Longitude
                  </label>
                  <input
                    type="number"
                    step="0.000001"
                    value={longitude}
                    onChange={(e) => setLongitude(e.target.value)}
                    placeholder="-122.4194"
                    className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 glass-input"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                  Incident Description
                </label>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Describe the incident details for knowledge base cross-referencing..."
                  rows={2}
                  className="w-full px-3 py-2 rounded-lg text-sm text-slate-200 glass-input resize-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-[10px] uppercase font-mono tracking-wider text-slate-400 block">
                  Attach Analysis Files
                </label>
                <div className="border border-dashed border-slate-700 hover:border-brand-blue/50 rounded-lg p-4 text-center cursor-pointer transition-all duration-200 relative">
                  <input
                    type="file"
                    multiple
                    onChange={handleFileChange}
                    className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                  />
                  <Upload className="w-5 h-5 text-slate-400 mx-auto mb-2" />
                  <span className="text-xs text-slate-300 font-semibold block">
                    Drag & drop files or click
                  </span>
                  <span className="text-[10px] text-slate-500 mt-1 block">
                    Supports JPG, PNG, PDF, CSV, TXT
                  </span>
                </div>
                {files.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {files.map((file, idx) => (
                      <div
                        key={idx}
                        className="flex items-center justify-between px-2.5 py-1 rounded bg-slate-900 border border-slate-800 text-[10px] font-mono text-slate-400"
                      >
                        <span className="truncate max-w-[200px]">
                          {file.name}
                        </span>
                        <span>{(file.size / 1024).toFixed(0)} KB</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="submit"
                disabled={submitting}
                className="w-full mt-2 py-2.5 rounded-lg bg-brand-blue hover:bg-brand-blue/90 font-semibold text-xs uppercase tracking-wider text-white flex items-center justify-center gap-2 border border-brand-blue/30 shadow-[0_0_15px_rgba(59,130,246,0.15)] disabled:opacity-50 transition-all cursor-pointer"
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <>
                    <Play className="w-3.5 h-3.5" />
                    <span>Run Multi-Agent Engine</span>
                  </>
                )}
              </button>
            </form>
          </div>
        </div>

        {/* Right Side: Map & Incidents list (60%) */}
        <div className="lg:col-span-7 space-y-6">
          {/* Tactical Map */}
          <div className="glass-panel p-5 rounded-xl border border-glass-border">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <MapPin className="w-5 h-5 text-brand-blue" />
                <h2 className="font-display font-semibold text-lg">
                  Satellite Intelligence Map
                </h2>
              </div>
              <span className="text-[9px] font-mono text-slate-500 uppercase">
                Interactive SAT overlay
              </span>
            </div>
            <IncidentMap
              incidents={incidents}
              onSelect={(id) => {
                navigate({ to: `/incident/${id}` });
              }}
            />
          </div>

          {/* Active Incident List */}
          <div className="glass-panel p-5 rounded-xl border border-glass-border">
            <h2 className="font-display font-semibold text-lg mb-4">
              Active Incident Feeds
            </h2>
            <div className="overflow-hidden rounded-lg border border-glass-border">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-slate-900/60 border-b border-glass-border text-[9px] font-mono uppercase tracking-widest text-slate-400">
                    <th className="p-3">Incident</th>
                    <th className="p-3">Risk Level</th>
                    <th className="p-3">Confidence</th>
                    <th className="p-3">Triggered</th>
                    <th className="p-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-glass-border/30 bg-slate-950/20 text-xs font-sans">
                  {incidents.length === 0 ? (
                    <tr>
                      <td
                        colSpan={5}
                        className="p-8 text-center text-slate-500 font-mono"
                      >
                        NO INCIDENTS REGISTERED. LAUNCH A DEMO SCENARIO ABOVE.
                      </td>
                    </tr>
                  ) : (
                    incidents.map((inc) => (
                      <tr
                        key={inc.id}
                        className="hover:bg-slate-900/20 transition-all duration-200"
                      >
                        <td className="p-3">
                          <span className="font-semibold text-slate-200 block">
                            {inc.title}
                          </span>
                          <span className="text-[10px] font-mono text-slate-500 mt-0.5 block">
                            {inc.incident_type}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`inline-flex items-center px-2 py-0.5 rounded font-mono text-[10px] uppercase font-bold ${
                              inc.risk_level === "critical"
                                ? "bg-red-500/10 text-red-400 border border-red-500/20"
                                : inc.risk_level === "high"
                                  ? "bg-orange-500/10 text-orange-400 border border-orange-500/20"
                                  : inc.risk_level === "medium"
                                    ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
                                    : inc.risk_level === "low"
                                      ? "bg-green-500/10 text-green-400 border border-green-500/20"
                                      : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {inc.risk_level || "pending"}
                          </span>
                        </td>
                        <td className="p-3 font-mono text-slate-300">
                          {inc.confidence_score
                            ? `${(inc.confidence_score * 100).toFixed(0)}%`
                            : "N/A"}
                        </td>
                        <td className="p-3 text-[10px] font-mono text-slate-400">
                          {new Date(inc.created_at).toLocaleString()}
                        </td>
                        <td className="p-3 text-right">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() =>
                                navigate({ to: `/incident/${inc.id}` })
                              }
                              className="px-2.5 py-1 rounded bg-brand-blue/10 hover:bg-brand-blue text-brand-blue hover:text-white border border-brand-blue/20 hover:border-brand-blue text-[10px] font-semibold transition-all cursor-pointer"
                            >
                              Explore
                            </button>
                            {!inc.is_demo && (
                              <button
                                onClick={() => handleDeleteIncident(inc.id)}
                                className="p-1 rounded bg-red-500/10 hover:bg-red-500 text-red-400 hover:text-white border border-red-500/20 hover:border-red-500 transition-all cursor-pointer"
                                title="Delete incident"
                              >
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
