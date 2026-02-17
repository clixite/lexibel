"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Loader2, Search, Mail, Phone, X, Check, ChevronRight } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal, Button, Avatar, Card } from "@/components/ui";

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

const TYPE_STYLES: Record<string, string> = {
  natural: "bg-accent-50 text-accent-700",
  legal: "bg-purple-100 text-purple-700",
};

const TYPE_LABELS: Record<string, string> = {
  natural: "Personne physique",
  legal: "Personne morale",
};

export default function ContactsPage() {
  const { data: session } = useSession();
  const router = useRouter();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [creating, setCreating] = useState(false);
  const [success, setSuccess] = useState<string | null>(null);

  const [form, setForm] = useState({
    type: "natural" as "natural" | "legal",
    full_name: "",
    email: "",
    phone_e164: "",
    bce_number: "",
    language: "fr",
  });

  const token = (session?.user as any)?.accessToken;
  const tenantId = (session?.user as any)?.tenantId;

  const loadContacts = () => {
    if (!token) return;
    setLoading(true);
    apiFetch<ContactListResponse>("/contacts", token, { tenantId })
      .then((data) => setContacts(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadContacts();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session]);

  const handleCreate = async () => {
    if (!token || !form.full_name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await apiFetch("/contacts", token, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          type: form.type,
          full_name: form.full_name,
          email: form.email || null,
          phone_e164: form.phone_e164 || null,
          bce_number: form.type === "legal" ? form.bce_number || null : null,
          language: form.language,
        }),
      });
      setSuccess("Contact créé avec succès");
      setShowModal(false);
      setForm({ type: "natural", full_name: "", email: "", phone_e164: "", bce_number: "", language: "fr" });
      loadContacts();
      setTimeout(() => setSuccess(null), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
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

  if (loading) {
    return <LoadingSkeleton variant="table" />;
  }

  if (error) {
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
            Gérez votre réseau de contacts et relations commerciales
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
            placeholder="Chercher par nom, email, téléphone..."
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

      {/* Premium Create Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Ajouter un nouveau contact"
        size="lg"
        footer={
          <div className="flex justify-end gap-3">
            <Button
              variant="secondary"
              size="md"
              onClick={() => setShowModal(false)}
            >
              Annuler
            </Button>
            <Button
              variant="primary"
              size="md"
              loading={creating}
              disabled={creating || !form.full_name.trim()}
              onClick={handleCreate}
            >
              Créer le contact
            </Button>
          </div>
        }
      >
        <div className="space-y-6">
          {/* Type Selection */}
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-3">
              Type de contact
            </label>
            <div className="grid grid-cols-2 gap-3">
              {[
                { value: "natural", label: "Personne physique" },
                { value: "legal", label: "Personne morale" },
              ].map((t) => (
                <button
                  key={t.value}
                  onClick={() =>
                    setForm((f) => ({ ...f, type: t.value as "natural" | "legal" }))
                  }
                  className={`px-4 py-3 rounded-lg font-medium text-sm border-2 transition-all ${
                    form.type === t.value
                      ? "border-accent bg-accent-50 text-accent-700 shadow-md"
                      : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                  }`}
                >
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Name Field */}
          <div>
            <label className="block text-sm font-semibold text-neutral-900 mb-2">
              {form.type === "natural" ? "Nom complet" : "Raison sociale"}
            </label>
            <input
              type="text"
              value={form.full_name}
              onChange={(e) =>
                setForm((f) => ({ ...f, full_name: e.target.value }))
              }
              placeholder={
                form.type === "natural" ? "Jean Dupont" : "SA Immobel"
              }
              className="input"
            />
          </div>

          {/* Contact Fields */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Email
              </label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
                placeholder="contact@example.be"
                className="input"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Téléphone
              </label>
              <input
                type="tel"
                value={form.phone_e164}
                onChange={(e) =>
                  setForm((f) => ({ ...f, phone_e164: e.target.value }))
                }
                placeholder="+32470123456"
                className="input"
              />
            </div>
          </div>

          {/* BCE Number for Legal */}
          {form.type === "legal" && (
            <div>
              <label className="block text-sm font-semibold text-neutral-900 mb-2">
                Numéro BCE
              </label>
              <input
                type="text"
                value={form.bce_number}
                onChange={(e) =>
                  setForm((f) => ({ ...f, bce_number: e.target.value }))
                }
                placeholder="0123.456.789"
                className="input"
              />
            </div>
          )}
        </div>
      </Modal>

      {/* DataTable with Premium Styling */}
      {filtered.length === 0 ? (
        <div className="bg-white rounded-xl shadow-subtle border border-neutral-100 p-12 text-center">
          <EmptyState title="Aucun contact trouvé" />
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
                  Téléphone
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
                      <span className="text-sm text-neutral-400">—</span>
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
                      <span className="text-sm text-neutral-400">—</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-center">
                    <button
                      onClick={() => router.push(`/dashboard/contacts/${c.id}`)}
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
