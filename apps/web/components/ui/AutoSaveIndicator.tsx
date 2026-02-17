"use client";

import { useEffect, useState } from "react";
import { Check, Loader2, AlertCircle } from "lucide-react";

export type SaveStatus = "idle" | "saving" | "saved" | "error";

interface AutoSaveIndicatorProps {
  status: SaveStatus;
  lastSaved?: Date;
  error?: string;
}

export default function AutoSaveIndicator({
  status,
  lastSaved,
  error,
}: AutoSaveIndicatorProps) {
  const [timeAgo, setTimeAgo] = useState<string>("");

  useEffect(() => {
    if (!lastSaved) return;

    const updateTimeAgo = () => {
      const seconds = Math.floor((Date.now() - lastSaved.getTime()) / 1000);

      if (seconds < 5) {
        setTimeAgo("À l'instant");
      } else if (seconds < 60) {
        setTimeAgo(`Il y a ${seconds}s`);
      } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        setTimeAgo(`Il y a ${minutes}min`);
      } else {
        const hours = Math.floor(seconds / 3600);
        setTimeAgo(`Il y a ${hours}h`);
      }
    };

    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 10000); // Update every 10s

    return () => clearInterval(interval);
  }, [lastSaved]);

  return (
    <div className="flex items-center gap-2 text-sm text-neutral-600">
      {status === "saving" && (
        <>
          <Loader2 className="w-4 h-4 animate-spin text-primary" />
          <span>Sauvegarde...</span>
        </>
      )}
      {status === "saved" && lastSaved && (
        <>
          <Check className="w-4 h-4 text-success-600" />
          <span className="text-neutral-500">Sauvegardé {timeAgo}</span>
        </>
      )}
      {status === "error" && (
        <>
          <AlertCircle className="w-4 h-4 text-danger-600" />
          <span className="text-danger-600" title={error}>
            Erreur de sauvegarde
          </span>
        </>
      )}
    </div>
  );
}
