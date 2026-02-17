"use client";
import { useEffect, useState } from "react";
import { CheckCircle, XCircle, Info, AlertTriangle, X } from "lucide-react";

type ToastType = "success" | "error" | "info" | "warning";

interface Toast {
  id: string;
  type: ToastType;
  message: string;
  duration?: number;
}

let toastId = 0;
const listeners = new Set<(toasts: Toast[]) => void>();
let toasts: Toast[] = [];

export const toast = {
  success: (message: string, duration = 5000) => addToast("success", message, duration),
  error: (message: string, duration = 5000) => addToast("error", message, duration),
  info: (message: string, duration = 5000) => addToast("info", message, duration),
  warning: (message: string, duration = 5000) => addToast("warning", message, duration),
};

function addToast(type: ToastType, message: string, duration: number) {
  const id = String(toastId++);
  const newToast = { id, type, message, duration };
  toasts = [...toasts, newToast];
  listeners.forEach((l) => l(toasts));

  if (duration > 0) {
    setTimeout(() => removeToast(id), duration);
  }
}

function removeToast(id: string) {
  toasts = toasts.filter((t) => t.id !== id);
  listeners.forEach((l) => l(toasts));
}

const iconMap = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
  warning: AlertTriangle,
};

const colorMap = {
  success: {
    bg: "bg-success-50",
    border: "border-success-200",
    icon: "text-success-600",
    text: "text-success-900",
  },
  error: {
    bg: "bg-danger-50",
    border: "border-danger-200",
    icon: "text-danger-600",
    text: "text-danger-900",
  },
  info: {
    bg: "bg-primary-50",
    border: "border-primary-200",
    icon: "text-primary-600",
    text: "text-primary-900",
  },
  warning: {
    bg: "bg-warning-50",
    border: "border-warning-200",
    icon: "text-warning-600",
    text: "text-warning-900",
  },
};

export default function ToastContainer() {
  const [list, setList] = useState<Toast[]>([]);

  useEffect(() => {
    listeners.add(setList);
    return () => {
      listeners.delete(setList);
    };
  }, []);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 pointer-events-none">
      {list.map((toast) => {
        const Icon = iconMap[toast.type];
        const colors = colorMap[toast.type];

        return (
          <div
            key={toast.id}
            className={`pointer-events-auto ${colors.bg} border ${colors.border} rounded shadow-lg px-4 py-3 flex items-center gap-3 min-w-80 max-w-md animate-in slide-in-from-top-4 fade-in duration-200`}
          >
            <Icon className={`w-5 h-5 ${colors.icon} flex-shrink-0`} />
            <span className={`flex-1 text-sm font-medium ${colors.text}`}>
              {toast.message}
            </span>
            <button
              onClick={() => removeToast(toast.id)}
              className="flex-shrink-0 hover:opacity-70 transition-opacity"
            >
              <X className="w-4 h-4 text-neutral-400 hover:text-neutral-600" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
