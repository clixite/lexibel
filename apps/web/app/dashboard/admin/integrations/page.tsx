"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Mail,
  Calendar,
  Check,
  X,
  Loader2,
  AlertCircle,
  ExternalLink,
  Trash2,
  RefreshCw,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

interface OAuthIntegration {
  id: string;
  provider: "google" | "microsoft";
  email: string;
  scopes: string[];
  connected_at: string;
  last_sync_at?: string;
  status: "active" | "expired" | "error";
  error_message?: string;
}

interface IntegrationsResponse {
  items: OAuthIntegration[];
}

const PROVIDER_LABELS = {
  google: "Google Workspace",
  microsoft: "Microsoft 365",
};

const PROVIDER_ICONS = {
  google: "https://www.google.com/favicon.ico",
  microsoft: "https://www.microsoft.com/favicon.ico",
};

const PROVIDER_COLORS = {
  google: "bg-blue-50 text-blue-600",
  microsoft: "bg-orange-50 text-orange-600",
};

const STATUS_LABELS = {
  active: "Actif",
  expired: "Expiré",
  error: "Erreur",
};

const STATUS_COLORS = {
  active: "bg-green-50 text-green-700",
  expired: "bg-yellow-50 text-yellow-700",
  error: "bg-red-50 text-red-700",
};

export default function IntegrationsPage() {
  const { data: session } = useSession();
  const queryClient = useQueryClient();
  const user = session?.user as any;
  const token = user?.accessToken;
  const tenantId = user?.tenantId;

  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

  // Fetch integrations
  const integrationsQuery = useQuery({
    queryKey: ["oauth-integrations", tenantId],
    queryFn: async () => {
      if (!token) throw new Error("No token");
      return apiFetch<IntegrationsResponse>("/oauth/integrations", token, {
        tenantId,
      });
    },
    enabled: !!token,
  });

  // Delete integration
  const deleteMutation = useMutation({
    mutationFn: async (integrationId: string) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/oauth/integrations/${integrationId}`, token, {
        method: "DELETE",
        tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-integrations"] });
      toast.success("Intégration supprimée");
    },
    onError: (error: Error) => {
      toast.error("Erreur de suppression", { description: error.message });
    },
  });

  // Sync integration
  const syncMutation = useMutation({
    mutationFn: async (integrationId: string) => {
      if (!token) throw new Error("No token");
      return apiFetch(`/oauth/integrations/${integrationId}/sync`, token, {
        method: "POST",
        tenantId,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["oauth-integrations"] });
      toast.success("Synchronisation démarrée");
    },
    onError: (error: Error) => {
      toast.error("Erreur de synchronisation", { description: error.message });
    },
  });

  const handleConnect = async (provider: "google" | "microsoft") => {
    if (!token) return;

    setConnectingProvider(provider);

    try {
      // Get OAuth authorization URL
      const response = await apiFetch<{ authorization_url: string }>(
        `/oauth/${provider}/authorize`,
        token,
        { tenantId }
      );

      // Redirect to OAuth provider
      window.location.href = response.authorization_url;
    } catch (error: any) {
      toast.error("Erreur de connexion", { description: error.message });
      setConnectingProvider(null);
    }
  };

  const handleDelete = (integrationId: string, providerEmail: string) => {
    if (
      confirm(
        `Êtes-vous sûr de vouloir supprimer l'intégration pour ${providerEmail}?`
      )
    ) {
      deleteMutation.mutate(integrationId);
    }
  };

  const handleSync = (integrationId: string) => {
    syncMutation.mutate(integrationId);
  };

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-neutral-900">Intégrations OAuth</h1>
        <p className="text-neutral-500 text-sm mt-1">
          Connectez vos comptes Gmail et Outlook pour synchroniser vos emails et calendriers
        </p>
      </div>

      {/* Connect Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        {/* Google */}
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Mail className="w-6 h-6 text-blue-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-neutral-900 mb-1">
                Google Workspace
              </h3>
              <p className="text-sm text-neutral-600 mb-4">
                Gmail, Google Calendar, Google Drive
              </p>
              <button
                onClick={() => handleConnect("google")}
                disabled={connectingProvider === "google"}
                className="btn-primary flex items-center gap-2"
              >
                {connectingProvider === "google" ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Connexion...
                  </>
                ) : (
                  <>
                    <ExternalLink className="w-4 h-4" />
                    Connecter Google
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Microsoft */}
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-orange-50 rounded-lg">
              <Calendar className="w-6 h-6 text-orange-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-neutral-900 mb-1">
                Microsoft 365
              </h3>
              <p className="text-sm text-neutral-600 mb-4">
                Outlook Mail, Outlook Calendar, OneDrive
              </p>
              <button
                onClick={() => handleConnect("microsoft")}
                disabled={connectingProvider === "microsoft"}
                className="btn-primary flex items-center gap-2"
              >
                {connectingProvider === "microsoft" ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Connexion...
                  </>
                ) : (
                  <>
                    <ExternalLink className="w-4 h-4" />
                    Connecter Microsoft
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Active Integrations */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-neutral-900 mb-4">
          Intégrations actives
        </h2>

        {integrationsQuery.isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-neutral-400" />
          </div>
        )}

        {integrationsQuery.isError && (
          <div className="bg-red-50 rounded-lg p-6 border border-red-200">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-red-600" />
              <div>
                <h3 className="font-semibold text-red-900">Erreur de chargement</h3>
                <p className="text-sm text-red-700 mt-1">
                  Impossible de charger les intégrations.
                </p>
              </div>
            </div>
          </div>
        )}

        {integrationsQuery.data && integrationsQuery.data.items.length === 0 && (
          <div className="bg-white rounded-lg p-12 text-center border border-neutral-200">
            <Mail className="w-16 h-16 text-neutral-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-neutral-600 mb-2">
              Aucune intégration
            </h3>
            <p className="text-neutral-500">
              Connectez votre premier compte pour commencer à synchroniser vos données.
            </p>
          </div>
        )}

        {integrationsQuery.data && integrationsQuery.data.items.length > 0 && (
          <div className="space-y-4">
            {integrationsQuery.data.items.map((integration) => (
              <div key={integration.id} className="card">
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-4 flex-1">
                    <div
                      className={`p-3 rounded-lg ${PROVIDER_COLORS[integration.provider]}`}
                    >
                      <Mail className="w-6 h-6" />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-semibold text-neutral-900">
                          {PROVIDER_LABELS[integration.provider]}
                        </h3>
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLORS[integration.status]}`}
                        >
                          {STATUS_LABELS[integration.status]}
                        </span>
                      </div>
                      <p className="text-sm text-neutral-600 mb-2">
                        {integration.email}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-neutral-500">
                        <span>
                          Connecté le{" "}
                          {new Date(integration.connected_at).toLocaleDateString("fr-BE")}
                        </span>
                        {integration.last_sync_at && (
                          <span>
                            Dernière synchro:{" "}
                            {new Date(integration.last_sync_at).toLocaleString("fr-BE")}
                          </span>
                        )}
                      </div>
                      {integration.error_message && (
                        <div className="mt-2 text-sm text-red-600 bg-red-50 px-3 py-2 rounded">
                          {integration.error_message}
                        </div>
                      )}
                      <div className="mt-3 flex flex-wrap gap-1">
                        {integration.scopes.map((scope) => (
                          <span
                            key={scope}
                            className="px-2 py-0.5 bg-neutral-100 text-neutral-600 rounded text-xs"
                          >
                            {scope}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSync(integration.id)}
                      disabled={syncMutation.isPending}
                      className="p-2 hover:bg-neutral-100 rounded-md transition-colors"
                      title="Synchroniser maintenant"
                    >
                      <RefreshCw
                        className={`w-4 h-4 text-neutral-600 ${syncMutation.isPending ? "animate-spin" : ""}`}
                      />
                    </button>
                    <button
                      onClick={() => handleDelete(integration.id, integration.email)}
                      disabled={deleteMutation.isPending}
                      className="p-2 hover:bg-red-50 rounded-md transition-colors"
                      title="Supprimer"
                    >
                      <Trash2 className="w-4 h-4 text-red-600" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Info Card */}
      <div className="card bg-blue-50 border-blue-200">
        <div className="flex gap-3">
          <AlertCircle className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-blue-900 mb-1">
              Données synchronisées
            </h3>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• <strong>Emails:</strong> Synchronisation automatique des emails entrants et sortants</li>
              <li>• <strong>Calendriers:</strong> Événements et rendez-vous synchronisés en temps réel</li>
              <li>• <strong>Contacts:</strong> Carnet d'adresses synchronisé bidirectionnellement</li>
              <li>• <strong>Sécurité:</strong> Tokens chiffrés avec Fernet AES-128-CBC</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
