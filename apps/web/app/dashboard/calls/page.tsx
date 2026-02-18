"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Phone, PhoneIncoming, PhoneOutgoing, Clock, ChevronDown } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, StatCard, DataTable, Badge, Card, Button } from "@/components/ui";

interface Call {
  id: string;
  date: string;
  time: string;
  direction: "INBOUND" | "OUTBOUND";
  phone_number: string;
  duration: number;
  status: string;
}

interface CallStats {
  total: number;
  inbound: number;
  outbound: number;
  avg_duration: number;
}

export default function CallsPage() {
  const { accessToken } = useAuth();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [calls, setCalls] = useState<Call[]>([]);
  const [stats, setStats] = useState<CallStats | null>(null);
  const [direction, setDirection] = useState<"ALL" | "INBOUND" | "OUTBOUND">("ALL");

  useEffect(() => {
    async function fetchData() {
      if (!accessToken) return;
      try {
        setLoading(true);
        setError("");
        const query = direction !== "ALL" ? `?direction=${direction}` : "";
        const res = await apiFetch<Call[]>(`/calls${query}`, accessToken);
        setCalls(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement");
      } finally {
        setLoading(false);
      }
    }

    if (accessToken) {
      fetchData();
    }
  }, [accessToken, direction]);

  useEffect(() => {
    async function fetchStats() {
      if (!accessToken) return;
      try {
        const res = await apiFetch<CallStats>("/calls/stats", accessToken);
        setStats(res);
      } catch (err) {
        console.error("Erreur stats:", err);
      }
    }

    if (accessToken) {
      fetchStats();
    }
  }, [accessToken]);

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Appels téléphoniques</h1>
          <p className="text-neutral-500 text-sm mt-1">Historique et statistiques</p>
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Total appels"
              value={stats.total}
              icon={<Phone className="w-5 h-5" />}
              color="accent"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Entrants"
              value={stats.inbound}
              icon={<PhoneIncoming className="w-5 h-5" />}
              color="success"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Sortants"
              value={stats.outbound}
              icon={<PhoneOutgoing className="w-5 h-5" />}
              color="warning"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Durée moyenne"
              value={formatDuration(stats.avg_duration)}
              icon={<Clock className="w-5 h-5" />}
              color="accent"
            />
          </Card>
        </div>
      )}

      <div className="mb-6">
        <div className="relative inline-block">
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as any)}
            className="appearance-none px-4 py-2 border border-neutral-200 rounded-lg text-sm pr-8 bg-white"
          >
            <option value="ALL">Toutes directions</option>
            <option value="INBOUND">Entrant</option>
            <option value="OUTBOUND">Sortant</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400 pointer-events-none" />
        </div>
      </div>

      {loading && <LoadingSkeleton />}

      {error && <ErrorState message={error} />}

      {!loading && calls.length === 0 && (
        <EmptyState
          icon={<Phone className="w-12 h-12" />}
          title="Aucun appel"
          description="Aucun appel enregistré pour le moment"
        />
      )}

      {!loading && calls.length > 0 && (
        <Card className="overflow-hidden">
          <DataTable
            data={calls}
            columns={[
              {
                key: "date",
                label: "Date",
                render: (call) => new Date(call.date).toLocaleDateString("fr-FR"),
              },
              {
                key: "time",
                label: "Heure",
                render: (call) => call.time,
              },
              {
                key: "direction",
                label: "Direction",
                render: (call) => (
                  <Badge
                    variant={call.direction === "INBOUND" ? "success" : "accent"}
                    size="sm"
                    dot
                  >
                    {call.direction === "INBOUND" ? "Entrant" : "Sortant"}
                  </Badge>
                ),
              },
              {
                key: "phone_number",
                label: "Numéro",
                render: (call) => <span>{call.phone_number}</span>,
              },
              {
                key: "duration",
                label: "Durée",
                render: (call) => formatDuration(call.duration),
              },
              {
                key: "status",
                label: "Statut",
                render: (call) => (
                  <Badge variant="neutral" size="sm">
                    {call.status}
                  </Badge>
                ),
              },
            ]}
            onRowClick={(call) => router.push(`/dashboard/calls/${call.id}`)}
          />
        </Card>
      )}
    </div>
  );
}
