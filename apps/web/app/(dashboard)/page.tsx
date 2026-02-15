"use client";

import { useSession } from "next-auth/react";
import { Briefcase, Clock, FileText, Inbox, Loader2 } from "lucide-react";

const STAT_CARDS = [
  { label: "Dossiers actifs", value: "—", icon: Briefcase, color: "text-primary" },
  { label: "Heures ce mois", value: "—", icon: Clock, color: "text-secondary" },
  { label: "Factures en attente", value: "—", icon: FileText, color: "text-accent" },
  { label: "Inbox", value: "—", icon: Inbox, color: "text-success" },
];

export default function DashboardPage() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  const userName = session?.user?.name || session?.user?.email || "Utilisateur";

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Bienvenue sur LexiBel
        </h1>
        <p className="text-gray-500 mt-1">
          Bonjour {userName}, voici votre tableau de bord.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {STAT_CARDS.map((card) => (
          <div key={card.label} className="card flex items-center gap-4">
            <div className={`p-3 rounded-lg bg-gray-50 ${card.color}`}>
              <card.icon className="w-6 h-6" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">{card.value}</p>
              <p className="text-sm text-gray-500">{card.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Placeholder sections */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Activité récente
          </h3>
          <p className="text-sm text-gray-400">
            Les interactions récentes apparaîtront ici.
          </p>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Inbox — À traiter
          </h3>
          <p className="text-sm text-gray-400">
            Les éléments en attente de validation apparaîtront ici.
          </p>
        </div>
      </div>
    </div>
  );
}
