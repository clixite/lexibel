"use client";

import { Scale } from "lucide-react";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="fr">
      <body className="font-sans antialiased">
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800 px-4">
          <div className="w-full max-w-md text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent shadow-lg shadow-accent/20 mb-6">
              <Scale className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold text-white mb-3">
              Erreur inattendue
            </h1>
            <p className="text-neutral-400 mb-6 text-sm">
              Une erreur est survenue. Veuillez rafraichir la page.
            </p>
            <button
              onClick={() => reset()}
              className="px-6 py-2.5 bg-accent hover:bg-accent-600 text-white font-medium rounded-md transition-colors"
            >
              Rafraichir la page
            </button>
          </div>
        </div>
      </body>
    </html>
  );
}
