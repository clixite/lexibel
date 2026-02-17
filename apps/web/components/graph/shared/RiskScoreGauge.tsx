import { createRiskColorScale } from "@/lib/graph/graph-utils";

export interface RiskScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
  className?: string;
}

const SIZES = {
  sm: {
    width: 60,
    height: 60,
    strokeWidth: 6,
    fontSize: "text-sm",
  },
  md: {
    width: 100,
    height: 100,
    strokeWidth: 8,
    fontSize: "text-xl",
  },
  lg: {
    width: 140,
    height: 140,
    strokeWidth: 10,
    fontSize: "text-3xl",
  },
};

export default function RiskScoreGauge({
  score,
  size = "md",
  showLabel = true,
  className = "",
}: RiskScoreGaugeProps) {
  const { width, height, strokeWidth, fontSize } = SIZES[size];
  const radius = (width - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const colorScale = createRiskColorScale();
  const color = colorScale(score);

  const getRiskLevel = (score: number): string => {
    if (score >= 75) return "Critique";
    if (score >= 50) return "Élevé";
    if (score >= 25) return "Moyen";
    return "Faible";
  };

  return (
    <div className={`inline-flex flex-col items-center gap-2 ${className}`}>
      <div className="relative" style={{ width, height }}>
        <svg width={width} height={height} className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx={width / 2}
            cy={height / 2}
            r={radius}
            fill="none"
            stroke="#e5e7eb"
            strokeWidth={strokeWidth}
          />
          {/* Progress circle */}
          <circle
            cx={width / 2}
            cy={height / 2}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="transition-all duration-500 ease-in-out"
          />
        </svg>
        {/* Score text */}
        <div className="absolute inset-0 flex items-center justify-center">
          <span
            className={`font-bold ${fontSize}`}
            style={{ color }}
          >
            {Math.round(score)}
          </span>
        </div>
      </div>
      {showLabel && (
        <div className="text-center">
          <p className="text-xs text-neutral-500 font-medium">
            Niveau de risque
          </p>
          <p className="text-sm font-semibold" style={{ color }}>
            {getRiskLevel(score)}
          </p>
        </div>
      )}
    </div>
  );
}
