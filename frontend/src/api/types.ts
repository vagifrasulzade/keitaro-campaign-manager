// Mirrors backend/app/schemas/*. Keep in sync when the API changes.

export interface NamedItem {
  id: number;
  name: string;
}

export interface Meta {
  mock_mode: boolean;
  domains: NamedItem[];
  groups: NamedItem[];
  traffic_sources: NamedItem[];
  default_domain_id: number | null;
  default_group_id: number | null;
  default_traffic_source_id: number | null;
}

export interface Offer {
  id: number;
  name: string;
  state: string;
  country: string[];
}

export type OfferStatus = "active" | "removed";

export interface StreamOffer {
  offer_id: number;
  offer_name: string;
  share: number;
  status: OfferStatus;
  is_pinned: boolean;
  published_share: number | null;
  published_status: OfferStatus | null;
  is_published: boolean;
  is_dirty: boolean;
}

/** Keitaro stream filter, passed through as-is (payload shape depends on the filter). */
export interface StreamFilter {
  name: string;
  mode: string;
  payload: unknown;
}

export interface Stream {
  id: number;
  name: string;
  position: number;
  type: string;
  schema: string;
  action_type: string | null;
  action_payload: string | null;
  state: string;
  filters: StreamFilter[];
  supports_offers: boolean;
  is_dirty: boolean;
  total_share: number;
  offers: StreamOffer[];
}

export interface Campaign {
  id: number;
  name: string;
  alias: string;
  url: string | null;
  geo: string[];
  origin: string;
  domain_id: number | null;
  group_id: number | null;
  traffic_source_id: number | null;
  streams: Stream[];
}

export interface CampaignListItem {
  id: number;
  name: string;
  alias: string | null;
  state: string | null;
  group_id: number | null;
  is_local: boolean;
}

export interface CampaignCreate {
  name: string;
  /** "MX, AU RO" — the backend splits, uppercases and validates it */
  geo: string;
  offer_id: number;
  domain_id: number | null;
  group_id: number | null;
  traffic_source_id: number | null;
}
