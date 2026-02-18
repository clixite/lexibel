"use client";

import { ConflictType } from "@/lib/sentinel/api-client";

interface ConflictBadgeProps {
  type: ConflictType;
  className?: string;
}

const CONFLICT_LABELS: Record<ConflictType, string> = {
  direct_adversary: "Adversaire Direct",
  director_overlap: "Admin. Commun",
  family_tie: "Lien Familial",
  indirect_ownership: "Propriété Indirecte",
  group_company: "Groupe Société",
  business_partner: "Partenaire Commercial",
  historical_conflict: "Historique",
  professional_overlap: "Conseiller Commun",
};

const CONFLICT_COLORS: Record<
  ConflictType,
  { bg: string; text: string; border: string }
> = {
  direct_adversary: {
    bg: "bg-red-100 dark:bg-red-950",
    text: "text-red-900 dark:text-red-100",
    border: "border-red-300 dark:border-red-700",
  },
  director_overlap: {
    bg: "bg-orange-100 dark:bg-orange-950",
    text: "text-orange-900 dark:text-orange-100",
    border: "border-orange-300 dark:border-orange-700",
  },
  family_tie: {
    bg: "bg-red-100 dark:bg-red-950",
    text: "text-red-900 dark:text-red-100",
    border: "border-red-300 dark:border-red-700",
  },
  indirect_ownership: {
    bg: "bg-amber-100 dark:bg-amber-950",
    text: "text-amber-900 dark:text-amber-100",
    border: "border-amber-300 dark:border-amber-700",
  },
  group_company: {
    bg: "bg-yellow-100 dark:bg-yellow-950",
    text: "text-yellow-900 dark:text-yellow-100",
    border: "border-yellow-300 dark:border-yellow-700",
  },
  business_partner: {
    bg: "bg-yellow-100 dark:bg-yellow-950",
    text: "text-yellow-900 dark:text-yellow-100",
    border: "border-yellow-300 dark:border-yellow-700",
  },
  historical_conflict: {
    bg: "bg-blue-100 dark:bg-blue-950",
    text: "text-blue-900 dark:text-blue-100",
    border: "border-blue-300 dark:border-blue-700",
  },
  professional_overlap: {
    bg: "bg-purple-100 dark:bg-purple-950",
    text: "text-purple-900 dark:text-purple-100",
    border: "border-purple-300 dark:border-purple-700",
  },
};

export default function ConflictBadge({ type, className = "" }: ConflictBadgeProps) {
  const colors = CONFLICT_COLORS[type];

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors.bg} ${colors.text} ${colors.border} ${className}`}
    >
      {CONFLICT_LABELS[type]}
    </span>
  );
}
