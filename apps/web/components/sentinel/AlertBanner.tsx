"use client";

import { useState, useEffect } from "react";
import { X, AlertTriangle } from "lucide-react";
import { useSentinelAlerts } from "@/hooks/useSentinelAlerts";

export default function AlertBanner() {
  const { alerts } = useSentinelAlerts();
  const [isVisible, setIsVisible] = useState(false);
  const [currentAlert, setCurrentAlert] = useState<any>(null);

  useEffect(() => {
    if (alerts.length > 0) {
      const latestAlert = alerts[0];
      if (latestAlert.type === "conflict_detected" && latestAlert.conflict) {
        setCurrentAlert(latestAlert);
        setIsVisible(true);

        // Auto-hide after 10 seconds
        const timer = setTimeout(() => setIsVisible(false), 10000);
        return () => clearTimeout(timer);
      }
    }
  }, [alerts]);

  if (!isVisible || !currentAlert) return null;

  return (
    <div className="fixed top-20 right-4 z-50 max-w-md animate-slide-in-right">
      <div className="bg-red-50 dark:bg-red-950/90 border-l-4 border-red-500 rounded-lg shadow-lg p-4">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-red-900 dark:text-red-100 mb-1">
              Nouveau conflit détecté
            </p>
            <p className="text-sm text-red-800 dark:text-red-200 mb-2">
              {currentAlert.conflict?.description}
            </p>
            <p className="text-xs text-red-700 dark:text-red-300">
              Sévérité : {currentAlert.conflict?.severity_score ?? 0}/100
            </p>
          </div>
          <button
            onClick={() => setIsVisible(false)}
            className="flex-shrink-0 text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-200"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
