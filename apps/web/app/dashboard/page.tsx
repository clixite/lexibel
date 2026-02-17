"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import {
  Briefcase,
  Users,
  Clock,
  FileText,
  Mail,
  Phone,
  FileCheck,
  CalendarDays,
  Folder,
  Inbox,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import SkeletonCard from "@/components/skeletons/SkeletonCard";

interface DashboardStats {
  cases: number;
  contacts: number;
  hoursThisMonth: number;
  invoices: number;
  documents: number;
  inboxPending: number;
}

interface RecentCase {
  id: string;
  title: string;
  updated_at: string;
}

interface InboxItem {
  id: string;
  subject: string;
  item_type: string;
  from_name?: string;
}

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [statsLoading, setStatsLoading] = useState(true);
  const [recentCases, setRecentCases] = useState<RecentCase[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);

  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  useEffect(() => {
    if (!token) return;

    // Fetch stats and recent data
    Promise.all([
      apiFetch<{ items: any[] }>("/cases", token, { tenantId }).catch(() => ({ items: [] })),
      apiFetch<{ items: any[] }>("/contacts", token, { tenantId }).catch(() => ({ items: [] })),
      apiFetch<{ items: any[] }>("/time-entries", token, { tenantId }).catch(() => ({ items: [] })),
      apiFetch<{ items: any[] }>("/invoices", token, { tenantId }).catch(() => ({ items: [] })),
      apiFetch<{ items: any[] }>("/inbox?status=pending", token, { tenantId }).catch(() => ({ items: [] })),
      apiFetch<{ items: any[] }>("/cases?per_page=5&sort=-updated_at", token, { tenantId }).catch(() => ({ items: [] })),
      apiFetch<{ items: any[] }>("/inbox?status=pending&per_page=5", token, { tenantId }).catch(() => ({ items: [] })),
    ])
      .then(([
        casesData,
        contactsData,
        timeData,
        invoicesData,
        inboxData,
        recentCasesData,
        inboxItemsData,
      ]) => {
        const totalMinutes = timeData.items.reduce(
          (sum: number, e: any) => sum + (e.duration_minutes || 0),
          0,
        );

        setStats({
          cases: casesData.items.length,
          contacts: contactsData.items.length,
          hoursThisMonth: Math.round((totalMinutes / 60) * 10) / 10,
          invoices: invoicesData.items.filter((inv: any) => inv.status !== "paid").length,
          documents: 0, // TODO: Add documents endpoint
          inboxPending: inboxData.items.length,
        });

        setRecentCases(recentCasesData.items.slice(0, 5));
        setInboxItems(inboxItemsData.items);
      })
      .catch((error) => {
        console.error("Error fetching dashboard data:", error);
        setStats({ cases: 0, contacts: 0, hoursThisMonth: 0, invoices: 0, documents: 0, inboxPending: 0 });
      })
      .finally(() => setStatsLoading(false));
  }, [token, tenantId]);

  if (status === "loading") {
    return (
      <div className="space-y-6">
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  const email = user?.email || "Utilisateur";
  const firstName = email.split("@")[0].split(".")[0];
  const displayName = firstName.charAt(0).toUpperCase() + firstName.slice(1);

  const now = new Date();
  const dateStr = now.toLocaleDateString("fr-BE", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const STAT_CARDS = [
    {
      label: "Dossiers ouverts",
      value: stats?.cases ?? "—",
      icon: Briefcase,
      iconBg: "bg-accent-50",
      iconColor: "text-accent",
    },
    {
      label: "Contacts",
      value: stats?.contacts ?? "—",
      icon: Users,
      iconBg: "bg-success-50",
      iconColor: "text-success",
    },
    {
      label: "Heures ce mois",
      value: stats?.hoursThisMonth ?? "—",
      icon: Clock,
      iconBg: "bg-warning-50",
      iconColor: "text-warning",
    },
    {
      label: "Factures en attente",
      value: stats?.invoices ?? "—",
      icon: FileText,
      iconBg: "bg-danger-50",
      iconColor: "text-danger",
    },
    {
      label: "Inbox en attente",
      value: stats?.inboxPending ?? "—",
      icon: Inbox,
      iconBg: "bg-purple-50",
      iconColor: "text-purple-600",
    },
    {
      label: "Documents",
      value: stats?.documents ?? "—",
      icon: Folder,
      iconBg: "bg-teal-50",
      iconColor: "text-teal-600",
    },
  ];

  const getTimeAgo = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 60) return `Il y a ${diffMins}min`;
    if (diffHours < 24) return `Il y a ${diffHours}h`;
    if (diffDays === 1) return "Hier";
    return `Il y a ${diffDays}j`;
  };

  // TODO: fetch from API when endpoints exist
  const DEADLINES = [
    {
      title: "Conclusions \u2014 Dupont c/ Immobel",
      date: "18 f\u00e9v 2026",
      daysLeft: 2,
      urgent: true,
    },
    {
      title: "Audience \u2014 TPI Bruxelles",
      date: "21 f\u00e9v 2026",
      daysLeft: 5,
      urgent: false,
    },
    {
      title: "D\u00e9lai d\u2019appel \u2014 Janssens",
      date: "28 f\u00e9v 2026",
      daysLeft: 12,
      urgent: false,
    },
    {
      title: "D\u00e9p\u00f4t de bilan \u2014 SA Construct",
      date: "5 mars 2026",
      daysLeft: 17,
      urgent: false,
    },
  ];

  const sourceIcons = {
    email: Mail,
    phone: Phone,
    document: FileCheck,
  };

  const priorityStyles = {
    high: "bg-danger-50 text-danger-700",
    medium: "bg-warning-50 text-warning-700",
    low: "bg-neutral-100 text-neutral-600",
  };

  const priorityLabels = {
    high: "Urgent",
    medium: "Normal",
    low: "Basse",
  };

  return (
    <div>
      {/* Welcome header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-neutral-900">
          Bonjour{" "}
          <span className="bg-gradient-to-r from-accent to-accent-400 bg-clip-text text-transparent">
            {displayName}
          </span>
        </h1>
        <p className="text-neutral-500 mt-1 text-sm capitalize">{dateStr}</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 mb-8">
        {STAT_CARDS.map((card) => (
          <div
            key={card.label}
            className="card group cursor-default hover:-translate-y-0.5 transition-all duration-150"
          >
            <div className="flex items-center justify-between">
              <div className={`p-3 rounded-md ${card.iconBg}`}>
                <card.icon className={`w-5 h-5 ${card.iconColor}`} />
              </div>
            </div>
            <div className="mt-4">
              {statsLoading ? (
                <>
                  <div className="h-7 w-16 bg-neutral-100 rounded mb-2 animate-pulse" />
                  <div className="h-4 w-24 bg-neutral-100 rounded animate-pulse" />
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-neutral-900">
                    {card.value}
                  </p>
                  <p className="text-sm text-neutral-500 mt-0.5">{card.label}</p>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Three-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity */}
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-5">
            Activité récente
          </h3>
          <div className="space-y-4">
            {recentCases.length > 0 ? (
              recentCases.map((caseItem, i) => (
                <div key={caseItem.id} className="flex items-start gap-3">
                  <div className="relative mt-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-accent" />
                    {i < recentCases.length - 1 && (
                      <div className="absolute top-3 left-1/2 -translate-x-1/2 w-px h-6 bg-neutral-200" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-neutral-700 leading-snug">
                      Dossier "{caseItem.title}" mis à jour
                    </p>
                    <p className="text-xs text-neutral-400 mt-0.5">
                      {getTimeAgo(caseItem.updated_at)}
                    </p>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-neutral-500 text-center py-4">
                Aucune activité récente
              </p>
            )}
          </div>
        </div>

        {/* Inbox */}
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-5">
            Inbox — À traiter
          </h3>
          <div className="space-y-3">
            {inboxItems.length > 0 ? (
              inboxItems.map((item) => {
                const SourceIcon = sourceIcons[item.item_type as keyof typeof sourceIcons] || Mail;
                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 p-2.5 rounded-md hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
                  >
                    <SourceIcon className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                    <span className="flex-1 text-sm text-neutral-700 truncate">
                      {item.subject || "(Sans titre)"}
                      {item.from_name && ` — ${item.from_name}`}
                    </span>
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-neutral-500 text-center py-4">
                Aucun élément en attente
              </p>
            )}
          </div>
        </div>

        {/* Deadlines */}
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-5">
            Prochaines &eacute;ch&eacute;ances
          </h3>
          <div className="space-y-3">
            {DEADLINES.map((item, i) => (
              <div
                key={i}
                className="flex items-center gap-3 p-2.5 rounded-md hover:bg-neutral-50 transition-colors duration-150"
              >
                <CalendarDays className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-700 truncate">
                    {item.title}
                  </p>
                  <p className="text-xs text-neutral-400 mt-0.5">{item.date}</p>
                </div>
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    item.urgent
                      ? "bg-danger-50 text-danger-700"
                      : item.daysLeft <= 7
                        ? "bg-warning-50 text-warning-700"
                        : "bg-neutral-100 text-neutral-600"
                  }`}
                >
                  {item.daysLeft}j
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
