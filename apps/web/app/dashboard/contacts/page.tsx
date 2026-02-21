"use client";

import { useAuth } from "@/lib/useAuth";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Plus,
  Search,
  Mail,
  Phone,
  X,
  Check,
  ChevronRight,
  User,
  Building2,
  MapPin,
  CreditCard,
  Tag,
  Sparkles,
  Loader2,
  AlertTriangle,
  ShieldCheck,
  Info,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import {
  LoadingSkeleton,
  ErrorState,
  EmptyState,
  Badge,
  Modal,
  Button,
  Avatar,
} from "@/components/ui";

interface Contact {
  id: string;
  full_name: string;
  type: string;
  email: string | null;
  phone_e164: string | null;
  bce_number: string | null;
}

interface ContactListResponse {
  items: Contact[];
  total: number;
  page: number;
  per_page: number;
}

interface AddressFields {
  street: string;
  zip: string;
  city: string;
  country: string;
}

interface ContactFormState {
  // Core fields
  type: "natural" | "legal";
  full_name: string;
  email: string;
  phone_e164: string;
  bce_number: string;
  language: string;

  // Natural person metadata
  civility: string;
  first_name: string;
  last_name: string;
  birth_date: string;
  birth_place: string;
  nationality: string;
  civil_status: string;
  profession: string;
  national_register: string;

  // Legal entity metadata
  legal_form: string;
  vat_number: string;
  corporate_purpose: string;
  legal_representative: string;

  // Coordinates
  address: AddressFields;
  correspondence_address_different: boolean;
  correspondence_address: AddressFields;
  secondary_email: string;
  phone_fixed: string;
  fax: string;

  // Financial
  iban: string;
  bic: string;
  vat_liable: boolean;
  payment_preference: string;

  // Classification
  categories: string[];
  preferred_contact_method: string;
  notes: string;
}

interface AIAssistResponse {
  compliance_notes: string[];
  duplicate_warnings: string[];
  suggestions: string[];
}

const INITIAL_FORM: ContactFormState = {
  type: "natural",
  full_name: "",
  email: "",
  phone_e164: "",
  bce_number: "",
  language: "fr",
  civility: "",
  first_name: "",
  last_name: "",
  birth_date: "",
  birth_place: "",
  nationality: "Belge",
  civil_status: "",
  profession: "",
  national_register: "",
  legal_form: "",
  vat_number: "",
  corporate_purpose: "",
  legal_representative: "",
  address: { street: "", zip: "", city: "", country: "BE" },
  correspondence_address_different: false,
  correspondence_address: { street: "", zip: "", city: "", country: "BE" },
  secondary_email: "",
  phone_fixed: "",
  fax: "",
  iban: "",
  bic: "",
  vat_liable: false,
  payment_preference: "",
  categories: [],
  preferred_contact_method: "email",
  notes: "",
};

const TYPE_STYLES: Record<string, string> = {
  natural: "bg-accent-50 text-accent-700",
  legal: "bg-accent-100 text-accent-700",
};

const TYPE_LABELS: Record<string, string> = {
  natural: "Personne physique",
  legal: "Personne morale",
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

const LANGUAGE_OPTIONS = [
  { value: "fr", label: "Francais" },
  { value: "nl", label: "Neerlandais" },
  { value: "de", label: "Allemand" },
  { value: "en", label: "Anglais" },
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

const CATEGORY_OPTIONS = [
  "Client",
  "Prospect",
  "Avocat adverse",
  "Magistrat",
  "Notaire",
  "Huissier",
  "Expert",
  "Temoin",
  "Fournisseur",
  "Autre",
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

const TAB_IDS = {
  GENERAL: "general",
  COORDINATES: "coordinates",
  FINANCIAL: "financial",
  CLASSIFICATION: "classification",
};

export default function ContactsPage() {
  const { accessToken, tenantId } = useAuth();
  const router = useRouter();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState(TAB_IDS.GENERAL);
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});
  const [aiLoading, setAiLoading] = useState(false);
  const [aiResult, setAiResult] = useState<AIAssistResponse | null>(null);

  const [form, setForm] = useState<ContactFormState>({ ...INITIAL_FORM });

  const updateForm = (updates: Partial<ContactFormState>) => {
    setForm((prev) => ({ ...prev, ...updates }));
    // Clear validation errors for updated fields
    const updatedKeys = Object.keys(updates);
    if (updatedKeys.some((k) => k in validationErrors)) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        updatedKeys.forEach((k) => delete next[k]);
        return next;
      });
    }
  };

  const updateAddress = (
    field: "address" | "correspondence_address",
    key: keyof AddressFields,
    value: string,
  ) => {
    setForm((prev) => ({
      ...prev,
      [field]: { ...prev[field], [key]: value },
    }));
  };

  // Auto-compute full_name for natural persons
  useEffect(() => {
    if (form.type === "natural") {
      const parts = [form.civility, form.first_name, form.last_name].filter(
        Boolean,
      );
      const computedName = parts.join(" ");
      if (computedName && computedName !== form.full_name) {
        setForm((prev) => ({ ...prev, full_name: computedName }));
      }
    }
  }, [form.civility, form.first_name, form.last_name, form.type]);

  const loadContacts = () => {
    if (!accessToken) return;
    setLoading(true);
    apiFetch<ContactListResponse>("/contacts", accessToken, { tenantId })
      .then((data) => setContacts(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadContacts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken, tenantId]);

  const validateForm = (): boolean => {
    const errors: Record<string, string> = {};

    if (form.type === "natural") {
      if (!form.first_name.trim() && !form.last_name.trim()) {
        errors.first_name = "Le prenom ou le nom est obligatoire.";
      }
    } else {
      if (!form.full_name.trim()) {
        errors.full_name = "La raison sociale est obligatoire.";
      }
    }

    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      errors.email = "Format d'email invalide.";
    }

    if (
      form.secondary_email &&
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.secondary_email)
    ) {
      errors.secondary_email = "Format d'email invalide.";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const buildCreatePayload = () => {
    const addressStr = [
      form.address.street,
      [form.address.zip, form.address.city].filter(Boolean).join(" "),
      COUNTRY_OPTIONS.find((c) => c.value === form.address.country)?.label ||
        form.address.country,
    ]
      .filter(Boolean)
      .join(", ");

    const metadata: Record<string, unknown> = {};

    if (form.type === "natural") {
      if (form.civility) metadata.civility = form.civility;
      if (form.first_name) metadata.first_name = form.first_name;
      if (form.last_name) metadata.last_name = form.last_name;
      if (form.birth_date) metadata.birth_date = form.birth_date;
      if (form.birth_place) metadata.birth_place = form.birth_place;
      if (form.nationality) metadata.nationality = form.nationality;
      if (form.civil_status) metadata.civil_status = form.civil_status;
      if (form.profession) metadata.profession = form.profession;
      if (form.national_register)
        metadata.national_register = form.national_register;
    } else {
      if (form.legal_form) metadata.legal_form = form.legal_form;
      if (form.vat_number) metadata.vat_number = form.vat_number;
      if (form.corporate_purpose)
        metadata.corporate_purpose = form.corporate_purpose;
      if (form.legal_representative)
        metadata.legal_representative = form.legal_representative;
      if (form.address.street) {
        metadata.registered_office = { ...form.address };
      }
    }

    if (form.correspondence_address_different) {
      metadata.correspondence_address = { ...form.correspondence_address };
    }
    if (form.secondary_email)
      metadata.secondary_email = form.secondary_email;
    if (form.phone_fixed) metadata.phone_fixed = form.phone_fixed;
    if (form.fax) metadata.fax = form.fax;
    if (form.iban) metadata.iban = form.iban;
    if (form.bic) metadata.bic = form.bic;
    metadata.vat_liable = form.vat_liable;
    if (form.payment_preference)
      metadata.payment_preference = form.payment_preference;
    if (form.categories.length > 0) metadata.category = form.categories.join(", ");
    if (form.preferred_contact_method)
      metadata.preferred_contact_method = form.preferred_contact_method;
    if (form.notes) metadata.notes = form.notes;

    return {
      type: form.type,
      full_name: form.full_name,
      email: form.email || null,
      phone_e164: form.phone_e164 || null,
      bce_number: form.type === "legal" ? form.bce_number || null : null,
      address: addressStr || null,
      language: form.language,
      metadata: Object.keys(metadata).length > 0 ? metadata : undefined,
    };
  };

  const handleCreate = async () => {
    if (!accessToken) return;
    if (!validateForm()) return;

    setCreating(true);
    setError(null);
    try {
      const payload = buildCreatePayload();
      await apiFetch("/contacts", accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify(payload),
      });
      setSuccess("Contact cree avec succes");
      setShowModal(false);
      setForm({ ...INITIAL_FORM });
      setActiveTab(TAB_IDS.GENERAL);
      setAiResult(null);
      setValidationErrors({});
      loadContacts();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Une erreur est survenue";
      setError(message);
    } finally {
      setCreating(false);
    }
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setForm({ ...INITIAL_FORM });
    setActiveTab(TAB_IDS.GENERAL);
    setAiResult(null);
    setValidationErrors({});
  };

  const handleAIAssist = async () => {
    if (!accessToken) return;
    setAiLoading(true);
    try {
      const payload = buildCreatePayload();
      const result = await apiFetch<AIAssistResponse>(
        "/brain/contact/assist-creation",
        accessToken,
        {
          tenantId,
          method: "POST",
          body: JSON.stringify(payload),
        },
      );
      setAiResult(result);
    } catch {
      // AI service not available
      setAiResult({
        compliance_notes: [],
        duplicate_warnings: [],
        suggestions: ["Assistant IA indisponible. Veuillez reessayer plus tard."],
      });
    } finally {
      setAiLoading(false);
    }
  };

  const toggleCategory = (cat: string) => {
    setForm((prev) => ({
      ...prev,
      categories: prev.categories.includes(cat)
        ? prev.categories.filter((c) => c !== cat)
        : [...prev.categories, cat],
    }));
  };

  const filtered = contacts.filter((c) => {
    if (typeFilter && c.type !== typeFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      return (
        c.full_name.toLowerCase().includes(q) ||
        (c.email && c.email.toLowerCase().includes(q))
      );
    }
    return true;
  });

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  // --- Tab content renderers ---

  const renderGeneralTab = () => (
    <div className="space-y-6">
      {/* Type Selection */}
      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-3">
          Type de contact
        </label>
        <div className="grid grid-cols-2 gap-3">
          {[
            {
              value: "natural",
              label: "Personne physique",
              icon: <User className="w-5 h-5" />,
            },
            {
              value: "legal",
              label: "Personne morale",
              icon: <Building2 className="w-5 h-5" />,
            },
          ].map((t) => (
            <button
              key={t.value}
              onClick={() =>
                updateForm({
                  type: t.value as "natural" | "legal",
                  full_name:
                    t.value === "legal" ? "" : form.full_name,
                })
              }
              className={`px-4 py-3 rounded-lg font-medium text-sm border-2 transition-all flex items-center gap-3 ${
                form.type === t.value
                  ? "border-accent bg-accent-50 text-accent-700 shadow-md"
                  : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
              }`}
            >
              {t.icon}
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {/* Natural person fields */}
      {form.type === "natural" && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            {/* Civility */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Civilite
              </label>
              <select
                value={form.civility}
                onChange={(e) => updateForm({ civility: e.target.value })}
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

            {/* Prenom */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Prenom *
              </label>
              <input
                type="text"
                value={form.first_name}
                onChange={(e) => updateForm({ first_name: e.target.value })}
                placeholder="Jean"
                className={`input w-full ${validationErrors.first_name ? "border-danger-300 focus:ring-danger-500" : ""}`}
              />
              {validationErrors.first_name && (
                <p className="mt-1 text-sm text-danger-700">
                  {validationErrors.first_name}
                </p>
              )}
            </div>

            {/* Nom */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Nom *
              </label>
              <input
                type="text"
                value={form.last_name}
                onChange={(e) => updateForm({ last_name: e.target.value })}
                placeholder="Dupont"
                className={`input w-full ${validationErrors.last_name ? "border-danger-300 focus:ring-danger-500" : ""}`}
              />
            </div>
          </div>

          {/* Computed full name display */}
          {form.full_name && (
            <div className="bg-neutral-50 rounded-lg px-4 py-2 text-sm text-neutral-600">
              <span className="font-medium text-neutral-700">Nom complet : </span>
              {form.full_name}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {/* Date de naissance */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Date de naissance
              </label>
              <input
                type="date"
                value={form.birth_date}
                onChange={(e) => updateForm({ birth_date: e.target.value })}
                className="input w-full"
              />
            </div>

            {/* Lieu de naissance */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Lieu de naissance
              </label>
              <input
                type="text"
                value={form.birth_place}
                onChange={(e) => updateForm({ birth_place: e.target.value })}
                placeholder="Bruxelles"
                className="input w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Nationalite */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Nationalite
              </label>
              <input
                type="text"
                value={form.nationality}
                onChange={(e) => updateForm({ nationality: e.target.value })}
                placeholder="Belge"
                className="input w-full"
              />
            </div>

            {/* Etat civil */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Etat civil
              </label>
              <select
                value={form.civil_status}
                onChange={(e) => updateForm({ civil_status: e.target.value })}
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
            {/* Profession */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Profession
              </label>
              <input
                type="text"
                value={form.profession}
                onChange={(e) => updateForm({ profession: e.target.value })}
                placeholder="Ingenieur"
                className="input w-full"
              />
            </div>

            {/* Numero de registre national */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Numero de registre national
              </label>
              <input
                type="text"
                value={form.national_register}
                onChange={(e) =>
                  updateForm({ national_register: e.target.value })
                }
                placeholder="XX.XX.XX-XXX.XX"
                className="input w-full"
              />
            </div>
          </div>
        </div>
      )}

      {/* Legal entity fields */}
      {form.type === "legal" && (
        <div className="space-y-4">
          {/* Raison sociale */}
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-2">
              Raison sociale *
            </label>
            <input
              type="text"
              value={form.full_name}
              onChange={(e) => updateForm({ full_name: e.target.value })}
              placeholder="SA Immobel"
              className={`input w-full ${validationErrors.full_name ? "border-danger-300 focus:ring-danger-500" : ""}`}
            />
            {validationErrors.full_name && (
              <p className="mt-1 text-sm text-danger-700">
                {validationErrors.full_name}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Forme juridique */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Forme juridique
              </label>
              <select
                value={form.legal_form}
                onChange={(e) => updateForm({ legal_form: e.target.value })}
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

            {/* Numero BCE */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Numero BCE/KBO
              </label>
              <input
                type="text"
                value={form.bce_number}
                onChange={(e) => updateForm({ bce_number: e.target.value })}
                placeholder="0xxx.xxx.xxx"
                className="input w-full"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Numero TVA */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Numero TVA
              </label>
              <input
                type="text"
                value={form.vat_number}
                onChange={(e) => updateForm({ vat_number: e.target.value })}
                placeholder="BExxxxxxxxxx"
                className="input w-full"
              />
            </div>

            {/* Representant legal */}
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Representant legal
              </label>
              <input
                type="text"
                value={form.legal_representative}
                onChange={(e) =>
                  updateForm({ legal_representative: e.target.value })
                }
                placeholder="Jean Dupont"
                className="input w-full"
              />
            </div>
          </div>

          {/* Objet social */}
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-2">
              Objet social
            </label>
            <textarea
              value={form.corporate_purpose}
              onChange={(e) =>
                updateForm({ corporate_purpose: e.target.value })
              }
              placeholder="Activites informatiques"
              className="input w-full"
              rows={3}
            />
          </div>
        </div>
      )}
    </div>
  );

  const renderCoordinatesTab = () => (
    <div className="space-y-6">
      {/* Adresse principale */}
      <div>
        <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
          <MapPin className="w-4 h-4 text-accent-600" />
          Adresse principale
        </h3>
        <div className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Rue et numero
            </label>
            <input
              type="text"
              value={form.address.street}
              onChange={(e) => updateAddress("address", "street", e.target.value)}
              placeholder="Rue de la Loi 1"
              className="input w-full"
            />
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">
                Code postal
              </label>
              <input
                type="text"
                value={form.address.zip}
                onChange={(e) => updateAddress("address", "zip", e.target.value)}
                placeholder="1000"
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">
                Ville/Commune
              </label>
              <input
                type="text"
                value={form.address.city}
                onChange={(e) =>
                  updateAddress("address", "city", e.target.value)
                }
                placeholder="Bruxelles"
                className="input w-full"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">
                Pays
              </label>
              <select
                value={form.address.country}
                onChange={(e) =>
                  updateAddress("address", "country", e.target.value)
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
      </div>

      {/* Adresse de correspondance toggle */}
      <div>
        <label className="flex items-center gap-3 cursor-pointer">
          <div
            className={`relative w-10 h-5 rounded-full transition-colors ${form.correspondence_address_different ? "bg-accent" : "bg-neutral-300"}`}
            onClick={() =>
              updateForm({
                correspondence_address_different:
                  !form.correspondence_address_different,
              })
            }
          >
            <div
              className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${form.correspondence_address_different ? "translate-x-5" : ""}`}
            />
          </div>
          <span className="text-sm font-medium text-neutral-700">
            Adresse de correspondance differente de l'adresse principale
          </span>
        </label>
      </div>

      {form.correspondence_address_different && (
        <div>
          <h3 className="text-sm font-semibold text-neutral-900 mb-3 flex items-center gap-2">
            <MapPin className="w-4 h-4 text-warning-600" />
            Adresse de correspondance
          </h3>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">
                Rue et numero
              </label>
              <input
                type="text"
                value={form.correspondence_address.street}
                onChange={(e) =>
                  updateAddress(
                    "correspondence_address",
                    "street",
                    e.target.value,
                  )
                }
                placeholder="Rue de la Loi 1"
                className="input w-full"
              />
            </div>
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">
                  Code postal
                </label>
                <input
                  type="text"
                  value={form.correspondence_address.zip}
                  onChange={(e) =>
                    updateAddress(
                      "correspondence_address",
                      "zip",
                      e.target.value,
                    )
                  }
                  placeholder="1000"
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">
                  Ville/Commune
                </label>
                <input
                  type="text"
                  value={form.correspondence_address.city}
                  onChange={(e) =>
                    updateAddress(
                      "correspondence_address",
                      "city",
                      e.target.value,
                    )
                  }
                  placeholder="Bruxelles"
                  className="input w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">
                  Pays
                </label>
                <select
                  value={form.correspondence_address.country}
                  onChange={(e) =>
                    updateAddress(
                      "correspondence_address",
                      "country",
                      e.target.value,
                    )
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
        </div>
      )}

      {/* Contact details */}
      <div className="border-t border-neutral-200 pt-6">
        <h3 className="text-sm font-semibold text-neutral-900 mb-3">
          Moyens de contact
        </h3>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Email principal
            </label>
            <input
              type="email"
              value={form.email}
              onChange={(e) => updateForm({ email: e.target.value })}
              placeholder="contact@example.be"
              className={`input w-full ${validationErrors.email ? "border-danger-300 focus:ring-danger-500" : ""}`}
            />
            {validationErrors.email && (
              <p className="mt-1 text-xs text-danger-700">
                {validationErrors.email}
              </p>
            )}
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Email secondaire
            </label>
            <input
              type="email"
              value={form.secondary_email}
              onChange={(e) =>
                updateForm({ secondary_email: e.target.value })
              }
              placeholder="jean.dupont@work.be"
              className={`input w-full ${validationErrors.secondary_email ? "border-danger-300 focus:ring-danger-500" : ""}`}
            />
            {validationErrors.secondary_email && (
              <p className="mt-1 text-xs text-danger-700">
                {validationErrors.secondary_email}
              </p>
            )}
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 mt-4">
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Telephone mobile
            </label>
            <input
              type="tel"
              value={form.phone_e164}
              onChange={(e) => updateForm({ phone_e164: e.target.value })}
              placeholder="+32470123456"
              className="input w-full"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Telephone fixe
            </label>
            <input
              type="tel"
              value={form.phone_fixed}
              onChange={(e) => updateForm({ phone_fixed: e.target.value })}
              placeholder="+3222345678"
              className="input w-full"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-neutral-600 mb-1">
              Fax
            </label>
            <input
              type="tel"
              value={form.fax}
              onChange={(e) => updateForm({ fax: e.target.value })}
              placeholder="+3222345679"
              className="input w-full"
            />
          </div>
        </div>
      </div>

      {/* Language */}
      <div className="border-t border-neutral-200 pt-6">
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">
            Langue de correspondance
          </label>
          <select
            value={form.language}
            onChange={(e) => updateForm({ language: e.target.value })}
            className="input w-full max-w-xs"
          >
            {LANGUAGE_OPTIONS.map((l) => (
              <option key={l.value} value={l.value}>
                {l.label}
              </option>
            ))}
          </select>
        </div>
      </div>
    </div>
  );

  const renderFinancialTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">
            IBAN
          </label>
          <input
            type="text"
            value={form.iban}
            onChange={(e) => updateForm({ iban: e.target.value })}
            placeholder="BE68539007547034"
            className="input w-full"
          />
          <p className="mt-1 text-xs text-neutral-400">
            Format : BExx xxxx xxxx xxxx
          </p>
        </div>
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">
            BIC
          </label>
          <input
            type="text"
            value={form.bic}
            onChange={(e) => updateForm({ bic: e.target.value })}
            placeholder="BBRUBEBB"
            className="input w-full"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Assujetti TVA */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">
            Assujetti TVA
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              className={`relative w-10 h-5 rounded-full transition-colors ${form.vat_liable ? "bg-accent" : "bg-neutral-300"}`}
              onClick={() => updateForm({ vat_liable: !form.vat_liable })}
            >
              <div
                className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform ${form.vat_liable ? "translate-x-5" : ""}`}
              />
            </div>
            <span className="text-sm text-neutral-600">
              {form.vat_liable ? "Oui" : "Non"}
            </span>
          </label>
        </div>

        {/* Mode de paiement */}
        <div>
          <label className="block text-sm font-semibold text-neutral-900 mb-2">
            Mode de paiement prefere
          </label>
          <select
            value={form.payment_preference}
            onChange={(e) =>
              updateForm({ payment_preference: e.target.value })
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
  );

  const renderClassificationTab = () => (
    <div className="space-y-6">
      {/* Categories */}
      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-3">
          Categorie
        </label>
        <div className="flex flex-wrap gap-2">
          {CATEGORY_OPTIONS.map((cat) => (
            <button
              key={cat}
              onClick={() => toggleCategory(cat)}
              className={`px-3 py-1.5 rounded-full text-sm font-medium border transition-all ${
                form.categories.includes(cat)
                  ? "bg-accent text-white border-accent shadow-sm"
                  : "bg-white text-neutral-600 border-neutral-300 hover:border-neutral-400"
              }`}
            >
              {form.categories.includes(cat) && (
                <Check className="w-3 h-3 inline-block mr-1" />
              )}
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Preferred contact method */}
      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-3">
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
                name="preferred_contact_method"
                value={m.value}
                checked={form.preferred_contact_method === m.value}
                onChange={(e) =>
                  updateForm({ preferred_contact_method: e.target.value })
                }
                className="w-4 h-4 text-accent border-neutral-300 focus:ring-accent"
              />
              <span className="text-sm text-neutral-700">{m.label}</span>
            </label>
          ))}
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-semibold text-neutral-900 mb-2">
          Notes internes
        </label>
        <textarea
          value={form.notes}
          onChange={(e) => updateForm({ notes: e.target.value })}
          placeholder="Notes internes sur ce contact"
          className="input w-full"
          rows={4}
        />
      </div>

      {/* AI Assist */}
      <div className="border-t border-neutral-200 pt-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-neutral-900 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-accent-600" />
            Assistance IA
          </h3>
          <Button
            variant="secondary"
            size="sm"
            loading={aiLoading}
            disabled={aiLoading}
            onClick={handleAIAssist}
            icon={<Sparkles className="w-4 h-4" />}
          >
            Verifier avec l'IA
          </Button>
        </div>

        {aiResult && (
          <div className="space-y-4">
            {/* Compliance notes */}
            {aiResult.compliance_notes.length > 0 && (
              <div className="bg-accent-50 border border-accent-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <ShieldCheck className="w-4 h-4 text-accent-600" />
                  <span className="text-sm font-semibold text-accent-700">
                    Conformite et RGPD
                  </span>
                </div>
                <ul className="space-y-1">
                  {aiResult.compliance_notes.map((note, i) => (
                    <li
                      key={i}
                      className="text-sm text-accent-700 flex items-start gap-2"
                    >
                      <span className="w-1 h-1 rounded-full bg-accent-500 mt-2 flex-shrink-0" />
                      {note}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Duplicate warnings */}
            {aiResult.duplicate_warnings.length > 0 && (
              <div className="bg-warning-50 border border-warning-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="w-4 h-4 text-warning-600" />
                  <span className="text-sm font-semibold text-warning-700">
                    Verification des doublons
                  </span>
                </div>
                <ul className="space-y-1">
                  {aiResult.duplicate_warnings.map((warning, i) => (
                    <li
                      key={i}
                      className="text-sm text-warning-700 flex items-start gap-2"
                    >
                      <span className="w-1 h-1 rounded-full bg-warning-500 mt-2 flex-shrink-0" />
                      {warning}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Suggestions */}
            {aiResult.suggestions.length > 0 && (
              <div className="bg-neutral-50 border border-neutral-200 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Info className="w-4 h-4 text-neutral-600" />
                  <span className="text-sm font-semibold text-neutral-700">
                    Suggestions
                  </span>
                </div>
                <ul className="space-y-1">
                  {aiResult.suggestions.map((suggestion, i) => (
                    <li
                      key={i}
                      className="text-sm text-neutral-600 flex items-start gap-2"
                    >
                      <span className="w-1 h-1 rounded-full bg-neutral-400 mt-2 flex-shrink-0" />
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );

  const tabs = [
    {
      id: TAB_IDS.GENERAL,
      label: "Informations generales",
      icon: <User className="w-4 h-4" />,
    },
    {
      id: TAB_IDS.COORDINATES,
      label: "Coordonnees",
      icon: <MapPin className="w-4 h-4" />,
    },
    {
      id: TAB_IDS.FINANCIAL,
      label: "Informations financieres",
      icon: <CreditCard className="w-4 h-4" />,
    },
    {
      id: TAB_IDS.CLASSIFICATION,
      label: "Classification et notes",
      icon: <Tag className="w-4 h-4" />,
    },
  ];

  if (loading) {
    return <LoadingSkeleton variant="table" />;
  }

  if (error && !showModal) {
    return <ErrorState message={error} onRetry={() => window.location.reload()} />;
  }

  return (
    <div className="space-y-6">
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-lg text-sm flex items-center gap-2 shadow-lg animate-in fade-in">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Header Section - Corporate */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-display font-bold text-neutral-900 mb-2">
            Contacts
          </h1>
          <p className="text-neutral-600 text-sm">
            Gerez votre reseau de contacts et relations commerciales
          </p>
        </div>
        <Button
          variant="primary"
          size="lg"
          icon={<Plus className="w-5 h-5" />}
          onClick={() => setShowModal(true)}
        >
          Nouveau contact
        </Button>
      </div>

      {/* Premium Search & Filter Section */}
      <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-6 space-y-4">
        {/* Prominent Search */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-neutral-400" />
          <input
            type="text"
            placeholder="Chercher par nom, email, telephone..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-12 py-3 text-base border border-neutral-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-accent-200 focus:border-accent transition-all"
          />
        </div>

        {/* Type Filter Chips */}
        <div className="flex flex-wrap gap-2 items-center border-t border-neutral-100 pt-4">
          <span className="text-xs text-neutral-500 uppercase tracking-wider font-semibold">
            Filtrer par type:
          </span>
          <div className="flex flex-wrap gap-2">
            {[
              { label: "Tous", value: "" },
              { label: "Personnes physiques", value: "natural" },
              { label: "Personnes morales", value: "legal" },
            ].map((f) => (
              <button
                key={f.value}
                onClick={() => setTypeFilter(f.value)}
                className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-150 ${
                  typeFilter === f.value
                    ? "bg-accent text-white shadow-md hover:shadow-lg"
                    : "bg-neutral-100 text-neutral-600 hover:bg-neutral-200"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>
          <div className="flex-1" />
          <span className="text-xs text-neutral-500">
            {filtered.length} contact{filtered.length !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Multi-tab Creation Modal */}
      <Modal
        isOpen={showModal}
        onClose={handleCloseModal}
        title="Ajouter un nouveau contact"
        size="xl"
        footer={
          <div className="flex items-center justify-between">
            <p className="text-xs text-neutral-400">
              * Champs obligatoires (onglet Informations generales)
            </p>
            <div className="flex gap-3">
              <Button
                variant="secondary"
                size="md"
                onClick={handleCloseModal}
              >
                Annuler
              </Button>
              <Button
                variant="primary"
                size="md"
                loading={creating}
                disabled={creating}
                onClick={handleCreate}
              >
                Creer le contact
              </Button>
            </div>
          </div>
        }
      >
        {/* Error in modal */}
        {error && showModal && (
          <div className="mb-4 p-3 bg-danger-50 border border-danger-200 rounded-lg">
            <p className="text-sm text-danger-700">{error}</p>
          </div>
        )}

        {/* Tab Navigation */}
        <div className="border-b border-neutral-200 mb-6">
          <div className="flex gap-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
                  activeTab === tab.id
                    ? "border-accent text-accent-700"
                    : "border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300"
                }`}
              >
                {tab.icon}
                <span className="hidden sm:inline">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="min-h-[350px]">
          {activeTab === TAB_IDS.GENERAL && renderGeneralTab()}
          {activeTab === TAB_IDS.COORDINATES && renderCoordinatesTab()}
          {activeTab === TAB_IDS.FINANCIAL && renderFinancialTab()}
          {activeTab === TAB_IDS.CLASSIFICATION && renderClassificationTab()}
        </div>
      </Modal>

      {/* DataTable with Premium Styling */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-12 text-center">
          <EmptyState title="Aucun contact trouve" />
          {!searchQuery && !typeFilter && (
            <Button
              variant="primary"
              size="lg"
              icon={<Plus className="w-5 h-5" />}
              onClick={() => setShowModal(true)}
              className="mt-6"
            >
              Ajouter votre premier contact
            </Button>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 overflow-hidden">
          <table className="w-full">
            <thead className="bg-neutral-50 border-b border-neutral-200">
              <tr>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Contact
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Type
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Email
                </th>
                <th className="text-left px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Telephone
                </th>
                <th className="text-center px-6 py-4 text-xs font-semibold text-neutral-600 uppercase tracking-wider">
                  Action
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100">
              {filtered.map((c) => (
                <tr
                  key={c.id}
                  className="hover:bg-neutral-50 transition-all duration-150 cursor-pointer group"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <Avatar
                        fallback={getInitials(c.full_name)}
                        size="md"
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-neutral-900 group-hover:text-accent truncate">
                          {c.full_name}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <Badge
                      variant={c.type === "natural" ? "accent" : "neutral"}
                      size="sm"
                    >
                      {TYPE_LABELS[c.type] || c.type}
                    </Badge>
                  </td>
                  <td className="px-6 py-4">
                    {c.email ? (
                      <a
                        href={`mailto:${c.email}`}
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-700 transition-colors group-hover:underline"
                      >
                        <Mail className="w-3.5 h-3.5 flex-shrink-0" />
                        <span className="truncate">{c.email}</span>
                      </a>
                    ) : (
                      <span className="text-sm text-neutral-400">--</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {c.phone_e164 ? (
                      <a
                        href={`tel:${c.phone_e164}`}
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-700 transition-colors group-hover:underline"
                      >
                        <Phone className="w-3.5 h-3.5 flex-shrink-0" />
                        {c.phone_e164}
                      </a>
                    ) : (
                      <span className="text-sm text-neutral-400">--</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() =>
                        router.push(`/dashboard/contacts/${c.id}`)
                      }
                      className="p-2 rounded-lg hover:bg-accent hover:text-white transition-all opacity-0 group-hover:opacity-100"
                      title="Voir le contact"
                    >
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
