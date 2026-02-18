"use client";

import { ConflictDetail } from "@/lib/sentinel/api-client";
import ConflictBadge from "./ConflictBadge";
import SeverityIndicator from "./SeverityIndicator";
import { formatDistanceToNow } from "date-fns";
import { fr } from "date-fns/locale";
import { Users, Calendar, AlertTriangle } from "lucide-react";

interface ConflictCardProps {
  conflict: ConflictDetail & { status?: "active" | "resolved" | "dismissed"; resolved_at?: string | null };
  onClick?: () => void;
  className?: string;
}

export default function ConflictCard({
  conflict,
  onClick,
  className = "",
}: ConflictCardProps) {
  const status = conflict.status ?? "active";

  const statusColors = {
    active: "border-red-500 bg-red-50 dark:bg-red-950/20",
    resolved: "border-green-500 bg-green-50 dark:bg-green-950/20",
    dismissed: "border-gray-400 bg-gray-50 dark:bg-gray-800/20",
  };

  const statusLabels = {
    active: "Actif",
    resolved: "Résolu",
    dismissed: "Rejeté",
  };

  return (
    <div
      onClick={onClick}
      className={`p-4 rounded-lg border-l-4 ${statusColors[status]} cursor-pointer hover:shadow-md transition-shadow ${className}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <AlertTriangle
            className={`w-5 h-5 ${
              conflict.severity_score >= 90
                ? "text-red-600"
                : conflict.severity_score >= 75
                ? "text-orange-500"
                : "text-yellow-500"
            }`}
          />
          <ConflictBadge type={conflict.conflict_type} />
        </div>
        <span className="text-xs font-medium text-gray-600 dark:text-gray-400">
          {statusLabels[status]}
        </span>
      </div>

      {/* Description */}
      <p className="text-sm text-gray-900 dark:text-gray-100 mb-3 line-clamp-2">
        {conflict.description}
      </p>

      {/* Severity */}
      <div className="mb-3">
        <SeverityIndicator score={conflict.severity_score} size="sm" />
      </div>

      {/* Entities */}
      <div className="flex items-center gap-2 mb-2 text-xs text-gray-600 dark:text-gray-400">
        <Users className="w-4 h-4" />
        <span>
          {conflict.entities_involved.map((e) => e.name).join(" • ")}
        </span>
      </div>

      {/* Timestamp */}
      <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-500">
        <Calendar className="w-4 h-4" />
        <span>
          Détecté{" "}
          {formatDistanceToNow(new Date(conflict.detected_at), {
            addSuffix: true,
            locale: fr,
          })}
        </span>
      </div>
    </div>
  );
}
