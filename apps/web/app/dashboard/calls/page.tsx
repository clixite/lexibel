"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Phone, PhoneIncoming, PhoneOutgoing, Clock } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, StatCard, DataTable, Badge } from "@/components/ui";

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
  const { data: session } = useSession();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [calls, setCalls] = useState<Call[]>([]);
  const [stats, setStats] = useState<CallStats | null>(null);
  const [direction, setDirection] = useState<"ALL" | "INBOUND" | "OUTBOUND">("ALL");

  useEffect(() => {
    async function fetchData() {
      if (!session?.user?.accessToken) return;
      try {
        setLoading(true);
        setError("");
        const query = direction !== "ALL" ? `?direction=${direction}` : "";
        const res = await apiFetch<Call[]>(`/calls${query}`, session.user.accessToken);
        setCalls(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement");
      } finally {
        setLoading(false);
      }
    }

    if (session?.user?.accessToken) {
      fetchData();
    }
  }, [session?.user?.accessToken, direction]);

  useEffect(() => {
    async function fetchStats() {
      if (!session?.user?.accessToken) return;
      try {
        const res = await apiFetch<CallStats>("/calls/stats", session.user.accessToken);
        setStats(res);
      } catch (err) {
        console.error("Erreur stats:", err);
      }
    }

    if (session?.user?.accessToken) {
      fetchStats();
    }
  }, [session?.user?.accessToken]);

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
          <StatCard
            title="Total appels"
            value={stats.total}
            icon={<Phone className="w-5 h-5" />}
            color="accent"
          />
          <StatCard
            title="Entrants"
            value={stats.inbound}
            icon={<PhoneIncoming className="w-5 h-5" />}
            color="success"
          />
          <StatCard
            title="Sortants"
            value={stats.outbound}
            icon={<PhoneOutgoing className="w-5 h-5" />}
            color="warning"
          />
          <StatCard
            title="Durée moyenne"
            value={formatDuration(stats.avg_duration)}
            icon={<Clock className="w-5 h-5" />}
            color="accent"
          />
        </div>
      )}

      <div className="mb-6">
        <select
          value={direction}
          onChange={(e) => setDirection(e.target.value as any)}
          className="px-4 py-2 border border-neutral-200 rounded-lg text-sm"
        >
          <option value="ALL">Toutes directions</option>
          <option value="INBOUND">Entrant</option>
          <option value="OUTBOUND">Sortant</option>
        </select>
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
                <Badge variant={call.direction === "INBOUND" ? "success" : "accent"}>
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
              render: (call) => <span>{call.status}</span>,
            },
          ]}
          onRowClick={(call) => router.push(`/dashboard/calls/${call.id}`)}
        />
      )}
    </div>
  );
}
