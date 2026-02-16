"use client";

import { useSession } from "next-auth/react";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Loader2, ArrowLeft, Edit2, Save, X } from "lucide-react";

interface Contact {
  id: string;
  type: "natural" | "legal";
  full_name: string;
  email: string | null;
  phone_e164: string | null;
  bce_number: string | null;
  address: string | null;
  language: string | null;
  created_at: string;
  updated_at: string;
}

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
  const [editedContact, setEditedContact] = useState<Partial<Contact>>({});

  useEffect(() => {
    if (!token || !tenantId) return;

    const fetchContact = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await apiFetch(`/contacts/${contactId}`, token, { tenantId });
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

  const handleEdit = () => {
    setIsEditing(true);
    setEditedContact({ ...contact });
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditedContact({ ...contact });
  };

  const handleSave = async () => {
    if (!token || !tenantId) return;

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

      const updatedContact = await apiFetch(
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
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-accent-600" />
      </div>
    );
  }

  if (error && !contact) {
    return (
      <div className="p-6">
        <div className="card bg-red-50 border-red-200">
          <p className="text-red-700">{error}</p>
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

  const getTypeBadge = (type: "natural" | "legal") => {
    if (type === "natural") {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-accent-50 text-accent-700">
          Personne physique
        </span>
      );
    }
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-purple-100 text-purple-700">
        Personne morale
      </span>
    );
  };

  const getLanguageLabel = (lang: string | null) => {
    if (!lang) return "Non spécifié";
    const languages: Record<string, string> = {
      fr: "Français",
      nl: "Néerlandais",
      en: "Anglais",
      de: "Allemand",
    };
    return languages[lang] || lang;
  };

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Back button */}
      <button
        onClick={() => router.push("/dashboard/contacts")}
        className="inline-flex items-center gap-2 text-neutral-600 hover:text-neutral-900 mb-6 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour aux contacts
      </button>

      {/* Header */}
      <div className="mb-6">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-neutral-900 mb-3">
              {contact.full_name}
            </h1>
            <div>{getTypeBadge(contact.type)}</div>
          </div>
          <div className="flex gap-2">
            {!isEditing ? (
              <button onClick={handleEdit} className="btn-primary">
                <Edit2 className="w-4 h-4 mr-2" />
                Modifier
              </button>
            ) : (
              <>
                <button
                  onClick={handleCancel}
                  disabled={saving}
                  className="px-4 py-2 border border-neutral-300 rounded-lg hover:bg-neutral-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  <X className="w-4 h-4" />
                  Annuler
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Enregistrement...
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      Enregistrer
                    </>
                  )}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-700">{error}</p>
        </div>
      )}

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Informations */}
        <div className="lg:col-span-2">
          <div className="card">
            <h2 className="text-xl font-semibold text-neutral-900 mb-6">
              Informations
            </h2>
            <div className="space-y-6">
              {/* Type */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Type de contact
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.type === "natural"
                      ? "Personne physique"
                      : "Personne morale"}
                  </p>
                ) : (
                  <select
                    value={editedContact.type || "natural"}
                    onChange={(e) =>
                      handleInputChange(
                        "type",
                        e.target.value as "natural" | "legal"
                      )
                    }
                    className="input w-full"
                  >
                    <option value="natural">Personne physique</option>
                    <option value="legal">Personne morale</option>
                  </select>
                )}
              </div>

              {/* Full name */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Nom complet
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">{contact.full_name}</p>
                ) : (
                  <input
                    type="text"
                    value={editedContact.full_name || ""}
                    onChange={(e) => handleInputChange("full_name", e.target.value)}
                    className="input w-full"
                    required
                  />
                )}
              </div>

              {/* Email */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Email
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.email || (
                      <span className="text-neutral-500">Non spécifié</span>
                    )}
                  </p>
                ) : (
                  <input
                    type="email"
                    value={editedContact.email || ""}
                    onChange={(e) => handleInputChange("email", e.target.value)}
                    className="input w-full"
                    placeholder="email@example.com"
                  />
                )}
              </div>

              {/* Phone */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Téléphone
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.phone_e164 || (
                      <span className="text-neutral-500">Non spécifié</span>
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
                    placeholder="+32 2 123 45 67"
                  />
                )}
              </div>

              {/* BCE Number */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Numéro BCE
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {contact.bce_number || (
                      <span className="text-neutral-500">Non spécifié</span>
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
                    placeholder="BE 0123.456.789"
                  />
                )}
              </div>

              {/* Address */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Adresse
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900 whitespace-pre-line">
                    {contact.address || (
                      <span className="text-neutral-500">Non spécifiée</span>
                    )}
                  </p>
                ) : (
                  <textarea
                    value={editedContact.address || ""}
                    onChange={(e) => handleInputChange("address", e.target.value)}
                    className="input w-full"
                    rows={3}
                    placeholder="Rue, numéro&#10;Code postal, Ville"
                  />
                )}
              </div>

              {/* Language */}
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-2">
                  Langue de correspondance
                </label>
                {!isEditing ? (
                  <p className="text-neutral-900">
                    {getLanguageLabel(contact.language)}
                  </p>
                ) : (
                  <select
                    value={editedContact.language || ""}
                    onChange={(e) => handleInputChange("language", e.target.value)}
                    className="input w-full"
                  >
                    <option value="">Non spécifié</option>
                    <option value="fr">Français</option>
                    <option value="nl">Néerlandais</option>
                    <option value="en">Anglais</option>
                    <option value="de">Allemand</option>
                  </select>
                )}
              </div>
            </div>

            {/* Metadata */}
            <div className="mt-8 pt-6 border-t border-neutral-200">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-neutral-500 mb-1">Créé le</p>
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
                  <p className="text-neutral-500 mb-1">Modifié le</p>
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

        {/* Dossiers liés */}
        <div className="lg:col-span-1">
          <div className="card">
            <h2 className="text-xl font-semibold text-neutral-900 mb-4">
              Dossiers liés
            </h2>
            <div className="text-center py-8">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-neutral-100 mb-4">
                <svg
                  className="w-8 h-8 text-neutral-400"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                  />
                </svg>
              </div>
              <p className="text-neutral-600 font-medium">
                Fonctionnalité à venir
              </p>
              <p className="text-sm text-neutral-500 mt-2">
                La liste des dossiers associés à ce contact sera bientôt disponible.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
