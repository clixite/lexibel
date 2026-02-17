"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { Upload, ArrowRight, ArrowLeft, Check, Loader2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

type Step = 1 | 2 | 3 | 4 | 5;

const SOURCES = [
  { id: "veoCRM", label: "VeoCRM", description: "Import depuis VeoCRM" },
  { id: "custom", label: "Custom", description: "Import depuis source personnalisée" },
];

const STEP_LABELS = ["Source", "Upload", "Preview", "Confirmation", "Résultats"];

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
  const [importLoading, setImportLoading] = useState(false);

  const token = (session?.user as any)?.accessToken;

  // Progress calculation
  const progressPercent = (step / 5) * 100;

  const createJob = async () => {
    if (!token || !source) return;
    setLoading(true);
    setError(null);
    try {
      const job = await apiFetch<any>("/api/v1/migration/jobs", token, {
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
        `/api/v1/migration/jobs/${jobId}/preview`,
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

  const goToConfirmation = () => {
    setStep(4);
  };

  const startImport = async () => {
    if (!token || !jobId) return;
    setImportLoading(true);
    setError(null);
    try {
      const importResult = await apiFetch<any>(
        `/api/v1/migration/import`,
        token,
        { method: "POST", body: JSON.stringify({ job_id: jobId }) }
      );
      setResult(importResult);
      setStep(5);
    } catch (err: any) {
      setError(err.message);
      setStep(3);
    } finally {
      setImportLoading(false);
    }
  };

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2">
          <Upload className="w-6 h-6 text-accent" />
          Migration Center
        </h1>
        <p className="text-neutral-500 mt-1 text-sm">
          Importez vos données depuis VeoCRM ou une source personnalisée.
        </p>
      </div>

      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-neutral-900">Progression</span>
          <span className="text-sm font-medium text-neutral-600">{Math.round(progressPercent)}%</span>
        </div>
        <div className="h-2 bg-neutral-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-accent transition-all duration-300"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-2 mb-8 overflow-x-auto pb-2">
        {STEP_LABELS.map((label, i) => (
          <div key={label} className="flex items-center gap-2 flex-shrink-0">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium transition-all duration-150 flex-shrink-0 ${
                i + 1 === step
                  ? "bg-accent text-white"
                  : i + 1 < step
                    ? "bg-success text-white"
                    : "bg-neutral-200 text-neutral-500"
              }`}
            >
              {i + 1 < step ? <Check className="w-4 h-4" /> : i + 1}
            </div>
            <span className={`text-sm whitespace-nowrap ${i + 1 === step ? "font-medium text-neutral-900" : "text-neutral-500"}`}>
              {label}
            </span>
            {i < STEP_LABELS.length - 1 && (
              <div className={`w-8 h-0.5 transition-colors flex-shrink-0 ${i + 1 < step ? "bg-success" : "bg-neutral-200"}`} />
            )}
          </div>
        ))}
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Step 1: Select source */}
      {step === 1 && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Étape 1: Sélectionnez la source</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {SOURCES.map((s) => (
              <button
                key={s.id}
                onClick={() => setSource(s.id)}
                className={`p-4 rounded-lg border text-left transition-all duration-150 ${
                  source === s.id
                    ? "border-accent bg-accent-50"
                    : "border-neutral-200 bg-white hover:border-neutral-300 hover:shadow-subtle"
                }`}
              >
                <p className="font-medium text-neutral-900">{s.label}</p>
                <p className="text-sm text-neutral-500 mt-1">{s.description}</p>
              </button>
            ))}
          </div>
          <div className="flex justify-end">
            <button
              onClick={createJob}
              disabled={!source || loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Suivant
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Upload */}
      {step === 2 && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Étape 2: Téléchargez le fichier CSV</h2>
          <p className="text-sm text-neutral-600 mb-4">
            Collez le contenu de votre fichier CSV ci-dessous.
          </p>
          <textarea
            value={csvText}
            onChange={(e) => setCsvText(e.target.value)}
            placeholder={"reference,title,type,status\nDOS-001,Dossier Test,general,open"}
            className="input h-64 font-mono mb-6"
          />
          <div className="flex justify-between">
            <button onClick={() => setStep(1)} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Précédent
            </button>
            <button
              onClick={uploadAndPreview}
              disabled={!csvText.trim() || loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Suivant
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview */}
      {step === 3 && preview && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Étape 3: Prévisualisation des données</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Total enregistrements</p>
              <p className="text-2xl font-bold text-neutral-900">{preview.total_records}</p>
            </div>
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Doublons détectés</p>
              <p className="text-2xl font-bold text-warning">{preview.duplicates || 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Statut</p>
              <p className="text-sm font-medium text-success mt-1">Prêt à importer</p>
            </div>
          </div>

          {preview.sample && preview.sample.length > 0 && (
            <div className="bg-white rounded-lg shadow-subtle p-4 mb-6">
              <h3 className="text-sm font-medium text-neutral-900 mb-2">Échantillon des données</h3>
              <div className="overflow-x-auto">
                <pre className="text-xs text-neutral-600 overflow-auto max-h-48">
                  {JSON.stringify(preview.sample, null, 2)}
                </pre>
              </div>
            </div>
          )}

          <div className="flex justify-between">
            <button onClick={() => setStep(2)} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Précédent
            </button>
            <button
              onClick={goToConfirmation}
              disabled={loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Suivant
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Confirmation */}
      {step === 4 && preview && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Étape 4: Confirmation de l'import</h2>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-blue-800">
              Vous êtes sur le point d'importer <strong>{preview.total_records} enregistrements</strong> depuis la source <strong>{source}</strong>.
              Cette opération ne peut pas être annulée.
            </p>
          </div>

          <div className="bg-white rounded-lg shadow-subtle p-4 mb-6">
            <h3 className="text-sm font-medium text-neutral-900 mb-3">Résumé de l'import</h3>
            <ul className="space-y-2 text-sm">
              <li className="flex justify-between">
                <span className="text-neutral-600">Source:</span>
                <span className="font-medium text-neutral-900">{source}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-neutral-600">Enregistrements:</span>
                <span className="font-medium text-neutral-900">{preview.total_records}</span>
              </li>
              <li className="flex justify-between">
                <span className="text-neutral-600">Doublons:</span>
                <span className="font-medium text-warning">{preview.duplicates || 0}</span>
              </li>
            </ul>
          </div>

          <div className="flex justify-between">
            <button onClick={() => setStep(3)} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Précédent
            </button>
            <button
              onClick={startImport}
              disabled={importLoading}
              className="flex items-center gap-2 px-4 py-2 bg-success text-white rounded-md text-sm font-medium hover:bg-success-600 transition-all duration-150 disabled:opacity-50"
            >
              {importLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Lancer l&apos;import
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Results */}
      {step === 5 && result && (
        <div>
          <h2 className="text-lg font-semibold text-neutral-900 mb-4">Étape 5: Résultats de l'import</h2>

          {/* Success/Error Alert */}
          {result.status === "completed" ? (
            <div className="bg-success-50 border border-success-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <Check className="w-5 h-5 text-success-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-success-900">Import réussi</h3>
                  <p className="text-success-700 text-sm mt-1">
                    Vos données ont été importées avec succès.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-danger-50 border border-danger-200 rounded-lg p-4 mb-6">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-danger-600 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="font-semibold text-danger-900">Erreur lors de l'import</h3>
                  <p className="text-danger-700 text-sm mt-1">
                    Une erreur s'est produite lors de l'import de vos données.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Statut</p>
              <p className={`text-lg font-bold ${result.status === "completed" ? "text-success" : "text-danger"}`}>
                {result.status === "completed" ? "Réussi" : "Erreur"}
              </p>
            </div>
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Importés</p>
              <p className="text-2xl font-bold text-success">{result.imported_records || 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Échoués</p>
              <p className="text-2xl font-bold text-danger">{result.failed_records || 0}</p>
            </div>
            <div className="bg-white rounded-lg shadow-subtle p-4">
              <p className="text-sm text-neutral-500">Total</p>
              <p className="text-2xl font-bold text-neutral-900">{result.total_records}</p>
            </div>
          </div>

          {result.error_log && result.error_log.length > 0 && (
            <div className="bg-danger-50 rounded-lg border border-danger-200 p-4 mb-6">
              <h3 className="text-sm font-medium text-danger-700 mb-2">Erreurs détectées</h3>
              <div className="bg-white rounded p-2 max-h-48 overflow-y-auto">
                <pre className="text-xs text-danger-600">
                  {JSON.stringify(result.error_log, null, 2)}
                </pre>
              </div>
            </div>
          )}

          <button
            onClick={() => { setStep(1); setSource(""); setJobId(""); setCsvText(""); setPreview(null); setResult(null); }}
            className="btn-primary"
          >
            Nouvelle migration
          </button>
        </div>
      )}
    </div>
  );
}
