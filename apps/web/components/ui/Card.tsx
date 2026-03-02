"use client";

import { ReactNode } from "react";

export interface CardProps {
  children: ReactNode;
  hover?: boolean;
  className?: string;
  header?: ReactNode;
  footer?: ReactNode;
  onClick?: () => void;
  variant?: "default" | "flush" | "accent-top";
}

export default function Card({
  children,
  hover = false,
  className = "",
  header,
  footer,
  onClick,
  variant = "default",
}: CardProps) {
  const baseClasses = "bg-white rounded-sm transition-shadow duration-150 overflow-hidden";
  const hoverClasses = hover ? "hover:shadow-md" : "";
  const clickableClasses = onClick ? "cursor-pointer" : "";

  return (
    <div
      className={`${baseClasses} ${hoverClasses} ${clickableClasses} ${className}`}
      style={{ boxShadow: "var(--shadow-card)" }}
      onClick={onClick}
    >
      {variant === "accent-top" && (
        <div className="h-[3px] bg-accent rounded-t-sm" />
      )}

      {header && (
        <div className="px-6 py-4 border-b border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface-raised))]">
          {header}
        </div>
      )}

      {variant === "flush" ? children : (
        <div className="p-6">
          {children}
        </div>
      )}

      {footer && (
        <div className="px-6 py-4 border-t border-[rgb(var(--color-border))] bg-[rgb(var(--color-surface-raised))] rounded-b-sm">
          {footer}
        </div>
      )}
    </div>
  );
}
