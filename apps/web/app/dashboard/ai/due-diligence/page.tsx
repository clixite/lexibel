"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import { Shield, AlertTriangle, CheckCircle, Loader2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface EntityRisk {
  entity_name: string;
  entity_type: string;
  risk_level: string;
  risk_score: number;
  flags: string[];
  sanctions_hit: boolean;
  bce_status: string;
}

interface DueDiligenceResult {
  case_id: string;
  generated_at: string;
  entities: EntityRisk[];
  risk_flags: string[];
  sanctions_hits: number;
  overall_risk: string;
  recommendations: string[];
  total_entities_checked: number;
}

const RISK_COLORS: Record<string, string> = {
  LOW: "text-green-600 bg-green-50",
  MEDIUM: "text-amber-600 bg-amber-50",
  HIGH: "text-orange-600 bg-orange-50",
  CRITICAL: "text-red-600 bg-red-50",
};

export default function DueDiligencePage() {
  const { data: session } = useSession();
  const [caseId, setCaseId] = useState("");
  const [documentsText, setDocumentsText] = useState("");
  const [result, setResult] = useState<DueDiligenceResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  const runAnalysis = async () => {
    if (!caseId.trim() || !token) return;
    setLoading(true);
    setError("");
    setResult(null);

    try {
      const data = await apiFetch<DueDiligenceResult>(
        `/agents/due-diligence/${caseId}`,
        token,
        {
          tenantId,
          method: "POST",
          body: JSON.stringify({
            documents_text: documentsText,
            events: [],
          }),
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
          <Shield className="w-6 h-6 text-red-500" />
          Due Diligence
        </h1>
        <p className="text-slate-500 mt-1">
          Analyse automatisée des entités et risques juridiques.
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
              Texte des documents (optionnel)
            </label>
            <textarea
              value={documentsText}
              onChange={(e) => setDocumentsText(e.target.value)}
              rows={4}
              placeholder="Collez ici le texte des documents à analyser..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={runAnalysis}
            disabled={loading || !caseId.trim()}
            className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 flex items-center gap-2 w-fit"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            Lancer l&apos;analyse
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
          {/* Risk Summary */}
          <div className="bg-white border border-slate-200 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Résumé</h2>
              <span
                className={`px-3 py-1 rounded-full text-sm font-medium ${RISK_COLORS[result.overall_risk] || ""}`}
              >
                Risque : {result.overall_risk}
              </span>
            </div>
            <div className="grid grid-cols-3 gap-4 text-center">
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold">{result.total_entities_checked}</div>
                <div className="text-xs text-slate-500">Entités vérifiées</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold">{result.sanctions_hits}</div>
                <div className="text-xs text-slate-500">Sanctions</div>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg">
                <div className="text-2xl font-bold">{result.risk_flags.length}</div>
                <div className="text-xs text-slate-500">Drapeaux</div>
              </div>
            </div>
          </div>

          {/* Entities Table */}
          {result.entities.length > 0 && (
            <div className="bg-white border border-slate-200 rounded-xl p-6">
              <h2 className="text-lg font-semibold mb-4">Entités</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-slate-200">
                      <th className="text-left py-2 px-3 font-medium text-slate-600">Nom</th>
                      <th className="text-left py-2 px-3 font-medium text-slate-600">Type</th>
                      <th className="text-left py-2 px-3 font-medium text-slate-600">Risque</th>
                      <th className="text-left py-2 px-3 font-medium text-slate-600">Score</th>
                      <th className="text-left py-2 px-3 font-medium text-slate-600">Sanctions</th>
                      <th className="text-left py-2 px-3 font-medium text-slate-600">Drapeaux</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.entities.map((entity, i) => (
                      <tr key={i} className="border-b border-slate-100">
                        <td className="py-2 px-3 font-medium">{entity.entity_name}</td>
                        <td className="py-2 px-3 text-slate-500">{entity.entity_type}</td>
                        <td className="py-2 px-3">
                          <span className={`px-2 py-0.5 rounded text-xs font-medium ${RISK_COLORS[entity.risk_level] || ""}`}>
                            {entity.risk_level}
                          </span>
                        </td>
                        <td className="py-2 px-3">{entity.risk_score.toFixed(2)}</td>
                        <td className="py-2 px-3">
                          {entity.sanctions_hit ? (
                            <AlertTriangle className="w-4 h-4 text-red-500" />
                          ) : (
                            <CheckCircle className="w-4 h-4 text-green-500" />
                          )}
                        </td>
                        <td className="py-2 px-3 text-xs text-slate-500">
                          {entity.flags.join("; ") || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
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
                    <span className="mt-1 w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0" />
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
