"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "ghost-danger";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: ReactNode;
  children?: ReactNode;
}

export default function Button({
  variant = "primary",
  size = "md",
  loading = false,
  icon,
  children,
  className = "",
  disabled,
  ...props
}: ButtonProps) {
  const baseClasses =
    "inline-flex items-center justify-center gap-2 font-semibold rounded-sm transition-colors duration-150 focus:outline-none focus:ring-2 focus:ring-accent/30 focus:ring-offset-2";

  const variantClasses = {
    primary:
      "bg-accent text-[#0F172A] hover:bg-accent/90 shadow-sm",
    secondary:
      "border border-[rgb(var(--color-border))] bg-white text-[rgb(var(--color-text-primary))] hover:bg-[rgb(var(--color-surface-raised))] hover:border-[rgb(var(--color-primary))/30]",
    ghost:
      "bg-transparent text-[rgb(var(--color-text-secondary))] hover:bg-[rgb(var(--color-surface-raised))] hover:text-[rgb(var(--color-text-primary))]",
    danger:
      "bg-danger-700 text-white hover:bg-danger-800 shadow-sm",
    "ghost-danger":
      "bg-transparent text-danger-700 hover:bg-danger-50 hover:text-danger-800",
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-xs",
    md: "px-4 py-2 text-sm",
    lg: "px-6 py-2.5 text-base",
  };

  const disabledClasses = disabled || loading ? "opacity-50 cursor-not-allowed" : "";

  return (
    <button
      className={`${baseClasses} ${variantClasses[variant]} ${sizeClasses[size]} ${disabledClasses} ${className}`}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-4 w-4 animate-spin" />
      ) : icon ? (
        <span className="inline-flex">{icon}</span>
      ) : null}
      {children}
    </button>
  );
}
