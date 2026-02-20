"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-8">
      <div className="text-center max-w-md">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-danger-100 mb-4">
          <AlertTriangle className="w-7 h-7 text-danger-600" />
        </div>
        <h2 className="text-xl font-display font-semibold text-neutral-900 mb-2">
          Erreur de chargement
        </h2>
        <p className="text-sm text-neutral-600 mb-6">
          Une erreur est survenue lors du chargement de cette page.
          {error.message && (
            <span className="block mt-2 text-xs text-neutral-400 font-mono">
              {error.message}
            </span>
          )}
        </p>
        <button
          onClick={() => reset()}
          className="inline-flex items-center gap-2 px-5 py-2.5 bg-accent hover:bg-accent-600 text-white font-medium rounded-md transition-colors text-sm"
        >
          <RefreshCw className="w-4 h-4" />
          Reessayer
        </button>
      </div>
    </div>
  );
}
