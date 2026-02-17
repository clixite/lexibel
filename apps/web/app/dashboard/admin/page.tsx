"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { Shield, Users, Building2, Activity, Plug } from "lucide-react";
import { useRouter } from "next/navigation";
import UsersManager from "./UsersManager";
import TenantsManager from "./TenantsManager";
import SystemHealth from "./SystemHealth";
import IntegrationsManager from "./IntegrationsManager";

const TABS = [
  { id: "users", label: "Utilisateurs", icon: Users, description: "Gestion des utilisateurs et permissions" },
  { id: "tenants", label: "Tenants", icon: Building2, description: "Administration des tenants" },
  { id: "system", label: "Système", icon: Activity, description: "Santé et statistiques système" },
  { id: "integrations", label: "Intégrations", icon: Plug, description: "Connexions OAuth et services" },
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
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-neutral-900 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
            <Shield className="w-6 h-6 text-accent" />
          </div>
          Administration
        </h1>
        <p className="text-neutral-600 mt-2 text-sm">
          Gérez les utilisateurs, tenants, santé système et intégrations externes.
        </p>
      </div>

      {/* Tab Navigation - Enhanced */}
      <div className="mb-8">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`p-4 rounded-lg border-2 transition-all duration-200 text-left group ${
                  isActive
                    ? "border-accent bg-accent-50 shadow-md"
                    : "border-neutral-200 bg-white hover:border-accent hover:shadow-subtle"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-colors ${
                    isActive
                      ? "bg-accent text-white"
                      : "bg-neutral-100 text-neutral-600 group-hover:bg-accent group-hover:text-white"
                  }`}>
                    <Icon className="w-5 h-5" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`font-semibold transition-colors ${
                      isActive ? "text-neutral-900" : "text-neutral-700 group-hover:text-neutral-900"
                    }`}>
                      {tab.label}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5 line-clamp-1">
                      {tab.description}
                    </p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="animate-in fade-in duration-200">
        {activeTab === "users" && <UsersManager />}
        {activeTab === "tenants" && <TenantsManager />}
        {activeTab === "system" && <SystemHealth />}
        {activeTab === "integrations" && <IntegrationsManager />}
      </div>
    </div>
  );
}
