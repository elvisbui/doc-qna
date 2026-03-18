import { useState, useCallback, useRef } from 'react';

/** Visual style category of a toast notification. */
export type ToastType = 'success' | 'error' | 'info';

/** A toast notification displayed temporarily in the UI. */
export interface Toast {
  /** Unique identifier for the toast instance. */
  id: string;
  /** Visual style category (success, error, or info). */
  type: ToastType;
  /** Text content displayed in the toast. */
  message: string;
}

let nextId = 0;

/**
 * Manages toast notifications with auto-dismiss after 5 seconds.
 * @returns Toast list, addToast to create a notification, and removeToast to dismiss one.
 */
export function useToast() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: string) => {
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const addToast = useCallback(
    (type: ToastType, message: string) => {
      const id = `toast-${++nextId}`;
      const toast: Toast = { id, type, message };
      setToasts((prev) => [...prev, toast]);

      const timer = setTimeout(() => {
        removeToast(id);
      }, 5000);
      timersRef.current.set(id, timer);

      return id;
    },
    [removeToast],
  );

  return { toasts, addToast, removeToast };
}
