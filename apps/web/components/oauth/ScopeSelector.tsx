"use client";

import { Check } from "lucide-react";

export interface Scope {
  id: string;
  name: string;
  description: string;
  required: boolean;
}

interface ScopeSelectorProps {
  scopes: Scope[];
  selectedScopes: string[];
  onToggle: (scopeId: string) => void;
}

export function ScopeSelector({
  scopes,
  selectedScopes,
  onToggle,
}: ScopeSelectorProps) {
  return (
    <div className="space-y-3">
      {scopes.map((scope) => {
        const isSelected = selectedScopes.includes(scope.id);

        return (
          <button
            key={scope.id}
            onClick={() => !scope.required && onToggle(scope.id)}
            disabled={scope.required}
            className={`
              w-full p-4 rounded-lg border transition-all duration-200 text-left
              ${
                isSelected
                  ? "border-warm-gold-500 bg-warm-gold-50/5"
                  : "border-deep-slate-700 hover:border-deep-slate-600"
              }
              ${scope.required ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
            `}
          >
            <div className="flex items-start gap-3">
              {/* Checkbox */}
              <div
                className={`
                  mt-0.5 w-5 h-5 rounded border-2 flex items-center justify-center transition-colors
                  ${
                    isSelected
                      ? "bg-warm-gold-500 border-warm-gold-500"
                      : "border-deep-slate-600"
                  }
                `}
              >
                {isSelected && <Check className="w-3.5 h-3.5 text-deep-slate-900" />}
              </div>

              {/* Label & Description */}
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-deep-slate-100">
                    {scope.name}
                  </span>
                  {scope.required && (
                    <span className="text-xs px-2 py-0.5 rounded-full bg-warm-gold-500/20 text-warm-gold-400 font-medium">
                      obligatoire
                    </span>
                  )}
                </div>
                <p className="text-sm text-deep-slate-400 mt-1">
                  {scope.description}
                </p>
              </div>
            </div>
          </button>
        );
      })}
    </div>
  );
}
