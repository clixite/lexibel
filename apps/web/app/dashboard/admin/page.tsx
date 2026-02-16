"use client";

import { useState } from "react";
import { Shield } from "lucide-react";
import UsersManager from "./UsersManager";
import TenantsManager from "./TenantsManager";
import SystemHealth from "./SystemHealth";

const TABS = [
  { id: "users", label: "Utilisateurs" },
  { id: "tenants", label: "Tenants" },
  { id: "system", label: "Système" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState<TabId>("users");

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Shield className="w-6 h-6 text-indigo-500" />
          Administration
        </h1>
        <p className="text-slate-500 mt-1">
          Gestion des utilisateurs, tenants et supervision système.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 border-b border-slate-200">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? "border-indigo-500 text-indigo-600"
                : "border-transparent text-slate-500 hover:text-slate-700"
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
