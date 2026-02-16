"use client";

import { useSession } from "next-auth/react";
import { Briefcase, Users, Clock, FileText, Loader2 } from "lucide-react";

export default function DashboardPage() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const user = session?.user as any;
  const email = user?.email || "Utilisateur";
  const role = user?.role || "";
  const tenantId = user?.tenantId || "";

  const STAT_CARDS = [
    { label: "Dossiers ouverts", value: "—", icon: Briefcase, color: "bg-blue-50 text-blue-600" },
    { label: "Contacts", value: "—", icon: Users, color: "bg-green-50 text-green-600" },
    { label: "Heures ce mois", value: "—", icon: Clock, color: "bg-amber-50 text-amber-600" },
    { label: "Factures en attente", value: "—", icon: FileText, color: "bg-red-50 text-red-600" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">
          Bienvenue sur LexiBel
        </h1>
        <p className="text-gray-500 mt-1">
          Bonjour <span className="font-medium text-gray-700">{email}</span>
        </p>
        <div className="flex gap-4 mt-2 text-xs text-gray-400">
          <span>Role: <span className="text-gray-600">{role}</span></span>
          {tenantId && <span>Tenant: <span className="text-gray-600">{tenantId}</span></span>}
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {STAT_CARDS.map((card) => (
          <div
            key={card.label}
            className="bg-white rounded-xl border border-gray-200 p-5 flex items-center gap-4"
          >
            <div className={`p-3 rounded-lg ${card.color}`}>
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
        <div className="bg-white rounded-xl border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Activité récente
          </h3>
          <p className="text-sm text-gray-400">
            Les interactions récentes apparaîtront ici.
          </p>
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6">
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
