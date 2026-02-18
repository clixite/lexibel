"use client";

import { useState } from "react";
import { Check } from "lucide-react";

export interface WizardStep {
  id: string;
  title: string;
  description: string;
}

interface OAuthWizardProps {
  steps: WizardStep[];
  currentStep: number;
  children: React.ReactNode;
}

export function OAuthWizard({ steps, currentStep, children }: OAuthWizardProps) {
  return (
    <div className="w-full max-w-4xl mx-auto">
      {/* Progress Bar */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-4">
          {steps.map((step, index) => (
            <div key={step.id} className="flex-1 flex items-center">
              {/* Step Circle */}
              <div className="relative">
                <div
                  className={`
                    w-10 h-10 rounded-full flex items-center justify-center
                    border-2 transition-all duration-300
                    ${
                      index < currentStep
                        ? "bg-warm-gold-500 border-warm-gold-500 text-white"
                        : index === currentStep
                        ? "bg-warm-gold-100 border-warm-gold-500 text-warm-gold-700"
                        : "bg-deep-slate-700 border-deep-slate-600 text-deep-slate-400"
                    }
                  `}
                >
                  {index < currentStep ? (
                    <Check className="w-5 h-5" />
                  ) : (
                    <span className="font-semibold">{index + 1}</span>
                  )}
                </div>
              </div>

              {/* Connector Line */}
              {index < steps.length - 1 && (
                <div
                  className={`
                    flex-1 h-0.5 mx-2 transition-all duration-300
                    ${
                      index < currentStep
                        ? "bg-warm-gold-500"
                        : "bg-deep-slate-700"
                    }
                  `}
                />
              )}
            </div>
          ))}
        </div>

        {/* Step Labels */}
        <div className="flex items-start justify-between">
          {steps.map((step, index) => (
            <div
              key={step.id}
              className={`flex-1 ${index > 0 ? "text-center" : "text-left"} ${
                index === steps.length - 1 ? "text-right" : ""
              }`}
            >
              <div
                className={`text-sm font-medium transition-colors duration-300 ${
                  index === currentStep
                    ? "text-warm-gold-400"
                    : index < currentStep
                    ? "text-warm-gold-500"
                    : "text-deep-slate-500"
                }`}
              >
                {step.title}
              </div>
              <div
                className={`text-xs mt-1 transition-colors duration-300 ${
                  index === currentStep
                    ? "text-deep-slate-400"
                    : "text-deep-slate-600"
                }`}
              >
                {step.description}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Step Content */}
      <div key={currentStep} className="animate-fade-in">
        {children}
      </div>
    </div>
  );
}
