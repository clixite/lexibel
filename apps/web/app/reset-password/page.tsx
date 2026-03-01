"use client";

import { useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Scale, Loader2, AlertCircle, CheckCircle2, Eye, EyeOff } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caract\u00e8res.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    if (!token) {
      setError("Lien de r\u00e9initialisation invalide. Veuillez r\u00e9essayer.");
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "Erreur serveur" }));
        throw new Error(
          typeof body.detail === "string" ? body.detail : "Erreur serveur"
        );
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Une erreur est survenue");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-xl p-8">
      <h2 className="text-xl font-display font-semibold text-neutral-900 mb-2">
        R&eacute;initialiser le mot de passe
      </h2>
      <p className="text-sm text-neutral-500 mb-6">
        Choisissez un nouveau mot de passe pour votre compte.
      </p>

      {success ? (
        <div>
          <div className="flex items-start gap-3 p-4 text-sm text-success-700 bg-success-50 border border-success-200 rounded-md">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Mot de passe modifi&eacute;</p>
              <p className="mt-1 text-success-600">
                Votre mot de passe a &eacute;t&eacute; r&eacute;initialis&eacute; avec succ&egrave;s.
                Vous pouvez maintenant vous connecter.
              </p>
            </div>
          </div>
          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="inline-flex items-center justify-center w-full py-2.5 px-4 bg-accent hover:bg-accent-600 text-white font-medium rounded-md transition-colors"
            >
              Se connecter
            </Link>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit}>
          {error && (
            <div className="flex items-center gap-2 p-3 mb-4 text-sm text-danger-700 bg-danger-50 border border-danger-200 rounded-md">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="mb-4">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Nouveau mot de passe
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input w-full pr-10"
                placeholder="Minimum 8 caract\u00e8res"
                autoComplete="new-password"
                required
                minLength={8}
                disabled={loading}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-600 transition-colors"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="w-4 h-4" />
                ) : (
                  <Eye className="w-4 h-4" />
                )}
              </button>
            </div>
          </div>

          <div className="mb-4">
            <label
              htmlFor="confirm-password"
              className="block text-sm font-medium text-neutral-700 mb-1"
            >
              Confirmer le mot de passe
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="input w-full"
              placeholder="Confirmez votre mot de passe"
              autoComplete="new-password"
              required
              minLength={8}
              disabled={loading}
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 bg-accent hover:bg-accent-600 text-white font-medium rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                R&eacute;initialisation...
              </>
            ) : (
              "R&eacute;initialiser le mot de passe"
            )}
          </button>
        </form>
      )}

      {!success && (
        <div className="mt-6 text-center">
          <Link
            href="/login"
            className="text-sm text-accent hover:text-accent-600 transition-colors"
          >
            &larr; Retour &agrave; la connexion
          </Link>
        </div>
      )}
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden">
      {/* Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-950 via-primary-900 to-primary-800" />
      <div className="absolute inset-0 opacity-20 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-accent/30 via-transparent to-transparent" />

      <div className="w-full max-w-md relative z-10">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-accent shadow-lg shadow-accent/20 mb-4">
            <Scale className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-display font-bold text-white">LexiBel</h1>
          <p className="text-neutral-400 mt-1 text-sm font-sans">
            L&apos;&Eacute;cosyst&egrave;me Juridique Intelligent
          </p>
        </div>

        {/* Card */}
        <Suspense
          fallback={
            <div className="bg-white rounded-lg shadow-xl p-8 flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-accent" />
            </div>
          }
        >
          <ResetPasswordForm />
        </Suspense>
      </div>
    </div>
  );
}
