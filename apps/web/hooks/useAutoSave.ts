"use client";

import { useEffect, useRef, useState } from "react";
import type { SaveStatus } from "@/components/ui/AutoSaveIndicator";

interface UseAutoSaveOptions<T> {
  data: T;
  onSave: (data: T) => Promise<void>;
  delay?: number; // ms to wait before saving
  enabled?: boolean;
}

export function useAutoSave<T>({
  data,
  onSave,
  delay = 1000,
  enabled = true,
}: UseAutoSaveOptions<T>) {
  const [status, setStatus] = useState<SaveStatus>("idle");
  const [lastSaved, setLastSaved] = useState<Date | undefined>();
  const [error, setError] = useState<string | undefined>();
  const timeoutRef = useRef<NodeJS.Timeout>();
  const prevDataRef = useRef<T>(data);

  useEffect(() => {
    if (!enabled) return;

    // Skip if data hasn't changed
    if (JSON.stringify(data) === JSON.stringify(prevDataRef.current)) {
      return;
    }

    prevDataRef.current = data;

    // Clear previous timeout
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Set saving status
    setStatus("saving");

    // Schedule save
    timeoutRef.current = setTimeout(async () => {
      try {
        await onSave(data);
        setStatus("saved");
        setLastSaved(new Date());
        setError(undefined);
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "Erreur de sauvegarde");
      }
    }, delay);

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [data, onSave, delay, enabled]);

  const saveNow = async () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    setStatus("saving");
    try {
      await onSave(data);
      setStatus("saved");
      setLastSaved(new Date());
      setError(undefined);
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Erreur de sauvegarde");
    }
  };

  return {
    status,
    lastSaved,
    error,
    saveNow,
  };
}
