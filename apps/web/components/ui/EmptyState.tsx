"use client";

import { Inbox, Lightbulb } from 'lucide-react';

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
    shortcut?: string;
  };
  suggestions?: {
    label: string;
    onClick: () => void;
  }[];
}

export default function EmptyState({ title, description, icon, action, suggestions }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-neutral-100 rounded-full p-6 mb-6">
        {icon || <Inbox className="h-12 w-12 text-neutral-400" />}
      </div>
      <h3 className="text-xl font-semibold text-neutral-900 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-neutral-600 text-center mb-6 max-w-md">{description}</p>
      )}

      {action && (
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={action.onClick}
            className="px-5 py-2.5 bg-primary text-white rounded font-medium text-sm hover:bg-primary/90 transition-colors duration-150 shadow-sm"
          >
            {action.label}
          </button>
          {action.shortcut && (
            <kbd className="px-3 py-1.5 text-xs bg-neutral-100 text-neutral-600 rounded font-mono border border-neutral-200">
              {action.shortcut}
            </kbd>
          )}
        </div>
      )}

      {suggestions && suggestions.length > 0 && (
        <div className="w-full max-w-md mt-4">
          <div className="flex items-center gap-2 text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-3">
            <Lightbulb className="w-4 h-4" />
            <span>Suggestions</span>
          </div>
          <div className="space-y-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={suggestion.onClick}
                className="w-full text-left px-4 py-3 bg-white border border-neutral-200 rounded hover:border-primary hover:bg-primary/5 transition-all duration-150 text-sm text-neutral-700 hover:text-primary"
              >
                {suggestion.label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
