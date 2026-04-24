import { useEffect, useState } from 'react';
import type { Toast as ToastData, ToastType } from '@/hooks/useToast';

function Dot({ type }: { type: ToastType }) {
  const cls = {
    success: 'bg-white',
    error: 'bg-white/60',
    info: 'bg-white/60',
  }[type];
  return <span className={`h-1.5 w-1.5 rounded-full ${cls}`} aria-hidden="true" />;
}

function ToastItem({
  toast,
  onClose,
}: {
  toast: ToastData;
  onClose: (id: string) => void;
}) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const frame = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <div
      className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm text-white max-w-sm transition-all duration-300 ease-out bg-gray-900 dark:bg-white dark:text-gray-900 ${
        visible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'
      }`}
      style={{ boxShadow: '0 6px 24px rgba(0,0,0,0.12)' }}
    >
      <Dot type={toast.type} />
      <span className="flex-1">{toast.message}</span>
      <button
        onClick={() => onClose(toast.id)}
        className="flex-shrink-0 ml-2 rounded p-0.5 opacity-70 hover:opacity-100 transition-opacity"
        aria-label="Close notification"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-3.5 w-3.5"
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
