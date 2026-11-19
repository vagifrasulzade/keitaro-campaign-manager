import type { Campaign, CampaignCreate, CampaignListItem, Meta, Offer, Stream } from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function errorText(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

interface ValidationIssue {
  loc?: (string | number)[];
  msg?: string;
}

/** `{detail: "..."}` or FastAPI 422 `{detail: [{loc, msg}]}` → one readable line. */
function describeError(status: number, body: unknown): string {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string" && detail) return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((issue: ValidationIssue) => {
        const field = (issue.loc ?? []).filter((part) => part !== "body").join(".");
        const msg = (issue.msg ?? "invalid value").replace(/^Value error, /, "");
        return field ? `${field}: ${msg}` : msg;
      })
      .join("; ");
  }
  return `Request failed (HTTP ${status})`;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  let response: Response;
  try {
    response = await fetch(BASE + path, {
      method,
      headers: body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "Cannot reach the backend — is it running on :8000?");
  }

  const text = await response.text();
  let data: unknown = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }
  if (!response.ok) throw new ApiError(response.status, describeError(response.status, data));
  return data as T;
}

// Identical GETs that are still in flight share one request. React StrictMode runs effects
// twice in dev, and opening a campaign for the first time imports it — two parallel imports
// of the same campaign would race on the backend.
const inflight = new Map<string, Promise<unknown>>();

function get<T>(path: string): Promise<T> {
  const pending = inflight.get(path);
  if (pending) return pending as Promise<T>;
  const promise = request<T>("GET", path).finally(() => inflight.delete(path));
  inflight.set(path, promise);
  return promise;
}

const query = (params: Record<string, string | number>) =>
  new URLSearchParams(Object.entries(params).map(([key, value]) => [key, String(value)])).toString();

const offerPath = (streamId: number, offerId: number) => `/streams/${streamId}/offers/${offerId}`;

export const api = {
  meta: () => get<Meta>("/meta"),
  searchOffers: (q: string, limit = 15) => get<Offer[]>(`/offers?${query({ q, limit })}`),

  createCampaign: (data: CampaignCreate) => request<Campaign>("POST", "/campaigns", data),
  listCampaigns: (q = "") => get<CampaignListItem[]>(`/campaigns?${query({ q })}`),
  getCampaign: (id: number) => get<Campaign>(`/campaigns/${id}`),
  syncCampaign: (id: number) => request<Campaign>("POST", `/campaigns/${id}/sync`),

  addOffer: (streamId: number, offerId: number) =>
    request<Stream>("POST", `/streams/${streamId}/offers`, { offer_id: offerId }),
  removeOffer: (streamId: number, offerId: number) => request<Stream>("DELETE", offerPath(streamId, offerId)),
  restoreOffer: (streamId: number, offerId: number) =>
    request<Stream>("POST", `${offerPath(streamId, offerId)}/restore`),
  /** a number pins the offer with that share, null unpins it */
  setShare: (streamId: number, offerId: number, share: number | null) =>
    request<Stream>("PATCH", offerPath(streamId, offerId), { share }),
  push: (streamId: number) => request<Stream>("POST", `/streams/${streamId}/push`),
  cancel: (streamId: number) => request<Stream>("POST", `/streams/${streamId}/cancel`),
};
