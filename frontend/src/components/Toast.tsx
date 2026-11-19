import { createContext, useCallback, useContext, useRef, useState } from "react";
import type { ReactNode } from "react";
import { errorText } from "../api/client";

type ToastKind = "ok" | "error";
type ShowToast = (message: string, kind?: ToastKind) => void;

interface ToastItem {
  id: number;
  message: string;
  kind: ToastKind;
}

const HIDE_AFTER_MS: Record<ToastKind, number> = { ok: 2500, error: 6000 };

const ToastContext = createContext<ShowToast | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const nextId = useRef(0);

  const show = useCallback<ShowToast>((message, kind = "ok") => {
    const id = ++nextId.current;
    setToasts((list) => [...list, { id, message, kind }]);
    window.setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), HIDE_AFTER_MS[kind]);
  }, []);

  return (
    <ToastContext value={show}>
      {children}
      <div className="pointer-events-none fixed right-4 bottom-4 z-50 flex flex-col items-end gap-2">
        {toasts.map((t) => (
          <div
            key={t.id}
            role={t.kind === "error" ? "alert" : "status"}
            className={`pointer-events-auto max-w-sm rounded px-4 py-2.5 text-sm text-white shadow-lg ${
              t.kind === "error" ? "bg-red-600" : "bg-slate-700"
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext>
  );
}

export function useToast(): ShowToast {
  const show = useContext(ToastContext);
  if (!show) throw new Error("useToast must be used inside <ToastProvider>");
  return show;
}

/** `run(fn)` awaits fn and shows its error as a toast (then returns undefined); `busy` is true meanwhile. */
export function useAction() {
  const toast = useToast();
  const [busy, setBusy] = useState(false);
  const pending = useRef(0);

  const run = useCallback(
    async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
      pending.current++;
      setBusy(true);
      try {
        return await fn();
      } catch (err) {
        toast(errorText(err), "error");
        return undefined;
      } finally {
        pending.current--;
        setBusy(pending.current > 0);
      }
    },
    [toast],
  );

  return { run, busy };
}
