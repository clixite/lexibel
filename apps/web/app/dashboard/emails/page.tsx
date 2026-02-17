"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Mail,
  Search,
  Filter,
  Paperclip,
  Star,
  Clock,
  RefreshCw,
  Loader2,
  AlertCircle,
  Inbox,
  Calendar,
} from "lucide-react";
import { useEmailThreads, useEmailStats, useTriggerEmailSync } from "@/lib/hooks/useEmails";
import type { EmailListFilters } from "@/lib/types/email";
import { toast } from "sonner";

export default function EmailsPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [filters, setFilters] = useState<EmailListFilters>({
    page: 1,
    per_page: 20,
  });
  const [searchQuery, setSearchQuery] = useState("");

  // Queries
  const threadsQuery = useEmailThreads(filters, token, tenantId);
  const statsQuery = useEmailStats(undefined, token, tenantId);
  const syncMutation = useTriggerEmailSync(token, tenantId);

  const handleSearch = () => {
    setFilters((prev) => ({ ...prev, search: searchQuery, page: 1 }));
  };

  const handleSync = (integrationId: string) => {
    syncMutation.mutate(integrationId, {
      onSuccess: () => toast.success("Synchronisation démarrée"),
      onError: (error: Error) => toast.error(error.message),
    });
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900">Emails</h1>
          <p className="text-neutral-500 text-sm mt-1">
            Emails synchronisés depuis Gmail et Outlook
          </p>
        </div>
        <button
          onClick={() => router.push("/dashboard/admin/integrations")}
          className="btn-secondary"
        >
          Gérer les intégrations
        </button>
      </div>

      {/* Stats */}
      {statsQuery.data && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-blue-50 rounded-lg">
                <Mail className="w-5 h-5 text-blue-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.total_messages}
            </p>
            <p className="text-sm text-neutral-500">Total messages</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-purple-50 rounded-lg">
                <Inbox className="w-5 h-5 text-purple-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.total_threads}
            </p>
            <p className="text-sm text-neutral-500">Conversations</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-orange-50 rounded-lg">
                <Paperclip className="w-5 h-5 text-orange-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.with_attachments}
            </p>
            <p className="text-sm text-neutral-500">Avec pièces jointes</p>
          </div>

          <div className="card">
            <div className="flex items-center justify-between mb-3">
              <div className="p-2 bg-green-50 rounded-lg">
                <Calendar className="w-5 h-5 text-green-600" />
              </div>
            </div>
            <p className="text-2xl font-bold text-neutral-900">
              {statsQuery.data.last_7_days}
            </p>
            <p className="text-sm text-neutral-500">7 derniers jours</p>
          </div>
        </div>
      )}

      {/* Search and filters */}
      <div className="flex flex-col md:flex-row gap-4 mb-6">
        <div className="flex-1 flex gap-2">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Rechercher dans les emails..."
            className="input flex-1"
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
          />
          <button onClick={handleSearch} className="btn-primary px-4">
            <Search className="w-4 h-4" />
          </button>
        </div>

        <div className="flex gap-2">
          <select
            className="input"
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                has_attachments:
                  e.target.value === "true"
                    ? true
                    : e.target.value === "false"
                    ? false
                    : undefined,
                page: 1,
              }))
            }
          >
            <option value="">Tous les emails</option>
            <option value="true">Avec pièces jointes</option>
            <option value="false">Sans pièces jointes</option>
          </select>

          <select
            className="input"
            onChange={(e) =>
              setFilters((prev) => ({
                ...prev,
                is_important:
                  e.target.value === "true"
                    ? true
                    : e.target.value === "false"
                    ? false
                    : undefined,
                page: 1,
              }))
            }
          >
            <option value="">Tous</option>
            <option value="true">Importants</option>
            <option value="false">Non importants</option>
          </select>
        </div>
      </div>

      {/* Loading */}
      {threadsQuery.isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
        </div>
      )}

      {/* Error */}
      {threadsQuery.isError && (
        <div className="bg-red-50 rounded-lg p-6 border border-red-200">
          <div className="flex items-center gap-3">
            <AlertCircle className="h-6 w-6 text-red-600" />
            <div>
              <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
              <p className="text-sm text-red-700 mt-1">
                Impossible de charger les emails.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {threadsQuery.data && threadsQuery.data.items.length === 0 && (
        <div className="bg-white rounded-lg p-12 text-center border border-neutral-200">
          <Mail className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-neutral-600 mb-2">
            Aucun email
          </h3>
          <p className="text-neutral-500">
            {filters.search
              ? "Aucun résultat pour cette recherche"
              : "Connectez vos comptes Gmail ou Outlook pour synchroniser vos emails"}
          </p>
        </div>
      )}

      {/* Threads list */}
      {threadsQuery.data && threadsQuery.data.items.length > 0 && (
        <div className="space-y-2">
          {threadsQuery.data.items.map((thread) => (
            <div
              key={thread.id}
              className="card hover:shadow-md transition-shadow cursor-pointer"
              onClick={() => router.push(`/dashboard/emails/${thread.id}`)}
            >
              <div className="flex items-start gap-4">
                <div className="p-3 bg-blue-50 rounded-lg flex-shrink-0">
                  <Mail className="w-5 h-5 text-blue-600" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-neutral-900 truncate">
                          {thread.subject || "(Pas de sujet)"}
                        </h3>
                        {thread.is_important && (
                          <Star className="w-4 h-4 text-yellow-500 fill-yellow-500 flex-shrink-0" />
                        )}
                        {thread.has_attachments && (
                          <Paperclip className="w-4 h-4 text-neutral-400 flex-shrink-0" />
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-sm text-neutral-600">
                        <span>{thread.participant_names.slice(0, 2).join(", ")}</span>
                        {thread.participant_names.length > 2 && (
                          <span className="text-neutral-400">
                            +{thread.participant_names.length - 2} autres
                          </span>
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className="text-xs text-neutral-500 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {new Date(thread.last_message_date).toLocaleDateString("fr-BE")}
                      </span>
                      <span className="px-2 py-0.5 bg-neutral-100 text-neutral-600 rounded-full text-xs">
                        {thread.message_count} message{thread.message_count > 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>

                  {thread.case_id && (
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-1 bg-accent-50 text-accent-700 rounded text-xs font-medium">
                        Dossier: {thread.case_title || thread.case_id.slice(0, 8)}
                      </span>
                    </div>
                  )}

                  {thread.labels.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2">
                      {thread.labels.slice(0, 3).map((label, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 bg-neutral-100 text-neutral-600 rounded text-xs"
                        >
                          {label}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {threadsQuery.data && threadsQuery.data.total > threadsQuery.data.per_page && (
        <div className="flex items-center justify-center gap-2 mt-6">
          <button
            onClick={() =>
              setFilters((prev) => ({ ...prev, page: (prev.page || 1) - 1 }))
            }
            disabled={(filters.page || 1) <= 1}
            className="btn-secondary disabled:opacity-50"
          >
            Précédent
          </button>
          <span className="text-sm text-neutral-600">
            Page {filters.page || 1} sur{" "}
            {Math.ceil(threadsQuery.data.total / threadsQuery.data.per_page)}
          </span>
          <button
            onClick={() =>
              setFilters((prev) => ({ ...prev, page: (prev.page || 1) + 1 }))
            }
            disabled={
              (filters.page || 1) >=
              Math.ceil(threadsQuery.data.total / threadsQuery.data.per_page)
            }
            className="btn-secondary disabled:opacity-50"
          >
            Suivant
          </button>
        </div>
      )}
    </div>
  );
}
