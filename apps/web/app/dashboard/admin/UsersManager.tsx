"use client";

import { useState, useEffect } from "react";
import { UserPlus, Loader2, XCircle } from "lucide-react";

interface User {
  id: string;
  email: string;
  role: string;
  status: string;
  invited_at?: string;
}

const ROLES = [
  { value: "admin", label: "Admin" },
  { value: "lawyer", label: "Avocat" },
  { value: "paralegal", label: "Paralegal" },
  { value: "secretary", label: "Secrétaire" },
  { value: "accountant", label: "Comptable" },
];

export default function UsersManager() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("lawyer");
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const apiUrl =
    process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${apiUrl}/admin/users`, {
        credentials: "include",
      });
      if (res.ok) {
        const data = await res.json();
        setUsers(data.users || []);
      }
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const inviteUser = async () => {
    if (!inviteEmail.trim()) return;
    setInviting(true);
    setError("");
    setSuccess("");

    try {
      const res = await fetch(`${apiUrl}/admin/users/invite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `Erreur ${res.status}`);
      }
      setSuccess(`Invitation envoyée à ${inviteEmail}`);
      setInviteEmail("");
      fetchUsers();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Erreur inconnue");
    } finally {
      setInviting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Invite Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">Inviter un utilisateur</h2>
        <div className="flex gap-3 items-end">
          <div className="flex-1">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="avocat@cabinet.be"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <div className="w-40">
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Rôle
            </label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
          </div>
          <button
            onClick={inviteUser}
            disabled={inviting || !inviteEmail.trim()}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
          >
            {inviting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <UserPlus className="w-4 h-4" />
            )}
            Inviter
          </button>
        </div>
        {error && (
          <p className="mt-2 text-sm text-red-600">{error}</p>
        )}
        {success && (
          <p className="mt-2 text-sm text-green-600">{success}</p>
        )}
      </div>

      {/* Users List */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <h2 className="text-lg font-semibold mb-4">
          Utilisateurs {users.length > 0 && `(${users.length})`}
        </h2>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
          </div>
        ) : users.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">Aucun utilisateur.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Email
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Rôle
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Statut
                  </th>
                  <th className="text-left py-2 px-3 font-medium text-slate-600">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-slate-100">
                    <td className="py-2 px-3">{u.email}</td>
                    <td className="py-2 px-3">
                      <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700">
                        {u.role}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <span
                        className={`px-2 py-0.5 rounded text-xs font-medium ${
                          u.status === "active"
                            ? "bg-green-50 text-green-600"
                            : "bg-amber-50 text-amber-600"
                        }`}
                      >
                        {u.status}
                      </span>
                    </td>
                    <td className="py-2 px-3">
                      <button className="text-red-500 hover:text-red-700">
                        <XCircle className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
