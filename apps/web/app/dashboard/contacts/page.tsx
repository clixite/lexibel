"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Plus, Loader2, Search, UserX, Mail, Phone, X, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { LoadingSkeleton, ErrorState, EmptyState, Badge, Modal } from "@/components/ui";

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
    <div>
      {/* Success toast */}
      {success && (
        <div className="fixed top-4 right-4 z-50 bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2 shadow-lg">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-neutral-900">Contacts</h1>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-50 text-success-700">
            {contacts.length}
          </span>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          Nouveau contact
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-3 mb-6">
        <div className="flex gap-1 bg-neutral-100 rounded-md p-1">
          {[
            { label: "Tous", value: "" },
            { label: "Personnes physiques", value: "natural" },
            { label: "Personnes morales", value: "legal" },
          ].map((f) => (
            <button
              key={f.value}
              onClick={() => setTypeFilter(f.value)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-150 ${
                typeFilter === f.value
                  ? "bg-white text-neutral-900 shadow-subtle"
                  : "text-neutral-500 hover:text-neutral-700"
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
          <input
            type="text"
            placeholder="Rechercher un contact..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-9"
          />
        </div>
      </div>

      {/* Create Modal */}
      <Modal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        title="Nouveau contact"
        footer={
          <div className="flex justify-end gap-3">
            <button
              onClick={() => setShowModal(false)}
              className="px-4 py-2 text-sm font-medium text-neutral-600 bg-neutral-100 rounded-md hover:bg-neutral-200 transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleCreate}
              disabled={creating || !form.full_name.trim()}
              className="btn-primary flex items-center gap-2 disabled:opacity-50"
            >
              {creating && <Loader2 className="w-4 h-4 animate-spin" />}
              Créer le contact
            </button>
          </div>
        }
      >
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  Type
                </label>
                <div className="flex gap-3">
                  {[
                    { value: "natural", label: "Personne physique" },
                    { value: "legal", label: "Personne morale" },
                  ].map((t) => (
                    <button
                      key={t.value}
                      onClick={() => setForm((f) => ({ ...f, type: t.value as "natural" | "legal" }))}
                      className={`flex-1 px-4 py-2 rounded-md text-sm font-medium border transition-all ${
                        form.type === t.value
                          ? "border-accent bg-accent-50 text-accent-700"
                          : "border-neutral-200 text-neutral-600 hover:border-neutral-300"
                      }`}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-700 mb-1">
                  {form.type === "natural" ? "Nom complet" : "Raison sociale"}
                </label>
                <input
                  type="text"
                  value={form.full_name}
                  onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                  placeholder={form.type === "natural" ? "Jean Dupont" : "SA Immobel"}
                  className="input"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
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
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Téléphone
                  </label>
                  <input
                    type="tel"
                    value={form.phone_e164}
                    onChange={(e) => setForm((f) => ({ ...f, phone_e164: e.target.value }))}
                    placeholder="+32470123456"
                    className="input"
                  />
                </div>
              </div>
              {form.type === "legal" && (
                <div>
                  <label className="block text-sm font-medium text-neutral-700 mb-1">
                    Numéro BCE
                  </label>
                  <input
                    type="text"
                    value={form.bce_number}
                    onChange={(e) => setForm((f) => ({ ...f, bce_number: e.target.value }))}
                    placeholder="0123.456.789"
                    className="input"
                  />
                </div>
              )}
            </div>
      </Modal>

      {/* Table */}
      <div className="bg-white rounded-lg shadow-subtle overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-neutral-200">
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Nom
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Type
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Email
              </th>
              <th className="text-left px-6 py-3 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                Téléphone
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4}>
                  <div className="px-6 py-16 text-center">
                    <EmptyState title="Aucun contact trouvé" />
                    {!searchQuery && !typeFilter && (
                      <button
                        onClick={() => setShowModal(true)}
                        className="btn-primary mt-4"
                      >
                        <Plus className="w-4 h-4 inline mr-1.5" />
                        Nouveau contact
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.id}
                  onClick={() => router.push(`/dashboard/contacts/${c.id}`)}
                  className="hover:bg-neutral-50 transition-colors duration-150 cursor-pointer"
                >
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-accent-50 flex items-center justify-center text-xs font-semibold text-accent flex-shrink-0">
                        {getInitials(c.full_name)}
                      </div>
                      <span className="text-sm font-medium text-neutral-900">
                        {c.full_name}
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                        TYPE_STYLES[c.type] || "bg-neutral-100 text-neutral-600"
                      }`}
                    >
                      {TYPE_LABELS[c.type] || c.type}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    {c.email ? (
                      <span className="flex items-center gap-1.5 text-sm text-accent">
                        <Mail className="w-3.5 h-3.5" />
                        {c.email}
                      </span>
                    ) : (
                      <span className="text-sm text-neutral-400">&mdash;</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {c.phone_e164 ? (
                      <span className="flex items-center gap-1.5 text-sm text-accent">
                        <Phone className="w-3.5 h-3.5" />
                        {c.phone_e164}
                      </span>
                    ) : (
                      <span className="text-sm text-neutral-400">&mdash;</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
