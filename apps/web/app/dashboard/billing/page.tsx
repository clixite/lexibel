"use client";

import { useState, useRef, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import {
  Clock,
  FileText,
  Landmark,
  Activity,
  LayoutDashboard,
  PlusCircle,
} from "lucide-react";
import { useAuth } from "@/lib/useAuth";
import TimesheetView from "./TimesheetView";
import InvoiceList from "./InvoiceList";
import ThirdPartyView from "./ThirdPartyView";
import BillingDashboard from "./BillingDashboard";
import InvoiceCreation from "./InvoiceCreation";
import TimerWidget from "@/components/TimerWidget";
import Card from "@/components/ui/Card";
import Badge from "@/components/ui/Badge";

interface Tab {
  id: string;
  label: string;
  icon: React.ReactNode;
}

const TAB_DEFS: Tab[] = [
  {
    id: "dashboard",
    label: "Tableau de bord",
    icon: <LayoutDashboard className="w-4 h-4" />,
  },
  {
    id: "timesheet",
    label: "Prestations",
    icon: <Clock className="w-4 h-4" />,
  },
  {
    id: "invoices",
    label: "Factures",
    icon: <FileText className="w-4 h-4" />,
  },
  {
    id: "create-invoice",
    label: "Creer facture",
    icon: <PlusCircle className="w-4 h-4" />,
  },
  {
    id: "third-party",
    label: "Compte Tiers",
    icon: <Landmark className="w-4 h-4" />,
  },
];

type TabId = string;

function resolveInitialTab(param: string | null): TabId {
  if (param && TAB_DEFS.some((t) => t.id === param)) return param;
  return "dashboard";
}

export default function BillingPage() {
  const searchParams = useSearchParams();
  const { accessToken, tenantId } = useAuth();
  const initialTab = resolveInitialTab(searchParams?.get("tab") ?? null);
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

  // --- Callbacks for child components ---
  const handleInvoiceCreated = () => {
    setActiveTab("invoices");
  };

  const handleCancelCreation = () => {
    setActiveTab("invoices");
  };

  const handleCreateInvoiceFromDashboard = () => {
    setActiveTab("create-invoice");
  };

  // --- Render tab content ---
  const renderContent = () => {
    switch (activeTab) {
      case "dashboard":
        return (
          <BillingDashboard
            accessToken={accessToken}
            tenantId={tenantId}
            onCreateInvoice={handleCreateInvoiceFromDashboard}
          />
        );
      case "timesheet":
        return <TimesheetView />;
      case "invoices":
        return <InvoiceList />;
      case "create-invoice":
        return (
          <InvoiceCreation
            accessToken={accessToken}
            tenantId={tenantId}
            onCreated={handleInvoiceCreated}
            onCancel={handleCancelCreation}
          />
        );
      case "third-party":
        return <ThirdPartyView />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Section */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold text-neutral-900">Facturation</h1>
        <p className="text-neutral-500">
          Gerez vos prestations, factures et comptes tiers
        </p>
      </div>

      {/* Timer Widget Prominent */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="md:col-span-2 bg-gradient-to-br from-accent-50 to-white border border-accent-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-neutral-600 mb-2">
                Chronometre actif
              </p>
              <div className="text-5xl font-mono font-bold text-accent tracking-tighter">
                {formatTimerDisplay(timerSeconds)}
              </div>
              <p className="text-xs text-neutral-500 mt-2">
                Temps enregistre pour cette session
              </p>
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
            <p className="text-xs text-neutral-600 font-medium">
              SESSION EN COURS
            </p>
            <p className="text-2xl font-bold text-success">Ready</p>
          </div>
        </Card>
      </div>

      {/* Premium Tabs Component */}
      <Card className="overflow-hidden border border-neutral-200 shadow-lg">
        {/* Tab Headers with Animated Indicator */}
        <div className="relative border-b border-neutral-200 bg-neutral-50/50 backdrop-blur-sm px-2">
          <div className="flex gap-1 overflow-x-auto">
            {TAB_DEFS.map((tab) => (
              <button
                key={tab.id}
                ref={(el) => {
                  tabRefs.current[tab.id] = el;
                }}
                onClick={() => setActiveTab(tab.id)}
                className={`
                  relative px-4 py-3.5 text-sm font-medium transition-all duration-300
                  flex items-center gap-2.5 whitespace-nowrap
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
          <div className="animate-fadeIn">{renderContent()}</div>
        </div>
      </Card>

      {/* Floating Timer Widget */}
      <TimerWidget variant="floating" onTimeUpdate={handleTimeUpdate} />
    </div>
  );
}
