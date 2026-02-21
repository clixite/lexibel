"use client";

import { useAuth } from "@/lib/useAuth";
import { apiFetch } from "@/lib/api";
import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  Shield,
  Mail,
  Cloud,
  Phone,
  Mic,
  Brain,
  Check,
  X,
  AlertCircle,
  Loader2,
  Eye,
  EyeOff,
  Copy,
  ChevronRight,
  ChevronLeft,
  ExternalLink,
  Sparkles,
} from "lucide-react";

// ── Types ──

interface SettingField {
  key: string;
  label: string;
  type: "text" | "password" | "readonly";
  placeholder?: string;
  required?: boolean;
  helpText?: string;
  defaultValue?: string;
}

interface WizardStep {
  id: string;
  title: string;
  icon: React.ReactNode;
  description: string;
  instructions?: { text: string; link?: string; linkLabel?: string }[];
  fields: SettingField[];
  category: string;
  testable: boolean;
}

type TestStatus = "idle" | "testing" | "success" | "error";
type StepStatus = "pending" | "configured" | "error";

// ── Wizard Configuration ──

const REDIRECT_BASE = "https://lexibel.clixite.cloud";

const WIZARD_STEPS: WizardStep[] = [
  {
    id: "google",
    title: "Google Workspace",
    icon: <Mail className="w-5 h-5" />,
    description:
      "Connectez Google pour synchroniser Gmail, Google Drive et Calendar.",
    instructions: [
      {
        text: "Allez sur Google Cloud Console",
        link: "https://console.cloud.google.com",
        linkLabel: "Ouvrir Google Cloud",
      },
      { text: 'Créez un projet → Activez les APIs (Gmail, Drive, Calendar)' },
      { text: 'Credentials → Create OAuth Client ID (Web application)' },
      { text: "Copiez le Client ID et Client Secret ci-dessous" },
    ],
    fields: [
      {
        key: "GOOGLE_CLIENT_ID",
        label: "Client ID",
        type: "text",
        placeholder: "xxxx.apps.googleusercontent.com",
        required: true,
      },
      {
        key: "GOOGLE_CLIENT_SECRET",
        label: "Client Secret",
        type: "password",
        required: true,
      },
      {
        key: "GOOGLE_REDIRECT_URI",
        label: "Redirect URI (copier dans Google Cloud Console)",
        type: "readonly",
        defaultValue: `${REDIRECT_BASE}/api/v1/oauth/google/callback`,
      },
    ],
    category: "google",
    testable: true,
  },
  {
    id: "microsoft",
    title: "Microsoft 365",
    icon: <Cloud className="w-5 h-5" />,
    description:
      "Connectez Microsoft pour synchroniser Outlook, OneDrive et le calendrier.",
    instructions: [
      {
        text: "Allez sur Microsoft Entra",
        link: "https://entra.microsoft.com",
        linkLabel: "Ouvrir Entra",
      },
      { text: 'App registrations → New registration → Nom: "LexiBel"' },
      { text: "Certificates & secrets → New client secret → Copiez la Value" },
      {
        text: "Permissions API requises : Mail.Read, Mail.Send, Calendars.ReadWrite, Files.Read, User.Read",
      },
    ],
    fields: [
      {
        key: "MICROSOFT_CLIENT_ID",
        label: "Application (Client) ID",
        type: "text",
        placeholder: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        required: true,
      },
      {
        key: "MICROSOFT_CLIENT_SECRET",
        label: "Client Secret",
        type: "password",
        required: true,
      },
      {
        key: "MICROSOFT_TENANT_ID",
        label: "Tenant ID (optionnel, 'common' par défaut)",
        type: "text",
        placeholder: "common",
        defaultValue: "common",
      },
      {
        key: "MICROSOFT_REDIRECT_URI",
        label: "Redirect URI (copier dans Azure)",
        type: "readonly",
        defaultValue: `${REDIRECT_BASE}/api/v1/oauth/microsoft/callback`,
      },
    ],
    category: "microsoft",
    testable: true,
  },
  {
    id: "ringover",
    title: "Ringover",
    icon: <Phone className="w-5 h-5" />,
    description:
      "Connectez Ringover pour la téléphonie VoIP et le suivi des appels.",
    instructions: [
      {
        text: "Connectez-vous au dashboard Ringover",
        link: "https://dashboard.ringover.com",
        linkLabel: "Ouvrir Ringover",
      },
      { text: "Settings → API → Copiez la clé API" },
      {
        text: "Pour le webhook : Settings → Webhooks → Ajoutez l'URL ci-dessous",
      },
    ],
    fields: [
      {
        key: "RINGOVER_API_KEY",
        label: "Clé API",
        type: "password",
        required: true,
      },
      {
        key: "RINGOVER_WEBHOOK_SECRET",
        label: "Webhook Secret (optionnel)",
        type: "password",
      },
      {
        key: "RINGOVER_WEBHOOK_URL",
        label: "Webhook URL (copier dans Ringover)",
        type: "readonly",
        defaultValue: `${REDIRECT_BASE}/api/v1/webhooks/ringover`,
      },
    ],
    category: "ringover",
    testable: true,
  },
  {
    id: "plaud",
    title: "Plaud.ai",
    icon: <Mic className="w-5 h-5" />,
    description:
      "Connectez Plaud pour la transcription automatique des dictées.",
    instructions: [
      {
        text: "Connectez-vous au dashboard Plaud.ai",
        link: "https://plaud.ai",
        linkLabel: "Ouvrir Plaud",
      },
      { text: "API Settings → Generate API Key" },
      { text: "Copiez la clé ci-dessous" },
    ],
    fields: [
      {
        key: "PLAUD_API_KEY",
        label: "Clé API",
        type: "password",
        required: true,
      },
      {
        key: "PLAUD_WEBHOOK_URL",
        label: "Webhook URL (copier dans Plaud)",
        type: "readonly",
        defaultValue: `${REDIRECT_BASE}/api/v1/webhooks/plaud`,
      },
    ],
    category: "plaud",
    testable: true,
  },
  {
    id: "llm",
    title: "Intelligence Artificielle",
    icon: <Brain className="w-5 h-5" />,
    description:
      "Configurez les providers IA. Au moins 1 provider requis pour les fonctions IA.",
    instructions: [
      {
        text: "Anthropic (recommandé) : créez une clé sur console.anthropic.com",
        link: "https://console.anthropic.com",
        linkLabel: "Anthropic",
      },
      {
        text: "OpenAI : créez une clé sur platform.openai.com",
        link: "https://platform.openai.com/api-keys",
        linkLabel: "OpenAI",
      },
      {
        text: "Mistral : hébergé en France, GDPR natif — console.mistral.ai",
        link: "https://console.mistral.ai",
        linkLabel: "Mistral",
      },
      {
        text: "Google Gemini : disponible en europe-west1 — aistudio.google.com",
        link: "https://aistudio.google.com/apikey",
        linkLabel: "Gemini",
      },
    ],
    fields: [
      {
        key: "ANTHROPIC_API_KEY",
        label: "Anthropic (Claude) — Recommandé",
        type: "password",
        helpText: "Hébergé en UE, GDPR-ready via DPF",
      },
      {
        key: "OPENAI_API_KEY",
        label: "OpenAI (GPT)",
        type: "password",
      },
      {
        key: "MISTRAL_API_KEY",
        label: "Mistral AI — Hébergé en France",
        type: "password",
        helpText: "GDPR natif, données traitées en UE",
      },
      {
        key: "GEMINI_API_KEY",
        label: "Google Gemini",
        type: "password",
        helpText: "Disponible en europe-west1 (Belgique)",
      },
    ],
    category: "llm",
    testable: true,
  },
  {
    id: "summary",
    title: "Résumé",
    icon: <Sparkles className="w-5 h-5" />,
    description: "Récapitulatif de la configuration.",
    fields: [],
    category: "",
    testable: false,
  },
];

// ── Main Component ──

export default function SettingsWizardPage() {
  const { accessToken, tenantId, role } = useAuth();
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [formValues, setFormValues] = useState<Record<string, string>>({});
  const [visibleFields, setVisibleFields] = useState<Record<string, boolean>>(
    {}
  );
  const [testStatuses, setTestStatuses] = useState<
    Record<string, TestStatus>
  >({});
  const [testMessages, setTestMessages] = useState<
    Record<string, string>
  >({});
  const [testProviders, setTestProviders] = useState<
    Record<string, { provider: string; success: boolean; error?: string }[]>
  >({});
  const [stepStatuses, setStepStatuses] = useState<Record<string, StepStatus>>(
    {}
  );
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  // Load existing settings
  const loadSettings = useCallback(async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const data = await apiFetch<{
        settings: Record<string, { key: string; value: string; is_encrypted: boolean }[]>;
      }>("/admin/settings", accessToken, { tenantId });

      const values: Record<string, string> = {};
      const statuses: Record<string, StepStatus> = {};

      // Fill default values from readonly fields
      for (const step of WIZARD_STEPS) {
        for (const field of step.fields) {
          if (field.defaultValue) {
            values[field.key] = field.defaultValue;
          }
        }
      }

      // Override with DB values
      for (const [category, settings] of Object.entries(data.settings || {})) {
        let hasValue = false;
        for (const s of settings) {
          if (s.value && s.value !== "***") {
            values[s.key] = s.is_encrypted ? "" : s.value;
            hasValue = true;
          }
          // For encrypted fields, show placeholder to indicate value exists
          if (s.is_encrypted && s.value && s.value !== "***") {
            values[`_has_${s.key}`] = "true";
          }
        }
        if (hasValue || settings.length > 0) {
          statuses[category] = "configured";
        }
      }

      setFormValues(values);
      setStepStatuses(statuses);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message);
    } finally {
      setLoading(false);
    }
  }, [accessToken, tenantId]);

  useEffect(() => {
    loadSettings();
  }, [loadSettings]);

  // Access control
  if (role !== "super_admin") {
    return (
      <div className="bg-danger-50 border border-danger-200 rounded-lg p-6">
        <h2 className="text-lg font-semibold text-danger-900 mb-2">
          Accès refusé
        </h2>
        <p className="text-danger-700 text-sm">
          Seul un super administrateur peut configurer les intégrations.
        </p>
        <button
          onClick={() => router.push("/dashboard")}
          className="mt-4 btn-primary"
        >
          Retour au dashboard
        </button>
      </div>
    );
  }

  const currentWizardStep = WIZARD_STEPS[currentStep];

  // ── Handlers ──

  const handleFieldChange = (key: string, value: string) => {
    setFormValues((prev) => ({ ...prev, [key]: value }));
  };

  const toggleVisibility = (key: string) => {
    setVisibleFields((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const copyToClipboard = async (text: string, key: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(key);
    setTimeout(() => setCopied(null), 2000);
  };

  const handleSave = async () => {
    if (!accessToken || !currentWizardStep) return;
    setSaving(true);
    setError(null);

    try {
      const settingsToSave = currentWizardStep.fields
        .filter((f) => f.type !== "readonly" && formValues[f.key])
        .map((f) => ({
          key: f.key,
          value: formValues[f.key],
          category: currentWizardStep.category,
          label: f.label,
          description: f.helpText || "",
          is_required: f.required || false,
        }));

      if (settingsToSave.length === 0) {
        setSaving(false);
        return;
      }

      await apiFetch("/admin/settings", accessToken, {
        method: "PUT",
        tenantId,
        body: JSON.stringify({ settings: settingsToSave }),
      });

      setStepStatuses((prev) => ({
        ...prev,
        [currentWizardStep.category]: "configured",
      }));
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message);
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    if (!accessToken || !currentWizardStep) return;
    const category = currentWizardStep.category;

    setTestStatuses((prev) => ({ ...prev, [category]: "testing" }));
    setTestMessages((prev) => ({ ...prev, [category]: "" }));

    try {
      // Save first
      await handleSave();

      const result = await apiFetch<{
        success: boolean;
        message?: string;
        error?: string;
        providers?: { provider: string; success: boolean; error?: string }[];
      }>(`/admin/settings/test/${category}`, accessToken, {
        method: "POST",
        tenantId,
      });

      setTestStatuses((prev) => ({
        ...prev,
        [category]: result.success ? "success" : "error",
      }));
      setTestMessages((prev) => ({
        ...prev,
        [category]: result.message || result.error || "",
      }));
      if (result.providers) {
        setTestProviders((prev) => ({
          ...prev,
          [category]: result.providers!,
        }));
      }

      if (result.success) {
        setStepStatuses((prev) => ({ ...prev, [category]: "configured" }));
      } else {
        setStepStatuses((prev) => ({ ...prev, [category]: "error" }));
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setTestStatuses((prev) => ({ ...prev, [category]: "error" }));
      setTestMessages((prev) => ({
        ...prev,
        [category]: message,
      }));
    }
  };

  const getStepIcon = (stepIndex: number): React.ReactNode => {
    const step = WIZARD_STEPS[stepIndex];
    const status = stepStatuses[step.category];
    if (stepIndex === currentStep) return step.icon;
    if (status === "configured")
      return <Check className="w-4 h-4 text-emerald-500" />;
    if (status === "error")
      return <AlertCircle className="w-4 h-4 text-red-500" />;
    return step.icon;
  };

  // ── Render ──

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
        <span className="ml-3 text-neutral-600">
          Chargement de la configuration...
        </span>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-neutral-900 flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center">
            <Shield className="w-6 h-6 text-accent" />
          </div>
          Configuration
        </h1>
        <p className="text-neutral-600 mt-2 text-sm">
          Assistant de paramétrage — Configurez vos intégrations pas à pas.
        </p>
      </div>

      {/* Step Navigation */}
      <div className="mb-8">
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {WIZARD_STEPS.map((step, i) => {
            const isActive = i === currentStep;
            const status = stepStatuses[step.category];
            const isDone = status === "configured";

            return (
              <button
                key={step.id}
                onClick={() => setCurrentStep(i)}
                className={`flex items-center gap-2 px-4 py-2.5 rounded-lg border-2 transition-all min-w-fit ${
                  isActive
                    ? "border-accent bg-accent/5 shadow-md"
                    : isDone
                    ? "border-emerald-300 bg-emerald-50"
                    : "border-neutral-200 bg-white hover:border-neutral-300"
                }`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${
                    isActive
                      ? "bg-accent text-white"
                      : isDone
                      ? "bg-emerald-500 text-white"
                      : "bg-neutral-100 text-neutral-500"
                  }`}
                >
                  {isDone ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    i + 1
                  )}
                </div>
                <span
                  className={`text-sm font-medium whitespace-nowrap ${
                    isActive
                      ? "text-neutral-900"
                      : isDone
                      ? "text-emerald-700"
                      : "text-neutral-600"
                  }`}
                >
                  {step.title}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-6 bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          {error}
          <button
            onClick={() => setError(null)}
            className="ml-auto text-danger-500 hover:text-danger-700"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Step Content */}
      <div className="card p-0 overflow-hidden">
        {/* Step Header */}
        <div className="bg-neutral-50 border-b border-neutral-200 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-accent/10 flex items-center justify-center text-accent">
              {getStepIcon(currentStep)}
            </div>
            <div>
              <h2 className="text-xl font-bold text-neutral-900">
                {currentWizardStep.title}
              </h2>
              <p className="text-sm text-neutral-600">
                {currentWizardStep.description}
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Summary Step */}
          {currentWizardStep.id === "summary" ? (
            <SummaryView
              stepStatuses={stepStatuses}
              testStatuses={testStatuses}
              testMessages={testMessages}
              testProviders={testProviders}
              onGoToStep={setCurrentStep}
              onGoToDashboard={() => router.push("/dashboard")}
            />
          ) : (
            <>
              {/* Instructions */}
              {currentWizardStep.instructions &&
                currentWizardStep.instructions.length > 0 && (
                  <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                    <h3 className="text-sm font-semibold text-blue-900 mb-2">
                      Comment obtenir les credentials :
                    </h3>
                    <ol className="space-y-1.5">
                      {currentWizardStep.instructions.map((inst, i) => (
                        <li
                          key={i}
                          className="text-sm text-blue-800 flex items-start gap-2"
                        >
                          <span className="bg-blue-200 text-blue-900 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">
                            {i + 1}
                          </span>
                          <span>
                            {inst.text}
                            {inst.link && (
                              <a
                                href={inst.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="ml-2 inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline"
                              >
                                {inst.linkLabel || "Ouvrir"}
                                <ExternalLink className="w-3 h-3" />
                              </a>
                            )}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

              {/* Fields */}
              <div className="space-y-4">
                {currentWizardStep.fields.map((field) => (
                  <div key={field.key}>
                    <label className="block text-sm font-medium text-neutral-700 mb-1">
                      {field.label}
                      {field.required && (
                        <span className="text-red-500 ml-1">*</span>
                      )}
                    </label>
                    {field.helpText && (
                      <p className="text-xs text-neutral-500 mb-1">
                        {field.helpText}
                      </p>
                    )}

                    {field.type === "readonly" ? (
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={
                            formValues[field.key] || field.defaultValue || ""
                          }
                          readOnly
                          className="flex-1 px-3 py-2 bg-neutral-100 border border-neutral-200 rounded-lg text-sm text-neutral-600 font-mono"
                        />
                        <button
                          onClick={() =>
                            copyToClipboard(
                              formValues[field.key] ||
                                field.defaultValue ||
                                "",
                              field.key
                            )
                          }
                          className={`px-3 py-2 rounded-lg border transition-colors text-sm ${
                            copied === field.key
                              ? "bg-emerald-50 border-emerald-300 text-emerald-700"
                              : "bg-white border-neutral-200 hover:bg-neutral-50 text-neutral-600"
                          }`}
                        >
                          {copied === field.key ? (
                            <Check className="w-4 h-4" />
                          ) : (
                            <Copy className="w-4 h-4" />
                          )}
                        </button>
                      </div>
                    ) : (
                      <div className="relative">
                        <input
                          type={
                            field.type === "password" &&
                            !visibleFields[field.key]
                              ? "password"
                              : "text"
                          }
                          value={formValues[field.key] || ""}
                          onChange={(e) =>
                            handleFieldChange(field.key, e.target.value)
                          }
                          placeholder={
                            formValues[`_has_${field.key}`]
                              ? "(valeur existante — laisser vide pour garder)"
                              : field.placeholder
                          }
                          className="w-full px-3 py-2 border border-neutral-300 rounded-lg text-sm focus:ring-2 focus:ring-accent/30 focus:border-accent transition-colors"
                        />
                        {field.type === "password" && (
                          <button
                            type="button"
                            onClick={() => toggleVisibility(field.key)}
                            className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600"
                          >
                            {visibleFields[field.key] ? (
                              <EyeOff className="w-4 h-4" />
                            ) : (
                              <Eye className="w-4 h-4" />
                            )}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* Test Result */}
              {testStatuses[currentWizardStep.category] &&
                testStatuses[currentWizardStep.category] !== "idle" && (
                  <div
                    className={`mt-4 p-3 rounded-lg border text-sm ${
                      testStatuses[currentWizardStep.category] === "testing"
                        ? "bg-blue-50 border-blue-200 text-blue-700"
                        : testStatuses[currentWizardStep.category] === "success"
                        ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                        : "bg-red-50 border-red-200 text-red-700"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      {testStatuses[currentWizardStep.category] ===
                        "testing" && (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      )}
                      {testStatuses[currentWizardStep.category] ===
                        "success" && <Check className="w-4 h-4" />}
                      {testStatuses[currentWizardStep.category] === "error" && (
                        <AlertCircle className="w-4 h-4" />
                      )}
                      <span>
                        {testStatuses[currentWizardStep.category] === "testing"
                          ? "Test en cours..."
                          : testMessages[currentWizardStep.category]}
                      </span>
                    </div>

                    {/* LLM Provider Details */}
                    {testProviders[currentWizardStep.category] && (
                      <div className="mt-2 space-y-1">
                        {testProviders[currentWizardStep.category].map(
                          (p, i) => (
                            <div
                              key={i}
                              className="flex items-center gap-2 text-xs"
                            >
                              {p.success ? (
                                <Check className="w-3 h-3 text-emerald-500" />
                              ) : (
                                <X className="w-3 h-3 text-red-500" />
                              )}
                              <span>
                                {p.provider}
                                {p.error && ` — ${p.error}`}
                              </span>
                            </div>
                          )
                        )}
                      </div>
                    )}
                  </div>
                )}

              {/* Action Buttons */}
              <div className="mt-6 flex items-center gap-3">
                {currentWizardStep.testable && (
                  <button
                    onClick={handleTest}
                    disabled={
                      testStatuses[currentWizardStep.category] === "testing"
                    }
                    className="px-4 py-2 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-50 text-neutral-700 text-sm font-medium transition-colors flex items-center gap-2"
                  >
                    {testStatuses[currentWizardStep.category] === "testing" ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Shield className="w-4 h-4" />
                    )}
                    Tester
                  </button>
                )}

                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 text-white text-sm font-medium transition-colors flex items-center gap-2"
                >
                  {saving ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Check className="w-4 h-4" />
                  )}
                  Sauvegarder
                </button>
              </div>
            </>
          )}
        </div>

        {/* Navigation */}
        <div className="border-t border-neutral-200 px-6 py-4 flex justify-between">
          <button
            onClick={() => setCurrentStep((s) => Math.max(0, s - 1))}
            disabled={currentStep === 0}
            className="px-4 py-2 rounded-lg border border-neutral-300 bg-white hover:bg-neutral-50 text-neutral-700 text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="w-4 h-4" />
            Précédent
          </button>

          <button
            onClick={() =>
              setCurrentStep((s) =>
                Math.min(WIZARD_STEPS.length - 1, s + 1)
              )
            }
            disabled={currentStep === WIZARD_STEPS.length - 1}
            className="px-4 py-2 rounded-lg bg-accent hover:bg-accent/90 text-white text-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Suivant
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Summary View ──

function SummaryView({
  stepStatuses,
  testStatuses,
  testMessages,
  testProviders,
  onGoToStep,
  onGoToDashboard,
}: {
  stepStatuses: Record<string, StepStatus>;
  testStatuses: Record<string, TestStatus>;
  testMessages: Record<string, string>;
  testProviders: Record<
    string,
    { provider: string; success: boolean; error?: string }[]
  >;
  onGoToStep: (step: number) => void;
  onGoToDashboard: () => void;
}) {
  const integrations = [
    {
      name: "Google Workspace",
      category: "google",
      icon: <Mail className="w-5 h-5" />,
      services: "Gmail, Drive, Calendar",
      stepIndex: 0,
    },
    {
      name: "Microsoft 365",
      category: "microsoft",
      icon: <Cloud className="w-5 h-5" />,
      services: "Outlook, OneDrive",
      stepIndex: 1,
    },
    {
      name: "Ringover",
      category: "ringover",
      icon: <Phone className="w-5 h-5" />,
      services: "Téléphonie VoIP",
      stepIndex: 2,
    },
    {
      name: "Plaud.ai",
      category: "plaud",
      icon: <Mic className="w-5 h-5" />,
      services: "Transcription",
      stepIndex: 3,
    },
  ];

  const getStatusBadge = (category: string) => {
    const status = stepStatuses[category];
    const testStatus = testStatuses[category];

    if (testStatus === "success" || status === "configured") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-100 text-emerald-700 border border-emerald-200">
          <Check className="w-3 h-3" /> Configuré
        </span>
      );
    }
    if (testStatus === "error" || status === "error") {
      return (
        <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-red-100 text-red-700 border border-red-200">
          <AlertCircle className="w-3 h-3" /> Erreur
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium bg-neutral-100 text-neutral-600 border border-neutral-200">
        Non configuré
      </span>
    );
  };

  const configuredCount = integrations.filter(
    (i) =>
      stepStatuses[i.category] === "configured" ||
      testStatuses[i.category] === "success"
  ).length;

  return (
    <div className="space-y-6">
      <div className="text-center mb-8">
        <div className="w-16 h-16 rounded-full bg-accent/10 flex items-center justify-center mx-auto mb-4">
          <Sparkles className="w-8 h-8 text-accent" />
        </div>
        <h2 className="text-2xl font-bold text-neutral-900">
          {configuredCount > 0
            ? "Configuration terminée !"
            : "Récapitulatif"}
        </h2>
        <p className="text-neutral-600 mt-1 text-sm">
          {configuredCount}/{integrations.length} intégrations configurées
        </p>
      </div>

      <div className="space-y-3">
        {integrations.map((integration) => (
          <div
            key={integration.category}
            className="flex items-center justify-between p-4 bg-neutral-50 border border-neutral-200 rounded-lg"
          >
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white border border-neutral-200 flex items-center justify-center text-neutral-600">
                {integration.icon}
              </div>
              <div>
                <p className="font-semibold text-neutral-900">
                  {integration.name}
                </p>
                <p className="text-xs text-neutral-500">
                  {integration.services}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge(integration.category)}
              <button
                onClick={() => onGoToStep(integration.stepIndex)}
                className="text-accent hover:text-accent/80 text-sm font-medium"
              >
                Modifier
              </button>
            </div>
          </div>
        ))}

        {/* LLM Providers */}
        <div className="p-4 bg-neutral-50 border border-neutral-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white border border-neutral-200 flex items-center justify-center text-neutral-600">
                <Brain className="w-5 h-5" />
              </div>
              <div>
                <p className="font-semibold text-neutral-900">
                  Intelligence Artificielle
                </p>
                <p className="text-xs text-neutral-500">Providers LLM</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {getStatusBadge("llm")}
              <button
                onClick={() => onGoToStep(4)}
                className="text-accent hover:text-accent/80 text-sm font-medium"
              >
                Modifier
              </button>
            </div>
          </div>

          {testProviders["llm"] && (
            <div className="ml-13 space-y-1 mt-2">
              {testProviders["llm"].map((p, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  {p.success ? (
                    <Check className="w-3 h-3 text-emerald-500" />
                  ) : (
                    <X className="w-3 h-3 text-red-400" />
                  )}
                  <span
                    className={
                      p.success ? "text-emerald-700" : "text-neutral-500"
                    }
                  >
                    {p.provider}
                    {p.success ? " — Actif" : " — Non configuré"}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex justify-center mt-8">
        <button
          onClick={onGoToDashboard}
          className="px-6 py-2.5 rounded-lg bg-accent hover:bg-accent/90 text-white font-medium transition-colors flex items-center gap-2"
        >
          Aller au Dashboard
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
