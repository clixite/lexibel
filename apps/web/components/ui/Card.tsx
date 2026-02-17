"use client";

import { ReactNode } from "react";

export interface CardProps {
  children: ReactNode;
  hover?: boolean;
  className?: string;
  header?: ReactNode;
  footer?: ReactNode;
  onClick?: () => void;
}

export default function Card({
  children,
  hover = false,
  className = "",
  header,
  footer,
  onClick,
}: CardProps) {
  const baseClasses = "bg-white rounded shadow-sm transition-shadow duration-150";
  const hoverClasses = hover ? "hover:shadow-md" : "";
  const clickableClasses = onClick ? "cursor-pointer" : "";

  return (
    <div
      className={`${baseClasses} ${hoverClasses} ${clickableClasses} ${className}`}
      onClick={onClick}
    >
      {header && (
        <div className="px-6 py-4 border-b border-neutral-200">
          {header}
        </div>
      )}

      <div className="p-6">
        {children}
      </div>

      {footer && (
        <div className="px-6 py-4 border-t border-neutral-200 bg-neutral-50 rounded-b">
          {footer}
        </div>
      )}
    </div>
  );
}
