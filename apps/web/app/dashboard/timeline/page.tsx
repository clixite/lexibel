"use client";

import { Clock } from "lucide-react";

export default function TimelinePage() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Clock className="w-6 h-6 text-blue-600" />
        <h1 className="text-2xl font-bold text-gray-900">Timeline</h1>
      </div>
      <div className="bg-white rounded-xl border border-gray-200 p-12 text-center">
        <Clock className="w-12 h-12 text-gray-300 mx-auto mb-4" />
        <p className="text-gray-500 text-lg">Bientôt disponible</p>
        <p className="text-gray-400 text-sm mt-1">
          La timeline des interactions et événements apparaîtra ici.
        </p>
      </div>
    </div>
  );
}
