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
  FolderOpen,
  Inbox as InboxIcon,
  TrendingUp,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import {
  LoadingSkeleton,
  ErrorState,
  StatCard,
  Card,
  Badge,
  EmptyState,
} from "@/components/ui";

interface DashboardStats {
  total_cases: number;
  total_contacts: number;
  monthly_hours: number;
  total_invoices: number;
  total_documents: number;
  pending_inbox: number;
}

interface RecentCase {
  id: string;
  title: string;
  status: string;
  updated_at: string;
}

interface InboxItem {
  id: string;
  subject: string;
  source: string;
  from_name?: string;
}

interface DashboardResponse {
  stats?: DashboardStats;
  items?: any[];
}

export default function DashboardPage() {
  const { data: session } = useSession();
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentCases, setRecentCases] = useState<RecentCase[]>([]);
  const [inboxItems, setInboxItems] = useState<InboxItem[]>([]);

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  useEffect(() => {
    async function fetchData() {
      if (!token) return;
      try {
        setLoading(true);
        setError(null);

        const [statsRes, recentRes, inboxRes] = await Promise.all([
          apiFetch<DashboardResponse>("/dashboard/stats", token, { tenantId }).catch(
            (err) => {
              console.error(err);
              return {};
            }
          ),
          apiFetch<{ items: RecentCase[] }>(
            "/cases?page=1&per_page=5&sort=-updated_at",
            token,
            { tenantId }
          ).catch(() => ({ items: [] })),
          apiFetch<{ items: InboxItem[] }>(
            "/inbox?status=DRAFT&per_page=5",
            token,
            { tenantId }
          ).catch(() => ({ items: [] })),
        ]);

        setStats(
          "stats" in statsRes && statsRes.stats
            ? statsRes.stats
            : {
                total_cases: 0,
                total_contacts: 0,
                monthly_hours: 0,
                total_invoices: 0,
                total_documents: 0,
                pending_inbox: 0,
              }
        );
        setRecentCases(recentRes.items || []);
        setInboxItems(inboxRes.items || []);
      } catch (err: any) {
        console.error("Error fetching dashboard data:", err);
        setError("Impossible de charger les données du tableau de bord");
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, [token, tenantId]);

  if (loading) {
    return <LoadingSkeleton variant="stats" />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  const user = session?.user as any;
  const email = user?.email || "Utilisateur";
  const firstName = email.split("@")[0].split(".")[0];
  const displayName =
    firstName.charAt(0).toUpperCase() + firstName.slice(1);

  const now = new Date();
  const dateStr = now.toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  const getStatusVariant = (
    status: string
  ): "default" | "success" | "warning" | "danger" | "accent" | "neutral" => {
    const lowerStatus = status.toLowerCase();
    if (
      lowerStatus.includes("closed") ||
      lowerStatus.includes("résolu")
    ) {
      return "success";
    }
    if (
      lowerStatus.includes("pending") ||
      lowerStatus.includes("en attente")
    ) {
      return "warning";
    }
    if (
      lowerStatus.includes("urgent") ||
      lowerStatus.includes("critical")
    ) {
      return "danger";
    }
    return "accent";
  };

  const STAT_CARDS = [
    {
      title: "Dossiers",
      value: stats?.total_cases ?? 0,
      icon: <Briefcase className="w-5 h-5" />,
      color: "accent" as const,
      trend: { value: 12, label: "vs mois dernier" },
    },
    {
      title: "Contacts",
      value: stats?.total_contacts ?? 0,
      icon: <Users className="w-5 h-5" />,
      color: "success" as const,
      trend: { value: 8, label: "vs mois dernier" },
    },
    {
      title: "Heures ce mois",
      value: stats?.monthly_hours ?? 0,
      icon: <Clock className="w-5 h-5" />,
      color: "warning" as const,
      trend: { value: 5, label: "vs mois dernier" },
    },
    {
      title: "Factures",
      value: stats?.total_invoices ?? 0,
      icon: <FileText className="w-5 h-5" />,
      color: "error" as const,
      trend: { value: 3, label: "vs mois dernier" },
    },
    {
      title: "Inbox en attente",
      value: stats?.pending_inbox ?? 0,
      icon: <InboxIcon className="w-5 h-5" />,
      color: "warning" as const,
      trend: { value: -2, label: "vs mois dernier" },
    },
    {
      title: "Documents",
      value: stats?.total_documents ?? 0,
      icon: <FolderOpen className="w-5 h-5" />,
      color: "accent" as const,
      trend: { value: 15, label: "vs mois dernier" },
    },
  ];

  const getTimeAgo = (dateString: string): string => {
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

  const DEADLINES = [
    {
      title: "Conclusions — Dupont c/ Immobel",
      date: "18 février 2026",
      daysLeft: 2,
      urgent: true,
    },
    {
      title: "Audience — TPI Bruxelles",
      date: "21 février 2026",
      daysLeft: 5,
      urgent: false,
    },
    {
      title: "Délai d'appel — Janssens",
      date: "28 février 2026",
      daysLeft: 12,
      urgent: false,
    },
    {
      title: "Dépôt de bilan — SA Construct",
      date: "5 mars 2026",
      daysLeft: 17,
      urgent: false,
    },
  ];

  const sourceIcons: Record<string, React.ComponentType<any>> = {
    email: Mail,
    phone: Phone,
    document: FileCheck,
  };

  return (
    <div className="min-h-screen bg-neutral-50">
      {/* Hero Section - Corporate */}
      <div className="mb-8 animate-fade">
        <div className="relative overflow-hidden bg-white border border-neutral-200 p-8 md:p-12">
          <div className="relative z-10">
            <h1 className="text-4xl font-display font-bold text-primary mb-2">
              Bonjour, {displayName}
            </h1>
            <p className="text-lg text-neutral-600 capitalize">
              {dateStr}
            </p>
          </div>
        </div>
      </div>

      {/* Stats Grid - 6 Cards - Corporate */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
        {STAT_CARDS.map((card, index) => (
          <div
            key={card.title}
            className="animate-fade"
          >
            <StatCard
              title={card.title}
              value={card.value}
              icon={card.icon}
              color={card.color}
              trend={card.trend}
            />
          </div>
        ))}
      </div>

      {/* Two-Column Grid: Recent Activity & Inbox */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {/* Recent Cases */}
        <Card
          header={
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Dossiers récents
            </h3>
          }
        >
          {recentCases.length === 0 ? (
            <EmptyState
              title="Aucun dossier récent"
              description="Vos dossiers apparaîtront ici"
              icon={<FolderOpen className="h-12 w-12 text-neutral-300" />}
            />
          ) : (
            <div className="space-y-3">
              {recentCases.slice(0, 5).map((caseItem, index) => (
                <div
                  key={caseItem.id}
                  className="flex items-center gap-3 p-3 hover:bg-neutral-50 rounded transition-colors duration-150 cursor-pointer group"
                >
                  <Badge variant={getStatusVariant(caseItem.status)} size="sm">
                    {caseItem.status}
                  </Badge>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-neutral-900 group-hover:text-primary transition-colors duration-150">
                      {caseItem.title}
                    </p>
                    <p className="text-xs text-neutral-500 mt-0.5">
                      {new Date(caseItem.updated_at).toLocaleDateString(
                        "fr-FR"
                      )}
                    </p>
                  </div>
                  <TrendingUp className="w-4 h-4 text-neutral-300 flex-shrink-0" />
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* Inbox Pending */}
        <Card
          header={
            <h3 className="font-display text-lg font-semibold text-neutral-900">
              Inbox à traiter
            </h3>
          }
        >
          {inboxItems.length === 0 ? (
            <EmptyState
              title="Aucun élément en attente"
              description="Votre inbox est vide"
              icon={<InboxIcon className="h-12 w-12 text-neutral-300" />}
            />
          ) : (
            <div className="space-y-3">
              {inboxItems.slice(0, 5).map((item, index) => {
                const SourceIcon =
                  sourceIcons[item.source as keyof typeof sourceIcons] || Mail;
                return (
                  <div
                    key={item.id}
                    className="flex items-center gap-3 p-3 hover:bg-neutral-50 rounded transition-colors duration-150 cursor-pointer group"
                  >
                    <div className="p-2 bg-primary/10 rounded flex-shrink-0">
                      <SourceIcon className="w-4 h-4 text-primary" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-neutral-900 group-hover:text-primary font-medium truncate transition-colors duration-150">
                        {item.subject || "(Sans titre)"}
                      </p>
                      {item.from_name && (
                        <p className="text-xs text-neutral-500 truncate">
                          {item.from_name}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </Card>
      </div>

      {/* Deadlines Section */}
      <Card
        header={
          <h3 className="font-display text-lg font-semibold text-neutral-900">
            Prochaines échéances
          </h3>
        }
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {DEADLINES.map((deadline, index) => (
            <div
              key={index}
              className="flex items-start gap-4 p-4 border border-neutral-200 rounded hover:shadow-md transition-shadow duration-150 cursor-pointer group"
            >
              <div className="p-2.5 bg-primary/10 rounded flex-shrink-0">
                <CalendarDays className="w-5 h-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-neutral-900 group-hover:text-primary transition-colors duration-150">
                  {deadline.title}
                </p>
                <p className="text-xs text-neutral-500 mt-1">
                  {deadline.date}
                </p>
              </div>
              <Badge
                variant={
                  deadline.urgent ? "danger" : "default"
                }
                size="sm"
              >
                {deadline.daysLeft}j
              </Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
