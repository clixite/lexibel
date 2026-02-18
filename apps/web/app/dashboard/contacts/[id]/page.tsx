"use client";

import { useSession } from "next-auth/react";
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
} from "lucide-react";
import SkeletonCard from "@/components/skeletons/SkeletonCard";

interface Contact {
  id: string;
  type: "natural" | "legal";
  full_name: string;
  bce_number: string | null;
  email: string | null;
  phone_e164: string | null;
  address: string | null;
  language: string | null;
  created_at: string;
  updated_at: string;
}

interface ValidationErrors {
  email?: string;
  full_name?: string;
}

const TYPE_LABELS: Record<string, string> = {
  natural: "Personne physique",
  legal: "Personne morale",
};

const LANGUAGE_OPTIONS = [
  { value: "fr", label: "Fran\u00e7ais" },
  { value: "nl", label: "N\u00e9erlandais" },
  { value: "en", label: "Anglais" },
  { value: "de", label: "Allemand" },
];

export default function ContactDetailPage() {
  const { data: session } = useSession();
  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;
  const params = useParams();
  const router = useRouter();
  const contactId = params.id as string;

  const [contact, setContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);
  const [editedContact, setEditedContact] = useState<Partial<Contact>>({});
  const [validationErrors, setValidationErrors] = useState<ValidationErrors>(
    {}
  );

  useEffect(() => {
    if (!token || !tenantId) return;

    const fetchContact = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiFetch<Contact>(
          `/contacts/${contactId}`,
          token,
          { tenantId }
        );
        setContact(data);
        setEditedContact(data);
      } catch (err: any) {
        setError(err.message || "Erreur lors du chargement du contact");
      } finally {
        setLoading(false);
      }
    };

    fetchContact();
  }, [token, tenantId, contactId]);

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  const getLanguageLabel = (lang: string | null) => {
    if (!lang) return "Non sp\u00e9cifi\u00e9";
    const found = LANGUAGE_OPTIONS.find((l) => l.value === lang);
    return found ? found.label : lang;
  };

  const validateEmail = (email: string): boolean => {
    if (!email) return true;
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(email);
  };

  const validate = (): boolean => {
    const errors: ValidationErrors = {};

    if (!editedContact.full_name?.trim()) {
      errors.full_name = "Le nom complet est obligatoire.";
    }

    if (editedContact.email && !validateEmail(editedContact.email)) {
      errors.email = "Format d\u2019email invalide.";
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditedContact({ ...contact });
    setValidationErrors({});
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedContact({ ...contact });
    setValidationErrors({});
    setError(null);
  };

  const handleSave = async () => {
    if (!token || !tenantId) return;
    if (!validate()) return;

    try {
      setSaving(true);
      setError(null);

      const updateData = {
        type: editedContact.type,
        full_name: editedContact.full_name,
        email: editedContact.email || null,
        phone_e164: editedContact.phone_e164 || null,
        bce_number: editedContact.bce_number || null,
        address: editedContact.address || null,
        language: editedContact.language || null,
      };

      const updatedContact = await apiFetch<Contact>(
        `/contacts/${contactId}`,
        token,
        {
          method: "PATCH",
          body: JSON.stringify(updateData),
          tenantId,
        }
      );

      setContact(updatedContact);
      setEditedContact(updatedContact);
      setIsEditing(false);
      setValidationErrors({});
      setSuccess("Contact mis \u00e0 jour avec succ\u00e8s");
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la sauvegarde du contact");
    } finally {
      setSaving(false);
    }
  };

  const handleInputChange = (field: keyof Contact, value: string) => {
    setEditedContact((prev) => ({
      ...prev,
      [field]: value,
    }));
    // Clear validation error for this field on change
    if (field in validationErrors) {
      setValidationErrors((prev) => {
        const next = { ...prev };
        delete next[field as keyof ValidationErrors];
        return next;
      });
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

  const avatarBg =
    contact.type === "legal" ? "bg-purple-100" : "bg-accent-50";
  const avatarText =
    contact.type === "legal" ? "text-purple-700" : "text-accent-700";

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
            <h1 className="text-2xl font-bold text-neutral-900">
              {contact.full_name}
            </h1>
            <span
              className={`inline-flex items-center px-3 py-1 rounded-full text-sm font-medium mt-1 ${
                contact.type === "legal"
                  ? "bg-accent-100 text-accent-700"
                  : "bg-accent-50 text-accent-700"
              }`}
            >
              {TYPE_LABELS[contact.type] || contact.type}
            </span>
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

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Informations (col-span-2) */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-xl font-semibold text-neutral-900 mb-6">
              Informations
            </h2>
            <div className="space-y-5">
              {/* Type */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  Type de contact
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {TYPE_LABELS[contact.type] || contact.type}
                  </p>
                ) : (
                  <select
                    value={editedContact.type || "natural"}
                    onChange={(e) => handleInputChange("type", e.target.value)}
                    className="input w-full"
                  >
                    <option value="natural">Personne physique</option>
                    <option value="legal">Personne morale</option>
                  </select>
                )}
              </div>

              {/* Nom complet */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  Nom complet
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">{contact.full_name}</p>
                ) : (
                  <>
                    <input
                      type="text"
                      value={editedContact.full_name || ""}
                      onChange={(e) =>
                        handleInputChange("full_name", e.target.value)
                      }
                      className={`input w-full ${
                        validationErrors.full_name
                          ? "border-danger-300 focus:ring-danger-500"
                          : ""
                      }`}
                      placeholder="Jean Dupont"
                    />
                    {validationErrors.full_name && (
                      <p className="mt-1 text-sm text-danger-700">
                        {validationErrors.full_name}
                      </p>
                    )}
                  </>
                )}
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  Email
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.email || (
                      <span className="text-neutral-400">Non sp&eacute;cifi&eacute;</span>
                    )}
                  </p>
                ) : (
                  <>
                    <input
                      type="email"
                      value={editedContact.email || ""}
                      onChange={(e) =>
                        handleInputChange("email", e.target.value)
                      }
                      className={`input w-full ${
                        validationErrors.email
                          ? "border-danger-300 focus:ring-danger-500"
                          : ""
                      }`}
                      placeholder="contact@example.be"
                    />
                    {validationErrors.email && (
                      <p className="mt-1 text-sm text-danger-700">
                        {validationErrors.email}
                      </p>
                    )}
                  </>
                )}
              </div>

              {/* T\u00e9l\u00e9phone */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  T&eacute;l&eacute;phone
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.phone_e164 || (
                      <span className="text-neutral-400">Non sp&eacute;cifi&eacute;</span>
                    )}
                  </p>
                ) : (
                  <input
                    type="tel"
                    value={editedContact.phone_e164 || ""}
                    onChange={(e) =>
                      handleInputChange("phone_e164", e.target.value)
                    }
                    className="input w-full"
                    placeholder="+32 470 12 34 56"
                  />
                )}
              </div>

              {/* Num\u00e9ro BCE */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  Num&eacute;ro BCE
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.bce_number || (
                      <span className="text-neutral-400">Non sp&eacute;cifi&eacute;</span>
                    )}
                  </p>
                ) : (
                  <input
                    type="text"
                    value={editedContact.bce_number || ""}
                    onChange={(e) =>
                      handleInputChange("bce_number", e.target.value)
                    }
                    className="input w-full"
                    placeholder="0xxx.xxx.xxx"
                  />
                )}
              </div>

              {/* Adresse */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  Adresse
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900 whitespace-pre-line">
                    {contact.address || (
                      <span className="text-neutral-400">Non sp&eacute;cifi&eacute;e</span>
                    )}
                  </p>
                ) : (
                  <textarea
                    value={editedContact.address || ""}
                    onChange={(e) =>
                      handleInputChange("address", e.target.value)
                    }
                    className="input w-full"
                    rows={3}
                    placeholder="Rue, num&#233;ro&#10;Code postal, Ville"
                  />
                )}
              </div>

              {/* Langue */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1.5">
                  Langue de correspondance
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {getLanguageLabel(contact.language)}
                  </p>
                ) : (
                  <select
                    value={editedContact.language || ""}
                    onChange={(e) =>
                      handleInputChange("language", e.target.value)
                    }
                    className="input w-full"
                  >
                    <option value="">Non sp&eacute;cifi&eacute;</option>
                    {LANGUAGE_OPTIONS.map((lang) => (
                      <option key={lang.value} value={lang.value}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                )}
              </div>
            </div>

            {/* Timestamps */}
            <div className="mt-8 pt-6 border-t border-neutral-200">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-neutral-500 mb-1">Cr&eacute;&eacute; le</p>
                  <p className="text-neutral-900">
                    {new Date(contact.created_at).toLocaleDateString("fr-BE", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-neutral-500 mb-1">Modifi&eacute; le</p>
                  <p className="text-neutral-900">
                    {new Date(contact.updated_at).toLocaleDateString("fr-BE", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right sidebar (col-span-1) */}
        <div className="lg:col-span-1 space-y-6">
          {/* Dossiers li\u00e9s */}
          <div className="card">
            <h2 className="text-lg font-semibold text-neutral-900 mb-4">
              Dossiers li&eacute;s
            </h2>
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-neutral-100 mb-3">
                <Briefcase className="w-7 h-7 text-neutral-400" />
              </div>
              <p className="text-neutral-600 font-medium">
                Aucun dossier li&eacute;
              </p>
              <p className="text-sm text-neutral-400 mt-1">
                Les dossiers associ&eacute;s appara&icirc;tront ici.
              </p>
            </div>
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
                Historique &agrave; venir
              </p>
              <p className="text-sm text-neutral-400 mt-1">
                L&apos;historique des communications sera bient&ocirc;t disponible.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
