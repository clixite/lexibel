"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { Upload, ArrowRight, ArrowLeft, Check, Loader2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

type Step = 1 | 2 | 3 | 4 | 5;

const SOURCES = [
  { id: "forlex", label: "Forlex", description: "Import depuis Forlex (CSV/ZIP)" },
  { id: "dpa_jbox", label: "DPA JBox", description: "Import depuis DPA JBox (PDF + metadata)" },
  { id: "outlook", label: "Outlook", description: "Import emails depuis Microsoft Outlook" },
  { id: "csv", label: "CSV générique", description: "Import depuis un fichier CSV" },
];

const STEP_LABELS = ["Source", "Upload", "Preview", "Import", "Résultat"];

export default function MigrationPage() {
  const { data: session } = useSession();
  const [step, setStep] = useState<Step>(1);
  const [source, setSource] = useState<string>("");
  const [jobId, setJobId] = useState<string>("");
  const [csvText, setCsvText] = useState<string>("");
  const [preview, setPreview] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const token = (session?.user as any)?.accessToken;

  const createJob = async () => {
    if (!token || !source) return;
    setLoading(true);
    setError(null);
    try {
      const job = await apiFetch<any>("/migration/jobs", token, {
        method: "POST",
        body: JSON.stringify({ source_system: source }),
      });
      setJobId(job.id);
      setStep(2);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const uploadAndPreview = async () => {
    if (!token || !jobId || !csvText.trim()) return;
    setLoading(true);
    setError(null);
    try {
      // Parse CSV text into array of objects
      const lines = csvText.trim().split("\n");
      const headers = lines[0].split(",").map((h) => h.trim());
      const data = lines.slice(1).map((line) => {
        const values = line.split(",").map((v) => v.trim());
        const obj: Record<string, string> = {};
        headers.forEach((h, i) => {
          obj[h] = values[i] || "";
        });
        return obj;
      });

      const previewData = await apiFetch<any>(
        `/migration/jobs/${jobId}/preview`,
        token,
        { method: "POST", body: JSON.stringify({ data }) }
      );
      setPreview(previewData);
      setStep(3);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const startImport = async () => {
    if (!token || !jobId) return;
    setLoading(true);
    setError(null);
    try {
      setStep(4);
      const importResult = await apiFetch<any>(
        `/migration/jobs/${jobId}/start`,
        token,
        { method: "POST" }
      );
      setResult(importResult);
      setStep(5);
    } catch (err: any) {
      setError(err.message);
      setStep(3);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Upload className="w-6 h-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Migration Center</h1>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                i + 1 === step
                  ? "bg-blue-600 text-white"
                  : i + 1 < step
                    ? "bg-green-500 text-white"
                    : "bg-gray-200 text-gray-500"
              }`}
            >
              {i + 1 < step ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            <span className={`text-sm ${i + 1 === step ? "font-medium text-gray-900" : "text-gray-500"}`}>
              {label}
            </span>
            {i < STEP_LABELS.length - 1 && (
              <div className={`w-8 h-0.5 ${i + 1 < step ? "bg-green-500" : "bg-gray-200"}`} />
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Step 1: Select source */}
      {step === 1 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Sélectionnez la source</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SOURCES.map((s) => (
              <button
                key={s.id}
                onClick={() => setSource(s.id)}
                className={`p-4 rounded-xl border text-left transition-colors ${
                  source === s.id
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 bg-white hover:border-gray-300"
                }`}
              >
                <p className="font-medium text-gray-900">{s.label}</p>
                <p className="text-sm text-gray-500 mt-1">{s.description}</p>
              </button>
            ))}
          </div>
          <div className="flex justify-end mt-6">
            <button
              onClick={createJob}
              disabled={!source || loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Continuer
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Upload */}
      {step === 2 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Collez vos données (CSV)</h2>
          <textarea
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder={"reference,title,type,status\nDOS-001,Dossier Test,general,open"}
            className="w-full h-64 px-4 py-3 border border-gray-300 rounded-xl text-sm font-mono focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
          <div className="flex justify-between mt-6">
            <button onClick={() => setStep(1)} className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 text-sm">
              <ArrowLeft className="w-4 h-4" /> Retour
            </button>
            <button
              onClick={uploadAndPreview}
              disabled={!csvText.trim() || loading}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Prévisualiser
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview */}
      {step === 3 && preview && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Prévisualisation</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold text-gray-900">{preview.total_records}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Doublons détectés</p>
              <p className="text-2xl font-bold text-amber-600">{preview.duplicates}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Tables cibles</p>
              <p className="text-sm font-medium text-gray-900 mt-1">{preview.tables.join(", ")}</p>
            </div>
          </div>

          {preview.sample && preview.sample.length > 0 && (
            <div className="bg-white rounded-xl border border-gray-200 p-4 mb-6">
              <h3 className="text-sm font-medium text-gray-900 mb-2">Échantillon</h3>
              <pre className="text-xs text-gray-600 overflow-auto max-h-48">
                {JSON.stringify(preview.sample, null, 2)}
              </pre>
            </div>
          )}

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:text-gray-900 text-sm">
              <ArrowLeft className="w-4 h-4" /> Retour
            </button>
            <button
              onClick={startImport}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700 transition-colors disabled:opacity-50"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Lancer l&apos;import
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Progress */}
      {step === 4 && (
        <div className="text-center py-12">
          <Loader2 className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
          <p className="text-lg font-medium text-gray-900">Import en cours...</p>
          <p className="text-sm text-gray-500 mt-1">Veuillez patienter.</p>
        </div>
      )}

      {/* Step 5: Results */}
      {step === 5 && result && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Résultat</h2>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Statut</p>
              <p className={`text-lg font-bold ${result.status === "completed" ? "text-green-600" : "text-red-600"}`}>
                {result.status === "completed" ? "Terminé" : "Échoué"}
              </p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Importés</p>
              <p className="text-2xl font-bold text-green-600">{result.imported_records}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Échoués</p>
              <p className="text-2xl font-bold text-red-600">{result.failed_records}</p>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-4">
              <p className="text-sm text-gray-500">Total</p>
              <p className="text-2xl font-bold text-gray-900">{result.total_records}</p>
            </div>
          </div>

          {result.error_log && result.error_log.length > 0 && (
            <div className="bg-red-50 rounded-xl border border-red-200 p-4 mb-6">
              <h3 className="text-sm font-medium text-red-800 mb-2">Erreurs</h3>
              <pre className="text-xs text-red-600 overflow-auto max-h-32">
                {JSON.stringify(result.error_log, null, 2)}
              </pre>
            </div>
          )}

          <button
            onClick={() => { setStep(1); setSource(""); setJobId(""); setCsvText(""); setPreview(null); setResult(null); }}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Nouvelle migration
          </button>
        </div>
      )}
    </div>
  );
}
