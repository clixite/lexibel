"use client";

import { InputHTMLAttributes, ReactNode } from "react";

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  prefixIcon?: ReactNode;
  suffixIcon?: ReactNode;
}

export default function Input({
  label,
  error,
  prefixIcon,
  suffixIcon,
  className = "",
  ...props
}: InputProps) {
  const hasError = !!error;

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-neutral-700 mb-1.5">
          {label}
        </label>
      )}

      <div className="relative">
        {prefixIcon && (
          <div className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400">
            {prefixIcon}
          </div>
        )}

        <input
          className={`
            w-full px-3 py-2
            border rounded
            text-neutral-900 placeholder:text-neutral-400
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary
            disabled:bg-neutral-50 disabled:cursor-not-allowed disabled:opacity-50
            ${hasError ? "border-danger text-danger focus:ring-danger/20 focus:border-danger" : "border-neutral-300"}
            ${prefixIcon ? "pl-10" : ""}
            ${suffixIcon ? "pr-10" : ""}
            ${className}
          `}
          {...props}
        />

        {suffixIcon && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
            {suffixIcon}
          </div>
        )}
      </div>

      {error && (
        <p className="mt-1.5 text-sm text-danger animate-fade">
          {error}
        </p>
      )}
    </div>
  );
}
