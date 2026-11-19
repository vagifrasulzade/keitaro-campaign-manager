import { useEffect, useState } from "react";
import { api, errorText } from "../api/client";
import type { Campaign, CampaignListItem, Stream } from "../api/types";
import { StreamCard } from "../components/StreamCard";
import { useAction, useToast } from "../components/Toast";
import { Button, Card, INPUT_CLASS, LINK_CLASS, Tag } from "../components/ui";
import { byPosition } from "../format";

const SEARCH_DEBOUNCE_MS = 250;

interface Props {
  /** the tab is visible — the campaign list is refreshed every time it opens */
  active: boolean;
  campaignId: number | null;
  onSelect: (campaignId: number) => void;
}

export function CampaignEditor({ active, campaignId, onSelect }: Props) {
  const toast = useToast();
  const sync = useAction();
  const [search, setSearch] = useState("");
  const [items, setItems] = useState<CampaignListItem[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!active) return;
    let ignore = false;
    const timer = window.setTimeout(async () => {
      setListLoading(true);
      try {
        const list = await api.listCampaigns(search.trim());
        if (!ignore) setItems(list);
      } catch (err) {
        if (!ignore) toast(errorText(err), "error");
      } finally {
        if (!ignore) setListLoading(false);
      }
    }, SEARCH_DEBOUNCE_MS);
    return () => {
      ignore = true;
      window.clearTimeout(timer);
    };
  }, [active, search, toast]);

  useEffect(() => {
    if (campaignId === null) return;
    let ignore = false;
    setLoading(true);
    api
      .getCampaign(campaignId)
      .then((data) => {
        if (ignore) return;
        setCampaign(data);
        // the first open imports the campaign
        setItems((list) => list.map((item) => (item.id === data.id ? { ...item, is_local: true } : item)));
      })
      .catch((err) => {
        if (!ignore) toast(errorText(err), "error");
      })
      .finally(() => {
        if (!ignore) setLoading(false);
      });
    return () => {
      ignore = true;
    };
  }, [campaignId, toast]);

  async function fetchFromKeitaro(current: Campaign) {
    const hasDraft = current.streams.some((s) => s.is_dirty);
    if (hasDraft && !window.confirm("Unpublished changes will be lost. Fetch the streams from Keitaro anyway?")) return;
    const fresh = await sync.run(() => api.syncCampaign(current.id));
    if (fresh) {
      setCampaign(fresh);
      toast("Fetched from Keitaro");
    }
  }

  function replaceStream(stream: Stream) {
    setCampaign((c) => c && { ...c, streams: c.streams.map((s) => (s.id === stream.id ? stream : s)) });
  }

  const shown = campaign?.id === campaignId ? campaign : null;

  return (
    <div className="grid items-start gap-4 md:grid-cols-[280px_1fr]">
      <Card>
        <input
          type="search"
          aria-label="Search campaigns"
          className={INPUT_CLASS}
          placeholder="Search by name or ID…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <ul className="-mx-2 mt-3 max-h-[70vh] space-y-0.5 overflow-y-auto">
          {items.map((item) => {
            const selected = item.id === campaignId;
            return (
              <li key={item.id}>
                <button
                  type="button"
                  aria-current={selected || undefined}
                  className={`w-full rounded px-2 py-1.5 text-left ${
                    selected ? "bg-green-50 ring-1 ring-green-200" : "hover:bg-gray-50"
                  }`}
                  onClick={() => onSelect(item.id)}
                >
                  <span className="flex items-center gap-2">
                    <span className="min-w-0 flex-1 truncate text-sm font-medium text-gray-900">
                      {item.name || "(no name)"}
                    </span>
                    {item.is_local && <Tag>loaded</Tag>}
                  </span>
                  <span className="block truncate text-xs text-gray-500">
                    #{item.id}
                    {item.alias && ` · ${item.alias}`}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
        {listLoading && <p className="mt-3 text-xs text-gray-400">Loading…</p>}
        {!listLoading && items.length === 0 && <p className="mt-3 text-sm text-gray-500">No campaigns found</p>}
      </Card>

      <div className="min-w-0 space-y-4">
        {shown ? (
          <>
            <Card>
              <div className="flex flex-wrap items-start gap-3">
                <div className="min-w-0 flex-1">
                  <h2 className="text-lg font-semibold text-gray-900">
                    {shown.name} <span className="font-normal text-gray-400">#{shown.id}</span>
                  </h2>
                  {shown.url && (
                    <a href={shown.url} target="_blank" rel="noreferrer" className={`text-sm break-all ${LINK_CLASS}`}>
                      {shown.url}
                    </a>
                  )}
                  {shown.geo.length > 0 && (
                    <p className="mt-1 text-sm text-gray-600">Geo → google: {shown.geo.join(", ")}</p>
                  )}
                </div>
                <Button disabled={sync.busy} onClick={() => fetchFromKeitaro(shown)}>
                  {sync.busy ? "Fetching…" : "⟳ Fetch from Keitaro"}
                </Button>
              </div>
            </Card>
            {[...shown.streams].sort(byPosition).map((stream) => (
              <StreamCard key={stream.id} stream={stream} onChange={replaceStream} />
            ))}
            {shown.streams.length === 0 && (
              <Card>
                <p className="text-sm text-gray-500">This campaign has no streams.</p>
              </Card>
            )}
          </>
        ) : (
          <Card>
            <p className="text-sm text-gray-500">
              {loading ? "Loading campaign…" : "Pick a campaign on the left to edit its streams."}
            </p>
          </Card>
        )}
      </div>
    </div>
  );
}
