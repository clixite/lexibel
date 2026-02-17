"use client";

import { ButtonHTMLAttributes, ReactNode } from "react";
import { Loader2 } from "lucide-react";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
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
  const baseClasses = "inline-flex items-center justify-center gap-2 font-medium rounded-lg transition-all duration-normal focus:outline-none focus:ring-2 focus:ring-accent-300 focus:ring-offset-2";

  const variantClasses = {
    primary: "bg-accent text-white hover:bg-accent-700 hover:scale-[1.02] active:scale-[0.98] shadow-sm",
    secondary: "border-2 border-neutral-300 bg-white text-neutral-700 hover:bg-neutral-50 hover:border-neutral-400 active:scale-[0.98]",
    ghost: "bg-transparent text-neutral-700 hover:bg-neutral-100 active:bg-neutral-200",
    danger: "bg-danger text-white hover:bg-danger-700 hover:scale-[1.02] active:scale-[0.98] shadow-sm",
  };

  const sizeClasses = {
    sm: "px-3 py-1.5 text-sm",
    md: "px-4 py-2 text-base",
    lg: "px-6 py-3 text-lg",
  };

  const disabledClasses = disabled || loading ? "opacity-50 cursor-not-allowed hover:scale-100" : "";

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
