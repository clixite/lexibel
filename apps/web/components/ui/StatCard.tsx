"use client";

import { TrendingUp, TrendingDown } from "lucide-react";

export interface StatCardProps {
  title: string;
  value: string | number;
  icon: React.ReactNode;
  trend?: {
    value: number;
    label: string;
  };
  color?: "accent" | "success" | "warning" | "error";
}

export default function StatCard({
  title,
  value,
  icon,
  trend,
  color = "accent",
}: StatCardProps) {
  const stripClasses = {
    accent: "bg-accent",
    success: "bg-success-600",
    warning: "bg-warning-600",
    error: "bg-danger-600",
  };

  const iconTextClasses = {
    accent: "text-accent-600",
    success: "text-success-600",
    warning: "text-warning-600",
    error: "text-danger-600",
  };

  const isPositive = trend && trend.value >= 0;

  return (
    <div
      className="bg-white rounded-sm relative overflow-hidden p-5"
      style={{ boxShadow: "var(--shadow-card)" }}
    >
      {/* Color accent strip */}
      <div
        className={`absolute left-0 inset-y-0 w-[3px] ${stripClasses[color]}`}
      />

      {/* Label + icon row */}
      <div className="flex items-center justify-between mb-3 pl-2">
        <span className="label-overline">{title}</span>
        <span className={`${iconTextClasses[color]}`}>{icon}</span>
      </div>

      {/* Value */}
      <div className="pl-2">
        <p
          className="leading-none tracking-tight text-[rgb(var(--color-text-primary))]"
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "1.875rem",
            fontWeight: 700,
          }}
        >
          {value}
        </p>

        {trend && (
          <div className="flex items-center gap-1 mt-2">
            {isPositive ? (
              <TrendingUp className="w-3 h-3 text-success-600" />
            ) : (
              <TrendingDown className="w-3 h-3 text-danger-600" />
            )}
            <span
              className={`text-xs font-medium ${isPositive ? "text-success-600" : "text-danger-600"}`}
            >
              {Math.abs(trend.value)}%
            </span>
            <span className="text-xs text-[rgb(var(--color-text-secondary))]">
              {trend.label}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
