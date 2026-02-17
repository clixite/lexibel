"use client";

import { Archive, Trash2, X, Check, FileText, Mail, Tag } from "lucide-react";

interface BulkActionBarProps {
  selectedCount: number;
  onArchive?: () => void;
  onDelete?: () => void;
  onCancel: () => void;
  actions?: {
    label: string;
    icon: React.ReactNode;
    onClick: () => void;
    variant?: "default" | "danger";
  }[];
}

export default function BulkActionBar({
  selectedCount,
  onArchive,
  onDelete,
  onCancel,
  actions = [],
}: BulkActionBarProps) {
  if (selectedCount === 0) return null;

  const defaultActions = [
    ...(onArchive
      ? [
          {
            label: "Archiver",
            icon: <Archive className="w-4 h-4" />,
            onClick: onArchive,
            variant: "default" as const,
          },
        ]
      : []),
    ...(onDelete
      ? [
          {
            label: "Supprimer",
            icon: <Trash2 className="w-4 h-4" />,
            onClick: onDelete,
            variant: "danger" as const,
          },
        ]
      : []),
    ...actions,
  ];

  return (
    <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-40 animate-in slide-in-from-bottom-4 fade-in duration-200">
      <div className="bg-primary text-white px-6 py-4 rounded-lg shadow-2xl border border-primary-700 flex items-center gap-6">
        <div className="flex items-center gap-2">
          <div className="bg-white/20 rounded-full p-1.5">
            <Check className="w-4 h-4" />
          </div>
          <span className="text-sm font-semibold">
            {selectedCount} élément{selectedCount > 1 ? "s" : ""} sélectionné{selectedCount > 1 ? "s" : ""}
          </span>
        </div>

        <div className="h-6 w-px bg-white/20" />

        <div className="flex items-center gap-2">
          {defaultActions.map((action, index) => (
            <button
              key={index}
              onClick={action.onClick}
              className={`flex items-center gap-2 px-4 py-2 rounded text-sm font-medium transition-all duration-150 ${
                action.variant === "danger"
                  ? "bg-danger-600 hover:bg-danger-700 text-white"
                  : "bg-white/20 hover:bg-white/30"
              }`}
            >
              {action.icon}
              <span>{action.label}</span>
            </button>
          ))}
        </div>

        <div className="h-6 w-px bg-white/20" />

        <button
          onClick={onCancel}
          className="text-sm hover:underline flex items-center gap-1.5 px-2 py-1 hover:bg-white/10 rounded transition-colors duration-150"
        >
          <X className="w-4 h-4" />
          <span>Annuler</span>
        </button>
      </div>
    </div>
  );
}
