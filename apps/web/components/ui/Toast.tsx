"use client";

import { ReactNode, useEffect, useState } from "react";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";

export interface ToastProps {
  message: ReactNode;
  type?: "success" | "error" | "info";
  duration?: number;
  onClose: () => void;
}

export default function Toast({
  message,
  type = "info",
  duration = 5000,
  onClose,
}: ToastProps) {
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const remaining = Math.max(0, 100 - (elapsed / duration) * 100);
      setProgress(remaining);

      if (remaining === 0) {
        clearInterval(interval);
        onClose();
      }
    }, 10);

    return () => clearInterval(interval);
  }, [duration, onClose]);

  const typeConfig = {
    success: {
      icon: CheckCircle,
      bgColor: "bg-success-50",
      borderColor: "border-success-200",
      textColor: "text-success-900",
      iconColor: "text-success-500",
      progressColor: "bg-success-500",
    },
    error: {
      icon: AlertCircle,
      bgColor: "bg-danger-50",
      borderColor: "border-danger-200",
      textColor: "text-danger-900",
      iconColor: "text-danger-500",
      progressColor: "bg-danger-500",
    },
    info: {
      icon: Info,
      bgColor: "bg-primary-50",
      borderColor: "border-primary-200",
      textColor: "text-primary-900",
      iconColor: "text-primary-500",
      progressColor: "bg-primary-500",
    },
  };

  const config = typeConfig[type];
  const Icon = config.icon;

  return (
    <div
      className={`
        fixed top-4 right-4 z-50
        min-w-[320px] max-w-md
        ${config.bgColor} ${config.borderColor} ${config.textColor}
        border rounded-lg shadow-lg
        animate-slideLeft
        overflow-hidden
      `}
    >
      <div className="flex items-start gap-3 p-4">
        <Icon className={`h-5 w-5 ${config.iconColor} flex-shrink-0 mt-0.5`} />
        <div className="flex-1 text-sm font-medium">{message}</div>
        <button
          onClick={onClose}
          className="flex-shrink-0 p-0.5 rounded hover:bg-black/5 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Progress Bar */}
      <div className="h-1 bg-black/5">
        <div
          className={`h-full ${config.progressColor} transition-all duration-100 ease-linear`}
          style={{ width: `${progress}%` }}
        />
      </div>
    </div>
  );
}
