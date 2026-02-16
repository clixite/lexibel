"use client";

import { useState } from "react";
import { FileText, Clock, Landmark } from "lucide-react";
import TimesheetView from "./TimesheetView";
import InvoiceList from "./InvoiceList";
import ThirdPartyView from "./ThirdPartyView";

const TABS = [
  { id: "timesheet", label: "Timesheet", icon: Clock },
  { id: "invoices", label: "Factures", icon: FileText },
  { id: "third-party", label: "Compte Tiers", icon: Landmark },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function BillingPage() {
  const [activeTab, setActiveTab] = useState<TabId>("timesheet");

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">Facturation</h1>
      </div>

      {/* Tab bar */}
      <div className="flex gap-1 mb-6 bg-neutral-100 rounded-md p-1 w-fit">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all duration-150 ${
              activeTab === tab.id
                ? "bg-white text-neutral-900 shadow-subtle"
                : "text-neutral-500 hover:text-neutral-700"
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === "timesheet" && <TimesheetView />}
      {activeTab === "invoices" && <InvoiceList />}
      {activeTab === "third-party" && <ThirdPartyView />}
    </div>
  );
}
