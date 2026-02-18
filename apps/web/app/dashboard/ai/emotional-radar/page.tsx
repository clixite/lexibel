"use client";

import { useState } from "react";
import { useAuth } from "@/lib/useAuth";
import { Activity, AlertTriangle, TrendingDown, TrendingUp, Minus, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface EventTone {
  event_id: string;
  event_type: string;
  date: string;
  tone: string;
  score: number;
  keywords_found: string[];
  flagged: boolean;
  flag_reason: string;
}

interface EmotionalProfile {
  case_id: string;
  overall_tone: string;
  overall_score: number;
  trend: string;
  escalation_risk: string;
  events_analyzed: number;
  flagged_events: EventTone[];
  all_events: EventTone[];
  recommendations: string[];
}

const TONE_COLORS: Record<string, string> = {
  COOPERATIVE: "text-green-600 bg-green-50",
  NEUTRAL: "text-slate-600 bg-slate-50",
  TENSE: "text-amber-600 bg-amber-50",
  HOSTILE: "text-orange-600 bg-orange-50",
  THREATENING: "text-red-600 bg-red-50",
};

const RISK_COLORS: Record<string, string> = {
  LOW: "text-green-600",
  MEDIUM: "text-amber-600",
  HIGH: "text-orange-600",
  CRITICAL: "text-red-600",
};

function TrendIcon({ trend }: { trend: string }) {
  if (trend === "IMPROVING") return <TrendingUp className="w-4 h-4 text-green-500" />;
  if (trend === "DETERIORATING") return <TrendingDown className="w-4 h-4 text-red-500" />;
  return <Minus className="w-4 h-4 text-slate-400" />;
}

export default function EmotionalRadarPage() {
  const { accessToken, tenantId } = useAuth();
  const [caseId, setCaseId] = useState("");
  const [eventsJson, setEventsJson] = useState("");
  const [result, setResult] = useState<EmotionalProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const runAnalysis = async () => {
    if (!caseId.trim() || !accessToken) return;
    setLoading(true);
    setError("");
    setResult(null);

    let events: Record<string, unknown>[] = [];
    if (eventsJson.trim()) {
      try {
        events = JSON.parse(eventsJson);
      } catch {
        setError("JSON invalide pour les événements.");
        setLoading(false);
        return;
      }
    }

    try {
      const data = await apiFetch<EmotionalProfile>(
        `/agents/emotional-radar/${caseId}`,
        accessToken,
        {
          tenantId,
          method: "POST",
          body: JSON.stringify({ events }),
        }
      );
      setResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Activity className="w-6 h-6 text-amber-500" />
          Radar Émotionnel
        </h1>
        <p className="text-slate-500 mt-1">
          Analyse du ton des communications et détection d&apos;escalade.
        </p>
      </div>

      {/* Input Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
        <div className="grid grid-cols-1 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              ID du dossier
            </label>
            <input
              type="text"
              value={caseId}
              onChange={(e) => setCaseId(e.target.value)}
              placeholder="ex: case-001"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Événements (JSON)
            </label>
            <textarea
              value={eventsJson}
              onChange={(e) => setEventsJson(e.target.value)}
              rows={5}
              placeholder={`[{"id": "evt-1", "type": "email", "date": "2026-01-15", "content": "Texte de l'email..."}]`}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={runAnalysis}
            disabled={loading || !caseId.trim()}
            className="px-4 py-2 bg-amber-600 text-white rounded-lg text-sm font-medium hover:bg-amber-700 disabled:opacity-50 flex items-center gap-2 w-fit"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Activity className="w-4 h-4" />}
            Analyser le ton
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="space-y-6">
          {/* Profile Summary */}
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Profil émotionnel</h2>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${TONE_COLORS[result.overall_tone] || ""}`}>
                {result.overall_tone}
              </span>
            </div>
            <div className="grid grid-cols-4 gap-4 text-center">
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold">{result.overall_score.toFixed(2)}</div>
                <div className="text-xs text-slate-500">Score global</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="flex items-center justify-center gap-1">
                  <TrendIcon trend={result.trend} />
                  <span className="text-sm font-medium">{result.trend}</span>
                </div>
                <div className="text-xs text-slate-500 mt-1">Tendance</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className={`text-lg font-bold ${RISK_COLORS[result.escalation_risk] || ""}`}>
                  {result.escalation_risk}
                </div>
                <div className="text-xs text-slate-500">Risque escalade</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold">{result.events_analyzed}</div>
                <div className="text-xs text-slate-500">Analysés</div>
              </div>
            </div>
          </div>

          {/* Flagged Events */}
          {result.flagged_events.length > 0 && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-6">
              <h2 className="text-lg font-semibold text-red-800 flex items-center gap-2 mb-4">
                <AlertTriangle className="w-5 h-5" />
                Événements signalés ({result.flagged_events.length})
              </h2>
              <div className="space-y-3">
                {result.flagged_events.map((evt, i) => (
                  <div key={i} className="bg-white rounded-lg p-3 border border-red-100">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm font-medium">{evt.event_id} — {evt.event_type}</span>
                      <span className="text-xs text-slate-500">{evt.date}</span>
                    </div>
                    <p className="text-sm text-red-700">{evt.flag_reason}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Timeline of all events */}
          {result.all_events.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Timeline des tons</h2>
              <div className="space-y-2">
                {result.all_events.map((evt, i) => (
                  <div key={i} className="flex items-center gap-3 text-sm">
                    <span className="text-xs text-slate-400 w-20 flex-shrink-0">{evt.date}</span>
                    <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          evt.score >= 0.3
                            ? "bg-green-400"
                            : evt.score >= 0
                              ? "bg-slate-300"
                              : evt.score >= -0.3
                                ? "bg-amber-400"
                                : evt.score >= -0.6
                                  ? "bg-orange-400"
                                  : "bg-red-500"
                        }`}
                        style={{ width: `${Math.abs(evt.score) * 100}%`, minWidth: "4px" }}
                      />
                    </div>
                    <span className={`text-xs px-2 py-0.5 rounded font-medium ${TONE_COLORS[evt.tone] || ""}`}>
                      {evt.tone}
                    </span>
                    <span className="text-xs text-slate-400 w-12 text-right">{evt.score.toFixed(2)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommendations */}
          {result.recommendations.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Recommandations</h2>
              <ul className="space-y-2">
                {result.recommendations.map((rec, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm">
                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-amber-500 flex-shrink-0" />
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
