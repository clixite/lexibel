"use client";

import { useSession } from "next-auth/react";
import { useState } from "react";
import {
  FileText,
  ChevronRight,
  Loader2,
  Download,
  Copy,
  Briefcase,
} from "lucide-react";
import { apiFetch } from "@/lib/api";

const TEMPLATES = [
  {
    id: "mise-en-demeure",
    label: "Mise en demeure",
    description:
      "Lettre formelle de mise en demeure avec rappel des obligations et d\u00e9lai de r\u00e9ponse.",
    icon: "md",
  },
  {
    id: "conclusions",
    label: "Conclusions",
    description:
      "Conclusions pour proc\u00e9dure civile avec structure en fait et en droit.",
    icon: "cc",
  },
  {
    id: "requete",
    label: "Requ\u00eate",
    description:
      "Requ\u00eate unilat\u00e9rale ou contradictoire devant le tribunal comp\u00e9tent.",
    icon: "rq",
  },
  {
    id: "citation",
    label: "Citation",
    description:
      "Acte introductif d\u2019instance avec indication du tribunal et de la date d\u2019audience.",
    icon: "ct",
  },
  {
    id: "contrat",
    label: "Contrat type",
    description:
      "Contrat g\u00e9n\u00e9rique avec clauses standards : objet, dur\u00e9e, r\u00e9siliation, juridiction.",
    icon: "co",
  },
  {
    id: "pv-assemblee",
    label: "PV d\u2019assembl\u00e9e",
    description:
      "Proc\u00e8s-verbal d\u2019assembl\u00e9e g\u00e9n\u00e9rale (SA, SRL) avec ordre du jour et r\u00e9solutions.",
    icon: "pv",
  },
];

interface GenerateResponse {
  text: string;
  sources: any[];
  model: string;
  tokens_used: number;
  has_uncited_claims: boolean;
}

export default function DocumentsPage() {
  const { data: session } = useSession();
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);
  const [caseId, setCaseId] = useState("");
  const [instructions, setInstructions] = useState("");
  const [generatedText, setGeneratedText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleGenerate = async () => {
    const token = (session?.user as any)?.accessToken;
    if (!token || !selectedTemplate) return;

    const template = TEMPLATES.find((t) => t.id === selectedTemplate);
    if (!template) return;

    setLoading(true);
    setError(null);
    setGeneratedText("");

    const prompt = `G\u00e9n\u00e8re un document juridique belge de type "${template.label}".${
      instructions ? ` Instructions suppl\u00e9mentaires : ${instructions}` : ""
    } R\u00e9dige en fran\u00e7ais juridique belge, avec les formules d\u2019usage.`;

    try {
      const data = await apiFetch<GenerateResponse>("/ai/generate", token, {
        method: "POST",
        body: JSON.stringify({
          prompt,
          case_id: caseId.trim() || undefined,
          max_tokens: 2000,
        }),
      });
      setGeneratedText(data.text);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(generatedText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-neutral-900">
          Assemblage Documents
        </h1>
        <p className="text-neutral-500 text-sm mt-1">
          G&eacute;n&eacute;rez des documents juridiques &agrave; partir de
          mod&egrave;les et du contexte de vos dossiers.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Template selection + params */}
        <div className="lg:col-span-1 space-y-4">
          {/* Template grid */}
          <div className="bg-white rounded-lg shadow-subtle p-4">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">
              Mod&egrave;le
            </h3>
            <div className="space-y-2">
              {TEMPLATES.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setSelectedTemplate(t.id)}
                  className={`w-full flex items-center gap-3 p-3 rounded-md text-left transition-all duration-150 ${
                    selectedTemplate === t.id
                      ? "bg-accent-50 border border-accent-200"
                      : "hover:bg-neutral-50 border border-transparent"
                  }`}
                >
                  <div
                    className={`w-9 h-9 rounded-md flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                      selectedTemplate === t.id
                        ? "bg-accent text-white"
                        : "bg-neutral-100 text-neutral-600"
                    }`}
                  >
                    {t.icon.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-neutral-900">
                      {t.label}
                    </p>
                    <p className="text-xs text-neutral-500 truncate">
                      {t.description}
                    </p>
                  </div>
                  {selectedTemplate === t.id && (
                    <ChevronRight className="w-4 h-4 text-accent flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Parameters */}
          <div className="bg-white rounded-lg shadow-subtle p-4">
            <h3 className="text-sm font-semibold text-neutral-900 mb-3">
              Param&egrave;tres
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">
                  Dossier li&eacute; (optionnel)
                </label>
                <div className="relative">
                  <Briefcase className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neutral-400" />
                  <input
                    type="text"
                    value={caseId}
                    onChange={(e) => setCaseId(e.target.value)}
                    placeholder="UUID du dossier"
                    className="input pl-9 text-sm"
                  />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-600 mb-1">
                  Instructions
                </label>
                <textarea
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                  placeholder="Ex: Adresser &agrave; SA Immobel, d&eacute;lai de 15 jours, mentionner l'article 1382..."
                  rows={4}
                  className="input text-sm resize-none"
                />
              </div>
              <button
                onClick={handleGenerate}
                disabled={!selectedTemplate || loading}
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                {loading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <FileText className="w-4 h-4" />
                )}
                G&eacute;n&eacute;rer le document
              </button>
            </div>
          </div>
        </div>

        {/* Right: Generated output */}
        <div className="lg:col-span-2">
          {error && (
            <div className="bg-danger-50 border border-danger-200 text-danger-700 px-4 py-3 rounded-md mb-4 text-sm">
              {error}
            </div>
          )}

          {generatedText ? (
            <div className="bg-white rounded-lg shadow-subtle">
              <div className="flex items-center justify-between px-5 py-3 border-b border-neutral-200">
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-accent" />
                  <span className="text-sm font-medium text-neutral-900">
                    {TEMPLATES.find((t) => t.id === selectedTemplate)?.label}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopy}
                    className="btn-secondary flex items-center gap-1.5 px-3 py-1.5 text-xs"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    {copied ? "Copi\u00e9 !" : "Copier"}
                  </button>
                  <button className="btn-secondary flex items-center gap-1.5 px-3 py-1.5 text-xs">
                    <Download className="w-3.5 h-3.5" />
                    Exporter
                  </button>
                </div>
              </div>
              <div className="p-6">
                <div className="prose prose-sm max-w-none text-neutral-800 whitespace-pre-wrap leading-relaxed">
                  {generatedText}
                </div>
              </div>
            </div>
          ) : loading ? (
            <div className="bg-white rounded-lg shadow-subtle px-6 py-20 text-center">
              <Loader2 className="w-10 h-10 animate-spin text-accent mx-auto mb-4" />
              <p className="text-neutral-900 font-medium">
                G&eacute;n&eacute;ration en cours...
              </p>
              <p className="text-neutral-500 text-sm mt-1">
                Analyse du contexte et r&eacute;daction du document.
              </p>
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow-subtle px-6 py-20 text-center">
              <div className="w-16 h-16 rounded-lg bg-accent-50 flex items-center justify-center mx-auto mb-5">
                <FileText className="w-8 h-8 text-accent" />
              </div>
              <h2 className="text-lg font-semibold text-neutral-900 mb-2">
                Aper&ccedil;u du document
              </h2>
              <p className="text-neutral-500 text-sm max-w-sm mx-auto">
                S&eacute;lectionnez un mod&egrave;le, ajoutez vos instructions
                puis cliquez sur &laquo; G&eacute;n&eacute;rer &raquo; pour
                cr&eacute;er votre document.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
