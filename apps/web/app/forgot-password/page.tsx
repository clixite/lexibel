"use client";

import { useState } from "react";
import Link from "next/link";
import { Scale, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
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
        <div className="bg-white rounded-lg shadow-xl p-8">
          <h2 className="text-xl font-display font-semibold text-neutral-900 mb-2">
            Mot de passe oubli&eacute;
          </h2>
          <p className="text-sm text-neutral-500 mb-6">
            Entrez votre adresse email pour recevoir un lien de r&eacute;initialisation.
          </p>

          {success ? (
            <div className="flex items-start gap-3 p-4 text-sm text-success-700 bg-success-50 border border-success-200 rounded-md">
              <CheckCircle2 className="w-5 h-5 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium">Email envoy&eacute;</p>
                <p className="mt-1 text-success-600">
                  Si un compte existe avec cette adresse, un lien de
                  r&eacute;initialisation a &eacute;t&eacute; envoy&eacute;.
                  V&eacute;rifiez votre bo&icirc;te de r&eacute;ception.
                </p>
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
                  htmlFor="email"
                  className="block text-sm font-medium text-neutral-700 mb-1"
                >
                  Adresse email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input w-full"
                  placeholder="avocat@cabinet.be"
                  autoComplete="email"
                  required
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
                    Envoi en cours...
                  </>
                ) : (
                  "Envoyer le lien"
                )}
              </button>
            </form>
          )}

          <div className="mt-6 text-center">
            <Link
              href="/login"
              className="text-sm text-accent hover:text-accent-600 transition-colors"
            >
              &larr; Retour &agrave; la connexion
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
