"use client";

import { useState } from "react";
import { toast } from "@/components/ToastContainer";

interface UseOptimisticUpdateOptions<T> {
  onSuccess?: (item: T) => void;
  onError?: (error: Error) => void;
  successMessage?: string;
  errorMessage?: string;
}

export function useOptimisticUpdate<T extends { id?: string }>(
  items: T[],
  setItems: (items: T[]) => void,
  options: UseOptimisticUpdateOptions<T> = {}
) {
  const [pending, setPending] = useState<Set<string>>(new Set());

  const createOptimistic = async (
    data: Omit<T, "id">,
    apiFn: (data: Omit<T, "id">) => Promise<T>
  ) => {
    const tempId = `temp-${Date.now()}`;
    const tempItem = { ...data, id: tempId, _optimistic: true } as unknown as T;

    // 1. Optimistic update
    setItems([...items, tempItem]);
    setPending(new Set([...pending, tempId]));

    try {
      // 2. API call
      const result = await apiFn(data);

      // 3. Replace temp with real
      setItems(items.map((item) => (item.id === tempId ? result : item)));
      setPending(new Set([...pending].filter((id) => id !== tempId)));

      if (options.successMessage) {
        toast.success(options.successMessage);
      }
      options.onSuccess?.(result);

      return result;
    } catch (error) {
      // 4. Rollback on error
      setItems(items.filter((item) => item.id !== tempId));
      setPending(new Set([...pending].filter((id) => id !== tempId)));

      const err = error as Error;
      if (options.errorMessage) {
        toast.error(options.errorMessage);
      }
      options.onError?.(err);

      throw error;
    }
  };

  const updateOptimistic = async (
    id: string,
    updates: Partial<T>,
    apiFn: (id: string, updates: Partial<T>) => Promise<T>
  ) => {
    const originalItem = items.find((item) => item.id === id);
    if (!originalItem) return;

    // 1. Optimistic update
    setItems(items.map((item) => (item.id === id ? { ...item, ...updates } : item)));
    setPending(new Set([...pending, id]));

    try {
      // 2. API call
      const result = await apiFn(id, updates);

      // 3. Replace with real data
      setItems(items.map((item) => (item.id === id ? result : item)));
      setPending(new Set([...pending].filter((pid) => pid !== id)));

      if (options.successMessage) {
        toast.success(options.successMessage);
      }
      options.onSuccess?.(result);

      return result;
    } catch (error) {
      // 4. Rollback on error
      setItems(items.map((item) => (item.id === id ? originalItem : item)));
      setPending(new Set([...pending].filter((pid) => pid !== id)));

      const err = error as Error;
      if (options.errorMessage) {
        toast.error(options.errorMessage);
      }
      options.onError?.(err);

      throw error;
    }
  };

  const deleteOptimistic = async (
    id: string,
    apiFn: (id: string) => Promise<void>
  ) => {
    const originalItem = items.find((item) => item.id === id);
    if (!originalItem) return;

    // 1. Optimistic delete
    setItems(items.filter((item) => item.id !== id));
    setPending(new Set([...pending, id]));

    try {
      // 2. API call
      await apiFn(id);

      // 3. Confirm deletion
      setPending(new Set([...pending].filter((pid) => pid !== id)));

      if (options.successMessage) {
        toast.success(options.successMessage);
      }
    } catch (error) {
      // 4. Rollback on error
      setItems([...items, originalItem]);
      setPending(new Set([...pending].filter((pid) => pid !== id)));

      const err = error as Error;
      if (options.errorMessage) {
        toast.error(options.errorMessage);
      }
      options.onError?.(err);

      throw error;
    }
  };

  return {
    createOptimistic,
    updateOptimistic,
    deleteOptimistic,
    pending,
    isPending: (id: string) => pending.has(id),
  };
}
