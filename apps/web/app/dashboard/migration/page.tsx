"use client";

import { useAuth } from "@/lib/useAuth";
import { useState } from "react";
import { Upload, ArrowRight, ArrowLeft, Check, Loader2, AlertCircle, FileUp, Eye, CheckCircle2 } from "lucide-react";
import { apiFetch } from "@/lib/api";

type Step = 1 | 2 | 3 | 4 | 5;

const SOURCES = [
  { id: "veoCRM", label: "VeoCRM", description: "Import depuis VeoCRM", icon: "database" },
  { id: "custom", label: "Source personnalisée", description: "Import depuis fichier CSV", icon: "upload" },
];

const STEP_LABELS = ["Source", "Upload", "Preview", "Confirmation", "Résultats"];
const STEP_ICONS = [Upload, FileUp, Eye, CheckCircle2, Check];

export default function MigrationPage() {
  const { accessToken } = useAuth();
  const [step, setStep] = useState<Step>(1);
  const [source, setSource] = useState<string>("");
  const [jobId, setJobId] = useState<string>("");
  const [csvText, setCsvText] = useState<string>("");
  const [preview, setPreview] = useState<any>(null);
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [importLoading, setImportLoading] = useState(false);

  // Progress calculation
  const progressPercent = (step / 5) * 100;

  const createJob = async () => {
    if (!accessToken || !source) return;
    setLoading(true);
    setError(null);
    try {
      const job = await apiFetch<any>("/api/v1/migration/jobs", accessToken, {
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
    if (!accessToken || !jobId || !csvText.trim()) return;
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
        accessToken,
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
    if (!accessToken || !jobId) return;
    setImportLoading(true);
    setError(null);
    try {
      const importResult = await apiFetch<any>(
        `/api/v1/migration/import`,
        accessToken,
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
          Centre de Migration
        </h1>
        <p className="text-neutral-500 mt-1 text-sm">
          Importez vos données depuis VeoCRM ou une source personnalisée en 5 étapes simples.
        </p>
      </div>

      {/* Progress Bar - Enhanced Visual */}
      <div className="mb-8 bg-white rounded-lg shadow-subtle p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-semibold text-neutral-900">Progression</span>
          <span className="text-sm font-bold text-accent">{Math.round(progressPercent)}%</span>
        </div>
        <div className="h-2.5 bg-neutral-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-gradient-to-r from-accent to-accent-600 transition-all duration-300 shadow-md"
            style={{ width: `${progressPercent}%` }}
          />
        </div>
        <div className="mt-2 text-xs text-neutral-500">
          Étape {step} sur 5
        </div>
      </div>

      {/* Step indicator - Enhanced */}
      <div className="mb-8 overflow-x-auto">
        <div className="flex items-center gap-3 min-w-full pb-2">
          {STEP_LABELS.map((label, i) => {
            const IconComponent = STEP_ICONS[i];
            const isCompleted = i + 1 < step;
            const isActive = i + 1 === step;

            return (
              <div key={label} className="flex items-center gap-3 flex-shrink-0">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-medium transition-all duration-200 shadow-sm ${
                    isActive
                      ? "bg-accent text-white shadow-md"
                      : isCompleted
                        ? "bg-success text-white"
                        : "bg-neutral-100 text-neutral-400"
                  }`}
                >
                  {isCompleted ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <IconComponent className="w-5 h-5" />
                  )}
                </div>
                <span className={`text-sm whitespace-nowrap font-medium ${
                  isActive ? "text-neutral-900" : isCompleted ? "text-success" : "text-neutral-500"
                }`}>
                  {label}
                </span>
                {i < STEP_LABELS.length - 1 && (
                  <div className={`w-8 h-0.5 transition-colors flex-shrink-0 ${isCompleted ? "bg-success" : "bg-neutral-200"}`} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Step 1: Select source */}
      {step === 1 && (
        <div className="card">
          <h2 className="text-lg font-semibold text-neutral-900 mb-6">Sélectionnez la source d'import</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            {SOURCES.map((s) => (
              <button
                key={s.id}
                onClick={() => setSource(s.id)}
                className={`p-6 rounded-lg border-2 text-left transition-all duration-200 ${
                  source === s.id
                    ? "border-accent bg-accent-50 shadow-md"
                    : "border-neutral-200 bg-white hover:border-accent hover:shadow-md"
                }`}
              >
                <div className="flex items-start gap-4">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    source === s.id ? "bg-accent text-white" : "bg-neutral-100 text-accent"
                  }`}>
                    {s.icon === "database" ? (
                      <svg className="w-6 h-6" fill="currentColor" viewBox="0 0 20 20">
                        <path d="M3 12a9 9 0 0115.64-3.684m4.684-1.261A9.009 9.009 0 0012.5.5a.75.75 0 00-.75.75v4.5a.75.75 0 00.75.75h4.5a.75.75 0 00.75-.75z" />
                      </svg>
                    ) : (
                      <FileUp className="w-6 h-6" />
                    )}
                  </div>
                  <div className="flex-1">
                    <p className="font-semibold text-neutral-900">{s.label}</p>
                    <p className="text-sm text-neutral-500 mt-1">{s.description}</p>
                  </div>
                  {source === s.id && (
                    <Check className="w-5 h-5 text-accent flex-shrink-0 mt-1" />
                  )}
                </div>
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
        <div className="card">
          <h2 className="text-lg font-semibold text-neutral-900 mb-6">Téléchargez votre fichier CSV</h2>

          <div className="bg-accent-50 border border-accent-200 rounded-lg p-4 mb-6">
            <p className="text-sm text-accent-800">
              Format attendu: <code className="font-mono bg-white px-2 py-1 rounded">reference,title,type,status</code>
            </p>
          </div>

          <div className="mb-6">
            <label className="block text-sm font-semibold text-neutral-900 mb-3">
              Contenu du fichier CSV
            </label>
            <textarea
              value={csvText}
              onChange={(e) => setCsvText(e.target.value)}
              placeholder={"reference,title,type,status\nDOS-001,Dossier Test,general,open\nDOS-002,Dossier 2,litigation,pending"}
              className="input h-64 font-mono text-xs resize-none"
            />
            <p className="text-xs text-neutral-500 mt-2">
              {csvText.split('\n').length - 1} ligne(s) de données
            </p>
          </div>

          <div className="flex justify-between gap-3">
            <button onClick={() => setStep(1)} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Précédent
            </button>
            <button
              onClick={uploadAndPreview}
              disabled={!csvText.trim() || loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Prévisualiser
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview */}
      {step === 3 && preview && (
        <div className="card">
          <h2 className="text-lg font-semibold text-neutral-900 mb-6">Vérification des données</h2>

          {/* Statistics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200">
              <p className="text-sm text-blue-700 font-medium">Enregistrements</p>
              <p className="text-3xl font-bold text-blue-900 mt-2">{preview.total_records}</p>
            </div>
            <div className={`card bg-gradient-to-br ${
              (preview.duplicates || 0) > 0
                ? "from-warning-50 to-warning-100 border-warning-200"
                : "from-success-50 to-success-100 border-success-200"
            }`}>
              <p className={`text-sm font-medium ${
                (preview.duplicates || 0) > 0 ? "text-warning-700" : "text-success-700"
              }`}>
                Doublons
              </p>
              <p className={`text-3xl font-bold mt-2 ${
                (preview.duplicates || 0) > 0 ? "text-warning-900" : "text-success-900"
              }`}>
                {preview.duplicates || 0}
              </p>
            </div>
            <div className="card bg-gradient-to-br from-success-50 to-success-100 border border-success-200">
              <p className="text-sm text-success-700 font-medium">Statut</p>
              <div className="flex items-center gap-2 mt-2">
                <div className="w-2 h-2 rounded-full bg-success animate-pulse"></div>
                <p className="text-sm font-semibold text-success-900">Prêt à importer</p>
              </div>
            </div>
          </div>

          {/* Data Preview */}
          {preview.sample && preview.sample.length > 0 && (
            <div className="card bg-neutral-50 border border-neutral-200 mb-6">
              <h3 className="text-sm font-semibold text-neutral-900 mb-3">Aperçu des données</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-neutral-200">
                      {Object.keys(preview.sample[0] || {}).map((key) => (
                        <th key={key} className="text-left py-2 px-3 text-neutral-600 font-semibold">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.sample.slice(0, 5).map((row: any, idx: number) => (
                      <tr key={idx} className="border-b border-neutral-100 hover:bg-neutral-100 transition-colors">
                        {Object.values(row).map((val: any, i: number) => (
                          <td key={i} className="py-2 px-3 text-neutral-700">
                            {String(val).substring(0, 30)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
                {preview.sample.length > 5 && (
                  <p className="text-xs text-neutral-500 py-2 px-3 bg-neutral-100">
                    ...et {preview.sample.length - 5} ligne(s) supplémentaire(s)
                  </p>
                )}
              </div>
            </div>
          )}

          <div className="flex justify-between gap-3">
            <button onClick={() => setStep(2)} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Précédent
            </button>
            <button
              onClick={goToConfirmation}
              disabled={loading}
              className="btn-primary flex items-center gap-2"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
              Confirmer
            </button>
          </div>
        </div>
      )}

      {/* Step 4: Confirmation */}
      {step === 4 && preview && (
        <div className="card">
          <h2 className="text-lg font-semibold text-neutral-900 mb-6">Confirmez l'import</h2>

          {/* Warning Alert */}
          <div className="bg-warning-50 border border-warning-200 rounded-lg p-4 mb-6 flex gap-3">
            <AlertCircle className="w-5 h-5 text-warning-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-warning-900">Attention</p>
              <p className="text-sm text-warning-800 mt-1">
                Vous êtes sur le point d'importer <strong>{preview.total_records} enregistrements</strong> depuis <strong>{SOURCES.find(s => s.id === source)?.label}</strong>.
                Cette opération ne peut pas être annulée.
              </p>
            </div>
          </div>

          {/* Summary */}
          <div className="card bg-neutral-50 mb-6">
            <h3 className="text-sm font-semibold text-neutral-900 mb-4">Résumé de l'import</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-white rounded-lg p-4 border border-neutral-200">
                <p className="text-xs text-neutral-600 font-medium uppercase tracking-wide">Source</p>
                <p className="text-lg font-semibold text-neutral-900 mt-2">
                  {SOURCES.find(s => s.id === source)?.label}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-neutral-200">
                <p className="text-xs text-neutral-600 font-medium uppercase tracking-wide">Enregistrements</p>
                <p className="text-lg font-semibold text-neutral-900 mt-2">
                  {preview.total_records}
                </p>
              </div>
              <div className="bg-white rounded-lg p-4 border border-neutral-200">
                <p className="text-xs text-neutral-600 font-medium uppercase tracking-wide">Doublons</p>
                <p className={`text-lg font-semibold mt-2 ${
                  (preview.duplicates || 0) > 0 ? "text-warning-600" : "text-success-600"
                }`}>
                  {preview.duplicates || 0}
                </p>
              </div>
            </div>
          </div>

          <div className="flex justify-between gap-3">
            <button onClick={() => setStep(3)} className="btn-secondary flex items-center gap-2">
              <ArrowLeft className="w-4 h-4" /> Annuler
            </button>
            <button
              onClick={startImport}
              disabled={importLoading}
              className="flex items-center gap-2 px-6 py-2.5 bg-success text-white rounded-md text-sm font-semibold hover:bg-success-600 transition-all duration-150 disabled:opacity-50 shadow-sm"
            >
              {importLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
              Lancer l&apos;import
            </button>
          </div>
        </div>
      )}

      {/* Step 5: Results */}
      {step === 5 && result && (
        <div className="card">
          <h2 className="text-lg font-semibold text-neutral-900 mb-6">Résultats de l'import</h2>

          {/* Success/Error Alert */}
          {result.status === "completed" ? (
            <div className="bg-gradient-to-r from-success-50 to-success-100 border border-success-300 rounded-lg p-5 mb-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-success text-white flex items-center justify-center flex-shrink-0">
                  <Check className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-success-900 text-lg">Import réussi</h3>
                  <p className="text-success-800 text-sm mt-1">
                    Tous vos enregistrements ont été importés avec succès dans LexiBel.
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gradient-to-r from-danger-50 to-danger-100 border border-danger-300 rounded-lg p-5 mb-6">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-danger text-white flex items-center justify-center flex-shrink-0">
                  <AlertCircle className="w-6 h-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-bold text-danger-900 text-lg">Erreur lors de l'import</h3>
                  <p className="text-danger-800 text-sm mt-1">
                    Certains enregistrements n'ont pas pu être importés. Consultez les erreurs ci-dessous.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Statistics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className={`card ${result.status === "completed" ? "bg-gradient-to-br from-success-50 to-success-100 border-success-200" : "bg-gradient-to-br from-danger-50 to-danger-100 border-danger-200"}`}>
              <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Statut</p>
              <p className={`text-2xl font-bold mt-2 ${result.status === "completed" ? "text-success-900" : "text-danger-900"}`}>
                {result.status === "completed" ? "Réussi" : "Erreur"}
              </p>
            </div>
            <div className="card bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
              <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Importés</p>
              <p className="text-2xl font-bold mt-2 text-blue-900">{result.imported_records || 0}</p>
            </div>
            <div className="card bg-gradient-to-br from-warning-50 to-warning-100 border-warning-200">
              <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Échoués</p>
              <p className="text-2xl font-bold mt-2 text-warning-900">{result.failed_records || 0}</p>
            </div>
            <div className="card bg-gradient-to-br from-neutral-100 to-neutral-200 border-neutral-300">
              <p className="text-xs text-neutral-600 font-semibold uppercase tracking-wider">Total</p>
              <p className="text-2xl font-bold mt-2 text-neutral-900">{result.total_records}</p>
            </div>
          </div>

          {/* Error Log */}
          {result.error_log && result.error_log.length > 0 && (
            <div className="bg-danger-50 rounded-lg border border-danger-200 p-4 mb-6">
              <h3 className="text-sm font-semibold text-danger-900 mb-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                Erreurs détectées ({result.error_log.length})
              </h3>
              <div className="bg-white rounded-lg p-3 max-h-64 overflow-y-auto">
                <pre className="text-xs text-danger-700 font-mono whitespace-pre-wrap break-words">
                  {JSON.stringify(result.error_log, null, 2)}
                </pre>
              </div>
            </div>
          )}

          {/* Success Summary */}
          {result.status === "completed" && (
            <div className="bg-blue-50 rounded-lg border border-blue-200 p-4 mb-6">
              <h3 className="text-sm font-semibold text-blue-900 mb-2">Prochaines étapes</h3>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>✓ Vos données sont maintenant disponibles dans LexiBel</li>
                <li>✓ Vous pouvez commencer à les utiliser dans vos dossiers</li>
                <li>✓ Consultez le tableau de bord pour voir les statistiques d'import</li>
              </ul>
            </div>
          )}

          <button
            onClick={() => { setStep(1); setSource(""); setJobId(""); setCsvText(""); setPreview(null); setResult(null); }}
            className="btn-primary w-full"
          >
            Nouvelle migration
          </button>
        </div>
      )}
    </div>
  );
}
