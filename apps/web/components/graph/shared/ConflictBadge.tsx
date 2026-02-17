import { AlertTriangle } from "lucide-react";

export interface ConflictBadgeProps {
  count: number;
  size?: "sm" | "md" | "lg";
  onClick?: () => void;
  className?: string;
}

const SIZES = {
  sm: {
    badge: "px-2 py-0.5 text-xs",
    icon: "w-3 h-3",
  },
  md: {
    badge: "px-2.5 py-1 text-sm",
    icon: "w-4 h-4",
  },
  lg: {
    badge: "px-3 py-1.5 text-base",
    icon: "w-5 h-5",
  },
};

export default function ConflictBadge({
  count,
  size = "md",
  onClick,
  className = "",
}: ConflictBadgeProps) {
  const { badge, icon } = SIZES[size];

  if (count === 0) return null;

  return (
    <button
      onClick={onClick}
      disabled={!onClick}
      className={`inline-flex items-center gap-1.5 ${badge} rounded-full bg-red-100 text-red-700 font-medium hover:bg-red-200 transition-colors ${
        onClick ? "cursor-pointer" : "cursor-default"
      } ${className}`}
      title={`${count} conflit${count > 1 ? "s" : ""} détecté${count > 1 ? "s" : ""}`}
    >
      <AlertTriangle className={icon} />
      <span>{count}</span>
    </button>
  );
}
