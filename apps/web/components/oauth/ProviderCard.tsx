"use client";

import { Check } from "lucide-react";

export interface Provider {
  id: "google" | "microsoft";
  name: string;
  description: string;
  features: string[];
  icon: React.ReactNode;
  color: string;
}

interface ProviderCardProps {
  provider: Provider;
  selected: boolean;
  connected: boolean;
  onSelect: () => void;
}

export function ProviderCard({
  provider,
  selected,
  connected,
  onSelect,
}: ProviderCardProps) {
  return (
    <button
      onClick={onSelect}
      className={`
        transition-transform hover:scale-[1.02] active:scale-[0.98]
        relative w-full p-6 rounded-xl border-2 transition-all duration-200
        text-left
        ${
          selected
            ? "border-warm-gold-500 bg-warm-gold-50/5"
            : "border-deep-slate-700 hover:border-deep-slate-600 bg-deep-slate-800/30"
        }
        ${connected ? "opacity-75" : ""}
      `}
    >
      {/* Connected Badge */}
      {connected && (
        <div className="absolute top-4 right-4">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-success-500/20 border border-success-500/30">
            <Check className="w-3.5 h-3.5 text-success-400" />
            <span className="text-xs font-medium text-success-400">
              Connecté
            </span>
          </div>
        </div>
      )}

      {/* Provider Icon & Name */}
      <div className="flex items-start gap-4 mb-4">
        <div className={`p-3 rounded-lg ${provider.color}`}>{provider.icon}</div>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-deep-slate-100">
            {provider.name}
          </h3>
          <p className="text-sm text-deep-slate-400 mt-0.5">
            {provider.description}
          </p>
        </div>
      </div>

      {/* Features */}
      <div className="space-y-2">
        {provider.features.map((feature, index) => (
          <div key={index} className="flex items-center gap-2 text-sm">
            <div className="w-1.5 h-1.5 rounded-full bg-warm-gold-500" />
            <span className="text-deep-slate-300">{feature}</span>
          </div>
        ))}
      </div>

      {/* Selection Indicator */}
      {selected && (
        <div className="absolute inset-0 rounded-xl ring-2 ring-warm-gold-500 ring-offset-2 ring-offset-deep-slate-900 pointer-events-none" />
      )}
    </button>
  );
}
