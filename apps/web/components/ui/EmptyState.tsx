"use client";

import { Inbox } from 'lucide-react';

export interface EmptyStateProps {
  title: string;
  description?: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export default function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-neutral-100 rounded p-4 mb-4">
        {icon || <Inbox className="h-12 w-12 text-neutral-400" />}
      </div>
      <h3 className="text-lg font-medium text-neutral-900 mb-2">{title}</h3>
      {description && (
        <p className="text-sm text-neutral-600 text-center mb-6 max-w-md">{description}</p>
      )}
      {action && (
        <button
          onClick={action.onClick}
          className="px-4 py-2 bg-primary text-white rounded font-medium text-sm hover:bg-primary/90 transition-colors duration-150"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
