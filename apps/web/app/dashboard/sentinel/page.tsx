"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Shield, AlertTriangle, CheckCircle, Clock, TrendingUp } from "lucide-react";
import Link from "next/link";
import { sentinelAPI, ConflictSummary } from "@/lib/sentinel/api-client";
import ConflictCard from "@/components/sentinel/ConflictCard";
import ConflictCheckForm from "@/components/sentinel/ConflictCheckForm";
import { useSentinelAlerts } from "@/hooks/useSentinelAlerts";

export default function SentinelDashboard() {
  const router = useRouter();
  const [stats, setStats] = useState({
    total: 0,
    active: 0,
    critical: 0,
    resolved: 0,
  });
  const [recentConflicts, setRecentConflicts] = useState<ConflictSummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const { conflictCount, isConnected } = useSentinelAlerts();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      // Load recent conflicts
      const allConflicts = await sentinelAPI.listConflicts({ page: 1, page_size: 5 });
      setRecentConflicts(allConflicts.conflicts);

      // Calculate stats
      const activeConflicts = await sentinelAPI.listConflicts({
        status: "active",
        page_size: 100,
      });
      const criticalConflicts = await sentinelAPI.listConflicts({
        status: "active",
        severity_min: 90,
        page_size: 100,
      });
      const resolvedConflicts = await sentinelAPI.listConflicts({
        status: "resolved",
        page_size: 100,
      });

      setStats({
        total: allConflicts.pagination.total,
        active: activeConflicts.pagination.total,
        critical: criticalConflicts.pagination.total,
        resolved: resolvedConflicts.pagination.total,
      });
    } catch (error) {
      // SENTINEL data load failed — stats will show zeros
    } finally {
      setIsLoading(false);
    }
  };

  const statCards = [
    {
      label: "Total",
      value: stats.total,
      icon: Shield,
      color: "bg-blue-500",
      textColor: "text-blue-600 dark:text-blue-400",
    },
    {
      label: "Actifs",
      value: stats.active,
      icon: AlertTriangle,
      color: "bg-orange-500",
      textColor: "text-orange-600 dark:text-orange-400",
    },
    {
      label: "Critiques",
      value: stats.critical,
      icon: TrendingUp,
      color: "bg-red-500",
      textColor: "text-red-600 dark:text-red-400",
    },
    {
      label: "Résolus",
      value: stats.resolved,
      icon: CheckCircle,
      color: "bg-green-500",
      textColor: "text-green-600 dark:text-green-400",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <Shield className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            SENTINEL
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Détection et gestion des conflits d'intérêts
          </p>
        </div>

        {/* SSE Connection Status */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-100 dark:bg-gray-800">
          <div
            className={`w-2 h-2 rounded-full ${
              isConnected ? "bg-green-500 animate-pulse" : "bg-gray-400"
            }`}
          />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
            {isConnected ? "Surveillance active" : "Hors ligne"}
          </span>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <div
            key={stat.label}
            className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600 dark:text-gray-400">
                  {stat.label}
                </p>
                <p className={`text-3xl font-bold mt-2 ${stat.textColor}`}>
                  {isLoading ? (
                    <div className="h-9 w-12 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
                  ) : (
                    stat.value
                  )}
                </p>
              </div>
              <div className={`w-12 h-12 ${stat.color} rounded-lg flex items-center justify-center`}>
                <stat.icon className="w-6 h-6 text-white" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Quick Check Form */}
      <ConflictCheckForm />

      {/* Recent Conflicts */}
      <div className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Conflits récents
          </h2>
          <Link
            href="/dashboard/sentinel/conflicts"
            className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
          >
            Voir tous
          </Link>
        </div>

        {isLoading ? (
          <div className="space-y-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-32 bg-gray-100 dark:bg-gray-700 rounded-lg animate-pulse"
              />
            ))}
          </div>
        ) : recentConflicts.length > 0 ? (
          <div className="space-y-4">
            {recentConflicts.map((conflict) => (
              <ConflictCard
                key={conflict.id}
                conflict={conflict}
                onClick={() => {
                  router.push(`/dashboard/sentinel/conflicts?id=${conflict.id}`);
                }}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-12">
            <CheckCircle className="w-16 h-16 text-green-500 mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400 font-medium">
              Aucun conflit détecté
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-500 mt-1">
              Tous les dossiers sont conformes
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
