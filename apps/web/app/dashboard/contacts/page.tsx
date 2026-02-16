"use client";

import { useSession } from "next-auth/react";
import { useEffect, useState } from "react";
import { Users, Loader2 } from "lucide-react";
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

export default function ContactsPage() {
  const { data: session } = useSession();
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = (session?.user as any)?.accessToken;
    if (!token) return;

    apiFetch<ContactListResponse>("/contacts", token)
      .then((data) => setContacts(data.items))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [session]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-3 mb-6">
        <Users className="w-6 h-6 text-green-600" />
        <h1 className="text-2xl font-bold text-gray-900">Contacts</h1>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg mb-4 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-200 bg-gray-50">
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Nom</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
              <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Téléphone</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {contacts.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center text-sm text-gray-400">
                  Aucun contact trouvé.
                </td>
              </tr>
            ) : (
              contacts.map((c) => (
                <tr key={c.id} className="hover:bg-gray-50 transition-colors">
                  <td className="px-6 py-4 text-sm font-medium text-gray-900">{c.full_name}</td>
                  <td className="px-6 py-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      c.type === "natural"
                        ? "bg-blue-100 text-blue-800"
                        : "bg-purple-100 text-purple-800"
                    }`}>
                      {c.type === "natural" ? "Personne physique" : "Personne morale"}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">{c.email || "—"}</td>
                  <td className="px-6 py-4 text-sm text-gray-500">{c.phone_e164 || "—"}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
