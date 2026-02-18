"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/lib/useAuth";
import { UserPlus, Loader2, XCircle, Check } from "lucide-react";
import { apiFetch } from "@/lib/api";

interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
}

const ROLES = [
  { value: "partner", label: "Associé" },
  { value: "associate", label: "Avocat" },
  { value: "junior", label: "Stagiaire" },
  { value: "secretary", label: "Secrétaire" },
  { value: "accountant", label: "Comptable" },
  { value: "admin", label: "Admin" },
];

export default function UsersManager() {
  const { accessToken, tenantId } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteFullName, setInviteFullName] = useState("");
  const [inviteRole, setInviteRole] = useState("junior");
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const fetchUsers = async () => {
    if (!accessToken) return;
    setLoading(true);
    try {
      const data = await apiFetch<{ users: User[] }>("/admin/users", accessToken, { tenantId });
      setUsers(data.users || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [accessToken]);

  const inviteUser = async () => {
    if (!inviteEmail.trim() || !accessToken) return;
    setInviting(true);
    setError("");
    setSuccess("");

    try {
      await apiFetch("/admin/users/invite", accessToken, {
        tenantId,
        method: "POST",
        body: JSON.stringify({
          email: inviteEmail,
          role: inviteRole,
          full_name: inviteFullName || inviteEmail.split("@")[0],
        }),
      });
      setSuccess(`Utilisateur ${inviteEmail} créé avec succès`);
      setInviteEmail("");
      setInviteFullName("");
      fetchUsers();
      setTimeout(() => setSuccess(""), 3000);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setInviting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Success toast */}
      {success && (
        <div className="bg-success-50 border border-success-200 text-success-700 px-4 py-3 rounded-md text-sm flex items-center gap-2">
          <Check className="w-4 h-4" />
          {success}
        </div>
      )}

      {/* Invite Form */}
      <div className="card">
        <h2 className="text-base font-semibold text-neutral-900 mb-4">
          Inviter un utilisateur
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              placeholder="avocat@cabinet.be"
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Nom complet
            </label>
            <input
              type="text"
              value={inviteFullName}
              onChange={(e) => setInviteFullName(e.target.value)}
              placeholder="Jean Dupont"
              className="input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-neutral-700 mb-1">
              Rôle
            </label>
            <select
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="input"
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
            className="btn-primary flex items-center justify-center gap-2 disabled:opacity-50"
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
          <p className="mt-2 text-sm text-danger">{error}</p>
        )}
      </div>

      {/* Users List */}
      <div className="card">
        <h2 className="text-base font-semibold text-neutral-900 mb-4">
          Utilisateurs {users.length > 0 && `(${users.length})`}
        </h2>
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-neutral-400" />
          </div>
        ) : users.length === 0 ? (
          <p className="text-sm text-neutral-500 py-4">Aucun utilisateur.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-neutral-200">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Nom
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Email
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Rôle
                  </th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-neutral-500 uppercase tracking-wider">
                    Statut
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-100">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-neutral-50 transition-colors">
                    <td className="py-3 px-4 font-medium text-neutral-900">
                      {u.full_name}
                    </td>
                    <td className="py-3 px-4 text-neutral-600">{u.email}</td>
                    <td className="py-3 px-4">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-accent-50 text-accent-700">
                        {ROLES.find((r) => r.value === u.role)?.label || u.role}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          u.is_active
                            ? "bg-success-50 text-success-700"
                            : "bg-warning-50 text-warning-700"
                        }`}
                      >
                        {u.is_active ? "Actif" : "Inactif"}
                      </span>
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
