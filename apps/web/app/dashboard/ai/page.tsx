"use client";

import Link from "next/link";
import { Shield, Activity, FileText, Cpu } from "lucide-react";

const AI_CARDS = [
  {
    title: "Due Diligence",
    description:
      "Analyse automatis\u00e9e des entit\u00e9s : sanctions, registre BCE/KBO, drapeaux de risque.",
    href: "/dashboard/ai/due-diligence",
    icon: Shield,
    color: "text-danger",
    bgColor: "bg-danger-50",
  },
  {
    title: "Radar \u00c9motionnel",
    description:
      "Analyse du ton des communications. D\u00e9tection d\u2019escalade et seuils juridiques.",
    href: "/dashboard/ai/emotional-radar",
    icon: Activity,
    color: "text-warning",
    bgColor: "bg-warning-50",
  },
  {
    title: "Assemblage Documents",
    description:
      "G\u00e9n\u00e9ration de documents juridiques \u00e0 partir de mod\u00e8les : mise en demeure, conclusions, requ\u00eate, citation.",
    href: "/dashboard/ai/documents",
    icon: FileText,
    color: "text-accent",
    bgColor: "bg-accent-50",
  },
  {
    title: "vLLM & LoRA",
    description:
      "Infrastructure LLM locale avec adaptateurs LoRA sp\u00e9cialis\u00e9s : r\u00e9daction, r\u00e9sum\u00e9, analyse.",
    href: "/dashboard/ai/vllm",
    icon: Cpu,
    color: "text-purple-500",
    bgColor: "bg-purple-50",
  },
];

export default function AIHubPage() {
  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-neutral-900">Hub IA</h1>
        <p className="text-neutral-500 mt-1 text-sm">
          Agents intelligents et outils d&apos;analyse pour votre pratique
          juridique.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {AI_CARDS.map((card) => (
          <Link
            key={card.href}
            href={card.href}
            className="block bg-white rounded-lg shadow-subtle p-6 hover:shadow-medium hover:-translate-y-0.5 transition-all duration-150"
          >
            <div className="flex items-start gap-4">
              <div
                className={`w-12 h-12 rounded-md ${card.bgColor} flex items-center justify-center flex-shrink-0`}
              >
                <card.icon className={`w-6 h-6 ${card.color}`} />
              </div>
              <div>
                <h2 className="text-base font-semibold text-neutral-900">
                  {card.title}
                </h2>
                <p className="text-sm text-neutral-500 mt-1">
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
