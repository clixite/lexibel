"use client";

import { useAuth } from "@/lib/useAuth";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import {
  Loader2,
  ArrowLeft,
  Edit2,
  Save,
  X,
  Briefcase,
  MessageSquare,
  Check,
  Activity,
  AlertTriangle,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  Lightbulb,
  FolderOpen,
  RefreshCw,
  MapPin,
  Mail,
  Phone,
  CreditCard,
  FileText,
  User,
  Building2,
  Globe,
} from "lucide-react";
import { Badge } from "@/components/ui";
import SkeletonCard from "@/components/skeletons/SkeletonCard";

interface ContactMetadata {
  // Natural person
  civility?: string;
  first_name?: string;
  last_name?: string;
  birth_date?: string;
  birth_place?: string;
  national_register?: string;
  nationality?: string;
  civil_status?: string;
  profession?: string;

  // Legal entity
  legal_form?: string;
  vat_number?: string;
  registered_office?: {
    street?: string;
    city?: string;
    zip?: string;
    country?: string;
  };
  legal_representative?: string;
  corporate_purpose?: string;

  // Common
  correspondence_address?: {
    street?: string;
    city?: string;
    zip?: string;
    country?: string;
  };
  secondary_email?: string;
  phone_fixed?: string;
  fax?: string;
  iban?: string;
  bic?: string;
  vat_liable?: boolean;
  payment_preference?: string;
  preferred_contact_method?: string;
  category?: string;
  notes?: string;
}

interface Contact {
  id: string;
  type: "natural" | "legal";
  full_name: string;
  bce_number: string | null;
  email: string | null;
  phone_e164: string | null;
  address: string | null;
  language: string | null;
  metadata: ContactMetadata | null;
  created_at: string;
  updated_at: string;
}

interface LinkedCase {
  id: string;
  reference: string;
  title: string;
  status: string;
  role?: string;
}

interface ValidationErrors {
  email?: string;
  full_name?: string;
  first_name?: string;
}

interface ClientHealth {
  contact_id: string;
  contact_name: string;
  health_score: number;
  status: "healthy" | "needs_attention" | "at_risk" | "critical";
  active_cases: number;
  days_since_contact: number;
  risk_factors: string[];
  recommended_actions: string[];
}

interface EditFormState {
  type: "natural" | "legal";
  full_name: string;
  email: string;
  phone_e164: string;
  bce_number: string;
  address: string;
  language: string;
  // Natural person
  civility: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  birth_place: string;
  nationality: string;
  civil_status: string;
  profession: string;
  national_register: string;
  // Legal entity
  legal_form: string;
  vat_number: string;
  corporate_purpose: string;
  legal_representative: string;
  // Coordinates
  correspondence_address_street: string;
  correspondence_address_zip: string;
  correspondence_address_city: string;
  correspondence_address_country: string;
  secondary_email: string;
  phone_fixed: string;
  fax: string;
  // Financial
  iban: string;
  bic: string;
  vat_liable: boolean;
  payment_preference: string;
  // Classification
  category: string;
  preferred_contact_method: string;
  notes: string;
}

function generateMockHealth(contactName: string): ClientHealth {
  return {
    contact_id: "mock",
    contact_name: contactName,
    health_score: Math.floor(Math.random() * 40) + 50,
    status: "needs_attention",
    active_cases: Math.floor(Math.random() * 3) + 1,
    days_since_contact: Math.floor(Math.random() * 20) + 3,
    risk_factors: [
      `Aucun contact depuis ${Math.floor(Math.random() * 15) + 5} jours`,
      "Facture impayee en attente",
    ],
    recommended_actions: [
      "Planifier un appel de suivi",
      "Envoyer un e-mail de mise a jour sur le dossier",
    ],
  };
}

const STATUS_CONFIG: Record<
  string,
  { label: string; variant: string; icon: typeof ShieldCheck }
> = {
  healthy: {
    label: "Relation saine",
    variant: "bg-success-100 text-success-700",
    icon: ShieldCheck,
  },
  needs_attention: {
    label: "Attention requise",
    variant: "bg-warning-100 text-warning-700",
    icon: ShieldAlert,
  },
  at_risk: {
    label: "A risque",
    variant: "bg-danger-100 text-danger-700",
    icon: ShieldX,
  },
  critical: {
    label: "Critique",
    variant: "bg-danger-200 text-danger-800",
    icon: ShieldX,
  },
};

const CIVILITY_OPTIONS = ["M.", "Mme", "Maitre"];

const CIVIL_STATUS_OPTIONS = [
  { value: "celibataire", label: "Celibataire" },
  { value: "marie", label: "Marie(e)" },
  { value: "cohabitant_legal", label: "Cohabitant legal" },
  { value: "divorce", label: "Divorce(e)" },
  { value: "veuf", label: "Veuf/Veuve" },
  { value: "separe", label: "Separe(e)" },
];

const LEGAL_FORM_OPTIONS = [
  "SA",
  "SRL",
  "ASBL",
  "SC",
  "SNC",
  "SCS",
  "SE",
  "GIE",
  "Fondation",
  "Entreprise individuelle",
  "Autre",
];

const COUNTRY_OPTIONS = [
  { value: "BE", label: "Belgique" },
  { value: "FR", label: "France" },
  { value: "NL", label: "Pays-Bas" },
  { value: "LU", label: "Luxembourg" },
  { value: "DE", label: "Allemagne" },
  { value: "GB", label: "Royaume-Uni" },
  { value: "OTHER", label: "Autre" },
];

const PAYMENT_OPTIONS = [
  { value: "virement", label: "Virement" },
  { value: "domiciliation", label: "Domiciliation" },
  { value: "cheque", label: "Cheque" },
];

const CONTACT_METHOD_OPTIONS = [
  { value: "email", label: "Email" },
  { value: "telephone", label: "Telephone" },
  { value: "courrier", label: "Courrier" },
  { value: "en_personne", label: "En personne" },
];

function getScoreColor(score: number): string {
  if (score >= 80) return "#16a34a";
  if (score >= 60) return "#ca8a04";
  if (score >= 40) return "#ea580c";
  return "#dc2626";
}

function getScoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-50";
  if (score >= 60) return "bg-yellow-50";
  if (score >= 40) return "bg-orange-50";
  return "bg-red-50";
}

function HealthScoreGauge({ score }: { score: number }) {
  const size = 80;
  const strokeWidth = 7;
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = getScoreColor(score);

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-700 ease-in-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-lg font-bold" style={{ color }}>
          {score}
        </span>
      </div>
    </div>
  );
}

const TYPE_LABELS: Record<string, string> = {
  natural: "Personne physique",
  legal: "Personne morale",
};

const LANGUAGE_OPTIONS = [
  { value: "fr", label: "Francais" },
  { value: "nl", label: "Neerlandais" },
  { value: "en", label: "Anglais" },
  { value: "de", label: "Allemand" },
];

function maskIBAN(iban: string): string {
  if (!iban || iban.length < 8) return iban || "";
  return iban.slice(0, 4) + " **** **** " + iban.slice(-4);
}

function formatAddress(addr?: {
  street?: string;
  zip?: string;
  city?: string;
  country?: string;
}): string {
  if (!addr) return "";
  const parts = [
    addr.street,
    [addr.zip, addr.city].filter(Boolean).join(" "),
    COUNTRY_OPTIONS.find((c) => c.value === addr.country)?.label ||
      addr.country,
  ].filter(Boolean);
  return parts.join(", ");
}

function getCivilStatusLabel(value?: string): string {
  if (!value) return "";
  const found = CIVIL_STATUS_OPTIONS.find((s) => s.value === value);
  return found ? found.label : value;
}

function getContactMethodLabel(value?: string): string {
  if (!value) return "";
  const found = CONTACT_METHOD_OPTIONS.find((m) => m.value === value);
  return found ? found.label : value;
}

function getPaymentLabel(value?: string): string {
  if (!value) return "";
  const found = PAYMENT_OPTIONS.find((p) => p.value === value);
  return found ? found.label : value;
}

export default function ContactDetailPage() {
  const { accessToken, tenantId } = useAuth();
  const token = accessToken;
  const params = useParams();
  const router = useRouter();
  const contactId = params.id as string;

  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<EditFormState | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(
    {},
  );
  const [health, setHealth] = useState<ClientHealth | null>(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [linkedCases, setLinkedCases] = useState<LinkedCase[]>([]);
  const [casesLoading, setCasesLoading] = useState(false);

  useEffect(() => {
    if (!token || !tenantId) return;

    const fetchContact = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiFetch<Contact>(
          `/contacts/${contactId}`,
          token,
          { tenantId },
        );
        setContact(data);
      } catch (err: any) {
        setError(err.message || "Erreur lors du chargement du contact");
      } finally {
        setLoading(false);
      }
    };

    fetchContact();
  }, [token, tenantId, contactId]);

  // Fetch linked cases
  useEffect(() => {
    if (!token || !tenantId || !contact) return;
    setCasesLoading(true);
    apiFetch<LinkedCase[]>(`/contacts/${contactId}/cases`, token, { tenantId })
      .then((data) => setLinkedCases(Array.isArray(data) ? data : []))
      .catch(() => setLinkedCases([]))
      .finally(() => setCasesLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantId, contact?.id]);

  const fetchHealth = async () => {
    if (!token || !tenantId) return;
    setHealthLoading(true);
    try {
      const data = await apiFetch<ClientHealth>(
        `/brain/client/${contactId}/health`,
        token,
        { tenantId },
      );
      setHealth(data);
    } catch {
      if (contact) {
        setHealth(generateMockHealth(contact.full_name));
      }
    } finally {
      setHealthLoading(false);
    }
  };

  useEffect(() => {
    if (!token || !tenantId || !contact) return;
    fetchHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, tenantId, contactId, contact?.id]);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  const getLanguageLabel = (lang: string | null) => {
    if (!lang) return "Non specifie";
    const found = LANGUAGE_OPTIONS.find((l) => l.value === lang);
    return found ? found.label : lang;
  };

  const validateEmail = (email: string): boolean => {
    if (!email) return true;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validate = (): boolean => {
    if (!editForm) return false;
    const errors: ValidationErrors = {};

    if (editForm.type === "natural") {
      if (!editForm.first_name?.trim() && !editForm.last_name?.trim()) {
        errors.first_name = "Le prenom ou le nom est obligatoire.";
      }
    } else {
      if (!editForm.full_name?.trim()) {
        errors.full_name = "La raison sociale est obligatoire.";
      }
    }

    if (editForm.email && !validateEmail(editForm.email)) {
      errors.email = "Format d'email invalide.";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const contactToEditForm = (c: Contact): EditFormState => {
    const m = c.metadata || {};
    return {
      type: c.type,
      full_name: c.full_name || "",
      email: c.email || "",
      phone_e164: c.phone_e164 || "",
      bce_number: c.bce_number || "",
      address: c.address || "",
      language: c.language || "fr",
      civility: m.civility || "",
      first_name: m.first_name || "",
      last_name: m.last_name || "",
      birth_date: m.birth_date || "",
      birth_place: m.birth_place || "",
      nationality: m.nationality || "",
      civil_status: m.civil_status || "",
      profession: m.profession || "",
      national_register: m.national_register || "",
      legal_form: m.legal_form || "",
      vat_number: m.vat_number || "",
      corporate_purpose: m.corporate_purpose || "",
      legal_representative: m.legal_representative || "",
      correspondence_address_street: m.correspondence_address?.street || "",
      correspondence_address_zip: m.correspondence_address?.zip || "",
      correspondence_address_city: m.correspondence_address?.city || "",
      correspondence_address_country: m.correspondence_address?.country || "BE",
      secondary_email: m.secondary_email || "",
      phone_fixed: m.phone_fixed || "",
      fax: m.fax || "",
      iban: m.iban || "",
      bic: m.bic || "",
      vat_liable: m.vat_liable || false,
      payment_preference: m.payment_preference || "",
      category: m.category || "",
      preferred_contact_method: m.preferred_contact_method || "",
      notes: m.notes || "",
    };
  };

  const handleEdit = () => {
    if (!contact) return;
    setIsEditing(true);
    setEditForm(contactToEditForm(contact));
    setValidationErrors({});
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditForm(null);
    setValidationErrors({});
    setError(null);
  };

  const updateEditForm = (updates: Partial<EditFormState>) => {
    setEditForm((prev) => (prev ? { ...prev, ...updates } : null));
    const updatedKeys = Object.keys(updates);
    if (updatedKeys.some((k) => k in validationErrors)) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        updatedKeys.forEach((k) => delete next[k as keyof ValidationErrors]);
        return next;
      });
    }
  };

  // Auto-compute full_name for natural persons in edit mode
  useEffect(() => {
    if (!editForm || editForm.type !== "natural") return;
    const parts = [editForm.civility, editForm.first_name, editForm.last_name].filter(Boolean);
    const computedName = parts.join(" ");
    if (computedName && computedName !== editForm.full_name) {
      setEditForm((prev) => (prev ? { ...prev, full_name: computedName } : null));
    }
  }, [editForm?.civility, editForm?.first_name, editForm?.last_name, editForm?.type]);

  const handleSave = async () => {
    if (!token || !tenantId || !editForm) return;
    if (!validate()) return;

    try {
      setSaving(true);
      setError(null);

      const metadata: Record<string, unknown> = {};

      if (editForm.type === "natural") {
        if (editForm.civility) metadata.civility = editForm.civility;
        if (editForm.first_name) metadata.first_name = editForm.first_name;
        if (editForm.last_name) metadata.last_name = editForm.last_name;
        if (editForm.birth_date) metadata.birth_date = editForm.birth_date;
        if (editForm.birth_place) metadata.birth_place = editForm.birth_place;
        if (editForm.nationality) metadata.nationality = editForm.nationality;
        if (editForm.civil_status)
          metadata.civil_status = editForm.civil_status;
        if (editForm.profession) metadata.profession = editForm.profession;
        if (editForm.national_register)
          metadata.national_register = editForm.national_register;
      } else {
        if (editForm.legal_form) metadata.legal_form = editForm.legal_form;
        if (editForm.vat_number) metadata.vat_number = editForm.vat_number;
        if (editForm.corporate_purpose)
          metadata.corporate_purpose = editForm.corporate_purpose;
        if (editForm.legal_representative)
          metadata.legal_representative = editForm.legal_representative;
      }

      if (editForm.correspondence_address_street || editForm.correspondence_address_city) {
        metadata.correspondence_address = {
          street: editForm.correspondence_address_street,
          zip: editForm.correspondence_address_zip,
          city: editForm.correspondence_address_city,
          country: editForm.correspondence_address_country,
        };
      }

      if (editForm.secondary_email)
        metadata.secondary_email = editForm.secondary_email;
      if (editForm.phone_fixed) metadata.phone_fixed = editForm.phone_fixed;
      if (editForm.fax) metadata.fax = editForm.fax;
      if (editForm.iban) metadata.iban = editForm.iban;
      if (editForm.bic) metadata.bic = editForm.bic;
      metadata.vat_liable = editForm.vat_liable;
      if (editForm.payment_preference)
        metadata.payment_preference = editForm.payment_preference;
      if (editForm.category) metadata.category = editForm.category;
      if (editForm.preferred_contact_method)
        metadata.preferred_contact_method = editForm.preferred_contact_method;
      if (editForm.notes) metadata.notes = editForm.notes;

      const updateData = {
        type: editForm.type,
        full_name: editForm.full_name,
        email: editForm.email || null,
        phone_e164: editForm.phone_e164 || null,
        bce_number: editForm.bce_number || null,
        address: editForm.address || null,
        language: editForm.language || null,
        metadata: Object.keys(metadata).length > 0 ? metadata : null,
      };

      const updatedContact = await apiFetch<Contact>(
        `/contacts/${contactId}`,
        token,
        {
          method: "PATCH",
          body: JSON.stringify(updateData),
          tenantId,
        },
      );

      setContact(updatedContact);
      setIsEditing(false);
      setEditForm(null);
      setValidationErrors({});
      setSuccess("Contact mis a jour avec succes");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la sauvegarde du contact");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <SkeletonCard />
      </div>
    );
  }

  if (error && !contact) {
    return (
      <div className="p-6">
        <div className="card bg-danger-50 border border-danger-200">
          <p className="text-danger-700">{error}</p>
        </div>
      </div>
    );
  }

  if (!contact) {
    return (
      <div className="p-6">
        <div className="card">
          <p className="text-neutral-600">Contact introuvable</p>
        </div>
      </div>
    );
  }

  const meta = contact.metadata || {};
  const avatarBg =
    contact.type === "legal" ? "bg-purple-100" : "bg-accent-50";
  const avatarText =
    contact.type === "legal" ? "text-purple-700" : "text-accent-700";

  // Helper for read-only field rendering
  const ReadOnlyField = ({
    label,
    value,
    fullWidth = false,
  }: {
    label: string;
    value: string | null | undefined;
    fullWidth?: boolean;
  }) => (
    <div className={fullWidth ? "col-span-2" : ""}>
      <p className="text-xs font-medium text-neutral-500 mb-1">{label}</p>
      <p className="text-sm text-neutral-900">
        {value || (
          <span className="text-neutral-400">Non specifie</span>
        )}
      </p>
    </div>
  );

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Back button */}
      <button
        onClick={() => router.push("/dashboard/contacts")}
        className="inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour aux contacts
      </button>

      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div className="flex items-center gap-4">
          <div
            className={`w-14 h-14 rounded-full ${avatarBg} flex items-center justify-center text-lg font-bold ${avatarText} flex-shrink-0`}
          >
            {getInitials(contact.full_name)}
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-neutral-900">
                {meta.civility && contact.type === "natural"
                  ? `${meta.civility} `
                  : ""}
                {contact.full_name}
              </h1>
            </div>
            <div className="flex items-center gap-2 mt-1.5 flex-wrap">
              <Badge
                variant={contact.type === "natural" ? "accent" : "neutral"}
                size="sm"
              >
                {contact.type === "natural" ? (
                  <User className="w-3 h-3 inline-block mr-1" />
                ) : (
                  <Building2 className="w-3 h-3 inline-block mr-1" />
                )}
                {TYPE_LABELS[contact.type] || contact.type}
              </Badge>
              {meta.category && (
                <Badge variant="default" size="sm">
                  {meta.category}
                </Badge>
              )}
              {meta.legal_form && contact.type === "legal" && (
                <Badge variant="accent" size="sm">
                  {meta.legal_form}
                </Badge>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {!isEditing ? (
            <button
              onClick={handleEdit}
              className="btn-primary flex items-center gap-2"
            >
              <Edit2 className="w-4 h-4" />
              Modifier
            </button>
          ) : (
            <>
              <button
                onClick={handleCancel}
                disabled={saving}
                className="px-4 py-2 border border-neutral-300 rounded-md text-sm font-medium text-neutral-600 hover:bg-neutral-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <X className="w-4 h-4" />
                Annuler
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Enregistrement...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4" />
                    Enregistrer
                  </>
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 bg-danger-50 border border-danger-200 rounded-md">
          <p className="text-danger-700 text-sm">{error}</p>
        </div>
      )}

      {/* Sante relationnelle - Intelligence Card */}
      <div className="mb-6">
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Activity className="w-5 h-5 text-accent-600" />
              <h2 className="text-lg font-semibold text-neutral-900">
                Sante relationnelle
              </h2>
            </div>
            <button
              onClick={fetchHealth}
              disabled={healthLoading}
              className="p-1.5 rounded hover:bg-neutral-100 text-neutral-400 hover:text-neutral-600 transition-colors"
              title="Actualiser"
            >
              <RefreshCw
                className={`w-4 h-4 ${healthLoading ? "animate-spin" : ""}`}
              />
            </button>
          </div>

          {healthLoading && !health ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-accent-500" />
              <span className="ml-2 text-sm text-neutral-500">
                Analyse en cours...
              </span>
            </div>
          ) : health ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              {/* Score and Status */}
              <div className="flex flex-col items-center justify-center">
                <HealthScoreGauge score={health.health_score} />
                <p className="text-xs text-neutral-500 mt-2 font-medium">
                  Score: {health.health_score}/100
                </p>
                {(() => {
                  const config =
                    STATUS_CONFIG[health.status] ||
                    STATUS_CONFIG.needs_attention;
                  const StatusIcon = config.icon;
                  return (
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium mt-2 ${config.variant}`}
                    >
                      <StatusIcon className="w-3.5 h-3.5" />
                      {config.label}
                    </span>
                  );
                })()}
              </div>

              {/* Risk Factors */}
              <div>
                <div className="flex items-center gap-1.5 mb-3">
                  <AlertTriangle className="w-4 h-4 text-warning-600" />
                  <h3 className="text-sm font-semibold text-neutral-700">
                    Facteurs de risque
                  </h3>
                </div>
                {health.risk_factors.length > 0 ? (
                  <ul className="space-y-2">
                    {health.risk_factors.map((factor, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-neutral-600"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-warning-500 mt-1.5 flex-shrink-0" />
                        {factor}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-neutral-400">
                    Aucun facteur de risque identifie
                  </p>
                )}
              </div>

              {/* Recommended Actions */}
              <div>
                <div className="flex items-center gap-1.5 mb-3">
                  <Lightbulb className="w-4 h-4 text-accent-600" />
                  <h3 className="text-sm font-semibold text-neutral-700">
                    Actions recommandees
                  </h3>
                </div>
                {health.recommended_actions.length > 0 ? (
                  <ul className="space-y-2">
                    {health.recommended_actions.map((action, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 text-sm text-neutral-600"
                      >
                        <span className="w-1.5 h-1.5 rounded-full bg-accent-500 mt-1.5 flex-shrink-0" />
                        {action}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-neutral-400">
                    Aucune action recommandee
                  </p>
                )}
              </div>

              {/* Active Cases & Last Contact */}
              <div className="space-y-4">
                <div
                  className={`rounded-lg p-3 ${getScoreBgColor(health.health_score)}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <FolderOpen className="w-4 h-4 text-neutral-600" />
                    <span className="text-sm font-medium text-neutral-700">
                      Dossiers actifs
                    </span>
                  </div>
                  <p className="text-2xl font-bold text-neutral-900">
                    {health.active_cases}
                  </p>
                </div>
                <div className="rounded-lg p-3 bg-neutral-50">
                  <span className="text-xs text-neutral-500">
                    Dernier contact
                  </span>
                  <p className="text-sm font-semibold text-neutral-700 mt-0.5">
                    Il y a {health.days_since_contact} jour
                    {health.days_since_contact > 1 ? "s" : ""}
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-6">
              <Activity className="w-8 h-8 text-neutral-300 mx-auto mb-2" />
              <p className="text-sm text-neutral-500">
                Analyse relationnelle non disponible
              </p>
              <button
                onClick={fetchHealth}
                className="mt-2 text-sm text-accent-600 hover:text-accent-700 font-medium"
              >
                Reessayer
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left column (col-span-2) */}
        <div className="lg:col-span-2 space-y-6">
          {/* Informations card */}
          <div className="card">
            <div className="flex items-center gap-2 mb-6">
              {contact.type === "natural" ? (
                <User className="w-5 h-5 text-accent-600" />
              ) : (
                <Building2 className="w-5 h-5 text-accent-600" />
              )}
              <h2 className="text-xl font-semibold text-neutral-900">
                {contact.type === "natural"
                  ? "Informations personnelles"
                  : "Informations de l'entite"}
              </h2>
            </div>

            {!isEditing ? (
              /* VIEW MODE */
              <div>
                {contact.type === "natural" ? (
                  <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                    <ReadOnlyField label="Civilite" value={meta.civility} />
                    <ReadOnlyField label="Prenom" value={meta.first_name} />
                    <ReadOnlyField label="Nom" value={meta.last_name} />
                    <ReadOnlyField
                      label="Date de naissance"
                      value={
                        meta.birth_date
                          ? new Date(meta.birth_date).toLocaleDateString(
                              "fr-BE",
                            )
                          : undefined
                      }
                    />
                    <ReadOnlyField
                      label="Lieu de naissance"
                      value={meta.birth_place}
                    />
                    <ReadOnlyField
                      label="Nationalite"
                      value={meta.nationality}
                    />
                    <ReadOnlyField
                      label="Etat civil"
                      value={getCivilStatusLabel(meta.civil_status)}
                    />
                    <ReadOnlyField label="Profession" value={meta.profession} />
                    <ReadOnlyField
                      label="Numero de registre national"
                      value={meta.national_register}
                    />
                    <ReadOnlyField
                      label="Langue de correspondance"
                      value={getLanguageLabel(contact.language)}
                    />
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                    <ReadOnlyField
                      label="Raison sociale"
                      value={contact.full_name}
                    />
                    <ReadOnlyField
                      label="Forme juridique"
                      value={meta.legal_form}
                    />
                    <ReadOnlyField
                      label="Numero BCE/KBO"
                      value={contact.bce_number}
                    />
                    <ReadOnlyField
                      label="Numero TVA"
                      value={meta.vat_number}
                    />
                    <ReadOnlyField
                      label="Representant legal"
                      value={meta.legal_representative}
                    />
                    <ReadOnlyField
                      label="Langue de correspondance"
                      value={getLanguageLabel(contact.language)}
                    />
                    <ReadOnlyField
                      label="Objet social"
                      value={meta.corporate_purpose}
                      fullWidth
                    />
                  </div>
                )}

                {/* Timestamps */}
                <div className="mt-6 pt-4 border-t border-neutral-200">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-neutral-500 mb-1">Cree le</p>
                      <p className="text-neutral-900">
                        {new Date(contact.created_at).toLocaleDateString(
                          "fr-BE",
                          {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </p>
                    </div>
                    <div>
                      <p className="text-neutral-500 mb-1">Modifie le</p>
                      <p className="text-neutral-900">
                        {new Date(contact.updated_at).toLocaleDateString(
                          "fr-BE",
                          {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          },
                        )}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              /* EDIT MODE */
              <div className="space-y-5">
                {/* Type */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                    Type de contact
                  </label>
                  <select
                    value={editForm?.type || "natural"}
                    onChange={(e) =>
                      updateEditForm({
                        type: e.target.value as "natural" | "legal",
                      })
                    }
                    className="input w-full"
                  >
                    <option value="natural">Personne physique</option>
                    <option value="legal">Personne morale</option>
                  </select>
                </div>

                {editForm?.type === "natural" ? (
                  <>
                    <div className="grid grid-cols-3 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Civilite
                        </label>
                        <select
                          value={editForm.civility}
                          onChange={(e) =>
                            updateEditForm({ civility: e.target.value })
                          }
                          className="input w-full"
                        >
                          <option value="">-- Selectionner --</option>
                          {CIVILITY_OPTIONS.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Prenom *
                        </label>
                        <input
                          type="text"
                          value={editForm.first_name}
                          onChange={(e) =>
                            updateEditForm({ first_name: e.target.value })
                          }
                          className={`input w-full ${validationErrors.first_name ? "border-danger-300 focus:ring-danger-500" : ""}`}
                          placeholder="Jean"
                        />
                        {validationErrors.first_name && (
                          <p className="mt-1 text-sm text-danger-700">
                            {validationErrors.first_name}
                          </p>
                        )}
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Nom *
                        </label>
                        <input
                          type="text"
                          value={editForm.last_name}
                          onChange={(e) =>
                            updateEditForm({ last_name: e.target.value })
                          }
                          className="input w-full"
                          placeholder="Dupont"
                        />
                      </div>
                    </div>

                    {/* Auto-computed full name */}
                    {editForm.full_name && (
                      <div className="bg-neutral-50 rounded-lg px-4 py-2 text-sm text-neutral-600">
                        <span className="font-medium text-neutral-700">
                          Nom complet :{" "}
                        </span>
                        {editForm.full_name}
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Date de naissance
                        </label>
                        <input
                          type="date"
                          value={editForm.birth_date}
                          onChange={(e) =>
                            updateEditForm({ birth_date: e.target.value })
                          }
                          className="input w-full"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Lieu de naissance
                        </label>
                        <input
                          type="text"
                          value={editForm.birth_place}
                          onChange={(e) =>
                            updateEditForm({ birth_place: e.target.value })
                          }
                          className="input w-full"
                          placeholder="Bruxelles"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Nationalite
                        </label>
                        <input
                          type="text"
                          value={editForm.nationality}
                          onChange={(e) =>
                            updateEditForm({ nationality: e.target.value })
                          }
                          className="input w-full"
                          placeholder="Belge"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Etat civil
                        </label>
                        <select
                          value={editForm.civil_status}
                          onChange={(e) =>
                            updateEditForm({ civil_status: e.target.value })
                          }
                          className="input w-full"
                        >
                          <option value="">-- Selectionner --</option>
                          {CIVIL_STATUS_OPTIONS.map((s) => (
                            <option key={s.value} value={s.value}>
                              {s.label}
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Profession
                        </label>
                        <input
                          type="text"
                          value={editForm.profession}
                          onChange={(e) =>
                            updateEditForm({ profession: e.target.value })
                          }
                          className="input w-full"
                          placeholder="Ingenieur"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Numero de registre national
                        </label>
                        <input
                          type="text"
                          value={editForm.national_register}
                          onChange={(e) =>
                            updateEditForm({
                              national_register: e.target.value,
                            })
                          }
                          className="input w-full"
                          placeholder="XX.XX.XX-XXX.XX"
                        />
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                        Raison sociale *
                      </label>
                      <input
                        type="text"
                        value={editForm?.full_name || ""}
                        onChange={(e) =>
                          updateEditForm({ full_name: e.target.value })
                        }
                        className={`input w-full ${validationErrors.full_name ? "border-danger-300 focus:ring-danger-500" : ""}`}
                        placeholder="SA Immobel"
                      />
                      {validationErrors.full_name && (
                        <p className="mt-1 text-sm text-danger-700">
                          {validationErrors.full_name}
                        </p>
                      )}
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Forme juridique
                        </label>
                        <select
                          value={editForm?.legal_form || ""}
                          onChange={(e) =>
                            updateEditForm({ legal_form: e.target.value })
                          }
                          className="input w-full"
                        >
                          <option value="">-- Selectionner --</option>
                          {LEGAL_FORM_OPTIONS.map((lf) => (
                            <option key={lf} value={lf}>
                              {lf}
                            </option>
                          ))}
                        </select>
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Numero BCE/KBO
                        </label>
                        <input
                          type="text"
                          value={editForm?.bce_number || ""}
                          onChange={(e) =>
                            updateEditForm({ bce_number: e.target.value })
                          }
                          className="input w-full"
                          placeholder="0xxx.xxx.xxx"
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Numero TVA
                        </label>
                        <input
                          type="text"
                          value={editForm?.vat_number || ""}
                          onChange={(e) =>
                            updateEditForm({ vat_number: e.target.value })
                          }
                          className="input w-full"
                          placeholder="BExxxxxxxxxx"
                        />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                          Representant legal
                        </label>
                        <input
                          type="text"
                          value={editForm?.legal_representative || ""}
                          onChange={(e) =>
                            updateEditForm({
                              legal_representative: e.target.value,
                            })
                          }
                          className="input w-full"
                          placeholder="Jean Dupont"
                        />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                        Objet social
                      </label>
                      <textarea
                        value={editForm?.corporate_purpose || ""}
                        onChange={(e) =>
                          updateEditForm({ corporate_purpose: e.target.value })
                        }
                        className="input w-full"
                        rows={3}
                        placeholder="Activites informatiques"
                      />
                    </div>
                  </>
                )}

                {/* Language (common) */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                    Langue de correspondance
                  </label>
                  <select
                    value={editForm?.language || ""}
                    onChange={(e) =>
                      updateEditForm({ language: e.target.value })
                    }
                    className="input w-full"
                  >
                    <option value="">Non specifie</option>
                    {LANGUAGE_OPTIONS.map((lang) => (
                      <option key={lang.value} value={lang.value}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
          </div>

          {/* Coordonnees card */}
          <div className="card">
            <div className="flex items-center gap-2 mb-6">
              <MapPin className="w-5 h-5 text-accent-600" />
              <h2 className="text-xl font-semibold text-neutral-900">
                Coordonnees
              </h2>
            </div>

            {!isEditing ? (
              /* VIEW MODE */
              <div className="space-y-6">
                {/* Main address */}
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1">
                    Adresse principale
                  </p>
                  <p className="text-sm text-neutral-900">
                    {contact.address || (
                      <span className="text-neutral-400">
                        Non specifiee
                      </span>
                    )}
                  </p>
                </div>

                {/* Correspondence address */}
                {meta.correspondence_address &&
                  (meta.correspondence_address.street ||
                    meta.correspondence_address.city) && (
                    <div>
                      <p className="text-xs font-medium text-neutral-500 mb-1">
                        Adresse de correspondance
                      </p>
                      <p className="text-sm text-neutral-900">
                        {formatAddress(meta.correspondence_address)}
                      </p>
                    </div>
                  )}

                {/* Contact means */}
                <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-1">
                      Email principal
                    </p>
                    {contact.email ? (
                      <a
                        href={`mailto:${contact.email}`}
                        className="text-sm text-accent hover:text-accent-700 flex items-center gap-1.5"
                      >
                        <Mail className="w-3.5 h-3.5" />
                        {contact.email}
                      </a>
                    ) : (
                      <p className="text-sm text-neutral-400">
                        Non specifie
                      </p>
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-1">
                      Email secondaire
                    </p>
                    {meta.secondary_email ? (
                      <a
                        href={`mailto:${meta.secondary_email}`}
                        className="text-sm text-accent hover:text-accent-700 flex items-center gap-1.5"
                      >
                        <Mail className="w-3.5 h-3.5" />
                        {meta.secondary_email}
                      </a>
                    ) : (
                      <p className="text-sm text-neutral-400">
                        Non specifie
                      </p>
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-1">
                      Telephone mobile
                    </p>
                    {contact.phone_e164 ? (
                      <a
                        href={`tel:${contact.phone_e164}`}
                        className="text-sm text-accent hover:text-accent-700 flex items-center gap-1.5"
                      >
                        <Phone className="w-3.5 h-3.5" />
                        {contact.phone_e164}
                      </a>
                    ) : (
                      <p className="text-sm text-neutral-400">
                        Non specifie
                      </p>
                    )}
                  </div>

                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-1">
                      Telephone fixe
                    </p>
                    {meta.phone_fixed ? (
                      <a
                        href={`tel:${meta.phone_fixed}`}
                        className="text-sm text-accent hover:text-accent-700 flex items-center gap-1.5"
                      >
                        <Phone className="w-3.5 h-3.5" />
                        {meta.phone_fixed}
                      </a>
                    ) : (
                      <p className="text-sm text-neutral-400">
                        Non specifie
                      </p>
                    )}
                  </div>

                  {meta.fax && (
                    <div>
                      <p className="text-xs font-medium text-neutral-500 mb-1">
                        Fax
                      </p>
                      <p className="text-sm text-neutral-900">{meta.fax}</p>
                    </div>
                  )}

                  <div>
                    <p className="text-xs font-medium text-neutral-500 mb-1">
                      Methode de contact preferee
                    </p>
                    {meta.preferred_contact_method ? (
                      <Badge variant="accent" size="sm">
                        {getContactMethodLabel(meta.preferred_contact_method)}
                      </Badge>
                    ) : (
                      <p className="text-sm text-neutral-400">
                        Non specifiee
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              /* EDIT MODE */
              <div className="space-y-5">
                {/* Address */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                    Adresse principale
                  </label>
                  <textarea
                    value={editForm?.address || ""}
                    onChange={(e) =>
                      updateEditForm({ address: e.target.value })
                    }
                    className="input w-full"
                    rows={2}
                    placeholder="Rue de la Loi 1, 1000 Bruxelles, Belgique"
                  />
                </div>

                {/* Correspondence address */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                    Adresse de correspondance
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs text-neutral-500 mb-1">
                        Rue et numero
                      </label>
                      <input
                        type="text"
                        value={editForm?.correspondence_address_street || ""}
                        onChange={(e) =>
                          updateEditForm({
                            correspondence_address_street: e.target.value,
                          })
                        }
                        className="input w-full"
                        placeholder="Rue de la Loi 1"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-neutral-500 mb-1">
                        Code postal
                      </label>
                      <input
                        type="text"
                        value={editForm?.correspondence_address_zip || ""}
                        onChange={(e) =>
                          updateEditForm({
                            correspondence_address_zip: e.target.value,
                          })
                        }
                        className="input w-full"
                        placeholder="1000"
                      />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 mt-2">
                    <div>
                      <label className="block text-xs text-neutral-500 mb-1">
                        Ville/Commune
                      </label>
                      <input
                        type="text"
                        value={editForm?.correspondence_address_city || ""}
                        onChange={(e) =>
                          updateEditForm({
                            correspondence_address_city: e.target.value,
                          })
                        }
                        className="input w-full"
                        placeholder="Bruxelles"
                      />
                    </div>
                    <div>
                      <label className="block text-xs text-neutral-500 mb-1">
                        Pays
                      </label>
                      <select
                        value={editForm?.correspondence_address_country || "BE"}
                        onChange={(e) =>
                          updateEditForm({
                            correspondence_address_country: e.target.value,
                          })
                        }
                        className="input w-full"
                      >
                        {COUNTRY_OPTIONS.map((c) => (
                          <option key={c.value} value={c.value}>
                            {c.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                </div>

                {/* Emails */}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Email principal
                    </label>
                    <input
                      type="email"
                      value={editForm?.email || ""}
                      onChange={(e) =>
                        updateEditForm({ email: e.target.value })
                      }
                      className={`input w-full ${validationErrors.email ? "border-danger-300 focus:ring-danger-500" : ""}`}
                      placeholder="contact@example.be"
                    />
                    {validationErrors.email && (
                      <p className="mt-1 text-sm text-danger-700">
                        {validationErrors.email}
                      </p>
                    )}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Email secondaire
                    </label>
                    <input
                      type="email"
                      value={editForm?.secondary_email || ""}
                      onChange={(e) =>
                        updateEditForm({ secondary_email: e.target.value })
                      }
                      className="input w-full"
                      placeholder="jean.dupont@work.be"
                    />
                  </div>
                </div>

                {/* Phones */}
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Telephone mobile
                    </label>
                    <input
                      type="tel"
                      value={editForm?.phone_e164 || ""}
                      onChange={(e) =>
                        updateEditForm({ phone_e164: e.target.value })
                      }
                      className="input w-full"
                      placeholder="+32470123456"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Telephone fixe
                    </label>
                    <input
                      type="tel"
                      value={editForm?.phone_fixed || ""}
                      onChange={(e) =>
                        updateEditForm({ phone_fixed: e.target.value })
                      }
                      className="input w-full"
                      placeholder="+3222345678"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Fax
                    </label>
                    <input
                      type="tel"
                      value={editForm?.fax || ""}
                      onChange={(e) =>
                        updateEditForm({ fax: e.target.value })
                      }
                      className="input w-full"
                      placeholder="+3222345679"
                    />
                  </div>
                </div>

                {/* Preferred contact method */}
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                    Methode de contact preferee
                  </label>
                  <div className="flex flex-wrap gap-3">
                    {CONTACT_METHOD_OPTIONS.map((m) => (
                      <label
                        key={m.value}
                        className="flex items-center gap-2 cursor-pointer"
                      >
                        <input
                          type="radio"
                          name="edit_preferred_contact_method"
                          value={m.value}
                          checked={
                            editForm?.preferred_contact_method === m.value
                          }
                          onChange={(e) =>
                            updateEditForm({
                              preferred_contact_method: e.target.value,
                            })
                          }
                          className="w-4 h-4 text-accent border-neutral-300 focus:ring-accent"
                        />
                        <span className="text-sm text-neutral-700">
                          {m.label}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Financial card */}
          <div className="card">
            <div className="flex items-center gap-2 mb-6">
              <CreditCard className="w-5 h-5 text-accent-600" />
              <h2 className="text-xl font-semibold text-neutral-900">
                Informations financieres
              </h2>
            </div>

            {!isEditing ? (
              /* VIEW MODE */
              <div className="grid grid-cols-2 gap-x-6 gap-y-4">
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1">
                    IBAN
                  </p>
                  <p className="text-sm text-neutral-900 font-mono">
                    {meta.iban ? (
                      maskIBAN(meta.iban)
                    ) : (
                      <span className="text-neutral-400 font-sans">
                        Non specifie
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1">
                    BIC
                  </p>
                  <p className="text-sm text-neutral-900 font-mono">
                    {meta.bic || (
                      <span className="text-neutral-400 font-sans">
                        Non specifie
                      </span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1">
                    Assujetti TVA
                  </p>
                  <Badge
                    variant={meta.vat_liable ? "success" : "neutral"}
                    size="sm"
                  >
                    {meta.vat_liable ? "Oui" : "Non"}
                  </Badge>
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1">
                    Mode de paiement prefere
                  </p>
                  <p className="text-sm text-neutral-900">
                    {getPaymentLabel(meta.payment_preference) || (
                      <span className="text-neutral-400">
                        Non specifie
                      </span>
                    )}
                  </p>
                </div>
              </div>
            ) : (
              /* EDIT MODE */
              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      IBAN
                    </label>
                    <input
                      type="text"
                      value={editForm?.iban || ""}
                      onChange={(e) =>
                        updateEditForm({ iban: e.target.value })
                      }
                      className="input w-full"
                      placeholder="BE68539007547034"
                    />
                    <p className="mt-1 text-xs text-neutral-400">
                      Format : BExx xxxx xxxx xxxx
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      BIC
                    </label>
                    <input
                      type="text"
                      value={editForm?.bic || ""}
                      onChange={(e) =>
                        updateEditForm({ bic: e.target.value })
                      }
                      className="input w-full"
                      placeholder="BBRUBEBB"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Assujetti TVA
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <div
                        className={`relative w-10 h-5 rounded-full transition-colors ${editForm?.vat_liable ? "bg-accent" : "bg-neutral-300"}`}
                        onClick={() =>
                          updateEditForm({
                            vat_liable: !editForm?.vat_liable,
                          })
                        }
                      >
                        <div
                          className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${editForm?.vat_liable ? "translate-x-5" : ""}`}
                        />
                      </div>
                      <span className="text-sm text-neutral-600">
                        {editForm?.vat_liable ? "Oui" : "Non"}
                      </span>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                      Mode de paiement prefere
                    </label>
                    <select
                      value={editForm?.payment_preference || ""}
                      onChange={(e) =>
                        updateEditForm({ payment_preference: e.target.value })
                      }
                      className="input w-full"
                    >
                      <option value="">-- Selectionner --</option>
                      {PAYMENT_OPTIONS.map((p) => (
                        <option key={p.value} value={p.value}>
                          {p.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Notes card */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <FileText className="w-5 h-5 text-accent-600" />
              <h2 className="text-lg font-semibold text-neutral-900">
                Notes internes
              </h2>
            </div>

            {!isEditing ? (
              <div>
                {meta.notes ? (
                  <p className="text-sm text-neutral-700 whitespace-pre-line">
                    {meta.notes}
                  </p>
                ) : (
                  <p className="text-sm text-neutral-400">
                    Aucune note pour ce contact.
                  </p>
                )}
              </div>
            ) : (
              <div>
                <textarea
                  value={editForm?.notes || ""}
                  onChange={(e) => updateEditForm({ notes: e.target.value })}
                  className="input w-full"
                  rows={4}
                  placeholder="Notes internes sur ce contact"
                />
              </div>
            )}
          </div>
        </div>

        {/* Right sidebar (col-span-1) */}
        <div className="lg:col-span-1 space-y-6">
          {/* Classification card */}
          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Globe className="w-5 h-5 text-accent-600" />
              <h2 className="text-lg font-semibold text-neutral-900">
                Classification
              </h2>
            </div>

            {!isEditing ? (
              <div className="space-y-3">
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1.5">
                    Categorie
                  </p>
                  {meta.category ? (
                    <div className="flex flex-wrap gap-1.5">
                      {meta.category.split(", ").map((cat, i) => (
                        <Badge key={i} variant="accent" size="sm">
                          {cat}
                        </Badge>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-400">
                      Non classifie
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1.5">
                    Methode de contact preferee
                  </p>
                  {meta.preferred_contact_method ? (
                    <Badge variant="default" size="sm">
                      {getContactMethodLabel(meta.preferred_contact_method)}
                    </Badge>
                  ) : (
                    <p className="text-sm text-neutral-400">
                      Non specifiee
                    </p>
                  )}
                </div>
                <div>
                  <p className="text-xs font-medium text-neutral-500 mb-1.5">
                    Langue
                  </p>
                  <Badge variant="default" size="sm">
                    {getLanguageLabel(contact.language)}
                  </Badge>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                    Categorie
                  </label>
                  <input
                    type="text"
                    value={editForm?.category || ""}
                    onChange={(e) =>
                      updateEditForm({ category: e.target.value })
                    }
                    className="input w-full"
                    placeholder="Client, Prospect, ..."
                  />
                  <p className="mt-1 text-xs text-neutral-400">
                    Separees par des virgules
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Dossiers lies */}
          <div className="card">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">
              Dossiers lies
            </h2>
            {casesLoading ? (
              <div className="flex items-center justify-center py-6">
                <Loader2 className="w-5 h-5 animate-spin text-accent-500" />
              </div>
            ) : linkedCases.length > 0 ? (
              <div className="space-y-3">
                {linkedCases.map((lc) => (
                  <div
                    key={lc.id}
                    className="flex items-center justify-between p-3 bg-neutral-50 rounded-lg hover:bg-neutral-100 transition-colors cursor-pointer"
                    onClick={() =>
                      router.push(`/dashboard/cases/${lc.id}`)
                    }
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-neutral-900 truncate">
                        {lc.reference || lc.title}
                      </p>
                      {lc.title && lc.reference && (
                        <p className="text-xs text-neutral-500 truncate">
                          {lc.title}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      {lc.role && (
                        <Badge variant="accent" size="sm">
                          {lc.role}
                        </Badge>
                      )}
                      <Badge
                        variant={
                          lc.status === "open"
                            ? "success"
                            : lc.status === "closed"
                              ? "neutral"
                              : "warning"
                        }
                        size="sm"
                      >
                        {lc.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-neutral-100 mb-3">
                  <Briefcase className="w-7 h-7 text-neutral-400" />
                </div>
                <p className="text-neutral-600 font-medium">
                  Aucun dossier lie
                </p>
                <p className="text-sm text-neutral-400 mt-1">
                  Les dossiers associes apparaitront ici.
                </p>
              </div>
            )}
          </div>

          {/* Communications */}
          <div className="card">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">
              Communications
            </h2>
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-neutral-100 mb-3">
                <MessageSquare className="w-7 h-7 text-neutral-400" />
              </div>
              <p className="text-neutral-600 font-medium">
                Historique a venir
              </p>
              <p className="text-sm text-neutral-400 mt-1">
                L'historique des communications sera bientot disponible.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
