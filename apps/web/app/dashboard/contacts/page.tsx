"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Plus, Loader2, Search, UserX, Mail, Phone } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface Contact {
  id: string;
  full_name: string;
  type: string;
  email: string | null;
  phone_e164: string | null;
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
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  useEffect(() => {
    const token = (session?.user as any)?.accessToken;
    if (!token) return;

    apiFetch<ContactListResponse>("/contacts", token)
      .then((data) => setContacts(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [session]);

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

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-accent" />
      </div>
    );
  }

  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((w) => w[0])
      .slice(0, 2)
      .join("")
      .toUpperCase();
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-neutral-900">Contacts</h1>
          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-success-50 text-success-700">
            {contacts.length}
          </span>
        </div>
        <button className="btn-primary flex items-center gap-2">
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

      {error && (
        <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
          {error}
        </div>
      )}

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
                T&eacute;l&eacute;phone
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-neutral-100">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-16 text-center">
                  <UserX className="w-12 h-12 text-neutral-300 mx-auto mb-3" />
                  <p className="text-neutral-500 font-medium">
                    Aucun contact trouv&eacute;
                  </p>
                  <p className="text-neutral-400 text-sm mt-1">
                    {searchQuery || typeFilter
                      ? "Essayez de modifier vos filtres."
                      : "Ajoutez votre premier contact pour commencer."}
                  </p>
                  {!searchQuery && !typeFilter && (
                    <button className="btn-primary mt-4">
                      <Plus className="w-4 h-4 inline mr-1.5" />
                      Nouveau contact
                    </button>
                  )}
                </td>
              </tr>
            ) : (
              filtered.map((c) => (
                <tr
                  key={c.id}
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
                      <a
                        href={`mailto:${c.email}`}
                        className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-600 transition-colors"
                      >
                        <Mail className="w-3.5 h-3.5" />
                        {c.email}
                      </a>
                    ) : (
                      <span className="text-sm text-neutral-400">&mdash;</span>
                    )}
                  </td>
                  <td className="px-6 py-4">
                    {c.phone_e164 ? (
                      <a
                        href={`tel:${c.phone_e164}`}
                        className="flex items-center gap-1.5 text-sm text-accent hover:text-accent-600 transition-colors"
                      >
                        <Phone className="w-3.5 h-3.5" />
                        {c.phone_e164}
                      </a>
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
