import { useEffect, useState } from 'react';
import type { Toast as ToastData, ToastType } from '@/hooks/useToast';

const typeStyles: Record<ToastType, { bg: string; icon: string }> = {
  success: {
    bg: 'bg-green-600',
    icon: '✓',
  },
  error: {
    bg: 'bg-red-600',
    icon: '✕',
  },
  info: {
    bg: 'bg-blue-600',
    icon: 'ℹ',
  },
};

/** Individual toast notification with slide-in animation and close button. */
function ToastItem({
  toast,
  onClose,
}: {
  toast: ToastData;
  onClose: (id: string) => void;
}) {
  const [visible, setVisible] = useState(false);
  const style = typeStyles[toast.type];

  useEffect(() => {
    // Trigger slide-in on next frame
    const frame = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div
      className={`flex items-center gap-3 rounded-lg shadow-lg px-4 py-3 text-white text-sm max-w-sm transition-all duration-300 ease-out ${
        visible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      } ${style.bg}`}
    >
      <span className="flex-shrink-0 w-5 h-5 flex items-center justify-center rounded-full bg-white/20 text-xs font-bold">
        {style.icon}
      </span>
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={() => onClose(toast.id)}
        className="flex-shrink-0 ml-2 hover:bg-white/20 rounded p-0.5 transition-colors"
        aria-label="Close notification"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  );
}

/** Fixed-position container that stacks toast notifications in the bottom-right corner. */
export function ToastContainer({
  toasts,
  onClose,
}: {
  toasts: ToastData[];
  onClose: (id: string) => void;
}) {
  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-2">
      {toasts.map((toast) => (
        <ToastItem key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  );
}
