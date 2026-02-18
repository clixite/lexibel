"use client";

import { useState, useEffect } from "react";
import { useSession } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Mail, Cloud, Shield, Calendar, HardDrive, Check } from "lucide-react";
import { OAuthWizard } from "@/components/oauth/OAuthWizard";
import { ProviderCard, Provider } from "@/components/oauth/ProviderCard";
import { ScopeSelector, Scope } from "@/components/oauth/ScopeSelector";
import { ConnectionStatus } from "@/components/oauth/ConnectionStatus";
import { apiFetch } from "@/lib/api";

const WIZARD_STEPS = [
  {
    id: "provider",
    title: "Fournisseur",
    description: "Choisir votre service",
  },
  {
    id: "permissions",
    title: "Autorisations",
    description: "Sélectionner les accès",
  },
  {
    id: "connect",
    title: "Connexion",
    description: "Autoriser l'accès",
  },
  {
    id: "verify",
    title: "Vérification",
    description: "Tester la connexion",
  },
];

const PROVIDERS: Provider[] = [
  {
    id: "google",
    name: "Google Workspace",
    description: "Gmail, Drive, Docs, Calendar",
    features: [
      "Synchronisation emails Gmail",
      "Google Drive & Google Docs",
      "Édition en ligne des documents",
      "Agenda Google Calendar",
      "Recherche sémantique (IA)",
    ],
    icon: <Mail className="w-6 h-6 text-blue-400" />,
    color: "bg-blue-500/10",
  },
  {
    id: "microsoft",
    name: "Microsoft 365",
    description: "Outlook, OneDrive, SharePoint, Word",
    features: [
      "Synchronisation emails Outlook",
      "OneDrive & SharePoint",
      "Word / Excel Online",
      "Agenda Outlook",
      "Recherche sémantique (IA)",
    ],
    icon: <Cloud className="w-6 h-6 text-orange-400" />,
    color: "bg-orange-500/10",
  },
];

const GOOGLE_SCOPES: Scope[] = [
  {
    id: "gmail.readonly",
    name: "Lire vos emails",
    description: "Accès en lecture seule à votre boîte mail Gmail",
    required: true,
  },
  {
    id: "gmail.send",
    name: "Envoyer des emails",
    description: "Envoyer des emails en votre nom depuis LexiBel",
    required: false,
  },
  {
    id: "drive.readonly",
    name: "Accéder à Google Drive",
    description: "Synchroniser les fichiers et dossiers de Google Drive (métadonnées uniquement, vos fichiers restent chez Google)",
    required: true,
  },
  {
    id: "documents.readonly",
    name: "Lire les Google Docs",
    description: "Accéder au contenu des documents Google Docs pour l'indexation et la recherche",
    required: false,
  },
  {
    id: "calendar.readonly",
    name: "Accéder à votre agenda",
    description: "Lire les événements de votre calendrier Google",
    required: false,
  },
];

const MICROSOFT_SCOPES: Scope[] = [
  {
    id: "mail.read",
    name: "Lire vos emails",
    description: "Accès en lecture seule à votre boîte mail Outlook",
    required: true,
  },
  {
    id: "mail.send",
    name: "Envoyer des emails",
    description: "Envoyer des emails en votre nom depuis LexiBel",
    required: false,
  },
  {
    id: "files.read",
    name: "Accéder à OneDrive",
    description: "Synchroniser les fichiers OneDrive (métadonnées uniquement, vos fichiers restent chez Microsoft)",
    required: true,
  },
  {
    id: "sites.read.all",
    name: "Accéder à SharePoint",
    description: "Accéder aux bibliothèques de documents SharePoint de votre organisation",
    required: false,
  },
  {
    id: "calendars.read",
    name: "Accéder à votre agenda",
    description: "Lire les événements de votre calendrier Outlook",
    required: false,
  },
];

interface OAuthToken {
  id: string;
  provider: string;
  email_address: string | null;
  status: string;
}

export default function IntegrationsPage() {
  const { data: session } = useSession();
  const searchParams = useSearchParams();
  const [currentStep, setCurrentStep] = useState(0);
  const [selectedProvider, setSelectedProvider] = useState<"google" | "microsoft" | null>(null);
  const [selectedScopes, setSelectedScopes] = useState<string[]>([]);
  const [connectedEmail, setConnectedEmail] = useState<string>("");
  const [connectedTokens, setConnectedTokens] = useState<OAuthToken[]>([]);
  const [loading, setLoading] = useState(false);

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  // Handle OAuth callback
  useEffect(() => {
    const status = searchParams?.get("status");
    const email = searchParams?.get("email");

    if (status === "success" && email) {
      setConnectedEmail(email);
      setCurrentStep(3); // Go to verification step
    }
  }, [searchParams]);

  // Fetch connected tokens
  useEffect(() => {
    if (!token) return;

    const fetchTokens = async () => {
      try {
        const tokens = await apiFetch<OAuthToken[]>("/oauth/tokens", token, {
          tenantId,
        });
        setConnectedTokens(tokens || []);
      } catch (error) {
        console.error("Failed to fetch tokens:", error);
      }
    };

    fetchTokens();
  }, [token, tenantId]);

  const handleProviderSelect = (provider: "google" | "microsoft") => {
    setSelectedProvider(provider);
    // Auto-select required scopes
    const requiredScopes =
      provider === "google"
        ? GOOGLE_SCOPES.filter((s) => s.required).map((s) => s.id)
        : MICROSOFT_SCOPES.filter((s) => s.required).map((s) => s.id);
    setSelectedScopes(requiredScopes);
  };

  const handleScopeToggle = (scopeId: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scopeId)
        ? prev.filter((id) => id !== scopeId)
        : [...prev, scopeId]
    );
  };

  const handleConnect = async () => {
    if (!selectedProvider || !token) return;

    setLoading(true);
    try {
      // Get authorization URL
      const response = await apiFetch<{
        authorization_url: string;
        state: string;
        code_verifier: string;
      }>(`/oauth/${selectedProvider}/authorize`, token, {
        tenantId,
      });

      // Store code_verifier in sessionStorage for callback
      sessionStorage.setItem("oauth_code_verifier", response.code_verifier);
      sessionStorage.setItem("oauth_state", response.state);

      // Open OAuth popup
      const width = 500;
      const height = 600;
      const left = window.screen.width / 2 - width / 2;
      const top = window.screen.height / 2 - height / 2;

      window.open(
        response.authorization_url,
        "oauth_popup",
        `width=${width},height=${height},left=${left},top=${top}`
      );
    } catch (error) {
      console.error("Failed to start OAuth flow:", error);
    } finally {
      setLoading(false);
    }
  };

  const isProviderConnected = (providerId: string) => {
    return connectedTokens.some(
      (t) => t.provider === providerId && t.status === "active"
    );
  };

  return (
    <div className="min-h-screen bg-deep-slate-900 p-6">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-deep-slate-100 mb-2">
            Connexion OAuth SSO
          </h1>
          <p className="text-deep-slate-400">
            Connectez vos services Google Workspace ou Microsoft 365 pour
            synchroniser automatiquement vos emails et calendriers.
          </p>
        </div>

        {/* Wizard */}
        <OAuthWizard steps={WIZARD_STEPS} currentStep={currentStep}>
          {/* Step 1: Choose Provider */}
          {currentStep === 0 && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-deep-slate-100 mb-2">
                  Choisissez votre fournisseur
                </h2>
                <p className="text-deep-slate-400">
                  Sélectionnez le service que vous souhaitez connecter
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {PROVIDERS.map((provider) => (
                  <ProviderCard
                    key={provider.id}
                    provider={provider}
                    selected={selectedProvider === provider.id}
                    connected={isProviderConnected(provider.id)}
                    onSelect={() => handleProviderSelect(provider.id)}
                  />
                ))}
              </div>

              <div className="flex justify-end">
                <button
                  onClick={() => setCurrentStep(1)}
                  disabled={!selectedProvider}
                  className={`
                    px-6 py-2.5 rounded-lg font-medium transition-all
                    ${
                      selectedProvider
                        ? "bg-warm-gold-500 hover:bg-warm-gold-600 text-deep-slate-900"
                        : "bg-deep-slate-700 text-deep-slate-400 cursor-not-allowed"
                    }
                  `}
                >
                  Continuer →
                </button>
              </div>
            </div>
          )}

          {/* Step 2: Select Scopes */}
          {currentStep === 1 && selectedProvider && (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <h2 className="text-2xl font-bold text-deep-slate-100 mb-2">
                  Autorisations demandées
                </h2>
                <p className="text-deep-slate-400">
                  Choisissez les permissions que vous souhaitez accorder
                </p>
              </div>

              <ScopeSelector
                scopes={
                  selectedProvider === "google"
                    ? GOOGLE_SCOPES
                    : MICROSOFT_SCOPES
                }
                selectedScopes={selectedScopes}
                onToggle={handleScopeToggle}
              />

              {/* Security Notice */}
              <div className="p-4 rounded-lg bg-deep-slate-800/50 border border-deep-slate-700">
                <div className="flex items-start gap-3">
                  <Shield className="w-5 h-5 text-warm-gold-500 mt-0.5" />
                  <div>
                    <h4 className="font-medium text-deep-slate-100 mb-1">
                      Sécurité et confidentialité
                    </h4>
                    <p className="text-sm text-deep-slate-400">
                      LexiBel ne stocke jamais vos mots de passe. L'accès peut
                      être révoqué à tout moment depuis cette page. Tous les
                      tokens sont chiffrés avec AES-256.
                    </p>
                  </div>
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={() => setCurrentStep(0)}
                  className="px-6 py-2.5 rounded-lg border border-deep-slate-700 hover:bg-deep-slate-800 text-deep-slate-200 font-medium transition-colors"
                >
                  ← Retour
                </button>
                <button
                  onClick={() => {
                    setCurrentStep(2);
                    handleConnect();
                  }}
                  className="flex-1 px-6 py-2.5 rounded-lg bg-warm-gold-500 hover:bg-warm-gold-600 text-deep-slate-900 font-medium transition-colors"
                >
                  Autoriser l'accès →
                </button>
              </div>
            </div>
          )}

          {/* Step 3: OAuth Redirect */}
          {currentStep === 2 && (
            <div className="text-center py-12">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-warm-gold-500/10 mb-6">
                <div className="w-8 h-8 border-4 border-warm-gold-500 border-t-transparent rounded-full animate-spin" />
              </div>
              <h2 className="text-2xl font-bold text-deep-slate-100 mb-2">
                Connexion en cours...
              </h2>
              <p className="text-deep-slate-400 mb-8">
                Veuillez autoriser l'accès dans la fenêtre qui s'est ouverte
              </p>
              <button
                onClick={() => setCurrentStep(1)}
                className="px-6 py-2.5 rounded-lg border border-deep-slate-700 hover:bg-deep-slate-800 text-deep-slate-200 font-medium transition-colors"
              >
                Annuler
              </button>
            </div>
          )}

          {/* Step 4: Verification */}
          {currentStep === 3 && selectedProvider && (
            <ConnectionStatus
              provider={selectedProvider}
              email={connectedEmail}
              onComplete={() => {
                // Reset wizard
                setCurrentStep(0);
                setSelectedProvider(null);
                setSelectedScopes([]);
                setConnectedEmail("");
              }}
              onRetry={() => setCurrentStep(1)}
            />
          )}
        </OAuthWizard>

        {/* Connected Accounts */}
        {connectedTokens.length > 0 && currentStep === 0 && (
          <div className="mt-12">
            <h3 className="text-xl font-bold text-deep-slate-100 mb-4">
              Comptes connectés
            </h3>
            <div className="space-y-3">
              {connectedTokens.map((tokenData) => (
                <div
                  key={tokenData.id}
                  className="p-4 rounded-lg bg-deep-slate-800/50 border border-deep-slate-700 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-success-500/10">
                      <Check className="w-5 h-5 text-success-400" />
                    </div>
                    <div>
                      <div className="font-medium text-deep-slate-100">
                        {tokenData.email_address || "Email non disponible"}
                      </div>
                      <div className="text-sm text-deep-slate-400">
                        {tokenData.provider === "google"
                          ? "Google Workspace"
                          : "Microsoft 365"}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-2.5 py-1 rounded-full bg-success-500/20 border border-success-500/30 text-success-400 font-medium">
                      {tokenData.status === "active" ? "Actif" : tokenData.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
