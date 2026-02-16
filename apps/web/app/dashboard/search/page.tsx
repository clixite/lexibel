"use client";

import { Search } from "lucide-react";

export default function SearchPage() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Recherche</h1>
      </div>
      <div className="relative bg-white rounded-lg shadow-subtle overflow-hidden">
        <div className="absolute inset-0 opacity-[0.03]">
          <div
            className="w-full h-full"
            style={{
              backgroundImage:
                "radial-gradient(circle at 1px 1px, currentColor 1px, transparent 0)",
              backgroundSize: "24px 24px",
            }}
          />
        </div>
        <div className="relative px-6 py-20 text-center">
          <div className="w-16 h-16 rounded-lg bg-success-50 flex items-center justify-center mx-auto mb-5">
            <Search className="w-8 h-8 text-success" />
          </div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">
            Recherche globale
          </h2>
          <p className="text-neutral-500 text-sm max-w-md mx-auto mb-6">
            Recherche full-text &agrave; travers tous vos dossiers, contacts,
            documents et interactions. Filtres avanc&eacute;s et
            r&eacute;sultats instantan&eacute;s.
          </p>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
            Disponible Sprint 15
          </span>
        </div>
      </div>
    </div>
  );
}
