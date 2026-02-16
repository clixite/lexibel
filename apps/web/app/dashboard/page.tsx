"use client";

import { useSession } from "next-auth/react";
import {
  Briefcase,
  Users,
  Clock,
  FileText,
  Loader2,
  TrendingUp,
  Mail,
  Phone,
  FileCheck,
  CalendarDays,
} from "lucide-react";

export default function DashboardPage() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  const user = session?.user as any;
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
      value: "24",
      icon: Briefcase,
      iconBg: "bg-accent-50",
      iconColor: "text-accent",
      trend: "+12%",
      trendUp: true,
    },
    {
      label: "Contacts",
      value: "156",
      icon: Users,
      iconBg: "bg-success-50",
      iconColor: "text-success",
      trend: "+8%",
      trendUp: true,
    },
    {
      label: "Heures ce mois",
      value: "87.5",
      icon: Clock,
      iconBg: "bg-warning-50",
      iconColor: "text-warning",
      trend: "+5%",
      trendUp: true,
    },
    {
      label: "Factures en attente",
      value: "3",
      icon: FileText,
      iconBg: "bg-danger-50",
      iconColor: "text-danger",
      trend: "-2",
      trendUp: false,
    },
  ];

  const RECENT_ACTIVITY = [
    {
      color: "bg-accent",
      text: 'Dossier "Dupont c/ SA Immobel" mis \u00e0 jour',
      time: "Il y a 25 min",
    },
    {
      color: "bg-success",
      text: "Nouveau contact ajout\u00e9 : Me Laurent Verhaegen",
      time: "Il y a 1h",
    },
    {
      color: "bg-warning",
      text: "Conclusions d\u00e9pos\u00e9es \u2014 Tribunal de commerce Bruxelles",
      time: "Il y a 2h",
    },
    {
      color: "bg-neutral-400",
      text: "Facture #2024-089 envoy\u00e9e \u00e0 SA Immobel",
      time: "Il y a 3h",
    },
    {
      color: "bg-accent",
      text: 'Dossier "H\u00e9ritage Janssens" cr\u00e9\u00e9',
      time: "Hier, 17h30",
    },
  ];

  const INBOX_ITEMS = [
    {
      title: "Email de Me Verhaegen \u2014 Pi\u00e8ces manquantes",
      source: "email" as const,
      priority: "high" as const,
    },
    {
      title: "Appel entrant \u2014 SA Construct Plus",
      source: "phone" as const,
      priority: "medium" as const,
    },
    {
      title: "Document re\u00e7u \u2014 Jugement TPI Li\u00e8ge",
      source: "document" as const,
      priority: "low" as const,
    },
    {
      title: "Email de Mme Dupont \u2014 Question honoraires",
      source: "email" as const,
      priority: "medium" as const,
    },
  ];

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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
        {STAT_CARDS.map((card) => (
          <div
            key={card.label}
            className="card group cursor-default hover:-translate-y-0.5 transition-all duration-150"
          >
            <div className="flex items-center justify-between">
              <div className={`p-3 rounded-md ${card.iconBg}`}>
                <card.icon className={`w-5 h-5 ${card.iconColor}`} />
              </div>
              <div
                className={`flex items-center gap-1 text-xs font-medium ${
                  card.trendUp ? "text-success" : "text-danger"
                }`}
              >
                <TrendingUp
                  className={`w-3 h-3 ${!card.trendUp ? "rotate-180" : ""}`}
                />
                {card.trend}
              </div>
            </div>
            <div className="mt-4">
              <p className="text-2xl font-bold text-neutral-900">
                {card.value}
              </p>
              <p className="text-sm text-neutral-500 mt-0.5">{card.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Three-column grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Activity */}
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-5">
            Activit&eacute; r&eacute;cente
          </h3>
          <div className="space-y-4">
            {RECENT_ACTIVITY.map((item, i) => (
              <div key={i} className="flex items-start gap-3">
                <div className="relative mt-1.5">
                  <div
                    className={`w-2.5 h-2.5 rounded-full ${item.color}`}
                  />
                  {i < RECENT_ACTIVITY.length - 1 && (
                    <div className="absolute top-3 left-1/2 -translate-x-1/2 w-px h-6 bg-neutral-200" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-neutral-700 leading-snug">
                    {item.text}
                  </p>
                  <p className="text-xs text-neutral-400 mt-0.5">{item.time}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Inbox */}
        <div className="card">
          <h3 className="text-base font-semibold text-neutral-900 mb-5">
            Inbox &mdash; &Agrave; traiter
          </h3>
          <div className="space-y-3">
            {INBOX_ITEMS.map((item, i) => {
              const SourceIcon = sourceIcons[item.source];
              return (
                <div
                  key={i}
                  className="flex items-center gap-3 p-2.5 rounded-md hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
                >
                  <SourceIcon className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                  <span className="flex-1 text-sm text-neutral-700 truncate">
                    {item.title}
                  </span>
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium ${priorityStyles[item.priority]}`}
                  >
                    {priorityLabels[item.priority]}
                  </span>
                </div>
              );
            })}
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
