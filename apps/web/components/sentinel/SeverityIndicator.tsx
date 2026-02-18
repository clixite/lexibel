"use client";

interface SeverityIndicatorProps {
  score: number;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function getSeverityColor(score: number): string {
  if (score >= 90) return "bg-red-600";
  if (score >= 75) return "bg-orange-500";
  if (score >= 60) return "bg-yellow-500";
  if (score >= 40) return "bg-blue-500";
  return "bg-gray-400";
}

function getSeverityLabel(score: number): string {
  if (score >= 90) return "CRITIQUE";
  if (score >= 75) return "TRÈS ÉLEVÉ";
  if (score >= 60) return "ÉLEVÉ";
  if (score >= 40) return "MOYEN";
  return "FAIBLE";
}

export default function SeverityIndicator({
  score,
  showLabel = true,
  size = "md",
  className = "",
}: SeverityIndicatorProps) {
  const color = getSeverityColor(score);
  const label = getSeverityLabel(score);

  const sizeClasses = {
    sm: "h-2",
    md: "h-3",
    lg: "h-4",
  };

  return (
    <div className={`space-y-1 ${className}`}>
      {showLabel && (
        <div className="flex items-center justify-between text-xs">
          <span className="font-medium text-gray-700 dark:text-gray-300">{label}</span>
          <span className="font-semibold text-gray-900 dark:text-white">{score}/100</span>
        </div>
      )}
      <div className={`w-full bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <div
          className={`${color} ${sizeClasses[size]} rounded-full transition-all duration-500`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
