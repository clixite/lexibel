"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { Shield } from "lucide-react";
import { useRouter } from "next/navigation";
import UsersManager from "./UsersManager";
import TenantsManager from "./TenantsManager";
import SystemHealth from "./SystemHealth";
import IntegrationsManager from "./IntegrationsManager";

const TABS = [
  { id: "users", label: "Utilisateurs" },
  { id: "tenants", label: "Tenants" },
  { id: "system", label: "Système" },
  { id: "integrations", label: "Intégrations" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AdminPage() {
  const { data: session } = useSession();
  const [activeTab, setActiveTab] = useState<TabId>("users");
  const router = useRouter();

  // Protection: only super_admin can access
  const userRole = (session?.user as any)?.role;
  if (session && userRole !== "super_admin") {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-danger-900 mb-2">Accès refusé</h2>
        <p className="text-danger-700 text-sm mb-4">
          Vous n'avez pas les permissions pour accéder à cette page.
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="btn-primary"
        >
          Retour au tableau de bord
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2">
          <Shield className="w-6 h-6 text-accent" />
          Administration
        </h1>
        <p className="text-neutral-500 mt-1 text-sm">
          Gestion des utilisateurs, tenants et supervision système.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-neutral-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-all duration-150 ${
              activeTab === tab.id
                ? "border-accent text-accent"
                : "border-transparent text-neutral-500 hover:text-neutral-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      {activeTab === "users" && <UsersManager />}
      {activeTab === "tenants" && <TenantsManager />}
      {activeTab === "system" && <SystemHealth />}
      {activeTab === "integrations" && <IntegrationsManager />}
    </div>
  );
}
