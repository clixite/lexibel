"use client";

import { useSession } from "next-auth/react";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Mail, Paperclip, Clock, RefreshCw } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, StatCard, DataTable, Badge, Button, Card } from "@/components/ui";
import { toast } from "sonner";

interface EmailThread {
  id: string;
  subject: string;
  participants: string[];
  date: string;
  message_count: number;
  has_attachments: boolean;
}

interface EmailStats {
  total_threads: number;
  unread_count: number;
  with_attachments: number;
}

export default function EmailsPage() {
  const { data: session } = useSession();
  const router = useRouter();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [threads, setThreads] = useState<EmailThread[]>([]);
  const [stats, setStats] = useState<EmailStats | null>(null);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    async function fetchData() {
      if (!session?.user?.accessToken) return;
      try {
        setLoading(true);
        setError("");
        const res = await apiFetch<EmailThread[]>("/emails", session.user.accessToken);
        setThreads(res);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur de chargement");
      } finally {
        setLoading(false);
      }
    }

    if (session?.user?.accessToken) {
      fetchData();
    }
  }, [session?.user?.accessToken]);

  useEffect(() => {
    async function fetchStats() {
      if (!session?.user?.accessToken) return;
      try {
        const res = await apiFetch<EmailStats>("/emails/stats", session.user.accessToken);
        setStats(res);
      } catch (err) {
        console.error("Erreur stats:", err);
      }
    }

    if (session?.user?.accessToken) {
      fetchStats();
    }
  }, [session?.user?.accessToken]);

  const handleSync = async () => {
    if (!session?.user?.accessToken) return;
    try {
      setSyncing(true);
      await apiFetch("/emails/sync", session.user.accessToken, { method: "POST" });
      toast.success("Synchronisation démarrée");
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Erreur de synchronisation");
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Emails</h1>
          <p className="text-neutral-500 text-sm mt-1">Synchronisés depuis Gmail et Outlook</p>
        </div>
        <Button
          variant="primary"
          icon={<RefreshCw className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`} />}
          onClick={handleSync}
          disabled={syncing}
          loading={syncing}
        >
          {syncing ? "Synchronisation..." : "Synchroniser"}
        </Button>
      </div>

      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Total conversations"
              value={stats.total_threads}
              icon={<Mail className="w-5 h-5" />}
              color="accent"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Non lus"
              value={stats.unread_count}
              icon={<Mail className="w-5 h-5" />}
              color="warning"
            />
          </Card>
          <Card className="hover:shadow-lg transition-shadow">
            <StatCard
              title="Avec pièces jointes"
              value={stats.with_attachments}
              icon={<Paperclip className="w-5 h-5" />}
              color="success"
            />
          </Card>
        </div>
      )}

      {loading && <LoadingSkeleton />}

      {error && <ErrorState message={error} />}

      {!loading && threads.length === 0 && (
        <EmptyState
          icon={<Mail className="w-12 h-12" />}
          title="Aucun email"
          description="Connectez vos comptes Gmail ou Outlook pour synchroniser vos emails"
        />
      )}

      {!loading && threads.length > 0 && (
        <Card className="overflow-hidden">
          <DataTable
            data={threads}
            columns={[
              {
                key: "subject",
                label: "Sujet",
                render: (thread) => <span className="font-medium">{thread.subject}</span>,
              },
              {
                key: "participants",
                label: "Participants",
                render: (thread) => <span>{thread.participants.join(", ")}</span>,
              },
              {
                key: "date",
                label: "Date",
                render: (thread) => new Date(thread.date).toLocaleDateString("fr-FR"),
              },
              {
                key: "message_count",
                label: "Messages",
                render: (thread) => (
                  <Badge variant="neutral" size="sm">
                    {thread.message_count}
                  </Badge>
                ),
              },
              {
                key: "has_attachments",
                label: "Pièces jointes",
                render: (thread) => (
                  <Badge variant={thread.has_attachments ? "success" : "default"} size="sm">
                    {thread.has_attachments ? "Oui" : "Non"}
                  </Badge>
                ),
              },
            ]}
            onRowClick={(thread) => router.push(`/dashboard/emails/${thread.id}`)}
          />
        </Card>
      )}
    </div>
  );
}
