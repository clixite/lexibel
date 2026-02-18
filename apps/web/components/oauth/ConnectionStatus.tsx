"use client";

import { useState, useEffect } from "react";
import { Check, Loader2, AlertCircle } from "lucide-react";

interface TestResult {
  scope: string;
  status: "pending" | "success" | "error";
  message?: string;
}

interface ConnectionStatusProps {
  provider: "google" | "microsoft";
  email: string;
  onComplete: () => void;
  onRetry: () => void;
}

export function ConnectionStatus({
  provider,
  email,
  onComplete,
  onRetry,
}: ConnectionStatusProps) {
  const [testing, setTesting] = useState(true);
  const [testResults, setTestResults] = useState<TestResult[]>([
    { scope: "Lecture emails", status: "pending" },
    { scope: "Envoi emails", status: "pending" },
    { scope: "Agenda", status: "pending" },
  ]);

  useEffect(() => {
    // Simulate connection testing
    const runTests = async () => {
      // Test 1: Email read
      await new Promise((resolve) => setTimeout(resolve, 1000));
      setTestResults((prev) =>
        prev.map((r, i) =>
          i === 0
            ? { ...r, status: "success", message: "142 emails trouvés" }
            : r
        )
      );

      // Test 2: Email send
      await new Promise((resolve) => setTimeout(resolve, 800));
      setTestResults((prev) =>
        prev.map((r, i) =>
          i === 1 ? { ...r, status: "success", message: "OK" } : r
        )
      );

      // Test 3: Calendar
      await new Promise((resolve) => setTimeout(resolve, 700));
      setTestResults((prev) =>
        prev.map((r, i) =>
          i === 2
            ? { ...r, status: "success", message: "23 événements" }
            : r
        )
      );

      setTesting(false);
    };

    runTests();
  }, []);

  const allSuccess = testResults.every((r) => r.status === "success");
  const hasError = testResults.some((r) => r.status === "error");

  return (
    <div className="w-full max-w-2xl mx-auto">
      <div className="bg-deep-slate-800/50 border border-deep-slate-700 rounded-xl p-6">
        {/* Success Header */}
        {allSuccess && (
          <div className="flex items-center gap-3 mb-6 p-4 rounded-lg bg-success-500/10 border border-success-500/20">
            <div className="p-2 rounded-full bg-success-500/20">
              <Check className="w-5 h-5 text-success-400" />
            </div>
            <div>
              <h3 className="font-semibold text-success-400">
                Connexion réussie !
              </h3>
              <p className="text-sm text-success-400/80 mt-0.5">
                Email connecté: {email}
              </p>
            </div>
          </div>
        )}

        {/* Error Header */}
        {hasError && (
          <div className="flex items-center gap-3 mb-6 p-4 rounded-lg bg-danger-500/10 border border-danger-500/20">
            <div className="p-2 rounded-full bg-danger-500/20">
              <AlertCircle className="w-5 h-5 text-danger-400" />
            </div>
            <div>
              <h3 className="font-semibold text-danger-400">
                Erreur de connexion
              </h3>
              <p className="text-sm text-danger-400/80 mt-0.5">
                Certaines autorisations ont échoué
              </p>
            </div>
          </div>
        )}

        {/* Provider Info */}
        <div className="mb-6">
          <div className="text-sm text-deep-slate-400">Email connecté</div>
          <div className="text-lg font-medium text-deep-slate-100 mt-1">
            {email}
          </div>
          <div className="text-sm text-deep-slate-500 mt-0.5">
            Fournisseur:{" "}
            {provider === "google" ? "Google Workspace" : "Microsoft 365"}
          </div>
        </div>

        {/* Test Results */}
        <div className="space-y-3 mb-6">
          <h4 className="text-sm font-medium text-deep-slate-300 mb-3">
            Test de connexion
          </h4>
          {testResults.map((result, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-3 rounded-lg bg-deep-slate-900/50"
            >
              <div className="flex items-center gap-3">
                {result.status === "pending" && (
                  <Loader2 className="w-4 h-4 text-warm-gold-500 animate-spin" />
                )}
                {result.status === "success" && (
                  <Check className="w-4 h-4 text-success-400" />
                )}
                {result.status === "error" && (
                  <AlertCircle className="w-4 h-4 text-danger-400" />
                )}
                <span className="text-sm font-medium text-deep-slate-200">
                  {result.scope}
                </span>
              </div>
              {result.message && (
                <span className="text-sm text-deep-slate-400">
                  {result.message}
                </span>
              )}
            </div>
          ))}
        </div>

        {/* Actions */}
        <div className="flex gap-3">
          {hasError && (
            <button
              onClick={onRetry}
              className="flex-1 px-4 py-2.5 rounded-lg border border-deep-slate-700 hover:bg-deep-slate-800 text-deep-slate-200 font-medium transition-colors"
            >
              Réessayer
            </button>
          )}
          <button
            onClick={onComplete}
            disabled={testing}
            className={`
              flex-1 px-4 py-2.5 rounded-lg font-medium transition-all
              ${
                testing || hasError
                  ? "bg-deep-slate-700 text-deep-slate-400 cursor-not-allowed"
                  : "bg-warm-gold-500 hover:bg-warm-gold-600 text-deep-slate-900"
              }
            `}
          >
            {testing ? "Test en cours..." : "Terminer"}
          </button>
        </div>
      </div>
    </div>
  );
}
