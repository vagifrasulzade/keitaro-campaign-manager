import { useEffect, useState } from "react";
import { api, errorText } from "./api/client";
import type { Meta } from "./api/types";
import { useToast } from "./components/Toast";
import { Card } from "./components/ui";

type Tab = "create" | "editor";

const TABS: { id: Tab; label: string }[] = [
  { id: "create", label: "New campaign" },
  { id: "editor", label: "Campaign editor" },
];

export default function App() {
  const toast = useToast();
  const [tab, setTab] = useState<Tab>("create");
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    let ignore = false;
    api.meta().then(
      (data) => {
        if (!ignore) setMeta(data);
      },
      (err) => {
        if (!ignore) toast(`Could not load domains, groups and sources: ${errorText(err)}`, "error");
      },
    );
    return () => {
      ignore = true;
    };
  }, [toast]);

  return (
    <div className="min-h-screen bg-gray-100 text-gray-800">
      <header className="h-13 bg-slate-800 text-white">
        <div className="mx-auto flex h-full max-w-6xl items-center gap-6 px-4">
          <span className="font-semibold text-green-400">Keitaro · Campaign Manager</span>
          <nav className="flex h-full">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                aria-current={tab === t.id ? "page" : undefined}
                onClick={() => setTab(t.id)}
                className={`h-full border-b-2 px-4 text-sm transition-colors ${
                  tab === t.id ? "border-green-400 text-white" : "border-transparent text-slate-300 hover:text-white"
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
          <a href="/docs" target="_blank" rel="noreferrer" className="ml-auto text-sm text-slate-300 hover:text-white">
            API docs
          </a>
        </div>
      </header>

      {meta?.mock_mode && (
        <div className="border-b border-yellow-300 bg-yellow-100 px-4 py-2 text-center text-sm text-yellow-900">
          Demo mode: KEITARO_MOCK=true — nothing is sent to Keitaro
        </div>
      )}

      <main className="mx-auto max-w-6xl px-4 py-6">
        <Card>
          <p className="text-sm text-gray-500">{TABS.find((t) => t.id === tab)?.label} — coming next.</p>
        </Card>
      </main>
    </div>
  );
}
