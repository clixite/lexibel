import { AlertCircle, AlertTriangle, Info, XCircle } from "lucide-react";
import { getSeverityColor, getSeverityLabel } from "@/lib/graph/graph-utils";

export interface SeverityIndicatorProps {
  severity: "low" | "medium" | "high" | "critical";
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

const ICON_SIZES = {
  sm: "w-4 h-4",
  md: "w-5 h-5",
  lg: "w-6 h-6",
};

const TEXT_SIZES = {
  sm: "text-xs",
  md: "text-sm",
  lg: "text-base",
};

const SEVERITY_ICONS = {
  low: Info,
  medium: AlertCircle,
  high: AlertTriangle,
  critical: XCircle,
};

const SEVERITY_BG_COLORS = {
  low: "bg-green-50",
  medium: "bg-orange-50",
  high: "bg-red-50",
  critical: "bg-red-100",
};

const SEVERITY_TEXT_COLORS = {
  low: "text-green-700",
  medium: "text-orange-700",
  high: "text-red-700",
  critical: "text-red-900",
};

export default function SeverityIndicator({
  severity,
  size = "md",
  showLabel = true,
  className = "",
}: SeverityIndicatorProps) {
  const Icon = SEVERITY_ICONS[severity];
  const label = getSeverityLabel(severity);

  return (
    <div
      className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-lg ${SEVERITY_BG_COLORS[severity]} ${className}`}
    >
      <Icon
        className={`${ICON_SIZES[size]} ${SEVERITY_TEXT_COLORS[severity]}`}
      />
      {showLabel && (
        <span
          className={`font-medium ${TEXT_SIZES[size]} ${SEVERITY_TEXT_COLORS[severity]}`}
        >
          {label}
        </span>
      )}
    </div>
  );
}
