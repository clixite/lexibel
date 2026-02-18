"use client";

import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { Clock, FileText, Landmark, Activity } from "lucide-react";
import TimesheetView from "./TimesheetView";
import InvoiceList from "./InvoiceList";
import ThirdPartyView from "./ThirdPartyView";
import TimerWidget from "@/components/TimerWidget";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

interface Tab {
  id: string;
  label: string;
  content: React.ReactNode;
  icon: React.ReactNode;
}

const TABS: Tab[] = [
  {
    id: "timesheet",
    label: "Prestations",
    icon: <Clock className="w-4 h-4" />,
    content: <TimesheetView />
  },
  {
    id: "invoices",
    label: "Factures",
    icon: <FileText className="w-4 h-4" />,
    content: <InvoiceList />
  },
  {
    id: "third-party",
    label: "Compte Tiers",
    icon: <Landmark className="w-4 h-4" />,
    content: <ThirdPartyView />
  },
] as const;

type TabId = (typeof TABS)[number]["id"];

export default function BillingPage() {
  const searchParams = useSearchParams();
  const initialTab = searchParams?.get("tab") === "invoices" ? "invoices" : "timesheet";
  const [activeTab, setActiveTab] = useState<TabId>(initialTab);
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });
  const tabRefs = useRef<{ [key: string]: HTMLButtonElement | null }>({});
  const [timerSeconds, setTimerSeconds] = useState(0);

  // Update indicator position
  useEffect(() => {
    const activeElement = tabRefs.current[activeTab];
    if (activeElement) {
      setIndicatorStyle({
        left: activeElement.offsetLeft,
        width: activeElement.offsetWidth,
      });
    }
  }, [activeTab]);

  const handleTimeUpdate = (seconds: number) => {
    setTimerSeconds(seconds);
  };

  const formatTimerDisplay = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours.toString().padStart(2, "0")}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  };

  const activeTabData = TABS.find((tab) => tab.id === activeTab);

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-neutral-900">Facturation</h1>
        <p className="text-neutral-500">Gérez vos prestations, factures et comptes tiers</p>
      </div>

      {/* Timer Widget Prominent */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2 bg-gradient-to-br from-accent-50 to-white border border-accent-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-600 mb-2">Chronomètre actif</p>
              <div className="text-5xl font-mono font-bold text-accent tracking-tighter">
                {formatTimerDisplay(timerSeconds)}
              </div>
              <p className="text-xs text-neutral-500 mt-2">Temps enregistré pour cette session</p>
            </div>
            <div className="flex items-center justify-center w-20 h-20 rounded-full bg-accent/10">
              <Activity className="w-10 h-10 text-accent animate-pulse" />
            </div>
          </div>
        </Card>

        {/* Quick Stats */}
        <Card className="bg-gradient-to-br from-success-50 to-white border border-success-100">
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge variant="success" size="sm" dot>
                Actif
              </Badge>
            </div>
            <p className="text-xs text-neutral-600 font-medium">SESSION EN COURS</p>
            <p className="text-2xl font-bold text-success">Ready</p>
          </div>
        </Card>
      </div>

      {/* Premium Tabs Component */}
      <Card className="overflow-hidden border border-neutral-200 shadow-lg">
        {/* Tab Headers with Animated Indicator */}
        <div className="relative border-b border-neutral-200 bg-neutral-50/50 backdrop-blur-sm px-2">
          <div className="flex gap-1">
            {TABS.map((tab) => (
              <button
                key={tab.id}
                ref={(el) => {
                  tabRefs.current[tab.id] = el;
                }}
                onClick={() => setActiveTab(tab.id as TabId)}
                className={`
                  relative px-4 py-3.5 text-sm font-medium transition-all duration-300
                  flex items-center gap-2.5
                  ${
                    activeTab === tab.id
                      ? "text-accent"
                      : "text-neutral-600 hover:text-neutral-900"
                  }
                `}
              >
                <span className="inline-flex">{tab.icon}</span>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Animated Indicator Bar */}
          <div
            className="absolute bottom-0 h-0.5 bg-gradient-to-r from-accent via-accent to-accent-700 shadow-lg transition-all duration-500 ease-out"
            style={{
              left: `${indicatorStyle.left}px`,
              width: `${indicatorStyle.width}px`,
            }}
          />
        </div>

        {/* Tab Content */}
        <div className="p-6 md:p-8 bg-white/95 backdrop-blur-sm">
          <div className="animate-fadeIn">
            {activeTabData?.content}
          </div>
        </div>
      </Card>

      {/* Floating Timer Widget */}
      <TimerWidget variant="floating" onTimeUpdate={handleTimeUpdate} />
    </div>
  );
}
