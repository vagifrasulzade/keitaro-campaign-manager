import { useEffect, useState } from "react";
import type { KeyboardEvent } from "react";
import { api } from "../api/client";
import type { Stream, StreamOffer } from "../api/types";
import { formatFilter } from "../format";
import { OfferAutocomplete } from "./OfferAutocomplete";
import { useAction, useToast } from "./Toast";
import { Button, Card, Tag } from "./ui";

interface Props {
  stream: Stream;
  /** called with the stream returned by every editor endpoint */
  onChange: (stream: Stream) => void;
}

/** One stream of a campaign. All share math happens on the backend — this only renders its answer. */
export function StreamCard({ stream, onChange }: Props) {
  const toast = useToast();
  const { run, busy } = useAction();
  const streamId = stream.id;

  async function apply(call: () => Promise<Stream>, success?: string): Promise<boolean> {
    if (busy) return false;
    const updated = await run(call);
    if (!updated) return false;
    onChange(updated);
    if (success) toast(success);
    return true;
  }

  return (
    <Card highlight={stream.is_dirty}>
      <header className="flex flex-wrap items-center gap-2">
        <h3 className="font-semibold text-gray-900">
          #{stream.position} {stream.name}
        </h3>
        <Tag>{stream.type}</Tag>
        <Tag>{stream.schema}</Tag>
        {stream.state !== "active" && <Tag tone="red">{stream.state}</Tag>}
        <span className="ml-auto text-xs text-gray-500">Keitaro stream #{stream.id}</span>
      </header>
      {stream.filters.length > 0 ? (
        <p className="mt-1 text-sm text-green-700">{stream.filters.map(formatFilter).join(" · ")}</p>
      ) : (
        <p className="mt-1 text-sm text-gray-400">No filters</p>
      )}

      {!stream.supports_offers ? (
        <p className="mt-3 text-sm text-gray-700">
          → {stream.action_type} <span className="break-all">{stream.action_payload}</span>
        </p>
      ) : (
        <>
          {stream.is_dirty && (
            <p className="mt-3 rounded bg-amber-50 px-3 py-2 text-sm text-amber-800">
              Unpublished changes — Keitaro still has the previous version.
            </p>
          )}

          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 text-left text-xs text-gray-500 uppercase">
                  <th className="w-16 py-2 pr-2 font-medium">ID</th>
                  <th className="py-2 pr-2 font-medium">Offer</th>
                  <th className="w-36 py-2 pr-2 font-medium">Share</th>
                  <th className="w-10 py-2 pr-2 text-center font-medium">📌</th>
                  <th className="w-28 py-2 font-medium">
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {stream.offers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-4 text-center text-gray-500">
                      No offers yet — add one below.
                    </td>
                  </tr>
                )}
                {stream.offers.map((offer) => (
                  <OfferRow
                    key={offer.offer_id}
                    offer={offer}
                    busy={busy}
                    onSetShare={(share) => apply(() => api.setShare(streamId, offer.offer_id, share))}
                    onRemove={() => apply(() => api.removeOffer(streamId, offer.offer_id))}
                    onRestore={() => apply(() => api.restoreOffer(streamId, offer.offer_id))}
                  />
                ))}
              </tbody>
            </table>
          </div>

          <footer className="mt-4 flex flex-wrap items-center gap-3 border-t border-gray-100 pt-4">
            <div className="min-w-56 flex-1">
              <OfferAutocomplete
                placeholder="+ Add offer (name or ID)…"
                onSelect={(offer) => apply(() => api.addOffer(streamId, offer.id))}
              />
            </div>
            <span
              className={`text-sm font-semibold ${stream.total_share === 100 ? "text-green-700" : "text-red-600"}`}
            >
              Total: {stream.total_share}%
            </span>
            <Button disabled={busy || !stream.is_dirty} onClick={() => apply(() => api.cancel(streamId), "Draft discarded")}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={busy || !stream.is_dirty || stream.total_share !== 100}
              onClick={() => apply(() => api.push(streamId), "Pushed to Keitaro")}
            >
              Push to Keitaro
            </Button>
          </footer>
        </>
      )}
    </Card>
  );
}

interface OfferRowProps {
  offer: StreamOffer;
  busy: boolean;
  /** resolves to false if the request failed */
  onSetShare: (share: number | null) => Promise<boolean>;
  onRemove: () => void;
  onRestore: () => void;
}

function OfferRow({ offer, busy, onSetShare, onRemove, onRestore }: OfferRowProps) {
  const toast = useToast();
  const [value, setValue] = useState(String(offer.share));
  const active = offer.status === "active";

  useEffect(() => setValue(String(offer.share)), [offer.share]);

  const revert = () => setValue(String(offer.share));

  async function commitShare() {
    const text = value.trim();
    if (text === String(offer.share)) return;
    const share = Number(text);
    if (text === "" || !Number.isInteger(share) || share < 1 || share > 100) {
      toast("Share must be a whole number from 1 to 100", "error");
      revert();
      return;
    }
    if (!(await onSetShare(share))) revert();
  }

  function onShareKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") e.currentTarget.blur(); // blur commits
    else if (e.key === "Escape") revert();
  }

  let badge = null;
  if (!offer.is_published) badge = <Tag tone="green">new</Tag>;
  else if (!active && offer.published_status === "active") badge = <Tag tone="red">will be removed</Tag>;
  else if (!active) badge = <Tag>removed</Tag>;

  return (
    <tr className={`border-b border-gray-100 last:border-0 ${offer.is_dirty ? "bg-amber-50" : ""}`}>
      <td className="py-2 pr-2 text-gray-500">{offer.offer_id}</td>
      <td className="py-2 pr-2">
        <span className={active ? "text-gray-900" : "text-gray-400 line-through"}>{offer.offer_name}</span>
        {badge && <span className="ml-2">{badge}</span>}
      </td>
      <td className="py-2 pr-2">
        <div className="flex items-center gap-1.5">
          {active ? (
            <>
              <input
                type="number"
                min={1}
                max={100}
                aria-label={`Share of offer ${offer.offer_id}`}
                className={`w-16 rounded border px-2 py-1 text-right text-sm outline-none focus:ring-2 focus:ring-green-100 ${
                  offer.is_pinned ? "border-amber-400 bg-amber-50 font-semibold" : "border-gray-300 bg-white"
                }`}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onBlur={commitShare}
                onKeyDown={onShareKeyDown}
              />
              <span className="text-gray-500">%</span>
            </>
          ) : (
            <span className="text-gray-400">0%</span>
          )}
          {offer.is_published && offer.published_share !== offer.share && (
            <span className="text-xs whitespace-nowrap text-gray-400">was {offer.published_share}%</span>
          )}
        </div>
      </td>
      <td className="py-2 pr-2 text-center">
        {active && (
          <button
            type="button"
            disabled={busy}
            aria-pressed={offer.is_pinned}
            title={offer.is_pinned ? "Unpin — the share is calculated automatically" : "Pin the current share"}
            className={`rounded px-1.5 py-0.5 disabled:cursor-not-allowed disabled:opacity-45 ${
              offer.is_pinned ? "bg-amber-100 ring-1 ring-amber-400" : "opacity-40 grayscale hover:opacity-100"
            }`}
            onClick={() => onSetShare(offer.is_pinned ? null : offer.share)}
          >
            📌
          </button>
        )}
      </td>
      <td className="py-2 text-right">
        {active ? (
          <Button variant="danger" size="sm" disabled={busy} onClick={onRemove}>
            Remove
          </Button>
        ) : (
          <Button size="sm" disabled={busy} onClick={onRestore}>
            Bring back
          </Button>
        )}
      </td>
    </tr>
  );
}
