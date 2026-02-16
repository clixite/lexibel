"use client";

import { Inbox } from "lucide-react";

export default function InboxPage() {
  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Inbox</h1>
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
          <div className="w-16 h-16 rounded-lg bg-warning-50 flex items-center justify-center mx-auto mb-5">
            <Inbox className="w-8 h-8 text-warning" />
          </div>
          <h2 className="text-xl font-semibold text-neutral-900 mb-2">
            Inbox centralis&eacute;e
          </h2>
          <p className="text-neutral-500 text-sm max-w-md mx-auto mb-6">
            Tous vos &eacute;l&eacute;ments &agrave; valider au m&ecirc;me
            endroit : emails, appels, transcriptions, documents
            re&ccedil;us. Triez, priorisez et traitez efficacement.
          </p>
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
            Disponible Sprint 14
          </span>
        </div>
      </div>
    </div>
  );
}
