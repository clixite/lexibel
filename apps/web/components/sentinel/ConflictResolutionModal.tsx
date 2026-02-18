"use client";

import { useState } from "react";
import { X, FileText, Shield, AlertTriangle } from "lucide-react";
import { ResolutionType } from "@/lib/sentinel/api-client";

interface ConflictResolutionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onResolve: (resolution: ResolutionType, notes?: string) => Promise<void>;
  conflictDescription: string;
}

export default function ConflictResolutionModal({
  isOpen,
  onClose,
  onResolve,
  conflictDescription,
}: ConflictResolutionModalProps) {
  const [selectedResolution, setSelectedResolution] = useState<ResolutionType | null>(null);
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async () => {
    if (!selectedResolution) return;

    setIsSubmitting(true);
    try {
      await onResolve(selectedResolution, notes || undefined);
      onClose();
    } catch (error) {
      console.error("Failed to resolve conflict:", error);
      alert("Erreur lors de la résolution du conflit");
    } finally {
      setIsSubmitting(false);
    }
  };

  const resolutionOptions: Array<{
    value: ResolutionType;
    label: string;
    description: string;
    icon: React.ReactNode;
    color: string;
  }> = [
    {
      value: "refused",
      label: "Refuser le dossier",
      description: "Le cabinet refuse de prendre ce dossier en raison du conflit d'intérêts",
      icon: <X className="w-5 h-5" />,
      color: "border-red-500 bg-red-50 dark:bg-red-950/20",
    },
    {
      value: "waiver_obtained",
      label: "Dérogation obtenue",
      description: "Les parties ont donné leur consentement écrit et éclairé",
      icon: <Shield className="w-5 h-5" />,
      color: "border-green-500 bg-green-50 dark:bg-green-950/20",
    },
    {
      value: "false_positive",
      label: "Faux positif",
      description: "Le conflit détecté n'en est pas un après vérification manuelle",
      icon: <AlertTriangle className="w-5 h-5" />,
      color: "border-yellow-500 bg-yellow-50 dark:bg-yellow-950/20",
    },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            Résolution du conflit
          </h2>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* Conflict description */}
        <div className="p-6 bg-gray-50 dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700">
          <p className="text-sm text-gray-700 dark:text-gray-300">{conflictDescription}</p>
        </div>

        {/* Resolution options */}
        <div className="p-6 space-y-4">
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-4">
            Choisissez une méthode de résolution :
          </p>

          {resolutionOptions.map((option) => (
            <button
              key={option.value}
              onClick={() => setSelectedResolution(option.value)}
              className={`w-full p-4 border-2 rounded-lg text-left transition-all ${
                selectedResolution === option.value
                  ? option.color + " shadow-md"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`flex-shrink-0 ${
                    selectedResolution === option.value
                      ? "text-current"
                      : "text-gray-400 dark:text-gray-500"
                  }`}
                >
                  {option.icon}
                </div>
                <div className="flex-1">
                  <p className="font-semibold text-gray-900 dark:text-white mb-1">
                    {option.label}
                  </p>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {option.description}
                  </p>
                </div>
              </div>
            </button>
          ))}

          {/* Notes field (required for false_positive) */}
          {selectedResolution && (
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Notes {selectedResolution === "false_positive" && "(obligatoire)"}
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                placeholder={
                  selectedResolution === "false_positive"
                    ? "Expliquez pourquoi ce conflit est un faux positif..."
                    : "Commentaires additionnels (optionnel)..."
                }
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors disabled:opacity-50"
          >
            Annuler
          </button>
          <button
            onClick={handleSubmit}
            disabled={
              !selectedResolution ||
              isSubmitting ||
              (selectedResolution === "false_positive" && !notes.trim())
            }
            className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? "Résolution..." : "Confirmer la résolution"}
          </button>
        </div>
      </div>
    </div>
  );
}
