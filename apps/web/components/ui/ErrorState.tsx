"use client";

import { AlertCircle } from 'lucide-react';

export interface ErrorStateProps {
  message: string;
  onRetry?: () => void;
}

export default function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-12 px-4">
      <div className="bg-danger/10 rounded p-4 mb-4">
        <AlertCircle className="h-12 w-12 text-danger" />
      </div>
      <h3 className="text-lg font-medium text-neutral-900 mb-2">Une erreur est survenue</h3>
      <p className="text-sm text-neutral-600 text-center mb-6 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-primary text-white rounded font-medium text-sm hover:bg-primary/90 transition-colors duration-150"
        >
          Réessayer
        </button>
      )}
    </div>
  );
}
