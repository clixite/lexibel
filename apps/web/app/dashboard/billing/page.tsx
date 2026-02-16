"use client";

import { FileText } from "lucide-react";

export default function BillingPage() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <FileText className="w-6 h-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Facturation</h1>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <FileText className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500 text-lg">Bientôt disponible</p>
        <p className="text-gray-400 text-sm mt-1">
          La gestion de facturation et Peppol sera disponible prochainement.
        </p>
      </div>
    </div>
  );
}
