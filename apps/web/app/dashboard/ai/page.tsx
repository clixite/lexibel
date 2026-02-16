"use client";

import Link from "next/link";
import { Shield, Activity, FileText, Cpu } from "lucide-react";

const AI_CARDS = [
  {
    title: "Due Diligence",
    description:
      "Analyse automatisée des entités : sanctions, registre BCE/KBO, drapeaux de risque.",
    href: "/dashboard/ai/due-diligence",
    icon: Shield,
    color: "text-red-500",
    bgColor: "bg-red-50",
  },
  {
    title: "Radar Émotionnel",
    description:
      "Analyse du ton des communications. Détection d'escalade et seuils juridiques.",
    href: "/dashboard/ai/emotional-radar",
    icon: Activity,
    color: "text-amber-500",
    bgColor: "bg-amber-50",
  },
  {
    title: "Assemblage Documents",
    description:
      "Génération de documents juridiques à partir de modèles : mise en demeure, conclusions, requête, citation.",
    href: "/dashboard/ai/documents",
    icon: FileText,
    color: "text-blue-500",
    bgColor: "bg-blue-50",
  },
  {
    title: "vLLM & LoRA",
    description:
      "Infrastructure LLM locale avec adaptateurs LoRA spécialisés : rédaction, résumé, analyse.",
    href: "/dashboard/ai/vllm",
    icon: Cpu,
    color: "text-purple-500",
    bgColor: "bg-purple-50",
  },
];

export default function AIHubPage() {
  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Hub IA</h1>
        <p className="text-slate-500 mt-1">
          Agents intelligents et outils d&apos;analyse pour votre pratique
          juridique.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {AI_CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="block border border-slate-200 rounded-xl p-6 hover:shadow-lg transition-shadow bg-white"
          >
            <div className="flex items-start gap-4">
              <div
                className={`w-12 h-12 rounded-lg ${card.bgColor} flex items-center justify-center flex-shrink-0`}
              >
                <card.icon className={`w-6 h-6 ${card.color}`} />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-slate-900">
                  {card.title}
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  {card.description}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}
