import { useId, useRef, useState } from "react";
import type { FormEvent } from "react";
import { api } from "../api/client";
import type { Campaign, Meta, NamedItem, Offer, Stream } from "../api/types";
import { OfferAutocomplete } from "../components/OfferAutocomplete";
import { useAction, useToast } from "../components/Toast";
import { Button, Card, Field, INPUT_CLASS, LINK_CLASS, Tag } from "../components/ui";
import { byPosition, formatFilter } from "../format";

const COUNTRY_CODE = /^[A-Z]{2}$/;

/** "mx, au;ro AU" → ["MX", "AU", "RO"] — same rules as the backend */
function parseGeo(input: string): string[] {
  return [...new Set(input.split(/[\s,;]+/).filter(Boolean).map((code) => code.toUpperCase()))];
}

interface Props {
  meta: Meta | null;
  onOpenInEditor: (campaignId: number) => void;
}

export function CreateCampaign({ meta, onOpenInEditor }: Props) {
  const toast = useToast();
  const { run, busy } = useAction();
  const nameId = useId();
  const geoId = useId();
  const offerId = useId();

  const [name, setName] = useState("");
  const [geo, setGeo] = useState("");
  const [offer, setOffer] = useState<Offer | null>(null);
  const [focusOffer, setFocusOffer] = useState(false);
  const [showTarget, setShowTarget] = useState(false);
  // null → use the default from /meta
  const [domainId, setDomainId] = useState<number | null>(null);
  const [groupId, setGroupId] = useState<number | null>(null);
  const [sourceId, setSourceId] = useState<number | null>(null);
  const [created, setCreated] = useState<Campaign | null>(null);

  const codes = parseGeo(geo);
  const badCodes = codes.filter((code) => !COUNTRY_CODE.test(code));
  const domain = domainId ?? meta?.default_domain_id ?? null;
  const group = groupId ?? meta?.default_group_id ?? null;
  const source = sourceId ?? meta?.default_traffic_source_id ?? null;

  function validationError(): string | null {
    if (!name.trim()) return "Enter a campaign name";
    if (codes.length === 0) return "Enter at least one country code";
    if (badCodes.length > 0) return `Not a 2-letter country code: ${badCodes.join(", ")}`;
    if (!offer) return "Pick an offer";
    return null;
  }

  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const error = validationError();
    if (error || !offer) {
      toast(error ?? "Pick an offer", "error");
      return;
    }
    const campaign = await run(() =>
      api.createCampaign({
        name: name.trim(),
        geo: codes.join(", "),
        offer_id: offer.id,
        domain_id: domain,
        group_id: group,
        traffic_source_id: source,
      }),
    );
    if (!campaign) return;
    toast(`Campaign "${campaign.name}" created`);
    setCreated(campaign);
    setName("");
    setGeo("");
    setOffer(null);
    setFocusOffer(false);
  }

  const targetSummary = meta
    ? [nameOf(meta.domains, domain), nameOf(meta.groups, group), nameOf(meta.traffic_sources, source)].join(" · ")
    : "";

  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <Card>
        <h2 className="text-lg font-semibold text-gray-900">New campaign</h2>
        <p className="mt-1 text-sm text-gray-500">
          Creates a Keitaro campaign with two streams: listed countries → redirect, everybody else → offer.
        </p>

        <form onSubmit={submit} className="mt-5 space-y-4">
          <Field label="Name" htmlFor={nameId}>
            <input
              id={nameId}
              required
              maxLength={255}
              className={INPUT_CLASS}
              placeholder="test_yourname_campaign1"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </Field>

          <Field
            label="Geo"
            htmlFor={geoId}
            hint="Visitors from these countries → google.com. Everybody else → offer."
          >
            <input
              id={geoId}
              className={INPUT_CLASS}
              placeholder="MX, AU, RO"
              value={geo}
              onChange={(e) => setGeo(e.target.value)}
            />
            {codes.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {codes.map((code) => (
                  <Tag key={code} tone={COUNTRY_CODE.test(code) ? "gray" : "red"}>
                    {code}
                  </Tag>
                ))}
              </div>
            )}
          </Field>

          <Field label="Offer" htmlFor={offerId}>
            {offer ? (
              <div className="flex items-center gap-2 rounded border border-gray-300 bg-gray-50 px-3 py-2 text-sm">
                <span className="shrink-0 text-gray-500">[{offer.id}]</span>
                <span className="min-w-0 flex-1 truncate" title={offer.name}>
                  {offer.name}
                </span>
                <button
                  type="button"
                  className={`shrink-0 ${LINK_CLASS}`}
                  onClick={() => {
                    setOffer(null);
                    setFocusOffer(true);
                  }}
                >
                  change
                </button>
              </div>
            ) : (
              <OfferAutocomplete id={offerId} autoFocus={focusOffer} onSelect={setOffer} />
            )}
          </Field>

          <div>
            <button
              type="button"
              aria-expanded={showTarget}
              className="text-sm text-gray-600 hover:text-gray-900"
              onClick={() => setShowTarget((v) => !v)}
            >
              {showTarget ? "▾" : "▸"} Domain, group, source
              {!showTarget && targetSummary && <span className="ml-2 text-gray-400">{targetSummary}</span>}
            </button>
            {showTarget && (
              <div className="mt-3 grid gap-3 sm:grid-cols-3">
                <SelectField label="Domain" items={meta?.domains} value={domain} onChange={setDomainId} />
                <SelectField label="Group" items={meta?.groups} value={group} onChange={setGroupId} />
                <SelectField label="Traffic source" items={meta?.traffic_sources} value={source} onChange={setSourceId} />
              </div>
            )}
          </div>

          <div className="flex justify-end border-t border-gray-100 pt-4">
            <Button type="submit" variant="primary" disabled={busy}>
              {busy ? "Creating…" : "Create"}
            </Button>
          </div>
        </form>
      </Card>

      {created && <CreatedCampaign campaign={created} onOpenInEditor={() => onOpenInEditor(created.id)} />}
    </div>
  );
}

function nameOf(items: NamedItem[], id: number | null): string {
  return items.find((item) => item.id === id)?.name ?? "—";
}

interface SelectFieldProps {
  label: string;
  items: NamedItem[] | undefined;
  value: number | null;
  onChange: (id: number) => void;
}

function SelectField({ label, items, value, onChange }: SelectFieldProps) {
  const id = useId();
  return (
    <Field label={label} htmlFor={id}>
      <select
        id={id}
        className={INPUT_CLASS}
        disabled={!items}
        value={value ?? ""}
        onChange={(e) => onChange(Number(e.target.value))}
      >
        {!items && <option value="">Loading…</option>}
        {items && value === null && <option value="">Select…</option>}
        {items?.map((item) => (
          <option key={item.id} value={item.id}>
            {item.name}
          </option>
        ))}
      </select>
    </Field>
  );
}

function CreatedCampaign({ campaign, onOpenInEditor }: { campaign: Campaign; onOpenInEditor: () => void }) {
  const toast = useToast();
  const urlRef = useRef<HTMLInputElement>(null);

  async function copyUrl() {
    if (!campaign.url) return;
    try {
      await navigator.clipboard.writeText(campaign.url);
      toast("URL copied");
    } catch {
      // no clipboard API outside https / localhost
      urlRef.current?.select();
      toast("Could not copy automatically — press Ctrl+C", "error");
    }
  }

  return (
    <Card>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-gray-900">Campaign created</h3>
          <p className="text-sm text-gray-500">
            {campaign.name} · Keitaro ID <span className="font-semibold text-gray-900">#{campaign.id}</span>
          </p>
        </div>
        <Button variant="primary" onClick={onOpenInEditor}>
          Open in editor
        </Button>
      </div>

      <div className="mt-4 flex gap-2">
        <input
          ref={urlRef}
          readOnly
          aria-label="Campaign URL"
          className={INPUT_CLASS}
          value={campaign.url ?? ""}
          placeholder="No URL — the campaign has no domain"
          onFocus={(e) => e.target.select()}
        />
        <Button disabled={!campaign.url} onClick={copyUrl}>
          Copy
        </Button>
      </div>

      <div className="mt-4 space-y-2">
        {[...campaign.streams].sort(byPosition).map((stream) => (
          <StreamSummary key={stream.id} stream={stream} />
        ))}
      </div>
    </Card>
  );
}

function StreamSummary({ stream }: { stream: Stream }) {
  return (
    <div className="rounded border border-gray-200 px-3 py-2 text-sm">
      <div className="font-medium text-gray-900">
        #{stream.position} {stream.name}
      </div>
      {stream.filters.map((filter, i) => (
        <div key={i} className="text-xs text-green-700">
          {formatFilter(filter)}
        </div>
      ))}
      {stream.supports_offers ? (
        <ul className="mt-1 text-gray-700">
          {stream.offers.map((o) => (
            <li key={o.offer_id}>
              [{o.offer_id}] {o.offer_name} — <span className="font-semibold">{o.share}%</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="mt-1 text-gray-700">
          → {stream.action_type} {stream.action_payload}
        </div>
      )}
    </div>
  );
}
