"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import UsersManager from "./UsersManager";
import TenantsManager from "./TenantsManager";
import SystemHealth from "./SystemHealth";

const TABS = [
  { id: "users", label: "Utilisateurs" },
  { id: "tenants", label: "Tenants" },
  { id: "system", label: "Syst\u00e8me" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>("users");

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900 flex items-center gap-2">
          <Shield className="w-6 h-6 text-accent" />
          Administration
        </h1>
        <p className="text-neutral-500 mt-1 text-sm">
          Gestion des utilisateurs, tenants et supervision syst&egrave;me.
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
    </div>
  );
}
