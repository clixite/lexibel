"use client";

import { useAuth } from "@/lib/useAuth";
import { useState, useEffect } from "react";
import { Mail, Cloud, Loader2, Check, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";

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

const PROVIDER_LABELS: Record<string, string> = {
  google: "Google Workspace",
  microsoft: "Microsoft 365",
};

const PROVIDER_DESCRIPTIONS: Record<string, string> = {
  google: "Gmail, Google Calendar, Google Drive",
  microsoft: "Outlook Mail, Outlook Calendar, OneDrive",
};

const PROVIDER_ICONS: Record<string, React.ReactNode> = {
  google: <Mail className="w-6 h-6 text-blue-600" />,
  microsoft: <Cloud className="w-6 h-6 text-orange-600" />,
};

const STATUS_LABELS: Record<string, string> = {
  active: "Actif",
  expired: "Expiré",
  error: "Erreur",
};

const STATUS_COLORS: Record<string, string> = {
  active: "bg-success-50 text-success-700",
  expired: "bg-warning-50 text-warning-700",
  error: "bg-danger-50 text-danger-700",
};

export default function IntegrationsManager() {
  const { accessToken, tenantId } = useAuth();
  const [integrations, setIntegrations] = useState<OAuthIntegration[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);

  const fetchIntegrations = async () => {
    if (!accessToken) return;
    setLoading(true);
    setError(null);
    try {
      const data = await apiFetch<{ items: OAuthIntegration[] }>(
        "/admin/integrations",
        accessToken,
        { tenantId }
      );
      setIntegrations(data.items || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIntegrations();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const handleConnect = async (provider: "google" | "microsoft") => {
    if (!accessToken) return;

    setConnectingProvider(provider);
    setError(null);

    try {
      const response = await apiFetch<{ oauth_url: string }>(
        `/admin/integrations/connect/${provider}`,
        accessToken,
        { tenantId }
      );

      if (response.oauth_url) {
        window.open(response.oauth_url, "_blank", "width=500,height=600");
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setConnectingProvider(null);
    }
  };

  const handleDisconnect = async (integrationId: string) => {
    if (!accessToken) return;

    if (!confirm("Êtes-vous sûr de vouloir déconnecter cette intégration?")) {
      return;
    }

    try {
      await apiFetch(
        `/admin/integrations/${integrationId}`,
        accessToken,
        { method: "DELETE", tenantId }
      );
      await fetchIntegrations();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Integration Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Google Workspace */}
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-blue-50 rounded-lg">
              <Mail className="w-6 h-6 text-blue-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-neutral-900 mb-1">
                {PROVIDER_LABELS.google}
              </h3>
              <p className="text-sm text-neutral-600 mb-4">
                {PROVIDER_DESCRIPTIONS.google}
              </p>

              {/* Check if Google is connected */}
              {integrations.some((i) => i.provider === "google") ? (
                <div className="space-y-3">
                  {integrations
                    .filter((i) => i.provider === "google")
                    .map((integration) => (
                      <div key={integration.id} className="text-xs bg-neutral-50 p-2 rounded">
                        <p className="font-medium text-neutral-900">
                          {integration.email}
                        </p>
                        <span
                          className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${
                            STATUS_COLORS[integration.status]
                          }`}
                        >
                          {STATUS_LABELS[integration.status]}
                        </span>
                      </div>
                    ))}
                  <button
                    onClick={() => handleDisconnect(integrations.find((i) => i.provider === "google")?.id || "")}
                    className="text-danger-600 hover:text-danger-700 text-sm font-medium"
                  >
                    Déconnecter
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => handleConnect("google")}
                  disabled={connectingProvider === "google"}
                  className="btn-primary flex items-center gap-2 w-full justify-center"
                >
                  {connectingProvider === "google" ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Connexion...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      Connecter Google
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Microsoft 365 */}
        <div className="card">
          <div className="flex items-start gap-4">
            <div className="p-3 bg-orange-50 rounded-lg">
              <Cloud className="w-6 h-6 text-orange-600" />
            </div>
            <div className="flex-1">
              <h3 className="font-semibold text-neutral-900 mb-1">
                {PROVIDER_LABELS.microsoft}
              </h3>
              <p className="text-sm text-neutral-600 mb-4">
                {PROVIDER_DESCRIPTIONS.microsoft}
              </p>

              {/* Check if Microsoft is connected */}
              {integrations.some((i) => i.provider === "microsoft") ? (
                <div className="space-y-3">
                  {integrations
                    .filter((i) => i.provider === "microsoft")
                    .map((integration) => (
                      <div key={integration.id} className="text-xs bg-neutral-50 p-2 rounded">
                        <p className="font-medium text-neutral-900">
                          {integration.email}
                        </p>
                        <span
                          className={`inline-block mt-1 px-2 py-0.5 rounded text-xs font-medium ${
                            STATUS_COLORS[integration.status]
                          }`}
                        >
                          {STATUS_LABELS[integration.status]}
                        </span>
                      </div>
                    ))}
                  <button
                    onClick={() => handleDisconnect(integrations.find((i) => i.provider === "microsoft")?.id || "")}
                    className="text-danger-600 hover:text-danger-700 text-sm font-medium"
                  >
                    Déconnecter
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => handleConnect("microsoft")}
                  disabled={connectingProvider === "microsoft"}
                  className="btn-primary flex items-center gap-2 w-full justify-center"
                >
                  {connectingProvider === "microsoft" ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Connexion...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      Connecter Microsoft
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* All Integrations List */}
      {integrations.length > 0 && (
        <div className="card">
          <h2 className="text-base font-semibold text-neutral-900 mb-4">
            Intégrations actives
          </h2>
          {loading ? (
            <div className="flex justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-neutral-200">
                    <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                      Provider
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                      Statut
                    </th>
                    <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                      Connecté le
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-100">
                  {integrations.map((integration) => (
                    <tr key={integration.id} className="hover:bg-neutral-50 transition-colors">
                      <td className="py-3 px-4 font-medium text-neutral-900">
                        {PROVIDER_LABELS[integration.provider]}
                      </td>
                      <td className="py-3 px-4 text-neutral-600">
                        {integration.email}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            STATUS_COLORS[integration.status]
                          }`}
                        >
                          {STATUS_LABELS[integration.status]}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-neutral-500 text-xs">
                        {new Date(integration.connected_at).toLocaleDateString("fr-BE")}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
